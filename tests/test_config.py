"""
Tests for configuration management.
"""

import pytest
import tempfile
import os
from unittest.mock import patch

from config import Config


class TestConfig:
    """Test Config class."""
    
    def test_default_configuration(self):
        """Test default configuration values."""
        config = Config()
        
        assert config.db_url == 'sqlite:///emails.db'
        assert config.credentials_file == 'credentials.json'
        assert config.token_file == 'token.json'
        assert config.rules_file == 'rules.json'
        assert config.log_level == 'INFO'
        assert config.log_file == 'logs/app.log'
        assert config.max_emails_fetch == 100
        assert config.debug_mode is False
    
    def test_environment_variables(self):
        """Test configuration from environment variables."""
        env_vars = {
            'DB_URL': 'postgresql://test:test@localhost/test',
            'CREDENTIALS_FILE': 'custom_creds.json',
            'TOKEN_FILE': 'custom_token.json',
            'RULES_FILE': 'custom_rules.json',
            'LOG_LEVEL': 'DEBUG',
            'LOG_FILE': 'custom_logs/app.log',
            'MAX_EMAILS_FETCH': '50',
            'DEBUG': 'True'
        }
        
        with patch.dict(os.environ, env_vars):
            config = Config()
            
            assert config.db_url == 'postgresql://test:test@localhost/test'
            assert config.credentials_file == 'custom_creds.json'
            assert config.token_file == 'custom_token.json'
            assert config.rules_file == 'custom_rules.json'
            assert config.log_level == 'DEBUG'
            assert config.log_file == 'custom_logs/app.log'
            assert config.max_emails_fetch == 50
            assert config.debug_mode is True
    
    def test_validate_missing_credentials_file(self):
        """Test validation with missing credentials file."""
        config = Config()
        config.credentials_file = 'nonexistent_credentials.json'
        
        assert config.validate() is False
    
    def test_validate_missing_rules_file(self):
        """Test validation with missing rules file."""
        config = Config()
        config.rules_file = 'nonexistent_rules.json'
        
        assert config.validate() is False
    
    def test_validate_invalid_log_level(self):
        """Test validation with invalid log level."""
        config = Config()
        config.log_level = 'INVALID_LEVEL'
        
        # Create temporary files to avoid other validation errors
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as creds_file:
            config.credentials_file = creds_file.name
            creds_file_path = creds_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as rules_file:
            config.rules_file = rules_file.name
            rules_file_path = rules_file.name
            
        assert config.validate() is False
        
        # Cleanup
        try:
            os.unlink(creds_file_path)
        except (OSError, PermissionError):
            pass
        try:
            os.unlink(rules_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_validate_invalid_max_emails(self):
        """Test validation with invalid max emails count."""
        config = Config()
        config.max_emails_fetch = 0
        
        # Create temporary files to avoid other validation errors
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as creds_file:
            config.credentials_file = creds_file.name
            creds_file_path = creds_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as rules_file:
            config.rules_file = rules_file.name
            rules_file_path = rules_file.name
            
        assert config.validate() is False
        
        # Cleanup
        try:
            os.unlink(creds_file_path)
        except (OSError, PermissionError):
            pass
        try:
            os.unlink(rules_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_validate_success(self):
        """Test successful validation."""
        config = Config()
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as creds_file:
            config.credentials_file = creds_file.name
            creds_file_path = creds_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as rules_file:
            config.rules_file = rules_file.name
            rules_file_path = rules_file.name
            
        with tempfile.TemporaryDirectory() as temp_dir:
            config.log_file = os.path.join(temp_dir, 'app.log')
            
            assert config.validate() is True
        
        # Cleanup
        try:
            os.unlink(creds_file_path)
        except (OSError, PermissionError):
            pass
        try:
            os.unlink(rules_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_validate_creates_log_directory(self):
        """Test that validation creates log directory if it doesn't exist."""
        config = Config()
        
        # Create temporary files
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as creds_file:
            config.credentials_file = creds_file.name
            creds_file_path = creds_file.name
        
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as rules_file:
            config.rules_file = rules_file.name
            rules_file_path = rules_file.name
            
        with tempfile.TemporaryDirectory() as temp_dir:
            log_dir = os.path.join(temp_dir, 'nonexistent', 'logs')
            config.log_file = os.path.join(log_dir, 'app.log')
            
            assert config.validate() is True
            assert os.path.exists(log_dir)
        
        # Cleanup
        try:
            os.unlink(creds_file_path)
        except (OSError, PermissionError):
            pass
        try:
            os.unlink(rules_file_path)
        except (OSError, PermissionError):
            pass
    
    def test_setup_logging(self):
        """Test logging setup."""
        config = Config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config.log_file = os.path.join(temp_dir, 'test.log')
            
            # Setup logging should not raise an exception
            config.setup_logging()
            
            # Verify log file is created after a log message
            import logging
            logger = logging.getLogger('test_logger')
            logger.info('Test log message')
            
            assert os.path.exists(config.log_file)