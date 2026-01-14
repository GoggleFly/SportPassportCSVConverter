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
        echo "Using Rosetta 2 (arch -x86_64) to build x64 executable"
        PYTHON_CMD="arch -x86_64 python3"
        # Check if x64 Python is available
        if ! $PYTHON_CMD -c "import sys; print(sys.executable)" &>/dev/null; then
            echo "Error: x64 Python interpreter not available via Rosetta 2"
            echo "You may need to install a universal Python or use a different Python installation"
            exit 1
        fi
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
