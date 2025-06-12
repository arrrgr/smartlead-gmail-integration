#!/usr/bin/env python3
"""
CLI tool for Smartlead-Attio Integration
Allows manual syncing of campaigns and testing webhook handling
"""
import argparse
import json
import os
import sys
from smartlead_attio_sync import SmartleadAttioSync
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_campaign(args):
    """Sync a campaign from Smartlead to Attio"""
    # Get API keys from environment or arguments
    attio_key = args.attio_key or os.getenv('ATTIO_API_KEY')
    smartlead_key = args.smartlead_key or os.getenv('SMARTLEAD_API_KEY')
    
    if not attio_key or not smartlead_key:
        print("Error: Missing API keys. Provide via --attio-key and --smartlead-key or set environment variables.")
        return 1
    
    # Initialize sync handler
    sync = SmartleadAttioSync(attio_key, smartlead_key)
    
    print(f"Starting sync for campaign ID: {args.campaign_id}")
    if args.dry_run:
        print("DRY RUN MODE - No data will be synced")
    
    # Perform sync
    result = sync.sync_campaign(args.campaign_id, dry_run=args.dry_run)
    
    if result['success']:
        print(f"\n✓ Sync completed successfully!")
        print(f"Campaign: {result['campaign_name']}")
        print(f"Total synced: {result['total_synced']}")
        
        if result['errors']:
            print(f"\nErrors encountered ({len(result['errors'])}):")
            for error in result['errors'][:10]:  # Show first 10 errors
                print(f"  - {error['email']}: {error['error']}")
            if len(result['errors']) > 10:
                print(f"  ... and {len(result['errors']) - 10} more errors")
    else:
        print(f"\n✗ Sync failed: {result.get('error', 'Unknown error')}")
        return 1
    
    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return 0


def test_webhook(args):
    """Test webhook handling with sample data"""
    # Get API keys
    attio_key = args.attio_key or os.getenv('ATTIO_API_KEY')
    smartlead_key = args.smartlead_key or os.getenv('SMARTLEAD_API_KEY')
    
    if not attio_key or not smartlead_key:
        print("Error: Missing API keys.")
        return 1
    
    # Initialize sync handler
    sync = SmartleadAttioSync(attio_key, smartlead_key)
    
    # Load webhook data
    if args.webhook_file:
        with open(args.webhook_file, 'r') as f:
            webhook_data = json.load(f)
    else:
        # Sample webhook data
        webhook_data = {
            "event_type": args.event_type,
            "to_email": args.email,
            "campaign_id": args.campaign_id,
            "campaign_name": "Test Campaign"
        }
        
        if args.event_type == "LEAD_CATEGORY_UPDATED":
            webhook_data["lead_category"] = {
                "new_name": args.category or "Interested"
            }
    
    print(f"Testing webhook: {webhook_data['event_type']}")
    
    # Handle webhook
    result = sync.handle_webhook(webhook_data)
    
    if result['success']:
        print(f"✓ Webhook handled successfully: {result.get('message', '')}")
    else:
        print(f"✗ Webhook handling failed: {result.get('error', '')}")
        return 1
    
    return 0


def list_campaigns(args):
    """List all campaigns from Smartlead"""
    import requests
    
    smartlead_key = args.smartlead_key or os.getenv('SMARTLEAD_API_KEY')
    
    if not smartlead_key:
        print("Error: Missing Smartlead API key.")
        return 1
    
    try:
        url = f"https://server.smartlead.ai/api/v1/campaigns?api_key={smartlead_key}"
        response = requests.get(url)
        response.raise_for_status()
        
        campaigns = response.json()
        
        print(f"Found {len(campaigns)} campaigns:\n")
        print(f"{'ID':<10} {'Name':<40} {'Status':<15} {'Client':<20}")
        print("-" * 85)
        
        for campaign in campaigns:
            client_id = campaign.get('client_id', 'N/A')
            print(f"{campaign['id']:<10} {campaign['name'][:40]:<40} {campaign['status']:<15} {client_id:<20}")
        
    except Exception as e:
        print(f"Error listing campaigns: {e}")
        return 1
    
    return 0


def main():
    parser = argparse.ArgumentParser(description='Smartlead-Attio Integration CLI')
    parser.add_argument('--attio-key', help='Attio API key (or set ATTIO_API_KEY env var)')
    parser.add_argument('--smartlead-key', help='Smartlead API key (or set SMARTLEAD_API_KEY env var)')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Sync campaign command
    sync_parser = subparsers.add_parser('sync', help='Sync a campaign to Attio')
    sync_parser.add_argument('campaign_id', type=int, help='Campaign ID to sync')
    sync_parser.add_argument('--dry-run', action='store_true', help='Preview sync without making changes')
    sync_parser.add_argument('--output', help='Save results to JSON file')
    
    # Test webhook command
    webhook_parser = subparsers.add_parser('test-webhook', help='Test webhook handling')
    webhook_parser.add_argument('--event-type', 
                               choices=['EMAIL_SENT', 'FIRST_EMAIL_SENT', 'EMAIL_REPLY', 'LEAD_CATEGORY_UPDATED'],
                               default='FIRST_EMAIL_SENT',
                               help='Webhook event type')
    webhook_parser.add_argument('--email', default='test@example.com', help='Lead email address')
    webhook_parser.add_argument('--campaign-id', type=int, default=1, help='Campaign ID')
    webhook_parser.add_argument('--category', help='Category name (for LEAD_CATEGORY_UPDATED)')
    webhook_parser.add_argument('--webhook-file', help='Load webhook data from JSON file')
    
    # List campaigns command
    list_parser = subparsers.add_parser('list', help='List all Smartlead campaigns')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    if args.command == 'sync':
        return sync_campaign(args)
    elif args.command == 'test-webhook':
        return test_webhook(args)
    elif args.command == 'list':
        return list_campaigns(args)


if __name__ == '__main__':
    sys.exit(main()) 