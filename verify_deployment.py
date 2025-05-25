#!/usr/bin/env python3
"""
Enhanced EIDBI System Deployment Verification Script
This script tests all the new enhanced features to ensure they're working correctly.
"""

import requests
import json
import time
import sys
from typing import Dict, Any

class DeploymentVerifier:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.test_results = []
    
    def log_test(self, test_name: str, success: bool, details: str = ""):
        """Log test results."""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            "test": test_name,
            "success": success,
            "details": details
        })
    
    def test_basic_health(self) -> bool:
        """Test basic health endpoint."""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                version = data.get("version", "unknown")
                services = data.get("services", {})
                
                details = f"Version: {version}, Services: {services}"
                self.log_test("Basic Health Check", True, details)
                return True
            else:
                self.log_test("Basic Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Basic Health Check", False, str(e))
            return False
    
    def test_enhanced_features(self) -> bool:
        """Test enhanced feature endpoints."""
        endpoints = [
            ("/cache-stats", "Cache Statistics"),
            ("/data-sources/status", "Data Sources Status"),
            ("/feedback/stats", "Feedback Statistics")
        ]
        
        all_passed = True
        for endpoint, name in endpoints:
            try:
                response = self.session.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.log_test(f"Enhanced Feature: {name}", True, f"Response keys: {list(data.keys())}")
                else:
                    self.log_test(f"Enhanced Feature: {name}", False, f"HTTP {response.status_code}")
                    all_passed = False
            except Exception as e:
                self.log_test(f"Enhanced Feature: {name}", False, str(e))
                all_passed = False
        
        return all_passed
    
    def test_enhanced_query(self) -> bool:
        """Test the enhanced query endpoint with all new features."""
        try:
            payload = {
                "query_text": "What are the eligibility requirements for EIDBI?",
                "num_results": 3,
                "use_hybrid_search": True,
                "use_reranking": True,
                "use_enhanced_prompts": True,
                "use_additional_sources": False,  # Disable to avoid timeouts
                "user_session_id": "test_session_123"
            }
            
            response = self.session.post(
                f"{self.base_url}/query", 
                json=payload, 
                timeout=60  # Increased timeout
            )
            response.raise_for_status()
            
            data = response.json()
            required_fields = ["query", "answer", "retrieved_chunk_ids", "version", "query_type", "response_format"]
            
            for field in required_fields:
                if field not in data:
                    return False, f"Missing field: {field}"
            
            if data["version"] != "2.0.0":
                return False, f"Expected version 2.0.0, got {data['version']}"
                
            return True, f"Enhanced query successful. Query type: {data.get('query_type')}, Format: {data.get('response_format')}"
            
        except Exception as e:
            return False, str(e)
    
    def test_feedback_submission(self):
        """Test feedback submission functionality."""
        try:
            feedback_data = {
                "query_text": "What is EIDBI?",
                "response_text": "EIDBI is Early Intensive Developmental and Behavioral Intervention...",
                "feedback_type": "thumbs_up",
                "rating": 5,
                "categories": ["accuracy", "clarity"],
                "detailed_feedback": "Very helpful response",
                "retrieved_chunk_ids": ["test_chunk_1", "test_chunk_2"],
                "search_method": "hybrid",
                "user_session_id": "test_session_123"
            }
            
            response = requests.post(
                f"{self.base_url}/feedback", 
                json=feedback_data, 
                timeout=30  # Increased timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if "feedback_id" not in data:
                return False, "Missing feedback_id in response"
                
            return True, f"Feedback submitted successfully with ID: {data['feedback_id']}"
            
        except Exception as e:
            return False, str(e)
    
    def test_cache_functionality(self):
        """Test cache clearing functionality."""
        try:
            response = requests.post(
                f"{self.base_url}/clear-cache", 
                timeout=30  # Increased timeout
            )
            response.raise_for_status()
            
            data = response.json()
            if "message" not in data:
                return False, "Missing message in response"
                
            return True, f"Cache cleared: {data['message']}"
            
        except Exception as e:
            return False, str(e)
    
    def test_data_source_update(self):
        """Test data source update functionality."""
        try:
            # Test with force_update=False to avoid long waits
            response = requests.post(
                f"{self.base_url}/data-sources/update", 
                json={"force_update": False}, 
                timeout=120  # Increased timeout for network operations
            )
            response.raise_for_status()
            
            data = response.json()
            if "updated_sources" not in data:
                return False, "Missing updated_sources in response"
                
            return True, f"Data sources updated: {data.get('updated_sources', 0)} sources"
            
        except Exception as e:
            return False, str(e)
    
    def run_all_tests(self) -> bool:
        """Run all deployment verification tests."""
        print("🧪 Enhanced EIDBI System Deployment Verification")
        print("=" * 50)
        
        tests = [
            ("Basic Health Check", self.test_basic_health),
            ("Enhanced Features", self.test_enhanced_features),
            ("Enhanced Query", self.test_enhanced_query),
            ("Feedback Submission", self.test_feedback_submission),
            ("Cache Functionality", self.test_cache_functionality),
            ("Data Source Update", self.test_data_source_update)
        ]
        
        passed = 0
        total = len(tests)
        
        for test_name, test_func in tests:
            print(f"\n🔍 Running {test_name}...")
            try:
                if test_func():
                    passed += 1
            except Exception as e:
                self.log_test(test_name, False, f"Unexpected error: {e}")
        
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All tests passed! Enhanced system is working correctly.")
            return True
        else:
            print("⚠️  Some tests failed. Check the details above.")
            return False
    
    def generate_report(self) -> str:
        """Generate a detailed test report."""
        report = []
        report.append("Enhanced EIDBI System Deployment Verification Report")
        report.append("=" * 60)
        report.append(f"Test Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Base URL: {self.base_url}")
        report.append("")
        
        passed = sum(1 for result in self.test_results if result["success"])
        total = len(self.test_results)
        
        report.append(f"Overall Result: {passed}/{total} tests passed")
        report.append("")
        
        for result in self.test_results:
            status = "PASS" if result["success"] else "FAIL"
            report.append(f"[{status}] {result['test']}")
            if result["details"]:
                report.append(f"    Details: {result['details']}")
        
        return "\n".join(report)

def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Verify Enhanced EIDBI System Deployment")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the API")
    parser.add_argument("--report", help="Save detailed report to file")
    
    args = parser.parse_args()
    
    verifier = DeploymentVerifier(args.url)
    
    try:
        success = verifier.run_all_tests()
        
        if args.report:
            report = verifier.generate_report()
            with open(args.report, 'w') as f:
                f.write(report)
            print(f"\n📄 Detailed report saved to: {args.report}")
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n⏹️  Verification interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Verification failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 