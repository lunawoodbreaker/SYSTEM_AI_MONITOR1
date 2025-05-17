from fastapi import FastAPI, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import uvicorn
import os
from pathlib import Path
import asyncio

from ..core.code_analyzer import CodeAnalyzer
from ..core.file_watcher import FileWatcher
from ..ai.ai_analyzer import AIAnalyzer
from ..ai.code_reviewer import CodeReviewer, CodeIssue, ReviewSeverity
from ..core.system_analyzer import SystemAnalyzer
from ..config.settings import Settings

app = FastAPI(title="System AI Manager")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
settings = Settings()
analyzer = CodeAnalyzer(os.getcwd())
system_analyzer = SystemAnalyzer()
ai_analyzer = AIAnalyzer(settings.get("ollama.base_url"))
code_reviewer = CodeReviewer(settings.get("ollama.base_url"))
watcher = None

class FileAnalysis(BaseModel):
    path: str
    language: str
    complexity: int
    size: int
    last_modified: float
    ai_analysis: Optional[Dict[str, Any]] = None
    security_analysis: Optional[Dict[str, Any]] = None

class SystemAnalysis(BaseModel):
    platform: Dict[str, Any]
    hardware: Dict[str, Any]
    software: List[Dict[str, str]]
    drivers: List[Dict[str, str]]
    network: Dict[str, Any]
    processes: List[Dict[str, Any]]
    ai_analysis: Optional[Dict[str, Any]] = None

class CodeReview(BaseModel):
    issues: List[Dict[str, Any]]
    suggestions: Dict[str, Any]
    metadata: Dict[str, Any]

@app.get("/")
async def root():
    return {"message": "System AI Manager API"}

@app.get("/analyze/{file_path:path}")
async def analyze_file(file_path: str) -> FileAnalysis:
    try:
        result = analyzer.analyze_file(file_path)
        if not result:
            raise HTTPException(status_code=404, detail="File not found or could not be analyzed")
            
        # Get AI analysis
        ai_result = await ai_analyzer.analyze_code_structure(result['content'], file_path)
        result['ai_analysis'] = ai_result
        
        # Get security analysis
        security_result = await ai_analyzer.analyze_security(file_path, result['content'])
        result['security_analysis'] = security_result
        
        return FileAnalysis(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/review/{file_path:path}")
async def review_file(
    file_path: str,
    pause_on_error: bool = Query(True, description="Whether to pause on critical issues")
) -> CodeReview:
    try:
        code_reviewer.set_pause_on_error(pause_on_error)
        issues, suggestions = await code_reviewer.review_code(file_path)
        
        return CodeReview(
            issues=[{
                "line_number": issue.line_number,
                "severity": issue.severity.value,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "code_snippet": issue.code_snippet
            } for issue in issues],
            suggestions=suggestions,
            metadata={
                "file_path": file_path,
                "total_issues": len(issues),
                "critical_issues": sum(1 for i in issues if i.severity in [ReviewSeverity.ERROR, ReviewSeverity.CRITICAL])
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/review/text/{file_path:path}")
async def review_text(file_path: str) -> Dict[str, Any]:
    try:
        return await code_reviewer.review_text(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/suggestions/{file_path:path}")
async def get_code_suggestions(file_path: str) -> Dict[str, Any]:
    try:
        return await code_reviewer.suggest_code_improvements(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analyze-directory/{directory:path}")
async def analyze_directory(directory: str) -> Dict[str, FileAnalysis]:
    try:
        results = analyzer.analyze_directory(directory)
        return {k: FileAnalysis(**v) for k, v in results.items()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/analysis")
async def analyze_system() -> SystemAnalysis:
    try:
        system_info = system_analyzer.get_system_info()
        ai_analysis = await ai_analyzer.analyze_system_health(system_info)
        system_info['ai_analysis'] = ai_analysis
        return SystemAnalysis(**system_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/harmful-files/{directory:path}")
async def find_harmful_files(directory: str) -> List[Dict[str, Any]]:
    try:
        return system_analyzer.find_potentially_harmful_files(directory)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/unused-files/{directory:path}")
async def find_unused_files(directory: str) -> Dict[str, Any]:
    try:
        all_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                all_files.append(os.path.join(root, file))
                
        return await ai_analyzer.find_unused_files(directory, all_files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system/build-analysis/{directory:path}")
async def analyze_build_system(directory: str) -> Dict[str, Any]:
    try:
        build_files = []
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower() in ('package.json', 'requirements.txt', 'build.gradle', 'pom.xml', 'cmakelists.txt'):
                    build_files.append(os.path.join(root, file))
                    
        return await ai_analyzer.analyze_build_system(build_files)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/watch")
async def start_watching(directory: str):
    global watcher
    try:
        if watcher and watcher.is_running():
            watcher.stop()
        
        def on_file_change(file_path: str):
            asyncio.create_task(analyze_file(file_path))
            
        watcher = FileWatcher(directory, on_file_change)
        watcher.start()
        return {"message": f"Started watching directory: {directory}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/stop-watching")
async def stop_watching():
    global watcher
    try:
        if watcher:
            watcher.stop()
            return {"message": "Stopped watching directory"}
        return {"message": "No active watcher"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config")
async def get_config() -> Dict[str, Any]:
    return settings.config

@app.put("/config")
async def update_config(updates: Dict[str, Any]):
    settings.update(updates)
    return {"message": "Configuration updated"}

def start():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    start() 