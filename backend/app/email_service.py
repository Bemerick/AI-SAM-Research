"""
Email service for sending opportunity sharing emails.
Uses Microsoft Graph API to send emails via Office 365.
"""
import os
import requests
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

# Microsoft Graph API configuration
MS_TENANT_ID = os.getenv('MS_TENANT_ID', '')
MS_CLIENT_ID = os.getenv('MS_CLIENT_ID', '')
MS_CLIENT_SECRET = os.getenv('MS_CLIENT_SECRET', '')
EMAIL_FROM_ADDRESS = os.getenv('EMAIL_FROM_ADDRESS', '')
EMAIL_FROM_NAME = os.getenv('EMAIL_FROM_NAME', 'SAM Opportunity System')


class EmailService:
    """Service for sending emails via Microsoft Graph API."""

    @staticmethod
    def _get_access_token() -> Optional[str]:
        """
        Get access token for Microsoft Graph API using client credentials flow.

        Returns:
            Access token or None if authentication fails
        """
        if not all([MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET]):
            logger.error("Microsoft Graph credentials not configured. Set MS_TENANT_ID, MS_CLIENT_ID, MS_CLIENT_SECRET")
            return None

        try:
            token_url = f"https://login.microsoftonline.com/{MS_TENANT_ID}/oauth2/v2.0/token"

            data = {
                'grant_type': 'client_credentials',
                'client_id': MS_CLIENT_ID,
                'client_secret': MS_CLIENT_SECRET,
                'scope': 'https://graph.microsoft.com/.default'
            }

            response = requests.post(token_url, data=data)
            response.raise_for_status()

            return response.json().get('access_token')

        except Exception as e:
            logger.error(f"Failed to get Microsoft Graph access token: {e}")
            return None

    @staticmethod
    def send_opportunity_share_email(
        to_emails: List[str],
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
        from_name: Optional[str] = None
    ) -> bool:
        """
        Send an opportunity sharing email via Microsoft Graph API.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            html_body: HTML email body
            from_email: Sender email (defaults to EMAIL_FROM_ADDRESS)
            from_name: Sender name (defaults to EMAIL_FROM_NAME)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not to_emails:
            logger.error("No recipient email addresses provided")
            return False

        from_email = from_email or EMAIL_FROM_ADDRESS
        from_name = from_name or EMAIL_FROM_NAME

        if not from_email:
            logger.error("No sender email configured. Set EMAIL_FROM_ADDRESS")
            return False

        # Get access token
        access_token = EmailService._get_access_token()
        if not access_token:
            return False

        try:
            # Build message payload for Graph API
            message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_body
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": email
                            }
                        } for email in to_emails
                    ]
                },
                "saveToSentItems": "true"
            }

            # Send email via Graph API
            # Using /users/{user-id}/sendMail endpoint
            graph_url = f"https://graph.microsoft.com/v1.0/users/{from_email}/sendMail"

            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }

            response = requests.post(graph_url, json=message, headers=headers)
            response.raise_for_status()

            logger.info(f"Email sent successfully via Microsoft Graph API to {', '.join(to_emails)}")
            return True

        except requests.exceptions.HTTPError as e:
            logger.error(f"Failed to send email via Microsoft Graph API: {e}")
            logger.error(f"Response: {e.response.text if e.response else 'No response'}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email via Microsoft Graph API: {e}")
            return False


def format_opportunity_email_html(
    opportunity: dict,
    detail_url: str,
    sender_name: Optional[str] = None
) -> str:
    """
    Format opportunity data as HTML email.

    Args:
        opportunity: Opportunity data dictionary
        detail_url: Full URL to the opportunity detail page
        sender_name: Optional name of the person sharing

    Returns:
        HTML email body
    """
    from datetime import datetime

    def format_date(date_str):
        """Format date string."""
        if not date_str:
            return 'N/A'
        try:
            dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return dt.strftime('%b %d, %Y')
        except:
            return date_str

    title = opportunity.get('title', 'Untitled')
    notice_id = opportunity.get('notice_id', 'N/A')
    fit_score = opportunity.get('fit_score')
    department = opportunity.get('department', 'N/A')
    solicitation_number = opportunity.get('solicitation_number')
    naics_code = opportunity.get('naics_code', 'N/A')
    practice_area = opportunity.get('assigned_practice_area')
    posted_date = format_date(opportunity.get('posted_date'))
    response_deadline = format_date(opportunity.get('response_deadline'))
    set_aside = opportunity.get('set_aside')
    ptype = opportunity.get('ptype')
    city = opportunity.get('place_of_performance_city')
    state = opportunity.get('place_of_performance_state')
    summary = opportunity.get('summary_description')
    sam_link = opportunity.get('sam_link')

    place = ', '.join(filter(None, [city, state])) if city or state else None

    html = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: 0 auto; background-color: #f9fafb; }}
    .header {{ background-color: #2563eb; color: white; padding: 20px; text-align: center; }}
    .header h1 {{ margin: 0; font-size: 24px; }}
    .container {{ padding: 20px; }}
    .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 8px; padding: 20px; margin: 20px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
    .info-grid {{ margin-top: 15px; }}
    .info-item {{ margin-bottom: 15px; }}
    .info-label {{ font-weight: bold; color: #6b7280; font-size: 14px; }}
    .info-value {{ color: #111827; margin-top: 5px; }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 12px; font-size: 14px; font-weight: 600; background-color: #dbeafe; color: #1e40af; }}
    .summary {{ background-color: #eff6ff; border-left: 4px solid #2563eb; padding: 15px; margin: 15px 0; border-radius: 4px; }}
    .btn {{ display: inline-block; background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; margin: 10px 10px 10px 0; }}
    .footer {{ text-align: center; color: #6b7280; font-size: 12px; margin-top: 30px; padding: 20px; border-top: 1px solid #e5e7eb; }}
    .sender-note {{ background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 12px; margin: 15px 0; border-radius: 4px; font-size: 14px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>SAM.gov Opportunity</h1>
  </div>

  <div class="container">
    {f'<div class="sender-note"><strong>{sender_name}</strong> shared this opportunity with you.</div>' if sender_name else ''}

    <div class="card">
      <h2 style="margin-top: 0; color: #111827;">{title}</h2>
      <p style="color: #6b7280;">Notice ID: {notice_id}</p>

      {f'<div style="margin: 15px 0;"><span class="badge">Fit Score: {fit_score}/10</span></div>' if fit_score else ''}

      <div class="info-grid">
        <div class="info-item">
          <div class="info-label">Department</div>
          <div class="info-value">{department}</div>
        </div>

        {f'<div class="info-item"><div class="info-label">Solicitation Number</div><div class="info-value">{solicitation_number}</div></div>' if solicitation_number else ''}

        <div class="info-item">
          <div class="info-label">NAICS Code</div>
          <div class="info-value">{naics_code}</div>
        </div>

        {f'<div class="info-item"><div class="info-label">Practice Area</div><div class="info-value">{practice_area}</div></div>' if practice_area else ''}

        <div class="info-item">
          <div class="info-label">Posted Date</div>
          <div class="info-value">{posted_date}</div>
        </div>

        <div class="info-item">
          <div class="info-label">Response Deadline</div>
          <div class="info-value">{response_deadline}</div>
        </div>

        {f'<div class="info-item"><div class="info-label">Set Aside</div><div class="info-value">{set_aside}</div></div>' if set_aside else ''}

        {f'<div class="info-item"><div class="info-label">Type</div><div class="info-value">{ptype}</div></div>' if ptype else ''}

        {f'<div class="info-item"><div class="info-label">Place of Performance</div><div class="info-value">{place}</div></div>' if place else ''}
      </div>

      {f'<div class="summary"><strong style="color: #1e40af;">Summary:</strong><p style="margin: 10px 0 0 0;">{summary}</p></div>' if summary else ''}

      <div style="margin-top: 25px;">
        {f'<a href="{sam_link}" class="btn">View on SAM.gov</a>' if sam_link else ''}
        <a href="{detail_url}" class="btn">View Full Details</a>
      </div>
    </div>

    <div class="footer">
      <p>This opportunity was shared from the SAM Opportunity Management System</p>
    </div>
  </div>
</body>
</html>
""".strip()

    return html
