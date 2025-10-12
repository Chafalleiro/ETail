from abc import ABC, abstractmethod

class ETailPlugin(ABC):
    """Base class for all ETail plugins"""
    
    def __init__(self, app):
        self.app = app
        self.name = "Unnamed Plugin"
        self.version = "1.0"
        self.description = "No description provided"
        self.enabled = False
        
    @abstractmethod
    def setup(self):
        """Setup the plugin - called when enabled"""
        pass
        
    @abstractmethod
    def teardown(self):
        """Teardown the plugin - called when disabled"""
        pass
        
    def on_log_line(self, line):
        """Called for each new log line (optional)"""
        pass
        
    def on_filter_match(self, filter_data, line):
        """Called when a filter matches a line (optional)"""
        pass
        
    def get_settings_widget(self, parent):
        """Return a settings widget for this plugin (optional)"""
        return None