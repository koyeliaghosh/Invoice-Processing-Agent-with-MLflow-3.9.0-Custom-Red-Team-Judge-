# 🔴 MLflow 3.9 Red Team Judge Evaluator

**A complete Streamlit implementation demonstrating how to build Custom LLM-as-a-Judge and NLP Evaluators using the `mlflow.metrics.make_metric` API.**

This application acts as an AI Invoice Processing Agent (powered by Gemini 2.0 Flash) that intercepts and evaluates input payloads for two critical security risks before returning data:
1. **Personally Identifiable Information (PII) Leaks**
2. **Malicious Prompt Injection & Jailbreak Attempts**

---

## ✨ Key Features & Architecture

### 1. 🤖 Data Extraction Agent (Gemini 2.0 Flash)
The core application accepts a raw text payload or uploaded image (PDF/JPG/PNG) and extracts financial line-item data into structured JSON using Google Gemini.

### 2. 🛡️ Custom Judge 1: Deterministic PII Evaluator (Zero API Cost)
Instead of using expensive LLM tokens for simple scanning, the application implements **Microsoft Presidio (`en_core_web_sm`) and Regex** local processing via `make_metric`.
- If an SSN or Credit Card is found in the final payload, the MLflow Metric logs a **Critical Risk (Score: 1)**.

### 3. 💉 Custom Judge 2: LLM-as-a-Judge Prompt Injection Evaluator
The application implements an LLM Judge that evaluates *both* the original user input AND the Agent's extraction output.
- It tests specifically for attempts to bypass system prompts (e.g., `"IGNORE PREVIOUS INSTRUCTIONS"`, `"REFUND AMOUNT"`).
- If it detects a jailbreak attempt (even a failed one), the MLflow Metric logs **COMPROMISED (Score: 1)**.

### 4. 📊 Native MLflow 3.9 SQLite Dashboards
Bypasses the traditional MLflow iframe (which gets blocked by Streamlit Cloud CSP rules) and uses `mlflow.search_runs()` to natively pull historical Red Team security audit logs from the background SQLite Database, rendering them in a Pandas metrics table.

### 5. 💸 Cost Optimized & Hardened
The `llm_utils.py` circuit-breaker ensures production stability by enforcing:
- **Exponential Backoff:** Catches 429 Status Limits and waits rather than crashing.
- **Strict Token Limits:** Hardcoded `max_output_tokens=1024` prevents prompt-injection attacks from rapidly draining your API wallet.
- **Deterministic Grading:** `temperature=0.1` ensures rapid, non-creative judge grading.

---

## 🚀 How to Run Locally

### 1. Clone & Install
```bash
git clone https://github.com/your-username/invoice-processing-agent-red-team.git
cd invoice-processing-agent-red-team
pip install -r requirements.txt
```

### 2. Configure Environment variables
Create a `.env` file in the root directory and add your Google Gemini API key:
```env
GOOGLE_API_KEY="AIzaSy...your-gemini-key-here..."
# Optional:
# MLFLOW_TRACKING_URI="sqlite:///mlflow.db"
```

### 3. Launch the Application
```bash
streamlit run src/streamlit_app.py
```

---

## ☁️ Deploying on Streamlit Community Cloud

This app is production-ready for Streamlit Cloud.
1. Connect your Github repository to [share.streamlit.io](https://share.streamlit.io).
2. Set the Main file path to `src/streamlit_app.py`.
3. Open the **Advanced Settings / Secrets** and enter your API key:
```toml
GOOGLE_API_KEY = "AIzaSy..."
```

---

## 🧪 Testing the Red Team Evaluator

We have generated three test payloads located in the repository root so you can trigger the MLflow Metrics:
1. `safe_invoice.pdf` -> Will log zeroes (Safe).
2. `pii_leak_invoice.pdf` -> Will trigger the Presidio/Regex NLP Matrix (Score: 1).
3. `injection_invoice.pdf` -> Will trigger the LLM-as-a-Judge Injection detection (Score: 1).
