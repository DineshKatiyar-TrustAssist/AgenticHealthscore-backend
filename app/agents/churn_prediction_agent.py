from typing import Dict, List, Optional
from app.gemini.client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ChurnPredictionAgent:
    """
    Agent responsible for predicting customer churn probability.

    Uses Gemini to analyze health score patterns and predict churn risk.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize churn prediction agent.
        
        Args:
            api_key: Google API key for Gemini. If not provided, will be required when predicting.
        """
        self.api_key = api_key
    
    def _get_gemini_client(self) -> GeminiClient:
        """Get or create Gemini client with API key."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured. Please set it in the Settings page.")
        return GeminiClient(api_key=self.api_key)

    async def predict(
        self,
        customer_context: Dict,
        health_score_history: List[Dict],
        current_score: int,
    ) -> Dict:
        """
        Predict churn probability for a customer.

        Args:
            customer_context: Dict with customer info (name, tenure_days)
            health_score_history: List of historical health scores
            current_score: Current health score (1-10)

        Returns:
            Dict with churn_probability, risk_level, and factors
        """
        try:
            gemini = self._get_gemini_client()
            result = await gemini.predict_churn(
                customer_context=customer_context,
                health_score_history=health_score_history,
                current_score=current_score,
            )

            # Validate and normalize the result
            return self._validate_result(result, current_score)

        except Exception as e:
            logger.error(f"Error predicting churn: {e}")
            # Return a heuristic-based prediction on error
            return self._heuristic_prediction(current_score, health_score_history)

    def _validate_result(self, result: Dict, current_score: int) -> Dict:
        """Validate and normalize the churn prediction result."""
        # Ensure probability is within bounds
        probability = result.get("churn_probability", 0.5)
        probability = max(0.0, min(1.0, float(probability)))

        # Validate risk level
        valid_levels = ["low", "medium", "high", "critical"]
        risk_level = result.get("risk_level", "medium").lower()
        if risk_level not in valid_levels:
            risk_level = self._calculate_risk_level(probability)

        return {
            "churn_probability": round(probability, 4),
            "risk_level": risk_level,
            "contributing_factors": result.get("contributing_factors", []),
            "protective_factors": result.get("protective_factors", []),
            "predicted_timeframe": result.get("predicted_timeframe", "Unknown"),
            "confidence": min(1.0, max(0.0, float(result.get("confidence", 0.7)))),
        }

    def _heuristic_prediction(
        self,
        current_score: int,
        history: List[Dict],
    ) -> Dict:
        """Calculate a simple heuristic-based prediction when AI fails."""
        # Base probability on current score
        base_probability = (10 - current_score) / 10 * 0.6

        # Adjust based on trend
        if len(history) >= 2:
            recent_scores = [h.get("score", 5) for h in history[-5:]]
            avg_recent = sum(recent_scores) / len(recent_scores)
            if avg_recent < current_score:
                base_probability += 0.1  # Declining trend
            elif avg_recent > current_score:
                base_probability -= 0.1  # Improving trend

        probability = max(0.0, min(1.0, base_probability))

        return {
            "churn_probability": round(probability, 4),
            "risk_level": self._calculate_risk_level(probability),
            "contributing_factors": self._identify_factors(current_score, history),
            "protective_factors": [],
            "predicted_timeframe": "Unknown (heuristic prediction)",
            "confidence": 0.4,
        }

    def _calculate_risk_level(self, probability: float) -> str:
        """Calculate risk level from probability."""
        if probability < 0.2:
            return "low"
        elif probability < 0.5:
            return "medium"
        elif probability < 0.75:
            return "high"
        else:
            return "critical"

    def _identify_factors(self, current_score: int, history: List[Dict]) -> List[str]:
        """Identify basic contributing factors."""
        factors = []

        if current_score <= 3:
            factors.append("Very low health score")
        elif current_score <= 5:
            factors.append("Below average health score")

        if len(history) >= 3:
            recent = [h.get("score", 5) for h in history[-3:]]
            if all(recent[i] >= recent[i + 1] for i in range(len(recent) - 1)):
                factors.append("Declining score trend")

        return factors
