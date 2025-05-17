import os
import json
import pkg_resources
import subprocess
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from pathlib import Path

@dataclass
class DependencyInfo:
    name: str
    version: str
    latest_version: Optional[str]
    is_outdated: bool
    vulnerabilities: List[Dict[str, Any]]
    license: Optional[str]
    dependencies: List[str]

class DependencyAnalyzer:
    """Analyzes project dependencies and provides insights."""
    
    def __init__(self):
        self.supported_managers = {
            'python': ['requirements.txt', 'setup.py', 'Pipfile', 'pyproject.toml'],
            'node': ['package.json'],
            'ruby': ['Gemfile'],
            'php': ['composer.json'],
            'java': ['pom.xml', 'build.gradle']
        }
    
    def detect_package_manager(self, directory: str) -> Optional[str]:
        """Detect the package manager used in the project."""
        for manager, files in self.supported_managers.items():
            for file in files:
                if os.path.exists(os.path.join(directory, file)):
                    return manager
        return None
    
    def analyze_python_dependencies(self, directory: str) -> List[DependencyInfo]:
        """Analyze Python project dependencies."""
        dependencies = []
        
        # Check requirements.txt
        req_file = os.path.join(directory, 'requirements.txt')
        if os.path.exists(req_file):
            with open(req_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        try:
                            pkg = pkg_resources.working_set.by_key[line.split('==')[0]]
                            latest = self._get_latest_version(pkg.key)
                            deps = self._get_dependencies(pkg.key)
                            vulns = self._check_vulnerabilities(pkg.key, pkg.version)
                            
                            dependencies.append(DependencyInfo(
                                name=pkg.key,
                                version=pkg.version,
                                latest_version=latest,
                                is_outdated=latest and pkg.version < latest,
                                vulnerabilities=vulns,
                                license=self._get_license(pkg.key),
                                dependencies=deps
                            ))
                        except Exception as e:
                            print(f"Error analyzing {line}: {str(e)}")
        
        return dependencies
    
    def analyze_node_dependencies(self, directory: str) -> List[DependencyInfo]:
        """Analyze Node.js project dependencies."""
        dependencies = []
        package_json = os.path.join(directory, 'package.json')
        
        if os.path.exists(package_json):
            with open(package_json, 'r') as f:
                data = json.load(f)
                deps = {**data.get('dependencies', {}), **data.get('devDependencies', {})}
                
                for name, version in deps.items():
                    try:
                        latest = self._get_latest_version(name, 'npm')
                        vulns = self._check_vulnerabilities(name, version, 'npm')
                        subdeps = self._get_dependencies(name, 'npm')
                        
                        dependencies.append(DependencyInfo(
                            name=name,
                            version=version,
                            latest_version=latest,
                            is_outdated=latest and version < latest,
                            vulnerabilities=vulns,
                            license=self._get_license(name, 'npm'),
                            dependencies=subdeps
                        ))
                    except Exception as e:
                        print(f"Error analyzing {name}: {str(e)}")
        
        return dependencies
    
    def _get_latest_version(self, package: str, manager: str = 'pip') -> Optional[str]:
        """Get the latest version of a package."""
        try:
            if manager == 'pip':
                result = subprocess.run(
                    ['pip', 'index', 'versions', package],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    # Parse the output to get the latest version
                    return result.stdout.split('\n')[0].split(' ')[-1]
            elif manager == 'npm':
                result = subprocess.run(
                    ['npm', 'view', package, 'version'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def _check_vulnerabilities(self, package: str, version: str, manager: str = 'pip') -> List[Dict[str, Any]]:
        """Check for known vulnerabilities in a package."""
        vulnerabilities = []
        try:
            if manager == 'pip':
                result = subprocess.run(
                    ['safety', 'check', f'{package}=={version}', '--json'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    vulnerabilities = json.loads(result.stdout)
            elif manager == 'npm':
                result = subprocess.run(
                    ['npm', 'audit', '--json'],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    audit_data = json.loads(result.stdout)
                    if package in audit_data.get('advisories', {}):
                        vulnerabilities = audit_data['advisories'][package]
        except Exception:
            pass
        return vulnerabilities
    
    def _get_dependencies(self, package: str, manager: str = 'pip') -> List[str]:
        """Get direct dependencies of a package."""
        dependencies = []
        try:
            if manager == 'pip':
                result = subprocess.run(
                    ['pip', 'show', package],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Requires:'):
                            dependencies = [d.strip() for d in line.split(':')[1].split(',')]
            elif manager == 'npm':
                result = subprocess.run(
                    ['npm', 'ls', '--json'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    if package in data.get('dependencies', {}):
                        dependencies = list(data['dependencies'][package].get('dependencies', {}).keys())
        except Exception:
            pass
        return dependencies
    
    def _get_license(self, package: str, manager: str = 'pip') -> Optional[str]:
        """Get the license of a package."""
        try:
            if manager == 'pip':
                result = subprocess.run(
                    ['pip', 'show', package],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if line.startswith('License:'):
                            return line.split(':')[1].strip()
            elif manager == 'npm':
                result = subprocess.run(
                    ['npm', 'view', package, 'license'],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return result.stdout.strip()
        except Exception:
            pass
        return None
    
    def analyze_dependencies(self, directory: str) -> Dict[str, Any]:
        """Analyze all dependencies in a project."""
        manager = self.detect_package_manager(directory)
        if not manager:
            return {"error": "No supported package manager found"}
        
        dependencies = []
        if manager == 'python':
            dependencies = self.analyze_python_dependencies(directory)
        elif manager == 'node':
            dependencies = self.analyze_node_dependencies(directory)
        
        return {
            "package_manager": manager,
            "dependencies": [
                {
                    "name": dep.name,
                    "version": dep.version,
                    "latest_version": dep.latest_version,
                    "is_outdated": dep.is_outdated,
                    "vulnerabilities": dep.vulnerabilities,
                    "license": dep.license,
                    "dependencies": dep.dependencies
                }
                for dep in dependencies
            ]
        } 