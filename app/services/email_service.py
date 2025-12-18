import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime
from jinja2 import Template
from app.services.app_config_service import AppConfigService
from app.config import settings


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(self, db_session):
        self.db = db_session
        self.config_service = AppConfigService(db_session)

    async def _get_smtp_config(self) -> Optional[dict]:
        """Get SMTP configuration from database."""
        host = await self.config_service.get("SMTP_HOST")
        port = await self.config_service.get("SMTP_PORT")
        user = await self.config_service.get("SMTP_USER")
        password = await self.config_service.get("SMTP_PASSWORD")
        from_email = await self.config_service.get("SMTP_FROM_EMAIL")
        use_tls = await self.config_service.get("SMTP_USE_TLS")

        if not all([host, port, user, password, from_email]):
            return None

        port_int = int(port)
        use_tls_bool = use_tls and use_tls.lower() == "true"
        
        # For port 587, use STARTTLS; for port 465, use SSL
        use_ssl = port_int == 465
        start_tls = port_int == 587 and use_tls_bool

        return {
            "host": host,
            "port": port_int,
            "user": user,
            "password": password,
            "from_email": from_email,
            "use_ssl": use_ssl,
            "start_tls": start_tls,
        }

    async def _send_email(
        self, to_email: str, subject: str, html_body: str, text_body: str
    ) -> bool:
        """Send an email via SMTP."""
        smtp_config = await self._get_smtp_config()
        if not smtp_config:
            raise ValueError("SMTP configuration not found. Please configure SMTP settings in the database.")

        try:
            message = MIMEMultipart("alternative")
            message["From"] = smtp_config["from_email"]
            message["To"] = to_email
            message["Subject"] = subject

            message.attach(MIMEText(text_body, "plain"))
            message.attach(MIMEText(html_body, "html"))

            # For port 587, use STARTTLS; for port 465, use SSL/TLS
            if smtp_config["use_ssl"]:
                # Port 465 - use SSL/TLS
                await aiosmtplib.send(
                    message,
                    hostname=smtp_config["host"],
                    port=smtp_config["port"],
                    username=smtp_config["user"],
                    password=smtp_config["password"],
                    use_tls=True,
                )
            else:
                # Port 587 - use STARTTLS
                await aiosmtplib.send(
                    message,
                    hostname=smtp_config["host"],
                    port=smtp_config["port"],
                    username=smtp_config["user"],
                    password=smtp_config["password"],
                    start_tls=smtp_config["start_tls"],
                )
            return True
        except Exception as e:
            raise ValueError(f"Failed to send email: {str(e)}")

    async def send_verification_email(self, user_email: str, token: str) -> bool:
        """
        Send email verification link to user.

        Args:
            user_email: User's email address
            token: Verification token

        Returns:
            True if email sent successfully, False otherwise
        """
        verification_url = f"{settings.FRONTEND_URL}/auth/verify?token={token}"

        html_template = Template("""
        <html>
          <body>
            <h2>Verify Your Email Address</h2>
            <p>Thank you for signing up! Please click the link below to verify your email address:</p>
            <p><a href="{{ verification_url }}">Verify Email</a></p>
            <p>Or copy and paste this link into your browser:</p>
            <p>{{ verification_url }}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't create an account, please ignore this email.</p>
          </body>
        </html>
        """)

        text_template = Template("""
        Verify Your Email Address

        Thank you for signing up! Please visit the link below to verify your email address:

        {{ verification_url }}

        This link will expire in 1 hour.

        If you didn't create an account, please ignore this email.
        """)

        html_body = html_template.render(verification_url=verification_url)
        text_body = text_template.render(verification_url=verification_url)

        return await self._send_email(
            user_email,
            "Verify Your Email Address",
            html_body,
            text_body,
        )

    async def send_notification_email(
        self, user_email: str, signup_timestamp: datetime, verification_status: str
    ) -> bool:
        """
        Send notification email to admin about new user signup.

        Args:
            user_email: New user's email address
            signup_timestamp: When the user signed up
            verification_status: Current verification status ('pending' or 'verified')

        Returns:
            True if email sent successfully, False otherwise
        """
        admin_email = settings.ADMIN_NOTIFICATION_EMAIL

        html_template = Template("""
        <html>
          <body>
            <h2>New User Signup</h2>
            <p>A new user has signed up for the application:</p>
            <ul>
              <li><strong>Email:</strong> {{ user_email }}</li>
              <li><strong>Signup Time:</strong> {{ signup_time }}</li>
              <li><strong>Verification Status:</strong> {{ verification_status }}</li>
            </ul>
          </body>
        </html>
        """)

        text_template = Template("""
        New User Signup

        A new user has signed up for the application:

        Email: {{ user_email }}
        Signup Time: {{ signup_time }}
        Verification Status: {{ verification_status }}
        """)

        html_body = html_template.render(
            user_email=user_email,
            signup_time=signup_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            verification_status=verification_status,
        )
        text_body = text_template.render(
            user_email=user_email,
            signup_time=signup_timestamp.strftime("%Y-%m-%d %H:%M:%S UTC"),
            verification_status=verification_status,
        )

        return await self._send_email(
            admin_email,
            f"New User Signup: {user_email}",
            html_body,
            text_body,
        )

