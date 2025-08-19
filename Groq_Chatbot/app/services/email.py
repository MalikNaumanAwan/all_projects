import os
from email.message import EmailMessage
import aiosmtplib
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")


async def send_verification_email(email: str, token: str):
    """Send a verification email using Gmail SMTP."""
    link = f"http://192.168.100.4:2022/verify?token={token}"

    message = EmailMessage()
    message["From"] = GMAIL_USER
    message["To"] = email
    message["Subject"] = "hi its Nauman. Testing API"
    message.set_content(
        f"Hello,\n\nPlease click the link below to verify your email:\n{link}\n\nThanks!"
    )

    try:
        await aiosmtplib.send(
            message,
            hostname="smtp.gmail.com",
            port=587,
            start_tls=True,
            username=GMAIL_USER,
            password=GMAIL_PASSWORD,
        )
        print(f"✅ Verification email sent to {email}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
