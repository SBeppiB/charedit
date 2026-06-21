"""
Setup script for CHAREDIT library.
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="charedit",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A Python library for highlighting character dialogue in text",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/charedit",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Text Processing",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # No external dependencies for core library
    ],
    extras_require={
        "gui": ["PyQt6"],
        "dev": ["pytest", "black", "flake8"],
    },
    entry_points={
        "console_scripts": [
            "charedit=charedit.cli:main",
        ],
    },
)
