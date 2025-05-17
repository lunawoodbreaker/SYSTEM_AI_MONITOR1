from setuptools import setup, find_packages

setup(
    name="system_ai_manager",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "colorama>=0.4.6",
        "pyperclip>=1.8.2",
        "fastapi>=0.68.0",
        "uvicorn>=0.15.0",
        "requests>=2.26.0",
        "pydantic>=1.8.2",
        "python-multipart>=0.0.5",
        "aiofiles>=0.7.0",
        "watchdog>=2.1.6",
        "psutil>=5.8.0",
        "python-dotenv>=0.19.0",
    ],
    entry_points={
        'console_scripts': [
            'system-ai=system_ai_manager.src.cli:main',
        ],
    },
    author="Your Name",
    author_email="your.email@example.com",
    description="A system AI manager for code analysis and system health monitoring",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/system-ai-manager",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires=">=3.7",
) 