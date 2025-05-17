# improved_document_scanner.py
import os
import requests
import json
from datetime import datetime
import mimetypes  # This is a built-in module

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
    
    def scan_directory(self, directory, extensions=None, verbose=True, max_files=1000):
        """Scan a directory for files and store their content"""
        if extensions is None:
            extensions = ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.csv']
        
        # Print selected extensions
        print(f"Looking for files with extensions: {', '.join(extensions)}")
        print(f"Scanning directory: {directory}")
        
        file_count = 0
        processed_count = 0
        
        # Walk through directory
        for root, _, files in os.walk(directory):
            for file in files:
                file_count += 1
                if verbose and file_count % 100 == 0:
                    print(f"Scanned {file_count} files, processed {processed_count}...")
                
                # Check if we've reached the max files limit
                if max_files and file_count > max_files:
                    print(f"Reached maximum file limit ({max_files}). Stopping scan.")
                    break
                
                # Check if file has one of the desired extensions
                file_ext = os.path.splitext(file)[1].lower()
                if extensions and file_ext not in extensions:
                    continue
                
                file_path = os.path.join(root, file)
                
                try:
                    # Check file size first
                    file_size = os.path.getsize(file_path)
                    if file_size > 1000000:  # Skip files > 1MB
                        print(f"Skipping large file: {file_path} ({file_size/1000000:.2f} MB)")
                        continue
                    
                    # Get file info
                    file_info = {
                        'path': file_path,
                        'filename': file,
                        'extension': file_ext,
                        'size': file_size,
                        'modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                    }
                    
                    # Try to determine if it's a text file
                    mime_type, _ = mimetypes.guess_type(file_path)
                    if mime_type and ('text/' in mime_type or mime_type in ['application/json', 'application/javascript']):
                        file_info['mime_type'] = mime_type
                    else:
                        # Try to peek at the file to determine if it might be text
                        is_text = self._is_likely_text(file_path)
                        if not is_text:
                            continue
                    
                    # Read file content
                    content = self._read_file_content(file_path)
                    if content:
                        file_info['content'] = content
                        self.documents.append(file_info)
                        processed_count += 1
                        print(f"Processed: {file_path}")
                        
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
        
        print(f"Scan complete. Found {file_count} files, processed {processed_count}.")
        return processed_count
    
    def _is_likely_text(self, file_path, sample_size=512):
        """Check if a file is likely to be text by examining a sample"""
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(sample_size)
                if not sample:  # Empty file
                    return False
            
            # Check for null bytes (common in binary files)
            if b'\x00' in sample:
                return False
            
            # Count printable ASCII characters
            printable_count = sum(32 <= b <= 126 or b in (9, 10, 13) for b in sample)
            printable_ratio = printable_count / len(sample) if sample else 0
            return printable_ratio > 0.7  # If more than 70% is printable ASCII, likely text
        except Exception as e:
            print(f"Error checking if file is text: {e}")
            return False
    
    def _read_file_content(self, file_path):
        """Read content from a file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    def query_ollama(self, query, model="llama3", max_documents=5):
        """Query Ollama with document context"""
        if not self.documents:
            return "No documents have been processed. Please scan a directory with text files first."
        
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
    print("Improved Document Scanner and Ollama Query Tool")
    print("=============================================")
    
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
    default_dir = os.path.expanduser("~/Documents")
    directory = input(f"Enter directory to scan (default: {default_dir}): ") or default_dir
    
    if not os.path.isdir(directory):
        print(f"Error: {directory} is not a valid directory")
        return
    
    # Get file extensions
    default_extensions = ".txt,.md,.py,.js,.html,.css,.json,.csv"
    extensions_input = input(f"Enter file extensions to include (default: {default_extensions}): ") or default_extensions
    extensions = [ext.strip() if ext.strip().startswith('.') else f".{ext.strip()}" for ext in extensions_input.split(",")]
    
    # Get max files
    try:
        max_files = int(input("Maximum number of files to scan (default: 1000): ") or 1000)
    except ValueError:
        max_files = 1000
        print("Invalid number. Using default of 1000 files.")
    
    # Scan directory
    scanner.scan_directory(directory, extensions, max_files=max_files)
    
    if not scanner.documents:
        print("\nNo text documents were found or processed. Try a different directory or file extensions.")
        
        # Ask if they want to try a different directory
        retry = input("Would you like to try a different directory? (y/n): ")
        if retry.lower() == 'y':
            directory = input("Enter a new directory path: ")
            if os.path.isdir(directory):
                scanner.scan_directory(directory, extensions, max_files=max_files)
        
        if not scanner.documents:
            print("Still no documents processed. Cannot continue with queries.")
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
