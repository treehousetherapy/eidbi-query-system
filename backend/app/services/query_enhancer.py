# eidbi-query-system/backend/app/services/query_enhancer.py

import logging
from typing import List, Dict, Tuple
import re

logger = logging.getLogger(__name__)

class QueryEnhancer:
    """Service for enhancing queries to improve search results"""
    
    def __init__(self):
        # Common EIDBI-related expansions
        self.expansions = {
            "eidbi": [
                "Early Intensive Developmental and Behavioral Intervention",
                "EIDBI benefit",
                "EIDBI services",
                "EIDBI program"
            ],
            "what is": [
                "definition of",
                "explain",
                "overview of",
                "describe"
            ],
            "eligible": [
                "eligibility",
                "qualify",
                "requirements",
                "who can receive"
            ],
            "provider": [
                "provider requirements",
                "become a provider",
                "provider types",
                "QSP",
                "qualified supervising professional"
            ],
            "services": [
                "treatment",
                "intervention",
                "therapy",
                "support"
            ],
            "cost": [
                "payment",
                "insurance",
                "coverage",
                "Medical Assistance",
                "MA"
            ]
        }
        
        # Acronym mappings
        self.acronyms = {
            "eidbi": "Early Intensive Developmental and Behavioral Intervention",
            "asd": "autism spectrum disorder",
            "cmde": "comprehensive multi-disciplinary evaluation",
            "qsp": "qualified supervising professional",
            "ma": "Medical Assistance",
            "mhcp": "Minnesota Health Care Program",
            "tefra": "Tax Equity and Fiscal Responsibility Act"
        }
    
    def expand_query(self, query: str) -> List[str]:
        """
        Expand a query into multiple variations to improve search results
        
        Args:
            query: The original query text
            
        Returns:
            List of expanded query variations
        """
        logger.info(f"Expanding query: '{query}'")
        
        expanded_queries = [query]  # Always include original
        query_lower = query.lower()
        
        # 1. Expand acronyms
        for acronym, full_form in self.acronyms.items():
            if acronym in query_lower:
                # Add version with acronym replaced
                expanded_query = re.sub(
                    rf'\b{acronym}\b', 
                    full_form, 
                    query, 
                    flags=re.IGNORECASE
                )
                if expanded_query not in expanded_queries:
                    expanded_queries.append(expanded_query)
                
                # Add version with both acronym and full form
                combined = f"{query} {full_form}"
                if combined not in expanded_queries:
                    expanded_queries.append(combined)
        
        # 2. Add contextual expansions
        for key, expansions in self.expansions.items():
            if key in query_lower:
                for expansion in expansions:
                    # Create variations
                    if key == "what is" and "eidbi" in query_lower:
                        # Special handling for "What is EIDBI?"
                        variations = [
                            f"{expansion} EIDBI",
                            f"EIDBI {expansion}",
                            f"{expansion} Early Intensive Developmental and Behavioral Intervention"
                        ]
                        expanded_queries.extend(variations)
                    else:
                        # General expansion
                        expanded = f"{query} {expansion}"
                        if expanded not in expanded_queries:
                            expanded_queries.append(expanded)
        
        # 3. Add specific EIDBI context if query seems general
        if len(query.split()) <= 3 and "eidbi" in query_lower:
            context_additions = [
                f"{query} Minnesota Health Care Program",
                f"{query} autism spectrum disorder",
                f"{query} benefit program services"
            ]
            expanded_queries.extend(context_additions)
        
        # Limit to reasonable number of expansions
        expanded_queries = expanded_queries[:10]
        
        logger.info(f"Generated {len(expanded_queries)} query variations")
        for i, eq in enumerate(expanded_queries):
            logger.debug(f"  {i+1}. {eq}")
        
        return expanded_queries
    
    def extract_keywords(self, query: str) -> List[str]:
        """
        Extract important keywords from the query for keyword matching
        
        Args:
            query: The query text
            
        Returns:
            List of important keywords
        """
        # Remove common words
        stop_words = {
            'is', 'are', 'what', 'who', 'where', 'when', 'how', 'the', 'a', 
            'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of',
            'with', 'can', 'do', 'does', 'get', 'i', 'my', 'me'
        }
        
        # Tokenize and filter
        words = query.lower().split()
        keywords = []
        
        for word in words:
            # Clean punctuation
            cleaned = re.sub(r'[^\w\s-]', '', word)
            if cleaned and cleaned not in stop_words:
                keywords.append(cleaned)
                
                # Also add expanded form if it's an acronym
                if cleaned in self.acronyms:
                    keywords.append(self.acronyms[cleaned])
        
        # Add important phrases
        query_lower = query.lower()
        important_phrases = [
            "early intensive developmental and behavioral intervention",
            "autism spectrum disorder",
            "minnesota health care program",
            "medical assistance",
            "comprehensive multi-disciplinary evaluation"
        ]
        
        for phrase in important_phrases:
            if phrase in query_lower:
                keywords.append(phrase)
        
        logger.info(f"Extracted keywords: {keywords}")
        return keywords


# Singleton instance
query_enhancer = QueryEnhancer() 