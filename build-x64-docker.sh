#!/bin/bash
#
# Build x64 executable using Docker
# Useful for building x64 executables on Apple Silicon Macs
#

set -e

echo "Building x64 executable using Docker..."
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    echo "Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    exit 1
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build/
rm -rf dist/
rm -rf *.spec.bak

# Build using Docker
echo "Building executable in Docker container (this may take a few minutes)..."
docker run --rm \
    -v "$(pwd):/src" \
    -w /src \
    python:3.11-slim \
    bash -c "
        echo 'Installing dependencies...' &&
        pip install --quiet pyinstaller &&
        pip install --quiet -r requirements.txt &&
        echo 'Building executable...' &&
        python -m PyInstaller sport-passport-converter.spec --clean --noconfirm &&
        echo 'Build complete!'
    "

echo ""
echo "✓ Build complete!"
echo ""
echo "Executable is in the dist/ directory:"
ls -lh dist/

# Verify executable architecture
if [[ -f "dist/sport-passport-converter" ]]; then
    echo ""
    echo "Verifying executable architecture:"
    file dist/sport-passport-converter
fi

echo ""
echo "Note: The executable may take 10-30 seconds to start on first run"
echo "      as it extracts bundled libraries. A loading message will be displayed."
