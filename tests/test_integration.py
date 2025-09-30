"""
Integration tests for the complete Gmail Rule Engine system.
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from database import DatabaseManager
from gmail_service import GmailService
from rules_engine import RulesEngine
from config import Config


class TestGmailRuleEngineIntegration:
    """Integration tests for the complete system."""
    
    @pytest.fixture
    def integration_setup(self):
        """Set up complete integration test environment."""
        # Create temporary database
        temp_db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        temp_db_file.close()
        
        # Create temporary rules file
        temp_rules_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        rules_config = {
            'id': 'integration_test_rule',
            'name': 'Integration Test Rule',
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
            'actions': ['mark_as_read', 'move:ProcessedEmails']
        }
        json.dump(rules_config, temp_rules_file)
        temp_rules_file.close()
        
        # Create database manager
        db_manager = DatabaseManager(f'sqlite:///{temp_db_file.name}')
        
        # Mock Gmail service
        mock_gmail_service = Mock(spec=GmailService)
        mock_gmail_service.mark_as_read.return_value = True
        mock_gmail_service.move_to_label.return_value = True
        
        # Create rules engine
        rules_engine = RulesEngine(mock_gmail_service)
        
        yield {
            'db_manager': db_manager,
            'gmail_service': mock_gmail_service,
            'rules_engine': rules_engine,
            'rules_file': temp_rules_file.name,
            'db_file': temp_db_file.name
        }
        
        # Cleanup - close file handles and database connections first
        temp_rules_file.close()
        temp_db_file.close()
        if hasattr(db_manager, 'engine') and db_manager.engine:
            db_manager.engine.dispose()
        
        try:
            os.unlink(temp_db_file.name)
        except (OSError, PermissionError):
            pass
        try:
            os.unlink(temp_rules_file.name)
        except (OSError, PermissionError):
            pass
    
    def test_complete_email_processing_workflow(self, integration_setup):
        """Test complete workflow from email storage to rule application."""
        setup = integration_setup
        db_manager = setup['db_manager']
        gmail_service = setup['gmail_service']
        rules_engine = setup['rules_engine']
        rules_file = setup['rules_file']
        
        # Step 1: Save test emails to database
        test_emails = [
            {
                'gmail_id': 'test_email_1',
                'thread_id': 'thread_1',
                'from': 'test@example.com',
                'to': 'user@gmail.com',
                'subject': 'Test Email 1',
                'body': 'This is test email 1',
                'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),
                'is_read': False,
                'labels': '["INBOX", "UNREAD"]'
            },
            {
                'gmail_id': 'test_email_2',
                'thread_id': 'thread_2',
                'from': 'other@example.com',
                'to': 'user@gmail.com',
                'subject': 'Different Subject',
                'body': 'This is test email 2',
                'received_at': datetime(2025, 9, 26, 13, 0, 0, tzinfo=timezone.utc),
                'is_read': False,
                'labels': '["INBOX", "UNREAD"]'
            },
            {
                'gmail_id': 'test_email_3',
                'thread_id': 'thread_3',
                'from': 'test@example.com',
                'to': 'user@gmail.com',
                'subject': 'Test Email 3',
                'body': 'This is test email 3',
                'received_at': datetime(2025, 9, 26, 14, 0, 0, tzinfo=timezone.utc),
                'is_read': False,
                'labels': '["INBOX", "UNREAD"]'
            }
        ]
        
        saved_emails = []
        for email_data in test_emails:
            saved_email = db_manager.save_email(email_data)
            assert saved_email is not None
            saved_emails.append(saved_email)
        
        # Verify emails are saved
        assert db_manager.get_email_count() == 3
        
        # Step 2: Apply rules to emails
        with patch('rules_engine.db_manager', db_manager):
            stats = rules_engine.apply_rules_to_emails(saved_emails, rules_file)
        
        # Step 3: Verify results
        # Should process all 3 emails, but only 2 should match the rules
        # (test@example.com + "Test" in subject)
        assert stats['processed'] == 3
        assert stats['matched'] == 2  # test_email_1 and test_email_3
        assert stats['failed'] == 0
        
        # Verify Gmail service was called correctly
        assert gmail_service.mark_as_read.call_count == 2
        assert gmail_service.move_to_label.call_count == 2
        
        # Verify rule applications were logged
        rules_applied = db_manager.get_rules_for_email(saved_emails[0].id)
        assert len(rules_applied) == 1
        assert rules_applied[0].rule_id == 'integration_test_rule'
    
    def test_email_deduplication(self, integration_setup):
        """Test that duplicate emails are not saved twice."""
        setup = integration_setup
        db_manager = setup['db_manager']
        
        email_data = {
            'gmail_id': 'duplicate_test_email',
            'thread_id': 'thread_1',
            'from': 'test@example.com',
            'to': 'user@gmail.com',
            'subject': 'Duplicate Test Email',
            'body': 'This is a duplicate test',
            'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),
            'is_read': False,
            'labels': '["INBOX", "UNREAD"]'
        }
        
        # Save email first time
        email1 = db_manager.save_email(email_data)
        assert email1 is not None
        assert db_manager.get_email_count() == 1
        
        # Try to save same email again
        email2 = db_manager.save_email(email_data)
        assert email2 is not None
        assert email1.id == email2.id  # Should return same email
        assert db_manager.get_email_count() == 1  # Count should not increase
    
    def test_rules_with_different_predicates(self, integration_setup):
        """Test rules with different predicate logic."""
        setup = integration_setup
        db_manager = setup['db_manager']
        gmail_service = setup['gmail_service']
        rules_engine = setup['rules_engine']
        
        # Create email that matches one rule but not the other
        email_data = {
            'gmail_id': 'partial_match_email',
            'thread_id': 'thread_1',
            'from': 'test@example.com',
            'to': 'user@gmail.com',
            'subject': 'Different Subject',  # Doesn't contain "Test"
            'body': 'This is a test email',
            'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),
            'is_read': False,
            'labels': '["INBOX", "UNREAD"]'
        }
        
        saved_email = db_manager.save_email(email_data)
        
        # Test with ALL predicate (should not match)
        all_rules = {
            'id': 'all_predicate_rule',
            'name': 'ALL Predicate Rule',
            'predicate': 'ALL',
            'rules': [
                {'field': 'from', 'predicate': 'contains', 'value': 'test@example.com'},
                {'field': 'subject', 'predicate': 'contains', 'value': 'Test'}
            ],
            'actions': ['mark_as_read']
        }
        
        result = rules_engine.evaluate_email_against_rules(saved_email, all_rules)
        assert result is False
        
        # Test with ANY predicate (should match)
        any_rules = {
            'id': 'any_predicate_rule',
            'name': 'ANY Predicate Rule',
            'predicate': 'ANY',
            'rules': [
                {'field': 'from', 'predicate': 'contains', 'value': 'test@example.com'},
                {'field': 'subject', 'predicate': 'contains', 'value': 'Test'}
            ],
            'actions': ['mark_as_read']
        }
        
        result = rules_engine.evaluate_email_against_rules(saved_email, any_rules)
        assert result is True
    
    def test_date_based_rules(self, integration_setup):
        """Test rules with date-based conditions."""
        setup = integration_setup
        db_manager = setup['db_manager']
        rules_engine = setup['rules_engine']
        
        # Create email from 10 days ago
        old_email_data = {
            'gmail_id': 'old_email',
            'thread_id': 'thread_1',
            'from': 'test@example.com',
            'to': 'user@gmail.com',
            'subject': 'Old Email',
            'body': 'This is an old email',
            'received_at': datetime(2025, 9, 16, 12, 0, 0, tzinfo=timezone.utc),  # 10 days ago
            'is_read': False,
            'labels': '["INBOX", "UNREAD"]'
        }
        
        # Create recent email
        recent_email_data = {
            'gmail_id': 'recent_email',
            'thread_id': 'thread_2',
            'from': 'test@example.com',
            'to': 'user@gmail.com',
            'subject': 'Recent Email',
            'body': 'This is a recent email',
            'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),  # Today
            'is_read': False,
            'labels': '["INBOX", "UNREAD"]'
        }
        
        old_email = db_manager.save_email(old_email_data)
        recent_email = db_manager.save_email(recent_email_data)
        
        # Rule to match emails less than 7 days old
        date_rules = {
            'id': 'recent_emails_rule',
            'name': 'Recent Emails Rule',
            'predicate': 'ALL',
            'rules': [
                {'field': 'from', 'predicate': 'contains', 'value': 'test@example.com'},
                {'field': 'received_date', 'predicate': 'less than', 'value': '7'}
            ],
            'actions': ['mark_as_read']
        }
        
        # Old email should not match (older than 7 days)
        result = rules_engine.evaluate_email_against_rules(old_email, date_rules)
        assert result is False
        
        # Recent email should match (less than 7 days old)
        result = rules_engine.evaluate_email_against_rules(recent_email, date_rules)
        assert result is True
    
    def test_error_handling_invalid_rules(self, integration_setup):
        """Test error handling with invalid rules."""
        setup = integration_setup
        rules_engine = setup['rules_engine']
        
        # Test loading non-existent rules file
        result = rules_engine.load_rules('nonexistent_file.json')
        assert result is None
        
        # Test applying rules with invalid file
        stats = rules_engine.apply_rules_to_emails([], 'nonexistent_file.json')
        assert stats['processed'] == 0
        assert stats['matched'] == 0
        assert stats['failed'] == 0
    
    def test_action_failure_handling(self, integration_setup):
        """Test handling of action execution failures."""
        setup = integration_setup
        db_manager = setup['db_manager']
        gmail_service = setup['gmail_service']
        rules_engine = setup['rules_engine']
        
        # Make Gmail service fail for certain actions
        gmail_service.mark_as_read.return_value = False  # Fail marking as read
        gmail_service.move_to_label.return_value = True   # Succeed moving
        
        email_data = {
            'gmail_id': 'action_test_email',
            'thread_id': 'thread_1',
            'from': 'test@example.com',
            'to': 'user@gmail.com',
            'subject': 'Test Action Failure',
            'body': 'Testing action failure handling',
            'received_at': datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc),
            'is_read': False,
            'labels': '["INBOX", "UNREAD"]'
        }
        
        saved_email = db_manager.save_email(email_data)
        
        rules_config = {
            'id': 'mixed_success_rule',
            'name': 'Mixed Success Rule',
            'predicate': 'ALL',
            'rules': [
                {'field': 'from', 'predicate': 'contains', 'value': 'test@example.com'}
            ],
            'actions': ['mark_as_read', 'move:TestFolder']
        }
        
        with patch('database.db_manager', db_manager):
            result = rules_engine.apply_rules_to_email(saved_email, rules_config)
        
        # Should still return True because at least one action succeeded
        assert result is True
        
        # Verify that both actions were attempted
        gmail_service.mark_as_read.assert_called_once()
        gmail_service.move_to_label.assert_called_once()