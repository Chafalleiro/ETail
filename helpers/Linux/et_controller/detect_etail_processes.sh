#!/bin/bash

# analyze_process_trees.sh
# Detailed analysis of ETail process trees

echo "🌳 ETail Process Tree Analysis"
echo "=============================="

analyze_tree() {
    local pattern=$1
    local name=$2
    
    echo ""
    echo "🔍 Analyzing: $name"
    echo "========================"
    
    # Get all PIDs for this pattern
    pids=$(pgrep -f "$pattern")
    
    if [ -z "$pids" ]; then
        echo "❌ No processes found for: $pattern"
        return
    fi
    
    echo "📊 Found PIDs: $pids"
    
    # Analyze each PID's process tree
    for pid in $pids; do
        echo ""
        echo "🆔 Process Tree for PID: $pid"
        echo "------------------------"
        
        # Get process information
        echo "📝 Process Info:"
        ps -p $pid -o pid,ppid,user,comm,cmd --no-headers 2>/dev/null
        
        # Get full process tree
        echo "🌳 Full Process Tree:"
        pstree -p $pid
        
        # Get children
        echo "👶 Direct Children:"
        ps --ppid $pid -o pid,comm,cmd --no-headers 2>/dev/null
        
        echo "📈 Memory Usage:"
        ps -p $pid -o pid,rss,pmem,comm --no-headers 2>/dev/null
    done
    
    # Check for duplicate command lines
    echo ""
    echo "🔎 Checking for duplicates:"
    ps aux | grep "$pattern" | grep -v grep | awk '{ $1=$2=$3=$4=$5=$6=$7=$8=$9=""; print }' | sort | uniq -c | while read count command; do
        if [ $count -gt 1 ]; then
            echo "🚨 DUPLICATE: $count instances - $command"
        fi
    done
}

echo ""
analyze_tree "et_hardware_mon_linux" "ETail Hardware Monitor"

echo ""
analyze_tree "LinuxLogMonitor" "ETail Log Monitor"

echo ""
echo "🎯 Summary of all ETail process trees:"
echo "======================================"
pstree -p | grep -E "(et_hardware_mon_linux|LinuxLogMonitor)" || echo "No ETail processes found"
