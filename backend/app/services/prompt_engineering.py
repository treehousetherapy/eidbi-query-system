# backend/app/services/prompt_engineering.py

import logging
from typing import Dict, List, Any, Optional
from enum import Enum
import re

logger = logging.getLogger(__name__)

class QueryType(Enum):
    """Different types of queries that require different prompt strategies."""
    ELIGIBILITY = "eligibility"
    SERVICES = "services"
    PROCESS = "process"
    COST_PAYMENT = "cost_payment"
    PROVIDER = "provider"
    GENERAL = "general"
    DEFINITION = "definition"
    COMPARISON = "comparison"

class ResponseFormat(Enum):
    """Different response formats for different use cases."""
    CONCISE = "concise"
    DETAILED = "detailed"
    BULLET_POINTS = "bullet_points"
    STEP_BY_STEP = "step_by_step"
    FAQ_STYLE = "faq_style"

class PromptEngineeringService:
    """Enhanced prompt engineering service for more precise and concise answers."""
    
    def __init__(self):
        self.query_patterns = self._initialize_query_patterns()
        self.prompt_templates = self._initialize_prompt_templates()
        self.response_guidelines = self._initialize_response_guidelines()
    
    def _initialize_query_patterns(self) -> Dict[QueryType, List[str]]:
        """Initialize patterns to classify query types."""
        return {
            QueryType.ELIGIBILITY: [
                r'\b(eligible|eligibility|qualify|qualifies|who can|requirements?)\b',
                r'\b(age limit|under \d+|criteria|qualify for)\b',
                r'\b(can my child|is my child|am I eligible)\b'
            ],
            QueryType.SERVICES: [
                r'\b(services?|treatment|therapy|intervention|what does|what is provided)\b',
                r'\b(types? of|kinds? of|available|offered|include)\b',
                r'\b(behavioral|developmental|communication|social skills)\b'
            ],
            QueryType.PROCESS: [
                r'\b(how to|process|steps?|procedure|apply|application)\b',
                r'\b(get started|begin|start|enroll|sign up)\b',
                r'\b(referral|assessment|evaluation)\b'
            ],
            QueryType.COST_PAYMENT: [
                r'\b(cost|price|fee|payment|insurance|covered|pay)\b',
                r'\b(medical assistance|ma|minnesotacare|medicaid)\b',
                r'\b(free|expensive|affordable|copay)\b'
            ],
            QueryType.PROVIDER: [
                r'\b(provider|therapist|professional|staff|who provides)\b',
                r'\b(bcba|behavior analyst|psychologist|specialist)\b',
                r'\b(qualifications?|certified|licensed|training)\b',
                r'\b(how many|number of|count|total)\b.*\b(provider|therapist)\b',
                r'\b(provider.*count|therapist.*count)\b'
            ],
            QueryType.DEFINITION: [
                r'\b(what is|define|definition|meaning|means)\b',
                r'\b(eidbi|early intensive|autism|asd)\b'
            ],
            QueryType.COMPARISON: [
                r'\b(difference|compare|versus|vs|better|alternative)\b',
                r'\b(similar|like|same as|different from)\b'
            ]
        }
    
    def _initialize_prompt_templates(self) -> Dict[QueryType, Dict[ResponseFormat, str]]:
        """Initialize prompt templates for different query types and response formats."""
        return {
            QueryType.ELIGIBILITY: {
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Answer the eligibility question concisely and accurately.

Question: {query}

Context: {context}

Instructions:
- Provide a direct, clear answer about eligibility requirements
- Include key criteria (age, diagnosis, insurance)
- Keep response under 100 words
- Use bullet points if listing multiple requirements

Answer:""",
                
                ResponseFormat.DETAILED: """You are an expert on the Minnesota EIDBI program. Provide a comprehensive answer about eligibility.

Question: {query}

Context: {context}

Instructions:
- Cover all eligibility requirements thoroughly
- Explain any exceptions or special cases
- Include information about the application process if relevant
- Organize information clearly with headings if needed

Answer:"""
            },
            
            QueryType.SERVICES: {
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Describe the services briefly and clearly.

Question: {query}

Context: {context}

Instructions:
- List the main types of services provided
- Focus on the most important/common services
- Keep response under 150 words
- Use bullet points for clarity

Answer:""",
                
                ResponseFormat.BULLET_POINTS: """You are an expert on the Minnesota EIDBI program. List the services in a clear, organized format.

Question: {query}

Context: {context}

Instructions:
- Use bullet points or numbered lists
- Group related services together
- Include brief descriptions for each service
- Prioritize the most commonly used services

Answer:"""
            },
            
            QueryType.PROCESS: {
                ResponseFormat.STEP_BY_STEP: """You are an expert on the Minnesota EIDBI program. Explain the process in clear, actionable steps.

Question: {query}

Context: {context}

Instructions:
- Break down the process into numbered steps
- Make each step actionable and specific
- Include who to contact or where to go for each step
- Mention typical timeframes if available

Answer:""",
                
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Provide a brief overview of the process.

Question: {query}

Context: {context}

Instructions:
- Summarize the key steps in order
- Keep response under 100 words
- Focus on the most important actions the person needs to take

Answer:"""
            },
            
            QueryType.COST_PAYMENT: {
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Answer the cost/payment question directly.

Question: {query}

Context: {context}

Instructions:
- State clearly what is covered and what isn't
- Mention specific insurance programs (MA, MinnesotaCare)
- Include any out-of-pocket costs if applicable
- Keep response under 100 words

Answer:""",
                
                ResponseFormat.FAQ_STYLE: """You are an expert on the Minnesota EIDBI program. Answer in a clear FAQ format.

Question: {query}

Context: {context}

Instructions:
- Structure as a clear question and answer
- Address common follow-up questions
- Include practical information about payment/coverage
- Use simple, non-technical language

Answer:"""
            },
            
            QueryType.PROVIDER: {
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Answer the provider-related question directly and accurately.

Question: {query}

Context: {context}

Instructions:
- If asking about provider counts/numbers: Check if exact numbers are available in the context
- If exact provider count NOT found in context, explicitly state: "The exact number of EIDBI providers is not specified in the available information."
- Provide fallback guidance: "For the most current and accurate provider count, please consult the official Minnesota DHS Provider Directory or contact Minnesota DHS directly."
- If describing provider qualifications, use only information from the context
- Include actionable next steps when possible
- Keep response under 150 words

Answer:""",
                
                ResponseFormat.DETAILED: """You are an expert on the Minnesota EIDBI program. Provide comprehensive information about EIDBI providers.

Question: {query}

Context: {context}

Instructions:
- For provider count questions: Search carefully for specific numbers in the context
- If exact numbers are NOT available, clearly state: "The exact number of EIDBI providers is not provided in the current information."
- Always include this fallback: "For the most accurate and up-to-date provider count and directory, please refer to the official Minnesota DHS resources at https://www.dhs.state.mn.us/"
- Cover provider qualifications, services, and how to find providers
- Organize information with clear headings
- Include practical guidance for finding and selecting providers

Answer:"""
            },
            
            QueryType.GENERAL: {
                ResponseFormat.CONCISE: """You are an expert on the Minnesota EIDBI program. Provide a clear, concise answer.

Question: {query}

Context: {context}

Instructions:
- Answer directly and specifically
- Use information from the context only
- Keep response focused and under 150 words
- If the context doesn't contain the answer, say so clearly

Answer:""",
                
                ResponseFormat.DETAILED: """You are an expert on the Minnesota EIDBI program. Provide a comprehensive answer based on the context.

Question: {query}

Context: {context}

Instructions:
- Use only information from the provided context
- Organize information logically
- Include relevant details and examples
- If the context is insufficient, explain what information is missing

Answer:"""
            }
        }
    
    def _initialize_response_guidelines(self) -> Dict[str, str]:
        """Initialize general response guidelines."""
        return {
            "accuracy": "Base answers strictly on the provided context. If information is not in the context, state this clearly.",
            "clarity": "Use simple, clear language. Avoid jargon unless necessary, and define technical terms.",
            "conciseness": "Be direct and to the point. Eliminate unnecessary words while maintaining completeness.",
            "structure": "Organize information logically. Use bullet points, numbers, or headings when helpful.",
            "actionability": "When possible, include specific next steps or actions the user can take.",
            "empathy": "Use a helpful, professional tone that acknowledges the user's needs."
        }
    
    def classify_query_type(self, query: str) -> QueryType:
        """Classify the query type based on patterns."""
        query_lower = query.lower()
        
        # Score each query type based on pattern matches
        scores = {}
        for query_type, patterns in self.query_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, query_lower))
                score += matches
            scores[query_type] = score
        
        # Return the type with the highest score, or GENERAL if no clear match
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        else:
            return QueryType.GENERAL
    
    def determine_response_format(self, query: str, query_type: QueryType) -> ResponseFormat:
        """Determine the best response format based on query characteristics."""
        query_lower = query.lower()
        
        # Check for format indicators in the query
        if any(word in query_lower for word in ['steps', 'how to', 'process', 'procedure']):
            return ResponseFormat.STEP_BY_STEP
        elif any(word in query_lower for word in ['list', 'types', 'kinds', 'what are']):
            return ResponseFormat.BULLET_POINTS
        elif any(word in query_lower for word in ['brief', 'quick', 'summary', 'short']):
            return ResponseFormat.CONCISE
        elif any(word in query_lower for word in ['detailed', 'comprehensive', 'explain', 'tell me about']):
            return ResponseFormat.DETAILED
        
        # Default formats based on query type
        format_defaults = {
            QueryType.ELIGIBILITY: ResponseFormat.CONCISE,
            QueryType.SERVICES: ResponseFormat.BULLET_POINTS,
            QueryType.PROCESS: ResponseFormat.STEP_BY_STEP,
            QueryType.COST_PAYMENT: ResponseFormat.CONCISE,
            QueryType.PROVIDER: ResponseFormat.CONCISE,
            QueryType.DEFINITION: ResponseFormat.CONCISE,
            QueryType.COMPARISON: ResponseFormat.DETAILED,
            QueryType.GENERAL: ResponseFormat.CONCISE
        }
        
        return format_defaults.get(query_type, ResponseFormat.CONCISE)
    
    def construct_enhanced_prompt(
        self, 
        query: str, 
        context_chunks: List[Dict[str, Any]],
        query_type: Optional[QueryType] = None,
        response_format: Optional[ResponseFormat] = None
    ) -> str:
        """Construct an enhanced prompt using the appropriate template."""
        
        # Auto-classify if not provided
        if query_type is None:
            query_type = self.classify_query_type(query)
        
        if response_format is None:
            response_format = self.determine_response_format(query, query_type)
        
        # Prepare context
        context = self._format_context(context_chunks, query_type)
        
        # Get the appropriate template
        template = self._get_template(query_type, response_format)
        
        # Format the prompt
        prompt = template.format(query=query, context=context)
        
        logger.info(f"Generated prompt for query type: {query_type.value}, format: {response_format.value}")
        return prompt
    
    def _format_context(self, context_chunks: List[Dict[str, Any]], query_type: QueryType) -> str:
        """Format context chunks appropriately for the query type."""
        if not context_chunks:
            return "No relevant context available."
        
        # For eligibility queries, prioritize chunks with eligibility information
        if query_type == QueryType.ELIGIBILITY:
            # Sort chunks by relevance to eligibility
            eligibility_keywords = ['eligible', 'eligibility', 'qualify', 'requirements', 'criteria', 'age']
            sorted_chunks = sorted(
                context_chunks,
                key=lambda chunk: sum(1 for keyword in eligibility_keywords 
                                    if keyword in chunk.get('content', '').lower()),
                reverse=True
            )
            context_chunks = sorted_chunks
        
        # Format chunks with clear separators
        formatted_chunks = []
        for i, chunk in enumerate(context_chunks[:5]):  # Limit to top 5 chunks
            content = chunk.get('content', '').strip()
            if content:
                # Add source information if available
                source_info = ""
                if 'url' in chunk:
                    source_info = f" (Source: {chunk['url']})"
                
                formatted_chunks.append(f"Context {i+1}{source_info}:\n{content}")
        
        return "\n\n---\n\n".join(formatted_chunks)
    
    def _get_template(self, query_type: QueryType, response_format: ResponseFormat) -> str:
        """Get the appropriate prompt template."""
        # Try to get specific template for query type and format
        if query_type in self.prompt_templates:
            if response_format in self.prompt_templates[query_type]:
                return self.prompt_templates[query_type][response_format]
            # Fall back to concise format for this query type
            elif ResponseFormat.CONCISE in self.prompt_templates[query_type]:
                return self.prompt_templates[query_type][ResponseFormat.CONCISE]
        
        # Fall back to general template
        return self.prompt_templates[QueryType.GENERAL][ResponseFormat.CONCISE]
    
    def get_prompt_metadata(self, query: str) -> Dict[str, Any]:
        """Get metadata about how the prompt was constructed."""
        query_type = self.classify_query_type(query)
        response_format = self.determine_response_format(query, query_type)
        
        return {
            "query_type": query_type.value,
            "response_format": response_format.value,
            "template_used": f"{query_type.value}_{response_format.value}",
            "guidelines_applied": list(self.response_guidelines.keys())
        }

# Global prompt engineering service instance
prompt_service = PromptEngineeringService() 