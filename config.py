"""
Configuration management for Gmail Rule Engine.
Handles environment variables, database settings, and application configuration.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv


class Config:
    """Application configuration class."""
    
    def __init__(self):
        """Initialize configuration by loading environment variables."""
        # Load .env file if it exists
        load_dotenv()
        
        # Database configuration
        self.db_url = os.getenv('DB_URL', 'sqlite:///emails.db')
        
        # Gmail API configuration
        self.credentials_file = os.getenv('CREDENTIALS_FILE', 'credentials.json')
        self.token_file = os.getenv('TOKEN_FILE', 'token.json')
        self.scopes = ['https://www.googleapis.com/auth/gmail.modify']
        
        # Rules configuration
        self.rules_file = os.getenv('RULES_FILE', 'rules.json')
        
        # Logging configuration
        self.log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.log_file = os.getenv('LOG_FILE', 'logs/app.log')
        self.log_format = '%(levelname)s [%(asctime)s] %(message)s'
        self.log_date_format = '%Y-%m-%d %H:%M:%S'
        
        # Application settings
        self.max_emails_fetch = int(os.getenv('MAX_EMAILS_FETCH', '100'))
        self.debug_mode = os.getenv('DEBUG', 'False').lower() == 'true'
        
    def validate(self) -> bool:
        """
        Validate configuration settings.
        
        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        errors = []
        
        # Check if credentials file exists
        if not os.path.exists(self.credentials_file):
            errors.append(f"Credentials file not found: {self.credentials_file}")
        
        # Check if rules file exists
        if not os.path.exists(self.rules_file):
            errors.append(f"Rules file not found: {self.rules_file}")
        
        # Validate log level
        valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if self.log_level not in valid_log_levels:
            errors.append(f"Invalid log level: {self.log_level}")
        
        # Validate max emails fetch count
        if self.max_emails_fetch <= 0:
            errors.append("MAX_EMAILS_FETCH must be greater than 0")
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(self.log_file)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir, exist_ok=True)
            except OSError as e:
                errors.append(f"Cannot create log directory: {e}")
        
        if errors:
            for error in errors:
                print(f"Configuration Error: {error}")
            return False
        
        return True
    
    def setup_logging(self) -> None:
        """Setup logging configuration."""
        logging.basicConfig(
            level=getattr(logging, self.log_level),
            format=self.log_format,
            datefmt=self.log_date_format,
            handlers=[
                logging.FileHandler(self.log_file),
                logging.StreamHandler()
            ]
        )
        
        # Set specific loggers to WARNING level to reduce noise
        logging.getLogger('googleapiclient.discovery').setLevel(logging.WARNING)
        logging.getLogger('google.auth.transport').setLevel(logging.WARNING)
        logging.getLogger('urllib3.connectionpool').setLevel(logging.WARNING)


# Global configuration instance
config = Config()