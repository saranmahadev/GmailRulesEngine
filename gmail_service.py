"""
Gmail API service wrapper for fetching emails and performing actions.
Handles OAuth2 authentication, email retrieval, and Gmail operations.
"""

import os
import json
import base64
import logging
import email
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText

import googleapiclient.discovery
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError

from config import config

logger = logging.getLogger(__name__)


class GmailService:
    """Gmail API service wrapper."""
    
    def __init__(self):
        """Initialize Gmail service with authentication."""
        self.service = None
        self.credentials = None
        self._authenticate()
    
    def _authenticate(self) -> None:
        """Authenticate with Gmail API using OAuth2."""
        creds = None
        
        # Load existing token if available
        if os.path.exists(config.token_file):
            try:
                creds = Credentials.from_authorized_user_file(
                    config.token_file, config.scopes
                )
            except Exception as e:
                logger.warning(f"Failed to load existing token: {e}")
        
        # If no valid credentials are available, authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed existing credentials")
                except Exception as e:
                    logger.error(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(config.credentials_file):
                    raise FileNotFoundError(
                        f"Credentials file not found: {config.credentials_file}. "
                        "Please download it from Google Cloud Console."
                    )
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.credentials_file, config.scopes
                )
                creds = flow.run_local_server(port=0)
                logger.info("Completed OAuth2 authentication")
        
        # Save credentials for next run
        with open(config.token_file, 'w') as token:
            token.write(creds.to_json())
        
        # Build Gmail service
        self.credentials = creds
        self.service = googleapiclient.discovery.build(
            'gmail', 'v1', credentials=creds
        )
        logger.info("Gmail service initialized successfully")
    
    def fetch_emails(self, max_results: int = None, query: str = '') -> List[Dict[str, Any]]:
        """
        Fetch emails from Gmail inbox.
        
        Args:
            max_results: Maximum number of emails to fetch
            query: Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')
            
        Returns:
            List of email dictionaries
        """
        if not self.service:
            raise RuntimeError("Gmail service not initialized")
        
        max_results = max_results or config.max_emails_fetch
        emails = []
        
        try:
            # Get list of message IDs
            results = self.service.users().messages().list(
                userId='me',
                maxResults=max_results,
                q=query
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} messages to fetch")
            
            for message in messages:
                try:
                    email_data = self._fetch_email_details(message['id'])
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    logger.error(f"Failed to fetch email {message['id']}: {e}")
                    continue
            
            logger.info(f"Successfully fetched {len(emails)} emails")
            return emails
            
        except HttpError as error:
            logger.error(f"An error occurred while fetching emails: {error}")
            return []
    
    def _fetch_email_details(self, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch detailed information for a specific email.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            Dictionary containing email details
        """
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()
            
            # Extract headers
            headers = {
                header['name'].lower(): header['value']
                for header in message['payload'].get('headers', [])
            }
            
            # Extract body
            body = self._extract_email_body(message['payload'])
            
            # Parse date
            date_str = headers.get('date', '')
            received_at = self._parse_email_date(date_str)
            
            # Check if email is read
            is_read = 'UNREAD' not in message.get('labelIds', [])
            
            # Get labels
            label_ids = message.get('labelIds', [])
            labels = self._get_label_names(label_ids)
            
            email_data = {
                'gmail_id': message_id,
                'thread_id': message.get('threadId', ''),
                'from': headers.get('from', ''),
                'to': headers.get('to', ''),
                'subject': headers.get('subject', ''),
                'body': body,
                'received_at': received_at,
                'is_read': is_read,
                'labels': json.dumps(labels)
            }
            
            return email_data
            
        except HttpError as error:
            logger.error(f"Error fetching email details for {message_id}: {error}")
            return None
    
    def _extract_email_body(self, payload: Dict[str, Any]) -> str:
        """
        Extract email body from message payload.
        
        Args:
            payload: Email payload from Gmail API
            
        Returns:
            Email body text
        """
        body = ''
        
        try:
            # Handle multipart messages
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8')
                    elif part['mimeType'] == 'text/html' and not body:
                        # Use HTML as fallback if no plain text
                        data = part['body'].get('data', '')
                        if data:
                            body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Handle single part messages
            elif payload.get('body', {}).get('data'):
                data = payload['body']['data']
                body = base64.urlsafe_b64decode(data).decode('utf-8')
                
        except Exception as e:
            logger.warning(f"Failed to extract email body: {e}")
            body = ''
        
        return body
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """
        Parse email date string to datetime object.
        
        Args:
            date_str: Date string from email headers
            
        Returns:
            Parsed datetime object
        """
        try:
            # Parse using email.utils for RFC 2822 format
            from email.utils import parsedate_to_datetime
            return parsedate_to_datetime(date_str)
        except Exception as e:
            logger.warning(f"Failed to parse date '{date_str}': {e}")
            return datetime.now(timezone.utc)
    
    def _get_label_names(self, label_ids: List[str]) -> List[str]:
        """
        Convert label IDs to label names.
        
        Args:
            label_ids: List of Gmail label IDs
            
        Returns:
            List of label names
        """
        try:
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            label_map = {label['id']: label['name'] for label in labels}
            return [label_map.get(label_id, label_id) for label_id in label_ids]
            
        except HttpError as error:
            logger.error(f"Error fetching labels: {error}")
            return label_ids
    
    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark email as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked email {message_id} as read")
            return True
        except HttpError as error:
            logger.error(f"Failed to mark email as read: {error}")
            return False
    
    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark email as unread.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"Marked email {message_id} as unread")
            return True
        except HttpError as error:
            logger.error(f"Failed to mark email as unread: {error}")
            return False
    
    def move_to_label(self, message_id: str, label_name: str) -> bool:
        """
        Move email to a specific label/folder.
        
        Args:
            message_id: Gmail message ID
            label_name: Name of the label to move to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get or create label
            label_id = self._get_or_create_label(label_name)
            if not label_id:
                return False
            
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={
                    'addLabelIds': [label_id],
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
            logger.info(f"Moved email {message_id} to label '{label_name}'")
            return True
            
        except HttpError as error:
            logger.error(f"Failed to move email to label: {error}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """
        Get label ID by name, create if it doesn't exist.
        
        Args:
            label_name: Label name
            
        Returns:
            Label ID if successful, None otherwise
        """
        try:
            # Get existing labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])
            
            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']
            
            # Create new label
            label_body = {
                'name': label_name,
                'messageListVisibility': 'show',
                'labelListVisibility': 'labelShow'
            }
            
            created_label = self.service.users().labels().create(
                userId='me',
                body=label_body
            ).execute()
            
            logger.info(f"Created new label: {label_name}")
            return created_label['id']
            
        except HttpError as error:
            logger.error(f"Failed to get or create label: {error}")
            return None
    
    def archive_message(self, message_id: str) -> bool:
        """
        Archive email (remove from inbox).
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['INBOX']}
            ).execute()
            logger.info(f"Archived email {message_id}")
            return True
        except HttpError as error:
            logger.error(f"Failed to archive email: {error}")
            return False
    
    def delete_message(self, message_id: str) -> bool:
        """
        Delete email (move to trash).
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.service.users().messages().trash(
                userId='me',
                id=message_id
            ).execute()
            logger.info(f"Deleted email {message_id}")
            return True
        except HttpError as error:
            logger.error(f"Failed to delete email: {error}")
            return False


# Helper function to create Gmail service instance
def create_gmail_service() -> GmailService:
    """Create and return a new Gmail service instance."""
    return GmailService()