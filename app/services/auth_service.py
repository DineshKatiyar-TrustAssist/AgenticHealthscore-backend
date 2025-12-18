import secrets
import hashlib
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User, AuthProvider
from app.models.verification_token import VerificationToken, TokenType
from app.services.email_service import EmailService
from app.config import settings
from app.utils.logger import setup_logger

logger = setup_logger(__name__)


class AuthService:
    """Service for authentication operations."""

    def __init__(self, db: AsyncSession):
        """Initialize auth service with database session."""
        self.db = db
        self.email_service = EmailService(db)

    def _hash_password(self, password: str) -> str:
        """Hash a password using bcrypt. Pre-hash with SHA256 to handle passwords > 72 bytes."""
        # Bcrypt has a 72-byte limit, so pre-hash with SHA256 for longer passwords
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > 72:
            # Pre-hash with SHA256 to get a fixed 32-byte digest (always <= 72 bytes)
            password_bytes = hashlib.sha256(password_bytes).digest()
        # Hash with bcrypt (rounds=12)
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password_bytes, salt)
        return hashed.decode('utf-8')

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        # If password is > 72 bytes, pre-hash with SHA256 before verification
        password_bytes = plain_password.encode('utf-8')
        if len(password_bytes) > 72:
            password_bytes = hashlib.sha256(password_bytes).digest()
        # Verify with bcrypt
        try:
            return bcrypt.checkpw(password_bytes, hashed_password.encode('utf-8'))
        except Exception:
            return False

    def _generate_secure_token(self, length: int = 32) -> str:
        """Generate a secure random token."""
        return secrets.token_urlsafe(length)

    async def create_user(
        self, email: str, auth_provider: AuthProvider = AuthProvider.EMAIL
    ) -> tuple[User, Optional[VerificationToken]]:
        """
        Create a new user.

        For email users: creates unverified user, generates verification token, sends emails.
        For OAuth users: creates verified user (no token needed).

        Args:
            email: User's email address
            auth_provider: Authentication provider (EMAIL or GOOGLE)

        Returns:
            Tuple of (User, VerificationToken or None)
        """
        # Check if user already exists
        result = await self.db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        # Create user
        is_verified = auth_provider != AuthProvider.EMAIL
        user = User(
            email=email,
            auth_provider=auth_provider,
            is_verified=is_verified,
        )
        self.db.add(user)
        await self.db.flush()  # Get user ID

        verification_token = None

        # For email users, create verification token and send emails
        if auth_provider == AuthProvider.EMAIL:
            verification_token = await self.generate_verification_token(
                user.id, TokenType.EMAIL_VERIFICATION
            )

            # Send verification email
            await self.email_service.send_verification_email(
                user.email, verification_token.token
            )

            # Send admin notification
            await self.email_service.send_notification_email(
                user.email, user.created_at, "pending"
            )

        await self.db.commit()
        await self.db.refresh(user)

        return user, verification_token

    async def create_or_update_oauth_user(
        self,
        email: str,
        provider: AuthProvider,
        provider_id: str,
        provider_data: Optional[dict] = None,
    ) -> User:
        """
        Create or update an OAuth user.

        OAuth users are automatically verified (OAuth providers verify emails).

        Args:
            email: User's email address
            provider: OAuth provider (e.g., AuthProvider.GOOGLE)
            provider_id: User's ID from OAuth provider
            provider_data: Optional additional data from provider

        Returns:
            User object (created or updated)
        """
        # Check if user exists by email
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user:
            # Update existing user
            user.auth_provider = provider
            user.oauth_provider_id = provider_id
            user.is_verified = True  # OAuth users are always verified
            user.updated_at = datetime.now(timezone.utc)
        else:
            # Create new user
            user = User(
                email=email,
                auth_provider=provider,
                oauth_provider_id=provider_id,
                is_verified=True,  # OAuth users are auto-verified
            )
            self.db.add(user)
            await self.db.flush()

            # Send admin notification for new OAuth signup
            await self.email_service.send_notification_email(
                user.email, user.created_at, "verified (OAuth)"
            )

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def generate_verification_token(
        self, user_id: str, token_type: TokenType
    ) -> VerificationToken:
        """
        Generate a verification token for a user.

        Args:
            user_id: User ID
            token_type: Type of token (EMAIL_VERIFICATION or PASSWORD_RESET)

        Returns:
            VerificationToken object
        """
        token = self._generate_secure_token()
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=settings.VERIFICATION_TOKEN_EXPIRY_HOURS
        )

        verification_token = VerificationToken(
            user_id=user_id,
            token=token,
            token_type=token_type,
            expires_at=expires_at,
        )

        self.db.add(verification_token)
        await self.db.commit()
        await self.db.refresh(verification_token)

        return verification_token

    async def verify_email_token(self, token: str) -> User:
        """
        Verify an email verification token and mark user as verified.

        Args:
            token: Verification token

        Returns:
            User object

        Raises:
            ValueError: If token is invalid, expired, or already used
        """
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token == token,
                VerificationToken.token_type == TokenType.EMAIL_VERIFICATION,
            )
        )
        verification_token = result.scalar_one_or_none()

        if not verification_token:
            raise ValueError("Invalid verification token")

        if verification_token.used_at:
            raise ValueError("Verification token has already been used")

        # Ensure timezone-aware comparison
        expires_at = verification_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        
        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Verification token has expired")

        # Get user
        user_result = await self.db.execute(
            select(User).where(User.id == verification_token.user_id)
        )
        user = user_result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found for verification token")

        # Mark token as used and verify user
        verification_token.used_at = datetime.now(timezone.utc)
        user.is_verified = True
        user.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_password(self, user_id: str, password: str) -> User:
        """
        Set password for a user (email users only).

        Args:
            user_id: User ID
            password: Plain text password (will be hashed)

        Returns:
            User object

        Raises:
            ValueError: If password is too short or user not found
        """
        # Validate password
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Get user
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("User not found")

        if user.auth_provider != AuthProvider.EMAIL:
            raise ValueError("Password can only be set for email-based users")

        # Hash and store password
        user.password_hash = self._hash_password(password)
        user.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """
        Authenticate a user with email and password.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise

        Raises:
            ValueError: If user is not verified
        """
        result = await self.db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            return None

        if user.auth_provider != AuthProvider.EMAIL:
            return None  # OAuth users don't have passwords

        if not user.is_verified:
            raise ValueError("Email not verified. Please verify your email before logging in.")

        if not user.password_hash:
            raise ValueError("Password not set. Please set your password first.")

        if not self._verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            raise ValueError("User account is inactive")

        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def request_password_reset(self, email: str) -> None:
        """
        Request password reset for a user.

        Args:
            email: User's email address

        Raises:
            ValueError: If user not found or not verified
        """
        user = await self.get_user_by_email(email)
        if not user:
            # Don't reveal if user exists for security
            logger.info(f"Password reset requested for non-existent email: {email}")
            return

        if user.auth_provider != AuthProvider.EMAIL:
            logger.info(f"Password reset requested for OAuth user: {email}")
            return  # OAuth users don't have passwords

        if not user.is_verified:
            logger.info(f"Password reset requested for unverified user: {email}")
            return  # Don't reveal if user is not verified

        # Generate password reset token
        token = await self.generate_verification_token(
            user.id, TokenType.PASSWORD_RESET
        )
        logger.info(f"Generated password reset token for user: {email}")

        # Send password reset email
        try:
            success = await self.email_service.send_password_reset_email(user.email, token.token)
            if success:
                logger.info(f"Password reset email sent successfully to: {email}")
            else:
                logger.error(f"Failed to send password reset email to: {email}")
        except Exception as e:
            # Log error but don't reveal to user for security
            logger.error(f"Error sending password reset email to {email}: {str(e)}", exc_info=True)
            raise  # Re-raise to allow caller to handle if needed

    async def reset_password(self, token: str, new_password: str) -> User:
        """
        Reset password using reset token.

        Args:
            token: Password reset token
            new_password: New password

        Returns:
            User object

        Raises:
            ValueError: If token is invalid, expired, or already used
        """
        if len(new_password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        # Find token
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token == token,
                VerificationToken.token_type == TokenType.PASSWORD_RESET,
            )
        )
        reset_token = result.scalar_one_or_none()

        if not reset_token:
            raise ValueError("Invalid password reset token")

        if reset_token.used_at:
            raise ValueError("Password reset token has already been used")

        # Check expiration
        expires_at = reset_token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            raise ValueError("Password reset token has expired")

        # Get user
        user = await self.get_user_by_id(reset_token.user_id)
        if not user:
            raise ValueError("User not found")

        if user.auth_provider != AuthProvider.EMAIL:
            raise ValueError("Password can only be reset for email-based users")

        # Update password and mark token as used
        user.password_hash = self._hash_password(new_password)
        user.updated_at = datetime.now(timezone.utc)
        reset_token.used_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(user)

        return user

