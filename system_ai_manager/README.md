# System AI Manager

A Python-based system for managing and analyzing code files with AI capabilities.

## Project Structure

```
system_ai_manager/
├── src/               # Source code
├── tests/            # Test files
├── docs/             # Documentation
└── requirements.txt  # Python dependencies
```

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Features

- File system monitoring
- Code analysis
- Document scanning
- Web interface for interaction

## Usage

1. Start the web interface:
```bash
python src/web_interface.py
```

2. The system will automatically monitor and analyze files in the configured directories.

## Development

- All source code is in the `src/` directory
- Tests are in the `tests/` directory
- Documentation is in the `docs/` directory 