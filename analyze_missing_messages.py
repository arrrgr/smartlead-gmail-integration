#!/usr/bin/env python3
"""Analyze what messages exist in Smartlead and what might be missing"""

import os
from smartlead_bulk_export import SmartleadBulkExporter
from collections import defaultdict

def analyze_smartlead_data(api_key, client_id=None):
    """Analyze all campaigns and messages in Smartlead"""
    
    exporter = SmartleadBulkExporter(api_key)
    
    # Get all campaigns
    all_campaigns = exporter.get_campaigns()
    
    # Filter by client if specified
    if client_id:
        campaigns = [c for c in all_campaigns if str(c.get('client_id')) == str(client_id)]
        print(f"\nAnalyzing campaigns for client {client_id}")
    else:
        campaigns = all_campaigns
        print(f"\nAnalyzing all campaigns")
    
    print(f"Found {len(campaigns)} campaigns\n")
    
    # Statistics
    total_messages = 0
    total_leads = 0
    campaign_stats = []
    
    # Analyze each campaign
    for i, campaign in enumerate(campaigns, 1):
        campaign_id = campaign['id']
        campaign_name = campaign.get('name', 'Unknown')
        client_id_camp = campaign.get('client_id', 'Unknown')
        
        print(f"[{i}/{len(campaigns)}] Analyzing: {campaign_name}")
        print(f"    Campaign ID: {campaign_id}")
        print(f"    Client ID: {client_id_camp}")
        
        try:
            # Get leads for this campaign
            leads = exporter.get_campaign_leads(campaign_id)
            campaign_leads = len(leads)
            total_leads += campaign_leads
            
            print(f"    Leads: {campaign_leads}")
            
            # Count messages
            campaign_messages = 0
            lead_details = []
            
            for lead_info in leads:
                lead_data = lead_info.get('lead', {})
                lead_id = lead_data.get('id')
                lead_email = lead_data.get('email', 'Unknown')
                
                try:
                    # Get message history
                    history_data = exporter.get_lead_message_history(campaign_id, lead_id)
                    messages = history_data.get('history', [])
                    message_count = len(messages)
                    campaign_messages += message_count
                    
                    if message_count > 0:
                        lead_details.append({
                            'email': lead_email,
                            'messages': message_count
                        })
                    
                except Exception as e:
                    print(f"        Error getting messages for {lead_email}: {str(e)}")
            
            total_messages += campaign_messages
            
            print(f"    Total messages: {campaign_messages}")
            print(f"    Leads with messages: {len(lead_details)}")
            
            # Store campaign stats
            campaign_stats.append({
                'id': campaign_id,
                'name': campaign_name,
                'client_id': client_id_camp,
                'leads': campaign_leads,
                'messages': campaign_messages,
                'leads_with_messages': len(lead_details)
            })
            
        except Exception as e:
            print(f"    Error analyzing campaign: {str(e)}")
            campaign_stats.append({
                'id': campaign_id,
                'name': campaign_name,
                'client_id': client_id_camp,
                'leads': 0,
                'messages': 0,
                'leads_with_messages': 0,
                'error': str(e)
            })
        
        print()
    
    # Summary
    print("="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total campaigns analyzed: {len(campaigns)}")
    print(f"Total leads: {total_leads}")
    print(f"Total messages: {total_messages}")
    print()
    
    # Campaign breakdown
    print("Campaign Breakdown:")
    print("-"*60)
    for stat in campaign_stats:
        error_msg = f" [ERROR: {stat.get('error')}]" if 'error' in stat else ""
        print(f"- {stat['name']}")
        print(f"  ID: {stat['id']}, Client: {stat['client_id']}")
        print(f"  Leads: {stat['leads']}, Messages: {stat['messages']}{error_msg}")
    
    return {
        'total_campaigns': len(campaigns),
        'total_leads': total_leads,
        'total_messages': total_messages,
        'campaign_stats': campaign_stats
    }

def compare_with_upload_log(expected_messages, uploaded_messages):
    """Compare expected vs uploaded messages"""
    missing = expected_messages - uploaded_messages
    
    print("\n" + "="*60)
    print("COMPARISON")
    print("="*60)
    print(f"Expected messages: {expected_messages}")
    print(f"Uploaded messages: {uploaded_messages}")
    print(f"Missing messages: {missing}")
    print(f"Completion rate: {(uploaded_messages/expected_messages)*100:.1f}%")

def main():
    # Get API key
    api_key = os.getenv('SMARTLEAD_API_KEY')
    if not api_key:
        api_key = input("Enter your Smartlead API key: ").strip()
    
    # Ask for client ID
    client_id = input("Enter client ID to analyze (or press Enter for all): ").strip()
    
    # Analyze
    print("\nAnalyzing Smartlead data...")
    results = analyze_smartlead_data(api_key, client_id if client_id else None)
    
    # Compare with known upload
    print("\n" + "="*60)
    uploaded = input("How many messages were successfully uploaded? (press Enter to skip): ").strip()
    if uploaded and uploaded.isdigit():
        compare_with_upload_log(results['total_messages'], int(uploaded))
    
    # Ask about expected count
    expected = input("\nHow many messages were you expecting? (press Enter to skip): ").strip()
    if expected and expected.isdigit():
        print(f"\nDifference from expected: {int(expected) - results['total_messages']} messages")

if __name__ == "__main__":
    main() 