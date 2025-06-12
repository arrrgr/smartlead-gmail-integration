# Smartlead-Attio Integration

This integration automatically syncs companies and contacts from Smartlead campaigns to Attio CRM and manages pipeline stages based on email activity.

## Features

- **Automatic Company/Contact Sync**: Imports all leads from Smartlead campaigns as companies and contacts in Attio
- **Pipeline Management**: Automatically moves companies through pipeline stages based on email activity
- **Email Sync**: Leverages the existing Gmail integration to sync email conversations to Attio
- **Webhook Support**: Real-time updates based on Smartlead events
- **Bulk Import**: CLI tool for importing existing campaigns

## How It Works

1. **Company/Contact Creation**: When you sync a campaign or receive a webhook, the integration creates or updates companies and contacts in Attio
2. **Email Sync**: Emails are synced via the Gmail integration (Smartlead → Gmail → Attio)
3. **Pipeline Automation**: Companies move through the "Digital Outreach" pipeline automatically:
   - **Vulnerability Found**: Initial stage when company is added
   - **Email Sent**: When first email is sent
   - **Interested Reply**: When positive reply is received
   - **Booked**: When meeting is booked

## Setup Instructions

### 1. Prerequisites

- Attio account with API access
- Smartlead account with API access
- "Digital Outreach" list in Attio with the following stages:
  - Vulnerability Found
  - Email Sent
  - Interested Reply
  - Booked

### 2. Install Dependencies

```bash
cd attio_integration
pip install requests flask
```

### 3. Configure API Keys

Set environment variables:

```bash
export ATTIO_API_KEY="your-attio-api-key"
export SMARTLEAD_API_KEY="your-smartlead-api-key"
export WEBHOOK_SECRET_KEY="your-webhook-secret"  # Optional but recommended
```

### 4. Run the Integration

#### Option A: Web Server (for webhooks)

```bash
python attio_webhook_app.py
```

Visit `http://localhost:5002` to access the dashboard.

#### Option B: CLI (for manual sync)

```bash
# List all campaigns
python sync_cli.py list

# Sync a specific campaign
python sync_cli.py sync 12345

# Dry run (preview without syncing)
python sync_cli.py sync 12345 --dry-run

# Save results to file
python sync_cli.py sync 12345 --output results.json
```

### 5. Configure Smartlead Webhooks

In Smartlead, set up webhooks pointing to your integration:

1. Go to Campaign Settings → Webhooks
2. Add webhook URL: `https://your-server.com/webhook`
3. Select events:
   - EMAIL_SENT (for first email tracking)
   - EMAIL_REPLY
   - LEAD_CATEGORY_UPDATED
4. Add your webhook secret key if configured

## API Endpoints

### Dashboard
- `GET /` - Web dashboard for monitoring and manual sync

### Webhook Handler
- `POST /webhook` - Receives webhooks from Smartlead

### Campaign Sync
- `POST /sync-campaign/<campaign_id>` - Manually sync a campaign
  - Query params: `?dry_run=true` for preview mode

### Health Check
- `GET /health` - Check integration status

## CLI Commands

### List Campaigns
```bash
python sync_cli.py list
```

### Sync Campaign
```bash
python sync_cli.py sync <campaign_id> [options]

Options:
  --dry-run          Preview sync without making changes
  --output FILE      Save results to JSON file
  --attio-key KEY    Override Attio API key
  --smartlead-key KEY Override Smartlead API key
```

### Test Webhook
```bash
python sync_cli.py test-webhook [options]

Options:
  --event-type TYPE  Webhook event type
  --email EMAIL      Lead email address
  --campaign-id ID   Campaign ID
  --category NAME    Category name (for updates)
  --webhook-file FILE Load webhook data from file
```

## Pipeline Automation Rules

The integration automatically updates pipeline stages based on these events:

1. **Company Added** → "Vulnerability Found"
2. **First Email Sent** → "Email Sent"
3. **Positive Reply Received** → "Interested Reply"
   - Triggered by categories: Interested, Meeting Request, Information Request
4. **Meeting Booked** → "Booked"
   - Triggered by categories: Booked, Meeting Booked, Demo Scheduled

## Data Mapping

### Smartlead → Attio Company
- `company_name` → Company Name
- `website` or `company_url` → Company Domain

### Smartlead → Attio Person
- `email` → Email Address
- `first_name` + `last_name` → Name
- `phone_number` → Phone Number
- Linked to company if available

### Custom Fields
- Smartlead custom fields are added as notes on the person record
- Campaign information is added as notes on the company record

## Deployment

### Railway Deployment

1. Create a new Railway project
2. Set environment variables:
   ```
   ATTIO_API_KEY=your-key
   SMARTLEAD_API_KEY=your-key
   WEBHOOK_SECRET_KEY=your-secret
   PORT=5002
   ```
3. Deploy the `attio_webhook_app.py`
4. Use the Railway URL for webhooks

### Docker Deployment

Create a `Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY attio_integration/ .

RUN pip install requests flask gunicorn

CMD ["gunicorn", "--bind", "0.0.0.0:5002", "attio_webhook_app:app"]
```

## Troubleshooting

### Integration Not Working

1. Check API keys are correctly set
2. Verify "Digital Outreach" list exists in Attio with correct stages
3. Check logs for detailed error messages

### Companies Not Moving Through Pipeline

1. Ensure webhook events are being received
2. Verify lead categories match expected values
3. Check that companies are properly linked to contacts

### Duplicate Records

The integration checks for existing records by:
- Companies: Domain or exact name match
- People: Email address match

### Rate Limiting

- Attio API: Check current limits in your plan
- Add delays between bulk operations if needed

## Security Considerations

- Always use HTTPS in production
- Set `WEBHOOK_SECRET_KEY` to verify webhook authenticity
- Store API keys securely (use environment variables)
- Regularly rotate API keys

## Support

For issues or questions:
1. Check the logs for detailed error messages
2. Use dry-run mode to preview operations
3. Test webhooks with the CLI tool
4. Verify data mapping matches your Attio configuration 