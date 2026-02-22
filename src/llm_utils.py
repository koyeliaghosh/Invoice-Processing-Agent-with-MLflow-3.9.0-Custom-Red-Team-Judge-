import google.generativeai as genai
import time
import os
import logging
from typing import List, Optional, Any

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Constants
MAX_RETRIES = 3
BASE_DELAY = 2 # Seconds
BACKOFF_FACTOR = 2

# Configuration - genai.configure() is called lazily inside generate_content_safe
# to ensure load_dotenv() has already loaded the key.

# Fallback Model List - Order of preference (Efficiency -> Power)
# We start with Flash for speed/cost, fallback to others if needed.
# Or we can prefer the most stable one.
MODEL_FALLBACK_LIST = [
    'gemini-2.0-flash',
    'gemini-2.5-flash',
    'gemini-1.5-flash'
]

def generate_content_safe(
    prompt: Any, 
    system_instruction: Optional[str] = None,
    json_mode: bool = False,
    model_list: List[str] = MODEL_FALLBACK_LIST
) -> Optional[str]:
    """
    Generates content using Google Gemini with robust error handling:
    1. Rate Limit Handling (429): Exponential backoff.
    2. Model Fallback: Tries alternative models if the primary fails or is overloaded.
    3. Production Ready: Logging, error safety.
    """
    
    # Lazy configure - ensures API key is available after load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.error("GOOGLE_API_KEY not set! Cannot call Gemini.")
        return None
    genai.configure(api_key=api_key)
    
    last_exception = None  # Track last error for reporting
    
    generation_config = {
        "temperature": 0.1,  # Highly deterministic for cost/speed efficiency
        "max_output_tokens": 1024  # Strict token limit to prevent runaway costs
    }
    if json_mode:
        generation_config["response_mime_type"] = "application/json"

    for model_name in model_list:
        logger.info(f"Attempting generation with model: {model_name}")
        
        try:
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
            
            # Retry Loop for specific model
            for attempt in range(MAX_RETRIES):
                try:
                    response = model.generate_content(prompt, generation_config=generation_config)
                    return response.text
                except Exception as e:
                    error_str = str(e)
                    is_rate_limit = "429" in error_str or "Resource has been exhausted" in error_str
                    
                    if is_rate_limit:
                        delay = BASE_DELAY * (BACKOFF_FACTOR ** attempt)
                        logger.warning(f"Rate limit hit for {model_name} (Attempt {attempt+1}/{MAX_RETRIES}). Retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        # If it's not a rate limit (e.g. 400 Bad Request), maybe don't retry this model indefinitely?
                        # But for stability, we might treat 500s or 503s as retriable too.
                        # For now, let's assume random server errors could be transient.
                        logger.error(f"Error with {model_name}: {e}")
                        if attempt < MAX_RETRIES - 1:
                            delay = BASE_DELAY
                            time.sleep(delay)
                        else:
                            raise e # Move to next model if max retries hit
                            
        except Exception as e:
            logger.error(f"Failed all retries for model {model_name}. Reason: {e}")
            last_exception = e # Store the last exception from this block too
            continue # Try next model in the list
            
    error_msg = "All models failed to generate content."
    if last_exception:
        error_msg += f" Last error: {str(last_exception)}"
    logger.error(error_msg)
    return None
