"""
Script to set up SMTP configuration in the database.

Usage:
    python scripts/setup_smtp.py

You'll be prompted to enter SMTP settings.
For Gmail, you can use:
    Host: smtp.gmail.com
    Port: 587
    Use TLS: true
    User: your-email@gmail.com
    Password: your-app-password (not regular password)
    From Email: your-email@gmail.com
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import async_session_maker
from app.services.app_config_service import AppConfigService


async def setup_smtp():
    """Set up SMTP configuration interactively."""
    print("SMTP Configuration Setup")
    print("=" * 50)
    
    host = input("SMTP Host (e.g., smtp.gmail.com): ").strip()
    port = input("SMTP Port (e.g., 587 for TLS, 465 for SSL): ").strip()
    user = input("SMTP Username/Email: ").strip()
    password = input("SMTP Password/App Password: ").strip()
    from_email = input("From Email Address: ").strip()
    use_tls = input("Use TLS? (true/false) [true]: ").strip().lower() or "true"
    
    if not all([host, port, user, password, from_email]):
        print("Error: All fields are required!")
        return
    
    async with async_session_maker() as session:
        config_service = AppConfigService(session)
        
        await config_service.set("SMTP_HOST", host)
        await config_service.set("SMTP_PORT", port)
        await config_service.set("SMTP_USER", user)
        await config_service.set("SMTP_PASSWORD", password)
        await config_service.set("SMTP_FROM_EMAIL", from_email)
        await config_service.set("SMTP_USE_TLS", use_tls)
        
        print("\n✓ SMTP configuration saved successfully!")
        print("\nNote: For Gmail, you need to use an App Password, not your regular password.")
        print("Generate one at: https://myaccount.google.com/apppasswords")


if __name__ == "__main__":
    asyncio.run(setup_smtp())

