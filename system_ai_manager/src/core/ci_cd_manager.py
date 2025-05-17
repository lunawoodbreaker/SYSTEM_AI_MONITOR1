from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import yaml
import requests
from pathlib import Path
import subprocess
import docker
from datetime import datetime
import psutil
import logging
from github import Github
from github.Repository import Repository
from github.Workflow import Workflow

@dataclass
class CICDConfig:
    """Configuration for CI/CD pipeline."""
    repo_url: str
    github_token: Optional[str] = None
    docker_registry: Optional[str] = None
    docker_username: Optional[str] = None
    docker_password: Optional[str] = None
    environment: str = "development"
    auto_deploy: bool = False
    notify_on_failure: bool = True
    test_coverage_threshold: float = 0.8
    performance_threshold: float = 0.9
    health_check_interval: int = 300
    max_rollback_attempts: int = 3
    resource_limits: Dict[str, float] = None
    monitoring_endpoints: List[str] = None

class CICDManager:
    """AI-driven CI/CD pipeline management system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = CICDConfig(
            repo_url="",
            resource_limits={
                "cpu_percent": 80.0,
                "memory_percent": 80.0,
                "disk_percent": 80.0
            },
            monitoring_endpoints=[]
        )
        self.github = None
        self.repo = None
        self.docker_client = None
        self.logger = logging.getLogger(__name__)
        
    def initialize(self):
        """Initialize the CI/CD system."""
        if self.config.github_token:
            self.github = Github(self.config.github_token)
            self.repo = self.github.get_repo(self.config.repo_url)
            
        if self.config.docker_registry:
            self.docker_client = docker.from_env()
            
        # Initialize monitoring
        self._initialize_monitoring()
            
    def _initialize_monitoring(self):
        """Initialize system monitoring."""
        # Set up logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Start monitoring thread
        import threading
        self.monitoring_thread = threading.Thread(
            target=self._monitor_system_resources,
            daemon=True
        )
        self.monitoring_thread.start()
        
    def _monitor_system_resources(self):
        """Monitor system resources."""
        while True:
            try:
                # Get system metrics
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')
                
                # Check resource limits
                if (cpu_percent > self.config.resource_limits["cpu_percent"] or
                    memory.percent > self.config.resource_limits["memory_percent"] or
                    disk.percent > self.config.resource_limits["disk_percent"]):
                    self.logger.warning(
                        f"Resource limits exceeded: CPU {cpu_percent}%, "
                        f"Memory {memory.percent}%, Disk {disk.percent}%"
                    )
                    self._handle_resource_warning()
                    
                # Sleep for the configured interval
                import time
                time.sleep(self.config.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error monitoring system resources: {str(e)}")
                
    def _handle_resource_warning(self):
        """Handle resource warning by scaling or optimizing."""
        try:
            # Analyze resource usage
            analysis = self._analyze_resource_usage()
            
            # Generate optimization plan
            plan = self._generate_optimization_plan(analysis)
            
            # Execute optimization
            self._execute_optimization(plan)
            
        except Exception as e:
            self.logger.error(f"Error handling resource warning: {str(e)}")
            
    def _analyze_resource_usage(self) -> Dict[str, Any]:
        """Analyze system resource usage."""
        return {
            "cpu": {
                "usage": psutil.cpu_percent(interval=1),
                "processes": self._get_top_processes("cpu")
            },
            "memory": {
                "usage": psutil.virtual_memory().percent,
                "processes": self._get_top_processes("memory")
            },
            "disk": {
                "usage": psutil.disk_usage('/').percent,
                "largest_files": self._get_largest_files()
            }
        }
        
    def _get_top_processes(self, resource: str) -> List[Dict[str, Any]]:
        """Get top processes by resource usage."""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                pinfo = proc.info
                if resource == "cpu":
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "usage": pinfo['cpu_percent']
                    })
                elif resource == "memory":
                    processes.append({
                        "pid": pinfo['pid'],
                        "name": pinfo['name'],
                        "usage": pinfo['memory_percent']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        return sorted(processes, key=lambda x: x['usage'], reverse=True)[:5]
        
    def _get_largest_files(self) -> List[Dict[str, Any]]:
        """Get largest files in the system."""
        files = []
        for root, _, filenames in os.walk('/'):
            for filename in filenames:
                try:
                    path = os.path.join(root, filename)
                    size = os.path.getsize(path)
                    files.append({
                        "path": path,
                        "size": size
                    })
                except (OSError, PermissionError):
                    continue
                    
        return sorted(files, key=lambda x: x['size'], reverse=True)[:10]
        
    def _generate_optimization_plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimization plan based on resource analysis."""
        plan = {
            "actions": [],
            "priority": "high" if any(
                analysis[resource]["usage"] > self.config.resource_limits[f"{resource}_percent"]
                for resource in ["cpu", "memory", "disk"]
            ) else "medium"
        }
        
        # CPU optimization
        if analysis["cpu"]["usage"] > self.config.resource_limits["cpu_percent"]:
            plan["actions"].append({
                "type": "cpu",
                "action": "scale",
                "target": "horizontal",
                "reason": "High CPU usage detected"
            })
            
        # Memory optimization
        if analysis["memory"]["usage"] > self.config.resource_limits["memory_percent"]:
            plan["actions"].append({
                "type": "memory",
                "action": "cleanup",
                "target": "cache",
                "reason": "High memory usage detected"
            })
            
        # Disk optimization
        if analysis["disk"]["usage"] > self.config.resource_limits["disk_percent"]:
            plan["actions"].append({
                "type": "disk",
                "action": "cleanup",
                "target": "logs",
                "reason": "High disk usage detected"
            })
            
        return plan
        
    def _execute_optimization(self, plan: Dict[str, Any]):
        """Execute optimization plan."""
        for action in plan["actions"]:
            try:
                if action["type"] == "cpu":
                    self._optimize_cpu(action)
                elif action["type"] == "memory":
                    self._optimize_memory(action)
                elif action["type"] == "disk":
                    self._optimize_disk(action)
            except Exception as e:
                self.logger.error(f"Error executing optimization action: {str(e)}")
                
    def _optimize_cpu(self, action: Dict[str, Any]):
        """Optimize CPU usage."""
        if action["action"] == "scale":
            # Implement horizontal scaling logic
            self._scale_horizontally()
            
    def _optimize_memory(self, action: Dict[str, Any]):
        """Optimize memory usage."""
        if action["action"] == "cleanup":
            # Implement cache cleanup logic
            self._cleanup_memory_cache()
            
    def _optimize_disk(self, action: Dict[str, Any]):
        """Optimize disk usage."""
        if action["action"] == "cleanup":
            # Implement log cleanup logic
            self._cleanup_logs()
            
    def _scale_horizontally(self):
        """Scale the application horizontally."""
        try:
            # Get current deployment
            deployment = self._get_current_deployment()
            
            # Calculate new replica count
            current_replicas = deployment.get("replicas", 1)
            new_replicas = min(current_replicas + 1, 5)  # Max 5 replicas
            
            # Update deployment
            self._update_deployment_replicas(new_replicas)
            
            self.logger.info(f"Scaled deployment to {new_replicas} replicas")
            
        except Exception as e:
            self.logger.error(f"Error scaling horizontally: {str(e)}")
            
    def _cleanup_memory_cache(self):
        """Clean up memory cache."""
        try:
            # Clear Docker cache
            self.docker_client.images.prune()
            
            # Clear system cache
            if os.name == 'posix':
                subprocess.run(['sync'], check=True)
                with open('/proc/sys/vm/drop_caches', 'w') as f:
                    f.write('3')
                    
            self.logger.info("Cleaned up memory cache")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up memory cache: {str(e)}")
            
    def _cleanup_logs(self):
        """Clean up old log files."""
        try:
            # Find old log files
            log_dir = "logs"
            if os.path.exists(log_dir):
                for file in os.listdir(log_dir):
                    if file.endswith('.log'):
                        file_path = os.path.join(log_dir, file)
                        # Remove logs older than 7 days
                        if os.path.getmtime(file_path) < (datetime.now().timestamp() - 7 * 24 * 60 * 60):
                            os.remove(file_path)
                            
            self.logger.info("Cleaned up old log files")
            
        except Exception as e:
            self.logger.error(f"Error cleaning up logs: {str(e)}")
            
    def _get_current_deployment(self) -> Dict[str, Any]:
        """Get current deployment information."""
        # Implement deployment info retrieval
        return {"replicas": 1}
        
    def _update_deployment_replicas(self, replicas: int):
        """Update deployment replica count."""
        # Implement deployment update logic
        pass

    def setup_pipeline(self) -> Dict[str, Any]:
        """Set up the CI/CD pipeline."""
        try:
            # Create GitHub Actions workflow
            workflow = self._create_workflow()
            
            # Create Docker configuration
            docker_config = self._create_docker_config()
            
            # Create deployment configuration
            deploy_config = self._create_deploy_config()
            
            return {
                "status": "success",
                "workflow": workflow,
                "docker_config": docker_config,
                "deploy_config": deploy_config
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def run_pipeline(self, branch: str) -> Dict[str, Any]:
        """Run the CI/CD pipeline for a branch."""
        try:
            # Get the branch
            branch_ref = self.repo.get_branch(branch)
            
            # Run tests
            test_results = self._run_tests(branch)
            
            # Build Docker image
            if test_results["status"] == "success":
                build_results = self._build_docker_image(branch)
            else:
                return {
                    "status": "error",
                    "error": "Tests failed",
                    "test_results": test_results
                }
                
            # Deploy if configured
            if self.config.auto_deploy and build_results["status"] == "success":
                deploy_results = self._deploy(branch, build_results["image"])
            else:
                deploy_results = None
                
            return {
                "status": "success",
                "branch": branch,
                "test_results": test_results,
                "build_results": build_results,
                "deploy_results": deploy_results
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "branch": branch
            }
    
    def monitor_pipeline(self, run_id: int) -> Dict[str, Any]:
        """Monitor a CI/CD pipeline run."""
        try:
            # Get the workflow run
            run = self.repo.get_workflow_run(run_id)
            
            # Get the status
            status = run.status
            conclusion = run.conclusion
            
            # Get the jobs
            jobs = run.get_jobs()
            
            # Get the logs
            logs = {}
            for job in jobs:
                logs[job.name] = job.get_logs()
                
            # Check for failures
            if conclusion == "failure":
                if self.config.notify_on_failure:
                    self._notify_failure(run)
                    
            return {
                "status": "success",
                "run_id": run_id,
                "status": status,
                "conclusion": conclusion,
                "jobs": [job.name for job in jobs],
                "logs": logs
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "run_id": run_id
            }
    
    def _create_workflow(self) -> Dict[str, Any]:
        """Create GitHub Actions workflow configuration."""
        workflow = {
            "name": "CI/CD Pipeline",
            "on": {
                "push": {
                    "branches": ["main", "development"]
                },
                "pull_request": {
                    "branches": ["main", "development"]
                }
            },
            "jobs": {
                "test": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v2"
                        },
                        {
                            "name": "Set up Python",
                            "uses": "actions/setup-python@v2",
                            "with": {
                                "python-version": "3.9"
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": "pip install -r requirements.txt"
                        },
                        {
                            "name": "Run tests",
                            "run": "pytest --cov=./ --cov-report=xml"
                        }
                    ]
                },
                "build": {
                    "needs": "test",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v2"
                        },
                        {
                            "name": "Build Docker image",
                            "run": "docker build -t ${{ github.repository }}:${{ github.sha }} ."
                        }
                    ]
                },
                "deploy": {
                    "needs": "build",
                    "if": "github.ref == 'refs/heads/main'",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v2"
                        },
                        {
                            "name": "Deploy",
                            "run": "echo 'Deploying...'"
                        }
                    ]
                }
            }
        }
        
        # Create the workflow file
        workflow_path = ".github/workflows/ci-cd.yml"
        self.repo.create_file(
            path=workflow_path,
            message="Add CI/CD workflow",
            content=yaml.dump(workflow),
            branch="main"
        )
        
        return workflow
    
    def _create_docker_config(self) -> Dict[str, Any]:
        """Create Docker configuration."""
        dockerfile = """FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
"""
        
        # Create the Dockerfile
        with open("Dockerfile", "w") as f:
            f.write(dockerfile)
            
        return {
            "dockerfile": dockerfile,
            "path": "Dockerfile"
        }
    
    def _create_deploy_config(self) -> Dict[str, Any]:
        """Create deployment configuration."""
        deploy_config = {
            "development": {
                "host": "dev.example.com",
                "port": 8080,
                "environment": "development"
            },
            "staging": {
                "host": "staging.example.com",
                "port": 8080,
                "environment": "staging"
            },
            "production": {
                "host": "prod.example.com",
                "port": 8080,
                "environment": "production"
            }
        }
        
        # Create the deployment config file
        config_path = "deploy/config.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        with open(config_path, "w") as f:
            yaml.dump(deploy_config, f)
            
        return deploy_config
    
    def _run_tests(self, branch: str) -> Dict[str, Any]:
        """Run tests for a branch."""
        try:
            # Checkout the branch
            subprocess.run(["git", "checkout", branch], check=True)
            
            # Install dependencies
            subprocess.run(["pip", "install", "-r", "requirements.txt"], check=True)
            
            # Run tests
            result = subprocess.run(
                ["pytest", "--cov=./", "--cov-report=xml"],
                capture_output=True,
                text=True
            )
            
            # Parse test results
            test_results = {
                "status": "success" if result.returncode == 0 else "failure",
                "output": result.stdout,
                "error": result.stderr,
                "coverage": self._parse_coverage("coverage.xml")
            }
            
            return test_results
            
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "error": str(e),
                "output": e.stdout,
                "error_output": e.stderr
            }
    
    def _build_docker_image(self, branch: str) -> Dict[str, Any]:
        """Build Docker image for a branch."""
        try:
            # Build the image
            image_name = f"{self.repo.full_name}:{branch}"
            image, logs = self.docker_client.images.build(
                path=".",
                tag=image_name,
                rm=True
            )
            
            # Push to registry if configured
            if self.config.docker_registry:
                self._push_docker_image(image_name)
                
            return {
                "status": "success",
                "image": image_name,
                "logs": logs
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _deploy(self, branch: str, image: str) -> Dict[str, Any]:
        """Deploy the application."""
        try:
            # Get deployment config
            config = self._get_deploy_config(branch)
            
            # Deploy to the target environment
            if config["environment"] == "development":
                result = self._deploy_to_development(image, config)
            elif config["environment"] == "staging":
                result = self._deploy_to_staging(image, config)
            elif config["environment"] == "production":
                result = self._deploy_to_production(image, config)
            else:
                raise ValueError(f"Unknown environment: {config['environment']}")
                
            return {
                "status": "success",
                "environment": config["environment"],
                "result": result
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _push_docker_image(self, image_name: str):
        """Push Docker image to registry."""
        # Login to registry
        self.docker_client.login(
            username=self.config.docker_username,
            password=self.config.docker_password,
            registry=self.config.docker_registry
        )
        
        # Tag the image
        registry_image = f"{self.config.docker_registry}/{image_name}"
        self.docker_client.images.get(image_name).tag(registry_image)
        
        # Push the image
        self.docker_client.images.push(registry_image)
    
    def _get_deploy_config(self, branch: str) -> Dict[str, Any]:
        """Get deployment configuration for a branch."""
        if branch == "main":
            return {
                "environment": "production",
                "host": "prod.example.com",
                "port": 8080
            }
        elif branch == "staging":
            return {
                "environment": "staging",
                "host": "staging.example.com",
                "port": 8080
            }
        else:
            return {
                "environment": "development",
                "host": "dev.example.com",
                "port": 8080
            }
    
    def _deploy_to_development(self, image: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to development environment."""
        try:
            # Check system health before deployment
            health_check = self._check_system_health()
            if not health_check["healthy"]:
                return {
                    "status": "error",
                    "error": "System health check failed",
                    "details": health_check
                }
                
            # Deploy with monitoring
            deployment = self._deploy_with_monitoring(image, config)
            
            # Verify deployment
            verification = self._verify_deployment(deployment)
            if not verification["success"]:
                # Attempt rollback
                self._rollback_deployment(deployment)
                return {
                    "status": "error",
                    "error": "Deployment verification failed",
                    "details": verification
                }
                
            return {
                "status": "success",
                "message": "Deployed to development",
                "deployment": deployment,
                "verification": verification
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _check_system_health(self) -> Dict[str, Any]:
        """Check system health before deployment."""
        health = {
            "healthy": True,
            "checks": {}
        }
        
        # Check CPU
        cpu_percent = psutil.cpu_percent(interval=1)
        health["checks"]["cpu"] = {
            "status": "healthy" if cpu_percent < self.config.resource_limits["cpu_percent"] else "unhealthy",
            "value": cpu_percent
        }
        
        # Check memory
        memory = psutil.virtual_memory()
        health["checks"]["memory"] = {
            "status": "healthy" if memory.percent < self.config.resource_limits["memory_percent"] else "unhealthy",
            "value": memory.percent
        }
        
        # Check disk
        disk = psutil.disk_usage('/')
        health["checks"]["disk"] = {
            "status": "healthy" if disk.percent < self.config.resource_limits["disk_percent"] else "unhealthy",
            "value": disk.percent
        }
        
        # Update overall health
        health["healthy"] = all(
            check["status"] == "healthy"
            for check in health["checks"].values()
        )
        
        return health
        
    def _deploy_with_monitoring(self, image: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy with monitoring enabled."""
        deployment = {
            "image": image,
            "config": config,
            "start_time": datetime.now().isoformat(),
            "metrics": {}
        }
        
        # Start deployment
        # Add your deployment logic here
        
        # Start monitoring
        self._start_deployment_monitoring(deployment)
        
        return deployment
        
    def _verify_deployment(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Verify deployment success."""
        verification = {
            "success": True,
            "checks": {}
        }
        
        # Check application health
        health = self._check_application_health(deployment)
        verification["checks"]["health"] = health
        
        # Check performance
        performance = self._check_application_performance(deployment)
        verification["checks"]["performance"] = performance
        
        # Update overall success
        verification["success"] = all(
            check["status"] == "success"
            for check in verification["checks"].values()
        )
        
        return verification
        
    def _check_application_health(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Check application health."""
        # Implement health check logic
        return {
            "status": "success",
            "message": "Application healthy"
        }
        
    def _check_application_performance(self, deployment: Dict[str, Any]) -> Dict[str, Any]:
        """Check application performance."""
        # Implement performance check logic
        return {
            "status": "success",
            "message": "Performance acceptable"
        }
        
    def _rollback_deployment(self, deployment: Dict[str, Any]):
        """Rollback failed deployment."""
        try:
            # Get previous version
            previous_version = self._get_previous_version()
            
            # Rollback to previous version
            self._deploy_version(previous_version)
            
            self.logger.info(f"Rolled back to version {previous_version}")
            
        except Exception as e:
            self.logger.error(f"Error rolling back deployment: {str(e)}")
            
    def _get_previous_version(self) -> str:
        """Get previous deployment version."""
        # Implement version retrieval logic
        return "previous-version"
        
    def _deploy_version(self, version: str):
        """Deploy specific version."""
        # Implement version deployment logic
        pass
        
    def _start_deployment_monitoring(self, deployment: Dict[str, Any]):
        """Start monitoring deployment."""
        # Implement deployment monitoring logic
        pass
    
    def _deploy_to_staging(self, image: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to staging environment."""
        # Add your staging deployment logic here
        return {
            "status": "success",
            "message": "Deployed to staging"
        }
    
    def _deploy_to_production(self, image: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to production environment."""
        # Add your production deployment logic here
        return {
            "status": "success",
            "message": "Deployed to production"
        }
    
    def _parse_coverage(self, coverage_file: str) -> Dict[str, Any]:
        """Parse test coverage report."""
        try:
            import xml.etree.ElementTree as ET
            
            # Parse the coverage XML file
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            # Get coverage metrics
            coverage = {
                "lines": {
                    "total": int(root.get("lines-valid", 0)),
                    "covered": int(root.get("lines-covered", 0)),
                    "percentage": float(root.get("line-rate", 0)) * 100
                },
                "branches": {
                    "total": int(root.get("branches-valid", 0)),
                    "covered": int(root.get("branches-covered", 0)),
                    "percentage": float(root.get("branch-rate", 0)) * 100
                }
            }
            
            return coverage
            
        except Exception as e:
            return {
                "error": str(e)
            }
    
    def _notify_failure(self, run: Any):
        """Notify about pipeline failure."""
        # Create an issue
        self.repo.create_issue(
            title=f"CI/CD Pipeline Failed: Run #{run.id}",
            body=f"The CI/CD pipeline failed for run #{run.id}.\n\n"
                 f"Status: {run.status}\n"
                 f"Conclusion: {run.conclusion}\n\n"
                 f"View the run: {run.html_url}"
        ) 