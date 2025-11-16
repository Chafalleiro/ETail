#!/bin/bash

# install_hardware_monitor.sh
# Complete installer for Linux Hardware Monitor

set -e

SCRIPT_NAME="et_hardware_mon_linux"
SERVICE_NAME="et_hardware-monitor"
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
BUILD_DIR="./dist"

echo "🚀 Etail Linux Hardware Monitor Installer"
echo "======================================"

# Check if script is run as root
if [ "$(id -u)" -eq 0 ]; then
    echo "❌ Do not run this script as root/sudo initially."
    echo "💡 Run as regular user first, then use sudo only when prompted."
    exit 1
fi

# Check dependencies
echo "🔍 Checking dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed. Please install python3 first."
    exit 1
fi

# Check if virtual environment exists and has pyinstaller
if [ ! -d "build_venv" ] || ! build_venv/bin/pip list | grep -q pyinstaller; then
    echo "🐍 Setting up build environment..."
    python3 -m venv build_venv
    source build_venv/bin/activate
    pip install pyinstaller psutil
    deactivate
    echo "✅ Build environment ready"
fi

if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 is required but not installed. Please install python3-pip first."
    exit 1
fi

# Build the executable as regular user
echo "📦 Building executable..."
source build_venv/bin/activate
pyinstaller --onefile --hidden-import=psutil $SCRIPT_NAME.py
deactivate

if [ ! -f "$BUILD_DIR/$SCRIPT_NAME" ]; then
    echo "❌ Build failed - executable not found"
    exit 1
fi

echo "✅ Executable built successfully"

# Now request sudo for installation steps
echo ""
echo "🛠️  The following steps require root permissions:"
echo "======================================"

# Get configuration before sudo to avoid password prompts in subshell
read -p "Server host [192.168.1.132]: " SERVER_HOST
SERVER_HOST=${SERVER_HOST:-192.168.1.132}
read -p "Server port [21327]: " SERVER_PORT  
SERVER_PORT=${SERVER_PORT:-21327}
read -s -p "Server password: " SERVER_PASSWORD
echo ""

# Install executable with sudo
echo "📥 Installing executable to $INSTALL_DIR..."
sudo cp "$BUILD_DIR/$SCRIPT_NAME" "$INSTALL_DIR/"
sudo chmod +x "$INSTALL_DIR/$SCRIPT_NAME"
sudo chown root:root "$INSTALL_DIR/$SCRIPT_NAME"

echo "✅ Executable installed with proper permissions"

# Install lm-sensors if not present
echo "🔍 Checking for lm-sensors..."
if ! command -v sensors &> /dev/null; then
    echo "📥 Installing lm-sensors..."
    sudo apt update && sudo apt install -y lm-sensors
    echo "🔧 Running sensor detection..."
    sudo sensors-detect --auto
fi

# Create systemd service
echo "📄 Creating systemd service..."

# Create service file with sudo
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Hardware Monitor Service
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/$SCRIPT_NAME --host $SERVER_HOST --port $SERVER_PORT --password '$SERVER_PASSWORD'
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo chmod 644 $SERVICE_FILE

# Reload and enable service
echo "🔄 Setting up service..."
sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME

echo ""
echo "🎉 Installation complete!"
echo "======================================"
echo "📋 What was installed:"
echo "   ✅ Executable: $INSTALL_DIR/$SCRIPT_NAME (owned by root)"
echo "   ✅ Service: $SERVICE_FILE"
echo "   ✅ Auto-start: Enabled"
echo ""
echo "🚀 To start the service:"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "📊 To check status:"
echo "   systemctl status $SERVICE_NAME"
echo "   journalctl -u $SERVICE_NAME -f"
