#!/usr/bin/env python3
"""
Test script for the Idea Summarizer
-----------------------------------
This script tests the idea summarizer with a hardcoded idea
to help with fine-tuning prompts and verifying functionality.
"""

import os
import json
from dotenv import load_dotenv
from idea_summarizer import process_idea, save_idea_to_obsidian

# Load environment variables
load_dotenv()

# Sample idea for testing
SAMPLE_IDEA = """
Smart Home Energy Optimization Platform

A platform that uses AI to optimize energy usage in smart homes. The system would connect to various smart devices (thermostats, lights, appliances) and analyze usage patterns, weather forecasts, and electricity pricing to automatically adjust settings for maximum efficiency.

The platform would include:
1. A central hub that connects to all smart devices
2. Machine learning algorithms that learn user preferences and habits
3. Real-time energy usage monitoring and reporting
4. Automated scheduling based on electricity pricing (e.g., running dishwasher during off-peak hours)
5. Integration with renewable energy sources like solar panels
6. Mobile app for manual control and viewing analytics
7. Voice assistant compatibility (Alexa, Google Home)

The system could potentially save users 15-30% on energy bills while reducing their carbon footprint. It would be particularly valuable in areas with variable electricity pricing or for homes with solar/battery installations.
"""

def test_idea_processing():
    """Test the idea processing functionality"""
    print("Testing idea processing...")
    
    # Process the sample idea
    idea = process_idea(SAMPLE_IDEA, "test", "sample_idea")
    
    # Print the processed idea details
    print(f"\nProcessed Idea: {idea.title}")
    print(f"Category: {idea.category}")
    print(f"Summary length: {len(idea.summary)} characters")
    print(f"Key points: {len(idea.key_points)}")
    
    # Print tech stack
    if idea.tech_stack:
        print("\nTech Stack:")
        if idea.tech_stack.frontend:
            print(f"  Frontend: {', '.join(idea.tech_stack.frontend[:3])}...")
        if idea.tech_stack.backend:
            print(f"  Backend: {', '.join(idea.tech_stack.backend[:3])}...")
    
    # Print design philosophy
    if idea.design_philosophy and idea.design_philosophy.principles:
        print("\nDesign Principles:")
        for i, principle in enumerate(idea.design_philosophy.principles[:3], 1):
            print(f"  {i}. {principle}")
        if len(idea.design_philosophy.principles) > 3:
            print("  ...")
    
    # Print tags
    if idea.metadata.tags:
        print(f"\nTags: {', '.join(idea.metadata.tags[:5])}")
        if len(idea.metadata.tags) > 5:
            print("  ...")
    
    # Save to JSON for inspection
    with open("test_idea_output.json", "w", encoding="utf-8") as f:
        json.dump(idea.to_dict(), f, indent=2, default=str)
    print("\nFull idea details saved to test_idea_output.json")
    
    return idea

def test_obsidian_export(idea):
    """Test exporting to Obsidian"""
    print("\nExporting to Obsidian...")
    
    # Check if OBSIDIAN_VAULT is set
    vault_path = os.getenv("OBSIDIAN_VAULT")
    if not vault_path:
        print("OBSIDIAN_VAULT environment variable not set.")
        print("Using default path: /obsidian/vault")
    
    # Export to Obsidian
    try:
        file_path = save_idea_to_obsidian(idea)
        print(f"✅ Successfully exported idea to: {file_path}")
    except Exception as e:
        print(f"❌ Error exporting to Obsidian: {e}")
        print("Note: This is expected if running outside Docker or without proper volume mounts.")
        print("When running in Docker, the markdown will be saved to the Obsidian vault.")

def test_prompt_variations():
    """Test different prompt variations"""
    print("\nPrompt variation testing can be implemented here.")
    print("You can modify the LangchainProcessor.prompt_template in idea_summarizer.py")
    print("and run this test script again to see how changes affect the output.")
    
    # Example variations to try:
    variations = [
        "Add more emphasis on market analysis",
        "Focus more on technical implementation details",
        "Prioritize business model and monetization strategies",
        "Emphasize sustainability and environmental impact"
    ]
    
    for i, variation in enumerate(variations, 1):
        print(f"{i}. {variation}")

if __name__ == "__main__":
    print("=== Idea Summarizer Test ===\n")
    
    # Test idea processing
    processed_idea = test_idea_processing()
    
    # Test Obsidian export
    test_obsidian_export(processed_idea)
    
    # Prompt variation suggestions
    test_prompt_variations()
    
    print("\n=== Test Complete ===")
