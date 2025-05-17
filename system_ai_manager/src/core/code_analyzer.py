import os
import json
from typing import Dict, List, Optional
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CodeAnalyzer:
    def __init__(self, root_dir: str):
        self.root_dir = Path(root_dir)
        self.analysis_results: Dict[str, Dict] = {}
        
    def analyze_file(self, file_path: str) -> Dict:
        """Analyze a single file and return its metadata and structure."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            file_info = {
                'path': str(file_path),
                'size': os.path.getsize(file_path),
                'last_modified': os.path.getmtime(file_path),
                'content': content,
                'language': self._detect_language(file_path),
                'complexity': self._calculate_complexity(content)
            }
            
            self.analysis_results[str(file_path)] = file_info
            return file_info
            
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {str(e)}")
            return {}
            
    def _detect_language(self, file_path: str) -> str:
        """Detect the programming language of a file based on its extension."""
        ext = os.path.splitext(file_path)[1].lower()
        language_map = {
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.java': 'Java',
            '.cpp': 'C++',
            '.c': 'C',
            '.h': 'C/C++ Header',
            '.html': 'HTML',
            '.css': 'CSS',
            '.json': 'JSON',
            '.md': 'Markdown'
        }
        return language_map.get(ext, 'Unknown')
        
    def _calculate_complexity(self, content: str) -> int:
        """Calculate a simple complexity score for the code."""
        # Basic complexity calculation based on:
        # - Number of lines
        # - Number of control structures
        # - Number of function definitions
        lines = content.split('\n')
        control_structures = sum(1 for line in lines if any(keyword in line for keyword in 
            ['if ', 'for ', 'while ', 'switch ', 'case ']))
        functions = sum(1 for line in lines if 'def ' in line or 'function ' in line)
        
        return len(lines) + control_structures * 2 + functions * 3
        
    def analyze_directory(self, directory: Optional[str] = None) -> Dict[str, Dict]:
        """Analyze all files in a directory recursively."""
        target_dir = Path(directory) if directory else self.root_dir
        
        for root, _, files in os.walk(target_dir):
            for file in files:
                file_path = os.path.join(root, file)
                self.analyze_file(file_path)
                
        return self.analysis_results
        
    def save_analysis(self, output_file: str):
        """Save the analysis results to a JSON file."""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.analysis_results, f, indent=2)
            logger.info(f"Analysis results saved to {output_file}")
        except Exception as e:
            logger.error(f"Error saving analysis results: {str(e)}")
            
    def get_file_metadata(self, file_path: str) -> Dict:
        """Get metadata for a specific file."""
        return self.analysis_results.get(str(file_path), {}) 