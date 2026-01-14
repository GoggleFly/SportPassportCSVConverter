"""Setup configuration for Sport Passport CSV Converter."""
from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

setup(
    name="sport-passport-csv-converter",
    version="1.0.0",
    description="A command-line utility to convert Excel spreadsheets into compliant CSV format for Sport Passport import",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Sport Passport CSV Converter Team",
    python_requires=">=3.8",
    packages=find_packages(),
    install_requires=[
        "pandas>=2.0.0",
        "openpyxl>=3.1.0",
        "pydantic>=2.0.0",
        "rich>=13.0.0",
        "questionary>=2.0.0",
        "python-dateutil>=2.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-mock>=3.10.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "sport-passport-converter=converter.main:main",
            "sp-converter=converter.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business :: Financial :: Spreadsheet",
        "Topic :: Utilities",
    ],
    keywords=["csv", "excel", "converter", "sport-passport", "data-conversion"],
)
