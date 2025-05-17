import os
import sys
import asyncio
from pathlib import Path
import click
from typing import Optional, List, Dict, Any
import json
from datetime import datetime
import colorama
from colorama import Fore, Style
import pyperclip
import webbrowser
import requests
import typer

from .ai.code_reviewer import CodeReviewer
from .core.code_analyzer import CodeAnalyzer
from .core.system_analyzer import SystemAnalyzer
from .config.settings import Settings
from .core.dependency_analyzer import DependencyAnalyzer
from .core.performance_profiler import PerformanceProfiler
from .core.test_analyzer import TestAnalyzer
from .core.file_organizer import FileOrganizer

# Initialize colorama
colorama.init()

def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}=== {text} ==={Style.RESET_ALL}")

def print_success(text: str):
    """Print a success message."""
    print(f"{Fore.GREEN}✓ {text}{Style.RESET_ALL}")

def print_error(text: str):
    """Print an error message."""
    print(f"{Fore.RED}✗ {text}{Style.RESET_ALL}")

def print_warning(text: str):
    """Print a warning message."""
    print(f"{Fore.YELLOW}⚠ {text}{Style.RESET_ALL}")

def get_file_path() -> Optional[str]:
    """Get file path from user input with drag-and-drop support."""
    while True:
        print("\nDrag and drop a file here or enter the path (or 'q' to quit):")
        path = input().strip().strip('"')  # Remove quotes from drag-and-drop
        if path.lower() == 'q':
            return None
        if os.path.exists(path):
            return path
        print_error(f"File '{path}' does not exist. Please try again.")

def get_directory_path() -> Optional[str]:
    """Get directory path from user input with drag-and-drop support."""
    while True:
        print("\nDrag and drop a folder here or enter the path (or 'q' to quit):")
        path = input().strip().strip('"')  # Remove quotes from drag-and-drop
        if path.lower() == 'q':
            return None
        if os.path.exists(path) and os.path.isdir(path):
            return path
        print_error(f"Directory '{path}' does not exist. Please try again.")

def save_report(data: Dict[str, Any], file_type: str):
    """Save analysis report to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_report_{file_type}_{timestamp}.json"
    
    try:
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print_success(f"Report saved to {filename}")
        return filename
    except Exception as e:
        print_error(f"Failed to save report: {str(e)}")
        return None

async def ask_ollama(issue: CodeIssue, file_path: str, content: str) -> str:
    """Get additional insights from Ollama about an issue."""
    try:
        prompt = f"""I found this issue in my code:

File: {file_path}
Line: {issue.line_number}
Severity: {issue.severity.value}
Message: {issue.message}
Suggestion: {issue.suggestion}
Code snippet: {issue.code_snippet}

Context from the file:
{content}

Please provide:
1. A detailed explanation of why this is an issue
2. Best practices for handling this situation
3. Examples of correct implementation
4. Any potential edge cases to consider

Format the response in a clear, structured way."""

        response = requests.post(
            f"{settings.get('ollama.base_url')}/api/generate",
            json={
                "model": settings.get("ollama.models.code"),
                "prompt": prompt,
                "stream": False
            }
        )
        
        if response.status_code == 200:
            return response.json().get("response", "No response from AI model")
        else:
            return f"Error getting AI response: {response.status_code}"
            
    except Exception as e:
        return f"Error consulting AI: {str(e)}"

async def chat_with_ollama(issue: CodeIssue, file_path: str, content: str):
    """Start an interactive chat session with Ollama about the issue."""
    print("\n=== Starting Chat Session ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    # Initial context for the AI
    context = f"""I'm reviewing this code issue:

File: {file_path}
Line: {issue.line_number}
Severity: {issue.severity.value}
Message: {issue.message}
Suggestion: {issue.suggestion}
Code snippet: {issue.code_snippet}

Context from the file:
{content}

Please help me understand and resolve this issue. I'll ask questions and you'll provide guidance."""

    # Store chat history
    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display the current issue details")
            print("- fix: Get a detailed fix suggestion")
            print("- explain: Get a detailed explanation of the issue")
            print("- examples: Get example implementations")
            continue
        elif user_input.lower() == 'show':
            print(f"\nCurrent Issue:")
            print(f"File: {file_path}")
            print(f"Line: {issue.line_number}")
            print(f"Severity: {issue.severity.value}")
            print(f"Message: {issue.message}")
            if issue.suggestion:
                print(f"Suggestion: {issue.suggestion}")
            if issue.code_snippet:
                print(f"Code: {issue.code_snippet}")
            continue
        elif user_input.lower() == 'fix':
            user_input = "Please provide a detailed fix for this issue, including the complete code changes needed."
        elif user_input.lower() == 'explain':
            user_input = "Please explain why this is an issue and what problems it could cause."
        elif user_input.lower() == 'examples':
            user_input = "Please provide some example implementations that show how to handle this situation correctly."
        
        # Add user message to history
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            # Prepare the full conversation for the AI
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.code"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chat_session_{os.path.basename(file_path)}_{timestamp}.txt"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write("=== Chat Session ===\n\n")
                f.write(f"File: {file_path}\n")
                f.write(f"Line: {issue.line_number}\n")
                f.write(f"Issue: {issue.message}\n\n")
                f.write("=== Conversation ===\n\n")
                
                for msg in chat_history[1:]:  # Skip system message
                    f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")
                    
            print_success(f"Chat session saved to {filename}")
        except Exception as e:
            print_error(f"Failed to save chat session: {str(e)}")

async def handle_issue(issue: CodeIssue, file_path: str) -> bool:
    """Handle a single code issue interactively."""
    severity_color = {
        "INFO": Fore.BLUE,
        "WARNING": Fore.YELLOW,
        "ERROR": Fore.RED,
        "CRITICAL": Fore.RED + Style.BRIGHT
    }.get(issue.severity.value, Fore.WHITE)
    
    print(f"\n{severity_color}Issue Found:{Style.RESET_ALL}")
    print(f"Line {issue.line_number}: {issue.severity.value.upper()}")
    print(f"Message: {issue.message}")
    if issue.suggestion:
        print(f"Suggestion: {issue.suggestion}")
    if issue.code_snippet:
        print(f"Code: {issue.code_snippet}")
    
    # Read file content for context
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        content = ""
        print_warning(f"Could not read file content: {str(e)}")
    
    if issue.severity in [ReviewSeverity.ERROR, ReviewSeverity.CRITICAL]:
        print(f"\n{Fore.YELLOW}This is a {issue.severity.value} issue that requires attention.{Style.RESET_ALL}")
        
        while True:
            print("\nOptions:")
            print("1. View the file in your default editor")
            print("2. Copy the issue details to clipboard")
            print("3. Apply the suggested fix (if available)")
            print("4. Skip this issue")
            print("5. Ask Ollama for detailed explanation")
            print("6. Start interactive chat with Ollama")
            print("7. Exit the review")
            
            choice = input("\nWhat would you like to do? (1-7): ").strip()
            
            if choice == "1":
                try:
                    os.startfile(file_path) if os.name == 'nt' else os.system(f"xdg-open {file_path}")
                    print_success("File opened in your default editor")
                except Exception as e:
                    print_error(f"Failed to open file: {str(e)}")
                    
            elif choice == "2":
                issue_text = f"File: {file_path}\nLine: {issue.line_number}\nSeverity: {issue.severity.value}\nMessage: {issue.message}\nSuggestion: {issue.suggestion}"
                pyperclip.copy(issue_text)
                print_success("Issue details copied to clipboard")
                
            elif choice == "3":
                if issue.suggestion:
                    if click.confirm("Would you like to apply the suggested fix?"):
                        try:
                            with open(file_path, 'r') as f:
                                lines = f.readlines()
                            
                            if issue.line_number <= len(lines):
                                lines[issue.line_number - 1] = issue.suggestion + "\n"
                                
                                with open(file_path, 'w') as f:
                                    f.writelines(lines)
                                    
                                print_success("Fix applied successfully")
                                return True
                        except Exception as e:
                            print_error(f"Failed to apply fix: {str(e)}")
                else:
                    print_warning("No fix suggestion available for this issue")
                    
            elif choice == "4":
                print_warning("Skipping this issue")
                return True
                
            elif choice == "5":
                print("\nConsulting Ollama for detailed explanation...")
                explanation = await ask_ollama(issue, file_path, content)
                
                print("\n=== AI Explanation ===")
                print(explanation)
                
                if click.confirm("\nWould you like to copy this explanation to clipboard?"):
                    pyperclip.copy(explanation)
                    print_success("Explanation copied to clipboard")
                    
            elif choice == "6":
                await chat_with_ollama(issue, file_path, content)
                
            elif choice == "7":
                if click.confirm("Are you sure you want to exit the review?"):
                    return False
                    
            else:
                print_error("Invalid choice. Please try again.")
    
    return True

async def review_code(file_path: str, save_report: bool = False):
    """Review a code file with interactive issue handling."""
    reviewer = CodeReviewer()
    print(f"\nAnalyzing {file_path}...")
    
    issues, suggestions = await reviewer.review_code(file_path)
    
    print_header("Code Review Results")
    
    report_data = {
        "file_path": file_path,
        "timestamp": datetime.now().isoformat(),
        "issues": [],
        "suggestions": suggestions
    }
    
    if issues:
        print(f"\nFound {len(issues)} issues:")
        
        # Sort issues by severity
        severity_order = {
            ReviewSeverity.CRITICAL: 0,
            ReviewSeverity.ERROR: 1,
            ReviewSeverity.WARNING: 2,
            ReviewSeverity.INFO: 3
        }
        sorted_issues = sorted(issues, key=lambda x: severity_order[x.severity])
        
        for issue in sorted_issues:
            if not await handle_issue(issue, file_path):
                print_warning("\nReview stopped by user.")
                break
                
            report_data["issues"].append({
                "line_number": issue.line_number,
                "severity": issue.severity.value,
                "message": issue.message,
                "suggestion": issue.suggestion,
                "code_snippet": issue.code_snippet
            })
    else:
        print_success("No issues found!")
        
    if suggestions:
        print("\nImprovement Suggestions:")
        print(suggestions)
    
    if click.confirm("\nWould you like to start a chat about code quality?"):
        await chat_about_code_quality(file_path, report_data)
        
    if save_report:
        save_report(report_data, "code_review")

async def review_text(file_path: str, save_report: bool = False):
    """Review a text file."""
    reviewer = CodeReviewer()
    print(f"\nAnalyzing {file_path}...")
    
    result = await reviewer.review_text(file_path)
    
    print_header("Text Review Results")
    print(result)
    
    if save_report:
        save_report({
            "file_path": file_path,
            "timestamp": datetime.now().isoformat(),
            "analysis": result
        }, "text_review")

async def chat_about_system_analysis(system_info: Dict[str, Any]):
    """Start an interactive chat session about system analysis."""
    print("\n=== Starting System Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing my system with the following information:

Platform Information:
{json.dumps(system_info['platform'], indent=2)}

Hardware Information:
{json.dumps(system_info['hardware'], indent=2)}

Network Information:
{json.dumps(system_info['network'], indent=2)}

Please help me understand my system's health and provide recommendations."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display the current system information")
            print("- performance: Get performance analysis")
            print("- recommendations: Get system improvement recommendations")
            print("- security: Get security recommendations")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent System Information:")
            print(json.dumps(system_info, indent=2))
            continue
        elif user_input.lower() == 'performance':
            user_input = "Please analyze the system's performance and identify potential bottlenecks."
        elif user_input.lower() == 'recommendations':
            user_input = "What are your recommendations for improving system performance and stability?"
        elif user_input.lower() == 'security':
            user_input = "What security concerns do you see and how can they be addressed?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.text"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "system_analysis")

async def chat_about_directory_analysis(directory: str, analysis_results: Dict[str, Any]):
    """Start an interactive chat session about directory analysis."""
    print("\n=== Starting Directory Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing the directory: {directory}

Analysis Results:
{json.dumps(analysis_results, indent=2)}

Please help me understand the codebase structure and provide recommendations."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display the current analysis results")
            print("- structure: Get codebase structure analysis")
            print("- recommendations: Get improvement recommendations")
            print("- patterns: Identify code patterns and anti-patterns")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Analysis Results:")
            print(json.dumps(analysis_results, indent=2))
            continue
        elif user_input.lower() == 'structure':
            user_input = "Please analyze the codebase structure and identify any architectural issues."
        elif user_input.lower() == 'recommendations':
            user_input = "What are your recommendations for improving the codebase organization?"
        elif user_input.lower() == 'patterns':
            user_input = "What patterns and anti-patterns do you see in this codebase?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.code"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "directory_analysis")

def save_chat_session(chat_history: List[Dict[str, str]], session_type: str):
    """Save a chat session to a file."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"chat_session_{session_type}_{timestamp}.txt"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(f"=== Chat Session ({session_type}) ===\n\n")
            f.write("=== Conversation ===\n\n")
            
            for msg in chat_history[1:]:  # Skip system message
                f.write(f"{msg['role'].upper()}: {msg['content']}\n\n")
                
        print_success(f"Chat session saved to {filename}")
    except Exception as e:
        print_error(f"Failed to save chat session: {str(e)}")

async def analyze_system(save_report: bool = False):
    """Analyze system health."""
    system = SystemAnalyzer()
    print("\nAnalyzing system...")
    
    info = system.get_system_info()
    
    print_header("System Analysis Results")
    
    print("\nPlatform Information:")
    for key, value in info['platform'].items():
        print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {value}")
        
    print("\nHardware Information:")
    for key, value in info['hardware'].items():
        print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {value}")
        
    print("\nNetwork Information:")
    for key, value in info['network'].items():
        print(f"{Fore.CYAN}{key}{Style.RESET_ALL}: {value}")
    
    if click.confirm("\nWould you like to start a chat about the system analysis?"):
        await chat_about_system_analysis(info)
        
    if save_report:
        save_report({
            "timestamp": datetime.now().isoformat(),
            "system_info": info
        }, "system_analysis")

async def chat_about_security_analysis(directory: str, security_issues: List[Dict[str, Any]]):
    """Start an interactive chat session about security analysis."""
    print("\n=== Starting Security Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing security concerns in: {directory}

Security Issues Found:
{json.dumps(security_issues, indent=2)}

Please help me understand and address these security concerns."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current security issues")
            print("- vulnerabilities: Get detailed vulnerability analysis")
            print("- fixes: Get security fix recommendations")
            print("- best-practices: Get security best practices")
            print("- compliance: Check compliance with security standards")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Security Issues:")
            print(json.dumps(security_issues, indent=2))
            continue
        elif user_input.lower() == 'vulnerabilities':
            user_input = "Please analyze these vulnerabilities and explain their potential impact."
        elif user_input.lower() == 'fixes':
            user_input = "What specific fixes would you recommend for these security issues?"
        elif user_input.lower() == 'best-practices':
            user_input = "What security best practices should be implemented to prevent these issues?"
        elif user_input.lower() == 'compliance':
            user_input = "How do these issues affect compliance with common security standards?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.text"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "security_analysis")

async def chat_about_code_quality(file_path: str, analysis_results: Dict[str, Any]):
    """Start an interactive chat session about code quality analysis."""
    print("\n=== Starting Code Quality Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing code quality in: {file_path}

Analysis Results:
{json.dumps(analysis_results, indent=2)}

Please help me understand and improve the code quality."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current analysis results")
            print("- complexity: Analyze code complexity")
            print("- maintainability: Get maintainability recommendations")
            print("- optimization: Get code optimization suggestions")
            print("- testing: Get testing recommendations")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Analysis Results:")
            print(json.dumps(analysis_results, indent=2))
            continue
        elif user_input.lower() == 'complexity':
            user_input = "Please analyze the code complexity and suggest improvements."
        elif user_input.lower() == 'maintainability':
            user_input = "What recommendations do you have for improving code maintainability?"
        elif user_input.lower() == 'optimization':
            user_input = "How can this code be optimized for better performance?"
        elif user_input.lower() == 'testing':
            user_input = "What testing strategies would you recommend for this code?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.code"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "code_quality")

async def find_harmful_files(directory: str, save_report: bool = False):
    """Find potentially harmful files."""
    system = SystemAnalyzer()
    print(f"\nScanning {directory} for harmful files...")
    
    files = system.find_potentially_harmful_files(directory)
    
    print_header("Potentially Harmful Files")
    
    report_data = {
        "directory": directory,
        "timestamp": datetime.now().isoformat(),
        "files": []
    }
    
    if files:
        for file in files:
            severity_color = {
                "low": Fore.YELLOW,
                "medium": Fore.RED,
                "high": Fore.RED + Style.BRIGHT
            }.get(file['severity'].lower(), Fore.WHITE)
            
            print(f"\n{severity_color}File: {file['path']}{Style.RESET_ALL}")
            print(f"Reason: {file['reason']}")
            print(f"Severity: {file['severity']}")
            
            report_data["files"].append(file)
    else:
        print_success("No potentially harmful files found!")
    
    if click.confirm("\nWould you like to start a chat about the security analysis?"):
        await chat_about_security_analysis(directory, report_data["files"])
        
    if save_report:
        save_report(report_data, "harmful_files")

async def analyze_directory(directory: str, save_report: bool = False):
    """Analyze an entire directory."""
    analyzer = CodeAnalyzer()
    print(f"\nAnalyzing directory {directory}...")
    
    results = analyzer.analyze_directory(directory)
    
    print_header("Directory Analysis Results")
    
    report_data = {
        "directory": directory,
        "timestamp": datetime.now().isoformat(),
        "files": []
    }
    
    for file_path, analysis in results.items():
        print(f"\n{Fore.CYAN}File: {file_path}{Style.RESET_ALL}")
        print(f"Language: {analysis['language']}")
        print(f"Complexity: {analysis['complexity']}")
        print(f"Size: {analysis['size']} bytes")
        
        report_data["files"].append({
            "path": file_path,
            "analysis": analysis
        })
    
    if click.confirm("\nWould you like to start a chat about the directory analysis?"):
        await chat_about_directory_analysis(directory, report_data)
        
    if save_report:
        save_report(report_data, "directory_analysis")

async def analyze_dependencies(directory: str, save_report: bool = False):
    """Analyze project dependencies."""
    analyzer = DependencyAnalyzer()
    print(f"\nAnalyzing dependencies in {directory}...")
    
    results = analyzer.analyze_dependencies(directory)
    
    print_header("Dependency Analysis Results")
    
    if "error" in results:
        print_error(results["error"])
        return
    
    print(f"\nPackage Manager: {results['package_manager']}")
    print("\nDependencies:")
    for dep in results["dependencies"]:
        status_color = Fore.GREEN if not dep["is_outdated"] else Fore.YELLOW
        print(f"\n{Fore.CYAN}{dep['name']}{Style.RESET_ALL}")
        print(f"Version: {dep['version']}")
        if dep["latest_version"]:
            print(f"Latest: {status_color}{dep['latest_version']}{Style.RESET_ALL}")
        if dep["vulnerabilities"]:
            print(f"{Fore.RED}Vulnerabilities found:{Style.RESET_ALL}")
            for vuln in dep["vulnerabilities"]:
                print(f"- {vuln.get('description', 'Unknown vulnerability')}")
        if dep["license"]:
            print(f"License: {dep['license']}")
    
    if click.confirm("\nWould you like to start a chat about the dependency analysis?"):
        await chat_about_dependencies(directory, results)
    
    if save_report:
        save_report(results, "dependency_analysis")

async def analyze_performance(file_path: str, save_report: bool = False):
    """Analyze code performance."""
    profiler = PerformanceProfiler()
    print(f"\nAnalyzing performance of {file_path}...")
    
    results = profiler.profile_file(file_path)
    
    print_header("Performance Analysis Results")
    
    if "error" in results:
        print_error(results["error"])
        return
    
    print(f"\nExecution Time: {results['execution_time']:.2f} seconds")
    print(f"Memory Usage: {results['memory_usage'] / 1024 / 1024:.2f} MB")
    print(f"CPU Usage: {results['cpu_usage']}%")
    
    if results["hot_spots"]:
        print("\nHot Spots:")
        for spot in results["hot_spots"]:
            print(f"\nFunction: {spot['function']}")
            print(f"Total Time: {spot['total_time']:.2f} seconds")
            print(f"Calls: {spot['calls']}")
            print(f"Time per Call: {spot['time_per_call']:.2f} seconds")
    
    if results["memory_leaks"]:
        print(f"\n{Fore.RED}Potential Memory Leaks:{Style.RESET_ALL}")
        for leak in results["memory_leaks"]:
            print(f"\nType: {leak['type']}")
            if leak["type"] == "memory_growth":
                print(f"Growth: {leak['growth'] / 1024 / 1024:.2f} MB")
    
    if click.confirm("\nWould you like to start a chat about the performance analysis?"):
        await chat_about_performance(file_path, results)
    
    if save_report:
        save_report(results, "performance_analysis")

async def analyze_tests(directory: str, save_report: bool = False):
    """Analyze test coverage and quality."""
    analyzer = TestAnalyzer()
    print(f"\nAnalyzing tests in {directory}...")
    
    results = analyzer.analyze_tests(directory)
    
    print_header("Test Analysis Results")
    
    if "error" in results:
        print_error(results["error"])
        return
    
    metrics = results["test_metrics"]
    print(f"\nCoverage: {metrics['coverage_percentage']}%")
    print(f"Total Tests: {metrics['total_tests']}")
    print(f"Passed: {metrics['passed_tests']}")
    print(f"Failed: {metrics['failed_tests']}")
    print(f"Skipped: {metrics['skipped_tests']}")
    print(f"Duration: {metrics['test_duration']:.2f} seconds")
    
    print("\nTest Categories:")
    for category, count in metrics["test_categories"].items():
        print(f"- {category}: {count}")
    
    print("\nTest Quality Metrics:")
    quality = results["test_quality"]
    print(f"Test Size: {quality['test_size']} lines")
    print(f"Assertion Density: {quality['assertion_density']:.2f}")
    print(f"Test Complexity: {quality['test_complexity']:.2f}")
    
    if click.confirm("\nWould you like to start a chat about the test analysis?"):
        await chat_about_tests(directory, results)
    
    if save_report:
        save_report(results, "test_analysis")

async def chat_about_dependencies(directory: str, analysis_results: Dict[str, Any]):
    """Start an interactive chat session about dependency analysis."""
    print("\n=== Starting Dependency Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing dependencies in: {directory}

Analysis Results:
{json.dumps(analysis_results, indent=2)}

Please help me understand and improve the dependency management."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current analysis results")
            print("- outdated: Get outdated package analysis")
            print("- security: Get security recommendations")
            print("- cleanup: Get dependency cleanup suggestions")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Analysis Results:")
            print(json.dumps(analysis_results, indent=2))
            continue
        elif user_input.lower() == 'outdated':
            user_input = "Please analyze the outdated packages and suggest update strategies."
        elif user_input.lower() == 'security':
            user_input = "What security concerns do you see in the dependencies and how can they be addressed?"
        elif user_input.lower() == 'cleanup':
            user_input = "What recommendations do you have for cleaning up and optimizing the dependencies?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.text"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "dependency_analysis")

async def chat_about_performance(file_path: str, analysis_results: Dict[str, Any]):
    """Start an interactive chat session about performance analysis."""
    print("\n=== Starting Performance Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing performance of: {file_path}

Analysis Results:
{json.dumps(analysis_results, indent=2)}

Please help me understand and improve the code performance."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current analysis results")
            print("- bottlenecks: Get bottleneck analysis")
            print("- optimization: Get optimization suggestions")
            print("- memory: Get memory usage analysis")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Analysis Results:")
            print(json.dumps(analysis_results, indent=2))
            continue
        elif user_input.lower() == 'bottlenecks':
            user_input = "Please analyze the performance bottlenecks and suggest improvements."
        elif user_input.lower() == 'optimization':
            user_input = "What specific optimizations would you recommend for this code?"
        elif user_input.lower() == 'memory':
            user_input = "Please analyze the memory usage patterns and suggest improvements."
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.code"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "performance_analysis")

async def chat_about_tests(directory: str, analysis_results: Dict[str, Any]):
    """Start an interactive chat session about test analysis."""
    print("\n=== Starting Test Analysis Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm analyzing tests in: {directory}

Analysis Results:
{json.dumps(analysis_results, indent=2)}

Please help me understand and improve the test suite."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current analysis results")
            print("- coverage: Get coverage analysis")
            print("- quality: Get test quality analysis")
            print("- recommendations: Get test improvement recommendations")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Analysis Results:")
            print(json.dumps(analysis_results, indent=2))
            continue
        elif user_input.lower() == 'coverage':
            user_input = "Please analyze the test coverage and suggest areas for improvement."
        elif user_input.lower() == 'quality':
            user_input = "What are the quality issues in the test suite and how can they be addressed?"
        elif user_input.lower() == 'recommendations':
            user_input = "What specific recommendations do you have for improving the test suite?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.code"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "test_analysis")

async def organize_files(directory: str, save_report: bool = False):
    """Organize files using AI-driven analysis."""
    organizer = FileOrganizer(settings)
    print(f"\nAnalyzing directory {directory}...")
    
    analysis = organizer.analyze_directory(directory)
    
    if "error" in analysis:
        print_error(analysis["error"])
        return
    
    print_header("Directory Analysis Results")
    print(f"\nTotal Size: {analysis['total_size'] / 1024 / 1024:.2f} MB")
    print(f"Files: {analysis['file_count']}")
    print(f"Directories: {analysis['dir_count']}")
    
    print("\nGenerating organization plan...")
    try:
        plan = organizer.get_organization_plan(analysis)
        
        print_header("Organization Plan")
        
        print("\nSuggested Categories:")
        for category, patterns in plan.categories.items():
            print(f"\n{Fore.CYAN}{category}{Style.RESET_ALL}")
            for pattern in patterns:
                print(f"- {pattern}")
        
        print("\nProposed Moves:")
        for move in plan.moves:
            print(f"\n{Fore.YELLOW}Move:{Style.RESET_ALL}")
            print(f"From: {move['source']}")
            print(f"To: {move['destination']}")
        
        print("\nRecommendations:")
        for rec in plan.recommendations:
            print(f"- {rec}")
        
        if click.confirm("\nWould you like to start a chat about the organization plan?"):
            await chat_about_organization(directory, plan)
        
        if click.confirm("\nWould you like to preview the changes?"):
            results = organizer.execute_plan(plan, dry_run=True)
            
            print_header("Preview Results")
            print(f"\nFiles that would be moved: {len(results['success'])}")
            print(f"Files that would be skipped: {len(results['skipped'])}")
            print(f"Files that would fail: {len(results['failed'])}")
            
            if click.confirm("\nWould you like to proceed with the reorganization?"):
                results = organizer.execute_plan(plan, dry_run=False)
                
                print_header("Reorganization Results")
                print(f"\nSuccessfully moved: {len(results['success'])}")
                print(f"Skipped: {len(results['skipped'])}")
                print(f"Failed: {len(results['failed'])}")
                
                if results["failed"]:
                    print("\nFailed moves:")
                    for fail in results["failed"]:
                        print(f"\nFrom: {fail['source']}")
                        print(f"To: {fail['destination']}")
                        print(f"Error: {fail['error']}")
        
        if save_report:
            save_report({
                "directory": directory,
                "timestamp": datetime.now().isoformat(),
                "analysis": analysis,
                "plan": {
                    "categories": plan.categories,
                    "moves": plan.moves,
                    "recommendations": plan.recommendations
                }
            }, "file_organization")
            
    except Exception as e:
        print_error(f"Error generating organization plan: {str(e)}")

async def chat_about_organization(directory: str, plan: OrganizationPlan):
    """Start an interactive chat session about file organization."""
    print("\n=== Starting Organization Chat ===")
    print("Type 'exit' to end the chat, 'help' for available commands")
    
    context = f"""I'm organizing the directory: {directory}

Current Structure:
{json.dumps(plan.current_structure, indent=2)}

Proposed Changes:
{json.dumps(plan.suggested_structure, indent=2)}

Please help me understand and improve the organization plan."""

    chat_history = [{"role": "system", "content": context}]
    
    while True:
        user_input = input("\nYou: ").strip()
        
        if user_input.lower() == 'exit':
            break
        elif user_input.lower() == 'help':
            print("\nAvailable commands:")
            print("- exit: End the chat session")
            print("- help: Show this help message")
            print("- show: Display current organization plan")
            print("- structure: Get structure analysis")
            print("- categories: Get category recommendations")
            print("- moves: Get move recommendations")
            continue
        elif user_input.lower() == 'show':
            print("\nCurrent Organization Plan:")
            print(json.dumps(plan.suggested_structure, indent=2))
            continue
        elif user_input.lower() == 'structure':
            user_input = "Please analyze the current structure and suggest improvements."
        elif user_input.lower() == 'categories':
            user_input = "What categories would you recommend for these files?"
        elif user_input.lower() == 'moves':
            user_input = "What specific moves would you recommend to improve organization?"
        
        chat_history.append({"role": "user", "content": user_input})
        
        try:
            conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in chat_history])
            
            response = requests.post(
                f"{settings.get('ollama.base_url')}/api/generate",
                json={
                    "model": settings.get("ollama.models.text"),
                    "prompt": conversation,
                    "stream": False
                }
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "No response from AI model")
                print(f"\nOllama: {ai_response}")
                chat_history.append({"role": "assistant", "content": ai_response})
            else:
                print_error(f"Error getting AI response: {response.status_code}")
                
        except Exception as e:
            print_error(f"Error in chat: {str(e)}")
    
    if click.confirm("\nWould you like to save this chat session?"):
        save_chat_session(chat_history, "file_organization")

def setup_task_commands(app):
    """Setup task automation commands."""
    
    @app.command()
    def task_list():
        """List all automated tasks."""
        try:
            from core.task_automator import TaskAutomator
            automator = TaskAutomator(settings)
            tasks = automator.get_tasks()
            
            if not tasks:
                print("No tasks configured.")
                return
                
            print("\nConfigured Tasks:")
            print("=" * 80)
            for task in tasks:
                print(f"\nTask: {task['name']}")
                print(f"Description: {task['description']}")
                print(f"Trigger: {task['trigger_type']} - {task['trigger_value']}")
                print(f"Action: {task['action']}")
                print(f"Status: {'Enabled' if task['enabled'] else 'Disabled'}")
                if task['last_run']:
                    print(f"Last Run: {task['last_run']}")
                if task['next_run']:
                    print(f"Next Run: {task['next_run']}")
                print("-" * 80)
                
        except Exception as e:
            print(f"Error listing tasks: {str(e)}")
    
    @app.command()
    def task_add(
        name: str = typer.Option(..., prompt=True, help="Name of the task"),
        description: str = typer.Option(..., prompt=True, help="Description of the task"),
        trigger_type: str = typer.Option(..., prompt=True, help="Trigger type (time/interval/event/condition)"),
        trigger_value: str = typer.Option(..., prompt=True, help="Trigger value (HH:MM for time, seconds for interval, event name, or condition)"),
        action: str = typer.Option(..., prompt=True, help="Action to perform"),
        parameters: str = typer.Option("{}", help="JSON string of parameters")
    ):
        """Add a new automated task."""
        try:
            from core.task_automator import TaskAutomator, Task, TaskTrigger
            automator = TaskAutomator(settings)
            
            # Parse parameters
            try:
                params = json.loads(parameters)
            except:
                params = {}
            
            # Create task
            task = Task(
                name=name,
                description=description,
                trigger_type=TaskTrigger(trigger_type),
                trigger_value=trigger_value,
                action=action,
                parameters=params
            )
            
            # Add task
            if automator.add_task(task):
                print(f"Task '{name}' added successfully.")
            else:
                print("Failed to add task. Please check the configuration.")
                
        except Exception as e:
            print(f"Error adding task: {str(e)}")
    
    @app.command()
    def task_remove(
        name: str = typer.Option(..., prompt=True, help="Name of the task to remove")
    ):
        """Remove an automated task."""
        try:
            from core.task_automator import TaskAutomator
            automator = TaskAutomator(settings)
            
            if automator.remove_task(name):
                print(f"Task '{name}' removed successfully.")
            else:
                print(f"Task '{name}' not found.")
                
        except Exception as e:
            print(f"Error removing task: {str(e)}")
    
    @app.command()
    def task_update(
        name: str = typer.Option(..., prompt=True, help="Name of the task to update"),
        enabled: bool = typer.Option(None, help="Enable/disable the task"),
        description: str = typer.Option(None, help="New description"),
        trigger_value: str = typer.Option(None, help="New trigger value"),
        parameters: str = typer.Option(None, help="New JSON parameters")
    ):
        """Update an existing automated task."""
        try:
            from core.task_automator import TaskAutomator
            automator = TaskAutomator(settings)
            
            # Prepare updates
            updates = {}
            if enabled is not None:
                updates['enabled'] = enabled
            if description:
                updates['description'] = description
            if trigger_value:
                updates['trigger_value'] = trigger_value
            if parameters:
                try:
                    updates['parameters'] = json.loads(parameters)
                except:
                    print("Invalid JSON parameters.")
                    return
            
            if automator.update_task(name, updates):
                print(f"Task '{name}' updated successfully.")
            else:
                print(f"Task '{name}' not found.")
                
        except Exception as e:
            print(f"Error updating task: {str(e)}")
    
    @app.command()
    def task_start():
        """Start the task automation system."""
        try:
            from core.task_automator import TaskAutomator
            automator = TaskAutomator(settings)
            automator.start()
            print("Task automation system started.")
            
        except Exception as e:
            print(f"Error starting task automation: {str(e)}")
    
    @app.command()
    def task_stop():
        """Stop the task automation system."""
        try:
            from core.task_automator import TaskAutomator
            automator = TaskAutomator(settings)
            automator.stop()
            print("Task automation system stopped.")
            
        except Exception as e:
            print(f"Error stopping task automation: {str(e)}")

def main():
    app = typer.Typer(help="System AI Manager CLI")
    
    # Add commands
    setup_code_commands(app)
    setup_text_commands(app)
    setup_system_commands(app)
    setup_security_commands(app)
    setup_directory_commands(app)
    setup_dependency_commands(app)
    setup_performance_commands(app)
    setup_test_commands(app)
    setup_organization_commands(app)
    setup_task_commands(app)  # Add task automation commands
    
    app()

if __name__ == '__main__':
    main() 