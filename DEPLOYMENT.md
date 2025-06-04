# Cloud Deployment Guide

## Option 1: Railway (Recommended - Easiest)

Railway provides instant deployment with automatic SSL and easy environment variables.

### Steps:

1. **Install Railway CLI** (optional, can use web interface):
   ```bash
   npm install -g @railway/cli
   ```

2. **Deploy via Web Interface**:
   - Go to [railway.app](https://railway.app)
   - Click "New Project" → "Deploy from GitHub repo"
   - Connect your GitHub account and select your repository
   - Railway will automatically detect it's a Python app

3. **Set Environment Variables** in Railway dashboard:
   ```
   APP_URL=https://your-app-name.railway.app
   WEBHOOK_SECRET_KEY=your_smartlead_secret_key
   ```

4. **Important**: After deployment, you need to update the redirect URI in Google Cloud Console:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Navigate to APIs & Services → Credentials
   - Edit your OAuth 2.0 Client ID
   - Add `https://your-app-name.railway.app/oauth2callback` to Authorized redirect URIs

## Option 2: Render

Render offers free hosting with automatic SSL.

### Steps:

1. **Create account** at [render.com](https://render.com)

2. **Create New Web Service**:
   - Connect GitHub repo
   - Choose "Python" environment
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app --bind 0.0.0.0:$PORT`

3. **Set Environment Variables**:
   ```
   APP_URL=https://your-app-name.onrender.com
   WEBHOOK_SECRET_KEY=your_smartlead_secret_key
   ```

4. **Update Google OAuth redirect URI** (same as Railway)

## Option 3: Heroku

### Steps:

1. **Install Heroku CLI**:
   ```bash
   brew tap heroku/brew && brew install heroku  # macOS
   ```

2. **Create Heroku app**:
   ```bash
   heroku create your-app-name
   git add .
   git commit -m "Initial commit"
   git push heroku main
   ```

3. **Set environment variables**:
   ```bash
   heroku config:set APP_URL=https://your-app-name.herokuapp.com
   heroku config:set WEBHOOK_SECRET_KEY=your_smartlead_secret_key
   ```

4. **Update Google OAuth redirect URI**

## Option 4: Google Cloud Run

Best for production with auto-scaling.

### Dockerfile needed:

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

### Deploy:
```bash
gcloud run deploy smartlead-gmail \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars APP_URL=https://smartlead-gmail-xxxxx.run.app
```

## Post-Deployment Steps

1. **Visit your app URL** and authenticate with Gmail
2. **Configure Smartlead webhooks** to point to `https://your-app-url/webhook`
3. **Test with the test script** (update WEBHOOK_URL first):
   ```bash
   python test_webhook.py
   ```

## Important Notes

- **Token Persistence**: The `token.json` file needs to persist between deployments. Consider using:
  - Railway/Render: Use volumes for persistent storage
  - Heroku: Use Heroku Postgres or Redis to store tokens
  - Google Cloud: Use Cloud Storage or Firestore

- **Security**: Always use HTTPS URLs in production
- **Monitoring**: Set up logging to track webhook processing
- **Rate Limits**: Monitor Gmail API usage in Google Cloud Console 