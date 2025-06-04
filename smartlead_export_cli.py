#!/usr/bin/env python3
"""
Smartlead to Gmail Bulk Export Tool

This script exports all messages from Smartlead for a specific client
and uploads them to Gmail with proper labels.

Usage:
    python smartlead_export_cli.py --api-key YOUR_API_KEY --client-id CLIENT_ID
    python smartlead_export_cli.py --api-key YOUR_API_KEY --all-clients
    python smartlead_export_cli.py --api-key YOUR_API_KEY --campaign-id CAMPAIGN_ID
"""

import argparse
import sys
import json
from datetime import datetime
from smartlead_bulk_export import SmartleadBulkExporter


def list_clients_and_campaigns(exporter):
    """List all available clients and campaigns"""
    print("Fetching all campaigns...")
    campaigns = exporter.get_campaigns()
    
    # Group by client
    clients = {}
    for campaign in campaigns:
        client_id = campaign.get('client_id', 'Unknown')
        client_name = campaign.get('client_name', 'Unknown Client')
        
        if client_id not in clients:
            clients[client_id] = {
                'name': client_name,
                'campaigns': []
            }
        
        clients[client_id]['campaigns'].append({
            'id': campaign['id'],
            'name': campaign['name'],
            'status': campaign.get('status', 'Unknown')
        })
    
    print("\nAvailable Clients and Campaigns:")
    print("=" * 60)
    
    for client_id, client_info in clients.items():
        print(f"\nClient ID: {client_id}")
        print(f"  Campaigns:")
        for campaign in client_info['campaigns']:
            print(f"    - {campaign['name']} (ID: {campaign['id']}, Status: {campaign['status']})")
    
    return clients


def main():
    parser = argparse.ArgumentParser(description='Export Smartlead messages to Gmail')
    parser.add_argument('--api-key', required=True, help='Smartlead API key')
    parser.add_argument('--client-id', help='Export messages for a specific client ID')
    parser.add_argument('--campaign-id', help='Export messages for a specific campaign ID')
    parser.add_argument('--all-clients', action='store_true', help='Export messages for all clients')
    parser.add_argument('--list', action='store_true', help='List all clients and campaigns')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be exported without uploading')
    parser.add_argument('--output', help='Save export summary to JSON file')
    
    args = parser.parse_args()
    
    # Create exporter
    try:
        exporter = SmartleadBulkExporter(args.api_key)
    except Exception as e:
        print(f"Error initializing exporter: {str(e)}")
        print("\nMake sure you have authenticated with Gmail first by visiting:")
        print("https://web-production-3fc01.up.railway.app")
        return 1
    
    # Handle different modes
    results = None
    
    if args.list:
        # List mode
        list_clients_and_campaigns(exporter)
        return 0
    
    elif args.campaign_id:
        # Export specific campaign
        results = exporter.export_campaign_messages(args.campaign_id, dry_run=args.dry_run)
        
    elif args.client_id:
        # Export specific client
        results = exporter.export_client_messages(args.client_id, dry_run=args.dry_run)
        
    elif args.all_clients:
        # Export all clients
        if not args.dry_run:
            confirm = input("This will export ALL messages from ALL clients. Are you sure? (yes/no): ")
            if confirm.lower() != 'yes':
                print("Export cancelled.")
                return 0
        
        campaigns = exporter.get_campaigns()
        client_ids = set(c.get('client_id') for c in campaigns if c.get('client_id'))
        
        all_results = {}
        for client_id in client_ids:
            print(f"\n{'='*60}")
            print(f"Exporting client ID: {client_id}")
            print(f"{'='*60}")
            
            client_results = exporter.export_client_messages(client_id, dry_run=args.dry_run)
            all_results[client_id] = client_results
        
        # Aggregate results
        results = {
            'total_messages': sum(r['total_messages'] for r in all_results.values() if r),
            'successful_uploads': sum(r['successful_uploads'] for r in all_results.values() if r),
            'failed_uploads': sum(r['failed_uploads'] for r in all_results.values() if r),
            'by_client': all_results
        }
    
    else:
        parser.error("Please specify --client-id, --campaign-id, --all-clients, or --list")
    
    # Display results
    if results:
        print("\n" + "="*60)
        print(f"{'DRY RUN ' if args.dry_run else ''}EXPORT SUMMARY")
        print("="*60)
        print(f"Total messages: {results['total_messages']}")
        if not args.dry_run:
            print(f"Successfully uploaded: {results['successful_uploads']}")
            print(f"Failed uploads: {results['failed_uploads']}")
            if results['failed_uploads'] > 0:
                print("\nNote: Failed uploads may be due to duplicate messages or rate limits.")
                print("You can safely re-run the export - duplicates will be skipped.")
        
        # Save results if requested
        if args.output:
            with open(args.output, 'w') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'dry_run': args.dry_run,
                    'results': results
                }, f, indent=2)
            print(f"\nResults saved to: {args.output}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main()) 