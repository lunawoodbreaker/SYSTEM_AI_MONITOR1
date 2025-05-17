import os
from pathlib import Path
from typing import Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class Settings:
    def __init__(self, config_path: str = "config.json"):
        self.config_path = config_path
        self.default_config = {
            "ollama": {
                "base_url": "http://localhost:11434",
                "models": {
                    "code": "codellama",
                    "text": "mistral",
                    "security": "mistral"
                }
            },
            "review": {
                "pause_on_error": True,
                "severity_levels": ["info", "warning", "error", "critical"],
                "max_file_size": 1024 * 1024,  # 1MB
                "excluded_directories": [".git", "node_modules", "venv", "__pycache__"],
                "excluded_files": [".gitignore", ".env", "*.pyc"]
            },
            "system": {
                "scan_interval": 300,  # 5 minutes
                "max_depth": 10,
                "file_types": {
                    "code": [".py", ".js", ".ts", ".java", ".cpp", ".c", ".h", ".cs"],
                    "text": [".txt", ".md", ".rst", ".doc", ".docx"],
                    "config": [".json", ".yaml", ".yml", ".xml", ".ini", ".conf"]
                }
            },
            "logging": {
                "level": "INFO",
                "file": "system_ai_manager.log",
                "max_size": 1024 * 1024 * 10,  # 10MB
                "backup_count": 5
            }
        }
        self.config = self.load_config()
        
    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                # Merge with defaults to ensure all settings exist
                return self._merge_configs(self.default_config, config)
            else:
                # Create default config file
                self.save_config(self.default_config)
                return self.default_config
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
            return self.default_config
            
    def save_config(self, config: Dict[str, Any]):
        """Save configuration to file."""
        try:
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
            
    def _merge_configs(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with defaults."""
        merged = default.copy()
        for key, value in user.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = self._merge_configs(merged[key], value)
            else:
                merged[key] = value
        return merged
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        try:
            value = self.config
            for k in key.split('.'):
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
            
    def set(self, key: str, value: Any):
        """Set a configuration value."""
        try:
            keys = key.split('.')
            config = self.config
            for k in keys[:-1]:
                config = config[k]
            config[keys[-1]] = value
            self.save_config(self.config)
        except Exception as e:
            logger.error(f"Error setting config value: {str(e)}")
            
    def update(self, updates: Dict[str, Any]):
        """Update multiple configuration values."""
        try:
            self.config = self._merge_configs(self.config, updates)
            self.save_config(self.config)
        except Exception as e:
            logger.error(f"Error updating config: {str(e)}")
            
    def reset(self):
        """Reset configuration to defaults."""
        self.config = self.default_config.copy()
        self.save_config(self.config) 