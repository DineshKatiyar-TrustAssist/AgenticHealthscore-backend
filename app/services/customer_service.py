from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.health_score import HealthScore
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class CustomerService:
    """Service for managing customer operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: CustomerCreate) -> Customer:
        """Create a new customer."""
        customer = Customer(
            name=data.name,
            company_name=data.company_name,
            email=data.email,
            slack_user_id=data.slack_user_id,
        )
        self.db.add(customer)
        await self.db.flush()
        await self.db.refresh(customer)
        logger.info(f"Created customer: {customer.id}")
        return customer

    async def get_by_id(self, customer_id: str) -> Optional[Customer]:
        """Get customer by ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slack_user_id(self, slack_user_id: str) -> Optional[Customer]:
        """Get customer by Slack user ID."""
        result = await self.db.execute(
            select(Customer).where(Customer.slack_user_id == slack_user_id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False,
    ) -> tuple[List[Customer], int]:
        """Get all customers with pagination."""
        query = select(Customer)

        if not include_inactive:
            query = query.where(Customer.is_active == True)

        # Get total count
        count_query = select(func.count(Customer.id))
        if not include_inactive:
            count_query = count_query.where(Customer.is_active == True)
        total = (await self.db.execute(count_query)).scalar()

        # Get customers
        query = query.offset(skip).limit(limit).order_by(Customer.created_at.desc())
        result = await self.db.execute(query)
        customers = result.scalars().all()

        return list(customers), total

    async def get_active_customers(self) -> List[Customer]:
        """Get all active customers."""
        result = await self.db.execute(
            select(Customer).where(Customer.is_active == True)
        )
        return list(result.scalars().all())

    async def update(self, customer_id: str, data: CustomerUpdate) -> Optional[Customer]:
        """Update a customer."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(customer, field, value)

        customer.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        await self.db.refresh(customer)
        logger.info(f"Updated customer: {customer_id}")
        return customer

    async def delete(self, customer_id: str) -> bool:
        """Delete a customer (soft delete by setting is_active=False)."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return False

        customer.is_active = False
        customer.updated_at = datetime.now(timezone.utc)
        await self.db.flush()
        logger.info(f"Deleted customer: {customer_id}")
        return True

    async def get_with_latest_score(self, customer_id: str) -> Optional[dict]:
        """Get customer with their latest health score."""
        customer = await self.get_by_id(customer_id)
        if not customer:
            return None

        # Get latest health score
        result = await self.db.execute(
            select(HealthScore)
            .where(HealthScore.customer_id == customer_id)
            .order_by(HealthScore.created_at.desc())
            .limit(1)
        )
        latest_score = result.scalar_one_or_none()

        return {
            "customer": customer,
            "latest_score": latest_score.score if latest_score else None,
            "churn_probability": float(latest_score.churn_probability) if latest_score and latest_score.churn_probability else None,
        }

    async def get_at_risk_customers(self, churn_threshold: float = 0.5) -> List[dict]:
        """Get customers with churn probability above threshold."""
        # Subquery for latest health score per customer
        latest_score_subq = (
            select(
                HealthScore.customer_id,
                func.max(HealthScore.created_at).label("latest_date")
            )
            .group_by(HealthScore.customer_id)
            .subquery()
        )

        query = (
            select(Customer, HealthScore)
            .join(HealthScore, Customer.id == HealthScore.customer_id)
            .join(
                latest_score_subq,
                (HealthScore.customer_id == latest_score_subq.c.customer_id) &
                (HealthScore.created_at == latest_score_subq.c.latest_date)
            )
            .where(
                Customer.is_active == True,
                HealthScore.churn_probability >= churn_threshold
            )
            .order_by(HealthScore.churn_probability.desc())
        )

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "customer": row[0],
                "health_score": row[1].score,
                "churn_probability": float(row[1].churn_probability),
            }
            for row in rows
        ]
