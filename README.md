# 🔴 MLflow 3.9 Red Team Judge Evaluator

**A complete, production-ready Streamlit application demonstrating how to build Custom LLM-as-a-Judge and NLP Evaluators using the new `mlflow.metrics.make_metric` API in MLflow 3.9.0.**

This application acts as an AI Invoice Processing Agent (powered by Gemini 2.0 Flash) that intercepts and evaluates input payloads for two critical security risks before returning data:
1. **Personally Identifiable Information (PII) Leaks**
2. **Malicious Prompt Injection & Jailbreak Attempts**

---

## 🔬 How MLflow 3.9.0 is Configured & Utilized

This project showcases several advanced features introduced in MLflow 3.9.x for GenAI evaluation, bypassing traditional MLOps tracking and moving towards real-time LLM auditing.

### 1. Custom Metrics via `make_metric`
Instead of relying on boilerplate metrics, this application uses `mlflow.metrics.make_metric` to construct domain-specific Red Team judges:
- **`pii_metric` (Deterministic NLP):** 
  Uses the `make_metric` API to wrap Microsoft Presidio (`en_core_web_sm`) and Regex. It evaluates the agent's output locally without incurring LLM API costs. The `eval_fn` expects a Pandas DataFrame containing `prediction` and `inputs`, and returns an `mlflow.metrics.MetricValue` object containing a score (1 for Critical Risk, 0 for Safe) and a justification.
- **`injection_metric` (LLM-as-a-Judge):** 
  Wraps a secondary call to Gemini 2.0 Flash within `make_metric`. This judge acts as a security auditor, analyzing the original user prompt for adversarial instructions (e.g., "IGNORE PREVIOUS INSTRUCTIONS"). It returns an `mlflow.metrics.MetricValue` denoting if the prompt was compromised.

### 2. Local SQLite Database Configuration
By default, MLflow spins up a local UI. However, this application integrates MLflow natively into Streamlit.
- **Tracking URI Setting:** In `src/streamlit_app.py`, we programmatically configure MLflow to use a local disk database before any runs are executed: 
  `mlflow.set_tracking_uri("sqlite:///mlflow.db")`
- **Experiment Management:** We set a dedicated experiment space to isolate our security records: 
  `mlflow.set_experiment("InvoiceGuard_Security_Audits")`

### 3. Execution & Run Tracking
During the Streamlit execution flow, the evaluation process is wrapped in an MLflow run context:
```python
with mlflow.start_run() as run:
    # 1. Pipeline Execution
    extraction_json_str = extract_invoice_data(invoice_content)
    
    # 2. Metric Evaluations
    pii_res = pii_metric.eval_fn(eval_df, {})
    inj_res = injection_metric.eval_fn(eval_df, {})
    
    # 3. Native MLflow Logging
    mlflow.log_metric("pii_exposure_score", float(pii_res.scores[0]))
    mlflow.log_metric("prompt_injection_score", float(inj_res.scores[0]))
    mlflow.log_param("input_type", input_type)
    mlflow.log_text(extraction_json_str, "extracted_data.json")
```

### 4. Native Streamlit Dashboards (`search_runs`)
Displaying the `mlflow ui` inside Streamlit using `<iframe>` elements often fails in cloud deployments due to Content Security Policy (CSP) headers. 
To solve this, this application uses the `mlflow.search_runs()` API. It queries the `sqlite:///mlflow.db` backend to pull the experiment history directly into a Pandas DataFrame, which is then rendered natively via `st.dataframe()`.

---

## ✨ Application Architecture

### 1. 🤖 Data Extraction Agent (Gemini 2.0 Flash)
The core application accepts a raw text payload or an uploaded image (PDF/JPG/PNG) and extracts financial line-item data into structured JSON using Google Gemini's multimodal capabilities.

### 2. 💸 Cost Optimized & Hardened
The `llm_utils.py` circuit-breaker ensures production stability:
- **Exponential Backoff:** Catches `429 Too Many Requests` status limits and waits rather than crashing.
- **Strict Token Limits:** Hardcoded `max_output_tokens=1024` prevents prompt-injection attacks from rapidly draining API credits.
- **Deterministic Grading:** `temperature=0.1` ensures rapid, non-creative judge grading.

---

## 🚀 How to Run Locally

### 1. Clone & Install
```bash
git clone https://github.com/koyelias/MLflow-Red-Team-Judge-.git
cd MLflow-Red-Team-Judge-
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
1. Connect your GitHub repository to [share.streamlit.io](https://share.streamlit.io).
2. Set the Main file path to `src/streamlit_app.py`.
3. Open the **Advanced Settings / Secrets** and enter your API key:
```toml
GOOGLE_API_KEY = "AIzaSy..."
```

---

## 🧪 Testing the Red Team Evaluator

We have generated three test payloads located in the repository root so you can trigger the MLflow Metrics:
1. `safe_invoice.pdf` -> Clean transaction. Will log zeroes (Safe).
2. `pii_leak_invoice.pdf` -> Contains SSNs. Will trigger the Presidio/Regex NLP Matrix (Score: 1).
3. `injection_invoice.pdf` -> Contains override commands. Will trigger the LLM-as-a-Judge Injection detection (Score: 1).
