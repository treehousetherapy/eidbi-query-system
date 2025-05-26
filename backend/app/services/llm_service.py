# eidbi-query-system/backend/app/services/llm_service.py

import logging
import time
import re
from typing import Optional
import os

# Try both import methods for flexibility
try:
    from vertexai.generative_models import GenerativeModel
    from vertexai.language_models import TextGenerationModel
    using_vertexai_sdk = True
    using_gemini = True
except ImportError:
    try:
        from vertexai.language_models import TextGenerationModel
        using_vertexai_sdk = True
        using_gemini = False
    except ImportError:
        using_vertexai_sdk = False
        using_gemini = False
        logger = logging.getLogger(__name__)
        logger.warning("Could not import vertexai models, will try google.cloud.aiplatform")

# Import the Google Cloud AI Platform libraries
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict

# --- Import Settings and Initializer ---
try:
    # Import from backend's utils
    from utils.vertex_ai_utils import initialize_vertex_ai, LOCATION, PROJECT_ID
except ImportError as e:
    # Logger might not be initialized here yet
    print(f"ERROR in {__name__}: Failed to import shared Vertex AI utils: {e}")
    PROJECT_ID = None
    LOCATION = None
    # Provide a dummy function signature matching the real one
    def initialize_vertex_ai():
        print("ERROR: Dummy initialize_vertex_ai called due to import failure.")
        return False
# --- End Import ---

logger = logging.getLogger(__name__)

# Configuration - Updated to use currently available model
LLM_MODEL_NAME = "gemini-2.0-flash-lite" # Using Gemini 2.0 Flash-Lite as recommended replacement for text-bison
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.8
DEFAULT_TOP_K = 40

# Check if we should use mock responses
USE_MOCK_RESPONSES = os.getenv("MOCK_LLM_RESPONSES", "false").lower() == "true"

# Global variable for model instance
_llm_model_instance: Optional[object] = None

def _generate_offline_response(prompt: str) -> str:
    """
    Generates a simple offline response without making any API calls.
    Used as a fallback when Vertex AI is not available or configured.
    """
    logger.info("Using offline response mode - no API calls will be made")
    
    # Extract the question from the prompt
    question_start = prompt.find("Question:")
    question_end = prompt.find("Answer:") if "Answer:" in prompt else len(prompt)
    
    if question_start > -1:
        question = prompt[question_start + 9:question_end].strip()
    else:
        question = prompt.strip()
        
    # Simple keyword-based responses
    if "eligible" in question.lower() or "eligibility" in question.lower():
        return """Children and young adults under 21 who have a diagnosis of autism spectrum disorder (ASD) 
or a related condition, and who meet medical necessity criteria, are eligible for EIDBI services. 
The person must have a comprehensive evaluation indicating the medical necessity of the services.
Additionally, the individual must be enrolled in Medical Assistance (MA) or MinnesotaCare."""
        
    elif "cost" in question.lower() or "payment" in question.lower() or "insurance" in question.lower():
        return """EIDBI services are covered by Medical Assistance (MA) and MinnesotaCare in Minnesota.
Some private insurance plans may also cover these services. Families should contact their insurance 
provider to determine coverage details. For MA-eligible individuals, there is typically no cost to the family."""
        
    elif "service" in question.lower() or "provide" in question.lower() or "offer" in question.lower():
        return """EIDBI services include a range of treatments designed to improve communication, social, and behavioral skills.
These include:
- Comprehensive Multi-Disciplinary Evaluation (CMDE)
- Individual treatment plans
- Direct therapy services
- Intervention observation and direction
- Family/caregiver training and counseling
- Care coordination
Services are provided by a range of qualified professionals including EIDBI providers, mental health professionals, 
and behavioral aides working under supervision."""
        
    elif "provider" in question.lower() or "therapist" in question.lower():
        return """EIDBI services are provided by qualified professionals including:
- Licensed mental health professionals with expertise in child development
- Board Certified Behavior Analysts (BCBAs)
- Developmental psychologists
- Certified EIDBI providers
- Behavioral aides working under supervision
Providers must complete specific training and meet qualifications established by the Minnesota Department of Human Services."""
    
    # Default response for other questions
    else:
        return """The Minnesota Early Intensive Developmental and Behavioral Intervention (EIDBI) program
provides services for people under age 21 with autism spectrum disorder (ASD) or related conditions.
The program aims to improve skills in communication, social interaction, and behavior management
through evidence-based interventions. Services are individualized based on a comprehensive assessment
and are coordinated with families, schools, and other providers to support the individual's development."""

def _get_llm_model(model_name: str = LLM_MODEL_NAME) -> Optional[object]:
    """Gets or initializes the model instance."""
    global _llm_model_instance
    if _llm_model_instance:
        return _llm_model_instance

    if not initialize_vertex_ai():
        logger.error("Failed to initialize Vertex AI. Check logs for details.")
        return None

    try:
        if using_vertexai_sdk:
            # Use Gemini model (primary)
            if "gemini" in model_name.lower():
                logger.info(f"Initializing Gemini model: {model_name}")
                _llm_model_instance = GenerativeModel(model_name)
                logger.info("Gemini model initialized successfully.")
            # Use text-bison model (fallback/legacy)
            elif "text-bison" in model_name:
                logger.info(f"Initializing text generation model: {model_name}")
                _llm_model_instance = TextGenerationModel.from_pretrained(model_name)
                logger.info("Text generation model initialized successfully.")
            else:
                # Default to Gemini 2.0 Flash-Lite (current recommended model)
                logger.info(f"Defaulting to gemini-2.0-flash-lite model")
                _llm_model_instance = GenerativeModel("gemini-2.0-flash-lite")
                logger.info("Gemini 2.0 Flash-Lite model initialized successfully.")
        else:
            logger.info(f"Using direct aiplatform API for model: {model_name}")
            _llm_model_instance = model_name
            logger.info(f"Using model name: {_llm_model_instance} with aiplatform client")
        
        return _llm_model_instance
    except Exception as e:
        logger.error(f"Failed to initialize model {model_name}: {e}", exc_info=True)
        return None

def generate_text_response(prompt: str) -> Optional[str]:
    """
    Generate a response to the given prompt using Vertex AI models.
    Falls back to mock implementation if Vertex AI is not available.
    
    Args:
        prompt: The prompt to generate a response for
        
    Returns:
        The generated response, or None if generation fails
    """
    # Check if we should use mock responses
    if USE_MOCK_RESPONSES:
        logger.info("Using mock responses (MOCK_LLM_RESPONSES=true)")
        return _generate_offline_response(prompt)
    
    # Try to use real Vertex AI first
    model = _get_llm_model()
    
    if model and using_vertexai_sdk:
        try:
            logger.info(f"Generating response using Vertex AI for prompt: {prompt[:100]}...")
            
            # Check if it's a GenerativeModel (Gemini) - primary case
            if hasattr(model, 'generate_content'):
                response = model.generate_content(prompt)
                generated_text = response.text
            # Otherwise it's a TextGenerationModel (text-bison) - fallback
            elif hasattr(model, 'predict'):
                response = model.predict(
                    prompt,
                    max_output_tokens=DEFAULT_MAX_OUTPUT_TOKENS,
                    temperature=DEFAULT_TEMPERATURE,
                    top_p=DEFAULT_TOP_P,
                    top_k=DEFAULT_TOP_K,
                )
                generated_text = response.text
            else:
                raise AttributeError(f"Model does not have expected methods (generate_content or predict)")
            
            logger.info(f"Successfully generated response: {generated_text[:100]}...")
            return generated_text
            
        except Exception as e:
            logger.error(f"Error using Vertex AI text generation: {e}", exc_info=True)
            logger.info("Falling back to offline response")
            return _generate_offline_response(prompt)
    
    # Fall back to offline response
    logger.info("Vertex AI not available, using offline response")
    return _generate_offline_response(prompt)

# --- Example Usage ---
if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s')

    print(f"LLM Service using:")
    print(f"  Project: {PROJECT_ID}")
    print(f"  Location: {LOCATION}")
    print(f"  Model: {LLM_MODEL_NAME}")

    if initialize_vertex_ai():
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