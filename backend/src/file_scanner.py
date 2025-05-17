# file_scanner.py
import os
import glob
import hashlib
from typing import List, Dict
from datetime import datetime

class FileSystemScanner:
    def __init__(self, root_dirs: List[str], file_extensions: List[str] = None):
        self.root_dirs = root_dirs
        self.file_extensions = file_extensions or ['.txt', '.pdf', '.docx', '.md', '.csv', '.json', '.py', '.js']
        self.file_index = {}
        
    def scan(self) -> Dict:
        """Scan the file system and build an index"""
        for root_dir in self.root_dirs:
            for ext in self.file_extensions:
                pattern = os.path.join(root_dir, f"**/*{ext}")
                for file_path in glob.glob(pattern, recursive=True):
                    if os.path.isfile(file_path):
                        self._index_file(file_path)
        return self.file_index
    
    def _index_file(self, file_path: str) -> None:
        """Add file metadata to the index"""
        try:
            stat = os.stat(file_path)
            file_hash = self._get_file_hash(file_path)
            
            self.file_index[file_path] = {
                'size': stat.st_size,
                'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
                'hash': file_hash,
                'extension': os.path.splitext(file_path)[1].lower()
            }
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
    
    def _get_file_hash(self, file_path: str, block_size=65536) -> str:
        """Get hash of file for change detection"""
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
