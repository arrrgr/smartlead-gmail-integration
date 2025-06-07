import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Gmail OAuth2 Credentials
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')
GMAIL_ACCOUNT = os.getenv('GMAIL_ACCOUNT', 'marketing@oversecured.com')

# OAuth2 Configuration
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Dynamic redirect URI based on environment
APP_URL = os.getenv('APP_URL', 'http://localhost:5000')
REDIRECT_URI = f'{APP_URL}/oauth2callback'

# Webhook Configuration
WEBHOOK_PORT = int(os.getenv('PORT', 5001))  # Use PORT env var for cloud platforms
WEBHOOK_SECRET_KEY = os.getenv('WEBHOOK_SECRET_KEY', '')

# Gmail Labels
LABEL_SENT = os.getenv('LABEL_SENT', 'Smartlead/Sent')
LABEL_REPLIES = os.getenv('LABEL_REPLIES', 'Smartlead/Replies')

# Token storage
TOKEN_FILE = 'token.json'

# Flask settings
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true' 