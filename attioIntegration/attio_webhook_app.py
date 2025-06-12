"""
Flask app for Smartlead-Attio Integration
Handles webhooks and provides sync endpoints
"""
from flask import Flask, request, jsonify, render_template_string
import json
import logging
import os
from smartlead_attio_sync import SmartleadAttioSync

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')

# Initialize sync handler
attio_api_key = os.getenv('ATTIO_API_KEY')
smartlead_api_key = os.getenv('SMARTLEAD_API_KEY')
webhook_secret = os.getenv('WEBHOOK_SECRET_KEY', '')

if not attio_api_key or not smartlead_api_key:
    logger.error("Missing required API keys. Set ATTIO_API_KEY and SMARTLEAD_API_KEY environment variables.")
    sync_handler = None
else:
    sync_handler = SmartleadAttioSync(attio_api_key, smartlead_api_key)

# HTML template for dashboard
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Smartlead-Attio Integration</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 50px auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .status {
            padding: 15px;
            margin: 20px 0;
            border-radius: 5px;
            text-align: center;
        }
        .success {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .error {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .info {
            background-color: #d1ecf1;
            color: #0c5460;
            border: 1px solid #bee5eb;
        }
        .endpoint {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin: 10px 0;
            font-family: monospace;
        }
        .form-group {
            margin: 20px 0;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
        }
        input[type="text"], input[type="number"] {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background-color: #0056b3;
        }
        .result {
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 5px;
            white-space: pre-wrap;
            font-family: monospace;
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Smartlead-Attio Integration</h1>
        
        {% if not configured %}
        <div class="status error">
            <h2>⚠️ Configuration Required</h2>
            <p>Please set the following environment variables:</p>
            <ul style="text-align: left;">
                <li>ATTIO_API_KEY</li>
                <li>SMARTLEAD_API_KEY</li>
                <li>WEBHOOK_SECRET_KEY (optional)</li>
            </ul>
        </div>
        {% else %}
        <div class="status success">
            <h2>✓ Integration Active</h2>
            <p>The integration is configured and ready to receive webhooks.</p>
        </div>
        
        <div class="info">
            <h3>Webhook Endpoints</h3>
            <div class="endpoint">
                POST {{ webhook_url }}
            </div>
            <p>Configure this URL in your Smartlead webhook settings for:</p>
            <ul style="text-align: left;">
                <li>EMAIL_SENT (First Email)</li>
                <li>EMAIL_REPLY</li>
                <li>LEAD_CATEGORY_UPDATED</li>
            </ul>
        </div>
        
        <div class="info">
            <h3>Sync Campaign</h3>
            <form id="syncForm">
                <div class="form-group">
                    <label for="campaign_id">Campaign ID:</label>
                    <input type="number" id="campaign_id" name="campaign_id" required>
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="dry_run" name="dry_run">
                        Dry Run (preview without syncing)
                    </label>
                </div>
                <button type="submit">Sync Campaign</button>
            </form>
            <div id="syncResult" class="result"></div>
        </div>
        {% endif %}
    </div>
    
    <script>
        document.getElementById('syncForm')?.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const campaignId = document.getElementById('campaign_id').value;
            const dryRun = document.getElementById('dry_run').checked;
            const resultDiv = document.getElementById('syncResult');
            
            resultDiv.style.display = 'block';
            resultDiv.textContent = 'Syncing...';
            
            try {
                const response = await fetch(`/sync-campaign/${campaignId}?dry_run=${dryRun}`, {
                    method: 'POST'
                });
                const data = await response.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
            } catch (error) {
                resultDiv.textContent = `Error: ${error.message}`;
            }
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Dashboard page"""
    configured = sync_handler is not None
    webhook_url = request.url_root + 'webhook'
    
    return render_template_string(
        DASHBOARD_TEMPLATE,
        configured=configured,
        webhook_url=webhook_url
    )

@app.route('/webhook', methods=['POST'])
def webhook():
    """Handle incoming webhooks from Smartlead"""
    try:
        # Get webhook data
        webhook_data = request.get_json()
        
        # Log the webhook
        logger.info(f"Received webhook: {webhook_data.get('event_type', 'Unknown')}")
        
        # Verify secret key if configured
        if webhook_secret:
            provided_secret = webhook_data.get('secret_key', '')
            if provided_secret != webhook_secret:
                logger.warning("Invalid secret key in webhook")
                return jsonify({'error': 'Invalid secret key'}), 401
        
        # Check if sync handler is configured
        if not sync_handler:
            logger.error("Sync handler not configured")
            return jsonify({'error': 'Integration not configured'}), 503
        
        # Handle the webhook
        result = sync_handler.handle_webhook(webhook_data)
        
        if result['success']:
            logger.info(f"Webhook processed successfully: {result.get('message', '')}")
            return jsonify(result), 200
        else:
            logger.error(f"Webhook processing failed: {result.get('error', '')}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/sync-campaign/<int:campaign_id>', methods=['POST'])
def sync_campaign(campaign_id):
    """Sync all leads from a campaign to Attio"""
    try:
        if not sync_handler:
            return jsonify({'error': 'Integration not configured'}), 503
        
        dry_run = request.args.get('dry_run', 'false').lower() == 'true'
        
        logger.info(f"Starting campaign sync for ID: {campaign_id} (dry_run: {dry_run})")
        
        result = sync_handler.sync_campaign(campaign_id, dry_run=dry_run)
        
        if result['success']:
            logger.info(f"Campaign sync completed: {result}")
            return jsonify(result), 200
        else:
            logger.error(f"Campaign sync failed: {result}")
            return jsonify(result), 500
            
    except Exception as e:
        logger.error(f"Campaign sync error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'configured': sync_handler is not None
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5002))
    print(f"Starting Smartlead-Attio Integration on port {port}")
    print(f"Visit http://localhost:{port} to access the dashboard")
    app.run(host='0.0.0.0', port=port, debug=True) 