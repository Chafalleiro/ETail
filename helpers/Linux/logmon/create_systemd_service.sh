# create_systemd_service.sh
#!/bin/bash

# create_systemd_service.sh
# Creates a systemd service file for the Linux log client

SERVICE_NAME="linux-log-monitor"
EXECUTABLE_PATH="/usr/local/bin/LinuxLogMonitor"
CONFIG_FILE="/etc/linux-log-monitor.conf"

echo "Creating systemd service for Linux Log Monitor..."

# Create config directory
sudo mkdir -p /etc

# Create service file
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null << EOF
[Unit]
Description=Linux Log Monitor Client
After=network.target

[Service]
Type=simple
User=root
ExecStart=${EXECUTABLE_PATH} --config ${CONFIG_FILE}
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Create example config file
sudo tee ${CONFIG_FILE}.example > /dev/null << EOF
# Linux Log Monitor Configuration
# Copy this file to ${CONFIG_FILE} and adjust settings

# Server settings
host=your-server-ip
port=21327
password=your-password

# Log files to monitor (space separated)
log-files=/var/log/syslog /var/log/auth.log /var/log/kern.log

# Monitoring settings
poll-interval=1
tail-lines=50
encoding=utf-8
use-ssl=true

# Privilege settings
# drop-privileges=false
# run-as-user=nobody
EOF

echo "✅ Created systemd service: ${SERVICE_NAME}.service"
echo "📝 Example config created: ${CONFIG_FILE}.example"
echo ""
echo "To set up:"
echo "1. Copy the executable to ${EXECUTABLE_PATH}"
echo "2. Copy ${CONFIG_FILE}.example to ${CONFIG_FILE}"
echo "3. Edit ${CONFIG_FILE} with your settings"
echo "4. Run: sudo systemctl daemon-reload"
echo "5. Run: sudo systemctl enable ${SERVICE_NAME}"
echo "6. Run: sudo systemctl start ${SERVICE_NAME}"
