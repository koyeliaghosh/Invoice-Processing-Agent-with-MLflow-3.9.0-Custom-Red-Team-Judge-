import streamlit as st
import pandas as pd
import json
import os
import PIL.Image
import sys
import os

# Add the project root to sys.path so we can import from src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.extraction_agent import extract_invoice_data  # Using backend utility directly
from src.red_team_judges import pii_metric, injection_metric
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
    st.caption("v1.0.0 | Production Ready")

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
        uploaded_file = st.file_uploader("Upload Invoice Image", type=["png", "jpg", "jpeg"])
        if uploaded_file is not None:
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
            with st.spinner("Analyzing with Gemini & Red Team Judges..."):
                try:
                    # 1. Extraction
                    st.toast("Extracting data...", icon="🔍")
                    extraction_json_str = extract_invoice_data(invoice_content)
                    
                    # Safe Parse
                    try:
                        if '"error":' in extraction_json_str:
                             err = json.loads(extraction_json_str)
                             st.error(f"Extraction Failed: {err.get('error')}")
                             st.stop()
                        extraction_data = json.loads(extraction_json_str)
                    except:
                        st.error("Failed to parse AI response.")
                        st.text(extraction_json_str)
                        st.stop()

                    # 2. Red Team Audit
                    st.toast("Running Security Audit...", icon="🛡️")
                    
                    # Prepare dataframe for judges
                    eval_df = pd.DataFrame([{
                        'prediction': extraction_json_str, # Judge checks output
                        'inputs': invoice_content, # Judge checks input for injection
                        'input': invoice_content
                    }])
                    
                    # Run Judges
                    pii_res = pii_metric.eval_fn(eval_df, {})
                    pii_score = pii_res.scores[0]
                    pii_reason = pii_res.justifications[0]
                    
                    inj_res = injection_metric.eval_fn(eval_df, {})
                    inj_score = inj_res.scores[0]
                    inj_reason = inj_res.justifications[0]
                    
                    # --- Render Results ---
                    tab1, tab2 = st.tabs(["📝 Extraction", "🛡️ Audit Report"])
                    
                    with tab1:
                        st.json(extraction_data)
                        
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

                except Exception as e:
                    st.error(f"System Error: {str(e)}")
    else:
        st.info("Results will appear here after analysis.")
