#!/bin/bash

STATUS_FILE="$HOME/.config/etail-monitor-controller/status.json"
CONFIG_FILE="$HOME/.config/etail-monitor-controller/managed_monitors.json"

get_running_count() {
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo "0"
        return
    fi
    
    jq '[.managed_services[] | select(.status == "active"), 
         .managed_processes[] | select(.status == "running")] | length' "$STATUS_FILE" 2>/dev/null || echo "0"
}

get_total_count() {
    if [[ ! -f "$CONFIG_FILE" ]]; then
        echo "0"
        return
    fi
    
    jq '[.managed_services[], .managed_processes[]] | length' "$CONFIG_FILE" 2>/dev/null || echo "0"
}

get_tooltip() {
    if [[ ! -f "$STATUS_FILE" ]]; then
        echo "No status available"
        return
    fi
    
    jq -r '["<b>Services:</b>"] + 
           (.managed_services[] | 
            if .status == "active" then 
              "  <span color=\"green\">●</span> \(.name) (PID: \(.pid))" 
            else 
              "  <span color=\"red\">●</span> \(.name) (Stopped)" 
            end) + 
           ["","<b>Processes:</b>"] + 
           (.managed_processes[] | 
            if .status == "running" then 
              "  <span color=\"green\">●</span> \(.name) (PID: \(.pid))" 
            else 
              "  <span color=\"red\">●</span> \(.name) (Stopped)" 
            end) | join("\n")' "$STATUS_FILE" 2>/dev/null || echo "Error reading status"
}

RUNNING=$(get_running_count)
TOTAL=$(get_total_count)

# Output for Genmon
echo "ETail: $RUNNING/$TOTAL"
echo "---"
get_tooltip
echo "---"
echo "Right-click to open controller"
