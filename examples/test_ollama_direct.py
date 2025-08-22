#!/usr/bin/env python
"""
Direct test of Ollama connection
"""

import requests
import json

def test_ollama_direct():
    """Test direct connection to Ollama"""
    print("Testing direct Ollama API connection...")
    
    # Test 1: Check if Ollama is running
    try:
        response = requests.get("http://localhost:11434/api/tags")
        print(f"Ollama status: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print("Available models:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
    except Exception as e:
        print(f"Failed to connect to Ollama: {e}")
        return
    
    # Test 2: Simple generation with qwen3:4b
    print("\nTesting generation with qwen3:4b...")
    
    data = {
        "model": "qwen3:4b",
        "prompt": "Hello",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 100
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')[:200]}")
            print(f"Total duration: {result.get('total_duration', 0) / 1e9:.2f} seconds")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 30 seconds")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 3: Korean input
    print("\nTesting Korean input...")
    
    data = {
        "model": "qwen3:4b",
        "prompt": "안녕하세요",
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 100
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')[:200]}")
            print(f"Total duration: {result.get('total_duration', 0) / 1e9:.2f} seconds")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        print("Request timed out after 30 seconds")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_ollama_direct()