"""
Tests for rules engine functionality.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

from rules_engine import (
    RulesPredicate, DatePredicate, RuleEvaluator, 
    RuleAction, RulesEngine
)
from database import Email


class TestRulesPredicate:
    """Test RulesPredicate class."""
    
    def test_contains(self):
        """Test contains predicate."""
        assert RulesPredicate.contains("Hello World", "World") is True
        assert RulesPredicate.contains("hello world", "WORLD") is True
        assert RulesPredicate.contains("Hello", "xyz") is False
    
    def test_equals(self):
        """Test equals predicate."""
        assert RulesPredicate.equals("Hello", "hello") is True
        assert RulesPredicate.equals("Hello", "HELLO") is True
        assert RulesPredicate.equals("Hello", "World") is False
    
    def test_does_not_equal(self):
        """Test does not equal predicate."""
        assert RulesPredicate.does_not_equal("Hello", "World") is True
        assert RulesPredicate.does_not_equal("Hello", "hello") is False
    
    def test_does_not_contain(self):
        """Test does not contain predicate."""
        assert RulesPredicate.does_not_contain("Hello", "World") is True
        assert RulesPredicate.does_not_contain("Hello World", "World") is False
    
    def test_starts_with(self):
        """Test starts with predicate."""
        assert RulesPredicate.starts_with("Hello World", "Hello") is True
        assert RulesPredicate.starts_with("hello world", "HELLO") is True
        assert RulesPredicate.starts_with("World Hello", "Hello") is False
    
    def test_ends_with(self):
        """Test ends with predicate."""
        assert RulesPredicate.ends_with("Hello World", "World") is True
        assert RulesPredicate.ends_with("hello world", "WORLD") is True
        assert RulesPredicate.ends_with("World Hello", "World") is False
    
    def test_regex_match(self):
        """Test regex match predicate."""
        assert RulesPredicate.regex_match("test@example.com", r"\w+@\w+\.\w+") is True
        assert RulesPredicate.regex_match("Hello123", r"\d+") is True
        assert RulesPredicate.regex_match("Hello", r"\d+") is False
        
        # Test invalid regex
        assert RulesPredicate.regex_match("test", "[invalid") is False


class TestDatePredicate:
    """Test DatePredicate class."""
    
    def test_less_than_days_ago(self):
        """Test less than days ago predicate."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        assert DatePredicate.less_than_days_ago(yesterday, 3) is True
        assert DatePredicate.less_than_days_ago(week_ago, 3) is False
    
    def test_greater_than_days_ago(self):
        """Test greater than days ago predicate."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        week_ago = now - timedelta(days=7)
        
        assert DatePredicate.greater_than_days_ago(week_ago, 3) is True
        assert DatePredicate.greater_than_days_ago(yesterday, 3) is False
    
    def test_equals_date(self):
        """Test equals date predicate."""
        test_date = datetime(2025, 9, 26, 12, 0, 0)
        
        assert DatePredicate.equals_date(test_date, "2025-09-26") is True
        assert DatePredicate.equals_date(test_date, "2025-09-25") is False
        
        # Test invalid date
        assert DatePredicate.equals_date(test_date, "invalid-date") is False
    
    def test_before_date(self):
        """Test before date predicate."""
        test_date = datetime(2025, 9, 26, 12, 0, 0)
        
        assert DatePredicate.before_date(test_date, "2025-09-27") is True
        assert DatePredicate.before_date(test_date, "2025-09-25") is False
    
    def test_after_date(self):
        """Test after date predicate."""
        test_date = datetime(2025, 9, 26, 12, 0, 0)
        
        assert DatePredicate.after_date(test_date, "2025-09-25") is True
        assert DatePredicate.after_date(test_date, "2025-09-27") is False


class TestRuleEvaluator:
    """Test RuleEvaluator class."""
    
    @pytest.fixture
    def evaluator(self):
        return RuleEvaluator()
    
    @pytest.fixture
    def test_email(self):
        """Create test email object."""
        email = Mock(spec=Email)
        email.id = 1
        email.from_address = "test@example.com"
        email.to_address = "user@gmail.com"
        email.subject = "Test Email Subject"
        email.body = "This is a test email body"
        email.labels = '["INBOX", "UNREAD"]'
        email.received_at = datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
        return email
    
    def test_evaluate_from_field(self, evaluator, test_email):
        """Test evaluating 'from' field."""
        rule = {
            'field': 'from',
            'predicate': 'contains',
            'value': 'test@example.com'
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is True
        
        rule['value'] = 'different@example.com'
        assert evaluator.evaluate_rule(rule, test_email) is False
    
    def test_evaluate_subject_field(self, evaluator, test_email):
        """Test evaluating 'subject' field."""
        rule = {
            'field': 'subject',
            'predicate': 'contains',
            'value': 'Test'
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is True
        
        rule['predicate'] = 'does not contain'
        rule['value'] = 'NonExistent'
        assert evaluator.evaluate_rule(rule, test_email) is True
    
    def test_evaluate_body_field(self, evaluator, test_email):
        """Test evaluating 'body' field."""
        rule = {
            'field': 'body',
            'predicate': 'contains',
            'value': 'test email'
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is True
    
    def test_evaluate_date_field(self, evaluator, test_email):
        """Test evaluating date field."""
        rule = {
            'field': 'received_date',
            'predicate': 'less than',
            'value': '30'  # less than 30 days ago
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is True
        
        rule['predicate'] = 'greater than'
        rule['value'] = '30'  # greater than 30 days ago
        assert evaluator.evaluate_rule(rule, test_email) is False
    
    def test_evaluate_unknown_field(self, evaluator, test_email):
        """Test evaluating unknown field."""
        rule = {
            'field': 'unknown_field',
            'predicate': 'contains',
            'value': 'test'
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is False
    
    def test_evaluate_unknown_predicate(self, evaluator, test_email):
        """Test evaluating unknown predicate."""
        rule = {
            'field': 'from',
            'predicate': 'unknown_predicate',
            'value': 'test'
        }
        
        assert evaluator.evaluate_rule(rule, test_email) is False


class TestRuleAction:
    """Test RuleAction class."""
    
    @pytest.fixture
    def mock_gmail_service(self):
        """Mock Gmail service."""
        service = Mock()
        service.mark_as_read.return_value = True
        service.mark_as_unread.return_value = True
        service.move_to_label.return_value = True
        service.archive_message.return_value = True
        service.delete_message.return_value = True
        return service
    
    @pytest.fixture
    def action_executor(self, mock_gmail_service):
        """Create RuleAction instance."""
        return RuleAction(mock_gmail_service)
    
    @pytest.fixture
    def test_email(self):
        """Create test email object."""
        email = Mock(spec=Email)
        email.id = 1
        email.gmail_id = "test_gmail_id"
        return email
    
    def test_mark_as_read_action(self, action_executor, test_email, mock_gmail_service):
        """Test mark as read action."""
        with patch('database.db_manager.update_email_status', return_value=True):
            result = action_executor.execute_action('mark_as_read', test_email)
            
            assert result is True
            mock_gmail_service.mark_as_read.assert_called_once_with(test_email.gmail_id)
    
    def test_mark_as_unread_action(self, action_executor, test_email, mock_gmail_service):
        """Test mark as unread action."""
        with patch('database.db_manager.update_email_status', return_value=True):
            result = action_executor.execute_action('mark_as_unread', test_email)
            
            assert result is True
            mock_gmail_service.mark_as_unread.assert_called_once_with(test_email.gmail_id)
    
    def test_move_action(self, action_executor, test_email, mock_gmail_service):
        """Test move action."""
        result = action_executor.execute_action('move:Important', test_email)
        
        assert result is True
        mock_gmail_service.move_to_label.assert_called_once_with(test_email.gmail_id, 'Important')
    
    def test_archive_action(self, action_executor, test_email, mock_gmail_service):
        """Test archive action."""
        result = action_executor.execute_action('archive', test_email)
        
        assert result is True
        mock_gmail_service.archive_message.assert_called_once_with(test_email.gmail_id)
    
    def test_delete_action(self, action_executor, test_email, mock_gmail_service):
        """Test delete action."""
        result = action_executor.execute_action('delete', test_email)
        
        assert result is True
        mock_gmail_service.delete_message.assert_called_once_with(test_email.gmail_id)
    
    def test_unknown_action(self, action_executor, test_email):
        """Test unknown action."""
        result = action_executor.execute_action('unknown_action', test_email)
        
        assert result is False


class TestRulesEngine:
    """Test RulesEngine class."""
    
    @pytest.fixture
    def mock_gmail_service(self):
        """Mock Gmail service."""
        service = Mock()
        service.mark_as_read.return_value = True
        return service
    
    @pytest.fixture
    def rules_engine(self, mock_gmail_service):
        """Create RulesEngine instance."""
        return RulesEngine(mock_gmail_service)
    
    @pytest.fixture
    def test_email(self):
        """Create test email object."""
        email = Mock(spec=Email)
        email.id = 1
        email.gmail_id = "test_gmail_id"
        email.from_address = "test@example.com"
        email.to_address = "user@gmail.com"
        email.subject = "Test Email Subject"
        email.body = "This is a test email body"
        email.labels = '["INBOX", "UNREAD"]'
        email.received_at = datetime(2025, 9, 26, 12, 0, 0, tzinfo=timezone.utc)
        return email
    
    def test_load_rules_valid_file(self, rules_engine, sample_rules):
        """Test loading valid rules file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_rules, temp_file)
            temp_file.flush()
            temp_file_path = temp_file.name
            
        loaded_rules = rules_engine.load_rules(temp_file_path)
        
        assert loaded_rules is not None
        assert loaded_rules['id'] == sample_rules['id']
        assert loaded_rules['predicate'] == sample_rules['predicate']
        
        try:
            os.unlink(temp_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_load_rules_nonexistent_file(self, rules_engine):
        """Test loading non-existent rules file."""
        loaded_rules = rules_engine.load_rules('nonexistent.json')
        assert loaded_rules is None
    
    def test_load_rules_invalid_json(self, rules_engine):
        """Test loading invalid JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            temp_file.write('invalid json content')
            temp_file.flush()
            temp_file_path = temp_file.name
            
        loaded_rules = rules_engine.load_rules(temp_file_path)
        assert loaded_rules is None
        
        try:
            os.unlink(temp_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_evaluate_email_all_predicate(self, rules_engine, test_email, sample_rules):
        """Test evaluating email with ALL predicate."""
        # Should match (both rules should pass)
        result = rules_engine.evaluate_email_against_rules(test_email, sample_rules)
        assert result is True
        
        # Modify rule to not match
        sample_rules['rules'][0]['value'] = 'different@example.com'
        result = rules_engine.evaluate_email_against_rules(test_email, sample_rules)
        assert result is False
    
    def test_evaluate_email_any_predicate(self, rules_engine, test_email, sample_rules):
        """Test evaluating email with ANY predicate."""
        sample_rules['predicate'] = 'ANY'
        
        # Should match (first rule passes)
        result = rules_engine.evaluate_email_against_rules(test_email, sample_rules)
        assert result is True
        
        # Make both rules fail
        sample_rules['rules'][0]['value'] = 'different@example.com'
        sample_rules['rules'][1]['value'] = 'Different'
        result = rules_engine.evaluate_email_against_rules(test_email, sample_rules)
        assert result is False
    
    def test_apply_rules_to_email_success(self, rules_engine, test_email, sample_rules, mock_gmail_service):
        """Test applying rules to email successfully."""
        with patch('database.db_manager.log_rule_applied', return_value=Mock()):
            with patch('database.db_manager.update_email_status', return_value=True):
                result = rules_engine.apply_rules_to_email(test_email, sample_rules)
                
                assert result is True
                mock_gmail_service.mark_as_read.assert_called_once()
    
    def test_apply_rules_to_email_no_match(self, rules_engine, test_email, sample_rules):
        """Test applying rules to email that doesn't match."""
        # Make rule not match
        sample_rules['rules'][0]['value'] = 'different@example.com'
        
        result = rules_engine.apply_rules_to_email(test_email, sample_rules)
        assert result is False
    
    def test_apply_rules_to_emails(self, rules_engine, test_email, sample_rules):
        """Test applying rules to multiple emails."""
        emails = [test_email]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp_file:
            json.dump(sample_rules, temp_file)
            temp_file.flush()
            temp_file_path = temp_file.name
            
        with patch('database.db_manager.log_rule_applied', return_value=Mock()):
            with patch('database.db_manager.update_email_status', return_value=True):
                stats = rules_engine.apply_rules_to_emails(emails, temp_file_path)
                
                assert stats['processed'] == 1
                assert stats['matched'] == 1
                assert stats['failed'] == 0
        
        try:
            os.unlink(temp_file_path)
        except (OSError, PermissionError):
            pass