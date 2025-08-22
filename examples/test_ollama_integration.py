#!/usr/bin/env python
"""
Test Ollama integration with the chatbot
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

def test_ollama_connection():
    """Test basic Ollama connection"""
    print("Testing Ollama connection...")
    
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags")
        if response.status_code == 200:
            models = response.json().get('models', [])
            print(f"  [OK] Ollama is running with {len(models)} models")
            for model in models:
                print(f"      - {model['name']}")
        else:
            print(f"  [FAIL] Ollama returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"  [FAIL] Cannot connect to Ollama: {e}")
        print("  Make sure Ollama is running: ollama serve")
        return False
    
    return True

def test_basic_llm():
    """Test basic LLM functionality"""
    print("\nTesting basic LLM functionality...")
    
    try:
        from llama_index.llms.ollama import Ollama
        from utils import config_loader
        
        config = config_loader.get_section('ollama')
        llm = Ollama(
            model=config['model'],
            base_url=f"{config['host']}:{config['port']}",
            temperature=config.get('temperature', 0.7),
            request_timeout=30.0
        )
        
        # Test simple completion
        response = llm.complete("What is 2+2?")
        print(f"  [OK] LLM response: {str(response)[:100]}...")
        return True
        
    except Exception as e:
        print(f"  [FAIL] LLM test failed: {e}")
        return False

def test_embedding_model():
    """Test embedding model"""
    print("\nTesting embedding model...")
    
    try:
        from llama_index.embeddings.ollama import OllamaEmbedding
        from utils import config_loader
        
        config = config_loader.get_section('ollama')
        embed_model = OllamaEmbedding(
            model_name=config.get('embedding_model', 'nomic-embed-text'),
            base_url=f"{config['host']}:{config['port']}"
        )
        
        # Test embedding generation
        embedding = embed_model.get_text_embedding("test text")
        print(f"  [OK] Embedding generated with dimension: {len(embedding)}")
        return True
        
    except Exception as e:
        print(f"  [FAIL] Embedding test failed: {e}")
        return False

def test_rag_index_building():
    """Test building RAG index"""
    print("\nTesting RAG index building...")
    
    try:
        from parsers import SchemaIndexBuilder
        
        builder = SchemaIndexBuilder()
        
        # Try to load or build index
        index = builder.load_index()
        if index is None:
            print("  Building new index...")
            index = builder.build_index()
        
        if index:
            print("  [OK] RAG index ready")
            return True
        else:
            print("  [FAIL] Could not build index")
            return False
            
    except Exception as e:
        print(f"  [FAIL] RAG index test failed: {e}")
        return False

def test_agent_initialization():
    """Test agent initialization"""
    print("\nTesting agent initialization...")
    
    try:
        from agent import LLMAgent
        
        agent = LLMAgent()
        print("  [OK] Agent initialized successfully")
        
        # Test simple query
        print("\n  Testing simple query...")
        response = agent.chat("Hello, can you help me?")
        print(f"  Response: {response[:200]}...")
        
        return True
        
    except Exception as e:
        print(f"  [FAIL] Agent initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all integration tests"""
    print("="*60)
    print(" OLLAMA INTEGRATION TESTS")
    print("="*60)
    print()
    
    tests = [
        ("Ollama Connection", test_ollama_connection),
        ("Basic LLM", test_basic_llm),
        ("Embedding Model", test_embedding_model),
        ("RAG Index", test_rag_index_building),
        ("Agent Initialization", test_agent_initialization),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f" {test_name}")
        print('='*50)
        
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"  [ERROR] Unexpected error: {e}")
            results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print(" SUMMARY")
    print("="*60)
    
    for test_name, success in results:
        status = "[PASS]" if success else "[FAIL]"
        print(f"{test_name:<30} {status}")
    
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n[SUCCESS] All integration tests passed!")
    else:
        print("\n[WARNING] Some tests failed. Check Ollama setup.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())