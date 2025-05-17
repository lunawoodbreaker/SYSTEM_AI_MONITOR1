# working_document_scanner.py
import os
import requests
import json
from datetime import datetime

class SimpleDocumentScanner:
    def __init__(self):
        """Initialize the document scanner"""
        self.documents = []
        self.ollama_url = "http://localhost:11434"
        
    def check_ollama(self):
        """Check if Ollama is available and get available models"""
        try:
            # Check version
            response = requests.get(f"{self.ollama_url}/api/version")
            version = response.json().get("version", "unknown")
            
            # List models
            response = requests.get(f"{self.ollama_url}/api/tags")
            models = response.json().get("models", [])
            model_names = [model["name"] for model in models]
            
            print(f"Connected to Ollama (version {version})")
            print(f"Available models: {', '.join(model_names)}")
            
            return True, model_names
        except Exception as e:
            print(f"Error connecting to Ollama: {e}")
            return False, []
    
    def scan_directory(self, directory, extensions=None):
        """Scan a directory for files and store their content"""
        if extensions is None:
            extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.csv']
        
        print(f"Scanning directory: {directory}")
        file_count = 0
        processed_count = 0
        
        for root, _, files in os.walk(directory):
            for file in files:
                file_count += 1
                if file_count % 100 == 0:
                    print(f"Scanned {file_count} files, processed {processed_count}...")
                
                # Check if file has one of the desired extensions
                file_ext = os.path.splitext(file)[1].lower()
                if extensions and file_ext not in extensions:
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    # Get file info
                    file_info = {
                        'path': file_path,
                        'filename': file,
                        'extension': file_ext,
                        'size': os.path.getsize(file_path),
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    }
                    
                    # Read file content (text files only)
                    content = self._read_file_content(file_path)
                    if content:
                        file_info['content'] = content
                        self.documents.append(file_info)
                        processed_count += 1
                        
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
        
        print(f"Scan complete. Found {file_count} files, processed {processed_count}.")
        return processed_count
    
    def _read_file_content(self, file_path, max_size=1000000):
        """Read content from a file, only if it's likely to be text"""
        # Skip files that are too large
        if os.path.getsize(file_path) > max_size:
            return None
            
        # Try to read as text
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                # Check if content is likely text (not binary)
                if '\0' in content:
                    return None
                return content
        except Exception:
            return None
    
    def query_ollama(self, query, model="llama3", max_documents=5):
        """Query Ollama with document context"""
        # Prepare context from documents
        context = ""
        for i, doc in enumerate(self.documents[:max_documents]):
            # Add filename and snippet of content
            if 'content' in doc:
                snippet = doc['content'][:300] + "..." if len(doc['content']) > 300 else doc['content']
                context += f"\nDocument {i+1}: {doc['filename']}\n{snippet}\n"
        
        # Create the prompt
        prompt = f"""Below is information from several documents:
{context}

Based on the above documents, answer the following question:
{query}

If the answer is not in the documents, say so."""
        
        print(f"Sending query to Ollama model '{model}'...")
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False}
            )
            result = response.json().get("response", "No response received")
            return result
        except Exception as e:
            print(f"Error querying Ollama: {e}")
            return f"Error: {str(e)}"

def main():
    print("Document Scanner and Ollama Query Tool")
    print("=====================================")
    
    # Initialize scanner
    scanner = SimpleDocumentScanner()
    
    # Check Ollama connection
    ollama_ok, available_models = scanner.check_ollama()
    if not ollama_ok:
        print("Cannot continue without Ollama connection.")
        return
        
    # Select default model
    default_model = "llama3"
    if default_model not in available_models and available_models:
        default_model = available_models[0]
        print(f"Model 'llama3' not found. Using '{default_model}' as default instead.")
    
    # Get directory to scan
    default_dir = os.path.join(os.path.expanduser("~"), "Documents")
    directory = input(f"Enter directory to scan (default: {default_dir}): ") or default_dir
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
    
    # Get file extensions
    default_extensions = ".txt,.md,.py,.js,.html,.css,.json,.csv"
    extensions_input = input(f"Enter file extensions to include (default: {default_extensions}): ") or default_extensions
    extensions = [f".{ext.strip()}" if not ext.strip().startswith('.') else ext.strip() for ext in extensions_input.split(",")]
    
    # Scan directory
    scanner.scan_directory(directory, extensions)
    
    if not scanner.documents:
        print("No documents were processed. Cannot continue.")
        return
    
    # Interactive query loop
    print("\nSetup complete! You can now ask questions about your documents.")
    
    while True:
        query = input("\nEnter a query (or 'quit' to exit): ")
        if query.lower() in ['quit', 'exit', 'q']:
            break
            
        model_input = input(f"Enter Ollama model to use (default: {default_model}): ") or default_model
        
        # Check if model exists
        if model_input not in available_models:
            print(f"Warning: Model '{model_input}' not found in available models. Will try anyway.")
        
        response = scanner.query_ollama(query, model_input)
        print("\nResponse:")
        print(response)

if __name__ == "__main__":
    main()
