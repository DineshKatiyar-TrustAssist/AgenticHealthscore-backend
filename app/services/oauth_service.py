from typing import Optional
from authlib.integrations.httpx_client import AsyncOAuth2Client
from app.services.app_config_service import AppConfigService


class OAuthService:
    """Service for OAuth authentication flows."""

    # OAuth provider configurations
    GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
    GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
    GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

    def __init__(self, db_session):
        """Initialize OAuth service with database session for config access."""
        self.db = db_session
        self.config_service = AppConfigService(db_session)

    async def _get_oauth_config(self, provider: str) -> Optional[dict]:
        """Get OAuth configuration for a provider from database."""
        if provider == "google":
            client_id = await self.config_service.get("GOOGLE_OAUTH_CLIENT_ID")
            client_secret = await self.config_service.get("GOOGLE_OAUTH_CLIENT_SECRET")

            if not client_id or not client_secret:
                return None

            return {
                "client_id": client_id,
                "client_secret": client_secret,
            }
        return None

    async def get_authorization_url(
        self, provider: str, redirect_uri: str, state: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate OAuth authorization URL.

        Args:
            provider: OAuth provider name (e.g., 'google')
            redirect_uri: Callback URL after authorization
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL, or None if provider not configured
        """
        if provider == "google":
            config = await self._get_oauth_config("google")
            if not config:
                return None

            client = AsyncOAuth2Client(
                client_id=config["client_id"],
                client_secret=config["client_secret"],
            )

            authorization_url, _ = client.create_authorization_url(
                self.GOOGLE_AUTHORIZE_URL,
                redirect_uri=redirect_uri,
                scope="openid email profile",
                state=state,
            )

            return authorization_url
        else:
            logger.warning(f"Unsupported OAuth provider: {provider}")
            return None

    async def handle_oauth_callback(
        self, provider: str, code: str, redirect_uri: str
    ) -> Optional[dict]:
        """Handle OAuth callback: exchange code for access token and fetch user info."""
        if provider == "google":
            config = await self._get_oauth_config("google")
            if not config:
                return None

            try:
                client = AsyncOAuth2Client(
                    client_id=config["client_id"],
                    client_secret=config["client_secret"],
                )

                token_response = await client.fetch_token(
                    self.GOOGLE_TOKEN_URL,
                    code=code,
                    redirect_uri=redirect_uri,
                )

                if not token_response or "access_token" not in token_response:
                    return None

                async with client:
                    userinfo_response = await client.get(
                        self.GOOGLE_USERINFO_URL,
                        token=token_response,
                    )

                    if userinfo_response.status_code != 200:
                        return None

                    userinfo = userinfo_response.json()
                    return {
                        "email": userinfo.get("email"),
                        "provider_id": userinfo.get("id"),
                        "name": userinfo.get("name"),
                        "picture": userinfo.get("picture"),
                        "verified_email": userinfo.get("verified_email", False),
                    }
            except Exception:
                return None
        return None

