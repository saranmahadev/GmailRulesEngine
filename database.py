"""
Database models and ORM setup for Gmail Rule Engine.
Uses SQLAlchemy for database operations with SQLite by default.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from sqlalchemy.exc import SQLAlchemyError

from config import config

logger = logging.getLogger(__name__)

Base = declarative_base()


class Email(Base):
    """Email model representing stored Gmail messages."""
    
    __tablename__ = 'emails'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    gmail_id = Column(String(255), unique=True, nullable=False, index=True)
    thread_id = Column(String(255), nullable=False)
    from_address = Column(String(255), nullable=False, index=True)
    to_address = Column(Text, nullable=False)
    subject = Column(String(500), nullable=False, index=True)
    body = Column(Text, nullable=True)
    received_at = Column(DateTime, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False)
    labels = Column(Text, nullable=True)  # JSON string of label names
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship to rules applied
    rules_applied = relationship("RuleApplied", back_populates="email", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Email(id={self.id}, from='{self.from_address}', subject='{self.subject[:50]}...')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert email object to dictionary."""
        return {
            'id': self.id,
            'gmail_id': self.gmail_id,
            'thread_id': self.thread_id,
            'from': self.from_address,
            'to': self.to_address,
            'subject': self.subject,
            'body': self.body,
            'received_at': self.received_at.isoformat() if self.received_at else None,
            'is_read': self.is_read,
            'labels': self.labels,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class RuleApplied(Base):
    """Model to track which rules have been applied to which emails."""
    
    __tablename__ = 'rules_applied'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False)
    rule_id = Column(String(255), nullable=False)  # Rule identifier from JSON
    rule_name = Column(String(255), nullable=True)  # Human-readable rule name
    actions_applied = Column(Text, nullable=False)  # JSON string of applied actions
    applied_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    # Relationship to email
    email = relationship("Email", back_populates="rules_applied")
    
    def __repr__(self) -> str:
        return f"<RuleApplied(id={self.id}, email_id={self.email_id}, rule_id='{self.rule_id}')>"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert rule applied object to dictionary."""
        return {
            'id': self.id,
            'email_id': self.email_id,
            'rule_id': self.rule_id,
            'rule_name': self.rule_name,
            'actions_applied': self.actions_applied,
            'applied_at': self.applied_at.isoformat() if self.applied_at else None
        }


class DatabaseManager:
    """Database manager class for handling database operations."""
    
    def __init__(self, db_url: str = None):
        """
        Initialize database manager.
        
        Args:
            db_url: Database URL. If None, uses config.db_url
        """
        self.db_url = db_url or config.db_url
        self.engine = None
        self.session_factory = None
        self._initialize_database()
    
    def _initialize_database(self) -> None:
        """Initialize database connection and create tables."""
        try:
            self.engine = create_engine(
                self.db_url,
                echo=config.debug_mode,
                pool_pre_ping=True
            )
            
            # Create all tables
            Base.metadata.create_all(self.engine)
            
            # Create session factory
            self.session_factory = sessionmaker(bind=self.engine)
            
            logger.info(f"Database initialized successfully: {self.db_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def get_session(self) -> Session:
        """Get a new database session."""
        if not self.session_factory:
            raise RuntimeError("Database not initialized")
        return self.session_factory()
    
    def save_email(self, email_data: Dict[str, Any]) -> Optional[Email]:
        """
        Save email to database.
        
        Args:
            email_data: Dictionary containing email data
            
        Returns:
            Email object if saved successfully, None otherwise
        """
        session = self.get_session()
        try:
            # Check if email already exists
            existing_email = session.query(Email).filter_by(
                gmail_id=email_data['gmail_id']
            ).first()
            
            if existing_email:
                logger.debug(f"Email {email_data['gmail_id']} already exists")
                return existing_email
            
            # Create new email
            email = Email(
                gmail_id=email_data['gmail_id'],
                thread_id=email_data['thread_id'],
                from_address=email_data['from'],
                to_address=email_data['to'],
                subject=email_data['subject'],
                body=email_data.get('body', ''),
                received_at=email_data['received_at'],
                is_read=email_data.get('is_read', False),
                labels=email_data.get('labels', '')
            )
            
            session.add(email)
            session.commit()
            logger.info(f"Saved email: {email.id} from {email.from_address}")
            return email
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to save email: {e}")
            return None
        finally:
            session.close()
    
    def get_emails(self, limit: int = None, offset: int = 0) -> List[Email]:
        """
        Get emails from database.
        
        Args:
            limit: Maximum number of emails to return
            offset: Number of emails to skip
            
        Returns:
            List of Email objects
        """
        session = self.get_session()
        try:
            query = session.query(Email).order_by(Email.received_at.desc())
            
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
                
            return query.all()
        finally:
            session.close()
    
    def get_email_by_gmail_id(self, gmail_id: str) -> Optional[Email]:
        """Get email by Gmail ID."""
        session = self.get_session()
        try:
            return session.query(Email).filter_by(gmail_id=gmail_id).first()
        finally:
            session.close()
    
    def update_email_status(self, email_id: int, is_read: bool) -> bool:
        """
        Update email read status.
        
        Args:
            email_id: Email ID
            is_read: New read status
            
        Returns:
            True if updated successfully, False otherwise
        """
        session = self.get_session()
        try:
            email = session.query(Email).filter_by(id=email_id).first()
            if email:
                email.is_read = is_read
                email.updated_at = datetime.now(timezone.utc)
                session.commit()
                logger.info(f"Updated email {email_id} read status: {is_read}")
                return True
            return False
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to update email status: {e}")
            return False
        finally:
            session.close()
    
    def log_rule_applied(self, email_id: int, rule_id: str, rule_name: str, 
                        actions: List[str]) -> Optional[RuleApplied]:
        """
        Log that a rule has been applied to an email.
        
        Args:
            email_id: Email ID
            rule_id: Rule identifier
            rule_name: Human-readable rule name
            actions: List of actions applied
            
        Returns:
            RuleApplied object if logged successfully, None otherwise
        """
        session = self.get_session()
        try:
            rule_applied = RuleApplied(
                email_id=email_id,
                rule_id=rule_id,
                rule_name=rule_name,
                actions_applied=str(actions)  # Convert to string for storage
            )
            
            session.add(rule_applied)
            session.commit()
            
            # Refresh the object to ensure all attributes are loaded
            session.refresh(rule_applied)
            
            # Create a detached copy to avoid DetachedInstanceError
            detached_rule = RuleApplied(
                email_id=rule_applied.email_id,
                rule_id=rule_applied.rule_id,
                rule_name=rule_applied.rule_name,
                actions_applied=rule_applied.actions_applied,
                applied_at=rule_applied.applied_at
            )
            detached_rule.id = rule_applied.id
            
            logger.info(f"Logged rule '{rule_name}' applied to email {email_id}")
            return detached_rule
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Failed to log rule application: {e}")
            return None
        finally:
            session.close()
    
    def get_rules_for_email(self, email_id: int) -> List[RuleApplied]:
        """Get all rules applied to a specific email."""
        session = self.get_session()
        try:
            return session.query(RuleApplied).filter_by(email_id=email_id).all()
        finally:
            session.close()
    
    def get_email_count(self) -> int:
        """Get total number of emails in database."""
        session = self.get_session()
        try:
            return session.query(Email).count()
        finally:
            session.close()


# Global database manager instance
db_manager = DatabaseManager()