import secrets
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_db, get_current_active_user
from app.services.auth_service import AuthService
from app.services.oauth_service import OAuthService
from app.models.user import User, AuthProvider
from app.models.verification_token import TokenType
from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
    SetPasswordRequest,
    SetPasswordResponse,
    LoginRequest,
    LoginResponse,
    UserResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    ResetPasswordRequest,
    ResetPasswordResponse,
)
from app.utils.jwt import create_access_token
from app.config import settings

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: SignupRequest,
    db: AsyncSession = Depends(get_db),
):
    """Sign up a new user with email."""
    auth_service = AuthService(db)
    try:
        user, _ = await auth_service.create_user(
            request.email, auth_provider=AuthProvider.EMAIL
        )
        return SignupResponse(
            message="Signup successful. Please check your email to verify your account.",
            email=user.email,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)
        )


@router.get("/verify", response_model=VerifyEmailResponse)
async def verify_email(
    token: str = Query(..., description="Verification token from email"),
    db: AsyncSession = Depends(get_db),
):
    """Verify email address using token from verification email."""
    auth_service = AuthService(db)
    await auth_service.verify_email_token(token)
    redirect_url = f"{settings.FRONTEND_URL}/auth/set-password?token={token}"
    return VerifyEmailResponse(
        message="Email verified successfully. You can now set your password.",
        redirect_url=redirect_url,
    )


@router.post("/set-password", response_model=SetPasswordResponse)
async def set_password(
    request: SetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Set password for a user after email verification."""
    if not request.token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token required",
        )

    from app.models.verification_token import VerificationToken
    from sqlalchemy import select
    from datetime import datetime, timezone

    result = await db.execute(
        select(VerificationToken).where(
            VerificationToken.token == request.token,
            VerificationToken.token_type == TokenType.EMAIL_VERIFICATION,
        )
    )
    verification_token = result.scalar_one_or_none()

    if not verification_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token",
        )

    # Ensure timezone-aware comparison
    expires_at = verification_token.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )

    # Check if user is verified (token may have been used for verification)
    user_result = await db.execute(
        select(User).where(User.id == verification_token.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found",
        )
    
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not verified. Please verify your email first.",
        )

    # Mark token as used if not already used
    if not verification_token.used_at:
        verification_token.used_at = datetime.now(timezone.utc)
        await db.commit()

    auth_service = AuthService(db)
    await auth_service.set_password(verification_token.user_id, request.password)

    return SetPasswordResponse(
        message="Password set successfully. You can now log in."
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT token."""
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(request.email, request.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})

    from app.schemas.auth import UserInfo

    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserInfo(
            id=user.id,
            email=user.email,
            auth_provider=user.auth_provider.value,
            is_verified=user.is_verified,
            is_active=user.is_active,
            created_at=user.created_at,
        ),
    )


@router.get("/oauth/{provider}")
async def oauth_initiate(
    provider: str,
    db: AsyncSession = Depends(get_db),
):
    """Initiate OAuth flow for a provider (e.g., Google)."""
    oauth_service = OAuthService(db)
    state = secrets.token_urlsafe(32)
    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/oauth/{provider}/callback"

    authorization_url = await oauth_service.get_authorization_url(
        provider, redirect_uri, state=state
    )

    if not authorization_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth provider '{provider}' not configured",
        )

    return RedirectResponse(url=authorization_url)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="Authorization code from OAuth provider"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: AsyncSession = Depends(get_db),
):
    """OAuth callback endpoint."""
    oauth_service = OAuthService(db)
    auth_service = AuthService(db)

    redirect_uri = f"{settings.BACKEND_URL}/api/v1/auth/oauth/{provider}/callback"
    user_info = await oauth_service.handle_oauth_callback(provider, code, redirect_uri)

    if not user_info or not user_info.get("email"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to authenticate with OAuth provider",
        )

    provider_map = {"google": AuthProvider.GOOGLE}
    auth_provider = provider_map.get(provider)

    if not auth_provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OAuth provider: {provider}",
        )

    user = await auth_service.create_or_update_oauth_user(
        email=user_info["email"],
        provider=auth_provider,
        provider_id=user_info["provider_id"],
        provider_data=user_info,
    )

    access_token = create_access_token(data={"sub": user.id, "email": user.email})
    frontend_url = f"{settings.FRONTEND_URL}/auth/oauth/callback?token={access_token}&provider={provider}"

    return RedirectResponse(url=frontend_url)


@router.post("/password-reset/request", response_model=PasswordResetResponse)
async def request_password_reset(
    request: PasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request password reset email."""
    auth_service = AuthService(db)
    try:
        await auth_service.request_password_reset(request.email)
        return PasswordResetResponse(
            message="If the email exists and is verified, a password reset link has been sent."
        )
    except Exception:
        # Don't reveal if user exists for security
        return PasswordResetResponse(
            message="If the email exists and is verified, a password reset link has been sent."
        )


@router.post("/password-reset/reset", response_model=ResetPasswordResponse)
async def reset_password(
    request: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """Reset password using reset token."""
    auth_service = AuthService(db)
    try:
        await auth_service.reset_password(request.token, request.password)
        return ResetPasswordResponse(
            message="Password reset successfully. You can now log in with your new password."
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user information."""
    from app.schemas.auth import UserInfo

    return UserResponse(
        user=UserInfo(
            id=current_user.id,
            email=current_user.email,
            auth_provider=current_user.auth_provider.value,
            is_verified=current_user.is_verified,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
        )
    )

