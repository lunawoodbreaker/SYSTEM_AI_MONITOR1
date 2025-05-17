# test_ollama.py
print("Script started")

try:
    # Test if Ollama is responsive
    import requests
    print("Testing Ollama API connection...")
    
    response = requests.get("http://localhost:11434/api/version")
    print(f"Ollama version: {response.json().get('version', 'unknown')}")
    
    # Try to list models
    response = requests.post("http://localhost:11434/api/tags")
    models = response.json().get('models', [])
    print(f"Available models: {[model['name'] for model in models]}")
    
    # Test simple generation (without langchain)
    print("Testing direct generation...")
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": "Hello, world!", "stream": False}
    )
    result = response.json().get('response', '')
    print(f"Response: {result[:50]}..." if len(result) > 50 else f"Response: {result}")
    
    print("Direct Ollama tests completed successfully")
    
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
