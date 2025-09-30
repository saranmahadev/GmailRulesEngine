"""
Tests for Gmail service functionality.
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
import base64

import gmail_service
from gmail_service import GmailService


class TestGmailService:
    """Test GmailService class."""
    
    @pytest.fixture
    def mock_credentials(self):
        """Mock credentials object."""
        creds = Mock()
        creds.valid = True
        creds.expired = False
        creds.refresh_token = 'refresh_token'
        creds.to_json.return_value = '{"token": "test_token"}'
        return creds
    
    @pytest.fixture
    def mock_gmail_service(self):
        """Mock Google API service."""
        service = Mock()
        return service
    
    def test_authenticate_existing_valid_token(self, mock_credentials):
        """Test authentication with existing valid token."""
        with patch('os.path.exists', return_value=True):
            with patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                      return_value=mock_credentials):
                with patch('googleapiclient.discovery.build') as mock_build:
                    with patch('builtins.open', mock_open()):
                        service = GmailService()
                        
                        assert service.credentials is not None
                        assert service.service is not None
                        mock_build.assert_called_once()
    
    def test_authenticate_expired_token_refresh(self, mock_credentials):
        """Test authentication with expired token that gets refreshed."""
        mock_credentials.valid = False
        mock_credentials.expired = True
        
        with patch('os.path.exists', return_value=True):
            with patch('google.oauth2.credentials.Credentials.from_authorized_user_file', 
                      return_value=mock_credentials):
                with patch.object(mock_credentials, 'refresh') as mock_refresh:
                    with patch('googleapiclient.discovery.build') as mock_build:
                        with patch('builtins.open', mock_open()):
                            # After refresh, make it valid
                            mock_refresh.side_effect = lambda x: setattr(mock_credentials, 'valid', True)
                            
                            service = GmailService()
                            
                            mock_refresh.assert_called_once()
                            assert service.credentials is not None
    
    def test_authenticate_no_existing_token(self):
        """Test authentication with no existing token."""
        with patch('os.path.exists', side_effect=lambda x: x == 'credentials.json'):
            with patch('google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file') as mock_flow_class:
                mock_flow = Mock()
                mock_flow.run_local_server.return_value = Mock()
                mock_flow_class.return_value = mock_flow
                
                with patch('googleapiclient.discovery.build') as mock_build:
                    with patch('builtins.open', mock_open()):
                        service = GmailService()
                        
                        mock_flow.run_local_server.assert_called_once()
                        assert service.service is not None
    
    def test_fetch_emails(self, mock_gmail_service, mock_gmail_api_response, mock_gmail_message):
        """Test fetching emails from Gmail."""
        # Mock the API calls
        mock_gmail_service.users().messages().list().execute.return_value = mock_gmail_api_response
        mock_gmail_service.users().messages().get().execute.return_value = mock_gmail_message
        mock_gmail_service.users().labels().list().execute.return_value = {'labels': []}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            emails = service.fetch_emails(max_results=1)
            
            assert len(emails) == 1
            assert emails[0]['gmail_id'] == 'msg_123'
            assert emails[0]['from'] == 'test@example.com'
            assert emails[0]['subject'] == 'Test Email Subject'
    
    def test_extract_email_body_plain_text(self):
        """Test extracting plain text email body."""
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            
            # Test single part message
            payload = {
                'body': {
                    'data': base64.urlsafe_b64encode(b'This is test content').decode()
                }
            }
            
            body = service._extract_email_body(payload)
            assert body == 'This is test content'
    
    def test_extract_email_body_multipart(self):
        """Test extracting multipart email body."""
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            
            payload = {
                'parts': [
                    {
                        'mimeType': 'text/plain',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'Plain text content').decode()
                        }
                    },
                    {
                        'mimeType': 'text/html',
                        'body': {
                            'data': base64.urlsafe_b64encode(b'<p>HTML content</p>').decode()
                        }
                    }
                ]
            }
            
            body = service._extract_email_body(payload)
            assert body == 'Plain text content'
    
    def test_parse_email_date(self):
        """Test parsing email date."""
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            
            # Test valid date
            date_str = 'Mon, 26 Sep 2025 12:00:00 +0000'
            parsed_date = service._parse_email_date(date_str)
            
            assert isinstance(parsed_date, datetime)
            assert parsed_date.year == 2025
            assert parsed_date.month == 9
            assert parsed_date.day == 26
    
    def test_mark_as_read(self, mock_gmail_service):
        """Test marking email as read."""
        mock_gmail_service.users().messages().modify().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.mark_as_read('test_message_id')
            
            assert result is True
            mock_gmail_service.users().messages().modify.assert_called_with(
                userId='me',
                id='test_message_id',
                body={'removeLabelIds': ['UNREAD']}
            )
    
    def test_mark_as_unread(self, mock_gmail_service):
        """Test marking email as unread."""
        mock_gmail_service.users().messages().modify().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.mark_as_unread('test_message_id')
            
            assert result is True
            mock_gmail_service.users().messages().modify.assert_called_with(
                userId='me',
                id='test_message_id',
                body={'addLabelIds': ['UNREAD']}
            )
    
    def test_move_to_label_existing_label(self, mock_gmail_service):
        """Test moving email to existing label."""
        # Mock existing label
        mock_gmail_service.users().labels().list().execute.return_value = {
            'labels': [{'id': 'label_123', 'name': 'Important'}]
        }
        mock_gmail_service.users().messages().modify().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.move_to_label('test_message_id', 'Important')
            
            assert result is True
            mock_gmail_service.users().messages().modify.assert_called_with(
                userId='me',
                id='test_message_id',
                body={'addLabelIds': ['label_123'], 'removeLabelIds': ['INBOX']}
            )
    
    def test_move_to_label_create_new_label(self, mock_gmail_service):
        """Test moving email to new label (creates label)."""
        # Mock no existing labels, then successful label creation
        mock_gmail_service.users().labels().list().execute.return_value = {'labels': []}
        mock_gmail_service.users().labels().create().execute.return_value = {
            'id': 'new_label_123', 'name': 'NewLabel'
        }
        mock_gmail_service.users().messages().modify().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.move_to_label('test_message_id', 'NewLabel')
            
            assert result is True
            mock_gmail_service.users().labels().create.assert_called_with(
                userId='me',
                body={
                    'name': 'NewLabel',
                    'messageListVisibility': 'show',
                    'labelListVisibility': 'labelShow'
                }
            )
            mock_gmail_service.users().messages().modify.assert_called_with(
                userId='me',
                id='test_message_id',
                body={'addLabelIds': ['new_label_123'], 'removeLabelIds': ['INBOX']}
            )
    
    def test_archive_message(self, mock_gmail_service):
        """Test archiving email."""
        mock_gmail_service.users().messages().modify().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.archive_message('test_message_id')
            
            assert result is True
            mock_gmail_service.users().messages().modify.assert_called_with(
                userId='me',
                id='test_message_id',
                body={'removeLabelIds': ['INBOX']}
            )
    
    def test_delete_message(self, mock_gmail_service):
        """Test deleting email."""
        mock_gmail_service.users().messages().trash().execute.return_value = {}
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            result = service.delete_message('test_message_id')
            
            assert result is True
            mock_gmail_service.users().messages().trash.assert_called_with(
                userId='me',
                id='test_message_id'
            )
    
    def test_get_label_names(self, mock_gmail_service):
        """Test converting label IDs to names."""
        mock_gmail_service.users().labels().list().execute.return_value = {
            'labels': [
                {'id': 'INBOX', 'name': 'INBOX'},
                {'id': 'UNREAD', 'name': 'UNREAD'},
                {'id': 'label_123', 'name': 'Important'}
            ]
        }
        
        with patch('gmail_service.GmailService._authenticate'):
            service = GmailService()
            service.service = mock_gmail_service
            
            label_names = service._get_label_names(['INBOX', 'UNREAD', 'label_123'])
            
            assert label_names == ['INBOX', 'UNREAD', 'Important']


def test_create_gmail_service():
    """Test creating Gmail service instance."""
    with patch('gmail_service.GmailService._authenticate'):
        service = gmail_service.create_gmail_service()
        assert isinstance(service, GmailService)