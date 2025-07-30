import smtplib
import ssl
from email.mime.text import MIMEText
from email.header import Header
from email.utils import formataddr
from typing import Dict, Any

from eduauth.config import settings

async def send_email(to_email: str, subject: str, body: str, is_html: bool = False) -> Dict[str, Any]:
    """
    Sends an email using the configured SMTP server.

    Args:
        to_email (str): The recipient's email address.
        subject (str): The subject line of the email.
        body (str): The content of the email (can be plain text or HTML).
        is_html (bool): If True, the body is treated as HTML.

    Returns:
        Dict[str, Any]: A dictionary indicating success or failure.
    """
    try:
        # Create a MIMEText object for the email message
        msg = MIMEText(body, 'html' if is_html else 'plain', 'utf-8')
        # Set the sender's name and address
        msg['From'] = formataddr((str(Header(settings.EMAIL_FROM_NAME, 'utf-8')), settings.EMAIL_FROM_ADDRESS))
        msg['To'] = to_email
        msg['Subject'] = Header(subject, 'utf-8')

        # Create a secure SSL context
        context = ssl.create_default_context()

        # Connect to the SMTP server and send the email
        # Use 'with' statement to ensure the connection is properly closed
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.ehlo() # Can be omitted
            server.starttls(context=context) # Secure the connection
            server.ehlo() # Can be omitted
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD) # Log in to the SMTP server
            server.sendmail(settings.EMAIL_FROM_ADDRESS, to_email, msg.as_string()) # Send the email

        return {"status": "success", "message": "Email sent successfully."}
    except smtplib.SMTPAuthenticationError:
        print(f"SMTP Authentication Error: Check SMTP_USER and SMTP_PASSWORD in .env")
        return {"status": "error", "message": "SMTP authentication failed."}
    except smtplib.SMTPConnectError:
        print(f"SMTP Connection Error: Could not connect to {settings.SMTP_SERVER}:{settings.SMTP_PORT}")
        return {"status": "error", "message": "Could not connect to SMTP server."}
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        return {"status": "error", "message": f"Failed to send email: {e}"}

# Example usage (for testing, not part of the main application flow)
# async def test_email_sending():
#     result = await send_email(
#         to_email="test@example.com",
#         subject="Test EduAuth Email",
#         body="This is a test email from EduAuth.",
#         is_html=False
#     )
#     print(result)

# If you want to run the test, uncomment the following lines and run this file directly:
# import asyncio
# if __name__ == "__main__":
#     asyncio.run(test_email_sending())
