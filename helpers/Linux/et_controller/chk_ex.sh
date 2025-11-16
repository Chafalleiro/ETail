#!/bin/bash

echo "🔧 Checking ETail Executables"
echo "============================="

echo ""
echo "📁 Checking executable paths and permissions:"

check_executable() {
    local path=$1
    local name=$2
    
    echo ""
    echo "🔍 Checking: $name"
    echo "Path: $path"
    
    if [ -f "$path" ]; then
        echo "✅ File exists"
        if [ -x "$path" ]; then
            echo "✅ File is executable"
            echo "📊 File info:"
            ls -la "$path"
            echo "🔍 File type:"
            file "$path"
        else
            echo "❌ File is NOT executable"
            echo "💡 Try: chmod +x '$path'"
        fi
    else
        echo "❌ File does NOT exist"
        echo "💡 Check the installation path"
    fi
}

echo ""
check_executable "/usr/local/bin/et_hardware_mon_linux" "ETail Hardware Monitor"
check_executable "/usr/local/bin/LinuxLogMonitor" "ETail Log Monitor"

echo ""
echo "🧪 Testing direct execution:"
echo "Hardware Monitor:"
/usr/local/bin/et_hardware_mon_linux --help 2>&1 | head -3 || echo "❌ Failed to execute"

echo "Log Monitor:"
/usr/local/bin/LinuxLogMonitor --help 2>&1 | head -3 || echo "❌ Failed to execute"

echo ""
echo "📋 Current running processes:"
pgrep -fa "et_hardware_mon_linux" && echo "✅ Hardware monitor running" || echo "❌ Hardware monitor not running"
pgrep -fa "LinuxLogMonitor" && echo "✅ Log monitor running" || echo "❌ Log monitor not running"
