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
        """Run complete health analysis workflow for a customer."""
        from app.services.customer_service import CustomerService
        from app.services.message_service import MessageService
        from app.services.health_score_service import HealthScoreService

        try:
            logger.info(f"Starting health analysis for customer {customer_id}")
            
            # Initialize services
            customer_service = CustomerService(self.db)
            message_service = MessageService(self.db)
            health_score_service = HealthScoreService(self.db)

            # Get customer
            customer = await customer_service.get_by_id(customer_id)
            if not customer:
                raise ValueError(f"Customer {customer_id} not found")

            # Get messages
            now = datetime.now(timezone.utc)
            period_start = now - timedelta(days=analysis_period_days)
            messages = await message_service.get_customer_messages(customer_id=customer_id, since=period_start)

            if not messages:
                return {"status": "insufficient_data", "customer_id": str(customer_id), "message": "No messages found"}

            # Convert to dict format
            message_dicts = [{"content": m.content, "user_type": m.user_type, "timestamp": m.message_timestamp.isoformat()} for m in messages]

            # Run analysis pipeline
            sentiment_result = await self.sentiment_agent.analyze(message_dicts)
            await message_service.update_sentiments(messages, sentiment_result["messages"])

            customer_created_at = customer.created_at.replace(tzinfo=timezone.utc) if customer.created_at.tzinfo is None else customer.created_at
            customer_context = {
                "name": customer.name,
                "company_name": customer.company_name or "Unknown",
                "tenure_days": (now - customer_created_at).days,
            }

            health_result = await self.health_score_agent.calculate(customer_context, message_dicts, sentiment_result["summary"])

            score_history = await health_score_service.get_history(customer_id=customer_id, limit=10)
            history_dicts = [{"score": h.score, "created_at": h.created_at.isoformat()} for h in score_history]

            churn_result = await self.churn_agent.predict(customer_context, history_dicts, health_result["score"])

            recent_issues = self._extract_issues(message_dicts, sentiment_result)
            actions = await self.action_agent.generate(customer_context, health_result["score"], health_result["components"], recent_issues)

            # Store results
            health_score_record = await health_score_service.create(
                customer_id=customer_id,
                score=health_result["score"],
                churn_probability=churn_result["churn_probability"],
                score_components=health_result["components"],
                messages_analyzed=len(messages),
                reasoning=health_result["reasoning"],
                period_start=period_start,
                period_end=now,
            )

            for action in actions:
                await health_score_service.create_action_item(customer_id=customer_id, health_score_id=health_score_record.id, **action)

            await self.db.commit()

            return {
                "status": "success",
                "customer_id": str(customer_id),
                "health_score": health_result,
                "churn_prediction": churn_result,
                "action_items": actions,
                "messages_analyzed": len(messages),
                "analysis_period": {"start": period_start.isoformat(), "end": now.isoformat()},
            }
        except Exception as e:
            logger.error(f"Error analyzing customer {customer_id}: {e}")
            await self.db.rollback()
            raise

    async def analyze_all_customers(self) -> List[Dict]:
        """Run analysis for all active customers."""
        from app.services.customer_service import CustomerService

        customers = await CustomerService(self.db).get_active_customers()
        results = []

        for customer in customers:
            try:
                results.append(await self.analyze_customer(customer.id))
            except Exception as e:
                logger.error(f"Error analyzing customer {customer.id}: {e}")
                results.append({"status": "error", "customer_id": str(customer.id), "error": str(e)})

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
