import os
import json
import coverage
import unittest
import ast
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import importlib.util
import sys
from pathlib import Path

@dataclass
class TestMetrics:
    coverage_percentage: float
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    uncovered_lines: List[Dict[str, Any]]
    test_duration: float
    test_categories: Dict[str, int]

class TestAnalyzer:
    """Analyzes test coverage and quality."""
    
    def __init__(self):
        self.cov = coverage.Coverage()
    
    def analyze_tests(self, directory: str) -> Dict[str, Any]:
        """Analyze tests in a directory."""
        test_files = self._find_test_files(directory)
        if not test_files:
            return {"error": "No test files found"}
        
        # Start coverage
        self.cov.start()
        
        # Run tests
        test_metrics = self._run_tests(test_files)
        
        # Stop coverage and get report
        self.cov.stop()
        self.cov.save()
        
        coverage_data = self._analyze_coverage()
        
        return {
            "test_metrics": {
                "coverage_percentage": coverage_data["coverage_percentage"],
                "total_tests": test_metrics.total_tests,
                "passed_tests": test_metrics.passed_tests,
                "failed_tests": test_metrics.failed_tests,
                "skipped_tests": test_metrics.skipped_tests,
                "test_duration": test_metrics.test_duration,
                "test_categories": test_metrics.test_categories
            },
            "coverage_details": {
                "uncovered_lines": coverage_data["uncovered_lines"],
                "file_coverage": coverage_data["file_coverage"]
            },
            "test_quality": self._analyze_test_quality(test_files)
        }
    
    def _find_test_files(self, directory: str) -> List[str]:
        """Find all test files in a directory."""
        test_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.startswith('test_') and file.endswith('.py'):
                    test_files.append(os.path.join(root, file))
        return test_files
    
    def _run_tests(self, test_files: List[str]) -> TestMetrics:
        """Run tests and collect metrics."""
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()
        
        for test_file in test_files:
            spec = importlib.util.spec_from_file_location("test_module", test_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            suite.addTests(loader.loadTestsFromModule(module))
        
        result = unittest.TestResult()
        start_time = time.time()
        suite.run(result)
        end_time = time.time()
        
        # Analyze test categories
        categories = self._analyze_test_categories(test_files)
        
        return TestMetrics(
            coverage_percentage=0,  # Will be updated by coverage analysis
            total_tests=result.testsRun,
            passed_tests=result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
            failed_tests=len(result.failures) + len(result.errors),
            skipped_tests=len(result.skipped),
            uncovered_lines=[],  # Will be updated by coverage analysis
            test_duration=end_time - start_time,
            test_categories=categories
        )
    
    def _analyze_coverage(self) -> Dict[str, Any]:
        """Analyze code coverage."""
        self.cov.report()
        
        # Get coverage data
        coverage_data = {
            "coverage_percentage": self.cov.report(),
            "uncovered_lines": [],
            "file_coverage": {}
        }
        
        # Analyze uncovered lines
        for file_path in self.cov.get_measured_files():
            file_coverage = self.cov.analysis(file_path)
            if file_coverage:
                _, _, not_run, _ = file_coverage
                if not_run:
                    coverage_data["uncovered_lines"].append({
                        "file": file_path,
                        "lines": not_run
                    })
            
            # Get file coverage percentage
            file_coverage = self.cov.analysis2(file_path)
            if file_coverage:
                coverage_data["file_coverage"][file_path] = file_coverage[2]
        
        return coverage_data
    
    def _analyze_test_categories(self, test_files: List[str]) -> Dict[str, int]:
        """Analyze test categories (unit, integration, etc.)."""
        categories = {
            "unit": 0,
            "integration": 0,
            "functional": 0,
            "performance": 0,
            "security": 0
        }
        
        for test_file in test_files:
            with open(test_file, 'r') as f:
                content = f.read()
                
            # Analyze test file content to determine categories
            if "unittest.TestCase" in content:
                categories["unit"] += 1
            if "integration" in content.lower():
                categories["integration"] += 1
            if "functional" in content.lower():
                categories["functional"] += 1
            if "performance" in content.lower():
                categories["performance"] += 1
            if "security" in content.lower():
                categories["security"] += 1
        
        return categories
    
    def _analyze_test_quality(self, test_files: List[str]) -> Dict[str, Any]:
        """Analyze test quality metrics."""
        quality_metrics = {
            "test_size": 0,
            "assertion_density": 0,
            "test_complexity": 0,
            "test_isolation": 0,
            "test_readability": 0
        }
        
        total_asserts = 0
        total_lines = 0
        total_complexity = 0
        
        for test_file in test_files:
            with open(test_file, 'r') as f:
                content = f.read()
                tree = ast.parse(content)
                
                # Count assertions
                asserts = sum(1 for node in ast.walk(tree) if isinstance(node, ast.Call) 
                            and isinstance(node.func, ast.Name) 
                            and node.func.id.startswith('assert'))
                total_asserts += asserts
                
                # Count lines
                lines = len(content.splitlines())
                total_lines += lines
                
                # Calculate complexity
                complexity = self._calculate_complexity(tree)
                total_complexity += complexity
        
        if total_lines > 0:
            quality_metrics["test_size"] = total_lines
            quality_metrics["assertion_density"] = total_asserts / total_lines
            quality_metrics["test_complexity"] = total_complexity / len(test_files)
        
        return quality_metrics
    
    def _calculate_complexity(self, tree: ast.AST) -> int:
        """Calculate cyclomatic complexity of a test file."""
        complexity = 1  # Base complexity
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.While, ast.For, ast.Try, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(node, ast.BoolOp):
                complexity += len(node.values) - 1
        
        return complexity
    
    def get_test_recommendations(self, analysis_results: Dict[str, Any]) -> List[str]:
        """Generate test improvement recommendations."""
        recommendations = []
        
        # Check coverage
        if analysis_results["test_metrics"]["coverage_percentage"] < 80:
            recommendations.append("Test coverage is below 80%. Consider adding more tests.")
        
        # Check test distribution
        categories = analysis_results["test_metrics"]["test_categories"]
        if categories["unit"] == 0:
            recommendations.append("No unit tests found. Consider adding unit tests.")
        if categories["integration"] == 0:
            recommendations.append("No integration tests found. Consider adding integration tests.")
        
        # Check test quality
        quality = analysis_results["test_quality"]
        if quality["assertion_density"] < 0.1:
            recommendations.append("Low assertion density. Consider adding more assertions to tests.")
        if quality["test_complexity"] > 10:
            recommendations.append("High test complexity. Consider simplifying test cases.")
        
        # Check for failed tests
        if analysis_results["test_metrics"]["failed_tests"] > 0:
            recommendations.append("Some tests are failing. Review and fix failing tests.")
        
        return recommendations 