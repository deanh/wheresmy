#!/usr/bin/env python3
"""
Setup script for the wheresmy package.
"""

from setuptools import setup, find_packages

setup(
    name="wheresmy",
    version="0.1.0",
    description="Wheresmy - Image metadata extraction and search",
    author="Wheresmy Team",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "flask",
        "flask-cors",
        "pillow",
        "piexif",
        "transformers",
        "torch",
    ],
    entry_points={
        "console_scripts": [
            "wheresmy-search=wheresmy.cli.search_cli:main",
            "wheresmy-import=wheresmy.cli.import_metadata:main",
            "wheresmy-web=wheresmy.cli.run_web:main",
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
)