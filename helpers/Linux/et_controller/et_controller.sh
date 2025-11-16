#!/bin/bash

# et_controller.sh
# Installs the Wtail System Monitor Controller

set -e

echo "🚀 Installing Etail System Monitor Controller"
echo "======================================"

# Check if running as root
if [ "$(id -u)" -eq 0 ]; then
    echo "❌ Do not run as root. Run as regular user."
    exit 1
fi

# Create virtual environment
echo "🐍 Setting up Python environment..."
python3 -m venv et_controller_venv
source et_controller_venv/bin/activate

# Install dependencies
pip install psutil  # Usually comes with system Python

echo "✅ Environment setup complete"

# Make main script executable
chmod +x etail_mon_controller.py

echo ""
echo "🎉 Installation complete!"
echo "======================================"
echo "🚀 To start the controller:"
echo "   source controller_venv/bin/activate"
echo "   python3 monitor_controller.py"
echo ""
echo "💡 You can also create a desktop shortcut:"
echo "   [Desktop Entry]"
echo "   Type=Application"
echo "   Name=System Monitor Controller"
echo "   Exec=$(pwd)/controller_venv/bin/python3 $(pwd)/monitor_controller.py"
echo "   Icon=utilities-system-monitor"
echo "   Categories=System;"
