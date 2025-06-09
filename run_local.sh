#!/bin/bash

# Environment variables needed (set these before running):
# export GOOGLE_CLIENT_ID="your-client-id"
# export GOOGLE_CLIENT_SECRET="your-client-secret"
# export GMAIL_ACCOUNT="your-gmail-account"
# export APP_URL="http://localhost:5001"

# Check if required environment variables are set
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "Error: Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables"
    echo "Example:"
    echo '  export GOOGLE_CLIENT_ID="your-client-id"'
    echo '  export GOOGLE_CLIENT_SECRET="your-client-secret"'
    exit 1
fi

# Set default values if not provided
export GMAIL_ACCOUNT="${GMAIL_ACCOUNT:-marketing@oversecured.com}"
export APP_URL="${APP_URL:-http://localhost:5001}"

# Run the app
python3 app.py
python3 smartlead_bulk_export.py