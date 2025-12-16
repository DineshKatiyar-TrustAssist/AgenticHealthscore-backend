from typing import Dict, List
from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.agents.sentiment_agent import SentimentAnalysisAgent
from app.agents.health_score_agent import HealthScoreAgent
from app.agents.churn_prediction_agent import ChurnPredictionAgent
from app.agents.action_item_agent import ActionItemAgent
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CustomerHealthOrchestrator:
    """
    Orchestrates the multi-agent workflow for customer health analysis.

    Workflow:
    1. Fetch customer messages from database
    2. Sentiment Agent: Analyze message sentiments
    3. Health Score Agent: Calculate overall health score
    4. Churn Prediction Agent: Predict churn probability
    5. Action Item Agent: Generate recommendations
    6. Store results in database
    """

    def __init__(self, db_session, google_api_key: str = None):
        self.db = db_session
        self.google_api_key = google_api_key
        self.sentiment_agent = SentimentAnalysisAgent(api_key=google_api_key)
        self.health_score_agent = HealthScoreAgent(api_key=google_api_key)
        self.churn_agent = ChurnPredictionAgent(api_key=google_api_key)
        self.action_agent = ActionItemAgent(api_key=google_api_key)

    async def analyze_customer(
        self,
        customer_id: UUID,
        analysis_period_days: int = 30,
    ) -> Dict:
        """
        Run the complete health analysis workflow for a customer.

        Args:
            customer_id: UUID of the customer
            analysis_period_days: Number of days to analyze

        Returns:
            Complete analysis result with score, churn prediction, and actions
        """
        from app.services.customer_service import CustomerService
        from app.services.message_service import MessageService
        from app.services.health_score_service import HealthScoreService

        logger.info(f"Starting health analysis for customer {customer_id}")

        customer_service = CustomerService(self.db)
        message_service = MessageService(self.db)
        health_score_service = HealthScoreService(self.db)

        # Step 1: Gather customer data
        customer = await customer_service.get_by_id(customer_id)
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        from datetime import timezone
        period_start = datetime.now(timezone.utc) - timedelta(days=analysis_period_days)
        # Get messages from database only - no Slack API calls
        messages = await message_service.get_customer_messages(
            customer_id=customer_id,
            since=period_start,
        )

        if not messages:
            logger.warning(f"No messages found for customer {customer_id}")
            return {
                "status": "insufficient_data",
                "customer_id": str(customer_id),
                "message": "No messages found in analysis period",
            }

        # Convert messages to dict format for agents
        message_dicts = [
            {
                "content": m.content,
                "user_type": m.user_type,
                "timestamp": m.message_timestamp.isoformat(),
            }
            for m in messages
        ]

        # Step 2: Sentiment Analysis
        logger.info(f"Analyzing sentiment for {len(messages)} messages")
        sentiment_result = await self.sentiment_agent.analyze(message_dicts)

        # Update messages with sentiment scores
        await message_service.update_sentiments(messages, sentiment_result["messages"])

        # Step 3: Calculate Health Score
        logger.info("Calculating health score")
        customer_context = {
            "name": customer.name,
            "company_name": customer.company_name or "Unknown",
            "tenure_days": (datetime.now(timezone.utc) - customer.created_at).days,
        }

        health_result = await self.health_score_agent.calculate(
            customer_context=customer_context,
            messages=message_dicts,
            sentiment_summary=sentiment_result["summary"],
        )

        # Step 4: Predict Churn
        logger.info("Predicting churn probability")
        score_history = await health_score_service.get_history(
            customer_id=customer_id,
            limit=10,
        )

        # Convert history to dict format
        history_dicts = [
            {
                "score": h.score,
                "created_at": h.created_at.isoformat(),
            }
            for h in score_history
        ]

        churn_result = await self.churn_agent.predict(
            customer_context=customer_context,
            health_score_history=history_dicts,
            current_score=health_result["score"],
        )

        # Step 5: Generate Action Items
        logger.info("Generating action items")
        recent_issues = self._extract_issues(message_dicts, sentiment_result)

        actions = await self.action_agent.generate(
            customer_context=customer_context,
            health_score=health_result["score"],
            score_components=health_result["components"],
            recent_issues=recent_issues,
        )

        # Step 6: Store results
        health_score_record = await health_score_service.create(
            customer_id=customer_id,
            score=health_result["score"],
            churn_probability=churn_result["churn_probability"],
            score_components=health_result["components"],
            messages_analyzed=len(messages),
            reasoning=health_result["reasoning"],
            period_start=period_start,
            period_end=datetime.now(timezone.utc),
        )

        # Store action items
        for action in actions:
            await health_score_service.create_action_item(
                customer_id=customer_id,
                health_score_id=health_score_record.id,
                **action,
            )

        await self.db.commit()

        logger.info(f"Analysis complete for customer {customer_id}")

        return {
            "status": "success",
            "customer_id": str(customer_id),
            "health_score": health_result,
            "churn_prediction": churn_result,
            "action_items": actions,
            "messages_analyzed": len(messages),
            "analysis_period": {
                "start": period_start.isoformat(),
                "end": datetime.now(timezone.utc).isoformat(),
            },
        }

    async def analyze_all_customers(self) -> List[Dict]:
        """Run analysis for all active customers."""
        from app.services.customer_service import CustomerService

        customer_service = CustomerService(self.db)
        customers = await customer_service.get_active_customers()
        results = []

        for customer in customers:
            try:
                result = await self.analyze_customer(customer.id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error analyzing customer {customer.id}: {e}")
                results.append({
                    "status": "error",
                    "customer_id": str(customer.id),
                    "error": str(e),
                })

        return results

    def _extract_issues(
        self,
        messages: List[Dict],
        sentiment_result: Dict,
    ) -> List[str]:
        """Extract issue descriptions from negative sentiment messages."""
        issues = []

        for msg_result in sentiment_result.get("messages", []):
            if msg_result.get("sentiment_score", 0) < -0.3:
                idx = msg_result.get("index", 0)
                if idx < len(messages):
                    content = messages[idx].get("content", "")[:200]
                    issues.append(content)

        return issues[:5]  # Return top 5 issues
