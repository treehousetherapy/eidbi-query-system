# backend/app/services/feedback_service.py

import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib
import os

logger = logging.getLogger(__name__)

class FeedbackType(Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    RATING = "rating"
    DETAILED = "detailed"

class FeedbackCategory(Enum):
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CLARITY = "clarity"
    RELEVANCE = "relevance"
    SPEED = "speed"

@dataclass
class UserFeedback:
    """Represents user feedback on a query response."""
    feedback_id: str
    query_text: str
    response_text: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 scale
    categories: Optional[List[FeedbackCategory]] = None
    detailed_feedback: Optional[str] = None
    retrieved_chunk_ids: Optional[List[str]] = None
    search_method: Optional[str] = None
    timestamp: float = None
    user_session_id: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()
        if self.feedback_id is None:
            # Generate a unique feedback ID
            content = f"{self.query_text}:{self.timestamp}:{self.user_session_id}"
            self.feedback_id = hashlib.md5(content.encode()).hexdigest()[:12]

class FeedbackService:
    """Service for collecting and analyzing user feedback."""
    
    def __init__(self, storage_path: str = "feedback_data.jsonl"):
        self.storage_path = storage_path
        self.feedback_cache: List[UserFeedback] = []
        self.load_existing_feedback()
    
    def load_existing_feedback(self) -> None:
        """Load existing feedback from storage."""
        if not os.path.exists(self.storage_path):
            logger.info(f"No existing feedback file found at {self.storage_path}")
            return
            
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        # Convert string enums back to enum objects
                        if 'feedback_type' in data:
                            data['feedback_type'] = FeedbackType(data['feedback_type'])
                        if 'categories' in data and data['categories']:
                            data['categories'] = [FeedbackCategory(cat) for cat in data['categories']]
                        
                        feedback = UserFeedback(**data)
                        self.feedback_cache.append(feedback)
            
            logger.info(f"Loaded {len(self.feedback_cache)} existing feedback entries")
        except Exception as e:
            logger.error(f"Error loading existing feedback: {e}")
    
    def save_feedback(self, feedback: UserFeedback) -> bool:
        """Save feedback to persistent storage."""
        try:
            # Convert to dict and handle enums
            feedback_dict = asdict(feedback)
            feedback_dict['feedback_type'] = feedback.feedback_type.value
            if feedback.categories:
                feedback_dict['categories'] = [cat.value for cat in feedback.categories]
            
            # Append to file
            with open(self.storage_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback_dict) + '\n')
            
            # Add to cache
            self.feedback_cache.append(feedback)
            logger.info(f"Saved feedback {feedback.feedback_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False
    
    def submit_feedback(
        self,
        query_text: str,
        response_text: str,
        feedback_type: FeedbackType,
        rating: Optional[int] = None,
        categories: Optional[List[FeedbackCategory]] = None,
        detailed_feedback: Optional[str] = None,
        retrieved_chunk_ids: Optional[List[str]] = None,
        search_method: Optional[str] = None,
        user_session_id: Optional[str] = None
    ) -> str:
        """Submit new user feedback."""
        
        # Validate rating if provided
        if rating is not None and (rating < 1 or rating > 5):
            raise ValueError("Rating must be between 1 and 5")
        
        feedback = UserFeedback(
            feedback_id=None,  # Will be auto-generated
            query_text=query_text,
            response_text=response_text,
            feedback_type=feedback_type,
            rating=rating,
            categories=categories,
            detailed_feedback=detailed_feedback,
            retrieved_chunk_ids=retrieved_chunk_ids,
            search_method=search_method,
            user_session_id=user_session_id
        )
        
        if self.save_feedback(feedback):
            return feedback.feedback_id
        else:
            raise Exception("Failed to save feedback")
    
    def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get feedback statistics for the last N days."""
        cutoff_time = time.time() - (days * 24 * 3600)
        recent_feedback = [f for f in self.feedback_cache if f.timestamp >= cutoff_time]
        
        if not recent_feedback:
            return {
                "total_feedback": 0,
                "period_days": days,
                "average_rating": None,
                "feedback_by_type": {},
                "feedback_by_category": {},
                "low_rated_queries": []
            }
        
        # Calculate statistics
        ratings = [f.rating for f in recent_feedback if f.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        
        # Count by type
        type_counts = {}
        for feedback in recent_feedback:
            type_name = feedback.feedback_type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        # Count by category
        category_counts = {}
        for feedback in recent_feedback:
            if feedback.categories:
                for category in feedback.categories:
                    cat_name = category.value
                    category_counts[cat_name] = category_counts.get(cat_name, 0) + 1
        
        # Find low-rated queries (rating <= 2)
        low_rated = [
            {
                "query": f.query_text,
                "rating": f.rating,
                "feedback": f.detailed_feedback,
                "timestamp": f.timestamp
            }
            for f in recent_feedback 
            if f.rating is not None and f.rating <= 2
        ]
        
        return {
            "total_feedback": len(recent_feedback),
            "period_days": days,
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "feedback_by_type": type_counts,
            "feedback_by_category": category_counts,
            "low_rated_queries": low_rated[:10]  # Limit to 10 most recent
        }
    
    def get_problematic_queries(self, min_feedback_count: int = 2) -> List[Dict[str, Any]]:
        """Identify queries that consistently receive poor feedback."""
        query_feedback = {}
        
        # Group feedback by query
        for feedback in self.feedback_cache:
            query = feedback.query_text.lower().strip()
            if query not in query_feedback:
                query_feedback[query] = []
            query_feedback[query].append(feedback)
        
        problematic = []
        for query, feedbacks in query_feedback.items():
            if len(feedbacks) < min_feedback_count:
                continue
                
            # Calculate average rating
            ratings = [f.rating for f in feedbacks if f.rating is not None]
            if not ratings:
                continue
                
            avg_rating = sum(ratings) / len(ratings)
            negative_feedback_count = sum(1 for f in feedbacks if f.feedback_type == FeedbackType.THUMBS_DOWN)
            
            # Consider problematic if average rating <= 2.5 or >50% negative feedback
            if avg_rating <= 2.5 or (negative_feedback_count / len(feedbacks)) > 0.5:
                problematic.append({
                    "query": query,
                    "feedback_count": len(feedbacks),
                    "average_rating": round(avg_rating, 2),
                    "negative_percentage": round((negative_feedback_count / len(feedbacks)) * 100, 1),
                    "recent_feedback": [f.detailed_feedback for f in feedbacks[-3:] if f.detailed_feedback]
                })
        
        # Sort by average rating (worst first)
        problematic.sort(key=lambda x: x["average_rating"])
        return problematic
    
    def get_improvement_suggestions(self) -> List[Dict[str, Any]]:
        """Generate improvement suggestions based on feedback patterns."""
        suggestions = []
        
        # Analyze feedback categories
        category_issues = {}
        for feedback in self.feedback_cache:
            if feedback.rating and feedback.rating <= 2 and feedback.categories:
                for category in feedback.categories:
                    cat_name = category.value
                    if cat_name not in category_issues:
                        category_issues[cat_name] = []
                    category_issues[cat_name].append(feedback)
        
        # Generate suggestions based on common issues
        for category, feedbacks in category_issues.items():
            if len(feedbacks) >= 3:  # At least 3 complaints in this category
                suggestion = {
                    "category": category,
                    "issue_count": len(feedbacks),
                    "suggestion": self._get_category_suggestion(category),
                    "example_feedback": [f.detailed_feedback for f in feedbacks[:2] if f.detailed_feedback]
                }
                suggestions.append(suggestion)
        
        return suggestions
    
    def _get_category_suggestion(self, category: str) -> str:
        """Get improvement suggestion for a specific category."""
        suggestions_map = {
            "accuracy": "Consider improving fact-checking and source verification. Review retrieved chunks for accuracy.",
            "completeness": "Enhance context retrieval to include more comprehensive information. Consider expanding search scope.",
            "clarity": "Improve prompt engineering for clearer, more structured responses. Consider adding examples.",
            "relevance": "Refine search algorithms and query understanding. Improve keyword extraction and semantic matching.",
            "speed": "Optimize caching strategies and consider response time improvements."
        }
        return suggestions_map.get(category, "Review and improve this aspect based on user feedback.")

# Global feedback service instance
feedback_service = FeedbackService() 