import os
import json
import google.generativeai as genai
from dotenv import load_dotenv
from src.llm_utils import generate_content_safe, MODEL_FALLBACK_LIST
from typing import List, Optional, Any
import PIL.Image
import io

load_dotenv()

# genai.configure moved to llm_utils.py

def extract_invoice_data(invoice_data: Any) -> str:
    """
    Extracts structured data from invoice text or image using Gemini.
    Args:
        invoice_data: Can be a string (text), bytes (image data), or PIL.Image object.
    Returns:
        JSON string with extracted data.
    """
    
    base_prompt = """
    You are an expert financial analyst. Your task is to extract structured data from the provided invoice.
    Return a JSON object with the following keys:
    - invoice_number (string)
    - date (string, ISO 8601 format if possible)
    - vendor_name (string)
    - total_amount (float)
    - currency (string)
    - line_items (list of objects, each with description, quantity, unit_price, total)
    - notes (string, capture any important notes or sensitive info like SSN if visible)
    
    If specific fields are missing, set them to null.
    """
    
    prompt_content = []
    
    if isinstance(invoice_data, str):
        prompt_content.append(base_prompt)
        prompt_content.append(f"Invoice Text:\n{invoice_data}")
    else:
        # Image input (PIL Image or Bytes)
        prompt_content.append(base_prompt)
        prompt_content.append(invoice_data)
        prompt_content.append("Extract data from this invoice image.")
    
    try:
        response_text = generate_content_safe(
            prompt=prompt_content,
            json_mode=True,
            model_list=MODEL_FALLBACK_LIST
        )
        return response_text if response_text else json.dumps({"error": "Failed to generate extraction", "invoice_number": None})
    except Exception as e:
        return json.dumps({"error": str(e), "invoice_number": None, "total_amount": None})

if __name__ == "__main__":
    # Simple test
    sample_text = "Invoice #12345 from Acme Corp. Date: 2023-10-27. Total: $500.00. Services: Consulting."
    print(extract_invoice_data(sample_text))
