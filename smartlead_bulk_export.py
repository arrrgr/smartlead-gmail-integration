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
        
        # Initialize Gmail service if not provided
        if gmail_service is None:
            gmail_auth = GmailAuth()
            if not gmail_auth.is_authenticated():
                raise Exception("Gmail not authenticated. Please run the web app first to authenticate.")
            self.gmail_service = gmail_auth.get_gmail_service()
        else:
            self.gmail_service = gmail_service
            
        self.uploader = GmailUploader(self.gmail_service)
        
    def get_campaigns(self):
        """Get all campaigns"""
        url = f"{self.base_url}/campaigns?api_key={self.api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_campaign_by_id(self, campaign_id):
        """Get campaign details by ID"""
        url = f"{self.base_url}/campaigns/{campaign_id}?api_key={self.api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def get_campaign_leads(self, campaign_id, offset=0, limit=100):
        """Get all leads for a campaign with pagination"""
        all_leads = []
        
        while True:
            url = f"{self.base_url}/campaigns/{campaign_id}/leads?api_key={self.api_key}&offset={offset}&limit={limit}"
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            leads_data = data.get('data', [])
            all_leads.extend(leads_data)
            
            # Check if we've fetched all leads
            total_leads = data.get('total_leads', 0)
            if offset + limit >= total_leads:
                break
                
            offset += limit
            time.sleep(0.2)  # Rate limiting
            
        return all_leads
    
    def get_lead_message_history(self, campaign_id, lead_id):
        """Get message history for a specific lead in a campaign"""
        url = f"{self.base_url}/campaigns/{campaign_id}/leads/{lead_id}/message-history?api_key={self.api_key}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    
    def convert_smartlead_to_webhook_format(self, message, campaign_info, lead_info, from_email):
        """Convert Smartlead API message format to webhook format"""
        # Determine if this is a sent message or reply
        is_reply = message.get('type') == 'REPLY'
        
        # Extract lead details from the nested structure
        lead_data = lead_info.get('lead', {})
        
        webhook_data = {
            "event_type": "EMAIL_REPLY" if is_reply else "EMAIL_SENT",
            "event_timestamp": message.get('time', datetime.now().isoformat() + "Z"),
            "from_email": from_email if not is_reply else lead_data.get('email', ''),
            "to_email": lead_data.get('email', '') if not is_reply else from_email,
            "to_name": f"{lead_data.get('first_name', '')} {lead_data.get('last_name', '')}".strip(),
            "subject": message.get('subject', ''),
            "campaign_id": campaign_info.get('id'),
            "campaign_name": campaign_info.get('name', ''),
            "sequence_number": 1,  # This might need to be extracted from the message
        }
        
        # Add message content
        if is_reply:
            webhook_data["reply_message"] = {
                "message_id": message.get('message_id', f"<{datetime.now().timestamp()}@smartlead.ai>"),
                "html": message.get('email_body', ''),
                "text": message.get('email_body', ''),  # Smartlead doesn't separate HTML/text
                "time": message.get('time', datetime.now().isoformat() + "Z")
            }
            # For replies, we need a placeholder for the original message
            webhook_data["sent_message"] = {
                "message_id": "",
                "html": "",
                "text": "",
                "time": datetime.now().isoformat() + "Z"
            }
        else:
            webhook_data["sent_message"] = {
                "message_id": message.get('message_id', f"<{datetime.now().timestamp()}@smartlead.ai>"),
                "html": message.get('email_body', ''),
                "text": message.get('email_body', ''),  # Smartlead doesn't separate HTML/text
                "time": message.get('time', datetime.now().isoformat() + "Z")
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
    
    def export_campaign_messages(self, campaign_id, dry_run=False):
        """
        Export all messages for a specific campaign
        
        Args:
            campaign_id: The Smartlead campaign ID
            dry_run: If True, only print what would be done without uploading
        """
        print(f"Starting export for campaign ID: {campaign_id}")
        
        # Get campaign details
        try:
            campaign = self.get_campaign_by_id(campaign_id)
        except Exception as e:
            print(f"Error fetching campaign: {str(e)}")
            return None
            
        print(f"Campaign: {campaign.get('name', 'Unknown')}")
        
        # Get all leads in the campaign
        leads = self.get_campaign_leads(campaign_id)
        print(f"Found {len(leads)} leads")
        
        total_messages = 0
        successful_uploads = 0
        failed_uploads = 0
        
        for i, lead_info in enumerate(leads, 1):
            lead_data = lead_info.get('lead', {})
            lead_id = lead_data.get('id')
            lead_email = lead_data.get('email', 'Unknown')
            
            print(f"\n[{i}/{len(leads)}] Processing lead: {lead_email} (ID: {lead_id})")
            
            # Get message history for this lead
            try:
                history_data = self.get_lead_message_history(campaign_id, lead_id)
                messages = history_data.get('history', [])
                from_email = history_data.get('from', '')
                
                print(f"    Found {len(messages)} messages")
                
                for message in messages:
                    total_messages += 1
                    
                    # Convert to webhook format
                    webhook_data = self.convert_smartlead_to_webhook_format(
                        message, campaign, lead_info, from_email
                    )
                    
                    if dry_run:
                        print(f"    Would upload: {webhook_data['event_type']} - {webhook_data.get('subject', 'No subject')[:50]}...")
                    else:
                        # Process and upload the message
                        result = self.process_message(webhook_data)
                        
                        if result['success']:
                            successful_uploads += 1
                            print(f"    ✓ {webhook_data['event_type']} - {webhook_data.get('subject', 'No subject')[:50]}...")
                        else:
                            failed_uploads += 1
                            print(f"    ✗ Failed: {result.get('error', 'Unknown error')}")
                    
                    # Rate limiting - be nice to the APIs
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"    Error fetching message history: {str(e)}")
                continue
        
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
    
    def export_client_messages(self, client_id, dry_run=False):
        """
        Export all messages for campaigns belonging to a specific client
        
        Args:
            client_id: The Smartlead client ID
            dry_run: If True, only print what would be done without uploading
        """
        print(f"Starting export for client ID: {client_id}")
        
        # Get all campaigns and filter by client_id
        all_campaigns = self.get_campaigns()
        client_campaigns = [c for c in all_campaigns if c.get('client_id') == int(client_id)]
        
        print(f"Found {len(client_campaigns)} campaigns for client {client_id}")
        
        total_messages = 0
        successful_uploads = 0
        failed_uploads = 0
        
        for campaign in client_campaigns:
            campaign_id = campaign['id']
            print(f"\n{'='*60}")
            print(f"Processing campaign: {campaign['name']} (ID: {campaign_id})")
            print(f"{'='*60}")
            
            results = self.export_campaign_messages(campaign_id, dry_run=dry_run)
            
            if results:
                total_messages += results['total_messages']
                successful_uploads += results['successful_uploads']
                failed_uploads += results['failed_uploads']
        
        print(f"\n{'='*60}")
        print(f"{'DRY RUN ' if dry_run else ''}TOTAL EXPORT SUMMARY FOR CLIENT {client_id}")
        print(f"{'='*60}")
        print(f"Total messages: {total_messages}")
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
    
    # Ask what to export
    export_type = input("Export by (1) Campaign ID or (2) Client ID? Enter 1 or 2: ")
    
    if export_type == "1":
        CAMPAIGN_ID = input("Enter the campaign ID to export: ")
        target_id = CAMPAIGN_ID
        export_method = "campaign"
    else:
        CLIENT_ID = input("Enter the client ID to export: ")
        target_id = CLIENT_ID
        export_method = "client"
    
    # Ask for dry run
    dry_run_input = input("Do a dry run first? (y/n): ").lower()
    dry_run = dry_run_input == 'y'
    
    try:
        # Create exporter
        exporter = SmartleadBulkExporter(SMARTLEAD_API_KEY)
        
        # Run export
        if export_method == "campaign":
            results = exporter.export_campaign_messages(target_id, dry_run=dry_run)
        else:
            results = exporter.export_client_messages(target_id, dry_run=dry_run)
        
        if dry_run and results and results['total_messages'] > 0:
            proceed = input(f"\nFound {results['total_messages']} messages. Proceed with upload? (y/n): ").lower()
            if proceed == 'y':
                # Run actual export
                if export_method == "campaign":
                    results = exporter.export_campaign_messages(target_id, dry_run=False)
                else:
                    results = exporter.export_client_messages(target_id, dry_run=False)
                
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0


if __name__ == "__main__":
    main() 