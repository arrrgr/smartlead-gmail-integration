#!/usr/bin/env python3
"""
Run the safe bulk export with pre-filled credentials
"""

from smartlead_bulk_export_safe import SafeSmartleadBulkExporter

# Your credentials
API_KEY = "eefa0acd-633f-4734-bbd3-46ac9f4d2f6b_9ma6p68"
CLIENT_ID = "38760"

def run_safe_export():
    print("Starting Safe Smartlead Bulk Export")
    print("="*60)
    
    # Create exporter
    exporter = SafeSmartleadBulkExporter(API_KEY)
    
    # Show current status
    exporter.get_upload_status()
    
    # If no tracking exists, initialize it
    if len(exporter.uploaded_messages) == 0:
        print("\nNo tracking file found. Initializing with first 1670 messages...")
        print("This will prevent re-uploading messages from your first run.")
        
        response = input("\nInitialize tracking for 1670 already uploaded messages? (y/n): ")
        if response.lower() == 'y':
            from initialize_tracking import initialize_tracking_from_first_run
            initialize_tracking_from_first_run()
            # Reload the tracking
            exporter = SafeSmartleadBulkExporter(API_KEY)
            exporter.get_upload_status()
    
    # Run dry run first
    print(f"\nRunning DRY RUN for client {CLIENT_ID}...")
    results = exporter.export_client_messages(CLIENT_ID, dry_run=True)
    
    if results and (results['total_messages'] - results['skipped_uploads']) > 0:
        print("\n" + "="*60)
        print("DRY RUN COMPLETE")
        print("="*60)
        print(f"Total messages in Smartlead: {results['total_messages']}")
        print(f"Already uploaded: {results['skipped_uploads']}")
        print(f"New messages to upload: {results['total_messages'] - results['skipped_uploads']}")
        
        proceed = input(f"\nProceed with uploading {results['total_messages'] - results['skipped_uploads']} new messages? (y/n): ").lower()
        if proceed == 'y':
            print("\nStarting actual upload...")
            results = exporter.export_client_messages(CLIENT_ID, dry_run=False)
            
            print("\n" + "="*60)
            print("UPLOAD COMPLETE")
            print("="*60)
            print(f"Successfully uploaded: {results['successful_uploads']}")
            print(f"Failed uploads: {results['failed_uploads']}")
            print(f"Total messages now tracked: {len(exporter.uploaded_messages)}")
    else:
        print("\nNo new messages to upload!")

if __name__ == "__main__":
    run_safe_export() 