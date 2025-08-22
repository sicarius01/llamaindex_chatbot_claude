#!/usr/bin/env python
"""
Test the simplified agent
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_agent():
    """Test the simplified agent"""
    print("Testing Simplified LLM Agent...")
    
    from agent import LLMAgent
    
    # Initialize agent
    print("\n1. Initializing agent...")
    agent = LLMAgent()
    print("[SUCCESS] Agent initialized")
    
    # Test 1: Korean greeting
    print("\n2. Testing Korean greeting...")
    response = agent.chat("안녕하세요")
    print(f"Response: {response[:200]}")
    
    # Test 2: Simple greeting
    print("\n3. Testing simple greeting...")
    response = agent.chat("Hello")
    print(f"Response: {response[:200]}")
    
    # Test 3: Database query
    print("\n4. Testing database query...")
    response = agent.chat("What tables are available?")
    print(f"Response: {response[:200]}")
    
    # Test 4: SQL query
    print("\n5. Testing SQL query...")
    response = agent.chat("Write a SELECT query for all employees")
    print(f"Response: {response[:200]}")
    
    print("\n[SUCCESS] All tests completed!")

if __name__ == "__main__":
    try:
        test_agent()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()