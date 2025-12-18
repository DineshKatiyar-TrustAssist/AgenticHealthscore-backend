from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class SignupRequest(BaseModel):
    """Schema for user signup request."""

    email: EmailStr = Field(..., description="User's email address")


class SignupResponse(BaseModel):
    """Schema for user signup response."""

    message: str
    email: str


class VerifyEmailRequest(BaseModel):
    """Schema for email verification request."""

    token: str = Field(..., description="Verification token from email link")


class VerifyEmailResponse(BaseModel):
    """Schema for email verification response."""

    message: str
    redirect_url: str


class SetPasswordRequest(BaseModel):
    """Schema for setting password request."""

    password: str = Field(..., min_length=8, description="Password (minimum 8 characters)")
    token: Optional[str] = Field(
        None, description="Verification token (if setting password after email verification)"
    )


class SetPasswordResponse(BaseModel):
    """Schema for setting password response."""

    message: str


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str


class UserInfo(BaseModel):
    """Schema for user information in responses."""

    id: str
    email: str
    auth_provider: str
    is_verified: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    """Schema for login response."""

    access_token: str
    token_type: str = "bearer"
    user: UserInfo


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """Schema for current user response."""

    user: UserInfo


class PasswordResetRequest(BaseModel):
    """Schema for password reset request."""

    email: EmailStr = Field(..., description="User's email address")


class PasswordResetResponse(BaseModel):
    """Schema for password reset request response."""

    message: str


class ResetPasswordRequest(BaseModel):
    """Schema for resetting password with token."""

    token: str = Field(..., description="Password reset token from email")
    password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class ResetPasswordResponse(BaseModel):
    """Schema for reset password response."""

    message: str

