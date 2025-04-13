# eidbi-query-system/backend/app/services/llm_service.py

import logging
from typing import Optional

from vertexai.language_models import TextGenerationModel

# --- Import Settings and Initializer ---
try:
    import sys
    import os
    SERVICE_DIR = os.path.dirname(__file__)
    APP_DIR = os.path.dirname(SERVICE_DIR)
    BACKEND_DIR = os.path.dirname(APP_DIR)
    PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
    SCRAPER_UTILS_PATH = os.path.join(PROJECT_ROOT, 'scraper', 'utils')
    if SCRAPER_UTILS_PATH not in sys.path:
        sys.path.append(SCRAPER_UTILS_PATH)
    from utils.vertex_ai_utils import initialize_vertex_ai_once, LOCATION, PROJECT_ID
except ImportError as e:
    print(f"Error importing vertex_ai_utils in llm_service.py: {e}")
    PROJECT_ID = None
    LOCATION = None
    def initialize_vertex_ai_once(): return False
# --- End Import ---

logger = logging.getLogger(__name__)

# Configuration
LLM_MODEL_NAME = "text-bison@002" # Or the latest available/preferred version
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.8
DEFAULT_TOP_K = 40

# Global variable for model instance
_llm_model_instance: Optional[TextGenerationModel] = None

def _get_llm_model(model_name: str = LLM_MODEL_NAME) -> Optional[TextGenerationModel]:
    """Gets or initializes the TextGenerationModel instance."""
    global _llm_model_instance
    if _llm_model_instance:
        # TODO: Check if model_name matches cached instance if allowing overrides
        return _llm_model_instance

    if not initialize_vertex_ai_once():
        logger.error("Vertex AI not initialized. Cannot get LLM model.")
        return None

    try:
        logger.info(f"Initializing LLM model: {model_name}")
        _llm_model_instance = TextGenerationModel.from_pretrained(model_name)
        logger.info("LLM model initialized.")
        return _llm_model_instance
    except Exception as e:
        logger.error(f"Failed to initialize LLM model {model_name}: {e}", exc_info=True)
        return None

def generate_text_response(
    prompt: str,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    temperature: float = DEFAULT_TEMPERATURE,
    top_p: float = DEFAULT_TOP_P,
    top_k: int = DEFAULT_TOP_K
) -> Optional[str]:
    """
    Generates a text response from the LLM based on the provided prompt.

    Args:
        prompt: The input prompt for the language model.
        max_output_tokens: Maximum number of tokens to generate.
        temperature: Controls randomness (0.0-1.0). Lower is more deterministic.
        top_p: Nucleus sampling parameter.
        top_k: Top-k sampling parameter.

    Returns:
        The generated text response as a string, or None if an error occurs.
    """
    model = _get_llm_model()
    if not model:
        return None

    try:
        logger.info(f"Sending prompt to LLM ({LLM_MODEL_NAME}). Prompt length: {len(prompt)}")
        response = model.predict(
            prompt,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
        )
        logger.info("Received response from LLM.")
        # Depending on the model version, the response object might vary.
        # Accessing the text attribute is common.
        return response.text

    except Exception as e:
        logger.error(f"LLM prediction request failed: {e}", exc_info=True)
        return None

# --- Example Usage ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"LLM Service using:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Model: {LLM_MODEL_NAME}")

    if initialize_vertex_ai_once():
        test_prompt = "Explain the concept of vector embeddings in simple terms."
        print(f"\n--- Testing LLM Generation --- ")
        print(f"Prompt: {test_prompt}")
        llm_response = generate_text_response(test_prompt)

        if llm_response:
            print("\nLLM Response:")
            print(llm_response)
        else:
            print("\nFailed to get response from LLM. Check logs.")
    else:
        print("\nERROR: Vertex AI Initialization failed. Cannot run LLM example.") 