from etail_plugin import ETailPlugin
import tkinter as tk
from tkinter import ttk

class SamplePlugin(ETailPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.name = "Sample Plugin"
        self.version = "1.0"
        self.description = "A sample plugin that demonstrates plugin functionality"
        self.match_count = 0
        
    def setup(self):
        """Setup the plugin"""
        self.match_count = 0
        self.app.messages(2, 9, "Sample plugin enabled")
        
    def teardown(self):
        """Teardown the plugin"""
        self.app.messages(2, 9, f"Sample plugin disabled. Total matches: {self.match_count}")
        
    def on_log_line(self, line):
        """Process each log line"""
        if "error" in line.lower():
            pass
            
    def on_filter_match(self, filter_data, line):
        """Count filter matches"""
        self.match_count += 1
        print(f"SamplePlugin: Filter match #{self.match_count}: {filter_data['pattern']}")
        
    def get_settings_widget(self, parent):
        """Create settings widget"""
        def create_widget(master):
            frame = ttk.Frame(master, padding=10)
            ttk.Label(frame, text="Sample Plugin Settings").pack(anchor=tk.W)
            ttk.Label(frame, text=f"Total matches counted: {self.match_count}").pack(anchor=tk.W, pady=(10, 5))
            ttk.Button(frame, text="Reset Counter", command=lambda: self.reset_counter()).pack(pady=5)
            return frame
        return create_widget
        
    def reset_counter(self):
        """Reset the match counter"""
        self.match_count = 0
        self.app.messages(2, 9, "Sample plugin counter reset")