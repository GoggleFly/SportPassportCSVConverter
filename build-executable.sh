#!/bin/bash
#
# Build standalone executable using PyInstaller
# Creates a single-file executable (interactive version) that doesn't require Python installation
#

set -e

# Check for architecture argument
TARGET_ARCH="${1:-auto}"

echo "Building standalone executable for Sport Passport CSV Converter..."
echo ""

# Detect current architecture
CURRENT_ARCH=$(uname -m)
echo "Current architecture: $CURRENT_ARCH"

# Determine Python command based on target architecture
if [[ "$TARGET_ARCH" == "x64" || "$TARGET_ARCH" == "x86_64" ]]; then
    if [[ "$CURRENT_ARCH" == "arm64" ]]; then
        echo "Building for x64 (Intel) on Apple Silicon..."
        
        # Try to find an x86_64 Python interpreter
        PYTHON_CMD=""
        
        # Check system Python first
        if /usr/bin/python3 -c "import platform; exit(0 if platform.machine() == 'x86_64' else 1)" 2>/dev/null; then
            echo "Using system Python (/usr/bin/python3) for x64 build"
            PYTHON_CMD="/usr/bin/python3"
        # Check Homebrew x86_64 Python (if Homebrew was installed for Intel)
        elif [[ -f "/usr/local/bin/python3" ]] && file /usr/local/bin/python3 2>/dev/null | grep -q "x86_64"; then
            echo "Using Homebrew x86_64 Python (/usr/local/bin/python3)"
            PYTHON_CMD="/usr/local/bin/python3"
        # Check pyenv for x86_64 Python
        elif command -v pyenv &> /dev/null; then
            echo "Checking for x86_64 Python in pyenv..."
            # Look for x86_64 Python in pyenv
            PYENV_X64=$(find ~/.pyenv/versions -name python3 -type f 2>/dev/null | while read py; do
                if file "$py" 2>/dev/null | grep -q "x86_64"; then
                    echo "$py"
                    break
                fi
            done)
            
            if [[ -n "$PYENV_X64" && -x "$PYENV_X64" ]]; then
                echo "Found x86_64 Python in pyenv: $PYENV_X64"
                PYTHON_CMD="$PYENV_X64"
            fi
        fi
        
        # If no x86_64 Python found, provide installation instructions
        if [[ -z "$PYTHON_CMD" ]]; then
            echo ""
            echo "❌ Error: No x86_64 Python interpreter found."
            echo ""
            echo "To build x64 executables on Apple Silicon, you need an x86_64 Python interpreter."
            echo ""
            echo "Installation Options:"
            echo ""
            echo "Option 1: Install x86_64 Python via pyenv (Recommended)"
            echo "  arch -x86_64 pyenv install 3.11.9"
            echo "  # Then set it as a local version or use it directly"
            echo ""
            echo "Option 2: Install x86_64 Homebrew and Python"
            echo "  # First install Homebrew for Intel:"
            echo "  arch -x86_64 /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
            echo "  # Then install Python:"
            echo "  arch -x86_64 /usr/local/bin/brew install python@3.11"
            echo ""
            echo "Option 3: Use Docker to build x64 executable"
            echo "  # See PACKAGING.md for Docker build instructions"
            echo ""
            exit 1
        fi
        
        # Verify the Python is actually x86_64
        PYTHON_ARCH=$($PYTHON_CMD -c "import platform; print(platform.machine())" 2>/dev/null)
        if [[ "$PYTHON_ARCH" != "x86_64" ]]; then
            echo "Error: Selected Python interpreter is $PYTHON_ARCH, not x86_64"
            echo "Python path: $PYTHON_CMD"
            exit 1
        fi
        echo "Verified: Python architecture is x86_64"
    else
        echo "Building for x64 (native)..."
        PYTHON_CMD="python3"
    fi
elif [[ "$TARGET_ARCH" == "arm64" || "$TARGET_ARCH" == "arm" ]]; then
    echo "Building for ARM64 (Apple Silicon)..."
    PYTHON_CMD="python3"
else
    # Auto-detect: use native architecture
    echo "Auto-detecting architecture (building for native: $CURRENT_ARCH)..."
    PYTHON_CMD="python3"
fi

# Ensure we have required tools
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed"
    exit 1
fi

# Install PyInstaller if not already installed
if ! $PYTHON_CMD -m pip show pyinstaller &> /dev/null; then
    echo "Installing PyInstaller..."
    $PYTHON_CMD -m pip install pyinstaller
fi

# Verify all dependencies are installed
echo "Verifying dependencies are installed..."
$PYTHON_CMD -c "import pandas, openpyxl, pydantic, rich, questionary, dateutil; print('✓ All dependencies found')" || {
    echo "Error: Some dependencies are missing. Installing from requirements.txt..."
    $PYTHON_CMD -m pip install -r requirements.txt
}

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.spec.bak

# Build executable (interactive version only)
echo "Building standalone executable (interactive mode)..."
echo "Using Python: $($PYTHON_CMD --version)"
echo "Python architecture: $($PYTHON_CMD -c 'import platform; print(platform.machine())')"
$PYTHON_CMD -m PyInstaller sport-passport-converter.spec --clean --noconfirm

echo ""
echo "✓ Build complete!"
echo ""
echo "Executable is in the dist/ directory:"
ls -lh dist/

# Verify executable architecture (macOS only)
if [[ "$OSTYPE" == "darwin"* ]] && [[ -f "dist/sport-passport-converter" ]]; then
    echo ""
    echo "Verifying executable architecture:"
    file dist/sport-passport-converter
    if command -v lipo &> /dev/null; then
        echo "Architectures in executable:"
        lipo -info dist/sport-passport-converter 2>/dev/null || echo "  (single architecture binary)"
    fi
fi

echo ""
echo "Note: The executable may take 10-30 seconds to start on first run"
echo "      as it extracts bundled libraries. A loading message will be displayed."
echo ""
echo "Usage:"
echo "  ./build-executable.sh          # Build for native architecture"
echo "  ./build-executable.sh x64      # Build for x64 (Intel) architecture"
echo "  ./build-executable.sh arm64   # Build for ARM64 (Apple Silicon) architecture"
echo ""
echo "Alternative for x64 builds on Apple Silicon:"
echo "  ./build-x64-docker.sh          # Build x64 executable using Docker (no x86_64 Python needed)"

# Detect OS and provide appropriate instructions
if [[ "$OSTYPE" == "darwin"* ]]; then
    BUILT_ARCH=$(file dist/sport-passport-converter 2>/dev/null | grep -o "x86_64\|arm64" | head -1 || echo "unknown")
    echo ""
    echo "macOS executable created: dist/sport-passport-converter"
    echo "Built architecture: $BUILT_ARCH"
    echo ""
    echo "To distribute:"
    echo "  1. Test the executable: ./dist/sport-passport-converter"
    echo "  2. Create a .zip file with the executable"
    echo "  3. Optional: Create a .dmg installer for easier distribution"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo ""
    echo "Linux executable created: dist/sport-passport-converter"
    echo ""
    echo "To distribute:"
    echo "  1. Test the executable: ./dist/sport-passport-converter"
    echo "  2. Create a .tar.gz archive with the executable"
    echo "  3. Note: May need to build on target OS/architecture"
else
    echo ""
    echo "Executable created: dist/sport-passport-converter"
fi
