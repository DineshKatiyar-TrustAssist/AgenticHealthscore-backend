"""
Script to delete a user from the database.

Usage:
    python scripts/delete_user.py <email>
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_maker
from app.models.user import User
from app.models.verification_token import VerificationToken
from sqlalchemy import select


async def delete_user(email: str):
    """Delete a user by email."""
    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        
        if not user:
            print(f"User with email {email} not found.")
            return
        
        # Delete verification tokens first
        tokens_result = await session.execute(
            select(VerificationToken).where(VerificationToken.user_id == user.id)
        )
        tokens = tokens_result.scalars().all()
        for token in tokens:
            await session.delete(token)
        
        # Delete user
        await session.delete(user)
        await session.commit()
        print(f"✓ User {email} and associated tokens deleted successfully.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/delete_user.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    asyncio.run(delete_user(email))

