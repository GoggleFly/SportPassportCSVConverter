# Packaging and Distribution Guide

This guide explains how to package the Sport Passport CSV Converter for distribution to end users.

## Distribution Options

There are several ways to distribute this utility:

1. **Python Package (pip installable)** - For users who have Python installed
2. **Standalone Executable** - For users without Python (single-file executable)

---

## Option 1: Python Package (Recommended for Technical Users)

This creates a `.whl` file that users can install with pip.

### Prerequisites

```bash
pip install build wheel twine
```

### Building the Package

```bash
# Make build script executable (first time only)
chmod +x build-package.sh

# Build the package
./build-package.sh
```

This creates:
- `dist/sport-passport-csv-converter-1.0.0.tar.gz` (source distribution)
- `dist/sport-passport-csv-converter-1.0.0-py3-none-any.whl` (wheel package)

### Distributing the Package

#### Local Distribution

Users can install directly from the wheel file:

```bash
pip install dist/sport-passport-csv-converter-*.whl
```

After installation, users can run:

```bash
# Using the command name
sport-passport-converter input.xlsx

# Or the short alias
sp-converter input.xlsx

# Or as a module
python -m converter input.xlsx
```

#### Upload to PyPI (Public Distribution)

1. Create accounts on [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)

2. Install twine:
```bash
pip install twine
```

3. Upload to TestPyPI first (for testing):
```bash
twine upload --repository testpypi dist/*
```

4. Test installation from TestPyPI:
```bash
pip install --index-url https://test.pypi.org/simple/ sport-passport-csv-converter
```

5. If successful, upload to PyPI:
```bash
twine upload dist/*
```

6. Users can then install with:
```bash
pip install sport-passport-csv-converter
```

---

## Option 2: Standalone Executable (Recommended for Non-Technical Users)

This creates a single-file executable (interactive version) that doesn't require Python installation.

### Prerequisites

```bash
pip install pyinstaller
```

### Building the Executable

```bash
# Make build script executable (first time only)
chmod +x build-executable.sh

# Build the executable
./build-executable.sh
```

This creates `dist/sport-passport-converter` (or `.exe` on Windows) - the interactive version that prompts users for input and output file paths.

### Distributing the Executable

1. **Test the executable locally**:
   ```bash
   # Interactive version - prompts for input/output files
   ./dist/sport-passport-converter
   ```

2. **Package for distribution**:
   - **macOS/Linux**: Create a `.zip` or `.tar.gz` archive
   - **Windows**: Create a `.zip` archive (or use an installer tool like Inno Setup)

3. **Include documentation**:
   - Create a simple `README.txt` or `INSTRUCTIONS.txt` with usage examples
   - Include the main README.md if helpful

4. **Optional: Create an installer**:
   - **macOS**: Use `create-dmg` or `hdiutil` to create a `.dmg` file
   - **Windows**: Use Inno Setup, NSIS, or similar tools
   - **Linux**: Create a `.deb` or `.rpm` package

### Platform-Specific Notes

#### macOS
- The executable should work on macOS 10.15+ (Catalina and later)
- You may need to sign the executable to avoid Gatekeeper warnings
- Consider notarization for distribution outside the Mac App Store

#### Windows
- Build on Windows for best compatibility
- The executable name will be `sport-passport-converter.exe`
- Users may see Windows Defender warnings (common for unsigned executables)

#### Linux
- Build on the target distribution for best compatibility
- Consider creating distribution-specific packages (`.deb`, `.rpm`)
- The executable should work on most modern Linux distributions

---

## Option 3: Distribution via Docker (Advanced)

If you want to distribute as a Docker container:

### Create Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENTRYPOINT ["sport-passport-converter"]
```

### Build and Run

```bash
docker build -t sport-passport-converter .
docker run -v $(pwd):/data sport-passport-converter /data/input.xlsx
```

---

## Quick Start: Building Both Formats

To build both the Python package and standalone executable:

```bash
# Build Python package
./build-package.sh

# Build standalone executable
./build-executable.sh
```

Both will be in the `dist/` directory.

---

## Testing Before Distribution

Before distributing to users:

1. **Test in a clean environment**:
   ```bash
   # Create a virtual environment
   python3 -m venv test_env
   source test_env/bin/activate  # On Windows: test_env\Scripts\activate
   
   # For Python package: install from wheel
   pip install dist/sport-passport-csv-converter-*.whl
   
   # Test the command
   sport-passport-converter --help
   ```

2. **Test with sample files**: Use the provided test fixtures or sample Excel/CSV files

3. **Test interactive mode**: Ensure all prompts work correctly

4. **Test on target platforms**: If possible, test on the OS your users will use

---

## Version Management

To update the version:

1. Update `converter/__init__.py`: `__version__ = "1.0.1"`
2. Update `pyproject.toml`: `version = "1.0.1"`
3. Update `setup.py`: `version="1.0.1"`
4. Rebuild packages/executables

---

## Recommended Distribution Strategy

- **For technical users** (developers, IT staff): Distribute as Python package via PyPI or direct wheel file
- **For end users** (non-technical users): Distribute as standalone executable with simple instructions
- **For organizations**: Consider both options, with the executable as the primary recommendation

---

## Additional Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PyInstaller Documentation](https://pyinstaller.org/)
- [PyPI Packaging Guide](https://packaging.python.org/tutorials/packaging-projects/)
