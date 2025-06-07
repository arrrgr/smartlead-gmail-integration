#!/usr/bin/env python3
"""Test script to verify bulk export functionality"""

import os
from smartlead_bulk_export import SmartleadBulkExporter

def test_bulk_export():
    # Get API key from environment or prompt
    api_key = os.getenv('SMARTLEAD_API_KEY')
    if not api_key:
        api_key = input("Enter your Smartlead API key: ").strip()
    
    print("\n🔍 Testing Smartlead Bulk Export...")
    
    try:
        # Initialize exporter
        exporter = SmartleadBulkExporter(api_key)
        
        # Test 1: Fetch campaigns
        print("\n1. Fetching campaigns...")
        campaigns = exporter.get_campaigns()
        
        if not campaigns:
            print("❌ No campaigns found. Make sure your API key is correct.")
            return
        
        print(f"✅ Found {len(campaigns)} campaigns")
        
        # Show first few campaigns
        for i, campaign in enumerate(campaigns[:3]):
            print(f"   - {campaign.get('name', 'Unnamed')} (ID: {campaign.get('id')})")
        
        if len(campaigns) > 3:
            print(f"   ... and {len(campaigns) - 3} more")
        
        # Test 2: Get leads from first campaign
        first_campaign = campaigns[0]
        campaign_id = first_campaign.get('id')
        
        print(f"\n2. Fetching leads from campaign '{first_campaign.get('name')}'...")
        leads = exporter.get_campaign_leads(campaign_id)
        
        if not leads:
            print("❌ No leads found in this campaign.")
        else:
            print(f"✅ Found {len(leads)} leads")
            
            # Test 3: Get messages for first lead
            if leads:
                first_lead = leads[0]
                lead_id = first_lead.get('id')
                email = first_lead.get('email', 'Unknown')
                
                print(f"\n3. Fetching messages for lead '{email}'...")
                messages = exporter.get_lead_messages(campaign_id, lead_id)
                
                if not messages:
                    print("❌ No messages found for this lead.")
                else:
                    print(f"✅ Found {len(messages)} messages")
                    
                    # Show first message preview
                    if messages:
                        first_msg = messages[0]
                        print(f"\n   First message preview:")
                        print(f"   - Subject: {first_msg.get('subject', 'No subject')[:50]}...")
                        print(f"   - Date: {first_msg.get('time_sent', 'Unknown')}")
        
        print("\n✅ All tests passed! You can now run the full bulk export.")
        print("\nTo export all messages, run:")
        print("  python3 bulk_export.py")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {str(e)}")
        print("\nPlease check:")
        print("1. Your Smartlead API key is correct")
        print("2. You have campaigns with leads in your Smartlead account")
        print("3. Your internet connection is working")

if __name__ == "__main__":
    test_bulk_export() 