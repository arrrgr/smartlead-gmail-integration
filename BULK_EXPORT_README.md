# Smartlead Bulk Export to Gmail

This tool allows you to export all historical messages from Smartlead and import them into Gmail with proper labels and threading.

## Prerequisites

1. **Gmail Authentication**: You must first authenticate with Gmail using the web interface at your Railway app URL
2. **Smartlead API Key**: You need your Smartlead API key (found in Smartlead settings)
3. **Python Dependencies**: Install required packages:
   ```bash
   pip install -r requirements.txt
   ```

## Quick Start

### 1. Find Your Smartlead API Key

1. Log into Smartlead
2. Go to Settings → API
3. Copy your API key

### 2. List All Clients and Campaigns

First, see what's available to export:

```bash
python smartlead_export_cli.py --api-key YOUR_API_KEY --list
```

This will show all your clients and their campaigns with IDs.

### 3. Export Messages

#### For a Specific Client

```bash
# Dry run first (shows what would be exported)
python smartlead_export_cli.py --api-key YOUR_API_KEY --client-id CLIENT_ID --dry-run

# Actual export
python smartlead_export_cli.py --api-key YOUR_API_KEY --client-id CLIENT_ID
```

#### For a Specific Campaign

```bash
python smartlead_export_cli.py --api-key YOUR_API_KEY --campaign-id CAMPAIGN_ID
```

#### For All Clients (use with caution!)

```bash
python smartlead_export_cli.py --api-key YOUR_API_KEY --all-clients --dry-run
```

### 4. Save Export Summary

You can save a detailed export report:

```bash
python smartlead_export_cli.py --api-key YOUR_API_KEY --client-id CLIENT_ID --output export_report.json
```

## How It Works

1. **Fetches Data from Smartlead API**:
   - Gets all campaigns for the specified client
   - For each campaign, gets all leads
   - For each lead, gets all messages (sent and replies)

2. **Converts to MBOX Format**:
   - Preserves all email headers
   - Maintains threading with Message-ID and References
   - Includes both HTML and plain text versions

3. **Uploads to Gmail**:
   - Sent emails get labeled: `Smartlead/Sent`
   - Reply emails get labeled: `Smartlead/Replies`
   - Gmail automatically groups related messages into conversations

## Command Line Options

```
--api-key       Your Smartlead API key (required)
--client-id     Export messages for a specific client ID
--campaign-id   Export messages for a specific campaign ID
--all-clients   Export messages for all clients
--list          List all clients and campaigns
--dry-run       Show what would be exported without uploading
--output        Save export summary to JSON file
```

## Examples

### Example 1: Export with Progress Tracking

```bash
python smartlead_export_cli.py --api-key YOUR_API_KEY --client-id 12345
```

Output:
```
Starting export for client ID: 12345
Found 3 campaigns

Processing campaign: Q4 Outreach (ID: 67890)
  Found 150 leads

[1/150] Processing lead: john@example.com
  ✓ EMAIL_SENT - Introduction to our services...
  ✓ EMAIL_REPLY - Re: Introduction to our services...

[2/150] Processing lead: jane@example.com
  ✓ EMAIL_SENT - Following up on our conversation...
  
...

EXPORT SUMMARY
============================================================
Total messages: 487
Successfully uploaded: 485
Failed uploads: 2
```

### Example 2: Interactive Export

If you prefer an interactive experience:

```bash
python smartlead_bulk_export.py
```

This will prompt you for:
1. Your Smartlead API key
2. The client ID to export
3. Whether to do a dry run first

## Rate Limits and Performance

- The script includes a 0.5-second delay between messages to respect API rate limits
- Gmail API has a quota of 250 quota units per user per second
- Each message upload uses about 25 quota units
- For large exports (1000+ messages), the process may take 10-20 minutes

## Troubleshooting

### "Gmail not authenticated" Error

Make sure you've authenticated with Gmail first:
1. Visit your Railway app URL
2. Click "Authenticate with Gmail"
3. Complete the OAuth flow

### "API key invalid" Error

Double-check your Smartlead API key in the Smartlead settings.

### Duplicate Messages

The Gmail API automatically prevents duplicate messages based on Message-ID. If you run the export multiple times, duplicates will be skipped.

### Rate Limit Errors

If you hit rate limits, the script will show failed uploads. You can safely re-run the export - it will skip already uploaded messages.

## Advanced Usage

### Custom Filtering

You can modify the `smartlead_bulk_export.py` script to add custom filters:

```python
# Example: Only export messages from the last 30 days
from datetime import datetime, timedelta

def filter_recent_messages(messages):
    cutoff_date = datetime.now() - timedelta(days=30)
    return [m for m in messages if datetime.fromisoformat(m['sent_at'].rstrip('Z')) > cutoff_date]
```

### Batch Processing

For very large exports, you can process in batches:

```bash
# Export one campaign at a time
for campaign_id in 12345 67890 13579; do
    python smartlead_export_cli.py --api-key YOUR_API_KEY --campaign-id $campaign_id
    sleep 60  # Wait 1 minute between campaigns
done
```

## Security Notes

- Your Smartlead API key is sent with each request - keep it secure
- Gmail tokens are stored locally in `token.json` - don't commit this file
- All data is transferred over HTTPS

## Support

If you encounter issues:
1. Check the Railway logs for detailed error messages
2. Ensure your Gmail authentication is still valid
3. Verify your Smartlead API key has the necessary permissions 