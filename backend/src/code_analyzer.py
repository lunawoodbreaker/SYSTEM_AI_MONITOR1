# code_analyzer.py
import os
import re
import sys
import json
from typing import List, Dict, Any, Optional, Tuple
import requests
from pathlib import Path

class CodeAnalyzer:
    def __init__(self, ollama_url="http://localhost:11434"):
        """Initialize the code analyzer with connection to Ollama"""
        self.ollama_url = ollama_url
        self.code_files = []
        self.file_contents = {}
        self.supported_extensions = {
            # Programming languages
            '.py': 'Python',
            '.js': 'JavaScript',
            '.ts': 'TypeScript',
            '.jsx': 'React JSX',
            '.tsx': 'React TSX',
            '.html': 'HTML',
            '.css': 'CSS',
            '.scss': 'SCSS',
            '.sass': 'Sass',
            '.less': 'Less',
            '.java': 'Java',
            '.c': 'C',
            '.cpp': 'C++',
            '.h': 'C/C++ Header',
            '.cs': 'C#',
            '.go': 'Go',
            '.rs': 'Rust',
            '.rb': 'Ruby',
            '.php': 'PHP',
            '.swift': 'Swift',
            '.kt': 'Kotlin',
            '.scala': 'Scala',
            
            # Configuration files
            '.json': 'JSON',
            '.yaml': 'YAML',
            '.yml': 'YAML',
            '.toml': 'TOML',
            '.xml': 'XML',
            '.ini': 'INI',
            '.conf': 'Configuration',
            '.config': 'Configuration',
            
            # Build files
            '.cmake': 'CMake',
            '.makefile': 'Makefile',
            '.mk': 'Makefile',
            '.dockerfile': 'Dockerfile',
            '.jenkinsfile': 'Jenkinsfile',
        }
    
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
    
    def scan_directory(self, directory: str, recursive: bool = True) -> int:
        """Scan a directory for code files"""
        if not os.path.isdir(directory):
            print(f"Error: {directory} is not a valid directory")
            return 0
        
        print(f"Scanning directory: {directory}")
        file_count = 0
        
        # Walk through directory if recursive, otherwise just list files
        if recursive:
            for root, _, files in os.walk(directory):
                file_count += self._process_files(root, files)
        else:
            file_count += self._process_files(directory, os.listdir(directory))
        
        print(f"Scan complete. Found {file_count} code files.")
        return file_count
    
    def _process_files(self, directory: str, files: List[str]) -> int:
        """Process files in a directory"""
        file_count = 0
        
        for file in files:
            file_path = os.path.join(directory, file)
            
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Check extension
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext not in self.supported_extensions:
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Store file info
                relative_path = os.path.relpath(file_path)
                self.code_files.append({
                    'path': file_path,
                    'relative_path': relative_path,
                    'language': self.supported_extensions[file_ext],
                    'extension': file_ext,
                    'size': len(content),
                    'lines': content.count('\n') + 1
                })
                
                # Store content
                self.file_contents[file_path] = content
                
                file_count += 1
                print(f"Processed: {relative_path} ({self.supported_extensions[file_ext]})")
            except Exception as e:
                print(f"Error processing file {file_path}: {e}")
        
        return file_count
    
    def get_code_summary(self) -> Dict[str, Any]:
        """Get a summary of the code in the project"""
        if not self.code_files:
            return {"error": "No code files have been scanned yet."}
        
        # Gather statistics
        language_stats = {}
        total_lines = 0
        total_size = 0
        
        for file in self.code_files:
            lang = file['language']
            if lang not in language_stats:
                language_stats[lang] = {
                    'files': 0,
                    'lines': 0,
                    'size': 0
                }
            
            language_stats[lang]['files'] += 1
            language_stats[lang]['lines'] += file['lines']
            language_stats[lang]['size'] += file['size']
            
            total_lines += file['lines']
            total_size += file['size']
        
        return {
            'total_files': len(self.code_files),
            'total_lines': total_lines,
            'total_size': total_size,
            'languages': language_stats
        }
    
    def analyze_code_structure(self, model: str = "qwen2.5-coder:7b") -> str:
        """Analyze the structure of the codebase using an LLM"""
        if not self.code_files:
            return "No code files have been scanned yet."
        
        # Create a project overview
        summary = self.get_code_summary()
        
        # Generate a file tree
        file_tree = self._generate_file_tree()
        
        # Get a sample of important files
        file_samples = self._get_file_samples(max_samples=10, max_lines=50)
        
        # Prepare prompt
        prompt = f"""Analyze this codebase structure and provide insights:

## Project Summary
- Total Files: {summary['total_files']}
- Total Lines of Code: {summary['total_lines']}
- Languages: {', '.join(summary['languages'].keys())}

## File Structure
{file_tree}

## Code Samples
{file_samples}

Based on this information, please provide:
1. An overview of the project structure and purpose
2. The main components and their relationships
3. Potential architecture patterns being used
4. Any issues or improvements you can identify from the structure
"""
        
        print(f"Sending code analysis request to Ollama model '{model}'...")
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
    
    def find_code_patterns(self, pattern: str, files_filter: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Find code matching a regex pattern"""
        if not self.code_files:
            return [{"error": "No code files have been scanned yet."}]
        
        try:
            compiled_pattern = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            return [{"error": f"Invalid regex pattern: {e}"}]
        
        results = []
        
        for file_path, content in self.file_contents.items():
            # Check if file should be included based on filter
            if files_filter:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in files_filter:
                    continue
            
            # Search for pattern
            matches = compiled_pattern.finditer(content)
            for match in matches:
                # Get line number
                line_num = content[:match.start()].count('\n') + 1
                
                # Get context lines
                lines = content.split('\n')
                start_line = max(1, line_num - 2)
                end_line = min(len(lines), line_num + 2)
                context = '\n'.join(lines[start_line-1:end_line])
                
                results.append({
                    'file': file_path,
                    'line': line_num,
                    'match': match.group(0),
                    'context': context
                })
        
        return results
    
    def modify_code(self, file_path: str, modification_function, llm_guidance: bool = False, model: str = "qwen2.5-coder:7b") -> Tuple[bool, str]:
        """Modify code using a function or LLM guidance"""
        if file_path not in self.file_contents:
            return False, f"File {file_path} not found in scanned files."
        
        original_content = self.file_contents[file_path]
        
        if llm_guidance:
            # Use LLM to generate modified code
            prompt = f"""Below is the content of the file {file_path}. Please modify this code based on the specific instructions.

Instructions: {modification_function}

Original Code:Provide only the complete modified code as output, without any explanations or markdown formatting. The output should be ready to save directly as a file.
"""
            
            try:
                print(f"Sending code modification request to Ollama model '{model}'...")
                response = requests.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": model, "prompt": prompt, "stream": False}
                )
                modified_content = response.json().get("response", "")
                
                # Clean up the response if it contains markdown code blocks
                if "```" in modified_content:
                    # Extract just the code from the markdown
                    code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", modified_content, re.DOTALL)
                    if code_blocks:
                        modified_content = code_blocks[0]
                    else:
                        # Try without language specification
                        code_blocks = re.findall(r"```\n(.*?)```", modified_content, re.DOTALL)
                        if code_blocks:
                            modified_content = code_blocks[0]
            except Exception as e:
                return False, f"Error modifying code with LLM: {e}"
        else:
            # Use function to modify code
            try:
                modified_content = modification_function(original_content)
            except Exception as e:
                return False, f"Error applying modification function: {e}"
        
        # Update in-memory content
        self.file_contents[file_path] = modified_content
        
        return True, modified_content
    
    def save_modified_file(self, file_path: str, backup: bool = True) -> Tuple[bool, str]:
        """Save modified file to disk"""
        if file_path not in self.file_contents:
            return False, f"File {file_path} not found in scanned files."
        
        try:
            # Create backup
            if backup:
                backup_path = f"{file_path}.bak"
                with open(backup_path, 'w', encoding='utf-8') as f:
                    with open(file_path, 'r', encoding='utf-8', errors='replace') as original:
                        f.write(original.read())
            
            # Write modified content
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.file_contents[file_path])
            
            return True, f"File saved successfully. Backup created at {backup_path if backup else 'No backup created'}."
        except Exception as e:
            return False, f"Error saving file: {e}"
    
    def batch_modify(self, pattern: str, replacement: str, files_filter: Optional[List[str]] = None) -> Dict[str, Any]:
        """Batch modify files using regex pattern"""
        if not self.code_files:
            return {"error": "No code files have been scanned yet."}
        
        try:
            compiled_pattern = re.compile(pattern, re.MULTILINE)
        except re.error as e:
            return {"error": f"Invalid regex pattern: {e}"}
        
        results = {
            "total_files_checked": 0,
            "files_modified": 0,
            "total_replacements": 0,
            "details": []
        }
        
        for file_path, content in self.file_contents.items():
            # Check if file should be included based on filter
            if files_filter:
                file_ext = os.path.splitext(file_path)[1].lower()
                if file_ext not in files_filter:
                    continue
            
            results["total_files_checked"] += 1
            
            # Perform replacement
            modified_content, count = compiled_pattern.subn(replacement, content)
            
            if count > 0:
                # Update in-memory content
                self.file_contents[file_path] = modified_content
                
                results["files_modified"] += 1
                results["total_replacements"] += count
                results["details"].append({
                    "file": file_path,
                    "replacements": count
                })
        
        return results
    
    def _generate_file_tree(self) -> str:
        """Generate a tree-like representation of the file structure"""
        if not self.code_files:
            return "No files scanned."
        
        # Group by directory
        file_structure = {}
        for file in self.code_files:
            path = file['relative_path']
            parts = os.path.normpath(path).split(os.sep)
            
            current = file_structure
            for i, part in enumerate(parts[:-1]):
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add the file
            current[parts[-1]] = file['language']
        
        # Generate tree representation
        tree_text = []
        self._render_tree(file_structure, tree_text)
        
        return '\n'.join(tree_text)
    
    def _render_tree(self, structure, lines, prefix=""):
        """Recursively render a tree structure"""
        items = list(structure.items())
        
        for i, (name, value) in enumerate(items):
            is_last = i == len(items) - 1
            
            # Determine current line prefix and next level prefix
            current_prefix = prefix + ("└── " if is_last else "├── ")
            next_prefix = prefix + ("    " if is_last else "│   ")
            
            # Add the current line
            if isinstance(value, dict):
                lines.append(f"{current_prefix}{name}/")
                self._render_tree(value, lines, next_prefix)
            else:
                lines.append(f"{current_prefix}{name} ({value})")
    
    def _get_file_samples(self, max_samples=5, max_lines=30) -> str:
        """Get sample content from important files"""
        if not self.code_files:
            return "No files scanned."
        
        # Find important files (main files, config files, etc.)
        important_patterns = [
            r"main\.([a-zA-Z]+)$",   # main.py, main.js, etc.
            r"index\.([a-zA-Z]+)$",  # index.js, index.ts, etc.
            r"config\.([a-zA-Z]+)$", # config files
            r"setup\.([a-zA-Z]+)$",  # setup files
            r"CMakeLists\.txt$",     # CMake files
            r"Makefile$",            # Makefiles
            r"BUILD$",               # BUILD files
            r"requirements\.txt$",   # Python requirements
            r"package\.json$"        # Node.js package files
        ]
        
        important_files = []
        for file in self.code_files:
            path = file['relative_path']
            filename = os.path.basename(path)
            
            for pattern in important_patterns:
                if re.search(pattern, filename, re.IGNORECASE):
                    important_files.append(file['path'])
                    break
        
        # If not enough important files, add some regular files
        if len(important_files) < max_samples:
            remaining = max_samples - len(important_files)
            for file in self.code_files:
                if file['path'] not in important_files:
                    important_files.append(file['path'])
                    remaining -= 1
                    if remaining <= 0:
                        break
        
        # Limit to max_samples
        important_files = important_files[:max_samples]
        
        # Get content samples
        samples = []
        for file_path in important_files:
            content = self.file_contents[file_path]
            lines = content.split('\n')
            
            # Limit lines
            if len(lines) > max_lines:
                lines = lines[:max_lines] + ["..."]
            
            sample = '\n'.join(lines)
            samples.append(f"### {os.path.basename(file_path)}\n```\n{sample}\n```")
        
        return '\n\n'.join(samples)

def main():
    print("Code Analyzer and Modifier")
    print("===========================")
    
    # Initialize analyzer
    analyzer = CodeAnalyzer()
    
    # Check Ollama connection
    ollama_ok, available_models = analyzer.check_ollama()
    if not ollama_ok:
        print("Warning: Cannot connect to Ollama. Some features will not work.")
    
    # Select default model for code tasks
    code_model = "qwen2.5-coder:7b"  # Default
    if available_models and code_model not in available_models:
        if any("coder" in model.lower() for model in available_models):
            # Find a coder model
            for model in available_models:
                if "coder" in model.lower():
                    code_model = model
                    break
        else:
            # Use any available model
            code_model = available_models[0]
    
    print(f"Using model '{code_model}' for code tasks")
    
    # Get directory to scan
    build_dir = input("Enter build directory to scan: ")
    if not os.path.isdir(build_dir):
        print(f"Error: {build_dir} is not a valid directory")
        return
    
    # Scan directory
    analyzer.scan_directory(build_dir)
    
    # Interactive menu
    while True:
        print("\nCode Analysis Options:")
        print("1. Show code summary")
        print("2. Analyze code structure")
        print("3. Find code patterns")
        print("4. Batch modify code")
        print("5. Modify specific file with AI")
        print("0. Exit")
        
        choice = input("\nEnter choice (0-5): ")
        
        if choice == '0':
            break
        
        elif choice == '1':
            summary = analyzer.get_code_summary()
            print("\nCode Summary:")
            print(f"Total Files: {summary['total_files']}")
            print(f"Total Lines: {summary['total_lines']}")
            print("\nLanguage Statistics:")
            for lang, stats in summary['languages'].items():
                print(f"  {lang}: {stats['files']} files, {stats['lines']} lines")
        
        elif choice == '2':
            print("\nAnalyzing code structure...")
            analysis = analyzer.analyze_code_structure(model=code_model)
            print("\nCode Structure Analysis:")
            print(analysis)
        
        elif choice == '3':
            pattern = input("Enter regex pattern to search for: ")
            file_filter = input("Filter by extensions (comma-separated, e.g. .py,.js) or leave empty for all: ")
            
            filters = None
            if file_filter.strip():
                filters = [ext.strip() if ext.strip().startswith('.') else f".{ext.strip()}" 
                          for ext in file_filter.split(",")]
            
            results = analyzer.find_code_patterns(pattern, filters)
            
            print(f"\nFound {len(results)} matches:")
            for i, match in enumerate(results):
                if 'error' in match:
                    print(f"Error: {match['error']}")
                    break
                    
                print(f"\nMatch {i+1}:")
                print(f"File: {match['file']}")
                print(f"Line: {match['line']}")
                print(f"Context:\n{match['context']}")
        
        elif choice == '4':
            pattern = input("Enter regex pattern to find: ")
            replacement = input("Enter replacement text: ")
            file_filter = input("Filter by extensions (comma-separated, e.g. .py,.js) or leave empty for all: ")
            
            filters = None
            if file_filter.strip():
                filters = [ext.strip() if ext.strip().startswith('.') else f".{ext.strip()}" 
                          for ext in file_filter.split(",")]
            
            confirm = input(f"This will modify matching files. Are you sure? (y/n): ")
            if confirm.lower() != 'y':
                print("Operation cancelled.")
                continue
            
            results = analyzer.batch_modify(pattern, replacement, filters)
            
            if 'error' in results:
                print(f"Error: {results['error']}")
            else:
                print(f"\nModified {results['files_modified']} files with {results['total_replacements']} replacements")
                
                save_confirm = input("Save changes to disk? (y/n): ")
                if save_confirm.lower() == 'y':
                    for detail in results['details']:
                        file_path = detail['file']
                        success, message = analyzer.save_modified_file(file_path)
                        print(f"File {file_path}: {'Saved' if success else 'Error - ' + message}")
        
        elif choice == '5':
            # List files for selection
            print("\nAvailable files:")
            for i, file in enumerate(analyzer.code_files):
                print(f"{i+1}. {file['relative_path']} ({file['language']})")
            
            try:
                file_idx = int(input("Enter file number to modify: ")) - 1
                if file_idx < 0 or file_idx >= len(analyzer.code_files):
                    print("Invalid file number.")
                    continue
                
                file_path = analyzer.code_files[file_idx]['path']
                instructions = input("Enter modification instructions for the AI: ")
                
                success, modified = analyzer.modify_code(file_path, instructions, llm_guidance=True, model=code_model)
                
                if success:
                    print("\nModified Code:")
                    print("----------------------------")
                    print(modified[:1000] + "..." if len(modified) > 1000 else modified)
                    print("----------------------------")
                    
                    save_confirm = input("Save changes to disk? (y/n): ")
                    if save_confirm.lower() == 'y':
                        success, message = analyzer.save_modified_file(file_path)
                        print(f"File {file_path}: {'Saved' if success else 'Error - ' + message}")
                else:
                    print(f"Error: {modified}")
            except ValueError:
                print("Invalid input. Please enter a number.")
        
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
