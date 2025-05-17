from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import requests
from pathlib import Path
import ast
import re
from datetime import datetime
from github import Github
from github.PullRequest import PullRequest
from github.Repository import Repository

@dataclass
class CollaborationConfig:
    """Configuration for team collaboration."""
    repo_url: str
    github_token: Optional[str] = None
    review_assignees: List[str] = None
    auto_merge: bool = False
    require_reviews: bool = True
    notify_on_review: bool = True
    code_quality_threshold: float = 0.8

class TeamCollaborator:
    """AI-driven team collaboration and code review system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = CollaborationConfig(repo_url="")
        self.github = None
        self.repo = None
        
    def initialize(self):
        """Initialize the collaboration system."""
        if self.config.github_token:
            self.github = Github(self.config.github_token)
            self.repo = self.github.get_repo(self.config.repo_url)
            
    def review_pull_request(self, pr_number: int) -> Dict[str, Any]:
        """Review a pull request and provide feedback."""
        try:
            # Get the pull request
            pr = self.repo.get_pull(pr_number)
            
            # Get the changes
            changes = self._get_changes(pr)
            
            # Analyze the changes
            analysis = self._analyze_changes(changes)
            
            # Generate review comments
            comments = self._generate_review_comments(analysis)
            
            # Post the review
            review = pr.create_review(
                body=self._generate_review_summary(analysis),
                event="COMMENT",
                comments=comments
            )
            
            # Notify reviewers if configured
            if self.config.notify_on_review:
                self._notify_reviewers(pr, review)
                
            return {
                "status": "success",
                "pr_number": pr_number,
                "review_id": review.id,
                "comments": len(comments),
                "analysis": analysis
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "pr_number": pr_number
            }
    
    def suggest_improvements(self, code: str) -> Dict[str, Any]:
        """Suggest code improvements."""
        try:
            # Analyze the code
            analysis = self._analyze_code(code)
            
            # Generate suggestions
            suggestions = self._generate_suggestions(analysis)
            
            return {
                "status": "success",
                "suggestions": suggestions,
                "quality_score": analysis["quality_score"]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def resolve_conflicts(self, branch: str) -> Dict[str, Any]:
        """Resolve merge conflicts in a branch."""
        try:
            # Get the branch
            branch_ref = self.repo.get_branch(branch)
            
            # Find conflicts
            conflicts = self._find_conflicts(branch)
            
            # Resolve conflicts
            resolutions = self._resolve_conflicts(conflicts)
            
            # Apply resolutions
            self._apply_resolutions(resolutions)
            
            return {
                "status": "success",
                "branch": branch,
                "conflicts_found": len(conflicts),
                "conflicts_resolved": len(resolutions)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "branch": branch
            }
    
    def track_changes(self, branch: str) -> Dict[str, Any]:
        """Track and analyze changes in a branch."""
        try:
            # Get the branch
            branch_ref = self.repo.get_branch(branch)
            
            # Get the changes
            changes = self._get_branch_changes(branch)
            
            # Analyze the changes
            analysis = self._analyze_changes(changes)
            
            # Generate report
            report = self._generate_change_report(analysis)
            
            return {
                "status": "success",
                "branch": branch,
                "changes": len(changes),
                "report": report
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "branch": branch
            }
    
    def _get_changes(self, pr: PullRequest) -> List[Dict[str, Any]]:
        """Get changes from a pull request."""
        changes = []
        
        # Get the files changed
        files = pr.get_files()
        
        for file in files:
            # Get the patch
            patch = file.patch
            
            # Parse the changes
            file_changes = self._parse_patch(patch)
            
            changes.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "changes": file_changes
            })
            
        return changes
    
    def _analyze_changes(self, changes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze code changes."""
        analysis = {
            "quality_score": 0.0,
            "issues": [],
            "suggestions": [],
            "metrics": {
                "total_changes": 0,
                "additions": 0,
                "deletions": 0,
                "complexity": 0
            }
        }
        
        for change in changes:
            # Update metrics
            analysis["metrics"]["total_changes"] += len(change["changes"])
            analysis["metrics"]["additions"] += change["additions"]
            analysis["metrics"]["deletions"] += change["deletions"]
            
            # Analyze each change
            for code_change in change["changes"]:
                # Calculate complexity
                complexity = self._calculate_complexity(code_change["code"])
                analysis["metrics"]["complexity"] += complexity
                
                # Check for issues
                issues = self._check_code_issues(code_change["code"])
                analysis["issues"].extend(issues)
                
                # Generate suggestions
                suggestions = self._generate_code_suggestions(code_change["code"])
                analysis["suggestions"].extend(suggestions)
                
        # Calculate quality score
        analysis["quality_score"] = self._calculate_quality_score(analysis)
        
        return analysis
    
    def _generate_review_comments(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate review comments from analysis."""
        comments = []
        
        # Add comments for issues
        for issue in analysis["issues"]:
            comments.append({
                "path": issue["file"],
                "position": issue["line"],
                "body": f"**Issue**: {issue['message']}\n\n{issue['suggestion']}"
            })
            
        # Add comments for suggestions
        for suggestion in analysis["suggestions"]:
            comments.append({
                "path": suggestion["file"],
                "position": suggestion["line"],
                "body": f"**Suggestion**: {suggestion['message']}\n\n{suggestion['example']}"
            })
            
        return comments
    
    def _generate_review_summary(self, analysis: Dict[str, Any]) -> str:
        """Generate a summary of the review."""
        summary = f"## Code Review Summary\n\n"
        
        # Add quality score
        summary += f"**Quality Score**: {analysis['quality_score']:.2f}\n\n"
        
        # Add metrics
        summary += "### Metrics\n\n"
        summary += f"- Total Changes: {analysis['metrics']['total_changes']}\n"
        summary += f"- Additions: {analysis['metrics']['additions']}\n"
        summary += f"- Deletions: {analysis['metrics']['deletions']}\n"
        summary += f"- Complexity: {analysis['metrics']['complexity']}\n\n"
        
        # Add issues
        if analysis["issues"]:
            summary += "### Issues Found\n\n"
            for issue in analysis["issues"]:
                summary += f"- {issue['message']}\n"
            summary += "\n"
            
        # Add suggestions
        if analysis["suggestions"]:
            summary += "### Suggestions\n\n"
            for suggestion in analysis["suggestions"]:
                summary += f"- {suggestion['message']}\n"
            summary += "\n"
            
        return summary
    
    def _notify_reviewers(self, pr: PullRequest, review: Any):
        """Notify reviewers about the review."""
        # Get the reviewers
        reviewers = pr.get_review_requests()
        
        # Create a comment to notify reviewers
        pr.create_issue_comment(
            f"@reviewers A new review has been submitted. "
            f"Please review the changes and provide feedback."
        )
    
    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code quality and structure."""
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Analyze the code
            analysis = {
                "quality_score": 0.0,
                "issues": [],
                "suggestions": [],
                "metrics": {
                    "complexity": 0,
                    "lines": len(code.splitlines()),
                    "functions": 0,
                    "classes": 0
                }
            }
            
            # Calculate metrics
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    analysis["metrics"]["functions"] += 1
                    analysis["metrics"]["complexity"] += self._calculate_complexity(node)
                elif isinstance(node, ast.ClassDef):
                    analysis["metrics"]["classes"] += 1
                    
            # Check for issues
            analysis["issues"] = self._check_code_issues(code)
            
            # Generate suggestions
            analysis["suggestions"] = self._generate_code_suggestions(code)
            
            # Calculate quality score
            analysis["quality_score"] = self._calculate_quality_score(analysis)
            
            return analysis
            
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def _generate_suggestions(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate code improvement suggestions."""
        suggestions = []
        
        # Add suggestions based on issues
        for issue in analysis["issues"]:
            suggestions.append({
                "type": "issue",
                "message": issue["message"],
                "suggestion": issue["suggestion"],
                "example": self._generate_example(issue)
            })
            
        # Add suggestions based on metrics
        if analysis["metrics"]["complexity"] > 10:
            suggestions.append({
                "type": "complexity",
                "message": "High cyclomatic complexity detected",
                "suggestion": "Consider breaking down the function into smaller, more focused functions",
                "example": self._generate_complexity_example()
            })
            
        return suggestions
    
    def _find_conflicts(self, branch: str) -> List[Dict[str, Any]]:
        """Find merge conflicts in a branch."""
        conflicts = []
        
        # Get the branch
        branch_ref = self.repo.get_branch(branch)
        
        # Get the base branch
        base_branch = self.repo.get_branch(branch_ref.base.ref)
        
        # Compare the branches
        comparison = self.repo.compare(base_branch.commit.sha, branch_ref.commit.sha)
        
        # Find conflicts
        for file in comparison.files:
            if file.status == "modified":
                # Check for conflicts
                if "<<<<<<<" in file.patch:
                    conflicts.append({
                        "file": file.filename,
                        "status": file.status,
                        "patch": file.patch
                    })
                    
        return conflicts
    
    def _resolve_conflicts(self, conflicts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Resolve merge conflicts."""
        resolutions = []
        
        for conflict in conflicts:
            # Parse the conflict
            conflict_sections = self._parse_conflict(conflict["patch"])
            
            # Resolve the conflict
            resolution = self._resolve_conflict_section(conflict_sections)
            
            resolutions.append({
                "file": conflict["file"],
                "resolution": resolution
            })
            
        return resolutions
    
    def _apply_resolutions(self, resolutions: List[Dict[str, Any]]):
        """Apply conflict resolutions."""
        for resolution in resolutions:
            # Get the file
            file = self.repo.get_contents(resolution["file"])
            
            # Update the file
            self.repo.update_file(
                path=resolution["file"],
                message=f"Resolve conflicts in {resolution['file']}",
                content=resolution["resolution"],
                sha=file.sha
            )
    
    def _get_branch_changes(self, branch: str) -> List[Dict[str, Any]]:
        """Get changes in a branch."""
        changes = []
        
        # Get the branch
        branch_ref = self.repo.get_branch(branch)
        
        # Get the base branch
        base_branch = self.repo.get_branch(branch_ref.base.ref)
        
        # Compare the branches
        comparison = self.repo.compare(base_branch.commit.sha, branch_ref.commit.sha)
        
        # Get the changes
        for file in comparison.files:
            changes.append({
                "filename": file.filename,
                "status": file.status,
                "additions": file.additions,
                "deletions": file.deletions,
                "patch": file.patch
            })
            
        return changes
    
    def _generate_change_report(self, analysis: Dict[str, Any]) -> str:
        """Generate a report of changes."""
        report = f"## Change Report\n\n"
        
        # Add quality score
        report += f"**Quality Score**: {analysis['quality_score']:.2f}\n\n"
        
        # Add metrics
        report += "### Metrics\n\n"
        report += f"- Total Changes: {analysis['metrics']['total_changes']}\n"
        report += f"- Additions: {analysis['metrics']['additions']}\n"
        report += f"- Deletions: {analysis['metrics']['deletions']}\n"
        report += f"- Complexity: {analysis['metrics']['complexity']}\n\n"
        
        # Add issues
        if analysis["issues"]:
            report += "### Issues Found\n\n"
            for issue in analysis["issues"]:
                report += f"- {issue['message']}\n"
            report += "\n"
            
        # Add suggestions
        if analysis["suggestions"]:
            report += "### Suggestions\n\n"
            for suggestion in analysis["suggestions"]:
                report += f"- {suggestion['message']}\n"
            report += "\n"
            
        return report
    
    def _parse_patch(self, patch: str) -> List[Dict[str, Any]]:
        """Parse a git patch file."""
        changes = []
        current_change = None
        
        for line in patch.splitlines():
            if line.startswith("@@"):
                if current_change:
                    changes.append(current_change)
                current_change = {
                    "line": int(line.split()[1].split(",")[0][1:]),
                    "code": []
                }
            elif current_change:
                current_change["code"].append(line)
                
        if current_change:
            changes.append(current_change)
            
        return changes
    
    def _calculate_complexity(self, node: ast.AST) -> int:
        """Calculate cyclomatic complexity of a code block."""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, 
                                ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
                
        return complexity
    
    def _check_code_issues(self, code: str) -> List[Dict[str, Any]]:
        """Check code for issues."""
        issues = []
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Check for common issues
            for node in ast.walk(tree):
                # Check for print statements
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
                    issues.append({
                        "type": "print_statement",
                        "message": "Use of print statement detected",
                        "suggestion": "Consider using logging instead",
                        "line": node.lineno
                    })
                    
                # Check for bare except
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    issues.append({
                        "type": "bare_except",
                        "message": "Bare except clause detected",
                        "suggestion": "Specify the exception type to catch",
                        "line": node.lineno
                    })
                    
                # Check for long lines
                if isinstance(node, ast.Expr) and len(code.splitlines()[node.lineno - 1]) > 79:
                    issues.append({
                        "type": "long_line",
                        "message": "Line exceeds 79 characters",
                        "suggestion": "Break the line into multiple lines",
                        "line": node.lineno
                    })
                    
        except Exception as e:
            issues.append({
                "type": "parse_error",
                "message": f"Error parsing code: {str(e)}",
                "suggestion": "Check the code syntax",
                "line": 0
            })
            
        return issues
    
    def _generate_code_suggestions(self, code: str) -> List[Dict[str, Any]]:
        """Generate code improvement suggestions."""
        suggestions = []
        
        try:
            # Parse the code
            tree = ast.parse(code)
            
            # Generate suggestions
            for node in ast.walk(tree):
                # Suggest type hints
                if isinstance(node, ast.FunctionDef) and not node.returns:
                    suggestions.append({
                        "type": "type_hint",
                        "message": "Function missing return type hint",
                        "suggestion": "Add return type annotation",
                        "line": node.lineno
                    })
                    
                # Suggest docstrings
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not ast.get_docstring(node):
                    suggestions.append({
                        "type": "docstring",
                        "message": f"{'Class' if isinstance(node, ast.ClassDef) else 'Function'} missing docstring",
                        "suggestion": "Add a docstring explaining the purpose",
                        "line": node.lineno
                    })
                    
        except Exception as e:
            suggestions.append({
                "type": "parse_error",
                "message": f"Error parsing code: {str(e)}",
                "suggestion": "Check the code syntax",
                "line": 0
            })
            
        return suggestions
    
    def _calculate_quality_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate code quality score."""
        score = 1.0
        
        # Penalize for issues
        score -= len(analysis["issues"]) * 0.1
        
        # Penalize for high complexity
        if analysis["metrics"]["complexity"] > 10:
            score -= 0.2
            
        # Ensure score is between 0 and 1
        return max(0.0, min(1.0, score))
    
    def _parse_conflict(self, patch: str) -> List[Dict[str, Any]]:
        """Parse a conflict section in a patch."""
        sections = []
        current_section = None
        
        for line in patch.splitlines():
            if line.startswith("<<<<<<<"):
                current_section = {
                    "ours": [],
                    "theirs": []
                }
            elif line.startswith("======="):
                current_section["theirs"] = []
            elif line.startswith(">>>>>>>"):
                sections.append(current_section)
                current_section = None
            elif current_section:
                if not current_section["theirs"]:
                    current_section["ours"].append(line)
                else:
                    current_section["theirs"].append(line)
                    
        return sections
    
    def _resolve_conflict_section(self, sections: List[Dict[str, Any]]) -> str:
        """Resolve a conflict section."""
        resolution = []
        
        for section in sections:
            # Compare the sections
            if section["ours"] == section["theirs"]:
                # If identical, use either version
                resolution.extend(section["ours"])
            else:
                # If different, try to merge
                merged = self._merge_sections(section["ours"], section["theirs"])
                resolution.extend(merged)
                
        return "\n".join(resolution)
    
    def _merge_sections(self, ours: List[str], theirs: List[str]) -> List[str]:
        """Merge two conflicting sections."""
        # For now, just use our version
        # In a real implementation, this would be more sophisticated
        return ours
    
    def _generate_example(self, issue: Dict[str, Any]) -> str:
        """Generate an example fix for an issue."""
        if issue["type"] == "print_statement":
            return "```python\n# Before\nprint('Hello, world!')\n\n# After\nimport logging\nlogging.info('Hello, world!')\n```"
        elif issue["type"] == "bare_except":
            return "```python\n# Before\ntry:\n    do_something()\nexcept:\n    pass\n\n# After\ntry:\n    do_something()\nexcept Exception as e:\n    logging.error(f'Error: {e}')\n```"
        elif issue["type"] == "long_line":
            return "```python\n# Before\nvery_long_line = 'This is a very long line that exceeds the recommended length of 79 characters'\n\n# After\nvery_long_line = (\n    'This is a very long line that '\n    'exceeds the recommended length '\n    'of 79 characters'\n)\n```"
        return ""
    
    def _generate_complexity_example(self) -> str:
        """Generate an example of reducing complexity."""
        return """```python
# Before
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            if item % 2 == 0:
                result.append(item * 2)
            else:
                result.append(item * 3)
        else:
            if item % 2 == 0:
                result.append(item * 4)
            else:
                result.append(item * 5)
    return result

# After
def process_positive_item(item):
    if item % 2 == 0:
        return item * 2
    return item * 3

def process_negative_item(item):
    if item % 2 == 0:
        return item * 4
    return item * 5

def process_data(data):
    return [
        process_positive_item(item) if item > 0 else process_negative_item(item)
        for item in data
    ]
```""" 