#!/bin/bash

echo "🔍 Verifying ETail Monitor Controller Installation"
echo "================================================="

echo ""
echo "📦 Checking executable:"
if [ -f "/usr/local/bin/etail-monitor-controller" ]; then
    echo "✅ Executable found"
    /usr/local/bin/etail-monitor-controller --version
else
    echo "❌ Executable not found"
fi

echo ""
echo "📁 Checking configuration:"
if [ -f "/etc/etail-monitor-controller/managed_monitors.json" ]; then
    echo "✅ Configuration found"
    ls -la /etc/etail-monitor-controller/
else
    echo "❌ Configuration not found"
fi

echo ""
echo "🖥️ Checking desktop launcher:"
if [ -f "/usr/share/applications/etail-monitor-controller.desktop" ]; then
    echo "✅ Desktop launcher found"
else
    echo "❌ Desktop launcher not found"
fi

echo ""
echo "🐍 Checking dependencies:"
echo "The compiled executable should have no Python dependencies:"
ldd /usr/local/bin/etail-monitor-controller 2>/dev/null | grep -i python && echo "❌ Python dependencies found" || echo "✅ No Python dependencies"

echo ""
echo "🚀 Testing launch:"
timeout 2 /usr/local/bin/etail-monitor-controller --version && echo "✅ Launch test passed" || echo "⚠️  Launch may have issues"
