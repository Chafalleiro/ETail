#!/bin/bash

# install_controller.sh
# Installs the compiled ETail Monitor Controller system-wide

set -e

echo "🚀 Installing ETail Monitor Controller"
echo "======================================"

# Check if running as root
if [ "$(id -u)" -ne 0 ]; then
    echo "❌ This script must be run as root (use sudo)"
    exit 1
fi

# Check if executable exists
if [ ! -f "./dist/etail-monitor-controller" ]; then
    echo "❌ Executable not found. Please run build_controller.sh first."
    exit 1
fi

# Install executable
echo "📦 Installing executable to /usr/local/bin/"
cp ./dist/etail-monitor-controller /usr/local/bin/
chmod +x /usr/local/bin/etail-monitor-controller

# Create configuration directory
echo "📁 Creating configuration directory"
mkdir -p /etc/etail-monitor-controller

# Create sample configuration if it doesn't exist
if [ ! -f "/etc/etail-monitor-controller/managed_monitors.json" ]; then
    echo "📄 Creating sample configuration"
    cat > /etc/etail-monitor-controller/managed_monitors.json << 'EOF'
{
  "managed_services": [
    {
      "name": "ETail Hardware Monitor",
      "type": "service", 
      "service_name": "et-hardware-monitor",
      "executable": "/usr/local/bin/et_hardware_mon_linux",
      "config": {
        "host": "192.168.1.132",
        "port": 21327,
        "password": "your_password_here",
        "refresh_interval": 5,
        "ssl": true
      },
      "pid": null
    }
  ],
  "managed_processes": []
}
EOF
    chmod 644 /etc/etail-monitor-controller/managed_monitors.json
fi

# Create desktop launcher
echo "🖥️ Creating desktop launcher"
cat > /usr/share/applications/etail-monitor-controller.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ETail Monitor Controller
Comment=Manage ETail hardware and log monitors
Exec=etail-monitor-controller
Icon=utilities-system-monitor
Categories=System;Monitor;
Terminal=false
StartupNotify=true
EOF

echo ""
echo "🎉 Installation complete!"
echo "========================"
echo "✅ Executable: /usr/local/bin/etail-monitor-controller"
echo "✅ Configuration: /etc/etail-monitor-controller/managed_monitors.json"
echo "✅ Desktop launcher: /usr/share/applications/etail-monitor-controller.desktop"
echo ""
echo "🚀 Usage:"
echo "   GUI: etail-monitor-controller"
echo "   CLI: etail-monitor-controller --help"
