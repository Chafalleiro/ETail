#!/bin/bash

# build_controller.sh
# Builds ETail Monitor Controller as standalone executable

set -e

echo "🚀 Building etail-panel-applet Executable"
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
# sudo apt-get install libcairo2-dev
# sudo apt-get install libgirepository1.0-dev
# sudo apt install gir1.2-notify-0.7


echo "📦 Installing dependencies..."
pip install --upgrade pip
pip install pyinstaller psutil pyinstaller-hooks-contrib pycairo PyObject
pip install PyGObject==3.50.0


# Create the executable
echo "🔨 Building executable..."

pyinstaller --onefile --windowed \
--hidden-import gi \
--hidden-import gi.repository.Gtk \
--hidden-import gi.repository.Gdk \
--hidden-import gi.repository.Notify \
--add-data "$HOME/.config/etail-monitor-controller/*:.config/etail-panel-applet" \
etail-panel-applet.py

# Check if build was successful
if [ -f "./dist/etail-monitor-controller" ]; then
    echo "✅ Build successful!"
    echo "📦 Executable: ./dist/etail-panel-applet"
    
    # Make executable
    chmod +x ./dist/etail-panel-applet
    
    # Test the executable
    echo "🧪 Testing executable..."
    ./dist/etail-panel-applet --help 2>/dev/null && echo "✅ Executable test passed" || echo "⚠️  Executable may have issues"
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
