from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import ast
import re
from pathlib import Path
import black
import isort
import autopep8
from datetime import datetime

@dataclass
class MigrationConfig:
    """Configuration for code migration."""
    target_dir: str
    backup_dir: Optional[str] = None
    format_code: bool = True
    sort_imports: bool = True
    fix_pep8: bool = True
    update_dependencies: bool = True
    generate_tests: bool = True

class CodeMigrator:
    """AI-driven code migration and modernization system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = MigrationConfig(target_dir=".")
        
    def migrate_code(self, source_dir: str) -> Dict[str, Any]:
        """Migrate and modernize code in the given directory."""
        try:
            # Create backup if configured
            if self.config.backup_dir:
                self._create_backup(source_dir)
                
            # Analyze the code
            code_info = self._analyze_code(source_dir)
            
            # Generate migration plan
            plan = self._generate_migration_plan(code_info)
            
            # Execute migrations
            results = self._execute_migrations(plan, source_dir)
            
            # Format code if configured
            if self.config.format_code:
                self._format_code(source_dir)
                
            # Sort imports if configured
            if self.config.sort_imports:
                self._sort_imports(source_dir)
                
            # Fix PEP8 issues if configured
            if self.config.fix_pep8:
                self._fix_pep8(source_dir)
                
            # Update dependencies if configured
            if self.config.update_dependencies:
                self._update_dependencies(source_dir)
                
            # Generate tests if configured
            if self.config.generate_tests:
                self._generate_tests(source_dir, code_info)
                
            return {
                "status": "success",
                "timestamp": datetime.now().isoformat(),
                "migrations": results,
                "summary": self._generate_summary(results)
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _create_backup(self, source_dir: str):
        """Create a backup of the source directory."""
        backup_path = os.path.join(self.config.backup_dir, 
                                 f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        os.makedirs(backup_path, exist_ok=True)
        
        # Copy all files
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    src_path = os.path.join(root, file)
                    rel_path = os.path.relpath(src_path, source_dir)
                    dst_path = os.path.join(backup_path, rel_path)
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                    with open(src_path, 'r') as src, open(dst_path, 'w') as dst:
                        dst.write(src.read())
    
    def _analyze_code(self, source_dir: str) -> Dict[str, Any]:
        """Analyze code structure and patterns."""
        code_info = {
            "modules": [],
            "classes": [],
            "functions": [],
            "imports": [],
            "patterns": []
        }
        
        # Walk through the source directory
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # Parse the file
                    with open(file_path, 'r') as f:
                        tree = ast.parse(f.read())
                        
                    # Get module info
                    module = {
                        "name": os.path.splitext(file)[0],
                        "path": file_path,
                        "docstring": ast.get_docstring(tree),
                        "imports": self._get_imports(tree)
                    }
                    code_info["modules"].append(module)
                    code_info["imports"].extend(module["imports"])
                    
                    # Find classes and functions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_info = self._analyze_class(node, file_path)
                            code_info["classes"].append(class_info)
                            
                        elif isinstance(node, ast.FunctionDef):
                            func_info = self._analyze_function(node, file_path)
                            code_info["functions"].append(func_info)
                            
                    # Find patterns
                    patterns = self._find_patterns(tree, file_path)
                    code_info["patterns"].extend(patterns)
                    
        return code_info
    
    def _analyze_class(self, node: ast.ClassDef, file_path: str) -> Dict[str, Any]:
        """Analyze a class definition."""
        return {
            "name": node.name,
            "path": file_path,
            "docstring": ast.get_docstring(node),
            "bases": [self._get_base_name(b) for b in node.bases],
            "methods": [self._analyze_function(m, file_path) for m in node.body 
                       if isinstance(m, ast.FunctionDef)],
            "attributes": [self._analyze_attribute(a) for a in node.body 
                         if isinstance(a, ast.AnnAssign)],
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list]
        }
    
    def _analyze_function(self, node: ast.FunctionDef, file_path: str) -> Dict[str, Any]:
        """Analyze a function definition."""
        return {
            "name": node.name,
            "path": file_path,
            "docstring": ast.get_docstring(node),
            "parameters": self._analyze_parameters(node.args),
            "returns": self._get_return_type(node),
            "decorators": [self._get_decorator_name(d) for d in node.decorator_list],
            "complexity": self._calculate_complexity(node)
        }
    
    def _analyze_attribute(self, node: ast.AnnAssign) -> Dict[str, Any]:
        """Analyze a class attribute."""
        return {
            "name": node.target.id,
            "type": self._get_annotation_type(node.annotation),
            "value": self._get_value(node.value) if node.value else None
        }
    
    def _analyze_parameters(self, args: ast.arguments) -> List[Dict[str, Any]]:
        """Analyze function parameters."""
        params = []
        for arg in args.args:
            param = {
                "name": arg.arg,
                "type": self._get_annotation_type(arg.annotation) if arg.annotation else None,
                "default": None
            }
            params.append(param)
        return params
    
    def _find_patterns(self, tree: ast.AST, file_path: str) -> List[Dict[str, Any]]:
        """Find code patterns that need migration."""
        patterns = []
        
        # Check for old-style classes
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if not node.bases:
                    patterns.append({
                        "type": "old_style_class",
                        "name": node.name,
                        "path": file_path,
                        "suggestion": "Convert to new-style class by inheriting from object"
                    })
                    
        # Check for print statements
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'print':
                patterns.append({
                    "type": "print_statement",
                    "path": file_path,
                    "suggestion": "Replace print with logging"
                })
                
        # Check for string formatting
        for node in ast.walk(tree):
            if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
                if isinstance(node.left, ast.Str):
                    patterns.append({
                        "type": "old_string_format",
                        "path": file_path,
                        "suggestion": "Use f-strings or str.format()"
                    })
                    
        return patterns
    
    def _generate_migration_plan(self, code_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate a plan for code migrations."""
        plan = []
        
        # Add pattern-based migrations
        for pattern in code_info["patterns"]:
            plan.append({
                "type": "pattern",
                "pattern": pattern,
                "action": self._get_pattern_action(pattern)
            })
            
        # Add import-based migrations
        for imp in code_info["imports"]:
            if self._needs_import_update(imp):
                plan.append({
                    "type": "import",
                    "import": imp,
                    "action": self._get_import_action(imp)
                })
                
        # Add class-based migrations
        for class_info in code_info["classes"]:
            if self._needs_class_update(class_info):
                plan.append({
                    "type": "class",
                    "class": class_info,
                    "action": self._get_class_action(class_info)
                })
                
        # Add function-based migrations
        for func in code_info["functions"]:
            if self._needs_function_update(func):
                plan.append({
                    "type": "function",
                    "function": func,
                    "action": self._get_function_action(func)
                })
                
        return plan
    
    def _execute_migrations(self, plan: List[Dict[str, Any]], source_dir: str) -> List[Dict[str, Any]]:
        """Execute the migration plan."""
        results = []
        
        for migration in plan:
            try:
                if migration["type"] == "pattern":
                    result = self._apply_pattern_migration(migration["pattern"], 
                                                         migration["action"])
                elif migration["type"] == "import":
                    result = self._apply_import_migration(migration["import"], 
                                                        migration["action"])
                elif migration["type"] == "class":
                    result = self._apply_class_migration(migration["class"], 
                                                       migration["action"])
                elif migration["type"] == "function":
                    result = self._apply_function_migration(migration["function"], 
                                                          migration["action"])
                    
                results.append({
                    "type": migration["type"],
                    "status": "success",
                    "details": result
                })
                
            except Exception as e:
                results.append({
                    "type": migration["type"],
                    "status": "error",
                    "error": str(e)
                })
                
        return results
    
    def _format_code(self, source_dir: str):
        """Format code using black."""
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        formatted = black.format_str(content, mode=black.FileMode())
                        with open(file_path, 'w') as f:
                            f.write(formatted)
                    except Exception as e:
                        print(f"Error formatting {file_path}: {e}")
    
    def _sort_imports(self, source_dir: str):
        """Sort imports using isort."""
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        isort.file(file_path)
                    except Exception as e:
                        print(f"Error sorting imports in {file_path}: {e}")
    
    def _fix_pep8(self, source_dir: str):
        """Fix PEP8 issues using autopep8."""
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r') as f:
                            content = f.read()
                        fixed = autopep8.fix_code(content)
                        with open(file_path, 'w') as f:
                            f.write(fixed)
                    except Exception as e:
                        print(f"Error fixing PEP8 in {file_path}: {e}")
    
    def _update_dependencies(self, source_dir: str):
        """Update project dependencies."""
        # Find requirements.txt
        req_file = os.path.join(source_dir, "requirements.txt")
        if os.path.exists(req_file):
            # Read current requirements
            with open(req_file, 'r') as f:
                requirements = [line.strip() for line in f if line.strip()]
                
            # Update each requirement
            updated = []
            for req in requirements:
                try:
                    # Use pip to get latest version
                    import subprocess
                    result = subprocess.run(['pip', 'index', 'versions', req], 
                                         capture_output=True, text=True)
                    if result.returncode == 0:
                        # Parse latest version
                        latest = result.stdout.split('\n')[0].split()[-1]
                        updated.append(f"{req}=={latest}")
                except Exception as e:
                    print(f"Error updating {req}: {e}")
                    updated.append(req)
                    
            # Write updated requirements
            with open(req_file, 'w') as f:
                f.write('\n'.join(updated))
    
    def _generate_tests(self, source_dir: str, code_info: Dict[str, Any]):
        """Generate test files for the codebase."""
        tests_dir = os.path.join(source_dir, "tests")
        os.makedirs(tests_dir, exist_ok=True)
        
        # Generate tests for each module
        for module in code_info["modules"]:
            test_file = os.path.join(tests_dir, f"test_{module['name']}.py")
            
            with open(test_file, 'w') as f:
                f.write(f"import unittest\n")
                f.write(f"from {module['name']} import *\n\n")
                f.write(f"class Test{module['name'].title()}(unittest.TestCase):\n")
                
                # Generate tests for each class
                for class_info in code_info["classes"]:
                    if class_info["path"] == module["path"]:
                        f.write(f"\n    def test_{class_info['name'].lower()}(self):\n")
                        f.write(f"        # TODO: Implement test for {class_info['name']}\n")
                        f.write(f"        pass\n")
                        
                # Generate tests for each function
                for func in code_info["functions"]:
                    if func["path"] == module["path"]:
                        f.write(f"\n    def test_{func['name'].lower()}(self):\n")
                        f.write(f"        # TODO: Implement test for {func['name']}\n")
                        f.write(f"        pass\n")
    
    def _get_imports(self, tree: ast.AST) -> List[str]:
        """Get all imports from a module."""
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    imports.append(name.name)
            elif isinstance(node, ast.ImportFrom):
                for name in node.names:
                    imports.append(f"{node.module}.{name.name}")
        return imports
    
    def _get_base_name(self, base: ast.AST) -> str:
        """Get the name of a base class."""
        if isinstance(base, ast.Name):
            return base.id
        elif isinstance(base, ast.Attribute):
            return f"{self._get_base_name(base.value)}.{base.attr}"
        return str(base)
    
    def _get_decorator_name(self, decorator: ast.AST) -> str:
        """Get the name of a decorator."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            return self._get_decorator_name(decorator.func)
        elif isinstance(decorator, ast.Attribute):
            return f"{self._get_decorator_name(decorator.value)}.{decorator.attr}"
        return str(decorator)
    
    def _get_annotation_type(self, annotation: ast.AST) -> str:
        """Convert an AST annotation to a string type."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}[{self._get_annotation_type(annotation.slice)}]"
        return str(annotation)
    
    def _get_value(self, value: ast.AST) -> Any:
        """Get the value of an AST node."""
        if isinstance(value, ast.Constant):
            return value.value
        elif isinstance(value, ast.Name):
            return value.id
        elif isinstance(value, ast.Attribute):
            return f"{self._get_value(value.value)}.{value.attr}"
        return str(value)
    
    def _get_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Get function return type."""
        if node.returns:
            return self._get_annotation_type(node.returns)
        return None
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity of a function."""
        complexity = 1
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.Try, 
                                ast.ExceptHandler, ast.With, ast.Assert)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
                
        return complexity
    
    def _needs_import_update(self, imp: str) -> bool:
        """Check if an import needs updating."""
        # Add your import update rules here
        return False
    
    def _needs_class_update(self, class_info: Dict[str, Any]) -> bool:
        """Check if a class needs updating."""
        # Add your class update rules here
        return False
    
    def _needs_function_update(self, func: Dict[str, Any]) -> bool:
        """Check if a function needs updating."""
        # Add your function update rules here
        return False
    
    def _get_pattern_action(self, pattern: Dict[str, Any]) -> Dict[str, Any]:
        """Get the action to take for a pattern."""
        # Add your pattern action rules here
        return {}
    
    def _get_import_action(self, imp: str) -> Dict[str, Any]:
        """Get the action to take for an import."""
        # Add your import action rules here
        return {}
    
    def _get_class_action(self, class_info: Dict[str, Any]) -> Dict[str, Any]:
        """Get the action to take for a class."""
        # Add your class action rules here
        return {}
    
    def _get_function_action(self, func: Dict[str, Any]) -> Dict[str, Any]:
        """Get the action to take for a function."""
        # Add your function action rules here
        return {}
    
    def _apply_pattern_migration(self, pattern: Dict[str, Any], 
                               action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a pattern-based migration."""
        # Add your pattern migration logic here
        return {}
    
    def _apply_import_migration(self, imp: str, 
                              action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply an import-based migration."""
        # Add your import migration logic here
        return {}
    
    def _apply_class_migration(self, class_info: Dict[str, Any], 
                             action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a class-based migration."""
        # Add your class migration logic here
        return {}
    
    def _apply_function_migration(self, func: Dict[str, Any], 
                                action: Dict[str, Any]) -> Dict[str, Any]:
        """Apply a function-based migration."""
        # Add your function migration logic here
        return {}
    
    def _generate_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a summary of migration results."""
        summary = {
            "total": len(results),
            "successful": len([r for r in results if r["status"] == "success"]),
            "failed": len([r for r in results if r["status"] == "error"]),
            "by_type": {}
        }
        
        # Count by type
        for result in results:
            if result["type"] not in summary["by_type"]:
                summary["by_type"][result["type"]] = {
                    "total": 0,
                    "successful": 0,
                    "failed": 0
                }
                
            summary["by_type"][result["type"]]["total"] += 1
            if result["status"] == "success":
                summary["by_type"][result["type"]]["successful"] += 1
            else:
                summary["by_type"][result["type"]]["failed"] += 1
                
        return summary 