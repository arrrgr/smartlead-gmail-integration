from flask import Flask, request, jsonify, redirect, render_template_string
import json
import logging
from gmail_auth import GmailAuth
from mbox_converter import MboxConverter
from gmail_uploader import GmailUploader
import config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # Change this in production

# Initialize Gmail authentication
gmail_auth = GmailAuth()

# HTML template for auth page
AUTH_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smartlead Gmail Integration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .status {
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            text-align: center;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background-color: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .button {
            display: inline-block;
            padding: 10px 20px;
            background-color: #007bff;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 10px 0;
        }
        .button:hover {
            background-color: #0056b3;
        }
        .details {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            font-family: monospace;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Smartlead Gmail Integration</h1>
        {{ content | safe }}
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    """Home page with authentication status"""
    if gmail_auth.is_authenticated():
        webhook_url = f"{config.APP_URL}/webhook"
        content = '''
        <div class="status success">
            <h2>✓ Authenticated</h2>
            <p>Gmail integration is active for: <strong>{}</strong></p>
        </div>
        <div class="details">
            <h3>Webhook Endpoint:</h3>
            <p>{}</p>
            <h3>Configuration:</h3>
            <ul>
                <li>Sent emails label: {}</li>
                <li>Reply emails label: {}</li>
            </ul>
        </div>
        '''.format(config.GMAIL_ACCOUNT, webhook_url, config.LABEL_SENT, config.LABEL_REPLIES)
    else:
        auth_url = gmail_auth.get_auth_url()
        content = '''
        <div class="status info">
            <h2>Authentication Required</h2>
            <p>Please authenticate with Gmail to enable the integration.</p>
            <a href="{}" class="button">Authenticate with Gmail</a>
        </div>
        '''.format(auth_url)
    
    return render_template_string(AUTH_TEMPLATE, content=content)

@app.route('/oauth2callback')
def oauth2callback():
    """Handle OAuth2 callback from Google"""
    code = request.args.get('code')
    if not code:
        content = '''
        <div class="status error">
            <h2>Authentication Failed</h2>
            <p>No authorization code received.</p>
            <a href="/" class="button">Try Again</a>
        </div>
        '''
        return render_template_string(AUTH_TEMPLATE, content=content)
    
    try:
        gmail_auth.handle_callback(code)
        content = '''
        <div class="status success">
            <h2>✓ Authentication Successful!</h2>
            <p>Gmail integration is now active.</p>
            <a href="/" class="button">Go to Dashboard</a>
        </div>
        '''
    except Exception as e:
        content = '''
        <div class="status error">
            <h2>Authentication Failed</h2>
            <p>Error: {}</p>
            <a href="/" class="button">Try Again</a>
        </div>
        '''.format(str(e))
    
    return render_template_string(AUTH_TEMPLATE, content=content)

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhooks from Smartlead"""
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        # Log the webhook
        logger.info(f"Received webhook: {webhook_data.get('event_type', 'Unknown')}")
        
        # Verify secret key if configured
        if config.WEBHOOK_SECRET_KEY:
            provided_secret = webhook_data.get('secret_key', '')
            if provided_secret != config.WEBHOOK_SECRET_KEY:
                logger.warning("Invalid secret key in webhook")
                return jsonify({'error': 'Invalid secret key'}), 401
        
        # Check if authenticated
        if not gmail_auth.is_authenticated():
            logger.error("Gmail not authenticated")
            return jsonify({'error': 'Gmail not authenticated'}), 503
        
        # Get Gmail service
        gmail_service = gmail_auth.get_gmail_service()
        if not gmail_service:
            logger.error("Could not get Gmail service")
            return jsonify({'error': 'Gmail service unavailable'}), 503
        
        # Convert to email message
        email_message = MboxConverter.create_email_message(webhook_data)
        raw_message = MboxConverter.message_to_raw(email_message)
        
        # Upload to Gmail
        uploader = GmailUploader(gmail_service)
        result = uploader.upload_message(raw_message, webhook_data.get('event_type'))
        
        if result['success']:
            logger.info(f"Successfully uploaded message: {result['message_id']}")
            return jsonify({
                'success': True,
                'gmail_message_id': result['message_id'],
                'gmail_thread_id': result.get('thread_id')
            }), 200
        else:
            logger.error(f"Failed to upload message: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error')
            }), 500
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'authenticated': gmail_auth.is_authenticated()
    })

if __name__ == '__main__':
    print(f"Starting Smartlead Gmail Integration on port {config.WEBHOOK_PORT}")
    print(f"Visit {config.APP_URL} to authenticate")
    app.run(host='0.0.0.0', port=config.WEBHOOK_PORT, debug=config.DEBUG) 