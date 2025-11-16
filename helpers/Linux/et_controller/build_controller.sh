#!/bin/bash

# build_controller.sh
# Builds ETail Monitor Controller as standalone executable

set -e

echo "🚀 Building ETail Monitor Controller Executable"
echo "=============================================="

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "❌ Do not run as root. Run as regular user."
    exit 1
fi

# Create build environment
echo "🐍 Setting up build environment..."
python3 -m venv build_venv
source build_venv/bin/activate

# Install dependencies
echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller psutil

# Create the executable
echo "🔨 Building executable..."
pyinstaller --onefile \
    --name="etail-monitor-controller" \
    --add-data="*.json:." \
    --hidden-import="tkinter" \
    --hidden-import="psutil" \
    --hidden-import="pathlib" \
    --hidden-import="json" \
    --hidden-import="os" \
    --hidden-import="sys" \
    --hidden-import="subprocess" \
    --hidden-import="threading" \
    --hidden-import="re" \
    --hidden-import="time" \
    --console \
    etail_mon_controller.py

# Check if build was successful
if [ -f "./dist/etail-monitor-controller" ]; then
    echo "✅ Build successful!"
    echo "📦 Executable: ./dist/etail-monitor-controller"
    
    # Make executable
    chmod +x ./dist/etail-monitor-controller
    
    # Test the executable
    echo "🧪 Testing executable..."
    ./dist/etail-monitor-controller --help 2>/dev/null && echo "✅ Executable test passed" || echo "⚠️  Executable may have issues"
else
    echo "❌ Build failed!"
    exit 1
fi

# Clean up
deactivate
rm -rf build_venv

echo ""
echo "🎉 Build complete!"
echo "🚀 To install system-wide: sudo cp ./dist/etail-monitor-controller /usr/local/bin/"
