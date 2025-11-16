#!/bin/bash

# build_executable.sh
# Builds executable using existing virtual environment

SCRIPT_NAME="et_hardware_mon_linux"

echo "🔨 Building executable..."

if [ ! -d "build_venv" ]; then
    echo "❌ Build environment not found. Run ./setup_build_env.sh first"
    exit 1
fi

source build_venv/bin/activate
pyinstaller --onefile --hidden-import=psutil $SCRIPT_NAME.py
deactivate

if [ -f "./dist/$SCRIPT_NAME" ]; then
    echo "✅ Executable built: ./dist/$SCRIPT_NAME"
    echo ""
    echo "📦 To install: sudo cp ./dist/$SCRIPT_NAME /usr/local/bin/"
else
    echo "❌ Build failed"
    exit 1
fi
