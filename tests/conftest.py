"""
Test configuration and fixtures for Gmail Rule Engine tests.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from database import DatabaseManager, Email, RuleApplied
from gmail_service import GmailService
from rules_engine import RulesEngine
from config import Config


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_file:
        temp_db_url = f'sqlite:///{temp_file.name}'
        temp_file_path = temp_file.name
    
    db_manager = DatabaseManager(temp_db_url)
    try:
        yield db_manager
    finally:
        # Cleanup - close database connections first
        if hasattr(db_manager, 'engine') and db_manager.engine:
            db_manager.engine.dispose()
        try:
            os.unlink(temp_file_path)
        except (OSError, PermissionError):
            pass  # Ignore cleanup errors on Windows


@pytest.fixture
def sample_email_data():
    """Sample email data for testing."""
    return {
        'gmail_id': 'test_email_123',
        'thread_id': 'test_thread_456',
        'from': 'test@example.com',
        'to': 'user@gmail.com',
        'subject': 'Test Email Subject',
        'body': 'This is a test email body content.',
        'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),
        'is_read': False,
        'labels': '["INBOX", "UNREAD"]'
    }


@pytest.fixture
def sample_email_object(temp_db, sample_email_data):
    """Create a sample email object in the database."""
    email = temp_db.save_email(sample_email_data)
    return email


@pytest.fixture
def sample_rules():
    """Sample rules configuration for testing."""
    return {
        'id': 'test_rule',
        'name': 'Test Rule',
        'predicate': 'ALL',
        'rules': [
            {
                'field': 'from',
                'predicate': 'contains',
                'value': 'test@example.com'
            },
            {
                'field': 'subject',
                'predicate': 'contains',
                'value': 'Test'
            }
        ],
        'actions': ['mark_as_read']
    }


@pytest.fixture
def mock_gmail_service():
    """Mock Gmail service for testing."""
    service = Mock(spec=GmailService)
    service.mark_as_read.return_value = True
    service.mark_as_unread.return_value = True
    service.move_to_label.return_value = True
    service.archive_message.return_value = True
    service.delete_message.return_value = True
    return service


@pytest.fixture
def mock_gmail_api_response():
    """Mock Gmail API response data."""
    return {
        'messages': [
            {
                'id': 'msg_123',
                'threadId': 'thread_456'
            }
        ]
    }


@pytest.fixture
def mock_gmail_message():
    """Mock Gmail message details."""
    return {
        'id': 'msg_123',
        'threadId': 'thread_456',
        'labelIds': ['INBOX', 'UNREAD'],
        'payload': {
            'headers': [
                {'name': 'From', 'value': 'test@example.com'},
                {'name': 'To', 'value': 'user@gmail.com'},
                {'name': 'Subject', 'value': 'Test Email Subject'},
                {'name': 'Date', 'value': 'Mon, 26 Sep 2025 12:00:00 +0000'}
            ],
            'body': {
                'data': 'VGhpcyBpcyBhIHRlc3QgZW1haWwgYm9keSBjb250ZW50Lg=='  # base64 encoded
            }
        }
    }


@pytest.fixture
def temp_rules_file(temp_dir, sample_rules):
    """Create a temporary rules file."""
    import json
    rules_file = os.path.join(temp_dir, 'test_rules.json')
    with open(rules_file, 'w') as f:
        json.dump(sample_rules, f)
    return rules_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def test_config(temp_dir):
    """Create test configuration."""
    config = Config()
    config.db_url = f'sqlite:///{os.path.join(temp_dir, "test.db")}'
    config.rules_file = os.path.join(temp_dir, 'rules.json')
    config.credentials_file = os.path.join(temp_dir, 'credentials.json')
    config.token_file = os.path.join(temp_dir, 'token.json')
    config.log_file = os.path.join(temp_dir, 'test.log')
    return config