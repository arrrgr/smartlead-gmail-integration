"""
Smartlead to Attio Integration Handler
Syncs companies, contacts, and manages pipeline stages based on Smartlead events
"""
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from attio_client import AttioClient

logger = logging.getLogger(__name__)


class SmartleadAttioSync:
    def __init__(self, attio_api_key: str, smartlead_api_key: str):
        """Initialize the sync handler"""
        self.attio = AttioClient(attio_api_key)
        self.smartlead_api_key = smartlead_api_key
        
        # Configuration
        self.config = {
            'list_name': 'Digital Outreach',
            'pipeline_stages': {
                'vulnerability_found': 'Vulnerability Found',
                'email_sent': 'Email Sent',
                'interested_reply': 'Interested Reply',
                'booked': 'Booked'
            }
        }
        
        # Cache for list and status IDs
        self._list_id = None
        self._status_ids = {}
        
        # Initialize cache
        self._initialize_cache()
    
    def _initialize_cache(self):
        """Initialize list and status IDs cache"""
        try:
            # Get Digital Outreach list
            digital_outreach_list = self.attio.get_list(self.config['list_name'])
            if digital_outreach_list:
                self._list_id = digital_outreach_list['id']
                
                # Cache status IDs
                for key, status_name in self.config['pipeline_stages'].items():
                    status_id = self.attio.get_status_by_name(self._list_id, status_name)
                    if status_id:
                        self._status_ids[key] = status_id
                    else:
                        logger.warning(f"Status '{status_name}' not found in list")
            else:
                logger.error(f"List '{self.config['list_name']}' not found in Attio")
        except Exception as e:
            logger.error(f"Error initializing cache: {e}")
    
    def sync_lead_from_campaign(self, lead_data: Dict, campaign_data: Dict) -> Dict:
        """Sync a lead from Smartlead campaign to Attio"""
        try:
            # Extract lead information
            lead = lead_data.get('lead', lead_data)
            
            # Prepare company data
            company_data = {
                'name': lead.get('company_name', ''),
                'website': lead.get('website', '') or lead.get('company_url', '')
            }
            
            # Create or get company
            company = None
            if company_data['name'] or company_data['website']:
                company = self.attio.get_or_create_company(company_data)
                logger.info(f"Company synced: {company.get('id')} - {company_data['name']}")
            
            # Prepare person data
            person_data = {
                'email': lead.get('email', ''),
                'first_name': lead.get('first_name', ''),
                'last_name': lead.get('last_name', ''),
                'phone_number': lead.get('phone_number', '')
            }
            
            # Add custom fields as notes if present
            custom_fields = lead.get('custom_fields', {})
            
            # Create or get person
            person = self.attio.get_or_create_person(
                person_data, 
                company_id=company['id'] if company else None
            )
            logger.info(f"Person synced: {person.get('id')} - {person_data['email']}")
            
            # Add custom fields as a note
            if custom_fields:
                note_content = "Smartlead Custom Fields:\n"
                for key, value in custom_fields.items():
                    note_content += f"- {key}: {value}\n"
                
                self.attio.add_note(
                    record_id=person['id'],
                    parent_object='people',
                    title='Smartlead Import Data',
                    content=note_content
                )
            
            # Add campaign info as note
            campaign_note = f"Campaign: {campaign_data.get('name', 'Unknown')}\n"
            campaign_note += f"Campaign ID: {campaign_data.get('id', 'Unknown')}\n"
            campaign_note += f"Imported: {datetime.now().isoformat()}"
            
            if company:
                self.attio.add_note(
                    record_id=company['id'],
                    parent_object='companies',
                    title='Smartlead Campaign Info',
                    content=campaign_note
                )
            
            # Add company to Digital Outreach list if not already there
            if company and self._list_id:
                self._add_company_to_pipeline(company['id'])
            
            return {
                'success': True,
                'company_id': company['id'] if company else None,
                'person_id': person['id']
            }
            
        except Exception as e:
            logger.error(f"Error syncing lead: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _add_company_to_pipeline(self, company_id: str):
        """Add company to Digital Outreach pipeline if not already there"""
        try:
            # Check if already in list
            entry = self.attio.get_list_entry(self._list_id, company_id)
            
            if not entry:
                # Add to list with initial status
                self.attio.add_record_to_list(self._list_id, company_id)
                logger.info(f"Added company {company_id} to Digital Outreach pipeline")
                
                # Set initial status to "Vulnerability Found"
                entry = self.attio.get_list_entry(self._list_id, company_id)
                if entry and 'vulnerability_found' in self._status_ids:
                    self.attio.update_list_entry_status(
                        self._list_id,
                        entry['id'],
                        self._status_ids['vulnerability_found']
                    )
        except Exception as e:
            logger.error(f"Error adding company to pipeline: {e}")
    
    def handle_webhook(self, webhook_data: Dict) -> Dict:
        """Handle incoming webhook from Smartlead"""
        try:
            event_type = webhook_data.get('event_type')
            
            if event_type == 'EMAIL_SENT':
                return self._handle_email_sent(webhook_data)
            elif event_type == 'EMAIL_REPLY':
                return self._handle_email_reply(webhook_data)
            elif event_type == 'LEAD_CATEGORY_UPDATED':
                return self._handle_category_update(webhook_data)
            elif event_type == 'FIRST_EMAIL_SENT':
                return self._handle_first_email_sent(webhook_data)
            else:
                logger.warning(f"Unhandled webhook event type: {event_type}")
                return {'success': True, 'message': 'Event type not handled'}
                
        except Exception as e:
            logger.error(f"Error handling webhook: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_first_email_sent(self, webhook_data: Dict) -> Dict:
        """Handle first email sent event - move to Email Sent stage"""
        try:
            # Get company by email
            to_email = webhook_data.get('to_email', '')
            if not to_email:
                return {'success': False, 'error': 'No recipient email found'}
            
            # Find person by email
            filter_query = {
                "attribute": "email_addresses",
                "relation": "contains",
                "value": to_email
            }
            people = self.attio.search_records('people', filter_query)
            
            if not people:
                logger.warning(f"Person not found for email: {to_email}")
                return {'success': False, 'error': 'Person not found'}
            
            person = people[0]
            
            # Get associated company
            companies = person.get('values', {}).get('companies', [])
            if not companies:
                logger.warning(f"No company associated with person: {to_email}")
                return {'success': False, 'error': 'No company found'}
            
            company_id = companies[0].get('target_record_id')
            
            # Update pipeline status to "Email Sent"
            if self._list_id and 'email_sent' in self._status_ids:
                entry = self.attio.get_list_entry(self._list_id, company_id)
                if entry:
                    self.attio.update_list_entry_status(
                        self._list_id,
                        entry['id'],
                        self._status_ids['email_sent']
                    )
                    logger.info(f"Updated company {company_id} to Email Sent stage")
            
            return {'success': True, 'message': 'Pipeline updated to Email Sent'}
            
        except Exception as e:
            logger.error(f"Error handling first email sent: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_email_sent(self, webhook_data: Dict) -> Dict:
        """Handle email sent event"""
        # For regular email sent events, we might want to add notes or update metadata
        # but not change pipeline status (only first email changes status)
        return {'success': True, 'message': 'Email sent event processed'}
    
    def _handle_email_reply(self, webhook_data: Dict) -> Dict:
        """Handle email reply event"""
        try:
            # Check if this is a positive reply based on category
            reply_category = webhook_data.get('reply_category', '')
            
            # You might need to configure which categories indicate interest
            interested_categories = ['Interested', 'Meeting Request', 'Information Request']
            
            if reply_category in interested_categories:
                # Update pipeline to "Interested Reply"
                return self._update_pipeline_by_email(
                    webhook_data.get('to_email', ''),
                    'interested_reply'
                )
            
            return {'success': True, 'message': 'Reply processed'}
            
        except Exception as e:
            logger.error(f"Error handling email reply: {e}")
            return {'success': False, 'error': str(e)}
    
    def _handle_category_update(self, webhook_data: Dict) -> Dict:
        """Handle lead category update event"""
        try:
            new_category = webhook_data.get('lead_category', {}).get('new_name', '')
            
            # Check if category is "Booked" or similar
            if new_category.lower() in ['booked', 'meeting booked', 'demo scheduled']:
                return self._update_pipeline_by_email(
                    webhook_data.get('to_email', ''),
                    'booked'
                )
            elif new_category in ['Interested', 'Meeting Request']:
                return self._update_pipeline_by_email(
                    webhook_data.get('to_email', ''),
                    'interested_reply'
                )
            
            return {'success': True, 'message': 'Category update processed'}
            
        except Exception as e:
            logger.error(f"Error handling category update: {e}")
            return {'success': False, 'error': str(e)}
    
    def _update_pipeline_by_email(self, email: str, stage_key: str) -> Dict:
        """Update pipeline stage for a company based on contact email"""
        try:
            if not email:
                return {'success': False, 'error': 'No email provided'}
            
            # Find person by email
            filter_query = {
                "attribute": "email_addresses",
                "relation": "contains",
                "value": email
            }
            people = self.attio.search_records('people', filter_query)
            
            if not people:
                return {'success': False, 'error': 'Person not found'}
            
            person = people[0]
            
            # Get associated company
            companies = person.get('values', {}).get('companies', [])
            if not companies:
                return {'success': False, 'error': 'No company associated'}
            
            company_id = companies[0].get('target_record_id')
            
            # Update pipeline status
            if self._list_id and stage_key in self._status_ids:
                entry = self.attio.get_list_entry(self._list_id, company_id)
                if entry:
                    self.attio.update_list_entry_status(
                        self._list_id,
                        entry['id'],
                        self._status_ids[stage_key]
                    )
                    logger.info(f"Updated company {company_id} to {stage_key} stage")
                    return {'success': True, 'message': f'Pipeline updated to {stage_key}'}
            
            return {'success': False, 'error': 'Could not update pipeline'}
            
        except Exception as e:
            logger.error(f"Error updating pipeline: {e}")
            return {'success': False, 'error': str(e)}
    
    def sync_campaign(self, campaign_id: int, dry_run: bool = False) -> Dict:
        """Sync all leads from a Smartlead campaign to Attio"""
        import requests
        
        try:
            # Get campaign details
            campaign_url = f"https://server.smartlead.ai/api/v1/campaigns/{campaign_id}?api_key={self.smartlead_api_key}"
            campaign_response = requests.get(campaign_url)
            campaign_response.raise_for_status()
            campaign_data = campaign_response.json()
            
            # Get all leads in campaign
            offset = 0
            limit = 100
            total_synced = 0
            errors = []
            
            while True:
                leads_url = f"https://server.smartlead.ai/api/v1/campaigns/{campaign_id}/leads"
                leads_url += f"?api_key={self.smartlead_api_key}&offset={offset}&limit={limit}"
                
                leads_response = requests.get(leads_url)
                leads_response.raise_for_status()
                leads_data = leads_response.json()
                
                leads = leads_data.get('data', [])
                if not leads:
                    break
                
                for lead_data in leads:
                    if dry_run:
                        logger.info(f"[DRY RUN] Would sync: {lead_data.get('lead', {}).get('email', 'Unknown')}")
                    else:
                        result = self.sync_lead_from_campaign(lead_data, campaign_data)
                        if result['success']:
                            total_synced += 1
                        else:
                            errors.append({
                                'email': lead_data.get('lead', {}).get('email', 'Unknown'),
                                'error': result.get('error', 'Unknown error')
                            })
                
                offset += limit
                
                # Check if we've fetched all leads
                if offset >= leads_data.get('total_leads', 0):
                    break
            
            return {
                'success': True,
                'total_synced': total_synced,
                'errors': errors,
                'campaign_name': campaign_data.get('name', 'Unknown')
            }
            
        except Exception as e:
            logger.error(f"Error syncing campaign: {e}")
            return {
                'success': False,
                'error': str(e)
            } 