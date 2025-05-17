import os
import json
import requests
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.models = {
            "code": "codellama",  # For code analysis
            "system": "llama2",   # For system analysis
            "security": "mistral" # For security analysis
        }
        
    async def analyze_code_structure(self, code_content: str, file_path: str) -> Dict[str, Any]:
        """Analyze code structure using AI."""
        prompt = f"""Analyze this code and provide:
        1. Code structure and organization
        2. Potential issues or anti-patterns
        3. Suggestions for improvement
        4. Security concerns
        5. Performance considerations
        
        Code from {file_path}:
        {code_content}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["code"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in AI code analysis: {str(e)}")
            return {"error": str(e)}
            
    async def analyze_system_health(self, system_info: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze system health and security."""
        prompt = f"""Analyze this system information and provide:
        1. Outdated software/drivers
        2. Security vulnerabilities
        3. System optimization suggestions
        4. Potential issues
        
        System Info:
        {json.dumps(system_info, indent=2)}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["system"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in AI system analysis: {str(e)}")
            return {"error": str(e)}
            
    async def analyze_security(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Analyze file for security concerns."""
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file for security analysis: {str(e)}")
                return {"error": str(e)}
                
        prompt = f"""Analyze this file for security concerns:
        1. Malicious code patterns
        2. Data leakage risks
        3. Permission issues
        4. Security best practices
        
        File: {file_path}
        Content:
        {content}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["security"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in AI security analysis: {str(e)}")
            return {"error": str(e)}
            
    async def analyze_build_system(self, build_files: List[str]) -> Dict[str, Any]:
        """Analyze build system configuration."""
        build_content = {}
        for file in build_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    build_content[file] = f.read()
            except Exception as e:
                logger.error(f"Error reading build file {file}: {str(e)}")
                
        prompt = f"""Analyze these build system files and provide:
        1. Build system type and configuration
        2. Dependencies and versions
        3. Build process optimization
        4. Potential issues or improvements
        
        Build Files:
        {json.dumps(build_content, indent=2)}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["code"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in AI build analysis: {str(e)}")
            return {"error": str(e)}
            
    async def find_unused_files(self, directory: str, project_files: List[str]) -> Dict[str, Any]:
        """Find potentially unused files in the project."""
        prompt = f"""Analyze this project structure and identify:
        1. Potentially unused files
        2. Orphaned files
        3. Temporary files that should be cleaned
        4. Duplicate files
        
        Project Directory: {directory}
        Known Project Files: {json.dumps(project_files, indent=2)}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["system"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in AI unused files analysis: {str(e)}")
            return {"error": str(e)} 