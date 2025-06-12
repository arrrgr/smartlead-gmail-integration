"""
Attio API Client for managing CRM operations
"""
import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class AttioClient:
    def __init__(self, api_key: str):
        """Initialize Attio client with API key"""
        self.api_key = api_key
        self.base_url = "https://api.attio.com/v2"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Cache for object and attribute IDs
        self._cache = {
            'objects': {},
            'attributes': {},
            'lists': {},
            'statuses': {}
        }
    
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Make API request to Attio"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data
            )
            response.raise_for_status()
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Attio API error: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
    
    def get_object(self, object_slug: str) -> Dict:
        """Get object definition by slug (e.g., 'companies', 'people')"""
        if object_slug not in self._cache['objects']:
            result = self._make_request('GET', f'/objects/{object_slug}')
            self._cache['objects'][object_slug] = result['data']
        return self._cache['objects'][object_slug]
    
    def get_attribute(self, object_slug: str, attribute_slug: str) -> Dict:
        """Get attribute definition"""
        cache_key = f"{object_slug}:{attribute_slug}"
        if cache_key not in self._cache['attributes']:
            result = self._make_request('GET', f'/objects/{object_slug}/attributes/{attribute_slug}')
            self._cache['attributes'][cache_key] = result['data']
        return self._cache['attributes'][cache_key]
    
    def search_records(self, object_slug: str, filter_query: Dict) -> List[Dict]:
        """Search for records using filter"""
        data = {
            "filter": filter_query,
            "sorts": []
        }
        result = self._make_request('POST', f'/objects/{object_slug}/records/query', data)
        return result.get('data', [])
    
    def create_record(self, object_slug: str, values: Dict) -> Dict:
        """Create a new record"""
        data = {"data": {"values": values}}
        result = self._make_request('POST', f'/objects/{object_slug}/records', data)
        return result['data']
    
    def update_record(self, object_slug: str, record_id: str, values: Dict) -> Dict:
        """Update an existing record"""
        data = {"data": {"values": values}}
        result = self._make_request('PATCH', f'/objects/{object_slug}/records/{record_id}', data)
        return result['data']
    
    def get_or_create_company(self, company_data: Dict) -> Dict:
        """Get existing company or create new one"""
        # Search by domain or name
        domain = company_data.get('website', '').replace('http://', '').replace('https://', '').replace('www.', '')
        
        if domain:
            # Search by domain first
            filter_query = {
                "or": [
                    {
                        "attribute": "domains",
                        "relation": "contains",
                        "value": domain
                    }
                ]
            }
            existing = self.search_records('companies', filter_query)
            if existing:
                return existing[0]
        
        # Search by name if no domain match
        if company_data.get('name'):
            filter_query = {
                "attribute": "name",
                "relation": "eq",
                "value": company_data['name']
            }
            existing = self.search_records('companies', filter_query)
            if existing:
                return existing[0]
        
        # Create new company
        values = {
            "name": [{"value": company_data.get('name', 'Unknown Company')}]
        }
        
        if domain:
            values["domains"] = [{"domain": domain}]
        
        return self.create_record('companies', values)
    
    def get_or_create_person(self, person_data: Dict, company_id: Optional[str] = None) -> Dict:
        """Get existing person or create new one"""
        email = person_data.get('email', '').lower()
        
        if email:
            # Search by email
            filter_query = {
                "attribute": "email_addresses",
                "relation": "contains",
                "value": email
            }
            existing = self.search_records('people', filter_query)
            if existing:
                return existing[0]
        
        # Create new person
        values = {
            "name": [{"value": f"{person_data.get('first_name', '')} {person_data.get('last_name', '')}".strip() or email}]
        }
        
        if email:
            values["email_addresses"] = [{"email_address": email}]
        
        if person_data.get('phone_number'):
            values["phone_numbers"] = [{"phone_number": person_data['phone_number']}]
        
        if company_id:
            values["companies"] = [{"target_object": "companies", "target_record_id": company_id}]
        
        return self.create_record('people', values)
    
    def get_list(self, list_name: str) -> Optional[Dict]:
        """Get list by name"""
        if list_name not in self._cache['lists']:
            # Get all lists
            result = self._make_request('GET', '/lists')
            for list_item in result.get('data', []):
                self._cache['lists'][list_item['name']] = list_item
        
        return self._cache['lists'].get(list_name)
    
    def add_record_to_list(self, list_id: str, record_id: str, object_slug: str = 'companies') -> Dict:
        """Add a record to a list"""
        data = {
            "data": {
                "entries": [
                    {
                        "target_object": object_slug,
                        "target_record_id": record_id
                    }
                ]
            }
        }
        return self._make_request('POST', f'/lists/{list_id}/entries', data)
    
    def get_list_entry(self, list_id: str, record_id: str) -> Optional[Dict]:
        """Get a specific entry from a list"""
        result = self._make_request('GET', f'/lists/{list_id}/entries')
        for entry in result.get('data', []):
            if entry.get('target_record_id') == record_id:
                return entry
        return None
    
    def update_list_entry_status(self, list_id: str, entry_id: str, status_id: str) -> Dict:
        """Update the status of a list entry"""
        data = {
            "data": {
                "values": {
                    "status": [{"status_id": status_id}]
                }
            }
        }
        return self._make_request('PATCH', f'/lists/{list_id}/entries/{entry_id}', data)
    
    def get_status_by_name(self, list_id: str, status_name: str) -> Optional[str]:
        """Get status ID by name for a specific list"""
        cache_key = f"{list_id}:{status_name}"
        if cache_key not in self._cache['statuses']:
            # Get list details including statuses
            result = self._make_request('GET', f'/lists/{list_id}')
            list_data = result.get('data', {})
            
            # Find status attribute
            for attr in list_data.get('attributes', []):
                if attr.get('type') == 'status':
                    for option in attr.get('config', {}).get('options', []):
                        status_cache_key = f"{list_id}:{option['title']}"
                        self._cache['statuses'][status_cache_key] = option['id']
        
        return self._cache['statuses'].get(cache_key)
    
    def update_record_attribute(self, object_slug: str, record_id: str, attribute_slug: str, value: Any) -> Dict:
        """Update a specific attribute of a record"""
        values = {attribute_slug: [{"value": value}]}
        return self.update_record(object_slug, record_id, values)
    
    def add_note(self, record_id: str, parent_object: str, title: str, content: str) -> Dict:
        """Add a note to a record"""
        data = {
            "data": {
                "parent_object": parent_object,
                "parent_record_id": record_id,
                "title": title,
                "content": content,
                "format": "plaintext"
            }
        }
        return self._make_request('POST', '/notes', data) 