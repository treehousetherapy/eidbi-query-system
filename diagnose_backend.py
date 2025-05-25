#!/usr/bin/env python3
"""
Diagnostic script for EIDBI Backend Service
This script tests various endpoints to identify the cause of 500 errors
"""

import requests
import json
import sys
from datetime import datetime

# Backend URL from the error message
BACKEND_URL = "https://eidbi-backend-service-5geiseeama-uc.a.run.app"

def print_header(text):
    """Print a formatted header"""
    print(f"\n{'=' * 60}")
    print(f"{text}")
    print(f"{'=' * 60}")

def test_endpoint(endpoint, method="GET", data=None, description=""):
    """Test a single endpoint and print results"""
    url = f"{BACKEND_URL}{endpoint}"
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Testing: {method} {endpoint}")
    if description:
        print(f"Description: {description}")
    
    try:
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            headers = {'Content-Type': 'application/json'}
            response = requests.post(url, json=data, headers=headers, timeout=30)
        else:
            print(f"Unsupported method: {method}")
            return False
        
        print(f"Status Code: {response.status_code}")
        
        # Print headers that might be useful
        if 'X-Process-Time' in response.headers:
            print(f"Process Time: {response.headers['X-Process-Time']}s")
        
        # Try to parse JSON response
        try:
            json_response = response.json()
            print(f"Response: {json.dumps(json_response, indent=2)}")
        except:
            print(f"Response (text): {response.text[:500]}...")
        
        return response.status_code < 400
        
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out after 30 seconds")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"ERROR: Connection failed - {e}")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__} - {e}")
        return False

def main():
    """Run all diagnostic tests"""
    print_header("EIDBI Backend Service Diagnostics")
    print(f"Backend URL: {BACKEND_URL}")
    
    # Test 1: Root endpoint
    print_header("Test 1: Root Endpoint")
    test_endpoint("/", description="Basic connectivity test")
    
    # Test 2: Health check
    print_header("Test 2: Health Check")
    test_endpoint("/health", description="Service health status")
    
    # Test 3: Cache stats
    print_header("Test 3: Cache Stats")
    test_endpoint("/cache-stats", description="Check cache configuration")
    
    # Test 4: Simple answer (doesn't require vector DB)
    print_header("Test 4: Simple Answer Endpoint")
    test_endpoint(
        "/simple-answer",
        method="POST",
        data="What is EIDBI?",
        description="Test LLM without vector database"
    )
    
    # Test 5: Small embedding test
    print_header("Test 5: Embedding Generation")
    test_endpoint(
        "/generate-embeddings",
        method="POST",
        data=["Test sentence"],
        description="Test Vertex AI embedding service"
    )
    
    # Test 6: Query endpoint (the one giving 500 error)
    print_header("Test 6: Query Endpoint (Main Issue)")
    test_endpoint(
        "/query",
        method="POST",
        data={
            "query_text": "What is EIDBI?",
            "num_results": 3
        },
        description="Full query with vector search"
    )
    
    print_header("Diagnostic Summary")
    print("\nBased on the test results above, you can identify where the issue lies:")
    print("- If root/health endpoints fail: Service is not running or misconfigured")
    print("- If simple-answer fails: Issue with LLM service or Vertex AI credentials")
    print("- If embeddings fail: Issue with embedding service or Vertex AI credentials")
    print("- If only query fails: Issue with vector database or chunk retrieval")
    print("\nCheck Cloud Run logs for more detailed error messages.")

if __name__ == "__main__":
    main() 