#!/bin/bash

# Set environment variables
export GOOGLE_CLIENT_ID="234646251525-kdvnaoeu0gcvfgorsr8afer5ncfnrq50.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="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"
export GMAIL_ACCOUNT="marketing@oversecured.com"
export APP_URL="http://localhost:5001"

# Run the app
python3 app.py
python3 smartlead_bulk_export.py