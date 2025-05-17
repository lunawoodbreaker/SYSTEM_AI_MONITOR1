# file_watcher.py
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from enhanced_document_scanner import EnhancedDocumentScanner

class DocumentUpdateHandler(FileSystemEventHandler):
    def __init__(self, scanner, watched_extensions):
        self.scanner = scanner
        self.watched_extensions = watched_extensions
        self.recent_events = {}  # To prevent duplicate processing
        self.cooldown = 5  # seconds
        
    def on_created(self, event):
        if event.is_directory:
            return
        
        # Check if it's a file we're interested in
        file_ext = os.path.splitext(event.src_path)[1].lower()
        if file_ext not in self.watched_extensions:
            return
        
        # Check if we've seen this event recently
        current_time = time.time()
        if event.src_path in self.recent_events:
            if current_time - self.recent_events[event.src_path] < self.cooldown:
                return
        
        # Process the new file
        print(f"New file detected: {event.src_path}")
        self.scanner.scan_directory(os.path.dirname(event.src_path), [file_ext])
        
        # Update the recent events
        self.recent_events[event.src_path] = current_time
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        # Check if it's a file we're interested in
        file_ext = os.path.splitext(event.src_path)[1].lower()
        if file_ext not in self.watched_extensions:
            return
        
        # Check if we've seen this event recently
        current_time = time.time()
        if event.src_path in self.recent_events:
            if current_time - self.recent_events[event.src_path] < self.cooldown:
                return
        
        # Process the modified file
        print(f"File modified: {event.src_path}")
        self.scanner.scan_directory(os.path.dirname(event.src_path), [file_ext])
        
        # Update the recent events
        self.recent_events[event.src_path] = current_time

def start_watcher(directories, extensions):
    """Start watching directories for document changes"""
    if not directories:
        print("No directories specified for watching.")
        return None
    
    # Initialize scanner
    scanner = EnhancedDocumentScanner()
    
    # Initialize observer
    observer = Observer()
    event_handler = DocumentUpdateHandler(scanner, extensions)
    
    # Schedule watching for each directory
    for directory in directories:
        if os.path.isdir(directory):
            observer.schedule(event_handler, directory, recursive=True)
            print(f"Watching directory: {directory}")
        else:
            print(f"Warning: {directory} is not a valid directory")
    
    # Start the observer
    observer.start()
    print(f"File system watcher started. Monitoring for changes in {len(directories)} directories.")
    print(f"Watching for file extensions: {', '.join(extensions)}")
    
    return observer

if __name__ == "__main__":
    print("Document File System Watcher")
    print("===========================")
    
    # Get directories to watch
    dirs_input = input("Enter directories to watch (comma-separated): ")
    directories = [d.strip() for d in dirs_input.split(",") if d.strip()]
    
    # Get file extensions to watch
    exts_input = input("Enter file extensions to watch (comma-separated, e.g. .txt,.pdf): ")
    extensions = [e.strip() if e.strip().startswith('.') else f".{e.strip()}" 
                for e in exts_input.split(",") if e.strip()]
    
    # Start watching
    observer = start_watcher(directories, extensions)
    
    if observer:
        try:
            print("Press Ctrl+C to stop watching")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
