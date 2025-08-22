#!/usr/bin/env python
"""
Test ReActAgent API to find correct method
"""

from llama_index.core.agent import ReActAgent
from llama_index.llms.ollama import Ollama

# Create simple LLM
llm = Ollama(
    model="qwen3:4b",
    base_url="http://localhost:11434",
    request_timeout=30.0
)

# Create agent
agent = ReActAgent(
    tools=[],
    llm=llm,
    verbose=True
)

# Check available methods
print("Available methods in ReActAgent:")
for attr in dir(agent):
    if not attr.startswith('_'):
        print(f"  - {attr}")

# Try to find chat/query methods
if hasattr(agent, 'chat'):
    print("\n✓ Has 'chat' method")
if hasattr(agent, 'query'):
    print("✓ Has 'query' method")
if hasattr(agent, 'achat'):
    print("✓ Has 'achat' method (async chat)")
if hasattr(agent, 'stream_chat'):
    print("✓ Has 'stream_chat' method")

# Test actual usage
print("\n\nTesting actual usage:")
try:
    # Try chat
    if hasattr(agent, 'chat'):
        response = agent.chat("Hello")
        print(f"chat() worked: {response}")
except Exception as e:
    print(f"chat() failed: {e}")

try:
    # Try query  
    if hasattr(agent, 'query'):
        response = agent.query("Hello")
        print(f"query() worked: {response}")
except Exception as e:
    print(f"query() failed: {e}")

# Check if we need to use a different approach
print("\n\nChecking for alternative approach:")
if hasattr(agent, '__call__'):
    print("✓ Agent is callable - can use agent('message')")