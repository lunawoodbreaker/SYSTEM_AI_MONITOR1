from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import requests
from pathlib import Path
import ast
import inspect
import re
import graphviz
import markdown
import yaml
from datetime import datetime

@dataclass
class DocumentationConfig:
    """Configuration for documentation generation."""
    output_dir: str
    format: str = "markdown"  # markdown, html, pdf
    include_private: bool = False
    include_tests: bool = True
    include_examples: bool = True
    generate_diagrams: bool = True
    template_path: Optional[str] = None

class DocumentationGenerator:
    """AI-driven documentation generation system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = DocumentationConfig(output_dir="docs")
        
    def generate_api_docs(self, source_dir: str) -> Dict[str, Any]:
        """Generate API documentation from source code."""
        try:
            # Analyze the source code
            api_info = self._analyze_api(source_dir)
            
            # Generate documentation
            docs = {
                "title": "API Documentation",
                "version": self._get_version(),
                "timestamp": datetime.now().isoformat(),
                "endpoints": [],
                "models": [],
                "examples": []
            }
            
            # Process endpoints
            for endpoint in api_info["endpoints"]:
                endpoint_doc = self._document_endpoint(endpoint)
                docs["endpoints"].append(endpoint_doc)
                
            # Process models
            for model in api_info["models"]:
                model_doc = self._document_model(model)
                docs["models"].append(model_doc)
                
            # Generate examples
            if self.config.include_examples:
                docs["examples"] = self._generate_examples(api_info)
                
            # Save documentation
            self._save_documentation(docs, "api")
            
            return docs
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_code_docs(self, source_dir: str) -> Dict[str, Any]:
        """Generate code documentation with suggestions."""
        try:
            # Analyze the code
            code_info = self._analyze_code(source_dir)
            
            # Generate documentation
            docs = {
                "title": "Code Documentation",
                "timestamp": datetime.now().isoformat(),
                "modules": [],
                "classes": [],
                "functions": [],
                "suggestions": []
            }
            
            # Process modules
            for module in code_info["modules"]:
                module_doc = self._document_module(module)
                docs["modules"].append(module_doc)
                
            # Process classes
            for class_info in code_info["classes"]:
                class_doc = self._document_class(class_info)
                docs["classes"].append(class_doc)
                
            # Process functions
            for func in code_info["functions"]:
                func_doc = self._document_function(func)
                docs["functions"].append(func_doc)
                
            # Generate suggestions
            docs["suggestions"] = self._generate_doc_suggestions(code_info)
            
            # Save documentation
            self._save_documentation(docs, "code")
            
            return docs
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_readme(self, project_dir: str) -> Dict[str, Any]:
        """Generate a comprehensive README file."""
        try:
            # Analyze the project
            project_info = self._analyze_project(project_dir)
            
            # Generate README content
            readme = {
                "title": project_info["name"],
                "description": project_info["description"],
                "version": project_info["version"],
                "timestamp": datetime.now().isoformat(),
                "sections": [
                    {
                        "title": "Installation",
                        "content": self._generate_installation_section(project_info)
                    },
                    {
                        "title": "Usage",
                        "content": self._generate_usage_section(project_info)
                    },
                    {
                        "title": "Features",
                        "content": self._generate_features_section(project_info)
                    },
                    {
                        "title": "Configuration",
                        "content": self._generate_config_section(project_info)
                    },
                    {
                        "title": "Development",
                        "content": self._generate_development_section(project_info)
                    },
                    {
                        "title": "Contributing",
                        "content": self._generate_contributing_section(project_info)
                    },
                    {
                        "title": "License",
                        "content": self._generate_license_section(project_info)
                    }
                ]
            }
            
            # Save README
            self._save_readme(readme, project_dir)
            
            return readme
            
        except Exception as e:
            return {"error": str(e)}
    
    def generate_architecture_diagram(self, source_dir: str) -> Dict[str, Any]:
        """Generate architecture diagrams."""
        try:
            # Analyze the architecture
            arch_info = self._analyze_architecture(source_dir)
            
            # Generate diagrams
            diagrams = {
                "timestamp": datetime.now().isoformat(),
                "diagrams": []
            }
            
            # Generate component diagram
            if "components" in arch_info:
                component_diagram = self._generate_component_diagram(arch_info["components"])
                diagrams["diagrams"].append({
                    "type": "component",
                    "path": self._save_diagram(component_diagram, "component")
                })
                
            # Generate class diagram
            if "classes" in arch_info:
                class_diagram = self._generate_class_diagram(arch_info["classes"])
                diagrams["diagrams"].append({
                    "type": "class",
                    "path": self._save_diagram(class_diagram, "class")
                })
                
            # Generate sequence diagram
            if "sequences" in arch_info:
                sequence_diagram = self._generate_sequence_diagram(arch_info["sequences"])
                diagrams["diagrams"].append({
                    "type": "sequence",
                    "path": self._save_diagram(sequence_diagram, "sequence")
                })
                
            return diagrams
            
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_api(self, source_dir: str) -> Dict[str, Any]:
        """Analyze API endpoints and models."""
        api_info = {
            "endpoints": [],
            "models": []
        }
        
        # Walk through the source directory
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # Parse the file
                    with open(file_path, 'r') as f:
                        tree = ast.parse(f.read())
                        
                    # Find API endpoints
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Check for FastAPI/Flask decorators
                            if any(isinstance(d, ast.Call) and 
                                  isinstance(d.func, ast.Name) and 
                                  d.func.id in ['app.route', 'router.get', 'router.post'] 
                                  for d in node.decorator_list):
                                endpoint = {
                                    "name": node.name,
                                    "path": file_path,
                                    "method": self._get_http_method(node),
                                    "parameters": self._get_parameters(node),
                                    "return_type": self._get_return_type(node),
                                    "docstring": ast.get_docstring(node)
                                }
                                api_info["endpoints"].append(endpoint)
                                
                        elif isinstance(node, ast.ClassDef):
                            # Check for Pydantic models
                            if any(isinstance(b, ast.Name) and b.id == 'BaseModel' 
                                  for b in node.bases):
                                model = {
                                    "name": node.name,
                                    "path": file_path,
                                    "fields": self._get_model_fields(node),
                                    "docstring": ast.get_docstring(node)
                                }
                                api_info["models"].append(model)
                                
        return api_info
    
    def _analyze_code(self, source_dir: str) -> Dict[str, Any]:
        """Analyze code structure and content."""
        code_info = {
            "modules": [],
            "classes": [],
            "functions": []
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
                    
                    # Find classes and functions
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_info = {
                                "name": node.name,
                                "module": module["name"],
                                "path": file_path,
                                "docstring": ast.get_docstring(node),
                                "methods": self._get_class_methods(node),
                                "attributes": self._get_class_attributes(node),
                                "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
                            }
                            code_info["classes"].append(class_info)
                            
                        elif isinstance(node, ast.FunctionDef):
                            func_info = {
                                "name": node.name,
                                "module": module["name"],
                                "path": file_path,
                                "docstring": ast.get_docstring(node),
                                "parameters": self._get_parameters(node),
                                "return_type": self._get_return_type(node)
                            }
                            code_info["functions"].append(func_info)
                            
        return code_info
    
    def _analyze_project(self, project_dir: str) -> Dict[str, Any]:
        """Analyze project structure and metadata."""
        project_info = {
            "name": os.path.basename(project_dir),
            "description": "",
            "version": "0.1.0",
            "dependencies": [],
            "scripts": [],
            "tests": [],
            "docs": []
        }
        
        # Read setup.py or pyproject.toml
        setup_file = os.path.join(project_dir, "setup.py")
        if os.path.exists(setup_file):
            with open(setup_file, 'r') as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setup':
                        for keyword in node.keywords:
                            if keyword.arg == 'name':
                                project_info["name"] = keyword.value.value
                            elif keyword.arg == 'description':
                                project_info["description"] = keyword.value.value
                            elif keyword.arg == 'version':
                                project_info["version"] = keyword.value.value
                                
        # Find dependencies
        req_file = os.path.join(project_dir, "requirements.txt")
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                project_info["dependencies"] = [line.strip() for line in f if line.strip()]
                
        # Find scripts
        scripts_dir = os.path.join(project_dir, "scripts")
        if os.path.exists(scripts_dir):
            project_info["scripts"] = [f for f in os.listdir(scripts_dir) if f.endswith(".py")]
            
        # Find tests
        tests_dir = os.path.join(project_dir, "tests")
        if os.path.exists(tests_dir):
            project_info["tests"] = [f for f in os.listdir(tests_dir) if f.endswith(".py")]
            
        # Find docs
        docs_dir = os.path.join(project_dir, "docs")
        if os.path.exists(docs_dir):
            project_info["docs"] = [f for f in os.listdir(docs_dir) if f.endswith((".md", ".rst"))]
            
        return project_info
    
    def _analyze_architecture(self, source_dir: str) -> Dict[str, Any]:
        """Analyze system architecture."""
        arch_info = {
            "components": [],
            "classes": [],
            "sequences": []
        }
        
        # Walk through the source directory
        for root, _, files in os.walk(source_dir):
            for file in files:
                if file.endswith(".py"):
                    file_path = os.path.join(root, file)
                    
                    # Parse the file
                    with open(file_path, 'r') as f:
                        tree = ast.parse(f.read())
                        
                    # Find components (modules with specific patterns)
                    if any(pattern in file_path for pattern in ["api", "service", "model", "controller"]):
                        component = {
                            "name": os.path.splitext(file)[0],
                            "type": self._get_component_type(file_path),
                            "path": file_path,
                            "dependencies": self._get_imports(tree)
                        }
                        arch_info["components"].append(component)
                        
                    # Find classes
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            class_info = {
                                "name": node.name,
                                "module": os.path.splitext(file)[0],
                                "path": file_path,
                                "methods": self._get_class_methods(node),
                                "attributes": self._get_class_attributes(node),
                                "bases": [b.id for b in node.bases if isinstance(b, ast.Name)]
                            }
                            arch_info["classes"].append(class_info)
                            
                            # Find sequence patterns
                            for method in node.body:
                                if isinstance(method, ast.FunctionDef):
                                    sequence = self._analyze_sequence(method)
                                    if sequence:
                                        arch_info["sequences"].append(sequence)
                                        
        return arch_info
    
    def _document_endpoint(self, endpoint: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for an API endpoint."""
        return {
            "name": endpoint["name"],
            "method": endpoint["method"],
            "path": endpoint["path"],
            "description": endpoint["docstring"],
            "parameters": endpoint["parameters"],
            "return_type": endpoint["return_type"],
            "examples": self._generate_endpoint_examples(endpoint)
        }
    
    def _document_model(self, model: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for a data model."""
        return {
            "name": model["name"],
            "description": model["docstring"],
            "fields": model["fields"],
            "examples": self._generate_model_examples(model)
        }
    
    def _document_module(self, module: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for a module."""
        return {
            "name": module["name"],
            "description": module["docstring"],
            "imports": module["imports"],
            "usage": self._generate_module_usage(module)
        }
    
    def _document_class(self, class_info: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for a class."""
        return {
            "name": class_info["name"],
            "module": class_info["module"],
            "description": class_info["docstring"],
            "methods": class_info["methods"],
            "attributes": class_info["attributes"],
            "inheritance": class_info["bases"],
            "examples": self._generate_class_examples(class_info)
        }
    
    def _document_function(self, func: Dict[str, Any]) -> Dict[str, Any]:
        """Generate documentation for a function."""
        return {
            "name": func["name"],
            "module": func["module"],
            "description": func["docstring"],
            "parameters": func["parameters"],
            "return_type": func["return_type"],
            "examples": self._generate_function_examples(func)
        }
    
    def _generate_doc_suggestions(self, code_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate documentation improvement suggestions."""
        suggestions = []
        
        # Check for missing docstrings
        for module in code_info["modules"]:
            if not module["docstring"]:
                suggestions.append({
                    "type": "missing_docstring",
                    "element": "module",
                    "name": module["name"],
                    "path": module["path"],
                    "suggestion": "Add a module-level docstring explaining the module's purpose and contents."
                })
                
        for class_info in code_info["classes"]:
            if not class_info["docstring"]:
                suggestions.append({
                    "type": "missing_docstring",
                    "element": "class",
                    "name": class_info["name"],
                    "path": class_info["path"],
                    "suggestion": "Add a class-level docstring explaining the class's purpose and usage."
                })
                
        for func in code_info["functions"]:
            if not func["docstring"]:
                suggestions.append({
                    "type": "missing_docstring",
                    "element": "function",
                    "name": func["name"],
                    "path": func["path"],
                    "suggestion": "Add a function-level docstring explaining the function's purpose, parameters, and return value."
                })
                
        # Check for incomplete parameter documentation
        for func in code_info["functions"]:
            if func["docstring"]:
                doc_params = self._extract_docstring_params(func["docstring"])
                for param in func["parameters"]:
                    if param not in doc_params:
                        suggestions.append({
                            "type": "incomplete_docstring",
                            "element": "function",
                            "name": func["name"],
                            "path": func["path"],
                            "suggestion": f"Add documentation for parameter '{param}' in the function's docstring."
                        })
                        
        return suggestions
    
    def _generate_component_diagram(self, components: List[Dict[str, Any]]) -> graphviz.Digraph:
        """Generate a component diagram."""
        dot = graphviz.Digraph(comment='Component Diagram')
        dot.attr(rankdir='LR')
        
        # Add components
        for component in components:
            dot.node(component["name"], 
                    f"{component['name']}\n({component['type']})",
                    shape='box')
            
        # Add dependencies
        for component in components:
            for dep in component["dependencies"]:
                if any(c["name"] == dep for c in components):
                    dot.edge(component["name"], dep)
                    
        return dot
    
    def _generate_class_diagram(self, classes: List[Dict[str, Any]]) -> graphviz.Digraph:
        """Generate a class diagram."""
        dot = graphviz.Digraph(comment='Class Diagram')
        dot.attr(rankdir='BT')
        
        # Add classes
        for class_info in classes:
            # Create class label
            label = f"{class_info['name']}"
            if class_info["bases"]:
                label += f"\nInherits: {', '.join(class_info['bases'])}"
            label += "\n\n"
            
            # Add attributes
            if class_info["attributes"]:
                label += "Attributes:\n"
                for attr in class_info["attributes"]:
                    label += f"- {attr}\n"
                    
            # Add methods
            if class_info["methods"]:
                label += "\nMethods:\n"
                for method in class_info["methods"]:
                    label += f"- {method}\n"
                    
            dot.node(class_info["name"], label, shape='record')
            
        # Add inheritance relationships
        for class_info in classes:
            for base in class_info["bases"]:
                if any(c["name"] == base for c in classes):
                    dot.edge(class_info["name"], base)
                    
        return dot
    
    def _generate_sequence_diagram(self, sequences: List[Dict[str, Any]]) -> graphviz.Digraph:
        """Generate a sequence diagram."""
        dot = graphviz.Digraph(comment='Sequence Diagram')
        dot.attr(rankdir='TB')
        
        # Add participants
        participants = set()
        for sequence in sequences:
            participants.update(sequence["participants"])
            
        for participant in participants:
            dot.node(participant, participant, shape='box')
            
        # Add interactions
        for sequence in sequences:
            for i, interaction in enumerate(sequence["interactions"]):
                dot.edge(interaction["from"], 
                        interaction["to"],
                        label=f"{i+1}. {interaction['message']}")
                
        return dot
    
    def _save_documentation(self, docs: Dict[str, Any], doc_type: str):
        """Save documentation to files."""
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(self.config.output_dir, f"{doc_type}_docs.json")
        with open(json_path, 'w') as f:
            json.dump(docs, f, indent=2)
            
        # Convert to markdown
        md_path = os.path.join(self.config.output_dir, f"{doc_type}_docs.md")
        with open(md_path, 'w') as f:
            f.write(f"# {docs['title']}\n\n")
            f.write(f"Generated: {docs['timestamp']}\n\n")
            
            if doc_type == "api":
                self._write_api_markdown(docs, f)
            elif doc_type == "code":
                self._write_code_markdown(docs, f)
                
        # Convert to HTML if requested
        if self.config.format == "html":
            html_path = os.path.join(self.config.output_dir, f"{doc_type}_docs.html")
            with open(md_path, 'r') as f:
                md_content = f.read()
                html_content = markdown.markdown(md_content)
                with open(html_path, 'w') as h:
                    h.write(html_content)
    
    def _save_readme(self, readme: Dict[str, Any], project_dir: str):
        """Save README file."""
        readme_path = os.path.join(project_dir, "README.md")
        
        with open(readme_path, 'w') as f:
            f.write(f"# {readme['title']}\n\n")
            f.write(f"{readme['description']}\n\n")
            f.write(f"Version: {readme['version']}\n\n")
            
            for section in readme["sections"]:
                f.write(f"## {section['title']}\n\n")
                f.write(f"{section['content']}\n\n")
    
    def _save_diagram(self, diagram: graphviz.Digraph, diagram_type: str) -> str:
        """Save a diagram to a file."""
        # Create output directory
        os.makedirs(self.config.output_dir, exist_ok=True)
        
        # Save diagram
        output_path = os.path.join(self.config.output_dir, f"{diagram_type}_diagram")
        diagram.render(output_path, format='png', cleanup=True)
        
        return f"{output_path}.png"
    
    def _get_version(self) -> str:
        """Get the current version of the project."""
        try:
            with open("setup.py", 'r') as f:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'setup':
                        for keyword in node.keywords:
                            if keyword.arg == 'version':
                                return keyword.value.value
        except:
            pass
        return "0.1.0"
    
    def _get_http_method(self, node: ast.FunctionDef) -> str:
        """Get the HTTP method from a function's decorators."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute):
                if decorator.func.attr in ['get', 'post', 'put', 'delete', 'patch']:
                    return decorator.func.attr.upper()
        return "GET"
    
    def _get_parameters(self, node: ast.FunctionDef) -> List[Dict[str, Any]]:
        """Get function parameters with types and defaults."""
        params = []
        for arg in node.args.args:
            param = {
                "name": arg.arg,
                "type": self._get_annotation_type(arg.annotation) if arg.annotation else None,
                "default": None
            }
            params.append(param)
        return params
    
    def _get_return_type(self, node: ast.FunctionDef) -> Optional[str]:
        """Get function return type."""
        if node.returns:
            return self._get_annotation_type(node.returns)
        return None
    
    def _get_annotation_type(self, annotation: ast.AST) -> str:
        """Convert an AST annotation to a string type."""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                return f"{annotation.value.id}[{self._get_annotation_type(annotation.slice)}]"
        return str(annotation)
    
    def _get_model_fields(self, node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Get Pydantic model fields."""
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                field = {
                    "name": item.target.id,
                    "type": self._get_annotation_type(item.annotation),
                    "default": None
                }
                fields.append(field)
        return fields
    
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
    
    def _get_class_methods(self, node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Get class methods with their signatures."""
        methods = []
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                method = {
                    "name": item.name,
                    "parameters": self._get_parameters(item),
                    "return_type": self._get_return_type(item),
                    "docstring": ast.get_docstring(item)
                }
                methods.append(method)
        return methods
    
    def _get_class_attributes(self, node: ast.ClassDef) -> List[Dict[str, Any]]:
        """Get class attributes with their types."""
        attributes = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign):
                attribute = {
                    "name": item.target.id,
                    "type": self._get_annotation_type(item.annotation),
                    "default": None
                }
                attributes.append(attribute)
        return attributes
    
    def _get_component_type(self, file_path: str) -> str:
        """Determine the type of a component from its path."""
        if "api" in file_path:
            return "API"
        elif "service" in file_path:
            return "Service"
        elif "model" in file_path:
            return "Model"
        elif "controller" in file_path:
            return "Controller"
        return "Component"
    
    def _analyze_sequence(self, node: ast.FunctionDef) -> Optional[Dict[str, Any]]:
        """Analyze a function for sequence patterns."""
        sequence = {
            "name": node.name,
            "participants": set(),
            "interactions": []
        }
        
        for item in ast.walk(node):
            if isinstance(item, ast.Call):
                if isinstance(item.func, ast.Attribute):
                    # Method call
                    if isinstance(item.func.value, ast.Name):
                        sequence["participants"].add(item.func.value.id)
                        sequence["interactions"].append({
                            "from": "self",
                            "to": item.func.value.id,
                            "message": f"{item.func.attr}()"
                        })
                        
        if sequence["interactions"]:
            sequence["participants"] = list(sequence["participants"])
            return sequence
        return None
    
    def _extract_docstring_params(self, docstring: str) -> List[str]:
        """Extract parameter names from a docstring."""
        params = []
        if docstring:
            # Look for :param: or :param name: patterns
            param_pattern = r":param\s+(\w+):"
            params = re.findall(param_pattern, docstring)
        return params
    
    def _write_api_markdown(self, docs: Dict[str, Any], file):
        """Write API documentation in markdown format."""
        # Write endpoints
        file.write("## Endpoints\n\n")
        for endpoint in docs["endpoints"]:
            file.write(f"### {endpoint['method']} {endpoint['name']}\n\n")
            file.write(f"{endpoint['description']}\n\n")
            
            if endpoint["parameters"]:
                file.write("#### Parameters\n\n")
                for param in endpoint["parameters"]:
                    file.write(f"- `{param['name']}`: {param['type']}\n")
                file.write("\n")
                
            if endpoint["return_type"]:
                file.write(f"#### Returns\n\n`{endpoint['return_type']}`\n\n")
                
            if endpoint["examples"]:
                file.write("#### Examples\n\n")
                for example in endpoint["examples"]:
                    file.write(f"```python\n{example}\n```\n\n")
                    
        # Write models
        file.write("## Models\n\n")
        for model in docs["models"]:
            file.write(f"### {model['name']}\n\n")
            file.write(f"{model['description']}\n\n")
            
            if model["fields"]:
                file.write("#### Fields\n\n")
                for field in model["fields"]:
                    file.write(f"- `{field['name']}`: {field['type']}\n")
                file.write("\n")
                
            if model["examples"]:
                file.write("#### Examples\n\n")
                for example in model["examples"]:
                    file.write(f"```python\n{example}\n```\n\n")
    
    def _write_code_markdown(self, docs: Dict[str, Any], file):
        """Write code documentation in markdown format."""
        # Write modules
        file.write("## Modules\n\n")
        for module in docs["modules"]:
            file.write(f"### {module['name']}\n\n")
            file.write(f"{module['description']}\n\n")
            
            if module["imports"]:
                file.write("#### Imports\n\n")
                for imp in module["imports"]:
                    file.write(f"- `{imp}`\n")
                file.write("\n")
                
            if "usage" in module:
                file.write("#### Usage\n\n")
                file.write(f"{module['usage']}\n\n")
                
        # Write classes
        file.write("## Classes\n\n")
        for class_info in docs["classes"]:
            file.write(f"### {class_info['name']}\n\n")
            file.write(f"{class_info['description']}\n\n")
            
            if class_info["attributes"]:
                file.write("#### Attributes\n\n")
                for attr in class_info["attributes"]:
                    file.write(f"- `{attr['name']}`: {attr['type']}\n")
                file.write("\n")
                
            if class_info["methods"]:
                file.write("#### Methods\n\n")
                for method in class_info["methods"]:
                    file.write(f"##### {method['name']}\n\n")
                    file.write(f"{method['docstring']}\n\n")
                    
                    if method["parameters"]:
                        file.write("Parameters:\n")
                        for param in method["parameters"]:
                            file.write(f"- `{param['name']}`: {param['type']}\n")
                        file.write("\n")
                        
                    if method["return_type"]:
                        file.write(f"Returns: `{method['return_type']}`\n\n")
                        
            if class_info["examples"]:
                file.write("#### Examples\n\n")
                for example in class_info["examples"]:
                    file.write(f"```python\n{example}\n```\n\n")
                    
        # Write functions
        file.write("## Functions\n\n")
        for func in docs["functions"]:
            file.write(f"### {func['name']}\n\n")
            file.write(f"{func['description']}\n\n")
            
            if func["parameters"]:
                file.write("#### Parameters\n\n")
                for param in func["parameters"]:
                    file.write(f"- `{param['name']}`: {param['type']}\n")
                file.write("\n")
                
            if func["return_type"]:
                file.write(f"#### Returns\n\n`{func['return_type']}`\n\n")
                
            if func["examples"]:
                file.write("#### Examples\n\n")
                for example in func["examples"]:
                    file.write(f"```python\n{example}\n```\n\n")
                    
        # Write suggestions
        if docs["suggestions"]:
            file.write("## Documentation Suggestions\n\n")
            for suggestion in docs["suggestions"]:
                file.write(f"### {suggestion['element'].title()}: {suggestion['name']}\n\n")
                file.write(f"**Issue**: {suggestion['type']}\n\n")
                file.write(f"**Suggestion**: {suggestion['suggestion']}\n\n")
                file.write(f"**Location**: {suggestion['path']}\n\n") 