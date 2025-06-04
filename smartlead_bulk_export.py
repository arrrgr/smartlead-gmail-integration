import requests
import json
import time
from datetime import datetime
from gmail_auth import GmailAuth
from mbox_converter import MboxConverter
from gmail_uploader import GmailUploader
import config

class SmartleadBulkExporter:
    def __init__(self, api_key, gmail_service=None):
        """
        Initialize the bulk exporter
        
        Args:
            api_key: Your Smartlead API key
            gmail_service: Authenticated Gmail service (optional, will create if not provided)
        """
        self.api_key = api_key
        self.base_url = "https://server.smartlead.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Initialize Gmail service if not provided
        if gmail_service is None:
            gmail_auth = GmailAuth()
            if not gmail_auth.is_authenticated():
                raise Exception("Gmail not authenticated. Please run the web app first to authenticate.")
            self.gmail_service = gmail_auth.get_gmail_service()
        else:
            self.gmail_service = gmail_service
            
        self.uploader = GmailUploader(self.gmail_service)
        
    def get_campaigns(self, client_id=None):
        """Get all campaigns, optionally filtered by client"""
        url = f"{self.base_url}/campaigns"
        params = {}
        if client_id:
            params['client_id'] = client_id
            
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def get_campaign_leads(self, campaign_id):
        """Get all leads for a campaign"""
        url = f"{self.base_url}/campaigns/{campaign_id}/leads"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_lead_messages(self, campaign_id, lead_id):
        """Get all messages for a specific lead"""
        url = f"{self.base_url}/campaigns/{campaign_id}/leads/{lead_id}/messages"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def convert_smartlead_to_webhook_format(self, message, campaign_info, lead_info):
        """Convert Smartlead API message format to webhook format"""
        # Determine if this is a sent message or reply
        is_reply = message.get('direction', 'outbound') == 'inbound'
        
        webhook_data = {
            "event_type": "EMAIL_REPLY" if is_reply else "EMAIL_SENT",
            "event_timestamp": message.get('sent_at', datetime.now().isoformat() + "Z"),
            "from_email": message.get('from_email', campaign_info.get('from_email', '')),
            "to_email": message.get('to_email', lead_info.get('email', '')),
            "to_name": lead_info.get('name', ''),
            "subject": message.get('subject', ''),
            "campaign_id": campaign_info.get('id'),
            "campaign_name": campaign_info.get('name', ''),
            "sequence_number": message.get('sequence_number', 1),
        }
        
        # Add message content
        if is_reply:
            webhook_data["reply_message"] = {
                "message_id": message.get('message_id', f"<{message.get('id', 'unknown')}@smartlead.ai>"),
                "html": message.get('html_body', ''),
                "text": message.get('text_body', ''),
                "time": message.get('sent_at', datetime.now().isoformat() + "Z")
            }
            # For replies, we need the original message too
            webhook_data["sent_message"] = {
                "message_id": message.get('in_reply_to', ''),
                "html": "",  # We don't have the original in this context
                "text": "",
                "time": message.get('original_sent_at', datetime.now().isoformat() + "Z")
            }
        else:
            webhook_data["sent_message"] = {
                "message_id": message.get('message_id', f"<{message.get('id', 'unknown')}@smartlead.ai>"),
                "html": message.get('html_body', ''),
                "text": message.get('text_body', ''),
                "time": message.get('sent_at', datetime.now().isoformat() + "Z")
            }
        
        return webhook_data
    
    def process_message(self, webhook_data):
        """Process a single message and upload to Gmail"""
        try:
            # Convert to email message
            email_message = MboxConverter.create_email_message(webhook_data)
            raw_message = MboxConverter.message_to_raw(email_message)
            
            # Upload to Gmail
            result = self.uploader.upload_message(raw_message, webhook_data.get('event_type'))
            
            return result
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def export_client_messages(self, client_id, dry_run=False):
        """
        Export all messages for a specific client
        
        Args:
            client_id: The Smartlead client ID
            dry_run: If True, only print what would be done without uploading
        """
        print(f"Starting export for client ID: {client_id}")
        
        # Get all campaigns for the client
        campaigns = self.get_campaigns(client_id)
        print(f"Found {len(campaigns)} campaigns")
        
        total_messages = 0
        successful_uploads = 0
        failed_uploads = 0
        
        for campaign in campaigns:
            campaign_id = campaign['id']
            print(f"\nProcessing campaign: {campaign['name']} (ID: {campaign_id})")
            
            # Get all leads in the campaign
            leads = self.get_campaign_leads(campaign_id)
            print(f"  Found {len(leads)} leads")
            
            for lead in leads:
                lead_id = lead['id']
                print(f"  Processing lead: {lead.get('email', 'Unknown')} (ID: {lead_id})")
                
                # Get all messages for this lead
                messages = self.get_lead_messages(campaign_id, lead_id)
                print(f"    Found {len(messages)} messages")
                
                for message in messages:
                    total_messages += 1
                    
                    # Convert to webhook format
                    webhook_data = self.convert_smartlead_to_webhook_format(message, campaign, lead)
                    
                    if dry_run:
                        print(f"    Would upload: {webhook_data['event_type']} - {webhook_data['subject']}")
                    else:
                        # Process and upload the message
                        result = self.process_message(webhook_data)
                        
                        if result['success']:
                            successful_uploads += 1
                            print(f"    ✓ Uploaded: {webhook_data['event_type']} - {webhook_data['subject']}")
                        else:
                            failed_uploads += 1
                            print(f"    ✗ Failed: {webhook_data['event_type']} - {webhook_data['subject']}")
                            print(f"      Error: {result.get('error', 'Unknown error')}")
                    
                    # Rate limiting - be nice to the APIs
                    time.sleep(0.5)
        
        print(f"\n{'DRY RUN ' if dry_run else ''}Export Summary:")
        print(f"Total messages found: {total_messages}")
        if not dry_run:
            print(f"Successfully uploaded: {successful_uploads}")
            print(f"Failed uploads: {failed_uploads}")
        
        return {
            'total_messages': total_messages,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads
        }


def main():
    """Main function to run the bulk export"""
    # Configuration
    SMARTLEAD_API_KEY = input("Enter your Smartlead API key: ")
    CLIENT_ID = input("Enter the client ID to export: ")
    
    # Ask for dry run
    dry_run_input = input("Do a dry run first? (y/n): ").lower()
    dry_run = dry_run_input == 'y'
    
    try:
        # Create exporter
        exporter = SmartleadBulkExporter(SMARTLEAD_API_KEY)
        
        # Run export
        results = exporter.export_client_messages(CLIENT_ID, dry_run=dry_run)
        
        if dry_run and results['total_messages'] > 0:
            proceed = input(f"\nFound {results['total_messages']} messages. Proceed with upload? (y/n): ").lower()
            if proceed == 'y':
                # Run actual export
                results = exporter.export_client_messages(CLIENT_ID, dry_run=False)
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main() 