import os
import json
import base64
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import config

class GmailAuth:
    def __init__(self):
        self.creds = None
        self.service = None
        self.load_credentials()
    
    def load_credentials(self):
        """Load credentials from environment variable or token file"""
        # First, try to load from environment variable (for Railway)
        token_env = os.environ.get('GMAIL_TOKEN_JSON')
        if token_env:
            try:
                # Decode from base64 if stored as base64
                try:
                    token_data = base64.b64decode(token_env).decode('utf-8')
                    token_dict = json.loads(token_data)
                except:
                    # If not base64, try direct JSON
                    token_dict = json.loads(token_env)
                
                # Create credentials from the token data
                self.creds = Credentials.from_authorized_user_info(token_dict, config.SCOPES)
                print("Loaded credentials from environment variable")
            except Exception as e:
                print(f"Error loading credentials from env: {e}")
                self.creds = None
        
        # Fall back to token file if no env var
        elif os.path.exists(config.TOKEN_FILE):
            try:
                self.creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
                print("Loaded credentials from token file")
            except Exception as e:
                print(f"Error loading credentials from file: {e}")
                self.creds = None
        
        # Refresh token if expired
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.save_credentials()
                print("Refreshed expired token")
            except Exception as e:
                print(f"Error refreshing token: {e}")
                self.creds = None
    
    def save_credentials(self):
        """Save credentials to token file and print env var instructions"""
        if self.creds:
            # Save to file
            with open(config.TOKEN_FILE, 'w') as token:
                token.write(self.creds.to_json())
            
            # Also print instructions for setting env var
            token_json = self.creds.to_json()
            token_base64 = base64.b64encode(token_json.encode()).decode()
            
            print("\n" + "="*60)
            print("TOKEN SAVED! To use in Railway, set this environment variable:")
            print("="*60)
            print(f"GMAIL_TOKEN_JSON={token_base64}")
            print("="*60 + "\n")
    
    def get_auth_url(self):
        """Generate OAuth2 authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [config.REDIRECT_URI]
                }
            },
            scopes=config.SCOPES
        )
        flow.redirect_uri = config.REDIRECT_URI
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        return auth_url
    
    def handle_callback(self, authorization_code):
        """Handle OAuth2 callback and exchange code for tokens"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": config.GOOGLE_CLIENT_ID,
                    "client_secret": config.GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [config.REDIRECT_URI]
                }
            },
            scopes=config.SCOPES
        )
        flow.redirect_uri = config.REDIRECT_URI
        
        # Exchange authorization code for tokens
        flow.fetch_token(code=authorization_code)
        self.creds = flow.credentials
        self.save_credentials()
        return True
    
    def get_gmail_service(self):
        """Get authenticated Gmail service instance"""
        if not self.creds or not self.creds.valid:
            return None
        
        if not self.service:
            self.service = build('gmail', 'v1', credentials=self.creds)
        
        return self.service
    
    def is_authenticated(self):
        """Check if user is authenticated"""
        return self.creds is not None and self.creds.valid 