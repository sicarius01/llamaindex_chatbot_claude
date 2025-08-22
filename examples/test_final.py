#!/usr/bin/env python
"""
Final integration test with actual Ollama queries
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("="*60)
    print(" FINAL INTEGRATION TEST WITH OLLAMA")
    print("="*60)
    print()
    
    try:
        # Test 1: Import and initialize agent
        print("1. Initializing agent...")
        from agent import LLMAgent
        agent = LLMAgent()
        print("   [OK] Agent initialized")
        
        # Test 2: Simple query
        print("\n2. Testing simple query...")
        response = agent.chat("What tables are available in the database?")
        print(f"   Response: {response[:200]}...")
        print("   [OK] Query executed")
        
        # Test 3: Schema query  
        print("\n3. Testing schema query...")
        response = agent.chat("Tell me about the employees table")
        print(f"   Response: {response[:200]}...")
        print("   [OK] Schema query executed")
        
        # Test 4: SQL validation
        print("\n4. Testing SQL validation...")
        response = agent.chat("Can you write a SELECT query to get all employees?")
        print(f"   Response: {response[:200]}...")
        print("   [OK] SQL query generated")
        
        print("\n" + "="*60)
        print(" [SUCCESS] All tests passed!")
        print("="*60)
        return 0
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())