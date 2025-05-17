import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import logging
from pathlib import Path
from typing import Callable, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None]):
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory:
            logger.info(f"File modified: {event.src_path}")
            self.callback(event.src_path)
            
    def on_created(self, event):
        if not event.is_directory:
            logger.info(f"File created: {event.src_path}")
            self.callback(event.src_path)
            
    def on_deleted(self, event):
        if not event.is_directory:
            logger.info(f"File deleted: {event.src_path}")
            self.callback(event.src_path)

class FileWatcher:
    def __init__(self, watch_path: str, callback: Callable[[str], None]):
        self.watch_path = Path(watch_path)
        self.callback = callback
        self.observer = Observer()
        self.handler = FileChangeHandler(callback)
        
    def start(self):
        """Start watching the directory for changes."""
        try:
            self.observer.schedule(self.handler, str(self.watch_path), recursive=True)
            self.observer.start()
            logger.info(f"Started watching directory: {self.watch_path}")
        except Exception as e:
            logger.error(f"Error starting file watcher: {str(e)}")
            
    def stop(self):
        """Stop watching the directory."""
        try:
            self.observer.stop()
            self.observer.join()
            logger.info("Stopped file watcher")
        except Exception as e:
            logger.error(f"Error stopping file watcher: {str(e)}")
            
    def is_running(self) -> bool:
        """Check if the file watcher is running."""
        return self.observer.is_alive() 