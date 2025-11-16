#!/bin/bash
# install_linux_client.sh

echo "Installing Linux Log Monitor Client..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root for installation"
    exit 1
fi

# Build the executable
echo "🔨 Building executable..."
source log_monitor_env/bin/activate
python build_exe.py

# Install to /usr/local/bin
echo "📦 Installing to /usr/local/bin..."
cp dist/LinuxLogMonitor /usr/local/bin/
chmod +x /usr/local/bin/LinuxLogMonitor

# Create systemd service
echo "📋 Creating systemd service..."
chmod +x create_systemd_service.sh
./create_systemd_service.sh

# Create log directory
mkdir -p /var/log/linux-log-monitor

echo "✅ Installation complete!"
echo ""
echo "Next steps:"
echo "1. Edit /etc/linux-log-monitor.conf with your settings"
echo "2. Run: sudo systemctl daemon-reload"
echo "3. Run: sudo systemctl enable linux-log-monitor"
echo "4. Run: sudo systemctl start linux-log-monitor"
echo "5. Check status: sudo systemctl status linux-log-monitor"
echo "6. View logs: sudo journalctl -u linux-log-monitor -f"
