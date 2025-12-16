from typing import Dict, List, Optional
from app.gemini.client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class SentimentAnalysisAgent:
    """
    Agent responsible for analyzing sentiment in customer messages.

    Uses Gemini to perform batch sentiment analysis with context awareness.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize sentiment analysis agent.
        
        Args:
            api_key: Google API key for Gemini. If not provided, will be required when analyzing.
        """
        self.api_key = api_key
        self.batch_size = 50  # Process messages in batches
    
    def _get_gemini_client(self) -> GeminiClient:
        """Get or create Gemini client with API key."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured. Please set it in the Settings page.")
        return GeminiClient(api_key=self.api_key)

    async def analyze(self, messages: List[Dict]) -> Dict:
        """
        Analyze sentiment for a list of messages.

        Args:
            messages: List of message dictionaries with 'content' and 'user_type'

        Returns:
            Dict with per-message sentiments and summary
        """
        if not messages:
            return {
                "messages": [],
                "summary": self._empty_summary(),
            }

        all_results = []

        # Process in batches for large message volumes
        for i in range(0, len(messages), self.batch_size):
            batch = messages[i : i + self.batch_size]

            try:
                gemini = self._get_gemini_client()
                batch_result = await gemini.analyze_sentiment(batch)

                # Adjust indices for batched processing
                for msg_result in batch_result.get("messages", []):
                    msg_result["index"] = msg_result.get("index", 0) + i

                all_results.extend(batch_result.get("messages", []))

            except Exception as e:
                logger.error(f"Error analyzing sentiment batch {i}: {e}")
                # Add placeholder results for failed batch
                for j in range(len(batch)):
                    all_results.append({
                        "index": i + j,
                        "sentiment_score": 0,
                        "sentiment_label": "neutral",
                        "sentiment_magnitude": 0,
                        "key_phrases": [],
                        "error": str(e),
                    })

        # Calculate overall summary
        summary = self._calculate_summary(all_results)

        return {
            "messages": all_results,
            "summary": summary,
        }

    def _calculate_summary(self, results: List[Dict]) -> Dict:
        """Calculate summary statistics from sentiment results."""
        if not results:
            return self._empty_summary()

        scores = [r.get("sentiment_score", 0) for r in results if "error" not in r]

        if not scores:
            return self._empty_summary()

        avg_score = sum(scores) / len(scores)

        # Calculate trend (comparing first half vs second half)
        mid = len(scores) // 2
        if mid > 0:
            first_half_avg = sum(scores[:mid]) / mid
            second_half_avg = sum(scores[mid:]) / len(scores[mid:])

            if second_half_avg > first_half_avg + 0.1:
                trend = "improving"
            elif second_half_avg < first_half_avg - 0.1:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Determine dominant sentiment
        if avg_score > 0.2:
            dominant = "positive"
        elif avg_score < -0.2:
            dominant = "negative"
        else:
            dominant = "neutral"

        # Extract common themes
        all_phrases = []
        for r in results:
            all_phrases.extend(r.get("key_phrases", []))

        # Count phrase frequency
        phrase_counts = {}
        for phrase in all_phrases:
            phrase_lower = phrase.lower()
            phrase_counts[phrase_lower] = phrase_counts.get(phrase_lower, 0) + 1

        key_themes = sorted(
            phrase_counts.keys(),
            key=lambda x: phrase_counts[x],
            reverse=True,
        )[:5]

        return {
            "average_score": round(avg_score, 3),
            "trend": trend,
            "dominant_sentiment": dominant,
            "key_themes": key_themes,
            "total_analyzed": len(results),
            "positive_count": sum(1 for s in scores if s > 0.2),
            "negative_count": sum(1 for s in scores if s < -0.2),
            "neutral_count": sum(1 for s in scores if -0.2 <= s <= 0.2),
        }

    def _empty_summary(self) -> Dict:
        """Return empty summary structure."""
        return {
            "average_score": 0,
            "trend": "stable",
            "dominant_sentiment": "neutral",
            "key_themes": [],
            "total_analyzed": 0,
            "positive_count": 0,
            "negative_count": 0,
            "neutral_count": 0,
        }
