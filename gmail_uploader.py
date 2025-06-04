from googleapiclient.errors import HttpError
import config

class GmailUploader:
    def __init__(self, gmail_service):
        self.service = gmail_service
        self.label_cache = {}
        self._ensure_labels()
    
    def _ensure_labels(self):
        """Ensure required labels exist in Gmail"""
        try:
            # Get existing labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            existing_labels = {label['name']: label['id'] for label in labels}
            
            # Create labels if they don't exist
            for label_name in [config.LABEL_SENT, config.LABEL_REPLIES]:
                if label_name not in existing_labels:
                    label_id = self._create_label(label_name)
                    if label_id:
                        self.label_cache[label_name] = label_id
                else:
                    self.label_cache[label_name] = existing_labels[label_name]
        except HttpError as e:
            print(f"Error managing labels: {e}")
    
    def _create_label(self, label_name):
        """Create a new label in Gmail"""
        try:
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()
            
            return created_label['id']
        except HttpError as e:
            print(f"Error creating label {label_name}: {e}")
            return None
    
    def upload_message(self, raw_message, event_type):
        """Upload a message to Gmail"""
        try:
            # Determine which label to use
            label_name = config.LABEL_SENT if event_type == 'EMAIL_SENT' else config.LABEL_REPLIES
            label_id = self.label_cache.get(label_name)
            
            # Create message body
            message_body = {'raw': raw_message}
            
            # Add label if available
            if label_id:
                message_body['labelIds'] = [label_id]
            
            # Insert the message
            message = self.service.users().messages().insert(
                userId='me',
                body=message_body
            ).execute()
            
            return {
                'success': True,
                'message_id': message['id'],
                'thread_id': message.get('threadId')
            }
            
        except HttpError as e:
            error_message = f"Error uploading message: {e}"
            print(error_message)
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_message_by_id(self, message_id):
        """Get a message by its Gmail ID"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id
            ).execute()
            return message
        except HttpError as e:
            print(f"Error retrieving message: {e}")
            return None 