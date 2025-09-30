"""
Tests for database operations and models.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from database import DatabaseManager, Email, RuleApplied


class TestDatabaseManager:
    """Test DatabaseManager class."""
    
    def test_database_initialization(self, temp_db):
        """Test database initialization."""
        assert temp_db.engine is not None
        assert temp_db.session_factory is not None
    
    def test_save_email(self, temp_db, sample_email_data):
        """Test saving email to database."""
        email = temp_db.save_email(sample_email_data)
        
        assert email is not None
        assert email.id is not None
        assert email.gmail_id == sample_email_data['gmail_id']
        assert email.from_address == sample_email_data['from']
        assert email.subject == sample_email_data['subject']
        assert email.is_read == sample_email_data['is_read']
    
    def test_save_duplicate_email(self, temp_db, sample_email_data):
        """Test saving duplicate email (should return existing)."""
        # Save first email
        email1 = temp_db.save_email(sample_email_data)
        
        # Try to save same email again
        email2 = temp_db.save_email(sample_email_data)
        
        assert email1.id == email2.id
        assert email1.gmail_id == email2.gmail_id
    
    def test_get_emails(self, temp_db, sample_email_data):
        """Test retrieving emails from database."""
        # Save test email
        temp_db.save_email(sample_email_data)
        
        # Get emails
        emails = temp_db.get_emails(limit=10)
        
        assert len(emails) == 1
        assert emails[0].gmail_id == sample_email_data['gmail_id']
    
    def test_get_emails_with_limit(self, temp_db, sample_email_data):
        """Test getting emails with limit."""
        # Save multiple emails
        for i in range(5):
            email_data = sample_email_data.copy()
            email_data['gmail_id'] = f'test_email_{i}'
            temp_db.save_email(email_data)
        
        # Get with limit
        emails = temp_db.get_emails(limit=3)
        assert len(emails) == 3
    
    def test_get_email_by_gmail_id(self, temp_db, sample_email_data):
        """Test getting email by Gmail ID."""
        # Save email
        saved_email = temp_db.save_email(sample_email_data)
        
        # Retrieve by Gmail ID
        retrieved_email = temp_db.get_email_by_gmail_id(sample_email_data['gmail_id'])
        
        assert retrieved_email is not None
        assert retrieved_email.id == saved_email.id
        assert retrieved_email.gmail_id == sample_email_data['gmail_id']
    
    def test_get_nonexistent_email(self, temp_db):
        """Test getting non-existent email."""
        email = temp_db.get_email_by_gmail_id('nonexistent_id')
        assert email is None
    
    def test_update_email_status(self, temp_db, sample_email_object):
        """Test updating email read status."""
        # Update to read
        success = temp_db.update_email_status(sample_email_object.id, is_read=True)
        assert success is True
        
        # Verify update
        updated_email = temp_db.get_email_by_gmail_id(sample_email_object.gmail_id)
        assert updated_email.is_read is True
    
    def test_update_nonexistent_email_status(self, temp_db):
        """Test updating non-existent email status."""
        success = temp_db.update_email_status(99999, is_read=True)
        assert success is False
    
    def test_log_rule_applied(self, temp_db, sample_email_object):
        """Test logging rule application."""
        rule_applied = temp_db.log_rule_applied(
            email_id=sample_email_object.id,
            rule_id='test_rule',
            rule_name='Test Rule',
            actions=['mark_as_read', 'archive']
        )
        
        assert rule_applied is not None
        assert rule_applied.email_id == sample_email_object.id
        assert rule_applied.rule_id == 'test_rule'
        assert rule_applied.rule_name == 'Test Rule'
        assert 'mark_as_read' in rule_applied.actions_applied
    
    def test_get_rules_for_email(self, temp_db, sample_email_object):
        """Test getting rules applied to an email."""
        # Log rule application
        temp_db.log_rule_applied(
            email_id=sample_email_object.id,
            rule_id='test_rule',
            rule_name='Test Rule',
            actions=['mark_as_read']
        )
        
        # Get rules
        rules = temp_db.get_rules_for_email(sample_email_object.id)
        
        assert len(rules) == 1
        assert rules[0].rule_id == 'test_rule'
        assert rules[0].email_id == sample_email_object.id
    
    def test_get_email_count(self, temp_db, sample_email_data):
        """Test getting total email count."""
        # Initially should be 0
        assert temp_db.get_email_count() == 0
        
        # Save emails
        for i in range(3):
            email_data = sample_email_data.copy()
            email_data['gmail_id'] = f'test_email_{i}'
            temp_db.save_email(email_data)
        
        # Should now be 3
        assert temp_db.get_email_count() == 3


class TestEmailModel:
    """Test Email model."""
    
    def test_email_repr(self, sample_email_object):
        """Test email string representation."""
        repr_str = repr(sample_email_object)
        assert 'Email' in repr_str
        assert str(sample_email_object.id) in repr_str
        assert sample_email_object.from_address in repr_str
    
    def test_email_to_dict(self, sample_email_object):
        """Test converting email to dictionary."""
        email_dict = sample_email_object.to_dict()
        
        assert isinstance(email_dict, dict)
        assert email_dict['id'] == sample_email_object.id
        assert email_dict['gmail_id'] == sample_email_object.gmail_id
        assert email_dict['from'] == sample_email_object.from_address
        assert email_dict['subject'] == sample_email_object.subject
        assert 'received_at' in email_dict
        assert 'created_at' in email_dict


class TestRuleAppliedModel:
    """Test RuleApplied model."""
    
    def test_rule_applied_repr(self, temp_db, sample_email_object):
        """Test RuleApplied string representation."""
        rule_applied = temp_db.log_rule_applied(
            email_id=sample_email_object.id,
            rule_id='test_rule',
            rule_name='Test Rule',
            actions=['mark_as_read']
        )
        
        repr_str = repr(rule_applied)
        assert 'RuleApplied' in repr_str
        assert str(rule_applied.id) in repr_str
        assert str(sample_email_object.id) in repr_str
    
    def test_rule_applied_to_dict(self, temp_db, sample_email_object):
        """Test converting RuleApplied to dictionary."""
        rule_applied = temp_db.log_rule_applied(
            email_id=sample_email_object.id,
            rule_id='test_rule',
            rule_name='Test Rule',
            actions=['mark_as_read']
        )
        
        rule_dict = rule_applied.to_dict()
        
        assert isinstance(rule_dict, dict)
        assert rule_dict['id'] == rule_applied.id
        assert rule_dict['email_id'] == sample_email_object.id
        assert rule_dict['rule_id'] == 'test_rule'
        assert rule_dict['rule_name'] == 'Test Rule'
        assert 'applied_at' in rule_dict