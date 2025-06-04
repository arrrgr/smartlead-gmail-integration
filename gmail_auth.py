import os
import json
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
        """Load credentials from token file if it exists"""
        if os.path.exists(config.TOKEN_FILE):
            try:
                self.creds = Credentials.from_authorized_user_file(config.TOKEN_FILE, config.SCOPES)
            except Exception as e:
                print(f"Error loading credentials: {e}")
                self.creds = None
        
        # Refresh token if expired
        if self.creds and self.creds.expired and self.creds.refresh_token:
            try:
                self.creds.refresh(Request())
                self.save_credentials()
            except Exception as e:
                print(f"Error refreshing token: {e}")
                self.creds = None
    
    def save_credentials(self):
        """Save credentials to token file"""
        if self.creds:
            with open(config.TOKEN_FILE, 'w') as token:
                token.write(self.creds.to_json())
    
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