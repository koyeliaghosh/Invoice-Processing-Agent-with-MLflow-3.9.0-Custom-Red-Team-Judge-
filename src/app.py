from flask import Flask, request, jsonify, render_template
from src.extraction_agent import extract_invoice_data
from src.red_team_judges import pii_metric, injection_metric
import pandas as pd
from mlflow.metrics import MetricValue

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        invoice_content = None
        input_display_text = ""
        
        # Check for file upload (Multipart)
        if 'invoice_file' in request.files:
            file = request.files['invoice_file']
            if file.filename != '':
                try:
                    # Open image using PIL
                    import PIL.Image
                    image = PIL.Image.open(file.stream)
                    invoice_content = image
                    input_display_text = f"[Image File: {file.filename}]"
                except Exception as img_err:
                    return jsonify({'error': f"Invalid image file: {str(img_err)}"}), 400
        
        # Check for JSON text input
        elif request.is_json:
            data = request.get_json()
            input_text = data.get('invoice_text', '')
            if input_text:
                invoice_content = input_text
                input_display_text = input_text

        if not invoice_content:
             return jsonify({'error': 'No invoice text or file provided'}), 400
            
        # 1. Extraction
        logger.info(f"Extracting data from {type(invoice_content)}...")
        extraction_result_json = extract_invoice_data(invoice_content)
        
        # 2. Red Team Checks
        logger.info("Running Red Team Judges...")
        
        # Construct DataFrame for metric functions
        # Note: We pass the raw content (image or text) to the dataframe.
        eval_df = pd.DataFrame([{
            'prediction': extraction_result_json,
            'inputs': invoice_content, 
            'input': invoice_content 
        }])
        
        # Run PII Judge (Note: Regex won't work on Images, so PII might default to 0 for images unless we implement OCR-based PII)
        # We can accept that limitation for this demo step.
        pii_res_obj = pii_metric.eval_fn(eval_df, {})
        pii_score = pii_res_obj.scores[0]
        pii_reason = pii_res_obj.justifications[0]
        
        # Run Injection Judge
        inj_res_obj = injection_metric.eval_fn(eval_df, {})
        inj_score = inj_res_obj.scores[0]
        inj_reason = inj_res_obj.justifications[0]
        
        return jsonify({
            'extraction': extraction_result_json,
            'red_team_report': {
                'pii_score': pii_score,
                'pii_reason': pii_reason,
                'injection_score': inj_score,
                'injection_reason': inj_reason
            }
        })
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
