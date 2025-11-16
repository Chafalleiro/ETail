#!/usr/bin/env python3
import os
import json
import gi
import subprocess

gi.require_version('Gtk', '3.0')
gi.require_version('Notify', '0.7')
from gi.repository import Gtk, Gdk, Notify

class ETailWidget:
    def __init__(self):
        self.app_dir = os.path.expanduser("~/.config/etail-monitor-controller")
        self.status_file = os.path.join(self.app_dir, "status.json")
        self.config_file = os.path.join(self.app_dir, "managed_monitors.json")
        Notify.init("ETail Monitor Widget")
        
    def get_status(self):
        """Read current status from status file"""
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"managed_services": [], "managed_processes": []}
    
    def get_config(self):
        """Read configuration to get total expected processes"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                total_services = len(config.get("managed_services", []))
                total_processes = len(config.get("managed_processes", []))
                return total_services + total_processes
        except (FileNotFoundError, json.JSONDecodeError):
            return 0
    
    def get_running_count(self):
        """Count running processes and services"""
        status = self.get_status()
        running = 0
        
        for service in status.get("managed_services", []):
            if service.get("status") == "active":
                running += 1
        
        for process in status.get("managed_processes", []):
            if process.get("status") == "running":
                running += 1
                
        return running
    
    def get_display_text(self):
        """Generate text for panel display"""
        running = self.get_running_count()
        total = self.get_config()
        
        if total == 0:
            return "ETail: 0/0"
        
        return f"ETail: {running}/{total}"
    
    def get_tooltip_markup(self):
        """Generate detailed tooltip with colored status"""
        status = self.get_status()
        tooltip_lines = []
        
        # Services section
        if status.get("managed_services"):
            tooltip_lines.append("<b>Services:</b>")
            for service in status["managed_services"]:
                name = service.get("name", "Unknown")
                status_text = service.get("status", "unknown")
                pid = service.get("pid", "N/A")
                
                if status_text == "active":
                    tooltip_lines.append(f"  <span foreground='green'>●</span> {name} (PID: {pid})")
                else:
                    tooltip_lines.append(f"  <span foreground='red'>●</span> {name} (Stopped)")
            tooltip_lines.append("")
        
        # Processes section  
        if status.get("managed_processes"):
            tooltip_lines.append("<b>Processes:</b>")
            for process in status["managed_processes"]:
                name = process.get("name", "Unknown")
                status_text = process.get("status", "unknown")
                pid = process.get("pid", "N/A")
                
                if status_text == "running":
                    tooltip_lines.append(f"  <span foreground='green'>●</span> {name} (PID: {pid})")
                else:
                    tooltip_lines.append(f"  <span foreground='red'>●</span> {name} (Stopped)")
        
        if not tooltip_lines:
            tooltip_lines.append("No managed services or processes configured")
            
        return "\n".join(tooltip_lines)
    
    def show_notification(self, title, message):
        """Show desktop notification"""
        notification = Notify.Notification.new(title, message)
        notification.show()
    
    def launch_controller(self):
        """Launch the main controller application"""
        try:
            subprocess.Popen(["/usr/local/bin/etail-monitor-controller"])
            self.show_notification("ETail Monitor", "Controller launched")
        except Exception as e:
            self.show_notification("ETail Monitor Error", f"Failed to launch controller: {e}")
    
    def create_context_menu(self, event_button, event_time):
        """Create right-click context menu"""
        menu = Gtk.Menu()
        
        # Open Controller
        item_controller = Gtk.MenuItem(label="Open Controller")
        item_controller.connect("activate", lambda x: self.launch_controller())
        menu.append(item_controller)
        
        # Refresh
        item_refresh = Gtk.MenuItem(label="Refresh Status")
        item_refresh.connect("activate", lambda x: self.update_display())
        menu.append(item_refresh)
        
        # Separator
        menu.append(Gtk.SeparatorMenuItem())
        
        # Exit
        item_exit = Gtk.MenuItem(label="Exit Widget")
        item_exit.connect("activate", Gtk.main_quit)
        menu.append(item_exit)
        
        menu.show_all()
        menu.popup_at_pointer(None)  # Use popup_at_pointer instead of deprecated popup

def main():
    widget = ETailWidget()
    
    # For Genmon plugin, we just output the text
    print(widget.get_display_text())
    print(widget.get_tooltip_markup())

if __name__ == "__main__":
    main()
