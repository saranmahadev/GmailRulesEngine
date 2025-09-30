#!/usr/bin/env python3
"""
Setup script for Gmail Rule Engine
Initializes the application and creates necessary configuration files.
"""

import os
import sys
import json
import shutil

def create_directory_structure():
    """Create necessary directories."""
    directories = ['logs', 'tests']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def create_env_file():
    """Create .env file from template if it doesn't exist."""
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print("✅ Created .env file from template")
            print("📝 Please edit .env file with your configuration")
        else:
            print("⚠️  .env.example not found, please create .env manually")
    else:
        print("ℹ️  .env file already exists")

def create_sample_rules():
    """Create sample rules file if it doesn't exist."""
    if not os.path.exists('rules.json'):
        sample_rules = {
            "id": "sample_rule",
            "name": "Sample Email Rule",
            "description": "Mark GitHub notifications as read and move to Important",
            "predicate": "ALL",
            "rules": [
                {
                    "field": "from",
                    "predicate": "contains",
                    "value": "noreply@github.com"
                },
                {
                    "field": "subject",
                    "predicate": "does not contain",
                    "value": "release"
                }
            ],
            "actions": [
                "mark_as_read",
                "move:Important"
            ]
        }
        
        with open('rules.json', 'w') as f:
            json.dump(sample_rules, f, indent=2)
        
        print("✅ Created sample rules.json file")
    else:
        print("ℹ️  rules.json file already exists")

def check_python_version():
    """Check if Python version is compatible."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python version: {sys.version}")

def check_dependencies():
    """Check if required dependencies are installed."""
    # Map package names to their import names
    package_imports = {
        'flask': 'flask',
        'sqlalchemy': 'sqlalchemy',
        'google-api-python-client': 'googleapiclient',
        'python-dotenv': 'dotenv',
        'click': 'click',
        'google-auth-httplib2': 'google.auth.transport.requests',
        'google-auth-oauthlib': 'google_auth_oauthlib'
    }
    
    missing_packages = []
    
    for package_name, import_name in package_imports.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)
    
    if missing_packages:
        print("❌ Missing required packages:")
        for package in missing_packages:
            print(f"   - {package}")
        print("\n🔧 Install missing packages with:")
        print(f"   pip install {' '.join(missing_packages)}")
        return False
    
    print("✅ All required dependencies are installed")
    return True

def display_next_steps():
    """Display next steps for the user."""
    print("\n" + "="*60)
    print("🎉 Gmail Rule Engine Setup Complete!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. 🔐 Set up Google API credentials:")
    print("   - Follow instructions in CREDENTIALS_SETUP.md")
    print("   - Place credentials.json in this directory")
    print()
    print("2. ⚙️  Configure your settings:")
    print("   - Edit .env file with your preferences")
    print("   - Customize rules.json for your email rules")
    print()
    print("3. 🚀 Run the application:")
    print("   - Fetch emails: python main.py fetch")
    print("   - Apply rules: python main.py apply")
    print("   - List emails: python main.py list")
    print("   - View stats: python main.py stats")
    print()
    print("4. 🧪 Run tests:")
    print("   - pytest -v")
    print()
    print("5. 🌐 Start web interface:")
    print("   - python main.py web")
    print()
    print("📚 For more information, see README.md")

def main():
    """Main setup function."""
    print("🔧 Setting up Gmail Rule Engine...")
    print("="*40)
    
    # Check Python version
    check_python_version()
    
    # Create directory structure
    create_directory_structure()
    
    # Create configuration files
    create_env_file()
    create_sample_rules()
    
    # Check dependencies
    dependencies_ok = check_dependencies()
    
    if dependencies_ok:
        display_next_steps()
    else:
        print("\n❌ Setup incomplete due to missing dependencies")
        print("Please install the required packages and run setup again.")
        sys.exit(1)

if __name__ == '__main__':
    main()