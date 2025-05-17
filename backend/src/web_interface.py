# web_interface.py
import os
import gradio as gr
from enhanced_document_scanner import EnhancedDocumentScanner
import tempfile
import shutil

# Initialize scanner
scanner = EnhancedDocumentScanner()

# Check Ollama connection
ollama_ok, available_models = scanner.check_ollama()
if not ollama_ok:
    print("Warning: Cannot connect to Ollama. The interface will not function correctly.")
    available_models = []

# Global state to track uploaded files
temp_dir = tempfile.mkdtemp()
uploaded_files = []

def process_uploaded_files(files):
    """Process uploaded files and add them to the scanner"""
    global uploaded_files
    
    # Clear previous uploaded files
    for file in uploaded_files:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass
    
    uploaded_files = []
    
    # Save new uploaded files
    for file in files:
        file_name = os.path.basename(file.name)
        save_path = os.path.join(temp_dir, file_name)
        shutil.copy(file.name, save_path)
        uploaded_files.append(save_path)
    
    # Process the files
    processed_count = 0
    for file_path in uploaded_files:
        try:
            # Determine file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # Check if we can process this file type
            if file_ext in scanner.loaders:
                scanner.scan_directory(os.path.dirname(file_path), [file_ext])
                processed_count += 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    
    return f"Processed {processed_count} files successfully."

def scan_directory(directory, extensions, max_files):
    """Scan a directory for documents"""
    if not os.path.isdir(directory):
        return f"Error: {directory} is not a valid directory"
    
    # Process extensions input
    if extensions.strip():
        ext_list = [ext.strip() if ext.strip().startswith('.') else f".{ext.strip()}" 
                   for ext in extensions.split(",")]
    else:
        ext_list = list(scanner.loaders.keys())
    
    # Scan directory
    processed_count = scanner.scan_directory(directory, ext_list, max_files=max_files)
    
    return f"Scanned directory and processed {processed_count} files."

def query_documents(query, model_name, num_results):
    """Query documents using Ollama"""
    if not query.strip():
        return "Please enter a query."
    
    if not scanner.documents:
        return "No documents have been processed. Please scan a directory or upload files first."
    
    # Get response from Ollama
    response = scanner.query_ollama(query, model_name, max_documents=num_results)
    
    return response

# Create Gradio interface
with gr.Blocks(title="Document Scanner and LLM Query Tool") as demo:
    gr.Markdown("# Document Scanner and LLM Query Tool")
    gr.Markdown("Scan directories for documents, then ask questions about them using your local LLMs.")
    
    with gr.Tab("Upload Files"):
        with gr.Row():
            upload_input = gr.File(file_count="multiple", label="Upload Files")
            upload_output = gr.Textbox(label="Upload Status")
        
        upload_button = gr.Button("Process Uploaded Files")
        upload_button.click(process_uploaded_files, inputs=[upload_input], outputs=[upload_output])
    
    with gr.Tab("Scan Directory"):
        with gr.Row():
            dir_input = gr.Textbox(label="Directory Path", placeholder="Enter path to scan")
            extensions_input = gr.Textbox(
                label="File Extensions", 
                placeholder="Enter extensions (e.g., .txt,.pdf,.docx)",
                value=".txt,.pdf,.docx,.md"
            )
            max_files_input = gr.Number(label="Max Files", value=1000, minimum=1)
        
        scan_button = gr.Button("Scan Directory")
        scan_output = gr.Textbox(label="Scan Results")
        
        scan_button.click(
            scan_directory, 
            inputs=[dir_input, extensions_input, max_files_input], 
            outputs=[scan_output]
        )
    
    with gr.Tab("Query Documents"):
        with gr.Row():
            query_input = gr.Textbox(label="Your Question", placeholder="Ask about your documents...")
            model_input = gr.Dropdown(choices=available_models, label="Select Model")
            num_results = gr.Slider(minimum=1, maximum=10, value=5, step=1, label="Number of Context Documents")
        
        query_button = gr.Button("Ask")
        answer_output = gr.Textbox(label="Answer")
        
        query_button.click(
            query_documents, 
            inputs=[query_input, model_input, num_results], 
            outputs=[answer_output]
        )
    
    gr.Markdown("## Current Status")
    if scanner.embedding_model:
        gr.Markdown("✅ Embedding model loaded successfully")
    else:
        gr.Markdown("❌ Embedding model not loaded")
        
    if scanner.vector_store:
        gr.Markdown("✅ Vector store initialized")
    else:
        gr.Markdown("❌ Vector store not initialized")
        
    if ollama_ok:
        gr.Markdown(f"✅ Connected to Ollama (version {scanner.version if hasattr(scanner, 'version') else 'unknown'})")
        gr.Markdown(f"Available models: {', '.join(available_models)}")
    else:
        gr.Markdown("❌ Not connected to Ollama")

# Clean up temp directory on exit
import atexit
def cleanup():
    try:
        shutil.rmtree(temp_dir)
    except:
        pass
atexit.register(cleanup)

# Launch the interface
if __name__ == "__main__":
    demo.launch()
