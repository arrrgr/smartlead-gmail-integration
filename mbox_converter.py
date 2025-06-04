import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, parseaddr, formataddr
from datetime import datetime
import base64
import re

class MboxConverter:
    @staticmethod
    def create_email_message(webhook_data):
        """Convert webhook data to email message format"""
        event_type = webhook_data.get('event_type', '')
        
        if event_type == 'EMAIL_SENT':
            return MboxConverter._create_sent_message(webhook_data)
        elif event_type == 'EMAIL_REPLY':
            return MboxConverter._create_reply_message(webhook_data)
        else:
            raise ValueError(f"Unknown event type: {event_type}")
    
    @staticmethod
    def _create_sent_message(webhook_data):
        """Create email message for sent emails"""
        # Extract data
        from_email = webhook_data.get('from_email', '')
        to_email = webhook_data.get('to_email', '')
        to_name = webhook_data.get('to_name', '')
        subject = webhook_data.get('subject', '')
        
        # Get message content
        sent_message = webhook_data.get('sent_message', {})
        html_content = sent_message.get('html', webhook_data.get('sent_message_body', ''))
        text_content = sent_message.get('text', '')
        message_id = sent_message.get('message_id', webhook_data.get('message_id', ''))
        
        # Get timestamp
        timestamp_str = sent_message.get('time', webhook_data.get('event_timestamp', webhook_data.get('time_sent', '')))
        
        # Create message
        if html_content and text_content:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
        elif html_content:
            msg = MIMEText(html_content, 'html')
        else:
            msg = MIMEText(text_content or '', 'plain')
        
        # Set headers
        msg['From'] = from_email
        msg['To'] = formataddr((to_name, to_email)) if to_name else to_email
        msg['Subject'] = subject
        msg['Message-ID'] = message_id
        msg['Date'] = MboxConverter._format_date(timestamp_str)
        
        # Add custom headers for tracking
        msg['X-Smartlead-Campaign-ID'] = str(webhook_data.get('campaign_id', ''))
        msg['X-Smartlead-Campaign-Name'] = webhook_data.get('campaign_name', '')
        msg['X-Smartlead-Sequence-Number'] = str(webhook_data.get('sequence_number', ''))
        msg['X-Smartlead-Stats-ID'] = webhook_data.get('stats_id', '')
        
        return msg
    
    @staticmethod
    def _create_reply_message(webhook_data):
        """Create email message for reply emails"""
        # Extract data - note the from/to are swapped for replies
        from_email = webhook_data.get('to_email', '')  # The lead who replied
        from_name = webhook_data.get('to_name', '')
        to_email = webhook_data.get('from_email', '')  # Our mailbox
        subject = webhook_data.get('subject', '')
        
        # Get reply content
        reply_message = webhook_data.get('reply_message', {})
        html_content = reply_message.get('html', webhook_data.get('reply_body', ''))
        text_content = reply_message.get('text', webhook_data.get('preview_text', ''))
        message_id = reply_message.get('message_id', webhook_data.get('message_id', ''))
        
        # Get original message ID for threading
        sent_message = webhook_data.get('sent_message', {})
        in_reply_to = sent_message.get('message_id', '')
        
        # Get timestamp
        timestamp_str = reply_message.get('time', webhook_data.get('event_timestamp', webhook_data.get('time_replied', '')))
        
        # Create message
        if html_content and text_content:
            msg = MIMEMultipart('alternative')
            msg.attach(MIMEText(text_content, 'plain'))
            msg.attach(MIMEText(html_content, 'html'))
        elif html_content:
            msg = MIMEText(html_content, 'html')
        else:
            msg = MIMEText(text_content or '', 'plain')
        
        # Set headers
        msg['From'] = formataddr((from_name, from_email)) if from_name else from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg['Message-ID'] = message_id
        msg['Date'] = MboxConverter._format_date(timestamp_str)
        
        # Threading headers
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
            msg['References'] = in_reply_to
        
        # Add custom headers for tracking
        msg['X-Smartlead-Campaign-ID'] = str(webhook_data.get('campaign_id', ''))
        msg['X-Smartlead-Campaign-Name'] = webhook_data.get('campaign_name', '')
        msg['X-Smartlead-Sequence-Number'] = str(webhook_data.get('sequence_number', ''))
        msg['X-Smartlead-Stats-ID'] = webhook_data.get('stats_id', '')
        msg['X-Smartlead-Reply-Category'] = webhook_data.get('reply_category', '')
        
        return msg
    
    @staticmethod
    def _format_date(timestamp_str):
        """Format timestamp to RFC 2822 format"""
        if not timestamp_str:
            return formatdate(localtime=True)
        
        try:
            # Parse ISO format timestamp
            if 'T' in timestamp_str:
                dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                return formatdate(dt.timestamp(), localtime=False)
            else:
                return timestamp_str
        except:
            return formatdate(localtime=True)
    
    @staticmethod
    def message_to_raw(message):
        """Convert email message to raw format for Gmail API"""
        return base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8') 