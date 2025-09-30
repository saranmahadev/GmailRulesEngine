# 🔐 Gmail API Credentials Setup Guide

This guide will walk you through setting up Gmail API credentials for the Gmail Rules Engine project. This is a **required step** before you can use the application.

## 📋 Prerequisites

- Google Account with Gmail access
- Access to Google Cloud Console
- Basic understanding of OAuth 2.0 concepts

## 🎯 Overview

The Gmail Rules Engine uses **OAuth 2.0** authentication to securely access your Gmail account. This setup process involves:

1. Creating a Google Cloud Project
2. Enabling the Gmail API
3. Setting up OAuth 2.0 credentials
4. Configuring the OAuth consent screen
5. Downloading and placing the credentials file

---

## 📝 Step-by-Step Instructions

### **Step 1: Access Google Cloud Console**

1. Open your web browser and go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google Account
3. If this is your first time, accept the terms of service

### **Step 2: Create a New Project**

1. Click on the **project selector** dropdown at the top of the page
2. Click **"New Project"**
3. Enter project details:
   ```
   Project Name: Gmail Rules Engine
   Organization: (leave default or select your organization)
   Location: (leave default)
   ```
4. Click **"Create"**
5. Wait for the project to be created (this may take a few moments)
6. Make sure your new project is selected in the project selector

### **Step 3: Enable Gmail API**

1. In the Google Cloud Console, navigate to **"APIs & Services" > "Library"**
2. Search for **"Gmail API"**
3. Click on **"Gmail API"** from the search results
4. Click the **"Enable"** button
5. Wait for the API to be enabled

### **Step 4: Create OAuth 2.0 Credentials**

1. Navigate to **"APIs & Services" > "Credentials"**
2. Click **"+ Create Credentials"** at the top
3. Select **"OAuth client ID"**

#### **First-time OAuth Setup**

If this is your first time creating OAuth credentials, you'll be prompted to configure the OAuth consent screen:

1. Click **"Configure Consent Screen"**
2. Choose **"External"** (unless you have a Google Workspace account)
3. Click **"Create"**

### **Step 5: Configure OAuth Consent Screen**

#### **OAuth Consent Screen - App Information**

1. Fill in the required fields:
   ```
   App name: Gmail Rules Engine
   User support email: [your-email@gmail.com]
   App logo: (optional - skip for development)
   App domain: (leave blank for development)
   Developer contact information: [your-email@gmail.com]
   ```

2. Click **"Save and Continue"**

#### **OAuth Consent Screen - Scopes**

1. Click **"Add or Remove Scopes"**
2. Search for Gmail scopes and add:
   ```
   https://www.googleapis.com/auth/gmail.modify
   ```
3. Click **"Update"**
4. Click **"Save and Continue"**

#### **OAuth Consent Screen - Test Users**

1. Click **"+ Add Users"**
2. Add your Gmail address as a test user:
   ```
   [your-email@gmail.com]
   ```
3. Click **"Add"**
4. Click **"Save and Continue"**

#### **OAuth Consent Screen - Summary**

1. Review your settings
2. Click **"Back to Dashboard"**

### **Step 6: Create OAuth Client ID**

1. Go back to **"APIs & Services" > "Credentials"**
2. Click **"+ Create Credentials" > "OAuth client ID"**
3. Select **"Desktop application"** as the application type
4. Enter a name:
   ```
   Name: Gmail Rules Engine Desktop Client
   ```
5. Click **"Create"**

### **Step 7: Download Credentials**

1. A dialog will appear with your client ID and secret
2. Click **"Download JSON"**
3. Save the file as `credentials.json`
4. **Important**: Move this file to your project root directory:
   ```
   F:\HappyFox\credentials.json
   ```

---

## 📁 File Placement

Your project structure should look like this:

```
F:\HappyFox\
├── credentials.json          # ← Place downloaded file here
├── main.py
├── gmail_service.py
├── database.py
├── rules_engine.py
├── requirements.txt
└── README.md
```

---

## 🔐 Security Considerations

### **Important Security Notes**

1. **Never commit credentials.json to version control**
   ```bash
   # Add to .gitignore
   echo "credentials.json" >> .gitignore
   echo "token.json" >> .gitignore
   ```

2. **Protect your credentials file**
   - Keep `credentials.json` secure and private
   - Don't share it with others
   - Don't upload it to public repositories

3. **OAuth token storage**
   - The application will create a `token.json` file after first authentication
   - This file contains your access and refresh tokens
   - Keep this file secure as well

### **What Each File Contains**

- **credentials.json**: Contains your OAuth 2.0 client configuration
- **token.json**: Contains access/refresh tokens (created after first auth)

---

## 🧪 Testing Your Setup

### **Step 1: Verify Credentials File**

Check that your `credentials.json` file is correctly formatted:

```bash
# Navigate to your project directory
cd F:\HappyFox

# Check if credentials file exists
dir credentials.json

# Verify JSON format (should show client_id, client_secret, etc.)
type credentials.json
```

### **Step 2: Test Authentication**

Run the fetch command to test authentication:

```bash
# Activate your virtual environment
venv\Scripts\activate

# Install dependencies if not already done
pip install -r requirements.txt

# Test Gmail authentication
python main.py fetch
```

### **Expected Authentication Flow**

1. **First run**: A browser window will open
2. **Google OAuth page**: Sign in with your Google account
3. **Permission prompt**: Grant access to Gmail
4. **Success**: You'll see "Authentication successful" in the terminal
5. **Token storage**: A `token.json` file will be created automatically

---

## 🚨 Troubleshooting

### **Common Issues and Solutions**

#### **Issue 1: "File not found: credentials.json"**

**Solution**:
- Ensure `credentials.json` is in the project root directory
- Check the file name is exactly `credentials.json` (case-sensitive)
- Verify the file is not empty or corrupted

#### **Issue 2: "Invalid client_id"**

**Solution**:
- Re-download `credentials.json` from Google Cloud Console
- Ensure you selected "Desktop application" when creating OAuth client ID
- Check that Gmail API is enabled in your project

#### **Issue 3: "Access blocked: This app's request is invalid"**

**Solution**:
- Verify OAuth consent screen is properly configured
- Add your email as a test user in the consent screen
- Ensure the Gmail API scope is added: `https://www.googleapis.com/auth/gmail.modify`

#### **Issue 4: "The OAuth client was not found"**

**Solution**:
- Make sure your Google Cloud project is selected
- Recreate the OAuth client ID if necessary
- Download a fresh `credentials.json` file

#### **Issue 5: "insufficient_scope" Error**

**Solution**:
- Delete the existing `token.json` file
- Add the correct Gmail scope in OAuth consent screen
- Re-run authentication to get new tokens with proper scopes

#### **Issue 6: Browser doesn't open for authentication**

**Solution**:
- Check if you're running in a headless environment
- Manually copy the authorization URL from the terminal
- Paste it into a browser on a machine with GUI

### **Debug Commands**

```bash
# Check Python environment
python --version

# Verify Google API client installation
python -c "import googleapiclient; print('Google API client installed')"

# Test credentials file format
python -c "import json; print(json.load(open('credentials.json'))['installed']['client_id'])"

# Check if token exists
dir token.json
```

---

## 📚 Additional Resources

### **Google Documentation**

- [Gmail API Overview](https://developers.google.com/gmail/api/guides)
- [OAuth 2.0 for Desktop Apps](https://developers.google.com/identity/protocols/oauth2/native-app)
- [Gmail API Python Quickstart](https://developers.google.com/gmail/api/quickstart/python)

### **Scope Reference**

The application uses the following Gmail API scope:

- **`https://www.googleapis.com/auth/gmail.modify`**
  - Allows reading, composing, and sending messages
  - Allows modifying labels and marking emails as read/unread
  - Required for the rule engine functionality

### **API Quotas and Limits**

- **Daily quota**: 1 billion quota units per day
- **Per-user rate limit**: 250 quota units per user per second
- **Fetch emails**: ~5 quota units per request
- **Modify emails**: ~10-15 quota units per request

For typical usage (100-1000 emails), you won't hit these limits.

---

## ✅ Setup Verification Checklist

Use this checklist to ensure your setup is complete:

- [ ] Google Cloud project created
- [ ] Gmail API enabled in the project
- [ ] OAuth consent screen configured
- [ ] OAuth client ID created (Desktop application)
- [ ] `credentials.json` downloaded and placed in project root
- [ ] Test user (your email) added to OAuth consent screen
- [ ] Gmail API scope added: `https://www.googleapis.com/auth/gmail.modify`
- [ ] File permissions allow reading `credentials.json`
- [ ] Python dependencies installed (`pip install -r requirements.txt`)
- [ ] Authentication test successful (`python main.py fetch`)
- [ ] `token.json` file created after first authentication

---

## 🔄 Credential Maintenance

### **Token Refresh**

- Access tokens expire after 1 hour
- Refresh tokens are valid for 6 months (for test users)
- The application automatically handles token refresh
- Manual refresh is rarely needed

### **Revoking Access**

If you need to revoke access:

1. Go to [Google Account Permissions](https://myaccount.google.com/permissions)
2. Find "Gmail Rules Engine" in the list
3. Click "Remove Access"
4. Delete `token.json` from your project directory

### **Updating Credentials**

If you need to update your OAuth client:

1. Generate new credentials in Google Cloud Console
2. Download the new `credentials.json`
3. Replace the old file
4. Delete `token.json` to force re-authentication
5. Run authentication again

---

**🎉 Congratulations!** 

Once you complete this setup, your Gmail Rules Engine will be able to securely access your Gmail account and perform rule-based operations on your emails.
