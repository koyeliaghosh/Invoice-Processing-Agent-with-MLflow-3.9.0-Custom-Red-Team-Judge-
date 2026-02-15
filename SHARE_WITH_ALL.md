# How to Share Your Invoice Agent App

You have built a powerful AI Invoice Agent. Now share it!

## Step 1: Push to GitHub

1.  **Create a New Repo**:
    *   Go to: https://github.com/new
    *   Repository name: `invoice-processing-agent`
    *   Description: "AI Agent for Invoice Extraction & Red Teaming"
    *   **Public** (so Streamlit/others can see it)
    *   Do **NOT** initialize with README, .gitignore, or License (we already have them).
    *   Click **Create repository**.

2.  **Connect & Push**:
    Run these commands in your terminal:
    ```bash
    git remote add origin https://github.com/koyeliaghosh/invoice-processing-agent.git
    git branch -M main
    git push -u origin main
    ```

## Step 2: Deploy to Streamlit Cloud (Free)

1.  Go to **[share.streamlit.io](https://share.streamlit.io/)**
2.  Click **"New app"**.
3.  Select `koyeliaghosh/invoice-processing-agent`.
4.  Main file path: `src/streamlit_app.py`
5.  **Critcal**: Click "Advanced Settings" -> "Secrets" and add:
    ```toml
    GOOGLE_API_KEY = "your-actual-api-key-here"
    ```
6.  Click **Deploy**.

You will get a link like `https://invoice-processing-agent.streamlit.app` to share with everyone!
