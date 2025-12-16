import json
import re
from typing import Dict, List, Optional
from google import genai
from google.genai.types import GenerateContentConfig

from app.config import settings
from app.gemini.prompts import (
    SENTIMENT_ANALYSIS_PROMPT,
    HEALTH_SCORE_PROMPT,
    CHURN_PREDICTION_PROMPT,
    ACTION_ITEMS_PROMPT,
)
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class GeminiClient:
    """Client for Google Gemini API interactions."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google API key. If not provided, will raise ValueError.
            model: Gemini model name. Defaults to settings.GEMINI_MODEL.
        """
        if not api_key:
            raise ValueError("GOOGLE_API_KEY is not configured. Please set it in the Settings page.")
        self.client = genai.Client(api_key=api_key)
        self.model = model or settings.GEMINI_MODEL

    async def analyze_sentiment(self, messages: List[Dict]) -> Dict:
        """
        Analyze sentiment of a batch of messages.

        Args:
            messages: List of message dicts with 'content' and 'user_type' keys

        Returns:
            Dict with sentiment scores and labels for each message
        """
        messages_text = "\n".join(
            [f"[{m.get('user_type', 'unknown')}] {m['content']}" for m in messages]
        )

        prompt = SENTIMENT_ANALYSIS_PROMPT.format(messages=messages_text)

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        return self._parse_json_response(response.text)

    async def calculate_health_score(
        self,
        customer_context: Dict,
        messages: List[Dict],
        sentiment_summary: Dict,
    ) -> Dict:
        """
        Calculate customer health score using Gemini.

        Returns:
            Dict with score (1-10), components, and reasoning
        """
        prompt = HEALTH_SCORE_PROMPT.format(
            customer_name=customer_context.get("name", "Unknown"),
            company=customer_context.get("company_name", "Unknown"),
            message_count=len(messages),
            avg_sentiment=sentiment_summary.get("average_score", 0),
            sentiment_trend=sentiment_summary.get("trend", "stable"),
            recent_messages=self._format_recent_messages(messages[-20:]),
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        return self._parse_json_response(response.text)

    async def predict_churn(
        self,
        customer_context: Dict,
        health_score_history: List[Dict],
        current_score: int,
    ) -> Dict:
        """
        Predict churn probability.

        Returns:
            Dict with probability (0-1), risk_level, and factors
        """
        prompt = CHURN_PREDICTION_PROMPT.format(
            customer_name=customer_context.get("name", "Unknown"),
            current_score=current_score,
            score_history=self._format_score_history(health_score_history),
            tenure_days=customer_context.get("tenure_days", 0),
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )

        return self._parse_json_response(response.text)

    async def generate_action_items(
        self,
        customer_context: Dict,
        health_score: int,
        score_components: Dict,
        recent_issues: List[str],
    ) -> List[Dict]:
        """
        Generate actionable suggestions to improve health score.

        Returns:
            List of action items with title, description, priority, category
        """
        prompt = ACTION_ITEMS_PROMPT.format(
            customer_name=customer_context.get("name", "Unknown"),
            health_score=health_score,
            weak_areas=self._identify_weak_areas(score_components),
            recent_issues="\n".join(recent_issues) if recent_issues else "None identified",
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.4,
            ),
        )

        result = self._parse_json_response(response.text)
        return result.get("action_items", [])

    def _parse_json_response(self, text: str) -> Dict:
        """Parse JSON from Gemini response."""
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Extract JSON from markdown code blocks
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # Try finding raw JSON object
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        logger.error(f"Could not parse JSON from response: {text[:500]}")
        raise ValueError(f"Could not parse JSON from response")

    def _format_recent_messages(self, messages: List[Dict]) -> str:
        """Format messages for prompt."""
        return "\n".join(
            [
                f"- [{m.get('user_type', 'unknown')}] {m.get('content', '')[:200]}"
                for m in messages
            ]
        )

    def _format_score_history(self, history: List[Dict]) -> str:
        """Format health score history for prompt."""
        if not history:
            return "No previous scores available"

        return "\n".join(
            [f"- {h.get('created_at', 'N/A')}: Score {h.get('score', 'N/A')}/10" for h in history[-10:]]
        )

    def _identify_weak_areas(self, components: Dict) -> str:
        """Identify weak areas from score components."""
        if not components:
            return "None identified"

        weak = [k.replace("_", " ").title() for k, v in components.items() if v and v < 6]
        return ", ".join(weak) if weak else "None identified"
