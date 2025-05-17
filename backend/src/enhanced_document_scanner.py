# enhanced_document_scanner.py
import os
import requests
import json
from datetime import datetime
import mimetypes
from typing import List, Dict, Any, Optional
import tempfile
import uuid

# LangChain imports
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, Docx2txtLoader, 
    UnstructuredMarkdownLoader, CSVLoader, JSONLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

class EnhancedDocumentScanner:
    def __init__(self, persist_directory="./document_store"):
        """Initialize the document scanner with vector storage"""
        self.documents = []
        self.raw_documents = []
        self.ollama_url = "http://localhost:11434"
        self.persist_directory = persist_directory
        self.vector_store = None
        self.embedding_model = None
        
        # Ensure persist directory exists
        os.makedirs(self.persist_directory, exist_ok=True)
        
        # Initialize document loaders by extension
        self.loaders = {
            '.txt': TextLoader,
            '.md': UnstructuredMarkdownLoader,
            '.pdf': PyPDFLoader,
            '.docx': Docx2txtLoader,
            '.csv': CSVLoader,
            '.json': self._json_loader_factory
        }
        
        # Initialize embeddings and vector store
        self._initialize_embeddings()
        
    def _initialize_embeddings(self):
        """Initialize the embedding model and vector store"""
        try:
            print("Initializing embedding model...")
            self.embedding_model = HuggingFaceEmbeddings(
                model_name="BAAI/bge-small-en-v1.5"
            )
            
            # Check if vector store exists
            vector_store_exists = os.path.exists(os.path.join(self.persist_directory, "chroma.sqlite3"))
            
            if vector_store_exists:
                print("Loading existing vector store...")
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding_model
                )
                print(f"Loaded {self.vector_store._collection.count()} documents from vector store")
            else:
                print("Creating new vector store...")
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding_model
                )
        except Exception as e:
            print(f"Error initializing embeddings: {e}")
            self.embedding_model = None
            self.vector_store = None
    
    def _json_loader_factory(self, file_path):
        """Factory function for JSON loader to handle different JSON structures"""
        return JSONLoader(
            file_path=file_path,
            jq_schema=".",
            content_key="content"
        )
    
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
        """Scan a directory for files and process them into the vector store"""
        if extensions is None:
            extensions = list(self.loaders.keys())
        
        # Print selected extensions
        print(f"Looking for files with extensions: {', '.join(extensions)}")
        print(f"Scanning directory: {directory}")
        
        file_count = 0
        processed_count = 0
        
        # Walk through directory
        for root, _, files in os.walk(directory):
            for file in files:
                file_count += 1
                if verbose and file_count % 20 == 0:
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
                    if file_size > 10000000:  # Skip files > 10MB
                        print(f"Skipping large file: {file_path} ({file_size/1000000:.2f} MB)")
                        continue
                    
                    # Process file based on extension
                    if file_ext in self.loaders:
                        loader_class = self.loaders[file_ext]
                        print(f"Processing: {file_path}")
                        
                        # Load document
                        try:
                            loader = loader_class(file_path)
                            docs = loader.load()
                            
                            # Split documents into chunks
                            text_splitter = RecursiveCharacterTextSplitter(
                                chunk_size=1000,
                                chunk_overlap=200
                            )
                            split_docs = text_splitter.split_documents(docs)
                            
                            # Add to raw documents list
                            self.raw_documents.extend(docs)
                            
                            # Add to vector store if available
                            if self.vector_store is not None and self.embedding_model is not None:
                                self.vector_store.add_documents(split_docs)
                                
                            # Add to documents list for backup
                            for doc in split_docs:
                                self.documents.append({
                                    'content': doc.page_content,
                                    'metadata': doc.metadata
                                })
                            
                            processed_count += 1
                            print(f"Successfully processed: {file_path}")
                        except Exception as e:
                            print(f"Error loading document {file_path}: {e}")
                    elif self._is_likely_text(file_path):
                        # Fallback for text-like files not in loader dict
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                                content = f.read()
                                
                            metadata = {
                                'source': file_path,
                                'filename': file,
                                'extension': file_ext
                            }
                            
                            # Add to documents list
                            self.documents.append({
                                'content': content,
                                'metadata': metadata
                            })
                            
                            processed_count += 1
                            print(f"Processed as plain text: {file_path}")
                        except Exception as e:
                            print(f"Error processing text file {file_path}: {e}")
                        
                except Exception as e:
                    print(f"Error processing file {file_path}: {e}")
        
        # Persist the vector store
        if self.vector_store is not None:
            self.vector_store.persist()
        
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
    
    def query_documents(self, query, k=5):
        """Query the vector store for relevant documents"""
        if self.vector_store is None:
            print("Vector store not available. Using direct document search.")
            # Fallback to basic search in documents list
            results = []
            for doc in self.documents:
                content = doc['content'].lower()
                if query.lower() in content:
                    results.append(doc)
            return results[:k]
        
        # Use vector store for semantic search
        results = self.vector_store.similarity_search(query, k=k)
        return [{'content': doc.page_content, 'metadata': doc.metadata} for doc in results]
    
    def query_ollama(self, query, model="llama3", max_documents=5):
        """Query Ollama with semantically relevant document context"""
        # Get relevant documents
        relevant_docs = self.query_documents(query, k=max_documents)
        
        if not relevant_docs:
            return "No relevant documents found for your query. Please try a different question or scan more documents."
        
        # Prepare context from documents
        context = ""
        for i, doc in enumerate(relevant_docs):
            # Add document info and content
            source = doc['metadata'].get('source', 'Unknown')
            content = doc['content']
            context += f"\nDocument {i+1}: {os.path.basename(source)}\n{content}\n"
        
        # Create the prompt
        prompt = f"""Below is information from documents most relevant to the query:
{context}

Based on the above documents, please answer the following question:
{query}

If the answer cannot be determined from the documents, please say so clearly.
"""
        
        print(f"Sending query to Ollama model '{model}'...")
        print(f"Using {len(relevant_docs)} relevant document chunks for context")
        
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
    print("Enhanced Document Scanner and Semantic Search Tool")
    print("================================================")
    
    # Initialize scanner
    scanner = EnhancedDocumentScanner()
    
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
    available_extensions = ', '.join(scanner.loaders.keys())
    extensions_input = input(f"Enter file extensions to include (available: {available_extensions}, default: all): ")
    
    if extensions_input.strip():
        # Process user input for extensions
        extensions = [ext.strip() if ext.strip().startswith('.') else f".{ext.strip()}" 
                     for ext in extensions_input.split(",")]
    else:
        # Use all available loaders
        extensions = list(scanner.loaders.keys())
    
    # Get max files
    try:
        max_files = int(input("Maximum number of files to scan (default: 1000): ") or 1000)
    except ValueError:
        max_files = 1000
        print("Invalid number. Using default of 1000 files.")
    
    # Scan directory
    scanner.scan_directory(directory, extensions, max_files=max_files)
    
    if not scanner.documents:
        print("\nNo documents were found or processed. Try a different directory or file extensions.")
        
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
    print("\nSetup complete! You can now ask semantic questions about your documents.")
    print("Documents have been stored in a vector database for semantic retrieval.")
    
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
