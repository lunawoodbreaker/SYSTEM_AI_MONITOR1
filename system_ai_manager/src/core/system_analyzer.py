import os
import platform
import psutil
import subprocess
from typing import Dict, List, Optional, Any
import logging
from pathlib import Path
import winreg
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SystemAnalyzer:
    def __init__(self):
        self.system_info = {}
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information."""
        try:
            self.system_info = {
                "platform": {
                    "system": platform.system(),
                    "release": platform.release(),
                    "version": platform.version(),
                    "machine": platform.machine(),
                    "processor": platform.processor()
                },
                "hardware": {
                    "cpu": {
                        "physical_cores": psutil.cpu_count(logical=False),
                        "total_cores": psutil.cpu_count(logical=True),
                        "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
                        "cpu_percent": psutil.cpu_percent(interval=1)
                    },
                    "memory": {
                        "total": psutil.virtual_memory().total,
                        "available": psutil.virtual_memory().available,
                        "percent": psutil.virtual_memory().percent
                    },
                    "disk": {
                        "partitions": [partition._asdict() for partition in psutil.disk_partitions()],
                        "usage": psutil.disk_usage('/')._asdict()
                    }
                },
                "software": self._get_installed_software(),
                "drivers": self._get_driver_info(),
                "network": self._get_network_info(),
                "processes": self._get_running_processes()
            }
            return self.system_info
        except Exception as e:
            logger.error(f"Error getting system info: {str(e)}")
            return {"error": str(e)}
            
    def _get_installed_software(self) -> List[Dict[str, str]]:
        """Get list of installed software."""
        software_list = []
        try:
            if platform.system() == "Windows":
                # Windows registry keys for installed software
                keys = [
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
                    r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
                ]
                
                for key_path in keys:
                    try:
                        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                            for i in range(winreg.QueryInfoKey(key)[0]):
                                try:
                                    subkey_name = winreg.EnumKey(key, i)
                                    with winreg.OpenKey(key, subkey_name) as subkey:
                                        try:
                                            name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                            version = winreg.QueryValueEx(subkey, "DisplayVersion")[0]
                                            software_list.append({
                                                "name": name,
                                                "version": version
                                            })
                                        except:
                                            continue
                                except:
                                    continue
                    except:
                        continue
                        
        except Exception as e:
            logger.error(f"Error getting installed software: {str(e)}")
            
        return software_list
        
    def _get_driver_info(self) -> List[Dict[str, str]]:
        """Get system driver information."""
        drivers = []
        try:
            if platform.system() == "Windows":
                # Windows driver information
                try:
                    output = subprocess.check_output(
                        "driverquery /v /fo csv",
                        shell=True,
                        stderr=subprocess.STDOUT
                    ).decode('utf-8')
                    
                    for line in output.split('\n')[1:]:  # Skip header
                        if line.strip():
                            parts = line.strip('"').split('","')
                            if len(parts) >= 4:
                                drivers.append({
                                    "name": parts[0],
                                    "display_name": parts[1],
                                    "type": parts[2],
                                    "state": parts[3]
                                })
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error getting driver info: {str(e)}")
            
        return drivers
        
    def _get_network_info(self) -> Dict[str, Any]:
        """Get network interface information."""
        try:
            return {
                "interfaces": [interface._asdict() for interface in psutil.net_if_addrs().items()],
                "connections": [conn._asdict() for conn in psutil.net_connections()],
                "io_counters": psutil.net_io_counters()._asdict()
            }
        except Exception as e:
            logger.error(f"Error getting network info: {str(e)}")
            return {}
            
    def _get_running_processes(self) -> List[Dict[str, Any]]:
        """Get information about running processes."""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username', 'memory_percent', 'cpu_percent']):
                try:
                    processes.append(proc.info)
                except:
                    continue
        except Exception as e:
            logger.error(f"Error getting running processes: {str(e)}")
            
        return processes
        
    def check_file_permissions(self, file_path: str) -> Dict[str, Any]:
        """Check file permissions and security."""
        try:
            stat = os.stat(file_path)
            return {
                "path": file_path,
                "permissions": {
                    "mode": stat.st_mode,
                    "uid": stat.st_uid,
                    "gid": stat.st_gid,
                    "size": stat.st_size,
                    "atime": stat.st_atime,
                    "mtime": stat.st_mtime,
                    "ctime": stat.st_ctime
                },
                "is_readable": os.access(file_path, os.R_OK),
                "is_writable": os.access(file_path, os.W_OK),
                "is_executable": os.access(file_path, os.X_OK)
            }
        except Exception as e:
            logger.error(f"Error checking file permissions: {str(e)}")
            return {"error": str(e)}
            
    def find_potentially_harmful_files(self, directory: str) -> List[Dict[str, Any]]:
        """Find potentially harmful files in a directory."""
        harmful_files = []
        try:
            for root, _, files in os.walk(directory):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Check for suspicious file extensions
                    if file.lower().endswith(('.exe', '.bat', '.cmd', '.vbs', '.js', '.ps1')):
                        harmful_files.append({
                            "path": file_path,
                            "type": "executable",
                            "permissions": self.check_file_permissions(file_path)
                        })
        except Exception as e:
            logger.error(f"Error finding harmful files: {str(e)}")
            
        return harmful_files 