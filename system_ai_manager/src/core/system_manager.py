from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import psutil
import platform
import logging
from datetime import datetime
import threading
import time
import queue
import subprocess
import shutil
from pathlib import Path

@dataclass
class SystemConfig:
    """Configuration for system management."""
    monitor_interval: int = 60  # 1 minute
    resource_thresholds: Dict[str, float] = None
    optimization_enabled: bool = True
    auto_cleanup: bool = True
    cleanup_threshold: float = 0.9  # 90%
    log_retention_days: int = 30
    backup_enabled: bool = True
    backup_interval: int = 86400  # 24 hours
    notify_on_issues: bool = True

class SystemManager:
    """AI-driven system management and optimization."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = SystemConfig(
            resource_thresholds={
                "cpu_percent": 80.0,
                "memory_percent": 80.0,
                "disk_percent": 80.0
            }
        )
        self.monitor_queue = queue.Queue()
        self.monitor_thread = None
        self.optimization_thread = None
        self.initialize()
        
    def initialize(self):
        """Initialize the system manager."""
        # Start monitoring thread
        self._start_monitor_thread()
        
        # Start optimization thread if enabled
        if self.config.optimization_enabled:
            self._start_optimization_thread()
            
    def _start_monitor_thread(self):
        """Start system monitoring thread."""
        self.monitor_thread = threading.Thread(
            target=self._monitor_worker,
            daemon=True
        )
        self.monitor_thread.start()
        
    def _monitor_worker(self):
        """Background monitoring worker."""
        while True:
            try:
                # Get system metrics
                metrics = self._get_system_metrics()
                
                # Check resource usage
                issues = self._check_resource_usage(metrics)
                
                # Handle issues
                if issues:
                    self._handle_resource_issues(issues)
                    
                # Sleep for monitor interval
                time.sleep(self.config.monitor_interval)
                
            except Exception as e:
                logging.error(f"Monitor worker error: {e}")
                
    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics."""
        try:
            # Get CPU metrics
            cpu_metrics = {
                "percent": psutil.cpu_percent(interval=1),
                "count": psutil.cpu_count(),
                "freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None
            }
            
            # Get memory metrics
            memory = psutil.virtual_memory()
            memory_metrics = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
                "used": memory.used,
                "free": memory.free
            }
            
            # Get disk metrics
            disk = psutil.disk_usage('/')
            disk_metrics = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            }
            
            # Get network metrics
            net_io = psutil.net_io_counters()
            network_metrics = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
            
            # Get process metrics
            process_metrics = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    process_metrics.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            return {
                "timestamp": datetime.now().isoformat(),
                "cpu": cpu_metrics,
                "memory": memory_metrics,
                "disk": disk_metrics,
                "network": network_metrics,
                "processes": process_metrics
            }
            
        except Exception as e:
            logging.error(f"Error getting system metrics: {e}")
            return {}
            
    def _check_resource_usage(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Check resource usage against thresholds."""
        issues = []
        
        try:
            # Check CPU usage
            if metrics["cpu"]["percent"] > self.config.resource_thresholds["cpu_percent"]:
                issues.append({
                    "type": "cpu",
                    "metric": "percent",
                    "value": metrics["cpu"]["percent"],
                    "threshold": self.config.resource_thresholds["cpu_percent"]
                })
                
            # Check memory usage
            if metrics["memory"]["percent"] > self.config.resource_thresholds["memory_percent"]:
                issues.append({
                    "type": "memory",
                    "metric": "percent",
                    "value": metrics["memory"]["percent"],
                    "threshold": self.config.resource_thresholds["memory_percent"]
                })
                
            # Check disk usage
            if metrics["disk"]["percent"] > self.config.resource_thresholds["disk_percent"]:
                issues.append({
                    "type": "disk",
                    "metric": "percent",
                    "value": metrics["disk"]["percent"],
                    "threshold": self.config.resource_thresholds["disk_percent"]
                })
                
        except Exception as e:
            logging.error(f"Error checking resource usage: {e}")
            
        return issues
        
    def _handle_resource_issues(self, issues: List[Dict[str, Any]]):
        """Handle resource usage issues."""
        try:
            for issue in issues:
                # Log issue
                logging.warning(
                    f"Resource issue detected: {issue['type']} "
                    f"{issue['metric']} = {issue['value']}% "
                    f"(threshold: {issue['threshold']}%)"
                )
                
                # Add to optimization queue
                self.monitor_queue.put({
                    "type": "optimize",
                    "issue": issue
                })
                
                # Notify if enabled
                if self.config.notify_on_issues:
                    self._notify_resource_issue(issue)
                    
        except Exception as e:
            logging.error(f"Error handling resource issues: {e}")
            
    def _start_optimization_thread(self):
        """Start optimization thread."""
        self.optimization_thread = threading.Thread(
            target=self._optimization_worker,
            daemon=True
        )
        self.optimization_thread.start()
        
    def _optimization_worker(self):
        """Background optimization worker."""
        while True:
            try:
                # Get optimization task from queue
                task = self.monitor_queue.get()
                
                # Process optimization task
                if task["type"] == "optimize":
                    self._optimize_resource(task["issue"])
                    
                # Mark task as done
                self.monitor_queue.task_done()
                
            except Exception as e:
                logging.error(f"Optimization worker error: {e}")
                
    def _optimize_resource(self, issue: Dict[str, Any]):
        """Optimize resource usage."""
        try:
            if issue["type"] == "cpu":
                self._optimize_cpu()
            elif issue["type"] == "memory":
                self._optimize_memory()
            elif issue["type"] == "disk":
                self._optimize_disk()
                
        except Exception as e:
            logging.error(f"Error optimizing resource: {e}")
            
    def _optimize_cpu(self):
        """Optimize CPU usage."""
        try:
            # Get top CPU processes
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
            # Sort by CPU usage
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            
            # Handle high CPU processes
            for proc in processes[:5]:  # Top 5 processes
                if proc['cpu_percent'] > 50:  # 50% threshold
                    try:
                        # Get process
                        process = psutil.Process(proc['pid'])
                        
                        # Lower process priority
                        if platform.system() == "Windows":
                            process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
                        else:
                            process.nice(10)
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
        except Exception as e:
            logging.error(f"Error optimizing CPU: {e}")
            
    def _optimize_memory(self):
        """Optimize memory usage."""
        try:
            # Get memory usage
            memory = psutil.virtual_memory()
            
            if memory.percent > self.config.cleanup_threshold:
                # Clear system caches
                if platform.system() == "Windows":
                    subprocess.run(["cleanmgr", "/sagerun:1"], shell=True)
                else:
                    subprocess.run(["sync"], shell=True)
                    with open("/proc/sys/vm/drop_caches", "w") as f:
                        f.write("3")
                        
                # Clear temporary files
                temp_dirs = [
                    os.path.join(os.environ.get("TEMP", "/tmp")),
                    os.path.join(os.environ.get("TMP", "/tmp"))
                ]
                
                for temp_dir in temp_dirs:
                    if os.path.exists(temp_dir):
                        for item in os.listdir(temp_dir):
                            try:
                                item_path = os.path.join(temp_dir, item)
                                if os.path.isfile(item_path):
                                    os.remove(item_path)
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path)
                            except Exception:
                                pass
                                
        except Exception as e:
            logging.error(f"Error optimizing memory: {e}")
            
    def _optimize_disk(self):
        """Optimize disk usage."""
        try:
            # Get disk usage
            disk = psutil.disk_usage('/')
            
            if disk.percent > self.config.cleanup_threshold:
                # Clear old log files
                self._cleanup_logs()
                
                # Clear temporary files
                self._cleanup_temp_files()
                
                # Clear package caches
                self._cleanup_package_caches()
                
        except Exception as e:
            logging.error(f"Error optimizing disk: {e}")
            
    def _cleanup_logs(self):
        """Cleanup old log files."""
        try:
            # Get log directories
            log_dirs = [
                "/var/log",
                os.path.join(os.environ.get("APPDATA", ""), "logs"),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "logs")
            ]
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=self.config.log_retention_days)
            
            # Cleanup logs
            for log_dir in log_dirs:
                if os.path.exists(log_dir):
                    for item in os.listdir(log_dir):
                        try:
                            item_path = os.path.join(log_dir, item)
                            if os.path.isfile(item_path):
                                # Check file age
                                file_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                                if file_time < cutoff_date:
                                    os.remove(item_path)
                        except Exception:
                            pass
                            
        except Exception as e:
            logging.error(f"Error cleaning up logs: {e}")
            
    def _cleanup_temp_files(self):
        """Cleanup temporary files."""
        try:
            # Get temp directories
            temp_dirs = [
                os.path.join(os.environ.get("TEMP", "/tmp")),
                os.path.join(os.environ.get("TMP", "/tmp")),
                os.path.join(os.environ.get("LOCALAPPDATA", ""), "Temp")
            ]
            
            # Cleanup temp files
            for temp_dir in temp_dirs:
                if os.path.exists(temp_dir):
                    for item in os.listdir(temp_dir):
                        try:
                            item_path = os.path.join(temp_dir, item)
                            if os.path.isfile(item_path):
                                os.remove(item_path)
                            elif os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                        except Exception:
                            pass
                            
        except Exception as e:
            logging.error(f"Error cleaning up temp files: {e}")
            
    def _cleanup_package_caches(self):
        """Cleanup package caches."""
        try:
            if platform.system() == "Windows":
                # Cleanup Windows package cache
                subprocess.run(["cleanmgr", "/sagerun:1"], shell=True)
            else:
                # Cleanup package manager caches
                if os.path.exists("/var/cache/apt"):
                    subprocess.run(["apt-get", "clean"], shell=True)
                if os.path.exists("/var/cache/yum"):
                    subprocess.run(["yum", "clean", "all"], shell=True)
                    
        except Exception as e:
            logging.error(f"Error cleaning up package caches: {e}")
            
    def _notify_resource_issue(self, issue: Dict[str, Any]):
        """Notify about resource issue."""
        # Implement notification logic
        pass
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information."""
        try:
            # Get system metrics
            metrics = self._get_system_metrics()
            
            # Get system info
            system_info = {
                "platform": platform.system(),
                "platform_version": platform.version(),
                "architecture": platform.machine(),
                "processor": platform.processor(),
                "hostname": platform.node(),
                "python_version": platform.python_version()
            }
            
            return {
                "status": "success",
                "metrics": metrics,
                "system_info": system_info
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def optimize_system(self) -> Dict[str, Any]:
        """Optimize system performance."""
        try:
            # Optimize CPU
            self._optimize_cpu()
            
            # Optimize memory
            self._optimize_memory()
            
            # Optimize disk
            self._optimize_disk()
            
            return {
                "status": "success",
                "message": "System optimization completed"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def stop(self):
        """Stop system manager."""
        try:
            # Stop optimization thread
            if self.optimization_thread:
                self.monitor_queue.put(None)
                self.optimization_thread.join()
                
            # Stop monitor thread
            if self.monitor_thread:
                self.monitor_thread.join()
                
        except Exception as e:
            logging.error(f"Stop error: {e}") 