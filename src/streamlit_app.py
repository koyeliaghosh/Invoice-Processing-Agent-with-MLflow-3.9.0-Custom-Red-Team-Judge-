import streamlit as st
import pandas as pd
import json
import os
import PIL.Image
import sys
import time
from dotenv import load_dotenv

# Load environment variables FIRST (before any src imports that need API keys)
load_dotenv()

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extraction_agent import extract_invoice_data  # Using backend utility directly
from src.red_team_judges import pii_metric, injection_metric
import mlflow
from mlflow.metrics import MetricValue
import base64

# --- Configure Frontend ---
st.set_page_config(
    page_title="InvoiceGuard | AI Security",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern look
st.markdown("""
<style>
    .reportview-container {
        background: #0e1117;
    }
    .main {
        background: #0e1117;
    }
    div.stButton > button:first-child {
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 2rem;
        border: none;
    }
    div.stButton > button:hover {
        background-color: #45a049;
    }
    .metric-card {
        padding: 1rem;
        border-radius: 8px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .safe { background-color: rgba(74, 222, 128, 0.2); border: 2px solid #4ade80; }
    .danger { background-color: rgba(248, 113, 113, 0.2); border: 2px solid #f87171; }
</style>
""", unsafe_allow_html=True)

# --- Sidebar ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/9630/9630044.png", width=80) 
    st.title("InvoiceGuard 🛡️")
    st.markdown("---")
    st.info("""
    **Google AI Powered Agent**
    This app uses **Gemini 2.0 Flash** to extract invoice data and Red Team Judges to audit for security risks.
    """)
    st.caption("v1.0.1 | Production Ready")

# --- Main App ---
st.title("Streamlit Invoice Agent")
st.markdown("Upload an invoice (Image) or paste text to analyze.")

col1, col2 = st.columns([1, 1], gap="medium")

# Input Column
with col1:
    st.subheader("1. Input 📄")
    input_type = st.radio("Source:", ["Text Paste", "Image Upload"], horizontal=True)
    
    invoice_content = None
    
    if input_type == "Text Paste":
        invoice_content = st.text_area("Paste Invoice Text:", height=300, 
            placeholder="Invoice #1001\nVendor: SafeTech\nTotal: $500...")
    else:
        uploaded_file = st.file_uploader("Upload Invoice (PDF or Image)", type=["png", "jpg", "jpeg", "pdf"])
        
        if uploaded_file is not None:
            # Handle PDF (Convert first page to image)
            if uploaded_file.type == "application/pdf":
                try:
                    import pypdfium2 as pdfium
                    
                    pdf = pdfium.PdfDocument(uploaded_file)
                    page = pdf[0] # Get first page
                    bitmap = page.render(scale=2) # Render 2x for better quality
                    pil_image = bitmap.to_pil()
                    
                    # Store for processing
                    image = pil_image
                    invoice_content = image
                    
                    st.image(image, caption="PDF Preview (Page 1)", use_column_width=True)
                    st.success("Converted PDF page to image for analysis.")
                    
                except Exception as pdf_err:
                    st.error(f"Failed to read PDF: {pdf_err}")
            
            # Handle Standard Images
            else:
                image = PIL.Image.open(uploaded_file)
                st.image(image, caption="Uploaded Invoice", use_column_width=True)
                invoice_content = image

    analyze_btn = st.button("Analyze & Audit 🚀", type="primary", use_container_width=True)

# Analysis Column
with col2:
    st.subheader("2. Results 📊")
    
    if analyze_btn:
        if not invoice_content:
            st.warning("Please provide input first.")
        else:
            # Cancel mechanism using session state
            if 'cancel_analysis' not in st.session_state:
                st.session_state.cancel_analysis = False
            
            cancel_btn = st.button("🛑 Cancel Analysis", type="secondary", use_container_width=True) 
            if cancel_btn:
                st.session_state.cancel_analysis = True
                st.warning("Analysis cancelled by user.")
                st.stop()

            # Setup MLflow Experiment
            mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db"))
            mlflow.set_experiment("InvoiceGuard_Security_Audits")

            with st.status("Analyzing...", expanded=True) as status:
                try:
                    with mlflow.start_run() as run:
                        # 1. Extraction (with timeout guard)
                        status.write("🔍 Step 1/3: Extracting data with Gemini...")
                        start_time = time.time()
                        extraction_json_str = extract_invoice_data(invoice_content)
                    elapsed = round(time.time() - start_time, 2)
                    st.toast(f"Extraction took {elapsed}s")
                    
                    # Safe Parse
                    try:
                        if '"error":' in extraction_json_str:
                             err = json.loads(extraction_json_str)
                             status.update(label="❌ Extraction Failed", state="error", expanded=True)
                             st.error(f"Extraction Failed: {err.get('error')}")
                             st.stop()
                        extraction_data = json.loads(extraction_json_str)
                    except:
                        status.update(label="❌ Parse Error", state="error", expanded=True)
                        st.error("Failed to parse AI response.")
                        st.text(extraction_json_str)
                        st.stop()
                    
                    status.write(f"✅ Data extracted successfully ({elapsed}s)")

                    # 2. Red Team Audit - PII
                    status.write("🛡️ Step 2/3: Running PII Detection...")
                    
                    # Prepare dataframe for judges
                    eval_df = pd.DataFrame([{
                        'prediction': extraction_json_str, 
                        'inputs': invoice_content, 
                        'input': invoice_content
                    }])
                    
                    # Run PII Judge
                    pii_res = pii_metric.eval_fn(eval_df, {})
                    pii_score = pii_res.scores[0]
                    pii_reason = pii_res.justifications[0]
                    status.write(f"✅ PII Check Complete (Score: {pii_score})")
                    
                    # 3. Injection Judge
                    status.write("💉 Step 3/3: Running Injection Analysis (LLM Judge)...")
                    inj_res = injection_metric.eval_fn(eval_df, {})
                    inj_score = inj_res.scores[0]
                    inj_reason = inj_res.justifications[0]
                    status.write(f"✅ Injection Check Complete (Score: {inj_score})")
                    
                    status.update(label="✅ Analysis Finished!", state="complete", expanded=False)
                    
                    # Log Results to MLflow
                    mlflow.log_metric("pii_exposure_score", float(pii_score))
                    mlflow.log_metric("prompt_injection_score", float(inj_score))
                    mlflow.log_param("input_type", input_type)
                    mlflow.log_text(extraction_json_str, "extracted_data.json")
                    
                    # --- Render Results ---
                    tab1, tab2, tab3, tab4 = st.tabs([
                        "📝 Extracted Data", 
                        "🛡️ Audit Report", 
                        "🤖 Agent Trace",
                        "📊 MLflow"
                    ])
                    
                    with tab1:
                        # Header Metrics
                        inv_col1, inv_col2, inv_col3 = st.columns(3)
                        inv_col1.metric("Invoice Number", extraction_data.get("invoice_number", "N/A"))
                        inv_col2.metric("Date", extraction_data.get("date", "N/A"))
                        
                        currency = extraction_data.get("currency", "$") or "$"
                        total = extraction_data.get("total_amount")
                        total_str = f"{currency}{total}" if total is not None else "N/A"
                        inv_col3.metric("Total Amount", total_str)
                        
                        st.divider()
                        
                        # Vendor and Notes
                        st.markdown(f"**Vendor:** {extraction_data.get('vendor_name', 'N/A')}")
                        if extraction_data.get("notes"):
                            st.info(f"**Notes/Confidential:** {extraction_data.get('notes')}")
                            
                        # Line Items Table
                        st.subheader("Line Items")
                        line_items = extraction_data.get("line_items", [])
                        if line_items:
                            df_items = pd.DataFrame(line_items)
                            st.dataframe(df_items, use_container_width=True, hide_index=True)
                        else:
                            st.caption("No line items found.")
                        
                    with tab2:
                        # PII Card
                        pii_class = "danger" if pii_score > 0 else "safe"
                        pii_status = "CRITICAL RISK" if pii_score > 0 else "SAFE"
                        st.markdown(f"""
                        <div class="metric-card {pii_class}">
                            <h3>PII Exposure Logic</h3>
                            <h1>{pii_status}</h1>
                            <p>{pii_reason}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Injection Card
                        inj_class = "danger" if inj_score > 0 else "safe"
                        inj_status = "COMPROMISED" if inj_score > 0 else "SECURE"
                        st.markdown(f"""
                        <div class="metric-card {inj_class}">
                            <h3>Prompt Injection Judge</h3>
                            <h1>{inj_status}</h1>
                            <p>{inj_reason}</p>
                        </div>
                        """, unsafe_allow_html=True)

                    with tab3:
                        st.subheader("What did the Agent do?")
                        st.markdown("""
                        1. **Input Ingestion**: Read the text/image payload.
                        2. **Gemini Extraction**: Sent payload to Gemini 2.0 Flash with instructions to construct standard JSON.
                        3. **Security Analysis (Presidio)**: Ran Regex and `en_core_web_sm` NLP model against extracted data to find Credit Cards / SSNs.
                        4. **Red Team Judge (LLM)**: Sent the original payload and extraction back to Gemini to determine if a prompt injection was attempted and if the model improperly obeyed it.
                        """)
                        with st.expander("View Raw Output (JSON)"):
                            st.json(extraction_data)
                            
                    with tab4:
                        st.subheader("MLflow Tracking Dashboard")
                        st.markdown("If you are running MLflow locally on port 5001, you will see the dashboard below.")
                        try:
                            # Embed MLflow UI inline
                            st.components.v1.iframe("http://localhost:5001", height=600, scrolling=True)
                        except Exception as e:
                            st.warning("Could not load MLflow tracking UI. Is it running on http://localhost:5001 ?")

                except Exception as e:
                    status.update(label="❌ Error", state="error", expanded=True)
                    st.error(f"System Error: {str(e)}")
    else:
        st.info("Results will appear here after analysis.")
