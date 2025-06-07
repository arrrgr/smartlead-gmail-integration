#!/usr/bin/env python3
"""
Initialize tracking for messages already uploaded
This prevents re-uploading the 1670 messages from the first run
"""

import pickle
import os
from smartlead_bulk_export_safe import SafeSmartleadBulkExporter

def initialize_tracking_from_first_run():
    """
    Since we know 1670 messages were uploaded in the first run,
    we need to mark them as uploaded to prevent duplicates
    """
    
    print("Initializing tracking for already uploaded messages...")
    
    # Your credentials
    API_KEY = "eefa0acd-633f-4734-bbd3-46ac9f4d2f6b_9ma6p68"
    CLIENT_ID = "38760"
    
    # Create exporter to get message IDs
    exporter = SafeSmartleadBulkExporter(API_KEY)
    
    print(f"Current tracking status: {len(exporter.uploaded_messages)} messages tracked")
    
    if len(exporter.uploaded_messages) > 0:
        response = input(f"\nTracking file already exists with {len(exporter.uploaded_messages)} messages. Reset it? (y/n): ")
        if response.lower() != 'y':
            print("Keeping existing tracking.")
            return
    
    print("\nFetching all messages to identify the first 1670 that were uploaded...")
    
    # Get all campaigns for the client
    all_campaigns = exporter.get_campaigns()
    client_campaigns = [c for c in all_campaigns if str(c.get('client_id')) == str(CLIENT_ID)]
    
    print(f"Found {len(client_campaigns)} campaigns for client {CLIENT_ID}")
    
    # Collect all messages with their IDs
    all_messages = []
    message_count = 0
    
    for campaign in client_campaigns:
        campaign_id = campaign['id']
        print(f"\nProcessing campaign: {campaign['name']} (ID: {campaign_id})")
        
        try:
            leads = exporter.get_campaign_leads(campaign_id)
            
            for lead_info in leads:
                lead_data = lead_info.get('lead', {})
                lead_id = lead_data.get('id')
                
                try:
                    history_data = exporter.get_lead_message_history(campaign_id, lead_id)
                    messages = history_data.get('history', [])
                    
                    for message in messages:
                        message_data = {
                            'campaign_id': campaign_id,
                            'lead_id': lead_id,
                            'time': message.get('time'),
                            'subject': message.get('subject', '')
                        }
                        message_unique_id = exporter.create_message_id(message_data)
                        all_messages.append(message_unique_id)
                        message_count += 1
                        
                        # Stop if we've collected 1670 messages
                        if message_count >= 1670:
                            break
                    
                    if message_count >= 1670:
                        break
                        
                except Exception as e:
                    print(f"    Error getting messages for lead {lead_id}: {str(e)}")
                    continue
            
            if message_count >= 1670:
                break
                
        except Exception as e:
            print(f"    Error processing campaign: {str(e)}")
            continue
    
    print(f"\nCollected {len(all_messages)} message IDs (target was 1670)")
    
    # Mark the first 1670 as uploaded
    uploaded_count = min(len(all_messages), 1670)
    exporter.uploaded_messages = set(all_messages[:uploaded_count])
    
    # Save the tracking
    exporter.save_tracking()
    
    print(f"\nSuccessfully marked {uploaded_count} messages as already uploaded")
    print(f"Tracking file saved: {exporter.tracking_file}")
    
    return uploaded_count

if __name__ == "__main__":
    initialize_tracking_from_first_run() 