# Adding SMTP Password as Secret in Cloud Run

This guide shows how to securely store SMTP password using Cloud Run's Secret Manager integration.

## Step 1: Create Secret in Secret Manager

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **Secret Manager** → **Secrets**
3. Click **CREATE SECRET**
4. Fill in the form:
   - **Name**: `SMTP_PASSWORD`
   - **Secret value**: Paste your Gmail App Password
   - **Secret ID**: `SMTP_PASSWORD` (auto-filled from name)
5. Click **CREATE SECRET**

**Note**: For Gmail, use an **App Password** (not your regular password). Generate one at: https://myaccount.google.com/apppasswords

## Step 2: Grant Access to Cloud Run Service Account

1. In Secret Manager, click on the `SMTP_PASSWORD` secret you just created
2. Click the **PERMISSIONS** tab
3. Click **ADD PRINCIPAL**
4. In the **New principals** field, enter:
   ```
   PROJECT_NUMBER-compute@developer.gserviceaccount.com
   ```
   (Replace `PROJECT_NUMBER` with your GCP project number)
5. In the **Select a role** dropdown, select: **Secret Manager Secret Accessor**
6. Click **SAVE**

**How to find your Project Number:**
- Go to **IAM & Admin** → **Settings**
- Or run: `gcloud projects describe PROJECT_ID --format="value(projectNumber)"`

## Step 3: Reference Secret in Cloud Run

1. Go to **Cloud Run** → Select your backend service
2. Click **EDIT & DEPLOY NEW REVISION**
3. Go to the **Variables & Secrets** tab
4. Scroll down to the **Secrets** section
5. Click **Reference a Secret**
6. Fill in:
   - **Secret**: Select `SMTP_PASSWORD` from dropdown
   - **Version**: `latest`
   - **Variable Name**: `SMTP_PASSWORD` (must match exactly)
   - **Mount as**: Leave empty (defaults to `/secrets/SMTP_PASSWORD`)
7. Click **DONE**
8. Click **DEPLOY**

## Step 4: Update Code to Read from Secret (Optional)

If you want to read from the secret file path instead of environment variable:

The secret will be mounted at: `/secrets/SMTP_PASSWORD`

You can read it in your code like:
```python
secret_path = Path("/secrets/SMTP_PASSWORD")
if secret_path.exists():
    password = secret_path.read_text().strip()
```

However, Cloud Run also automatically exposes secrets as environment variables when you reference them, so the current code should work as-is.

## Verification

After deployment:
1. Check the Cloud Run service logs to ensure no SMTP errors
2. Test by signing up a new user - verification email should be sent

## Security Benefits

✅ **Encrypted at rest** - Secrets are encrypted in Secret Manager  
✅ **Access control** - IAM permissions control who can access  
✅ **Audit logging** - All access is logged  
✅ **Not visible in UI** - Secret values are hidden in Cloud Run UI  
✅ **Rotation support** - Easy to update secret without code changes  

## Troubleshooting

**Secret not found:**
- Verify secret exists in Secret Manager
- Check secret name matches exactly (case-sensitive)
- Ensure service account has Secret Accessor role

**Permission denied:**
- Verify Cloud Run service account has access
- Check project number in service account email
- Ensure Secret Accessor role is assigned

**Secret not accessible:**
- Verify secret is referenced in Cloud Run revision
- Check secret version is `latest`
- Ensure deployment completed successfully

