#!/usr/bin/env python3
"""
Safe Smartlead Bulk Export with Duplicate Prevention
This version tracks uploaded messages and prevents duplicates
"""

import requests
import json
import time
import hashlib
import pickle
import os
from datetime import datetime
from gmail_auth import GmailAuth
from mbox_converter import MboxConverter
from gmail_uploader import GmailUploader
import config

class SafeSmartleadBulkExporter:
    def __init__(self, api_key, gmail_service=None):
        """Initialize the safe bulk exporter with duplicate tracking"""
        self.api_key = api_key
        self.base_url = "https://server.smartlead.ai/api/v1"
        
        # Initialize Gmail service
        if gmail_service is None:
            gmail_auth = GmailAuth()
            if not gmail_auth.is_authenticated():
                raise Exception("Gmail not authenticated. Please run the web app first to authenticate.")
            self.gmail_service = gmail_auth.get_gmail_service()
        else:
            self.gmail_service = gmail_service
            
        self.uploader = GmailUploader(self.gmail_service)
        
        # Load or create upload tracking
        self.tracking_file = "upload_tracking.pkl"
        self.uploaded_messages = self.load_tracking()
        
    def load_tracking(self):
        """Load previously uploaded message IDs"""
        if os.path.exists(self.tracking_file):
            try:
                with open(self.tracking_file, 'rb') as f:
                    return pickle.load(f)
            except:
                return set()
        return set()
    
    def save_tracking(self):
        """Save uploaded message IDs"""
        with open(self.tracking_file, 'wb') as f:
            pickle.dump(self.uploaded_messages, f)
    
    def create_message_id(self, message_data):
        """Create a unique ID for a message to track duplicates"""
        # Create hash from key message properties
        key_data = f"{message_data.get('campaign_id')}_{message_data.get('lead_id')}_{message_data.get('time')}_{message_data.get('subject', '')}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def api_request_with_retry(self, url, max_retries=5):
        """Make API request with retry logic for rate limiting"""
        for attempt in range(max_retries):
            try:
                response = requests.get(url)
                
                if response.status_code == 429:  # Too Many Requests
                    wait_time = (attempt + 1) * 5  # Exponential backoff
                    print(f"        Rate limited. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                elif response.status_code == 502:  # Bad Gateway
                    wait_time = 3
                    print(f"        Server error. Waiting {wait_time} seconds...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(2)
        
        raise Exception(f"Failed after {max_retries} attempts")
    
    def get_campaigns(self):
        """Get all campaigns with retry logic"""
        url = f"{self.base_url}/campaigns?api_key={self.api_key}"
        return self.api_request_with_retry(url)
    
    def get_campaign_by_id(self, campaign_id):
        """Get campaign details by ID with retry logic"""
        url = f"{self.base_url}/campaigns/{campaign_id}?api_key={self.api_key}"
        return self.api_request_with_retry(url)
    
    def get_campaign_leads(self, campaign_id, offset=0, limit=100):
        """Get all leads for a campaign with pagination and retry logic"""
        all_leads = []
        
        while True:
            url = f"{self.base_url}/campaigns/{campaign_id}/leads?api_key={self.api_key}&offset={offset}&limit={limit}"
            
            try:
                data = self.api_request_with_retry(url)
                leads_data = data.get('data', [])
                all_leads.extend(leads_data)
                
                # Check if we've fetched all leads
                total_leads = int(data.get('total_leads', 0))
                if offset + limit >= total_leads:
                    break
                    
                offset += limit
                time.sleep(0.5)  # Rate limiting between pages
                
            except Exception as e:
                print(f"        Error fetching leads page at offset {offset}: {str(e)}")
                break
                
        return all_leads
    
    def get_lead_message_history(self, campaign_id, lead_id):
        """Get message history with retry logic"""
        url = f"{self.base_url}/campaigns/{campaign_id}/leads/{lead_id}/message-history?api_key={self.api_key}"
        return self.api_request_with_retry(url)
    
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
            "sequence_number": 1,
            "lead_id": lead_data.get('id'),  # Add lead_id for tracking
        }
        
        # Add message content
        if is_reply:
            webhook_data["reply_message"] = {
                "message_id": message.get('message_id', f"<{datetime.now().timestamp()}@smartlead.ai>"),
                "html": message.get('email_body', ''),
                "text": message.get('email_body', ''),
                "time": message.get('time', datetime.now().isoformat() + "Z")
            }
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
                "text": message.get('email_body', ''),
                "time": message.get('time', datetime.now().isoformat() + "Z")
            }
        
        return webhook_data
    
    def process_message(self, webhook_data, message_unique_id):
        """Process a single message and upload to Gmail if not already uploaded"""
        try:
            # Check if already uploaded
            if message_unique_id in self.uploaded_messages:
                return {'success': True, 'skipped': True, 'reason': 'Already uploaded'}
            
            # Convert to email message
            email_message = MboxConverter.create_email_message(webhook_data)
            raw_message = MboxConverter.message_to_raw(email_message)
            
            # Upload to Gmail
            result = self.uploader.upload_message(raw_message, webhook_data.get('event_type'))
            
            if result['success']:
                # Track this message as uploaded
                self.uploaded_messages.add(message_unique_id)
                # Save tracking every 10 uploads
                if len(self.uploaded_messages) % 10 == 0:
                    self.save_tracking()
            
            return result
            
        except Exception as e:
            print(f"Error processing message: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    def export_campaign_messages(self, campaign_id, dry_run=False):
        """Export all messages for a specific campaign with duplicate prevention"""
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
        skipped_uploads = 0
        
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
                    
                    # Create unique ID for this message
                    message_data = {
                        'campaign_id': campaign_id,
                        'lead_id': lead_id,
                        'time': message.get('time'),
                        'subject': message.get('subject', '')
                    }
                    message_unique_id = self.create_message_id(message_data)
                    
                    # Convert to webhook format
                    webhook_data = self.convert_smartlead_to_webhook_format(
                        message, campaign, lead_info, from_email
                    )
                    
                    if dry_run:
                        if message_unique_id in self.uploaded_messages:
                            print(f"    Would skip (already uploaded): {webhook_data['event_type']} - {webhook_data.get('subject', 'No subject')[:50]}...")
                            skipped_uploads += 1
                        else:
                            print(f"    Would upload: {webhook_data['event_type']} - {webhook_data.get('subject', 'No subject')[:50]}...")
                    else:
                        # Process and upload the message
                        result = self.process_message(webhook_data, message_unique_id)
                        
                        if result.get('skipped'):
                            skipped_uploads += 1
                            print(f"    ⏭️  Skipped (already uploaded): {webhook_data.get('subject', 'No subject')[:50]}...")
                        elif result['success']:
                            successful_uploads += 1
                            print(f"    ✓ {webhook_data['event_type']} - {webhook_data.get('subject', 'No subject')[:50]}...")
                        else:
                            failed_uploads += 1
                            print(f"    ✗ Failed: {result.get('error', 'Unknown error')}")
                    
                    # Rate limiting
                    if not dry_run and not result.get('skipped'):
                        time.sleep(0.5)
                    
            except Exception as e:
                print(f"    Error fetching message history: {str(e)}")
                continue
        
        # Save final tracking
        if not dry_run:
            self.save_tracking()
        
        print(f"\n{'DRY RUN ' if dry_run else ''}Export Summary:")
        print(f"Total messages found: {total_messages}")
        print(f"Already uploaded (skipped): {skipped_uploads}")
        print(f"New messages to upload: {total_messages - skipped_uploads}")
        if not dry_run:
            print(f"Successfully uploaded: {successful_uploads}")
            print(f"Failed uploads: {failed_uploads}")
        
        return {
            'total_messages': total_messages,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'skipped_uploads': skipped_uploads
        }
    
    def export_client_messages(self, client_id, dry_run=False):
        """Export all messages for campaigns belonging to a specific client"""
        print(f"Starting export for client ID: {client_id}")
        
        # Get all campaigns and filter by client_id
        all_campaigns = self.get_campaigns()
        client_campaigns = [c for c in all_campaigns if str(c.get('client_id')) == str(client_id)]
        
        print(f"Found {len(client_campaigns)} campaigns for client {client_id}")
        
        total_messages = 0
        successful_uploads = 0
        failed_uploads = 0
        skipped_uploads = 0
        
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
                skipped_uploads += results['skipped_uploads']
        
        print(f"\n{'='*60}")
        print(f"{'DRY RUN ' if dry_run else ''}TOTAL EXPORT SUMMARY FOR CLIENT {client_id}")
        print(f"{'='*60}")
        print(f"Total messages: {total_messages}")
        print(f"Already uploaded (skipped): {skipped_uploads}")
        print(f"New messages to upload: {total_messages - skipped_uploads}")
        if not dry_run:
            print(f"Successfully uploaded: {successful_uploads}")
            print(f"Failed uploads: {failed_uploads}")
        
        return {
            'total_messages': total_messages,
            'successful_uploads': successful_uploads,
            'failed_uploads': failed_uploads,
            'skipped_uploads': skipped_uploads
        }
    
    def get_upload_status(self):
        """Get current upload status"""
        print(f"\nCurrent Upload Status:")
        print(f"Total messages tracked as uploaded: {len(self.uploaded_messages)}")
        print(f"Tracking file: {self.tracking_file}")


def main():
    """Main function to run the safe bulk export"""
    # Configuration
    SMARTLEAD_API_KEY = input("Enter your Smartlead API key: ")
    
    # Create exporter
    exporter = SafeSmartleadBulkExporter(SMARTLEAD_API_KEY)
    
    # Show current status
    exporter.get_upload_status()
    
    # Ask what to export
    export_type = input("\nExport by (1) Campaign ID or (2) Client ID? Enter 1 or 2: ")
    
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
        # Run export
        if export_method == "campaign":
            results = exporter.export_campaign_messages(target_id, dry_run=dry_run)
        else:
            results = exporter.export_client_messages(target_id, dry_run=dry_run)
        
        if dry_run and results and (results['total_messages'] - results['skipped_uploads']) > 0:
            proceed = input(f"\nFound {results['total_messages'] - results['skipped_uploads']} new messages to upload. Proceed? (y/n): ").lower()
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