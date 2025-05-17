# document_processor.py
import os
from typing import List, Dict, Any, Optional
import magic

class Document:
    def __init__(self, content: str, metadata: Dict[str, Any]):
        self.content = content
        self.metadata = metadata

class DocumentProcessor:
    def __init__(self):
        self.supported_types = {
            'text/plain': self._process_text,
            'text/markdown': self._process_text,
            'text/csv': self._process_text,
            'application/json': self._process_text,
            'application/pdf': self._process_text_fallback,  # Simple fallback
            'application/msword': self._process_text_fallback,  # Simple fallback
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': self._process_text_fallback,
        }
    
    def process_file(self, file_path: str) -> Optional[Document]:
        """Process a file into a document with content and metadata"""
        if not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            return None
            
        try:
            # Detect file type
            mime = magic.Magic(mime=True)
            mime_type = mime.from_file(file_path)
            
            # Extract basic metadata
            metadata = {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'mime_type': mime_type,
                'size': os.path.getsize(file_path)
            }
            
            # Process based on mime type
            if mime_type in self.supported_types:
                processor = self.supported_types[mime_type]
                content = processor(file_path)
                if content:
                    return Document(content, metadata)
            else:
                # Try fallback based on extension
                ext = os.path.splitext(file_path)[1].lower()
                if ext in ['.txt', '.md', '.csv', '.json']:
                    content = self._process_text(file_path)
                    if content:
                        return Document(content, metadata)
                        
            print(f"Unsupported file type: {mime_type} for {file_path}")
            return None
            
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            return None
    
    def _process_text(self, file_path: str) -> str:
        """Process plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading text file {file_path}: {e}")
            return ""
            
    def _process_text_fallback(self, file_path: str) -> str:
        """Simple fallback for document types we can't fully process"""
        try:
            # Try to read as text first
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except:
            # If that fails, just return a placeholder
            return f"[Content of {os.path.basename(file_path)} - requires additional libraries to process]"
