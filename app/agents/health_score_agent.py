from typing import Dict, List, Optional
from app.gemini.client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class HealthScoreAgent:
    """
    Agent responsible for calculating customer health scores.

    Uses Gemini to analyze customer data and generate a health score
    with component breakdown and reasoning.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize health score agent.
        
        Args:
            api_key: Google API key for Gemini. If not provided, will be required when calculating.
        """
        self.api_key = api_key
    
    def _get_gemini_client(self) -> GeminiClient:
        """Get or create Gemini client with API key."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured. Please set it in the Settings page.")
        return GeminiClient(api_key=self.api_key)

    async def calculate(
        self,
        customer_context: Dict,
        messages: List[Dict],
        sentiment_summary: Dict,
    ) -> Dict:
        """
        Calculate health score for a customer.

        Args:
            customer_context: Dict with customer info (name, company_name, tenure_days)
            messages: List of recent messages
            sentiment_summary: Summary from sentiment analysis

        Returns:
            Dict with score (1-10), components, reasoning, and signals
        """
        try:
            gemini = self._get_gemini_client()
            result = await gemini.calculate_health_score(
                customer_context=customer_context,
                messages=messages,
                sentiment_summary=sentiment_summary,
            )

            # Validate and normalize the result
            return self._validate_result(result)

        except Exception as e:
            logger.error(f"Error calculating health score: {e}")
            # Return a default score on error
            return self._default_result(str(e))

    def _validate_result(self, result: Dict) -> Dict:
        """Validate and normalize the health score result."""
        # Ensure score is within bounds
        score = result.get("score", 5)
        score = max(1, min(10, int(score)))

        # Validate components
        default_components = {
            "sentiment_score": 5,
            "engagement_score": 5,
            "issue_resolution_score": 5,
            "tone_consistency_score": 5,
            "response_pattern_score": 5,
        }

        components = result.get("components", {})
        validated_components = {}

        for key, default in default_components.items():
            value = components.get(key, default)
            validated_components[key] = max(1, min(10, int(value)))

        return {
            "score": score,
            "components": validated_components,
            "reasoning": result.get("reasoning", "Score calculated based on available data."),
            "positive_signals": result.get("positive_signals", []),
            "warning_signals": result.get("warning_signals", []),
            "confidence": min(1.0, max(0.0, float(result.get("confidence", 0.7)))),
        }

    def _default_result(self, error: str) -> Dict:
        """Return default result when calculation fails."""
        return {
            "score": 5,
            "components": {
                "sentiment_score": 5,
                "engagement_score": 5,
                "issue_resolution_score": 5,
                "tone_consistency_score": 5,
                "response_pattern_score": 5,
            },
            "reasoning": f"Unable to calculate accurate score: {error}",
            "positive_signals": [],
            "warning_signals": ["Calculation error - manual review recommended"],
            "confidence": 0.3,
        }
