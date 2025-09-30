"""
Main application entry point for Gmail Rule Engine.
Provides CLI commands for fetching emails and applying rules.
"""

import sys
import logging
from typing import Optional

import click
from flask import Flask

from config import config
from database import db_manager, Email, RuleApplied
from gmail_service import create_gmail_service, GmailService
from rules_engine import create_rules_engine, RulesEngine

# Initialize Flask app for potential web interface
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = config.db_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

logger = logging.getLogger(__name__)


def initialize_application() -> bool:
    """
    Initialize application components.
    
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Setup logging
        config.setup_logging()
        logger.info("Starting Gmail Rule Engine")
        
        # Validate configuration
        if not config.validate():
            logger.error("Configuration validation failed")
            return False
        
        logger.info("Application initialized successfully")
        return True
        
    except Exception as e:
        print(f"Failed to initialize application: {e}")
        return False


@click.group()
def cli():
    """Gmail Rule Engine - Automated email processing with rules."""
    if not initialize_application():
        sys.exit(1)


@cli.command()
@click.option('--max-results', '-m', type=int, help='Maximum number of emails to fetch')
@click.option('--query', '-q', default='', help='Gmail search query (e.g., "is:unread")')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompts')
def fetch(max_results: Optional[int], query: str, force: bool):
    """Fetch emails from Gmail and store in database."""
    try:
        logger.info("Starting email fetch operation")
        
        # Initialize Gmail service
        gmail_service = create_gmail_service()
        
        # Confirm operation if not forced
        if not force:
            max_results = max_results or config.max_emails_fetch
            click.echo(f"About to fetch up to {max_results} emails with query: '{query}'")
            if not click.confirm('Continue?'):
                click.echo("Operation cancelled.")
                return
        
        # Fetch emails
        click.echo("Fetching emails from Gmail...")
        emails_data = gmail_service.fetch_emails(max_results=max_results, query=query)
        
        if not emails_data:
            click.echo("No emails found to fetch.")
            return
        
        click.echo(f"Found {len(emails_data)} emails. Saving to database...")
        
        # Save emails to database
        saved_count = 0
        skipped_count = 0
        
        with click.progressbar(emails_data, label='Saving emails') as emails:
            for email_data in emails:
                saved_email = db_manager.save_email(email_data)
                if saved_email:
                    if saved_email.created_at == saved_email.updated_at:
                        saved_count += 1
                    else:
                        skipped_count += 1
        
        click.echo(f"\n✅ Email fetch completed!")
        click.echo(f"   📧 New emails saved: {saved_count}")
        click.echo(f"   ⏭️  Emails skipped (already existed): {skipped_count}")
        click.echo(f"   📊 Total emails in database: {db_manager.get_email_count()}")
        
    except KeyboardInterrupt:
        click.echo("\n❌ Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error during fetch operation: {e}")
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


@cli.command()
@click.option('--rules', '-r', type=click.Path(exists=True), help='Path to rules JSON file')
@click.option('--limit', '-l', type=int, help='Limit number of emails to process')
@click.option('--offset', type=int, default=0, help='Skip this many emails')
@click.option('--dry-run', '-d', is_flag=True, help='Preview actions without executing them')
@click.option('--force', '-f', is_flag=True, help='Skip confirmation prompts')
def apply(rules: Optional[str], limit: Optional[int], offset: int, dry_run: bool, force: bool):
    """Apply rules from JSON file to stored emails."""
    try:
        logger.info("Starting rule application")
        
        # Use default rules file if not specified
        rules_file = rules or config.rules_file
        
        # Get emails from database
        emails = db_manager.get_emails(limit=limit, offset=offset)
        
        if not emails:
            click.echo("No emails found in database.")
            click.echo("Run 'python main.py fetch' first to fetch emails.")
            return
        
        # Confirm operation if not forced
        if not force:
            click.echo(f"About to apply rules from '{rules_file}' to {len(emails)} emails")
            if dry_run:
                click.echo("🔍 DRY RUN MODE: No actions will be executed")
            if not click.confirm('Continue?'):
                click.echo("Operation cancelled.")
                return
        
        if dry_run:
            click.echo("🔍 DRY RUN MODE - Previewing rule matches...")
            _preview_rules(emails, rules_file)
        else:
            # Initialize services
            gmail_service = create_gmail_service()
            rules_engine = create_rules_engine(gmail_service)
            
            # Apply rules
            click.echo(f"Applying rules to {len(emails)} emails...")
            stats = rules_engine.apply_rules_to_emails(emails, rules_file)
            
            click.echo(f"\n✅ Rule application completed!")
            click.echo(f"   📧 Emails processed: {stats['processed']}")
            click.echo(f"   ✅ Emails matched rules: {stats['matched']}")
            click.echo(f"   ❌ Emails failed processing: {stats['failed']}")
        
    except KeyboardInterrupt:
        click.echo("\n❌ Operation cancelled by user.")
    except Exception as e:
        logger.error(f"Error during rule application: {e}")
        click.echo(f"❌ Error: {e}")
        sys.exit(1)


def _preview_rules(emails: list[Email], rules_file: str):
    """Preview which emails would match rules without executing actions."""
    # Create a dummy Gmail service for rule evaluation
    rules_engine = create_rules_engine(None)
    rules_config = rules_engine.load_rules(rules_file)
    
    if not rules_config:
        click.echo("❌ Failed to load rules file")
        return
    
    matched_count = 0
    
    for email in emails:
        if rules_engine.evaluate_email_against_rules(email, rules_config):
            matched_count += 1
            click.echo(f"✅ MATCH: {email.from_address} - {email.subject[:50]}...")
    
    click.echo(f"\n📊 Preview Results:")
    click.echo(f"   📧 Total emails: {len(emails)}")
    click.echo(f"   ✅ Emails that would match: {matched_count}")
    click.echo(f"   ⏭️  Emails that would be skipped: {len(emails) - matched_count}")


@cli.command()
@click.option('--limit', '-l', type=int, default=10, help='Number of emails to show')
def list(limit: int):
    """List emails in the database."""
    try:
        emails = db_manager.get_emails(limit=limit)
        
        if not emails:
            click.echo("No emails found in database.")
            return
        
        click.echo(f"📧 Latest {len(emails)} emails:")
        click.echo("─" * 80)
        
        for email in emails:
            status = "📖" if email.is_read else "📩"
            received = email.received_at.strftime("%Y-%m-%d %H:%M")
            click.echo(f"{status} {received} | {email.from_address}")
            click.echo(f"    Subject: {email.subject}")
            
            # Show applied rules if any
            rules_applied = db_manager.get_rules_for_email(email.id)
            if rules_applied:
                rule_names = [rule.rule_name for rule in rules_applied]
                click.echo(f"    Rules: {', '.join(rule_names)}")
            
            click.echo()
        
        total_count = db_manager.get_email_count()
        click.echo(f"📊 Total emails in database: {total_count}")
        
    except Exception as e:
        logger.error(f"Error listing emails: {e}")
        click.echo(f"❌ Error: {e}")


@cli.command()
def stats():
    """Show database statistics."""
    try:
        total_emails = db_manager.get_email_count()
        
        # Get read/unread counts
        session = db_manager.get_session()
        try:
            read_count = session.query(Email).filter_by(is_read=True).count()
            unread_count = session.query(Email).filter_by(is_read=False).count()
        finally:
            session.close()
        
        click.echo("📊 Gmail Rule Engine Statistics")
        click.echo("─" * 40)
        click.echo(f"📧 Total emails: {total_emails}")
        click.echo(f"📖 Read emails: {read_count}")
        click.echo(f"📩 Unread emails: {unread_count}")
        click.echo(f"📁 Database: {config.db_url}")
        click.echo(f"📜 Rules file: {config.rules_file}")
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        click.echo(f"❌ Error: {e}")


@cli.command()
@click.confirmation_option(prompt='Are you sure you want to clear all data?')
def clear():
    """Clear all emails from database."""
    try:
        session = db_manager.get_session()
        try:
            # Delete all rule applications first (foreign key constraint)
            session.query(RuleApplied).delete()
            
            # Delete all emails
            count = session.query(Email).count()
            session.query(Email).delete()
            session.commit()
            
            click.echo(f"✅ Cleared {count} emails from database.")
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Error clearing database: {e}")
        click.echo(f"❌ Error: {e}")


# Flask routes for potential web interface
@app.route('/')
def index():
    """Basic status page."""
    total_emails = db_manager.get_email_count()
    return {
        'status': 'Gmail Rule Engine Running',
        'total_emails': total_emails,
        'database': config.db_url,
        'rules_file': config.rules_file
    }


@app.route('/emails')
def get_emails():
    """Get emails as JSON."""
    emails = db_manager.get_emails(limit=50)
    return {
        'emails': [email.to_dict() for email in emails],
        'total_count': db_manager.get_email_count()
    }


def run_web_server(host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
    """Run the Flask web server."""
    if not initialize_application():
        sys.exit(1)
    
    click.echo(f"🌐 Starting web server on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)


@cli.command()
@click.option('--host', default='127.0.0.1', help='Host to bind to')
@click.option('--port', default=5000, type=int, help='Port to bind to')
@click.option('--debug', is_flag=True, help='Enable debug mode')
def web(host: str, port: int, debug: bool):
    """Start web interface."""
    run_web_server(host, port, debug)


if __name__ == '__main__':
    cli()