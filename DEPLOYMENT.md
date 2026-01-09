# RoleSynch Deployment Guide - Google Cloud Run with GitHub Auto-Deploy

This guide walks you through deploying RoleSynch to Google Cloud Run with automatic deployments from GitHub.

## Prerequisites

- Google Cloud account with billing enabled
- GitHub account
- Your Firebase project already set up

## Step 1: Set Up Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or select an existing one
3. Note your **Project ID** (you'll need this later)

### Enable Required APIs

Run these commands in Cloud Shell or with gcloud CLI installed:

```bash
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable secretmanager.googleapis.com
```

## Step 2: Create a Service Account for GitHub Actions

1. Go to **IAM & Admin > Service Accounts**
2. Click **Create Service Account**
3. Name it `github-actions-deploy`
4. Grant these roles:
   - Cloud Run Admin
   - Storage Admin
   - Service Account User
   - Secret Manager Secret Accessor
5. Click **Done**
6. Click on the service account, go to **Keys** tab
7. Click **Add Key > Create new key > JSON**
8. Download the JSON file (keep this safe!)

## Step 3: Store Firebase Service Account in Secret Manager

1. Go to **Security > Secret Manager**
2. Click **Create Secret**
3. Name it `firebase-service-account`
4. Upload your `firebase-service-account.json` file as the secret value
5. Click **Create Secret**

## Step 4: Push Code to GitHub

1. Create a new repository on GitHub
2. Initialize and push your code:

```bash
cd /path/to/workalign
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rolesynch.git
git push -u origin main
```

## Step 5: Add GitHub Secrets

Go to your GitHub repo > **Settings > Secrets and variables > Actions**

Add these secrets:

| Secret Name | Value |
|-------------|-------|
| `GCP_PROJECT_ID` | Your Google Cloud project ID |
| `GCP_SA_KEY` | Entire contents of the service account JSON from Step 2 |
| `FIREBASE_API_KEY` | From your `.env` file |
| `FIREBASE_AUTH_DOMAIN` | From your `.env` file |
| `FIREBASE_PROJECT_ID` | From your `.env` file |
| `FIREBASE_STORAGE_BUCKET` | From your `.env` file |
| `FIREBASE_MESSAGING_SENDER_ID` | From your `.env` file |
| `FIREBASE_APP_ID` | From your `.env` file |
| `ADMIN_SECRET_KEY` | Your admin dashboard password |

## Step 6: Deploy!

Push any change to the `main` branch:

```bash
git add .
git commit -m "Deploy to Cloud Run"
git push origin main
```

GitHub Actions will automatically:
1. Build your Docker image
2. Push it to Google Container Registry
3. Deploy to Cloud Run
4. Output your live URL

## Viewing Your Deployment

- **GitHub**: Go to **Actions** tab to see deployment progress
- **Cloud Run**: Go to Cloud Console > Cloud Run to see your service
- **Logs**: Cloud Run > Your service > Logs

## Your Live URL

After deployment, your app will be available at:
```
https://rolesynch-XXXXX-uc.a.run.app
```

You can also set up a custom domain in Cloud Run settings.

## Cost Controls

The deployment is configured with:
- **Max instances**: 5 (limits scaling)
- **Min instances**: 0 (scales to zero when idle)
- **Memory**: 4GB (needed for ML models)
- **CPU**: 2 cores
- **Timeout**: 300 seconds

### Set Budget Alerts

1. Go to **Billing > Budgets & alerts**
2. Create a budget (e.g., $50/month)
3. Set alert thresholds at 50%, 90%, 100%

## Making Updates

Just push to `main`:

```bash
git add .
git commit -m "Your changes"
git push origin main
```

The new version deploys automatically in ~5-10 minutes.

## Rollback

If something goes wrong:

1. Go to Cloud Run > Your service
2. Click **Revisions**
3. Find a working revision
4. Click the three dots > **Manage Traffic**
5. Set 100% traffic to the working revision

## Troubleshooting

### Build Fails
- Check GitHub Actions logs for error details
- Ensure all secrets are set correctly

### App Crashes
- Check Cloud Run logs for Python errors
- Verify environment variables are set

### Memory Issues
- Increase memory in `.github/workflows/deploy.yml`
- Change `--memory 4Gi` to `--memory 8Gi`

### Slow Cold Starts
- Set `--min-instances 1` to keep one instance warm
- This costs ~$15-30/month extra

## Files Created for Deployment

- `Dockerfile` - Container configuration
- `.dockerignore` - Files to exclude from container
- `.github/workflows/deploy.yml` - Auto-deploy workflow
- `DEPLOYMENT.md` - This guide
