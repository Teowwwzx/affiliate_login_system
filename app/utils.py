from functools import wraps
import os
from flask import flash, redirect, url_for, abort, request, current_app
from flask_login import current_user
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
    print("Warning: RESEND_API_KEY environment variable not set. Email functionality will be disabled.")

def login_required(f):
    """Decorate routes to require login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(role_name):
    """Decorate routes to require a specific role."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role != role_name:
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

admin_required = role_required('admin')
leader_required = role_required('leader')

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
        email = resend.Emails.send(params)
        current_app.logger.info(f"Email sent successfully to {to}: {subject}")
        return email
    except Exception as e:
        current_app.logger.error(f"Error sending email to {to}: {e}")
        return None

# Example usage for direct testing
if __name__ == '__main__':
    if RESEND_API_KEY:
        print(f"Using Resend API Key: {RESEND_API_KEY[:5]}...{RESEND_API_KEY[-4:]}")
        print(f"Sending from email: {FROM_EMAIL}")
        test_to_email = "teowzx1@gmail.com"  # Change this to your test email
        test_subject = "Test Email from Affiliate System"
        test_html = "<h1>Hello!</h1><p>This is a test email sent via Resend.</p>"
        
        if test_to_email == "teowzx1@gmail.com":
            print("\nPlease update 'test_to_email' in utils.py to your actual email address to run the test.")
        else:
            print(f"Attempting to send test email to: {test_to_email}")
            response = send_email(test_to_email, test_subject, test_html)
            if response:
                print("Test email API call successful.")
            else:
                print("Test email API call failed.")
    else:
        print("RESEND_API_KEY is not set. Skipping test email.")