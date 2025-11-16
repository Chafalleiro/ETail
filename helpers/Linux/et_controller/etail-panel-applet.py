#!/usr/bin/env python3
import os
import json
import gi
import subprocess
import threading
import time

gi.require_version('Gtk', '3.0')
gi.require_version('AyatanaAppIndicator3', '0.1')
from gi.repository import Gtk, AyatanaAppIndicator3, GObject

class ETailPanelApplet:
    def __init__(self):
        self.app_dir = os.path.expanduser("~/.config/etail-monitor-controller")
        self.status_file = os.path.join(self.app_dir, "status.json")
        
        # Create app indicator
        self.indicator = AyatanaAppIndicator3.Indicator.new(
            "etail-monitor-applet",
            "dialog-information",
            AyatanaAppIndicator3.IndicatorCategory.APPLICATION_STATUS
        )
        self.indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
        
        self.update_display()
        self.create_menu()
        
        # Auto-refresh every 5 seconds
        self.update_thread = threading.Thread(target=self.auto_refresh, daemon=True)
        self.update_thread.start()
    
    def get_status(self):
        try:
            with open(self.status_file, 'r') as f:
                return json.load(f)
        except:
            return {"managed_services": [], "managed_processes": []}
    
    def get_display_info(self):
        status = self.get_status()
        running = 0
        total = 0
        
        # Count services
        services = status.get("managed_services", [])
        total += len(services)
        running += sum(1 for s in services if s.get("status") == "active")
        
        # Count processes
        processes = status.get("managed_processes", [])
        total += len(processes)
        running += sum(1 for p in processes if p.get("status") == "running")
        
        return running, total
    
    def update_display(self):
        running, total = self.get_display_info()
        
        # Set icon based on status
        if total == 0:
            icon = "dialog-warning"
            label = "ETail: No config"
        elif running == total:
            icon = "emblem-default"
            label = f"ETail: {running}/{total}"
        elif running == 0:
            icon = "dialog-error"
            label = f"ETail: {running}/{total}"
        else:
            icon = "dialog-warning"
            label = f"ETail: {running}/{total}"
        
        self.indicator.set_icon(icon)
        self.indicator.set_label(label, "")
    
    def create_menu(self):
        menu = Gtk.Menu()
        
        # Status header
        running, total = self.get_display_info()
        status_item = Gtk.MenuItem(label=f"Status: {running}/{total} running")
        status_item.set_sensitive(False)
        menu.append(status_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        # Open Controller
        controller_item = Gtk.MenuItem(label="Open Controller")
        controller_item.connect("activate", self.launch_controller)
        menu.append(controller_item)
        
        # Refresh
        refresh_item = Gtk.MenuItem(label="Refresh")
        refresh_item.connect("activate", lambda x: self.update_display())
        menu.append(refresh_item)
        
        menu.append(Gtk.SeparatorMenuItem())
        
        # Exit
        exit_item = Gtk.MenuItem(label="Exit")
        exit_item.connect("activate", Gtk.main_quit)
        menu.append(exit_item)
        
        menu.show_all()
        self.indicator.set_menu(menu)
    
    def launch_controller(self, widget=None):
        subprocess.Popen(["/usr/local/bin/etail-monitor-controller"])
    
    def auto_refresh(self):
        while True:
            time.sleep(5)
            GObject.idle_add(self.update_display)

def main():
    Gtk.init([])
    applet = ETailPanelApplet()
    Gtk.main()

if __name__ == "__main__":
    main()
