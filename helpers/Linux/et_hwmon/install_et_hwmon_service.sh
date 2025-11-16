#!/bin/bash

# install_et_hwmon_service.sh
# Creates a systemd service file for the Linux Hardware Monitor

SERVICE_NAME="et-hardware-monitor"
EXECUTABLE_NAME="et_hardware_mon_linux"
INSTALL_DIR="/usr/local/bin"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

echo "🔧 Creating systemd service for Hardware Monitor..."

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if executable exists
if [ ! -f "$INSTALL_DIR/$EXECUTABLE_NAME" ]; then
    echo "❌ Executable not found at $INSTALL_DIR/$EXECUTABLE_NAME"
    echo "💡 Please build and install the executable first"
    exit 1
fi

# Get configuration from user
echo ""
echo "📝 Please enter your server configuration:"
read -p "Server host [192.168.1.132]: " SERVER_HOST
SERVER_HOST=${SERVER_HOST:-192.168.1.132}
read -p "Server port [21327]: " SERVER_PORT
SERVER_PORT=${SERVER_PORT:-21327}
read -s -p "Server password: " SERVER_PASSWORD
echo ""

# Create service file
echo "📄 Creating service file at $SERVICE_FILE..."
sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=ETail Hardware Monitor Service
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/$EXECUTABLE_NAME --host $SERVER_HOST --port $SERVER_PORT --password '$SERVER_PASSWORD'
Restart=always
RestartSec=10
User=root
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Set proper permissions
chmod 644 $SERVICE_FILE

echo "✅ Created systemd service: $SERVICE_NAME"
echo ""
echo "🚀 To complete setup:"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable $SERVICE_NAME"
echo "   sudo systemctl start $SERVICE_NAME"
echo ""
echo "📋 Useful commands:"
echo "   sudo systemctl status $SERVICE_NAME    # Check status"
echo "   sudo journalctl -u $SERVICE_NAME -f    # View logs"
echo "   sudo systemctl stop $SERVICE_NAME      # Stop service"
