# Smartlead Gmail Integration

This integration receives webhooks from Smartlead, converts email messages to MBOX format, and uploads them to a Gmail account.

## 🚀 Quick Deploy

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/template/deploy?template=https://github.com/yourusername/smartlead-gmail-integration)

After deploying, set these environment variables in Railway:
- `APP_URL`: Your Railway app URL (e.g., https://your-app.railway.app)
- `WEBHOOK_SECRET_KEY`: Your Smartlead webhook secret key

## Features

- Receives webhooks for sent emails and replies from Smartlead
- Converts email data to proper MBOX format with all headers
- Uploads emails to Gmail with appropriate labels
- Preserves email threading for conversations
- OAuth2 authentication with Gmail
- Web interface for authentication and status monitoring

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure OAuth2 Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Gmail API
4. Create OAuth2 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:5000/oauth2callback`
6. Download credentials and note:
   - Client ID: `YOUR_GOOGLE_CLIENT_ID`
   - Client Secret: `YOUR_GOOGLE_CLIENT_SECRET`

### 3. Set Smartlead Secret Key (Optional)

Edit `config.py` and set your Smartlead webhook secret key:
```python
WEBHOOK_SECRET_KEY = os.getenv('WEBHOOK_SECRET_KEY', 'your_actual_secret_key')
```

### 4. Run the Application

```bash
python app.py
```

The application will start on port 5000 by default.

### 5. Authenticate with Gmail

1. Open your browser and go to `http://localhost:5000`
2. Click "Authenticate with Gmail"
3. Log in with the Gmail account (`marketing@oversecured.com`)
4. Grant the necessary permissions
5. You'll be redirected back to the application

### 6. Configure Smartlead Webhook

In your Smartlead account, set up webhooks to point to:
- URL: `http://your-server-address:5000/webhook`
- Events: EMAIL_SENT, EMAIL_REPLY

## How It Works

1. **Webhook Reception**: The Flask server receives webhooks at `/webhook`
2. **Data Conversion**: Email data is converted to MBOX format with proper headers
3. **Gmail Upload**: Messages are uploaded to Gmail using the Gmail API
4. **Label Organization**: 
   - Sent emails are labeled with `Smartlead/Sent`
   - Reply emails are labeled with `Smartlead/Replies`

## Email Threading

The integration preserves email threading by:
- Using the original Message-ID headers
- Setting In-Reply-To and References headers for replies
- Gmail automatically groups related messages into conversations

## API Endpoints

- `GET /` - Authentication status and dashboard
- `GET /oauth2callback` - OAuth2 callback handler
- `POST /webhook` - Webhook receiver for Smartlead events
- `GET /health` - Health check endpoint

## Webhook Response

Successful webhook processing returns:
```json
{
    "success": true,
    "gmail_message_id": "...",
    "gmail_thread_id": "..."
}
```

## Deployment Notes

For production deployment:

1. Use a proper web server (e.g., Gunicorn, uWSGI)
2. Set up HTTPS with a valid SSL certificate
3. Use a reverse proxy (e.g., Nginx)
4. Store tokens securely
5. Set proper environment variables
6. Update the redirect URI in Google Cloud Console if needed

## Troubleshooting

1. **Authentication Issues**: Delete `token.json` and re-authenticate
2. **Webhook Failures**: Check the logs for detailed error messages
3. **Label Creation**: Ensure the Gmail account has permission to create labels
4. **Rate Limits**: Gmail API has quotas - monitor usage in Google Cloud Console

## Security Considerations

- The OAuth2 credentials are embedded in the code for convenience
- In production, use environment variables for sensitive data
- Validate webhook signatures using the secret key
- Use HTTPS for all endpoints
- Regularly rotate tokens and credentials 