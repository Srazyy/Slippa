# YouTube Upload Setup Guide

To upload clips to YouTube, you need to set up Google API credentials. This is a **one-time setup**.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click **"Select a project"** → **"New Project"**
3. Name it something like "Slippa" and click **Create**

## Step 2: Enable YouTube Data API

1. In the sidebar, go to **APIs & Services** → **Library**
2. Search for **"YouTube Data API v3"**
3. Click on it and press **Enable**

## Step 3: Create OAuth Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **"+ Create Credentials"** → **"OAuth client ID"**
3. If asked to configure consent screen:
   - Choose **External**
   - Fill in app name ("Slippa"), user support email
   - Add your email under test users
   - Save
4. Back in Credentials, create OAuth client ID:
   - Application type: **Web application**
   - Name: "Slippa"
   - Authorized redirect URIs: add `http://localhost:5000/oauth/callback`
   - Click **Create**
5. Click **"Download JSON"** on the created credential

## Step 4: Place the File

1. Rename the downloaded file to `client_secrets.json`
2. Place it in the **Slippa root folder** (same level as `requirements.txt`)

```
Slippa/
├── client_secrets.json  ← here
├── requirements.txt
├── slippa/
└── ...
```

## Step 5: Connect Your Account

1. Start Slippa: `python -m slippa`
2. After generating clips, click **"📤 Upload to YouTube"** on any clip
3. You'll be redirected to Google login — grant permission
4. Done! A `token.json` is saved so you won't need to log in again

## Notes

- Uploads default to **private** — nothing goes public unless you change it
- YouTube API has a daily quota (~6 uploads/day for a personal project)
- `client_secrets.json` and `token.json` are in `.gitignore` — they won't be committed
