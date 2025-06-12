# Fix Railway Authentication Persistence Issue

## Problem
The Railway app loses Gmail authentication when you close your browser because the OAuth token is stored in a local file (`token.json`) which doesn't persist between Railway deployments or restarts.

## Solution Overview
Store the OAuth token as an environment variable in Railway so it persists across sessions and deployments.

## Step-by-Step Fix

### Step 1: Get Your OAuth Token

1. **Run the app locally** to authenticate and generate a token:
   ```bash
   python app.py
   ```

2. **Complete the OAuth flow**:
   - Visit `http://localhost:5000`
   - Click "Authenticate with Gmail"
   - Log in with your Gmail account
   - Grant permissions

3. **Copy the token** that's printed in the console. After successful authentication, you'll see output like:
   ```
   ============================================================
   TOKEN SAVED! To use in Railway, set this environment variable:
   ============================================================
   GMAIL_TOKEN_JSON=eyJ0eXBlIjogInNlcnZpY2VfYWNjb3VudCIsIC...
   ============================================================
   ```

### Step 2: Set Environment Variable in Railway

1. **Go to your Railway project dashboard**
2. **Navigate to Variables** tab
3. **Add a new variable**:
   - Name: `GMAIL_TOKEN_JSON`
   - Value: (paste the entire base64 string from Step 1)
4. **Save and deploy**

### Step 3: Verify Token Persistence

1. **Check the logs** in Railway to confirm the token is loaded:
   ```
   Loaded credentials from environment variable
   ```

2. **Test the webhook endpoint**:
   ```bash
   curl https://your-app.railway.app/health
   ```
   
   Should return:
   ```json
   {
     "status": "healthy",
     "authenticated": true
   }
   ```

## Additional Improvements

### 1. Add Automatic Token Refresh Logging

Update `gmail_auth.py` to better handle token refresh:

```python
def load_credentials(self):
    """Load credentials from environment variable or token file"""
    # ... existing code ...
    
    # Refresh token if expired
    if self.creds and self.creds.expired and self.creds.refresh_token:
        try:
            self.creds.refresh(Request())
            self.save_credentials()
            print("Refreshed expired token")
            
            # For Railway, also update the env var reminder
            if os.environ.get('RAILWAY_ENVIRONMENT'):
                token_json = self.creds.to_json()
                token_base64 = base64.b64encode(token_json.encode()).decode()
                print(f"Token refreshed! Update GMAIL_TOKEN_JSON in Railway: {token_base64[:50]}...")
        except Exception as e:
            print(f"Error refreshing token: {e}")
            self.creds = None
```

### 2. Add Token Expiry Monitoring

Add an endpoint to check token expiry:

```python
@app.route('/token-status')
def token_status():
    """Check token expiry status"""
    if not gmail_auth.is_authenticated():
        return jsonify({'authenticated': False})
    
    creds = gmail_auth.creds
    return jsonify({
        'authenticated': True,
        'expired': creds.expired if creds else None,
        'has_refresh_token': bool(creds.refresh_token) if creds else False
    })
```

### 3. Set Up Monitoring

1. **Use Railway's health checks** to monitor the `/health` endpoint
2. **Set up alerts** if authentication fails
3. **Monitor token expiry** and refresh as needed

## Troubleshooting

### Token Not Loading
- Check if `GMAIL_TOKEN_JSON` is properly set in Railway variables
- Verify the base64 string is complete (no truncation)
- Check Railway logs for error messages

### Token Expired
- OAuth tokens expire after a certain period
- The app should auto-refresh if it has a refresh token
- If auto-refresh fails, re-authenticate locally and update the Railway variable

### Rate Limiting Issues
The Gmail API has quotas:
- 250 quota units per user per second
- Each message upload uses ~25 quota units
- Solution: Add delays between uploads or implement exponential backoff

## Best Practices

1. **Rotate tokens periodically** for security
2. **Monitor token expiry** and refresh proactively
3. **Keep a backup** of your token locally
4. **Use Railway's secrets** feature for sensitive data
5. **Set up proper error handling** and logging

## Quick Commands

### Check if authenticated:
```bash
curl https://your-app.railway.app/health
```

### Re-authenticate locally:
```bash
# Delete old token
rm token.json

# Run app and authenticate
python app.py

# Copy new token from console output
```

### Update Railway variable:
```bash
# Using Railway CLI
railway variables set GMAIL_TOKEN_JSON="your-base64-token"
```

## Security Notes

- Never commit `token.json` to version control
- Use Railway's environment variables for all sensitive data
- Regularly audit and rotate OAuth tokens
- Monitor for unauthorized access attempts 