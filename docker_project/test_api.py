#!/usr/bin/env python3
"""
API Test Script for Idea Summarizer
-----------------------------------
This script tests the /summarize API endpoint by sending a POST request
with a sample idea and displaying the response.
"""

import requests
import json
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:8000")
SUMMARIZE_ENDPOINT = f"{API_URL}/summarize"

# Sample idea for testing
SAMPLE_IDEA = """
AI-Powered Personal Finance Coach

A mobile application that serves as a personal finance coach, using AI to analyze spending habits, income, and financial goals to provide personalized advice and actionable steps for improving financial health.

Key features would include:
1. Automatic categorization and analysis of transactions
2. Personalized budget recommendations based on spending patterns
3. Goal setting and tracking with AI-generated milestones
4. Predictive analysis for future financial scenarios
5. Educational content tailored to the user's financial literacy level
6. Gamification elements to encourage positive financial behaviors
7. Integration with financial institutions for real-time data

The app would differentiate itself by focusing on behavioral psychology and habit formation, not just numbers and budgets. It would adapt its approach based on the user's financial personality type and learning style.
"""

def test_summarize_endpoint():
    """Test the /summarize endpoint with a sample idea"""
    print(f"Testing {SUMMARIZE_ENDPOINT} endpoint...")
    
    # Prepare the request payload
    payload = {
        "idea_text": SAMPLE_IDEA
    }
    
    # Send the POST request
    try:
        response = requests.post(SUMMARIZE_ENDPOINT, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("\n✅ API request successful!")
            
            # Parse and display the response
            data = response.json()
            
            # Display key information
            print(f"\nTitle: {data.get('title')}")
            print(f"Category: {data.get('category')}")
            
            # Display summary (truncated)
            summary = data.get('summary', '')
            print(f"\nSummary: {summary[:150]}..." if len(summary) > 150 else f"\nSummary: {summary}")
            
            # Display key points
            print("\nKey Points:")
            for i, point in enumerate(data.get('key_points', [])[:3], 1):
                print(f"  {i}. {point}")
            if len(data.get('key_points', [])) > 3:
                print("  ...")
            
            # Display tech stack (frontend only)
            if 'tech_stack' in data and 'frontend' in data['tech_stack']:
                print("\nFrontend Tech:")
                for tech in data['tech_stack']['frontend'][:3]:
                    print(f"  - {tech}")
                if len(data['tech_stack']['frontend']) > 3:
                    print("  ...")
            
            # Check if the idea was saved to Obsidian
            if 'obsidian_path' in data:
                print(f"\n✅ Idea saved to Obsidian at: {data['obsidian_path']}")
            else:
                print("\n⚠️ Note: Idea was not saved to Obsidian. This may be expected if running outside Docker.")
            
            # Save full response to a file for inspection
            with open("api_response.json", "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print("\nFull response saved to api_response.json")
            
            # Verify all expected fields are present
            expected_fields = ['id', 'title', 'summary', 'key_points', 'category', 
                              'tech_stack', 'design_philosophy', 'market_analysis', 'risks']
            missing_fields = [field for field in expected_fields if field not in data]
            
            if missing_fields:
                print(f"\n⚠️ Warning: Missing expected fields: {', '.join(missing_fields)}")
            else:
                print("\n✅ All expected fields are present in the response")
                
            print("\nNote: The API automatically saves all ideas to the Obsidian vault.")
                
            return True
            
        else:
            print(f"\n❌ API request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"\n❌ Connection error: Could not connect to {SUMMARIZE_ENDPOINT}")
        print("Make sure the Flask server is running and accessible.")
        return False
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

if __name__ == "__main__":
    print("=== Idea Summarizer API Test ===\n")
    
    # Test the summarize endpoint
    success = test_summarize_endpoint()
    
    # Exit with appropriate status code
    sys.exit(0 if success else 1)
