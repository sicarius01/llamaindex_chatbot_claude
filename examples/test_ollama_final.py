#!/usr/bin/env python
"""
Final test with qwen3:4b model
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

def test_with_simple_llm():
    """Test with simple LLM call"""
    print("Testing Ollama with qwen3:4b model...")
    
    from llama_index.llms.ollama import Ollama
    
    llm = Ollama(
        model="qwen3:4b",
        base_url="http://localhost:11434",
        temperature=0.7,
        request_timeout=60.0
    )
    
    # Test simple completion
    print("\nTest 1: Simple math question")
    response = llm.complete("What is 2+2? Answer in one word.")
    print(f"Response: {response}")
    
    print("\nTest 2: Database question")
    response = llm.complete("Write a SELECT query to get all employees from the employees table. Only provide the SQL query.")
    print(f"Response: {response}")
    
    print("\nTest 3: Table information")
    response = llm.complete("List 3 common database table names for an e-commerce system.")
    print(f"Response: {response}")

if __name__ == "__main__":
    try:
        test_with_simple_llm()
        print("\n[SUCCESS] All tests completed!")
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()