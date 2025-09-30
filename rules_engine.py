"""
Rules engine for processing emails based on JSON-defined rules.
Supports predicate logic and automated actions on Gmail messages.
"""

import json
import logging
import re
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union
from dateutil import parser as date_parser

from database import Email, db_manager
from gmail_service import GmailService

logger = logging.getLogger(__name__)


class RulesPredicate:
    """Predicate evaluation for email field matching."""
    
    @staticmethod
    def contains(field_value: str, test_value: str) -> bool:
        """Check if field contains test value (case-insensitive)."""
        return test_value.lower() in field_value.lower()
    
    @staticmethod
    def equals(field_value: str, test_value: str) -> bool:
        """Check if field equals test value (case-insensitive)."""
        return field_value.lower() == test_value.lower()
    
    @staticmethod
    def does_not_equal(field_value: str, test_value: str) -> bool:
        """Check if field does not equal test value (case-insensitive)."""
        return field_value.lower() != test_value.lower()
    
    @staticmethod
    def does_not_contain(field_value: str, test_value: str) -> bool:
        """Check if field does not contain test value (case-insensitive)."""
        return test_value.lower() not in field_value.lower()
    
    @staticmethod
    def starts_with(field_value: str, test_value: str) -> bool:
        """Check if field starts with test value (case-insensitive)."""
        return field_value.lower().startswith(test_value.lower())
    
    @staticmethod
    def ends_with(field_value: str, test_value: str) -> bool:
        """Check if field ends with test value (case-insensitive)."""
        return field_value.lower().endswith(test_value.lower())
    
    @staticmethod
    def regex_match(field_value: str, pattern: str) -> bool:
        """Check if field matches regex pattern."""
        try:
            return bool(re.search(pattern, field_value, re.IGNORECASE))
        except re.error:
            logger.warning(f"Invalid regex pattern: {pattern}")
            return False


class DatePredicate:
    """Date-specific predicate evaluation."""
    
    @staticmethod
    def less_than_days_ago(received_at: datetime, days: int) -> bool:
        """Check if email was received less than N days ago."""
        # Ensure timezone consistency
        now = datetime.now(timezone.utc) if received_at.tzinfo else datetime.now()
        cutoff_date = now - timedelta(days=days)
        return received_at > cutoff_date
    
    @staticmethod
    def greater_than_days_ago(received_at: datetime, days: int) -> bool:
        """Check if email was received more than N days ago."""
        # Ensure timezone consistency
        now = datetime.now(timezone.utc) if received_at.tzinfo else datetime.now()
        cutoff_date = now - timedelta(days=days)
        return received_at < cutoff_date
    
    @staticmethod
    def equals_date(received_at: datetime, date_str: str) -> bool:
        """Check if email was received on specific date."""
        try:
            target_date = date_parser.parse(date_str).date()
            return received_at.date() == target_date
        except Exception:
            logger.warning(f"Invalid date format: {date_str}")
            return False
    
    @staticmethod
    def before_date(received_at: datetime, date_str: str) -> bool:
        """Check if email was received before specific date."""
        try:
            target_date = date_parser.parse(date_str)
            # Ensure timezone consistency
            if received_at.tzinfo and not target_date.tzinfo:
                target_date = target_date.replace(tzinfo=timezone.utc)
            elif not received_at.tzinfo and target_date.tzinfo:
                target_date = target_date.replace(tzinfo=None)
            return received_at < target_date
        except Exception:
            logger.warning(f"Invalid date format: {date_str}")
            return False
    
    @staticmethod
    def after_date(received_at: datetime, date_str: str) -> bool:
        """Check if email was received after specific date."""
        try:
            target_date = date_parser.parse(date_str)
            # Ensure timezone consistency
            if received_at.tzinfo and not target_date.tzinfo:
                target_date = target_date.replace(tzinfo=timezone.utc)
            elif not received_at.tzinfo and target_date.tzinfo:
                target_date = target_date.replace(tzinfo=None)
            return received_at > target_date
        except Exception:
            logger.warning(f"Invalid date format: {date_str}")
            return False


class RuleEvaluator:
    """Evaluates individual rules against emails."""
    
    def __init__(self):
        """Initialize rule evaluator."""
        self.string_predicates = {
            'contains': RulesPredicate.contains,
            'equals': RulesPredicate.equals,
            'does not equal': RulesPredicate.does_not_equal,
            'does not contain': RulesPredicate.does_not_contain,
            'starts with': RulesPredicate.starts_with,
            'ends with': RulesPredicate.ends_with,
            'matches': RulesPredicate.regex_match,
        }
        
        self.date_predicates = {
            'less than': DatePredicate.less_than_days_ago,
            'greater than': DatePredicate.greater_than_days_ago,
            'equals': DatePredicate.equals_date,
            'before': DatePredicate.before_date,
            'after': DatePredicate.after_date,
        }
    
    def evaluate_rule(self, rule: Dict[str, Any], email: Email) -> bool:
        """
        Evaluate a single rule against an email.
        
        Args:
            rule: Rule dictionary with field, predicate, and value
            email: Email object to evaluate
            
        Returns:
            True if rule matches, False otherwise
        """
        field = rule.get('field', '').lower()
        predicate = rule.get('predicate', '').lower()
        value = rule.get('value', '')
        
        # Get field value from email
        field_value = self._get_email_field_value(email, field)
        if field_value is None:
            return False
        
        # Handle date fields
        if field == 'received_date' or field == 'received_at':
            return self._evaluate_date_predicate(email.received_at, predicate, value)
        
        # Handle string fields
        return self._evaluate_string_predicate(field_value, predicate, value)
    
    def _get_email_field_value(self, email: Email, field: str) -> Optional[str]:
        """
        Get field value from email object.
        
        Args:
            email: Email object
            field: Field name
            
        Returns:
            Field value as string, None if field not found
        """
        field_mapping = {
            'from': email.from_address,
            'to': email.to_address,
            'subject': email.subject,
            'body': email.body or '',
            'message': email.body or '',
            'labels': email.labels or '',
            'received_date': email.received_at,
            'received_at': email.received_at,
        }
        
        return field_mapping.get(field)
    
    def _evaluate_string_predicate(self, field_value: str, predicate: str, test_value: str) -> bool:
        """
        Evaluate string predicate.
        
        Args:
            field_value: Value from email field
            predicate: Predicate type
            test_value: Value to test against
            
        Returns:
            True if predicate matches, False otherwise
        """
        predicate_func = self.string_predicates.get(predicate)
        if not predicate_func:
            logger.warning(f"Unknown string predicate: {predicate}")
            return False
        
        try:
            return predicate_func(field_value, test_value)
        except Exception as e:
            logger.error(f"Error evaluating string predicate: {e}")
            return False
    
    def _evaluate_date_predicate(self, received_at: datetime, predicate: str, value: str) -> bool:
        """
        Evaluate date predicate.
        
        Args:
            received_at: Email received datetime
            predicate: Predicate type
            value: Value to test against
            
        Returns:
            True if predicate matches, False otherwise
        """
        predicate_func = self.date_predicates.get(predicate)
        if not predicate_func:
            logger.warning(f"Unknown date predicate: {predicate}")
            return False
        
        try:
            # Handle numeric values for days
            if predicate in ['less than', 'greater than']:
                days = int(value)
                return predicate_func(received_at, days)
            else:
                return predicate_func(received_at, value)
        except Exception as e:
            logger.error(f"Error evaluating date predicate: {e}")
            return False


class RuleAction:
    """Execute actions on emails based on rules."""
    
    def __init__(self, gmail_service: GmailService):
        """
        Initialize rule actions.
        
        Args:
            gmail_service: Gmail service instance
        """
        self.gmail_service = gmail_service
    
    def execute_action(self, action: str, email: Email) -> bool:
        """
        Execute a single action on an email.
        
        Args:
            action: Action string (e.g., 'mark_as_read', 'move:Important')
            email: Email object
            
        Returns:
            True if action executed successfully, False otherwise
        """
        action = action.strip()
        
        try:
            # Normalize action type but preserve parameters
            action_type = action.split(':')[0].lower() if ':' in action else action.lower()
            
            if action_type == 'mark_as_read' or action_type == 'mark_read':
                success = self.gmail_service.mark_as_read(email.gmail_id)
                if success:
                    db_manager.update_email_status(email.id, is_read=True)
                return success
            
            elif action_type == 'mark_as_unread' or action_type == 'mark_unread':
                success = self.gmail_service.mark_as_unread(email.gmail_id)
                if success:
                    db_manager.update_email_status(email.id, is_read=False)
                return success
            
            elif action_type == 'move':
                label_name = action.split(':', 1)[1].strip()
                return self.gmail_service.move_to_label(email.gmail_id, label_name)
            
            elif action_type == 'archive':
                return self.gmail_service.archive_message(email.gmail_id)
            
            elif action_type == 'delete':
                return self.gmail_service.delete_message(email.gmail_id)
            
            else:
                logger.warning(f"Unknown action: {action}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing action '{action}': {e}")
            return False


class RulesEngine:
    """Main rules engine for processing emails."""
    
    def __init__(self, gmail_service: GmailService):
        """
        Initialize rules engine.
        
        Args:
            gmail_service: Gmail service instance
        """
        self.gmail_service = gmail_service
        self.evaluator = RuleEvaluator()
        self.action_executor = RuleAction(gmail_service)
    
    def load_rules(self, rules_file: str) -> Optional[Dict[str, Any]]:
        """
        Load rules from JSON file.
        
        Args:
            rules_file: Path to rules JSON file
            
        Returns:
            Rules dictionary if loaded successfully, None otherwise
        """
        try:
            with open(rules_file, 'r') as f:
                rules = json.load(f)
            logger.info(f"Loaded rules from {rules_file}")
            return rules
        except FileNotFoundError:
            logger.error(f"Rules file not found: {rules_file}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in rules file: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading rules file: {e}")
            return None
    
    def evaluate_email_against_rules(self, email: Email, rules_config: Dict[str, Any]) -> bool:
        """
        Evaluate if an email matches the rule set.
        
        Args:
            email: Email object to evaluate
            rules_config: Rules configuration dictionary
            
        Returns:
            True if email matches rules, False otherwise
        """
        predicate = rules_config.get('predicate', 'ALL').upper()
        rules = rules_config.get('rules', [])
        
        if not rules:
            return False
        
        rule_results = []
        for rule in rules:
            result = self.evaluator.evaluate_rule(rule, email)
            rule_results.append(result)
            logger.debug(f"Rule evaluation: {rule} -> {result}")
        
        # Apply predicate logic
        if predicate == 'ALL' or predicate == 'AND':
            return all(rule_results)
        elif predicate == 'ANY' or predicate == 'OR':
            return any(rule_results)
        else:
            logger.warning(f"Unknown predicate: {predicate}, defaulting to ALL")
            return all(rule_results)
    
    def apply_rules_to_email(self, email: Email, rules_config: Dict[str, Any]) -> bool:
        """
        Apply rules to a single email.
        
        Args:
            email: Email object
            rules_config: Rules configuration dictionary
            
        Returns:
            True if rules were applied, False otherwise
        """
        # Check if email matches rules
        if not self.evaluate_email_against_rules(email, rules_config):
            return False
        
        # Execute actions
        actions = rules_config.get('actions', [])
        if not actions:
            logger.warning("No actions specified in rules")
            return False
        
        successful_actions = []
        for action in actions:
            if self.action_executor.execute_action(action, email):
                successful_actions.append(action)
            else:
                logger.error(f"Failed to execute action: {action}")
        
        # Log rule application
        if successful_actions:
            rule_id = rules_config.get('id', 'unnamed_rule')
            rule_name = rules_config.get('name', f'Rule {rule_id}')
            
            db_manager.log_rule_applied(
                email_id=email.id,
                rule_id=rule_id,
                rule_name=rule_name,
                actions=successful_actions
            )
            
            logger.info(f"Applied rule '{rule_name}' to email {email.id}")
            return True
        
        return False
    
    def apply_rules_to_emails(self, emails: List[Email], rules_file: str) -> Dict[str, int]:
        """
        Apply rules to multiple emails.
        
        Args:
            emails: List of email objects
            rules_file: Path to rules JSON file
            
        Returns:
            Dictionary with statistics (processed, matched, failed)
        """
        rules_config = self.load_rules(rules_file)
        if not rules_config:
            return {'processed': 0, 'matched': 0, 'failed': 0}
        
        stats = {'processed': 0, 'matched': 0, 'failed': 0}
        
        for email in emails:
            try:
                stats['processed'] += 1
                if self.apply_rules_to_email(email, rules_config):
                    stats['matched'] += 1
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}")
                stats['failed'] += 1
        
        logger.info(f"Rule application complete: {stats}")
        return stats
    
    def apply_multiple_rule_sets(self, emails: List[Email], rule_files: List[str]) -> Dict[str, Any]:
        """
        Apply multiple rule sets to emails.
        
        Args:
            emails: List of email objects
            rule_files: List of paths to rules JSON files
            
        Returns:
            Dictionary with detailed statistics per rule set
        """
        overall_stats = {
            'total_emails': len(emails),
            'total_rule_sets': len(rule_files),
            'rule_set_results': {}
        }
        
        for rule_file in rule_files:
            logger.info(f"Applying rules from {rule_file}")
            stats = self.apply_rules_to_emails(emails, rule_file)
            overall_stats['rule_set_results'][rule_file] = stats
        
        return overall_stats


def create_rules_engine(gmail_service: GmailService) -> RulesEngine:
    """Create and return a new rules engine instance."""
    return RulesEngine(gmail_service)