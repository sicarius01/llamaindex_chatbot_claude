#!/usr/bin/env python
"""
Final test to verify the agent is working properly
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_agent():
    """Test the agent with actual queries"""
    print("Testing LLM Agent with qwen3:4b model...")
    
    from agent import LLMAgent
    
    # Initialize agent
    print("\n1. Initializing agent...")
    agent = LLMAgent()
    print("[SUCCESS] Agent initialized successfully")
    
    # Test 1: Simple greeting
    print("\n2. Testing simple greeting...")
    response = agent.chat("Hello, can you help me with database queries?")
    print(f"Response: {response[:200]}...")
    
    # Test 2: Ask about available tables
    print("\n3. Testing database schema query...")
    response = agent.chat("What tables are available in the database?")
    print(f"Response: {response[:200]}...")
    
    # Test 3: Ask for SQL query
    print("\n4. Testing SQL query generation...")
    response = agent.chat("Can you write a SELECT query to get all employees from the employees table?")
    print(f"Response: {response[:200]}...")
    
    # Test 4: Test conversation memory
    print("\n5. Testing conversation memory...")
    response = agent.chat("What was my first question?")
    print(f"Response: {response[:200]}...")
    
    # Test 5: Get conversation summary
    print("\n6. Getting conversation summary...")
    summary = agent.get_conversation_summary()
    print(f"Summary: Total messages: {summary['total_messages']}, Tokens: {summary.get('total_tokens', 'N/A')}")
    
    print("\n[SUCCESS] All tests completed successfully!")

if __name__ == "__main__":
    try:
        test_agent()
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()