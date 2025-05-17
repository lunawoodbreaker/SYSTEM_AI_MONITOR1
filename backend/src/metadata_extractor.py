# metadata_extractor.py
import os
import magic
from hachoir.parser import createParser
from hachoir.metadata import extractMetadata
from datetime import datetime

class MetadataExtractor:
    def extract_metadata(self, file_path):
        """Extract rich metadata from files without requiring ExifTool"""
        metadata = {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'extension': os.path.splitext(file_path)[1].lower(),
            'size_bytes': os.path.getsize(file_path),
            'size_human': self._format_size(os.path.getsize(file_path)),
            'last_modified': datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
            'created': datetime.fromtimestamp(os.path.getctime(file_path)).isoformat(),
        }
        
        # Get MIME type
        try:
            mime = magic.Magic(mime=True)
            metadata['mime_type'] = mime.from_file(file_path)
        except Exception as e:
            metadata['mime_type'] = "unknown/unknown"
            print(f"Error getting MIME type for {file_path}: {e}")
        
        # Extract file-specific metadata using hachoir
        try:
            parser = createParser(file_path)
            if parser:
                extracted_metadata = extractMetadata(parser)
                if extracted_metadata:
                    for line in extracted_metadata.exportPlaintext():
                        if ': ' in line:
                            key, value = line.split(': ', 1)
                            metadata[key.strip().lower().replace(' ', '_')] = value.strip()
        except Exception as e:
            print(f"Error extracting hachoir metadata from {file_path}: {e}")
            
        # For image files, try getting dimensions using Pillow
        if metadata['mime_type'].startswith('image/'):
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    metadata['width'] = img.width
                    metadata['height'] = img.height
                    metadata['format'] = img.format
                    if hasattr(img, 'info'):
                        for key, value in img.info.items():
                            if isinstance(value, (str, int, float, bool)):
                                metadata[f'image_{key}'] = value
            except Exception as e:
                print(f"Error extracting Pillow metadata from {file_path}: {e}")
                
        return metadata
    
    def _format_size(self, size_bytes):
        """Convert bytes to human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} PB"
