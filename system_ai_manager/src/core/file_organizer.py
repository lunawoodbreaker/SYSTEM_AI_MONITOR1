import os
import shutil
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path
import requests
from datetime import datetime

@dataclass
class FileInfo:
    path: str
    name: str
    extension: str
    size: int
    last_modified: datetime
    type: str  # file, directory
    content_type: Optional[str]  # For files: text, binary, image, etc.
    category: Optional[str]  # Determined by AI analysis

@dataclass
class OrganizationPlan:
    current_structure: Dict[str, Any]
    suggested_structure: Dict[str, Any]
    moves: List[Dict[str, str]]
    categories: Dict[str, List[str]]
    recommendations: List[str]

class FileOrganizer:
    """AI-driven file system organization tool."""
    
    def __init__(self, settings):
        self.settings = settings
        self.content_types = {
            'text': ['.txt', '.md', '.rst', '.log'],
            'code': ['.py', '.js', '.java', '.cpp', '.h', '.cs', '.php', '.rb', '.go'],
            'document': ['.doc', '.docx', '.pdf', '.odt', '.rtf'],
            'spreadsheet': ['.xls', '.xlsx', '.csv', '.ods'],
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp'],
            'video': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv'],
            'audio': ['.mp3', '.wav', '.ogg', '.flac', '.m4a'],
            'archive': ['.zip', '.rar', '.7z', '.tar', '.gz'],
            'executable': ['.exe', '.msi', '.app', '.dmg'],
            'config': ['.json', '.yaml', '.yml', '.xml', '.ini', '.conf', '.toml']
        }
    
    def analyze_directory(self, directory: str) -> Dict[str, Any]:
        """Analyze a directory structure and its contents."""
        try:
            file_info_list = []
            total_size = 0
            file_count = 0
            dir_count = 0
            
            for root, dirs, files in os.walk(directory):
                # Analyze directories
                for dir_name in dirs:
                    dir_path = os.path.join(root, dir_name)
                    dir_info = FileInfo(
                        path=dir_path,
                        name=dir_name,
                        extension='',
                        size=0,
                        last_modified=datetime.fromtimestamp(os.path.getmtime(dir_path)),
                        type='directory',
                        content_type=None,
                        category=None
                    )
                    file_info_list.append(dir_info)
                    dir_count += 1
                
                # Analyze files
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    try:
                        size = os.path.getsize(file_path)
                        extension = os.path.splitext(file_name)[1].lower()
                        
                        file_info = FileInfo(
                            path=file_path,
                            name=file_name,
                            extension=extension,
                            size=size,
                            last_modified=datetime.fromtimestamp(os.path.getmtime(file_path)),
                            type='file',
                            content_type=self._get_content_type(extension),
                            category=None
                        )
                        file_info_list.append(file_info)
                        total_size += size
                        file_count += 1
                    except Exception as e:
                        print(f"Error analyzing file {file_path}: {str(e)}")
            
            return {
                "directory": directory,
                "total_size": total_size,
                "file_count": file_count,
                "dir_count": dir_count,
                "files": [self._file_info_to_dict(f) for f in file_info_list]
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _get_content_type(self, extension: str) -> Optional[str]:
        """Determine the content type based on file extension."""
        for content_type, extensions in self.content_types.items():
            if extension in extensions:
                return content_type
        return None
    
    def _file_info_to_dict(self, file_info: FileInfo) -> Dict[str, Any]:
        """Convert FileInfo object to dictionary."""
        return {
            "path": file_info.path,
            "name": file_info.name,
            "extension": file_info.extension,
            "size": file_info.size,
            "last_modified": file_info.last_modified.isoformat(),
            "type": file_info.type,
            "content_type": file_info.content_type,
            "category": file_info.category
        }
    
    def get_organization_plan(self, analysis: Dict[str, Any]) -> OrganizationPlan:
        """Get AI-driven organization plan for the directory."""
        try:
            # Prepare context for AI
            context = f"""I'm analyzing a directory with the following structure:
{json.dumps(analysis, indent=2)}

Please suggest:
1. A logical directory structure
2. Categories for files and directories
3. Specific moves to reorganize the content
4. Best practices for organization

Consider:
- File types and content
- Project organization
- Common patterns
- Accessibility
- Maintainability"""

            # Get AI suggestions
            response = requests.post(
                f"{self.settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": self.settings.get("ollama.models.text"),
                    "prompt": context,
                    "stream": False
                }
            )
            
            if response.status_code != 200:
                raise Exception(f"Error getting AI response: {response.status_code}")
            
            ai_suggestions = response.json().get("response", "")
            
            # Parse AI suggestions into structured plan
            plan = self._parse_ai_suggestions(ai_suggestions, analysis)
            
            return plan
            
        except Exception as e:
            raise Exception(f"Error generating organization plan: {str(e)}")
    
    def _parse_ai_suggestions(self, suggestions: str, analysis: Dict[str, Any]) -> OrganizationPlan:
        """Parse AI suggestions into a structured organization plan."""
        # This is a simplified version - in practice, you'd want more sophisticated parsing
        categories = {}
        moves = []
        recommendations = []
        
        # Extract categories and moves from AI suggestions
        lines = suggestions.split('\n')
        current_category = None
        
        for line in lines:
            line = line.strip()
            if line.startswith('Category:'):
                current_category = line.split(':', 1)[1].strip()
                categories[current_category] = []
            elif line.startswith('Move:'):
                move = line.split(':', 1)[1].strip()
                if '->' in move:
                    src, dst = move.split('->')
                    moves.append({
                        "source": src.strip(),
                        "destination": dst.strip()
                    })
            elif line.startswith('Recommendation:'):
                recommendations.append(line.split(':', 1)[1].strip())
        
        # Create suggested structure
        suggested_structure = self._create_suggested_structure(analysis, categories, moves)
        
        return OrganizationPlan(
            current_structure=analysis,
            suggested_structure=suggested_structure,
            moves=moves,
            categories=categories,
            recommendations=recommendations
        )
    
    def _create_suggested_structure(self, analysis: Dict[str, Any], 
                                  categories: Dict[str, List[str]], 
                                  moves: List[Dict[str, str]]) -> Dict[str, Any]:
        """Create a suggested directory structure based on AI recommendations."""
        structure = {
            "root": analysis["directory"],
            "categories": {},
            "moves": moves
        }
        
        # Organize files into categories
        for file_info in analysis["files"]:
            for category, patterns in categories.items():
                if any(pattern in file_info["path"].lower() for pattern in patterns):
                    if category not in structure["categories"]:
                        structure["categories"][category] = []
                    structure["categories"][category].append(file_info)
        
        return structure
    
    def execute_plan(self, plan: OrganizationPlan, dry_run: bool = True) -> Dict[str, Any]:
        """Execute the organization plan."""
        results = {
            "success": [],
            "failed": [],
            "skipped": []
        }
        
        for move in plan.moves:
            src = move["source"]
            dst = move["destination"]
            
            try:
                if not os.path.exists(src):
                    results["skipped"].append({
                        "source": src,
                        "reason": "Source does not exist"
                    })
                    continue
                
                if not dry_run:
                    # Create destination directory if it doesn't exist
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    
                    # Move the file/directory
                    shutil.move(src, dst)
                    
                    results["success"].append({
                        "source": src,
                        "destination": dst
                    })
                else:
                    results["success"].append({
                        "source": src,
                        "destination": dst,
                        "status": "would be moved"
                    })
                    
            except Exception as e:
                results["failed"].append({
                    "source": src,
                    "destination": dst,
                    "error": str(e)
                })
        
        return results 