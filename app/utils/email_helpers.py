# app/utils/email_helpers.py
import os
from flask import current_app
import resend
from dotenv import load_dotenv

# Load environment variables from .env file (if it exists)
load_dotenv()

# Email Configuration
RESEND_API_KEY = os.getenv('RESEND_API_KEY')
FROM_EMAIL = os.getenv('FROM_EMAIL', 'noreply@rniaffiliate.com')  # Default to your domain

# Initialize Resend API
if RESEND_API_KEY:
    resend.api_key = RESEND_API_KEY
else:
    # Use print for initial setup, logger might not be configured yet if this module is imported early
    print("Warning: RESEND_API_KEY environment variable not set. Email functionality will be disabled.")

def send_email(to: str, subject: str, html_content: str):
    """
    Sends an email using the Resend API.

    Args:
        to (str): The recipient's email address.
        subject (str): The subject of the email.
        html_content (str): The HTML content of the email.

    Returns:
        dict: The response from the Resend API, or None if API key is missing or an error occurs.
    """
    if not RESEND_API_KEY:
        current_app.logger.error("Resend API key is not configured. Cannot send email.")
        return None

    try:
        params = {
            "from": FROM_EMAIL,
            "to": to,
            "subject": subject,
            "html": html_content,
        }
        email_response = resend.Emails.send(params)
        current_app.logger.info(f"Email sent successfully to {to}: {subject}")
        return email_response
    except Exception as e:
        current_app.logger.error(f"Error sending email to {to}: {e}", exc_info=True)
        return None
