# Deployment Instructions for Google Cloud Run (Serverless)

This application is ready to handle real traffic on Google Cloud Run. Since this is a Python Flask app packaged with `gunicorn`, it scales automatically.

## Prerequisites

1.  **Google Cloud Project**: You need a Google Cloud Project with billing enabled.
2.  **Google Cloud SDK**: Install and initialize the CLI tool.
    *   [Download Installer](https://cloud.google.com/sdk/docs/install)
    *   Initialize: `gcloud init`

## Step-by-Step Deployment

**1. Set your Project ID**
Run the following command in your terminal (PowerShell or Command Prompt):
```powershell
# Replace 'YOUR_PROJECT_ID' with your actual Google Cloud Project ID
gcloud config set project YOUR_PROJECT_ID
```
*Tip: You can find your Project ID in the Google Cloud Console dashboard.*

**2. Submit the Build to Container Registry**
This command builds the Docker image and pushes it to Google Container Registry (gcr.io).
```powershell
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/invoice-agent
```
Wait for the build to complete (it may take 1-2 minutes).

**3. Deploy to Cloud Run**
This command deploys the image as a serverless service.
**IMPORTANT**: Replace `YOUR_API_KEY` with your actual Google Gemini API Key.
```powershell
gcloud run deploy invoice-agent --image gcr.io/YOUR_PROJECT_ID/invoice-agent --platform managed --region us-central1 --allow-unauthenticated --set-env-vars GOOGLE_API_KEY="YOUR_API_KEY"
```

## Verify Deployment

After the deployment finishes, the terminal will display a URL (e.g., `https://invoice-agent-[hash]-uc.a.run.app`).
1.  Open that URL in your browser.
2.  You should see the same **InvoiceGuard UI**.
3.  Test it with an invoice!

## Updating the App

If you make changes to the code:
1.  Re-run Step 2 (Build).
2.  Re-run Step 3 (Deploy).
