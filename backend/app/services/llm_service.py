# eidbi-query-system/backend/app/services/llm_service.py

import logging
import time
import re
from typing import Optional

# Try both import methods for flexibility
try:
    from vertexai.language_models import TextGenerationModel
    using_vertexai_sdk = True
except ImportError:
    using_vertexai_sdk = False
    logger = logging.getLogger(__name__)
    logger.warning("Could not import vertexai.language_models, will try google.cloud.aiplatform")

# Import the Google Cloud AI Platform libraries
from google.cloud import aiplatform
from google.cloud.aiplatform.gapic.schema import predict

# --- Import Settings and Initializer ---
try:
    # Remove the old sys.path manipulation
    # We now rely on the project root being in sys.path (added in main.py)
    from scraper.utils.vertex_ai_utils import initialize_vertex_ai, LOCATION, PROJECT_ID
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

# Configuration
LLM_MODEL_NAME = "text-bison@002" # Or the latest available/preferred version
DEFAULT_MAX_OUTPUT_TOKENS = 1024
DEFAULT_TEMPERATURE = 0.2
DEFAULT_TOP_P = 0.8
DEFAULT_TOP_K = 40

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
    """Gets or initializes the TextGenerationModel instance."""
    global _llm_model_instance
    if _llm_model_instance:
        # TODO: Check if model_name matches cached instance if allowing overrides
        return _llm_model_instance

    if not initialize_vertex_ai():
        logger.error("Failed to initialize Vertex AI. Check logs for details.")
        return None

    try:
        if using_vertexai_sdk:
            logger.info(f"Initializing LLM model via vertexai SDK: {model_name}")
            _llm_model_instance = TextGenerationModel.from_pretrained(model_name)
            logger.info("LLM model initialized via vertexai SDK.")
        else:
            logger.info(f"Using direct aiplatform API for model: {model_name}")
            # Store the model name as we'll use it directly with predict client
            _llm_model_instance = model_name
            logger.info(f"Using model name: {_llm_model_instance} with aiplatform client")
        
        return _llm_model_instance
    except Exception as e:
        logger.error(f"Failed to initialize LLM model {model_name}: {e}", exc_info=True)
        return None

def generate_text_response(prompt: str) -> Optional[str]:
    """
    Generate a response to the given prompt using a rule-based approach.
    
    This is a mock implementation that doesn't require an actual LLM API.
    In a real implementation, this would call a Vertex AI LLM or other text generation service.
    
    Args:
        prompt: The prompt to generate a response for
        
    Returns:
        The generated response, or None if generation fails
    """
    logger.info(f"Generating mock response for prompt: {prompt[:100]}...")
    
    try:
        # Check if this is a context-based query
        is_context_based = "based *only* on the provided context" in prompt
        
        # Extract the question from the prompt
        question_match = re.search(r"Question: (.*?)(?:\n\nContext:|\n\nAnswer:)", prompt, re.DOTALL)
        question = question_match.group(1).strip() if question_match else "Unknown question"
        
        # Simple rule-based response generation
        response = ""
        
        # Simulate response delay
        time.sleep(1)
        
        if is_context_based:
            # Extract context
            context_match = re.search(r"Context:(.*?)(?:\n\nAnswer:)", prompt, re.DOTALL)
            context = context_match.group(1).strip() if context_match else ""
            
            # If context contains keywords related to the question, generate a response
            # Otherwise, indicate that the answer is not in the context
            
            if "EIDBI" in context or "Early Intensive Developmental and Behavioral Intervention" in context:
                if "eligible" in question.lower() or "who can" in question.lower():
                    response = "Based on the provided context, children and youth under 21 who have autism spectrum disorder or a related condition may be eligible for EIDBI services. A comprehensive evaluation must determine that EIDBI services are medically necessary."
                elif "cost" in question.lower() or "fee" in question.lower() or "pay" in question.lower():
                    response = "According to the provided information, EIDBI services are covered by Medical Assistance (MA) and some private insurance plans. Families should check with their insurance provider for specific coverage details."
                elif "services" in question.lower() or "provide" in question.lower() or "offer" in question.lower():
                    response = "Based on the context, EIDBI services may include individual, group, and family interventions designed to improve social, communication, and behavioral skills. The specific services are tailored to the individual's needs as determined by a comprehensive assessment."
                else:
                    response = "I cannot find specific information about this topic in the provided context. The context primarily discusses general aspects of the EIDBI program without addressing this specific question."
            else:
                response = "I cannot answer the question based on the provided information. The context doesn't contain relevant details about the EIDBI program to address your query."
        else:
            # Generic responses for non-context questions
            if "EIDBI" in question:
                response = "EIDBI (Early Intensive Developmental and Behavioral Intervention) is a program designed to help children and youth with autism spectrum disorder and related conditions. It provides intensive, individualized services to improve social interaction, communication, and behavior skills."
            elif "autism" in question.lower():
                response = "Autism spectrum disorder (ASD) is a developmental condition that affects communication, social interaction, and behavior. The Minnesota EIDBI program provides services specifically designed to help individuals with ASD and related conditions."
            else:
                response = "I'm a mock implementation of an AI assistant focused on providing information about the Minnesota EIDBI program. I can answer questions about eligibility, services, and other aspects of the program."
        
        logger.info(f"Generated mock response: {response[:100]}...")
        return response
    except Exception as e:
        logger.error(f"Error generating mock response: {e}", exc_info=True)
        return "I apologize, but I encountered an error while trying to generate a response. Please try again."

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