from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, time
import asyncio
import json
import os
import requests
from pathlib import Path
import schedule
import time as time_module
import logging
from enum import Enum

class TaskTrigger(Enum):
    TIME = "time"
    INTERVAL = "interval"
    EVENT = "event"
    CONDITION = "condition"

@dataclass
class Task:
    name: str
    description: str
    trigger_type: TaskTrigger
    trigger_value: Any  # time string, interval in seconds, event name, or condition
    action: str  # The action to perform
    parameters: Dict[str, Any]  # Parameters for the action
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class TaskAutomator:
    """AI-driven task automation system."""
    
    def __init__(self, settings):
        self.settings = settings
        self.tasks: List[Task] = []
        self.running = False
        self.logger = logging.getLogger("TaskAutomator")
        self.task_handlers = {
            "analyze_code": self._handle_code_analysis,
            "check_security": self._handle_security_check,
            "optimize_performance": self._handle_performance_optimization,
            "update_dependencies": self._handle_dependency_update,
            "generate_documentation": self._handle_documentation_generation,
            "run_tests": self._handle_test_execution,
            "backup_files": self._handle_backup,
            "notify": self._handle_notification,
            "git_operations": self._handle_git_operations,
            "deploy": self._handle_deployment
        }
        
    def add_task(self, task: Task) -> bool:
        """Add a new task to the automation system."""
        try:
            # Validate task
            if not self._validate_task(task):
                return False
                
            # Add to task list
            self.tasks.append(task)
            
            # Schedule the task
            self._schedule_task(task)
            
            # Save tasks
            self._save_tasks()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding task: {str(e)}")
            return False
    
    def remove_task(self, task_name: str) -> bool:
        """Remove a task from the automation system."""
        try:
            task = next((t for t in self.tasks if t.name == task_name), None)
            if task:
                self.tasks.remove(task)
                self._save_tasks()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error removing task: {str(e)}")
            return False
    
    def update_task(self, task_name: str, updates: Dict[str, Any]) -> bool:
        """Update an existing task."""
        try:
            task = next((t for t in self.tasks if t.name == task_name), None)
            if task:
                for key, value in updates.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                self._save_tasks()
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error updating task: {str(e)}")
            return False
    
    def get_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks in a serializable format."""
        return [self._task_to_dict(task) for task in self.tasks]
    
    def start(self):
        """Start the task automation system."""
        self.running = True
        self._load_tasks()
        
        # Start the scheduler in a separate thread
        asyncio.create_task(self._run_scheduler())
        
        self.logger.info("Task automation system started")
    
    def stop(self):
        """Stop the task automation system."""
        self.running = False
        self.logger.info("Task automation system stopped")
    
    async def _run_scheduler(self):
        """Run the task scheduler."""
        while self.running:
            schedule.run_pending()
            await asyncio.sleep(1)
    
    def _validate_task(self, task: Task) -> bool:
        """Validate a task configuration."""
        try:
            # Check required fields
            if not all([task.name, task.description, task.trigger_type, task.action]):
                return False
            
            # Validate trigger type and value
            if task.trigger_type == TaskTrigger.TIME:
                # Validate time format (HH:MM)
                try:
                    time.fromisoformat(task.trigger_value)
                except ValueError:
                    return False
                    
            elif task.trigger_type == TaskTrigger.INTERVAL:
                # Validate interval (positive number)
                if not isinstance(task.trigger_value, (int, float)) or task.trigger_value <= 0:
                    return False
                    
            elif task.trigger_type == TaskTrigger.EVENT:
                # Validate event name
                if not isinstance(task.trigger_value, str):
                    return False
                    
            elif task.trigger_type == TaskTrigger.CONDITION:
                # Validate condition (should be a valid Python expression)
                try:
                    compile(task.trigger_value, '<string>', 'eval')
                except:
                    return False
            
            # Validate action
            if task.action not in self.task_handlers:
                return False
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error validating task: {str(e)}")
            return False
    
    def _schedule_task(self, task: Task):
        """Schedule a task based on its trigger type."""
        try:
            if task.trigger_type == TaskTrigger.TIME:
                schedule.every().day.at(task.trigger_value).do(
                    self._execute_task, task
                )
            elif task.trigger_type == TaskTrigger.INTERVAL:
                schedule.every(task.trigger_value).seconds.do(
                    self._execute_task, task
                )
            elif task.trigger_type == TaskTrigger.EVENT:
                # Event-based tasks are handled separately
                pass
            elif task.trigger_type == TaskTrigger.CONDITION:
                # Condition-based tasks are checked in the scheduler loop
                pass
                
        except Exception as e:
            self.logger.error(f"Error scheduling task: {str(e)}")
    
    async def _execute_task(self, task: Task):
        """Execute a task."""
        try:
            if not task.enabled:
                return
                
            self.logger.info(f"Executing task: {task.name}")
            
            # Update last run time
            task.last_run = datetime.now()
            
            # Get the handler for this action
            handler = self.task_handlers.get(task.action)
            if handler:
                # Execute the handler
                await handler(task.parameters)
                
                # Update next run time
                if task.trigger_type == TaskTrigger.TIME:
                    task.next_run = datetime.combine(
                        datetime.now().date(),
                        time.fromisoformat(task.trigger_value)
                    )
                elif task.trigger_type == TaskTrigger.INTERVAL:
                    task.next_run = datetime.now() + task.trigger_value
                    
            else:
                self.logger.error(f"No handler found for action: {task.action}")
                
        except Exception as e:
            self.logger.error(f"Error executing task: {str(e)}")
    
    def _save_tasks(self):
        """Save tasks to a file."""
        try:
            tasks_file = Path("tasks.json")
            with open(tasks_file, 'w') as f:
                json.dump([self._task_to_dict(task) for task in self.tasks], f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving tasks: {str(e)}")
    
    def _load_tasks(self):
        """Load tasks from a file."""
        try:
            tasks_file = Path("tasks.json")
            if tasks_file.exists():
                with open(tasks_file, 'r') as f:
                    tasks_data = json.load(f)
                    self.tasks = [self._dict_to_task(task) for task in tasks_data]
                    
                # Reschedule all tasks
                for task in self.tasks:
                    self._schedule_task(task)
        except Exception as e:
            self.logger.error(f"Error loading tasks: {str(e)}")
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert a Task object to a dictionary."""
        return {
            "name": task.name,
            "description": task.description,
            "trigger_type": task.trigger_type.value,
            "trigger_value": task.trigger_value,
            "action": task.action,
            "parameters": task.parameters,
            "enabled": task.enabled,
            "last_run": task.last_run.isoformat() if task.last_run else None,
            "next_run": task.next_run.isoformat() if task.next_run else None
        }
    
    def _dict_to_task(self, data: Dict[str, Any]) -> Task:
        """Convert a dictionary to a Task object."""
        return Task(
            name=data["name"],
            description=data["description"],
            trigger_type=TaskTrigger(data["trigger_type"]),
            trigger_value=data["trigger_value"],
            action=data["action"],
            parameters=data["parameters"],
            enabled=data["enabled"],
            last_run=datetime.fromisoformat(data["last_run"]) if data["last_run"] else None,
            next_run=datetime.fromisoformat(data["next_run"]) if data["next_run"] else None
        )
    
    # Task Handlers
    async def _handle_code_analysis(self, parameters: Dict[str, Any]):
        """Handle code analysis task."""
        try:
            # Get the code analyzer
            from .code_analyzer import CodeAnalyzer
            analyzer = CodeAnalyzer()
            
            # Perform analysis
            if "file" in parameters:
                result = analyzer.analyze_file(parameters["file"])
            elif "directory" in parameters:
                result = analyzer.analyze_directory(parameters["directory"])
            else:
                raise ValueError("No file or directory specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in code analysis: {str(e)}")
    
    async def _handle_security_check(self, parameters: Dict[str, Any]):
        """Handle security check task."""
        try:
            # Get the security analyzer
            from .system_analyzer import SystemAnalyzer
            analyzer = SystemAnalyzer()
            
            # Perform security check
            if "file" in parameters:
                result = analyzer.find_potentially_harmful_files(parameters["file"])
            elif "directory" in parameters:
                result = analyzer.find_potentially_harmful_files(parameters["directory"])
            else:
                raise ValueError("No file or directory specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in security check: {str(e)}")
    
    async def _handle_performance_optimization(self, parameters: Dict[str, Any]):
        """Handle performance optimization task."""
        try:
            # Get the performance profiler
            from .performance_profiler import PerformanceProfiler
            profiler = PerformanceProfiler()
            
            # Perform profiling
            if "file" in parameters:
                result = profiler.profile_file(parameters["file"])
            else:
                raise ValueError("No file specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in performance optimization: {str(e)}")
    
    async def _handle_dependency_update(self, parameters: Dict[str, Any]):
        """Handle dependency update task."""
        try:
            # Get the dependency analyzer
            from .dependency_analyzer import DependencyAnalyzer
            analyzer = DependencyAnalyzer()
            
            # Perform dependency analysis
            if "directory" in parameters:
                result = analyzer.analyze_dependencies(parameters["directory"])
            else:
                raise ValueError("No directory specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in dependency update: {str(e)}")
    
    async def _handle_documentation_generation(self, parameters: Dict[str, Any]):
        """Handle documentation generation task."""
        try:
            # Get the code analyzer
            from .code_analyzer import CodeAnalyzer
            analyzer = CodeAnalyzer()
            
            # Generate documentation
            if "file" in parameters:
                result = analyzer.generate_documentation(parameters["file"])
            elif "directory" in parameters:
                result = analyzer.generate_documentation(parameters["directory"])
            else:
                raise ValueError("No file or directory specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in documentation generation: {str(e)}")
    
    async def _handle_test_execution(self, parameters: Dict[str, Any]):
        """Handle test execution task."""
        try:
            # Get the test analyzer
            from .test_analyzer import TestAnalyzer
            analyzer = TestAnalyzer()
            
            # Run tests
            if "directory" in parameters:
                result = analyzer.analyze_tests(parameters["directory"])
            else:
                raise ValueError("No directory specified")
                
            # Send results to AI for processing
            await self._process_with_ai(result, parameters)
            
        except Exception as e:
            self.logger.error(f"Error in test execution: {str(e)}")
    
    async def _handle_backup(self, parameters: Dict[str, Any]):
        """Handle backup task."""
        try:
            if "source" not in parameters or "destination" not in parameters:
                raise ValueError("Source and destination must be specified")
                
            # Perform backup
            import shutil
            shutil.copytree(parameters["source"], parameters["destination"])
            
        except Exception as e:
            self.logger.error(f"Error in backup: {str(e)}")
    
    async def _handle_notification(self, parameters: Dict[str, Any]):
        """Handle notification task."""
        try:
            if "message" not in parameters:
                raise ValueError("Message must be specified")
                
            # Send notification
            # This is a placeholder - implement your preferred notification method
            print(f"Notification: {parameters['message']}")
            
        except Exception as e:
            self.logger.error(f"Error in notification: {str(e)}")
    
    async def _handle_git_operations(self, parameters: Dict[str, Any]):
        """Handle git operations task."""
        try:
            if "operation" not in parameters:
                raise ValueError("Operation must be specified")
                
            # Perform git operation
            import subprocess
            
            if parameters["operation"] == "commit":
                subprocess.run(["git", "commit", "-m", parameters.get("message", "Auto commit")])
            elif parameters["operation"] == "push":
                subprocess.run(["git", "push"])
            elif parameters["operation"] == "pull":
                subprocess.run(["git", "pull"])
            else:
                raise ValueError(f"Unknown git operation: {parameters['operation']}")
                
        except Exception as e:
            self.logger.error(f"Error in git operations: {str(e)}")
    
    async def _handle_deployment(self, parameters: Dict[str, Any]):
        """Handle deployment task."""
        try:
            if "target" not in parameters:
                raise ValueError("Target must be specified")
                
            # Perform deployment
            # This is a placeholder - implement your preferred deployment method
            print(f"Deploying to {parameters['target']}")
            
        except Exception as e:
            self.logger.error(f"Error in deployment: {str(e)}")
    
    async def _process_with_ai(self, data: Any, parameters: Dict[str, Any]):
        """Process task results with AI."""
        try:
            # Prepare the prompt
            prompt = f"""I have the following task results:

{json.dumps(data, indent=2)}

Please analyze these results and provide:
1. A summary of the findings
2. Recommendations for improvement
3. Any potential issues or concerns
4. Next steps or actions to take

Additional context:
{json.dumps(parameters, indent=2)}"""

            # Send to AI
            response = requests.post(
                f"{self.settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": self.settings.get("ollama.models.text"),
                    "prompt": prompt,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                
                # Handle the AI response
                if "notify" in parameters:
                    await self._handle_notification({
                        "message": f"Task completed with AI analysis:\n{ai_response}"
                    })
                    
                # Save the results
                if "save_results" in parameters:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"task_results_{timestamp}.json"
                    with open(filename, 'w') as f:
                        json.dump({
                            "data": data,
                            "ai_analysis": ai_response,
                            "parameters": parameters,
                            "timestamp": timestamp
                        }, f, indent=2)
                        
            else:
                self.logger.error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            self.logger.error(f"Error processing with AI: {str(e)}") 