from typing import Dict, List, Optional
from app.gemini.client import GeminiClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class ActionItemAgent:
    """
    Agent responsible for generating actionable recommendations.

    Uses Gemini to suggest specific actions to improve customer health.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize action item agent.
        
        Args:
            api_key: Google API key for Gemini. If not provided, will be required when generating.
        """
        self.api_key = api_key
    
    def _get_gemini_client(self) -> GeminiClient:
        """Get or create Gemini client with API key."""
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured. Please set it in the Settings page.")
        return GeminiClient(api_key=self.api_key)

    async def generate(
        self,
        customer_context: Dict,
        health_score: int,
        score_components: Dict,
        recent_issues: List[str],
    ) -> List[Dict]:
        """
        Generate action items to improve customer health.

        Args:
            customer_context: Dict with customer info (name, company_name)
            health_score: Current health score (1-10)
            score_components: Breakdown of score components
            recent_issues: List of recent issues/complaints

        Returns:
            List of action items with title, description, priority, etc.
        """
        try:
            gemini = self._get_gemini_client()
            result = await gemini.generate_action_items(
                customer_context=customer_context,
                health_score=health_score,
                score_components=score_components,
                recent_issues=recent_issues,
            )

            # Validate and normalize each action item
            return [self._validate_item(item) for item in result]

        except Exception as e:
            logger.error(f"Error generating action items: {e}")
            # Return default action items on error
            return self._default_actions(health_score, score_components)

    def _validate_item(self, item: Dict) -> Dict:
        """Validate and normalize an action item."""
        valid_priorities = ["critical", "high", "medium", "low"]
        valid_categories = ["engagement", "support", "relationship", "technical", "billing"]

        priority = item.get("priority", "medium").lower()
        if priority not in valid_priorities:
            priority = "medium"

        category = item.get("category", "engagement").lower()
        if category not in valid_categories:
            category = "engagement"

        impact_score = item.get("impact_score", 5)
        impact_score = max(1, min(10, int(impact_score)))

        effort_score = item.get("effort_score", 5)
        effort_score = max(1, min(10, int(effort_score)))

        return {
            "title": item.get("title", "Follow up with customer")[:255],
            "description": item.get("description", ""),
            "priority": priority,
            "category": category,
            "impact_score": impact_score,
            "effort_score": effort_score,
            "suggested_timeline": item.get("suggested_timeline", ""),
            "success_metrics": item.get("success_metrics", []),
        }

    def _default_actions(self, health_score: int, components: Dict) -> List[Dict]:
        """Generate default action items when AI fails."""
        actions = []

        # Always suggest a check-in for low scores
        if health_score <= 5:
            actions.append({
                "title": "Schedule customer check-in call",
                "description": "Reach out to understand current pain points and gather feedback.",
                "priority": "high" if health_score <= 3 else "medium",
                "category": "relationship",
                "impact_score": 7,
                "effort_score": 3,
                "suggested_timeline": "Within 1 week",
                "success_metrics": ["Call completed", "Feedback gathered"],
            })

        # Check component scores for specific recommendations
        if components:
            sentiment = components.get("sentiment_score", 5)
            engagement = components.get("engagement_score", 5)
            resolution = components.get("issue_resolution_score", 5)

            if sentiment < 5:
                actions.append({
                    "title": "Address customer concerns",
                    "description": "Review recent communications and address any unresolved complaints.",
                    "priority": "high",
                    "category": "support",
                    "impact_score": 8,
                    "effort_score": 4,
                    "suggested_timeline": "Within 3 days",
                    "success_metrics": ["Issues identified", "Resolution plan created"],
                })

            if engagement < 5:
                actions.append({
                    "title": "Increase customer engagement",
                    "description": "Share relevant product updates, tips, or success stories.",
                    "priority": "medium",
                    "category": "engagement",
                    "impact_score": 6,
                    "effort_score": 2,
                    "suggested_timeline": "Within 2 weeks",
                    "success_metrics": ["Content shared", "Response received"],
                })

            if resolution < 5:
                actions.append({
                    "title": "Review open support tickets",
                    "description": "Audit and prioritize any open support issues for this customer.",
                    "priority": "high",
                    "category": "support",
                    "impact_score": 8,
                    "effort_score": 5,
                    "suggested_timeline": "Within 1 week",
                    "success_metrics": ["Tickets reviewed", "Issues resolved"],
                })

        # Ensure we always have at least one action
        if not actions:
            actions.append({
                "title": "Monitor customer health",
                "description": "Continue monitoring and maintain regular communication.",
                "priority": "low",
                "category": "relationship",
                "impact_score": 4,
                "effort_score": 1,
                "suggested_timeline": "Ongoing",
                "success_metrics": ["Regular check-ins maintained"],
            })

        return actions[:5]  # Return at most 5 actions
