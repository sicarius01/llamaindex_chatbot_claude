#!/usr/bin/env python
"""
Test main.py with clean log file
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_main():
    """Test main with clean setup"""
    print("Testing chatbot without log file conflicts...")
    
    from agent import LLMAgent
    
    # Initialize agent
    print("\nInitializing agent...")
    agent = LLMAgent()
    print("[OK] Agent initialized")
    
    # Test simple query
    print("\nTesting query...")
    response = agent.chat("Hello, what tables are in the database?")
    print(f"Response: {response[:100]}...")
    
    print("\n[SUCCESS] Test completed!")

if __name__ == "__main__":
    test_main()