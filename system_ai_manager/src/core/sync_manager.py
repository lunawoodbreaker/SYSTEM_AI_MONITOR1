from dataclasses import dataclass
from typing import Dict, List, Any, Optional
import os
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime
import logging
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import threading
import time
import queue
import watchdog.observers
import watchdog.events

@dataclass
class SyncConfig:
    """Configuration for synchronization."""
    sync_dir: str
    backup_dir: str
    encryption_key: Optional[str] = None
    sync_interval: int = 300  # 5 minutes
    max_backups: int = 10
    compression_enabled: bool = True
    encryption_enabled: bool = True
    auto_sync: bool = True
    notify_on_sync: bool = True
    exclude_patterns: List[str] = None

class SyncManager:
    """Privacy-focused synchronization and backup manager."""
    
    def __init__(self, settings):
        self.settings = settings
        self.config = SyncConfig(
            sync_dir="sync",
            backup_dir="backups",
            exclude_patterns=["*.tmp", "*.log", "*.cache"]
        )
        self.fernet = None
        self.sync_queue = queue.Queue()
        self.sync_thread = None
        self.observer = None
        self.initialize()
        
    def initialize(self):
        """Initialize the sync manager."""
        # Create directories
        os.makedirs(self.config.sync_dir, exist_ok=True)
        os.makedirs(self.config.backup_dir, exist_ok=True)
        
        # Initialize encryption if enabled
        if self.config.encryption_enabled:
            self._initialize_encryption()
            
        # Start sync thread if auto sync is enabled
        if self.config.auto_sync:
            self._start_sync_thread()
            
        # Start file watcher
        self._start_file_watcher()
        
    def _initialize_encryption(self):
        """Initialize encryption system."""
        try:
            if self.config.encryption_key:
                # Use provided key
                key = self.config.encryption_key.encode()
            else:
                # Generate new key
                key = Fernet.generate_key()
                
            # Create Fernet instance
            self.fernet = Fernet(key)
            
        except Exception as e:
            logging.error(f"Failed to initialize encryption: {e}")
            self.fernet = None
            
    def _start_sync_thread(self):
        """Start background sync thread."""
        self.sync_thread = threading.Thread(
            target=self._sync_worker,
            daemon=True
        )
        self.sync_thread.start()
        
    def _sync_worker(self):
        """Background sync worker."""
        while True:
            try:
                # Get sync task from queue
                task = self.sync_queue.get()
                
                # Process sync task
                if task["type"] == "sync":
                    self._process_sync(task["paths"])
                elif task["type"] == "backup":
                    self._process_backup(task["paths"])
                    
                # Mark task as done
                self.sync_queue.task_done()
                
            except Exception as e:
                logging.error(f"Sync worker error: {e}")
                
            # Sleep for sync interval
            time.sleep(self.config.sync_interval)
            
    def _start_file_watcher(self):
        """Start file system watcher."""
        try:
            # Create observer
            self.observer = watchdog.observers.Observer()
            
            # Create event handler
            handler = SyncEventHandler(self)
            
            # Schedule watching
            self.observer.schedule(
                handler,
                self.config.sync_dir,
                recursive=True
            )
            
            # Start observer
            self.observer.start()
            
        except Exception as e:
            logging.error(f"Failed to start file watcher: {e}")
            
    def sync_files(self, paths: List[str]) -> Dict[str, Any]:
        """Sync files between locations."""
        try:
            # Add sync task to queue
            self.sync_queue.put({
                "type": "sync",
                "paths": paths
            })
            
            return {
                "status": "success",
                "message": "Sync task queued"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _process_sync(self, paths: List[str]):
        """Process sync task."""
        try:
            for path in paths:
                # Check if path exists
                if not os.path.exists(path):
                    continue
                    
                # Get file info
                file_info = self._get_file_info(path)
                
                # Check if file should be synced
                if not self._should_sync_file(path):
                    continue
                    
                # Sync file
                self._sync_file(path, file_info)
                
            # Notify if enabled
            if self.config.notify_on_sync:
                self._notify_sync_complete()
                
        except Exception as e:
            logging.error(f"Sync process error: {e}")
            
    def _get_file_info(self, path: str) -> Dict[str, Any]:
        """Get file information."""
        stat = os.stat(path)
        return {
            "path": path,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "hash": self._calculate_file_hash(path)
        }
        
    def _calculate_file_hash(self, path: str) -> str:
        """Calculate file hash."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
        
    def _should_sync_file(self, path: str) -> bool:
        """Check if file should be synced."""
        # Check exclude patterns
        for pattern in self.config.exclude_patterns:
            if Path(path).match(pattern):
                return False
                
        return True
        
    def _sync_file(self, path: str, file_info: Dict[str, Any]):
        """Sync single file."""
        try:
            # Get sync destination
            dest_path = self._get_sync_destination(path)
            
            # Check if file needs syncing
            if os.path.exists(dest_path):
                dest_info = self._get_file_info(dest_path)
                if dest_info["hash"] == file_info["hash"]:
                    return
                    
            # Create destination directory
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file
            if self.config.encryption_enabled and self.fernet:
                self._encrypt_and_copy(path, dest_path)
            else:
                shutil.copy2(path, dest_path)
                
        except Exception as e:
            logging.error(f"File sync error: {e}")
            
    def _get_sync_destination(self, path: str) -> str:
        """Get sync destination path."""
        # Convert to relative path
        rel_path = os.path.relpath(path, self.config.sync_dir)
        
        # Create destination path
        return os.path.join(self.config.sync_dir, rel_path)
        
    def _encrypt_and_copy(self, src_path: str, dest_path: str):
        """Encrypt and copy file."""
        try:
            # Read source file
            with open(src_path, "rb") as f:
                data = f.read()
                
            # Encrypt data
            encrypted_data = self.fernet.encrypt(data)
            
            # Write encrypted data
            with open(dest_path, "wb") as f:
                f.write(encrypted_data)
                
        except Exception as e:
            logging.error(f"Encryption error: {e}")
            
    def create_backup(self, paths: List[str]) -> Dict[str, Any]:
        """Create backup of files."""
        try:
            # Add backup task to queue
            self.sync_queue.put({
                "type": "backup",
                "paths": paths
            })
            
            return {
                "status": "success",
                "message": "Backup task queued"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _process_backup(self, paths: List[str]):
        """Process backup task."""
        try:
            # Create backup directory
            backup_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = os.path.join(self.config.backup_dir, backup_time)
            os.makedirs(backup_dir, exist_ok=True)
            
            # Backup files
            for path in paths:
                if os.path.exists(path):
                    self._backup_file(path, backup_dir)
                    
            # Cleanup old backups
            self._cleanup_old_backups()
            
            # Notify if enabled
            if self.config.notify_on_sync:
                self._notify_backup_complete(backup_dir)
                
        except Exception as e:
            logging.error(f"Backup process error: {e}")
            
    def _backup_file(self, path: str, backup_dir: str):
        """Backup single file."""
        try:
            # Get relative path
            rel_path = os.path.relpath(path, self.config.sync_dir)
            
            # Create destination path
            dest_path = os.path.join(backup_dir, rel_path)
            
            # Create destination directory
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Copy file
            if self.config.encryption_enabled and self.fernet:
                self._encrypt_and_copy(path, dest_path)
            else:
                shutil.copy2(path, dest_path)
                
        except Exception as e:
            logging.error(f"File backup error: {e}")
            
    def _cleanup_old_backups(self):
        """Cleanup old backups."""
        try:
            # Get backup directories
            backup_dirs = sorted([
                os.path.join(self.config.backup_dir, d)
                for d in os.listdir(self.config.backup_dir)
                if os.path.isdir(os.path.join(self.config.backup_dir, d))
            ])
            
            # Remove old backups
            while len(backup_dirs) > self.config.max_backups:
                old_dir = backup_dirs.pop(0)
                shutil.rmtree(old_dir)
                
        except Exception as e:
            logging.error(f"Backup cleanup error: {e}")
            
    def restore_backup(self, backup_dir: str, target_dir: str) -> Dict[str, Any]:
        """Restore files from backup."""
        try:
            # Check if backup exists
            if not os.path.exists(backup_dir):
                return {
                    "status": "error",
                    "error": "Backup not found"
                }
                
            # Create target directory
            os.makedirs(target_dir, exist_ok=True)
            
            # Restore files
            for root, _, files in os.walk(backup_dir):
                for file in files:
                    # Get source path
                    src_path = os.path.join(root, file)
                    
                    # Get relative path
                    rel_path = os.path.relpath(src_path, backup_dir)
                    
                    # Get destination path
                    dest_path = os.path.join(target_dir, rel_path)
                    
                    # Create destination directory
                    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                    
                    # Copy file
                    if self.config.encryption_enabled and self.fernet:
                        self._decrypt_and_copy(src_path, dest_path)
                    else:
                        shutil.copy2(src_path, dest_path)
                        
            return {
                "status": "success",
                "message": "Backup restored"
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
            
    def _decrypt_and_copy(self, src_path: str, dest_path: str):
        """Decrypt and copy file."""
        try:
            # Read encrypted file
            with open(src_path, "rb") as f:
                encrypted_data = f.read()
                
            # Decrypt data
            decrypted_data = self.fernet.decrypt(encrypted_data)
            
            # Write decrypted data
            with open(dest_path, "wb") as f:
                f.write(decrypted_data)
                
        except Exception as e:
            logging.error(f"Decryption error: {e}")
            
    def _notify_sync_complete(self):
        """Notify sync completion."""
        # Implement notification logic
        pass
        
    def _notify_backup_complete(self, backup_dir: str):
        """Notify backup completion."""
        # Implement notification logic
        pass
        
    def stop(self):
        """Stop sync manager."""
        try:
            # Stop file watcher
            if self.observer:
                self.observer.stop()
                self.observer.join()
                
            # Stop sync thread
            if self.sync_thread:
                self.sync_queue.put(None)
                self.sync_thread.join()
                
        except Exception as e:
            logging.error(f"Stop error: {e}")

class SyncEventHandler(watchdog.events.FileSystemEventHandler):
    """File system event handler for sync."""
    
    def __init__(self, sync_manager):
        self.sync_manager = sync_manager
        
    def on_created(self, event):
        if not event.is_directory:
            self.sync_manager.sync_files([event.src_path])
            
    def on_modified(self, event):
        if not event.is_directory:
            self.sync_manager.sync_files([event.src_path])
            
    def on_deleted(self, event):
        if not event.is_directory:
            # Handle file deletion
            pass
            
    def on_moved(self, event):
        if not event.is_directory:
            # Handle file move
            pass 