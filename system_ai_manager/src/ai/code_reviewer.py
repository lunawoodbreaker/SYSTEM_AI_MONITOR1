import os
import json
import requests
from typing import Dict, List, Optional, Any, Tuple
import logging
from pathlib import Path
import asyncio
from dataclasses import dataclass
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReviewSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class CodeIssue:
    line_number: int
    severity: ReviewSeverity
    message: str
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None

class CodeReviewer:
    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_base_url = ollama_base_url
        self.models = {
            "code": "codellama",  # For code analysis
            "text": "mistral",    # For text analysis
            "security": "mistral" # For security analysis
        }
        self.review_pause_on_error = True
        
    async def review_code(self, file_path: str, content: Optional[str] = None) -> Tuple[List[CodeIssue], Dict[str, Any]]:
        """Review code and provide suggestions."""
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file for review: {str(e)}")
                return [], {"error": str(e)}
                
        # Split content into lines for line-specific analysis
        lines = content.split('\n')
        
        # First pass: Basic syntax and structure analysis
        issues = []
        try:
            # Analyze code structure
            structure_prompt = f"""Analyze this code and identify:
            1. Syntax errors
            2. Structural issues
            3. Potential bugs
            4. Code style violations
            5. Performance issues
            
            Code from {file_path}:
            {content}
            
            Format the response as a JSON array of issues, each with:
            - line_number: int
            - severity: "info"|"warning"|"error"|"critical"
            - message: string
            - suggestion: string (optional)
            - code_snippet: string (optional)
            """
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["code"],
                    "prompt": structure_prompt,
                    "stream": False
                }
            )
            
            analysis = response.json()
            if "response" in analysis:
                try:
                    issues_data = json.loads(analysis["response"])
                    for issue in issues_data:
                        issues.append(CodeIssue(
                            line_number=issue.get("line_number", 0),
                            severity=ReviewSeverity(issue.get("severity", "info")),
                            message=issue.get("message", ""),
                            suggestion=issue.get("suggestion"),
                            code_snippet=issue.get("code_snippet")
                        ))
                except json.JSONDecodeError:
                    logger.error("Failed to parse AI response as JSON")
                    
            # If we found critical issues and should pause
            if self.review_pause_on_error and any(i.severity in [ReviewSeverity.ERROR, ReviewSeverity.CRITICAL] for i in issues):
                logger.warning("Critical issues found. Review paused.")
                # Here you would typically trigger a UI prompt or notification
                
            # Second pass: Get improvement suggestions
            suggestions_prompt = f"""Based on this code, provide specific improvement suggestions:
            1. Code organization
            2. Performance optimizations
            3. Best practices
            4. Design patterns
            5. Testing recommendations
            
            Code from {file_path}:
            {content}
            """
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["code"],
                    "prompt": suggestions_prompt,
                    "stream": False
                }
            )
            
            suggestions = response.json()
            
            return issues, suggestions
            
        except Exception as e:
            logger.error(f"Error in code review: {str(e)}")
            return [], {"error": str(e)}
            
    async def review_text(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Review text content (documentation, comments, etc.)."""
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file for text review: {str(e)}")
                return {"error": str(e)}
                
        prompt = f"""Review this text content and provide:
        1. Grammar and spelling
        2. Clarity and readability
        3. Consistency
        4. Completeness
        5. Suggestions for improvement
        
        Content from {file_path}:
        {content}
        """
        
        try:
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.models["text"],
                    "prompt": prompt,
                    "stream": False
                }
            )
            return response.json()
        except Exception as e:
            logger.error(f"Error in text review: {str(e)}")
            return {"error": str(e)}
            
    async def suggest_code_improvements(self, file_path: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Get specific code improvement suggestions."""
        if content is None:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except Exception as e:
                logger.error(f"Error reading file for suggestions: {str(e)}")
                return {"error": str(e)}
                
        prompt = f"""Provide specific, actionable code improvement suggestions for:
        1. Code organization and structure
        2. Performance optimizations
        3. Best practices implementation
        4. Design pattern applications
        5. Testing strategies
        
        Include specific code examples for each suggestion.
        
        Code from {file_path}:
        {content}
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
            logger.error(f"Error getting code suggestions: {str(e)}")
            return {"error": str(e)}
            
    def set_pause_on_error(self, pause: bool):
        """Set whether to pause on critical issues."""
        self.review_pause_on_error = pause 