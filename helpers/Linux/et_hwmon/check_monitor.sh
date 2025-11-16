#!/bin/bash

# check_monitor.sh
# Quick status check for the hardware monitor

SERVICE_NAME="et-hardware-monitor"

echo "🔍 Hardware Monitor Status Check"
echo "======================================"

# Check service status
echo "📊 Service Status:"
systemctl status $SERVICE_NAME --no-pager -l

echo ""
echo "📜 Recent Logs:"
journalctl -u $SERVICE_NAME -n 10 --no-pager

echo ""
echo "🌡️  Sensor Check:"
if command -v sensors &> /dev/null; then
    sensors | head -10
else
    echo "lm-sensors not installed"
fi
