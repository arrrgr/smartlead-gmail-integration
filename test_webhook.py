import requests
import json
from datetime import datetime

# Configuration
WEBHOOK_URL = 'https://web-production-3fc01.up.railway.app/webhook'  # Your webhook endpoint
SECRET_KEY = ''  # Your Smartlead secret key (if configured)

# Sample EMAIL_SENT webhook
email_sent_payload = {
    "webhook_id": 100,
    "webhook_name": "Test Webhook",
    "sl_email_lead_id": "lead123",
    "sl_email_lead_map_id": "map123",
    "webhook_url": WEBHOOK_URL,
    "stats_id": "stats123",
    "event_type": "EMAIL_SENT",
    "event_timestamp": datetime.now().isoformat() + "Z",
    "from_email": "marketing@oversecured.com",
    "to_email": "test@example.com",
    "to_name": "Test User",
    "subject": "Test Email from Smartlead Integration",
    "campaign_id": 111,
    "campaign_name": "Test Campaign",
    "campaign_status": "ACTIVE",
    "sequence_number": 1,
    "sent_message": {
        "message_id": f"<test-{datetime.now().timestamp()}@oversecured.com>",
        "html": "<html><body><h1>Test Email</h1><p>This is a test email from the Smartlead integration.</p></body></html>",
        "text": "Test Email\n\nThis is a test email from the Smartlead integration.",
        "time": datetime.now().isoformat() + "Z"
    },
    "client_id": 111,
    "app_url": "https://app.smartlead.ai/app/master-inbox",
    "secret_key": SECRET_KEY,
    "description": "Test email sent",
    "metadata": {
        "webhook_created_at": datetime.now().isoformat() + "Z"
    }
}

# Sample EMAIL_REPLY webhook
email_reply_payload = {
    "webhook_id": 101,
    "webhook_name": "Test Webhook",
    "sl_email_lead_id": "lead123",
    "sl_email_lead_map_id": "map123",
    "sl_lead_email": "test@example.com",
    "webhook_url": WEBHOOK_URL,
    "stats_id": "stats124",
    "event_type": "EMAIL_REPLY",
    "event_timestamp": datetime.now().isoformat() + "Z",
    "from_email": "marketing@oversecured.com",
    "to_email": "test@example.com",
    "to_name": "Test User",
    "subject": "Re: Test Email from Smartlead Integration",
    "campaign_id": 111,
    "campaign_name": "Test Campaign",
    "campaign_status": "ACTIVE",
    "sequence_number": 1,
    "sent_message": {
        "message_id": f"<test-{datetime.now().timestamp()}@oversecured.com>",
        "html": "<html><body><h1>Test Email</h1><p>This is a test email from the Smartlead integration.</p></body></html>",
        "text": "Test Email\n\nThis is a test email from the Smartlead integration.",
        "time": datetime.now().isoformat() + "Z"
    },
    "reply_message": {
        "message_id": f"<reply-{datetime.now().timestamp()}@example.com>",
        "html": "<html><body><p>Thanks for your email! This is a test reply.</p></body></html>",
        "text": "Thanks for your email! This is a test reply.",
        "time": datetime.now().isoformat() + "Z"
    },
    "reply_category": "positive",
    "client_id": 111,
    "app_url": "https://app.smartlead.ai/app/master-inbox",
    "secret_key": SECRET_KEY,
    "description": "Test reply received",
    "metadata": {
        "webhook_created_at": datetime.now().isoformat() + "Z"
    }
}

def test_email_sent():
    """Test EMAIL_SENT webhook"""
    print("Testing EMAIL_SENT webhook...")
    response = requests.post(WEBHOOK_URL, json=email_sent_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)
    return response

def test_email_reply():
    """Test EMAIL_REPLY webhook"""
    print("Testing EMAIL_REPLY webhook...")
    response = requests.post(WEBHOOK_URL, json=email_reply_payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    print("-" * 50)
    return response

if __name__ == "__main__":
    print("Smartlead Webhook Tester")
    print("=" * 50)
    print(f"Testing webhook endpoint: {WEBHOOK_URL}")
    print("Make sure the Flask app is running and authenticated with Gmail!")
    print("=" * 50)
    
    input("Press Enter to send EMAIL_SENT webhook...")
    test_email_sent()
    
    input("Press Enter to send EMAIL_REPLY webhook...")
    test_email_reply()
    
    print("\nTest complete! Check your Gmail account for the uploaded messages.") 