import sys
from pathlib import Path

# Import the ETailPlugin class
try:
    from plugins.etail_plugin import ETailPlugin
except ImportError:
    # Fallback: define it here if not found
    from abc import ABC, abstractmethod
    class ETailPlugin(ABC):
        def __init__(self, app):
            self.app = app
            self.name = "Unnamed Plugin"
            self.version = "1.0" 
            self.description = "No description provided"
            self.enabled = False
            
        @abstractmethod
        def setup(self): pass
            
        @abstractmethod 
        def teardown(self): pass

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from tkinter.colorchooser import askcolor
import os
import chardet
import threading
from threading import Thread, Event
import time
import re
import json
import pygame
import pyttsx3
import importlib
import inspect
try:
    from plyer import notification
    HAS_SYSTEM_NOTIFICATIONS = True
    print("Plyer available for system notifications")
except ImportError:
    HAS_SYSTEM_NOTIFICATIONS = False
    print("Plyer not available for system notifications")

from abc import ABC, abstractmethod

"""A Tuple of fixed messages coded by index.
Set as global to be used anywhere.
index   string
0       Running
1       Stopped
2       Ready
3       Error
4       Paused
5       Detected file encoding:
6       Filter added.
7       Filter removed.
8       Index out of bonds.
9       Sucess.
"""
mssgs = ("Running",
"Stopped",
"Ready",
"Error",
"Paused",
"Detected file encoding: ",
"Filter added.",
"Filter removed.",
"Index out of bonds.",
"Success")

# ****************************************************************************
# *************************** Plugin Manager ********************************
# ****************************************************************************

# Plugin Manager
class PluginManager:
    def __init__(self, app):
        self.app = app
        self.plugins = {}
        self.loaded_plugins = {}
        # Get directory where your main script is located
        if getattr(sys, 'frozen', False):
            # If application is bundled (e.g., PyInstaller)
            app_dir = Path(sys.executable).parent
        else:
            # If running from script
            app_dir = Path(__file__).parent

        self.plugins_dir = app_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
    def discover_plugins(self):
        """Discover available plugins using duck typing - FIXED FOR COMPILED PLUGINS"""
        self.plugins.clear()

        print(f"DEBUG: Looking for plugins in: {self.plugins_dir.absolute()}")

        if not self.plugins_dir.exists():
            print(f"DEBUG: Plugin directory doesn't exist: {self.plugins_dir}")
            return

        # Add plugins directory to Python path so imports work
        plugins_path = str(self.plugins_dir.absolute())
        if plugins_path not in sys.path:
            sys.path.insert(0, plugins_path)
            print(f"DEBUG: Added to Python path: {plugins_path}")

        # Look for BOTH .py AND .pyd files
        python_files = list(self.plugins_dir.glob("*.py"))
        compiled_files = list(self.plugins_dir.glob("*.pyd"))
        plugin_files = python_files + compiled_files
    
        print(f"DEBUG: Found {len(python_files)} Python files and {len(compiled_files)} compiled files")
        print(f"DEBUG: All plugin files: {[f.name for f in plugin_files]}")

        for file_path in plugin_files:
            # Skip interface file and __init__ in both source and compiled forms
            if (file_path.name.startswith("_") or 
                file_path.stem == "etail_plugin"):  # This handles both .py and .pyd
                continue

            # Extract the base module name from compiled files
            if file_path.suffix == '.pyd':
                # For compiled files: sample_plugin.cp313-win_amd64.pyd -> sample_plugin
                plugin_name = file_path.name.split('.')[0]  # Take first part before any dots
                print(f"DEBUG: Compiled plugin detected, using base name: {plugin_name}")
            else:
                # For source files: sample_plugin.py -> sample_plugin
                plugin_name = file_path.stem

            print(f"DEBUG: Processing plugin: {plugin_name} from {file_path.name}")

            try:
                # Use import_module for proper import resolution
                module = importlib.import_module(plugin_name)
                print(f"DEBUG: Successfully imported module: {plugin_name}")

                # Find plugin classes using duck typing
                found_class = False
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    # Check if this class looks like a plugin (has required methods)
                    if (hasattr(obj, 'setup') and 
                        hasattr(obj, 'teardown') and 
                        callable(obj.setup) and 
                        callable(obj.teardown) and
                        obj.__module__ == module.__name__):

                        # Create a test instance to verify it has plugin attributes
                        try:
                            test_instance = obj(self.app)
                            if (hasattr(test_instance, 'name') and 
                                hasattr(test_instance, 'version') and 
                                hasattr(test_instance, 'description')):

                                self.plugins[plugin_name] = {
                                    'class': obj,
                                    'module': module,
                                    'file': file_path,
                                    'enabled': False
                                }
                                found_class = True
                                print(f"DEBUG: SUCCESS - Found valid plugin class: {name}")
                                break
                        except Exception as e:
                            print(f"DEBUG: Failed to instantiate {name}: {e}")
                            continue

                if not found_class:
                    print(f"DEBUG: No valid plugin class found in {plugin_name}")

            except Exception as e:
                print(f"DEBUG: ERROR loading {plugin_name}: {e}")
                import traceback
                traceback.print_exc()

        print(f"DEBUG: Total plugins loaded: {len(self.plugins)}")

    def load_plugin(self, plugin_name):
        """Load and enable a plugin - FIXED VERSION"""
        if plugin_name not in self.plugins:
            return False

        try:
            # Get plugin info first
            plugin_info = self.plugins[plugin_name]
            plugin_class = plugin_info['class']  # Define plugin_class BEFORE using it

            # Now safe to use plugin_class in debug print
            print(f"DEBUG: Loading plugin class {plugin_class} for plugin {plugin_name}")

            # Create instance and set up
            plugin_instance = plugin_class(self.app)
            plugin_instance.setup()

            # Update state
            self.loaded_plugins[plugin_name] = plugin_instance
            self.plugins[plugin_name]['enabled'] = True

            self.app.messages(2, 9, f"Plugin loaded: {plugin_name}")
            return True

        except Exception as e:
            self.app.messages(2, 3, f"Error loading plugin {plugin_name}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def unload_plugin(self, plugin_name):
        """Unload and disable a plugin"""
        if plugin_name not in self.loaded_plugins:
            return False
            
        try:
            plugin_instance = self.loaded_plugins[plugin_name]
            plugin_instance.teardown()
            del self.loaded_plugins[plugin_name]
            self.plugins[plugin_name]['enabled'] = False
            self.app.messages(2, 9, f"Plugin unloaded: {plugin_name}")
            return True
            
        except Exception as e:
            self.app.messages(2, 3, f"Error unloading plugin {plugin_name}: {e}")
            return False
    
    def call_plugin_method(self, method_name, *args, **kwargs):
        """Call a method on all loaded plugins"""
        results = []
        for plugin_name, plugin in self.loaded_plugins.items():
            try:
                method = getattr(plugin, method_name, None)
                if method and callable(method):
                    result = method(*args, **kwargs)
                    results.append((plugin_name, result))
            except Exception as e:
                print(f"Error calling {method_name} on {plugin_name}: {e}")
        return results

# ****************************************************************************
# *************************** Collapsible frame******************************
# ****************************************************************************

class CollapsibleFrame(ttk.Frame):
    def __init__(self, parent, text="", *args, **kwargs):
        ttk.Frame.__init__(self, parent, *args, **kwargs)
        
        self.is_expanded = True
        self.text = text
        
        # Create header frame with better styling
        self.header_frame = ttk.Frame(self, relief="raised", borderwidth=1)
        self.header_frame.pack(fill=tk.X, pady=(0, 0))
        
        # Toggle button with better styling
        self.toggle_btn = ttk.Button(
            self.header_frame, 
            text=f"▼ {text}",
            command=self.toggle,
            style="Accordion.TButton"
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=5, pady=2)
        
        # Content frame
        self.content_frame = ttk.Frame(self, relief="sunken", borderwidth=1)
        if self.is_expanded:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0), padx=2)
    
    def toggle(self):
        """Toggle the visibility of the content"""
        if self.is_expanded:
            self.content_frame.pack_forget()
            self.toggle_btn.config(text=f"► {self.text}")
        else:
            self.content_frame.pack(fill=tk.BOTH, expand=True, pady=(2, 0), padx=2)
            self.toggle_btn.config(text=f"▼ {self.text}")
        
        self.is_expanded = not self.is_expanded
    
    def get_content_frame(self):
        """Get the content frame to add widgets"""
        return self.content_frame

# ****************************************************************************
# *************************** Config******************************************
# ****************************************************************************
class ConfigManager:
    def __init__(self, config_file="~/.etail/config.json"):
        self.config_file = Path(config_file).expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)

        # File to track last used configuration
        self.last_config_tracker = self.config_file.parent / "last_config.txt"
        
        self.config = self.load_default_config()
        
        # Try to load last used config, fall back to default
        self.load_last_configuration()
        
    def __getitem__(self, key):
        """Allow dictionary-style access: config_manager['log_file']"""
        return self.config.get(key)

    def __setitem__(self, key, value):
        """Allow dictionary-style assignment: config_manager['log_file'] = 'path'"""
        self.config[key] = value

    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value

    def get_last_config_path(self):
        """Get the path of the last used configuration file"""
        try:
            if self.last_config_tracker.exists():
                with open(self.last_config_tracker, 'r', encoding='utf-8') as f:
                    last_config_path = f.read().strip()
                    if last_config_path and Path(last_config_path).exists():
                        return last_config_path
            return None
        except Exception as e:
            print(f"Error reading last config tracker: {e}")
            return None
    
    def set_last_config_path(self, config_path):
        """Update the last configuration file path"""
        try:
            with open(self.last_config_tracker, 'w', encoding='utf-8') as f:
                f.write(str(config_path))
            return True
        except Exception as e:
            print(f"Error setting last config path: {e}")
            return False
    
    def load_last_configuration(self):
        """Load the last used configuration file"""
        last_config_path = self.get_last_config_path()

        if last_config_path:
            try:
                print(f"Loading last configuration: {last_config_path}")
                with open(last_config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    self.config_file = Path(last_config_path)  # Update current config file
                print("Last configuration loaded successfully")
                return True
            except Exception as e:
                print(f"Error loading last configuration: {e}, falling back to defaults")
                # Fall back to default config file
                self.load_default_config_file()
        else:
            # No last config, try to load default config file
            self.load_default_config_file()
        
        return False
    
    def load_default_config_file(self):
        """Load the default configuration file if it exists"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                print("Default configuration loaded successfully")
                return True
        except Exception as e:
            print(f"Error loading default config: {e}")
        
        return False
   
    def load_default_config(self):
        """Return default configuration values"""
        return {
            "log_file": "",
            "initial_lines": 50,
            "refresh_interval": 100,
            "auto_load_config": True,
            "last_directory": str(Path.home()),
            "filters_file": "",
            "advanced_filters_file": "",
            "recent_filters": [],
            "recent_advanced_filters": []
        }
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # Update default config with loaded values
                    self.config.update(loaded_config)
                    print(f"Configuration loaded successfully")
            else:
                print(f"Default configuration loaded successfully")
        except Exception as e:
            print(f"Error loading config:, {e} using defaults")
    
    def save_config(self, config_path=None):
        """Save current configuration to file and update last config tracker"""
        try:
            # Use provided path or current config file
            save_path = Path(config_path) if config_path else self.config_file
            
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # Update the last config tracker
            self.set_last_config_path(save_path)
            
            # Update current config file reference
            self.config_file = save_path
            
            print(f"Configuration saved to: {save_path}")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    #Update a recent files list, maintaining max entries
    def update_recent_list(self, list_name, file_path, max_entries=5):
        if file_path and os.path.exists(file_path):
            if list_name not in self.config:
                self.config[list_name] = []
            
            # Remove if already exists
            if file_path in self.config[list_name]:
                self.config[list_name].remove(file_path)
            
            # Add to beginning
            self.config[list_name].insert(0, file_path)
            
            # Trim to max entries
            self.config[list_name] = self.config[list_name][:max_entries]

    def get_default_filters_path(self):
        """Get the path for the default filters file"""
        return self.config_file.parent / "default_filters.json"
    
    def should_auto_load_filters(self):
        """Check if we should auto-load filters based on config"""
        return self.get("auto_load_config", True)
    
    def set_auto_load_filters(self, value):
        """Set whether to auto-load filters on startup"""
        self.set("auto_load_filters", value)

# ****************************************************************************
# *************************** Action Handler *********************************
# ****************************************************************************
class ActionHandler:
    def __init__(self, root):
        self.root = root
        self.tts_engine = None
        self.pygame_initialized = False
        self.init_tts()
        self.init_sound()
    
    def init_tts(self):
        """Initialize text-to-speech engine with better error handling"""
        try:
            self.tts_engine = pyttsx3.init()
            if self.tts_engine:
                # Set speech properties
                self.tts_engine.setProperty('rate', 150)
                self.tts_engine.setProperty('volume', 0.8)
            else:
                print("TTS engine initialization returned None")
        except Exception as e:
            print(f"TTS initialization failed: {e}")
            self.tts_engine = None

    def get_available_voices(self):
        """Get available voices from pyttsx3 and return formatted list"""
        #"HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech_OneCore\\Voices\\Tokens\\MSTTS_V110_enGB_SusanM" not listed
        try:
            if not self.tts_engine:
                print(f"Error init the engine:")
                self.init_tts()
            voices = self.tts_engine.getProperty('voices')
            if not voices:
                self.messages(2, 3, "No TTS voices available")

            voice_list = []
            for i, voice in enumerate(voices):
                # Extract voice name - format varies by platform
                try:
                    voice_name = voice.name
                except AttributeError:
                    voice_name = f"Voice {i+1}"

                voice_info = {
                    'id': voice.id,
                    'name': voice_name,
                    'index': i
                }
                voice_list.append(voice_info)     
            return voice_list
        except Exception as e:
            print(f"Error getting voices: {e}")
            return []

    def init_sound(self):
        """Initialize pygame mixer for sound playback"""
        try:
            pygame.mixer.init()
            self.pygame_initialized = True
        except Exception as e:
            print(f"Sound initialization failed: {e}")
            self.pygame_initialized = False
    
    def execute_action(self, action, modifier, line_content=""):
        """Execute the specified action with the modifier"""
        try:
            if action == "sound" and modifier:
                self.play_sound(modifier)
            elif action == "tts":
                self.speak_text(modifier[0],modifier[1])
            elif action == "skip":
                return True  # Signal to skip this line
            elif action == "notification" and modifier:
                self.show_notification(modifier)
            elif action == "dialog" and modifier:
                self.show_dialog(modifier)
            return False
        except Exception as e:
            print(f"Action execution error: {e}")
            return False
    
    def play_sound(self, sound_file):
        """Play a sound file in a separate thread"""
        def _play_sound():
            try:
                if self.pygame_initialized and os.path.exists(sound_file):
                    pygame.mixer.music.load(sound_file)
                    pygame.mixer.music.play()
                else:
                    print(f"Sound file not found or sound system not available: {sound_file}")
            except Exception as e:
                print(f"Error playing sound: {e}")
        
        sound_thread = threading.Thread(target=_play_sound, daemon=True)
        sound_thread.start()
    
    def speak_text(self, text, voice):
        """Speak text using TTS in a separate thread"""
        def _speak():
            try:
                if self.tts_engine:
                    self.tts_engine.startLoop(False)
                    if self.tts_engine._inLoop:
                        self.tts_engine.endLoop()
                    self.tts_engine.setProperty('voice', voice)
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e} filter: {text}")
        tts_thread = threading.Thread(target=_speak, daemon=True)
        tts_thread.start()
    
# Update the ActionHandler.show_notification method:
    def show_notification(self, message):
        """Show a system notification using plyer"""
        try:
            if HAS_SYSTEM_NOTIFICATIONS:
                notification.notify(
                    title="ETail Alert",
                    message=message,
                    timeout=10,  # seconds
                    app_name="ETail Log Monitor"
                )
            else:
                # Fallback to tkinter messagebox
                self.root.after(0, lambda: messagebox.showinfo("ETail Notification", message))
        except Exception as e:
            print(f"Etail Says - System notification failed: {e}")
            # Fallback
            self.root.after(0, lambda: messagebox.showinfo("ETail Notification", message))
    
    def show_dialog(self, message):
        """Show a dialog window"""
        self.root.after(0, lambda: messagebox.showwarning("ETail Alert", message))

# ****************************************************************************
# *************************** Inits*******************************************
# ****************************************************************************

class LogTailApp:
    def __init__(self, root):
        self.root = root
        icon_path = self.resource_path("Etail.ico")
        self.root.wm_iconbitmap(icon_path)
        self.root.title("Etail 0.2")
        #root.iconbitmap('Etail.ico')
        root.minsize(900, 100)
        
        # Apply modern styling first
        self.setup_styling()

        # Initialize configuration manager
        self.config_manager = ConfigManager()
        # Initialize Action manager
        self.action_handler = ActionHandler(root)

        # Control variables
        self.stop_event = Event()
        self.tail_thread = None
        self.last_position = 0  # Track file position
        self.filters = {}

        # Regex builder components
        self.regex_fields = []  # Store field widgets
        self.regex_operators = []  # Store operator widgets between fields
        self.max_fields = 10
               
        # Filter editing state
        self.editing_filter_key = None  # Track which filter we're editing
        self.original_filter_key = None  # Store original key in case pattern changes

        self.advanced_filters = {}
        self.editing_advanced_filter_key = None

        # Predefined regex patterns
        self.predefined_patterns = {
            "Date (YYYY-MM-DD)": r"\d{4}-\d{2}-\d{2}",
            "Date (MM/DD/YYYY)": r"\d{2}/\d{2}/\d{4}",
            "Time (HH:MM:SS)": r"\d{2}:\d{2}:\d{2}",
            "IPv4 Address": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "IPv6 Address": r"\b(?:[A-F0-9]{1,4}:){7}[A-F0-9]{1,4}\b",
            "Email Address": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "Phone Number": r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",
            "URL": r"https?://[^\s]+",
            "Hex Color": r"#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})\b",
            "MAC Address": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
            "Credit Card": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
            "UUID": r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            "Log Level": r"\b(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL|FATAL)\b",
            "Number": r"\b\d+\b",
            "Word": r"\b\w+\b"
        }

        self.detect_encoding = self.simple_encoding_detect
        self.create_widgets()
        self.messages(2,2,"test")
        
        # Auto-load if enabled
        if self.config_manager.get("auto_load_config", True):
            self.load_configuration()
            # Auto-load simple filters
            self.auto_load_filters()

        # Initialize plugin manager AFTER everything else is set up
        self.plugin_manager = None
        self.root.after(100, self.initialize_plugin_system)  # Delay plugin init

    def initialize_plugin_system(self):
        """Initialize plugin system after main UI is loaded"""
        try:
            self.plugin_manager = PluginManager(self)
            self.messages(2, 9, "Plugin system initialized")
        except Exception as e:
            self.messages(2, 3, f"Plugin system failed: {e}")

    def resource_path(self, relative_path):
        """Get absolute path to resource, works for dev and for PyInstaller"""
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def auto_load_filters(self):
        """Automatically load filters file if it exists and auto-load is enabled"""
        try:
            # Auto-load simple filters
            filters_path = Path(self.config_manager.get("filters_file", ""))
            if (self.config_manager.should_auto_load_filters() and 
                filters_path.exists()):
            
                self.messages(2, 2, f"Auto-loading filters from {filters_path}")
                self.filters_file_var.set(str(filters_path))
                self.load_filters()
        
            # AUTO-LOAD ADVANCED FILTERS - NEW
            advanced_filters_path = Path(self.config_manager.get("advanced_filters_file", ""))
            if (self.config_manager.should_auto_load_filters() and 
                advanced_filters_path.exists()):
            
                self.messages(2, 2, f"Auto-loading advanced filters from {advanced_filters_path}")
                self.advanced_filters_file_var.set(str(advanced_filters_path))
                self.load_advanced_filters_auto()
            
        except Exception as e:
            self.messages(2, 3, f"Error auto-loading filters: {e}")    

    def load_filters(self):
        """Load filters from the configured filters file (auto-load version)"""
        filters_file = self.filters_file_var.get()
        if not filters_file or not os.path.exists(filters_file):
            # Don't show error for auto-load - it's normal for file not to exist initially
            return
    
        try:
            with open(filters_file, 'r', encoding='utf-8') as f:
                filters_data = json.load(f)
        
        # Clear current filters
            self.filters.clear()
            self.filter_listbox.delete(0, tk.END)
        
            # Load new filters
            for filter_data in filters_data.get("filters", []):
                filter_key = f"{filter_data['pattern']}|{filter_data['action']}|{filter_data.get('action_modifier', '')}"
                self.filters[filter_key] = filter_data
            
                # Add to listbox
                action_display = filter_data['action'] if filter_data['action'] != "none" else "color only"
                modifier_display = f" ({filter_data['action_modifier']})" if filter_data.get('action_modifier') else ""
                display_text = f"{filter_data['pattern']} → {action_display}{modifier_display}"
                self.filter_listbox.insert(tk.END, display_text)
            
                # Configure text tag
                self.log_text.tag_configure(filter_key, 
                                      foreground=filter_data['fg_color'], 
                                      background=filter_data['bg_color'])
        
            # Update recent filters list
            self.config_manager.update_recent_list("recent_filters", filters_file)
            self.update_recent_combos()
        
            self.messages(2, 9, f"Loaded {len(self.filters)} filters automatically")
        
        except Exception as e:
            # Silent fail for auto-load - don't bother user with errors on startup
            print(f"Auto-load filters error: {e}")

    def save_filters_default(self):
        """Save current filters to the default filters file"""
        try:
            default_filters_path = self.config_manager.get_default_filters_path()
        
            filters_data = {
                "version": "1.1",
                "filters": list(self.filters.values())
            }
        
            with open(default_filters_path, 'w', encoding='utf-8') as f:
                json.dump(filters_data, f, indent=2, ensure_ascii=False)
        
            self.messages(2, 9, f"Filters saved to default location: {default_filters_path}")
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving default filters: {e}")
            return False

    def save_json(self, what_to_save, file_to_save, list_to_save, dialog):

        """Save current filters to the configured filters file"""
        file_types = [
            ('JSON files', '*.json'),
            ('All Files', '*.*')
        ]

        # Get current directory from config manager if available
        initial_dir = self.config_manager.get("last_directory", "")

        if dialog:
            # Open save file dialog
            file_to_save = filedialog.asksaveasfilename(
                title="Save Configuration As",
                defaultextension=".json",
                filetypes=file_types,
                initialdir=initial_dir,
            )

        try:
            with open(file_to_save, 'w', encoding='utf-8') as f:
                json.dump(list_to_save, f, indent=2, ensure_ascii=False)

            # Update recent filters list
            match what_to_save:
                case "simple":
                    self.config_manager.update_recent_list("recent_filters", file_to_save)
                    self.filters_file_var.set(Path(file_to_save))
                case "advanced":
                    self.config_manager.update_recent_list("recent_advanced_filters", file_to_save)
                    self.advanced_filters_file_var.set(Path(file_to_save))

            self.update_recent_combos()
            self.messages(2, 9, "Filters saved successfully")
            
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving filters: {e}")
            return False

    def setup_styling(self):
        """Setup modern styling and themes"""
        self.style = ttk.Style()
        # Try to use a modern theme, fall back to default if not available
        available_themes = self.style.theme_names()
        preferred_themes = ['classic', 'alt', 'xpnative', 'winnative', 'alt', 'clam', 'vista', 'default']
        
        for theme in preferred_themes:
            if theme in available_themes:
                self.style.theme_use(theme)
                break
        else:
            self.style.theme_use(available_themes[0] if available_themes else 'default')

        # Configure custom styles
        self.configure_styles()

    def configure_styles(self):
        """Configure custom widget styles"""
        # Colors for a modern look
        self.primary_color = "#2c3e50"
        self.secondary_color = "#3498db"
        self.success_color = "#27ae60"
        self.warning_color = "#f39c12"
        self.danger_color = "#e74c3c"
        self.light_bg = "#ecf0f1"
        self.dark_bg = "#34495e"
        self.dsbld_clr = "#c0c0c0"
        
        # Configure frame styles
        self.style.configure('Primary.TFrame', background=self.light_bg)
        self.style.configure('Secondary.TFrame', background=self.dark_bg)
        
        # Configure label styles
        self.style.configure('Title.TLabel', 
                           font=('Arial', 12, 'bold'),
                           foreground=self.primary_color)
        self.style.configure('Subtitle.TLabel',
                           font=('Arial', 10, 'bold'),
                           foreground=self.secondary_color)
        self.style.configure('Success.TLabel',
                           foreground=self.success_color)
        self.style.configure('Warning.TLabel',
                           foreground=self.warning_color)
        self.style.configure('Error.TLabel',
                           foreground=self.danger_color)
        
        # Configure button styles
        self.style.configure('Primary.TButton',
                           font=('Arial', 9, 'bold'),
                           foreground='white',
                           background=self.secondary_color,
                           focuscolor=self.style.configure('.')['background'])
        
        self.style.map('Primary.TButton',
                      background=[('active', self.primary_color), ('pressed', self.primary_color), ('disabled', self.dsbld_clr)],
                      foreground= [('active', 'white'), ('pressed', 'white'), ('disabled', self.dsbld_clr)]
                      )
        
        self.style.configure('Success.TButton',
                           background=self.success_color,
                           foreground='white'
                           )
        
        self.style.configure('Danger.TButton',
                           background=self.danger_color,
                           foreground='white'
                           )
        
        # Configure notebook style
        self.style.configure('Custom.TNotebook', 
                           background=self.light_bg,
                           tabmargins=[2, 5, 2, 0])
        
        self.style.configure('Custom.TNotebook.Tab',
                           padding=[15, 5],
                           font=('Arial', 9, 'bold'),
                           background=self.light_bg,
                           foreground=self.primary_color)
        
        self.style.map('Custom.TNotebook.Tab',
                      background=[('selected', self.secondary_color), ('active', self.secondary_color)],
                      foreground=[('selected', self.primary_color), ('active', self.primary_color)]
                      )
        
        # Configure labelframe styles
        self.style.configure('Custom.TLabelframe',
                           background=self.light_bg,
                           relief='solid',
                           borderwidth=1)
        
        self.style.configure('Custom.TLabelframe.Label',
                           font=('Arial', 9, 'bold'),
                           foreground=self.primary_color,
                           background=self.light_bg)
        
        # Configure entry styles
        self.style.configure('Modern.TEntry',
                           fieldbackground='white',
                           borderwidth=1,
                           relief='solid')
        
        # Configure combobox styles
        self.style.configure('Modern.TCombobox',
                           fieldbackground='white',
                           background='white')
        
        # Status indicators
        self.style.configure('Status.Running.TLabel',
                           foreground=self.success_color,
                           font=('Arial', 9, 'bold'))
        
        self.style.configure('Status.Stopped.TLabel',
                           foreground=self.danger_color,
                           font=('Arial', 9, 'bold'))
        
        self.style.configure('Status.Paused.TLabel',
                           foreground=self.warning_color,
                           font=('Arial', 9, 'bold'))
        
        # Accordion button style for collapsible frames
        self.style.configure('Accordion.TButton',
                           font=('Arial', 9, 'bold'),
                           anchor='w',
                           padding=(5, 2))

    def change_theme(self, theme_to_use, sw_conf_thm):
        if sw_conf_thm.get() == True:
            self.configure_styles()
        else:
            self.style = ttk.Style()
            self.style.configure('default')

        self.style.theme_use(theme_to_use)  # Change to a different theme
    # *********************************************************************
    def messages(self,par_1,par_2,par_3):
        self.str_out = f"{mssgs[par_2]} {par_3}"
        match par_1:
            case 0:
                print(self.str_out)
            case 1:
                self.update_status(self.str_out)
            case 2:
                print(self.str_out)
                self.update_status(self.str_out)

    def simple_encoding_detect(self, file_path):
        """Detects file encoding efficiently."""
        try:
            # Only read first 10KB for encoding detection
            with open(file_path, 'rb') as file:
                raw_data = file.read(10240)  # Read only first 10KB
            
            if not raw_data:
                return 'utf-8'
            
            detected = chardet.detect(raw_data)
            encoding = detected.get('encoding')
            confidence = detected.get('confidence', 0)
            return encoding if encoding and confidence > 0.8 else 'utf-8'
        except Exception as e:
            self.messages(2,3,f"Encoding detection failed: {e}. Using fallback 'utf-8'.")
            return 'utf-8'

    def get_last_lines(self, filepath, num_lines=50, encoding='utf-8'):
        """Efficiently get only the last N lines of a file."""
        try:
            with open(filepath, 'r', encoding=encoding, errors='replace') as file:
                # Move to end of file
                file.seek(0, os.SEEK_END)
                file_size = file.tell()

                # Start reading backwards from the end
                buffer_size = 8192
                buffer = bytearray()
                lines_found = 0
                position = file_size
                
                while position > 0 and lines_found < num_lines + 1:
                    # Read chunk from current position
                    chunk_size = min(buffer_size, position)
                    position -= chunk_size
                    file.seek(position)
                    chunk = file.read(chunk_size)
                    # Add chunk to buffer and count lines
                    buffer = bytearray(chunk.encode(encoding) if isinstance(chunk, str) else chunk) + buffer
                    lines_found = buffer.count(b'\n') if isinstance(buffer, bytearray) else chunk.count('\n')
                
                # Convert to string and get last N lines
                if isinstance(buffer, bytearray):
                    content = buffer.decode(encoding, errors='replace')
                else:
                    content = buffer
                
                lines = content.splitlines()
                return lines[-num_lines:] if len(lines) > num_lines else lines              
        except Exception as e:
            self.messages(2,3,f"Error reading last lines: {e}")
            return []


    # *************************************************************************
    # *************************** Screen  *************************************
    # *************************************************************************   

    def create_widgets(self):
        """Create and arrange the GUI components with modern styling"""
        # Main container with modern background
        main_container = ttk.Frame(self.root, style='Primary.TFrame')
        main_container.pack(fill=tk.BOTH, expand=True)
    
        # Top frame with status
        top_frame = ttk.Frame(main_container)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
    
        # Status label with styled status
        self.status_label = ttk.Label(top_frame, text="Ready", style='Status.Stopped.TLabel')
        self.status_label.pack(side=tk.RIGHT)
    
        # Create notebook with custom style
        notebook = ttk.Notebook(main_container, style='Custom.TNotebook')
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Create tabs with consistent styling
        self.log_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.config_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.simple_filters_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.advanced_filters_tab = ttk.Frame(notebook, style='Primary.TFrame')
        self.plugins_tab = ttk.Frame(notebook, style='Primary.TFrame')  # New plugins tab

        notebook.add(self.log_tab, text="Log View")
        notebook.add(self.config_tab, text="Configuration") 
        notebook.add(self.simple_filters_tab, text="Simple Filters")
        notebook.add(self.advanced_filters_tab, text="Advanced Filters")
        notebook.add(self.plugins_tab, text="Plugins")  # Add plugins tab

        self.create_log_tab()
        self.create_config_tab()
        self.create_simple_filters_tab()
        self.create_advanced_filters_tab()
        self.create_plugins_tab()  # New method for plugins
        self.create_status_bar()
    
    # *************************************************************************

    def create_status_bar(self):
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    # *************************************************************************

    def update_status(self, message):
        self.status_var.set(message)
        if "Running" in message:
            self.status_label.config(style='Status.Running.TLabel')
        elif "Stopped" in message:
            self.status_label.config(style='Status.Stopped.TLabel') 
        elif "Paused" in message:
            self.status_label.config(style='Status.Paused.TLabel')
        else:
            self.status_label.config(style='')  # Default style
        self.root.update_idletasks()

    # ****************************************************************************

    def create_log_tab(self):
        """Create log viewing tab with modern styling"""
        # Main frame
        main_frame = ttk.Frame(self.log_tab, style='Primary.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Controls frame with modern styling
        controls_frame = ttk.LabelFrame(main_frame, text="Log Controls", style='Custom.TLabelframe')
        controls_frame.pack(fill=tk.X, pady=(0, 5))

        # Left controls
        left_controls = ttk.Frame(controls_frame)
        left_controls.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.start_button = ttk.Button(left_controls, text="Start Tail", state="normal", command=self.start_tail, style='Success.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        self.stop_button = ttk.Button(left_controls, text="Stop Tail", state="disabled", command=self.stop_tail, style='Danger.TButton')
        self.stop_button.pack(side=tk.LEFT, padx=(0, 5))

        ttk.Button(left_controls, text="Clear Display", command=self.clear_display).pack(side=tk.LEFT, padx=(0, 5))

        self.pause_var = tk.BooleanVar(value=False)
        self.pause_button = ttk.Button(left_controls, text="Pause", state="disabled", command=self.toggle_pause, style='Primary.TButton')
        self.pause_button.pack(side=tk.LEFT, padx=(20, 5))

        # Right controls - search
        right_controls = ttk.Frame(controls_frame)
        right_controls.pack(side=tk.RIGHT)

        # Encoding indicator
        self.encoding_label = ttk.Label(right_controls, text="")
        self.encoding_label.pack(side=tk.RIGHT)

        ttk.Label(right_controls, text="Search:").pack(side=tk.LEFT, padx=(0, 5))

        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(right_controls, textvariable=self.search_var, width=25, style='Modern.TEntry')
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind('<Return>', lambda e: self.search_log())

        ttk.Button(right_controls, text="Find", command=self.search_log, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(right_controls, text="Clear", command=self.clear_search).pack(side=tk.LEFT, padx=(0, 5))

        # Search navigation buttons
        self.prev_button = ttk.Button(right_controls, text="▲ Prev", command=self.search_previous, state="disabled", style='Primary.TButton')
        self.prev_button.pack(side=tk.LEFT, padx=(0, 5))
        self.next_button = ttk.Button(right_controls, text="▼ Next", command=self.search_next, state="disabled", style='Primary.TButton')
        self.next_button.pack(side=tk.LEFT, padx=(0, 5))
  
        # Initialize search state
        self.search_matches = []
        self.current_match_index = -1

        # Log display area
        log_display_frame = ttk.LabelFrame(main_frame, text="Log Content", style='Custom.TLabelframe')
        log_display_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        self.log_text = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, width=80, height=25,
                                            font=('IBM Plex Mono Text', 10))  # Monospace font for logs
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Configure text tags with modern colors
        self.log_text.tag_configure("default", foreground="#2c3e50")
        self.log_text.tag_configure("search_highlight", background="#f39c12", foreground="black")
        self.log_text.tag_configure("search_current", background="#e74c3c", foreground="white")

        # Configure text tags for search highlighting
        self.log_text.tag_configure("search_highlight", background="yellow", foreground="black")
        self.log_text.tag_configure("search_current", background="orange", foreground="black")
    
        # Configure default text tag
        self.log_text.tag_configure("default", foreground="black")

    # ****************************************************************************
 
    def create_simple_filters_tab(self):
        #Create simple filters tab content.
        main_frame = ttk.Frame(self.simple_filters_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        # ENHANCED FILTER CONFIGURATION SECTION
        filter_frame = ttk.LabelFrame(main_frame, text="Filter Configuration", padding="10")
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Filter pattern
        ttk.Label(filter_frame, text="Filter Pattern:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_string = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_string, width=40).grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
        
        # Regex checkbox
        self.filter_regex_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(filter_frame, text="Use Regex", variable=self.filter_regex_var).grid(row=0, column=2, pady=2, sticky="w")
        
        # Colors
        ttk.Label(filter_frame, text="Text Color:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        self.fg_color = tk.StringVar(value="black")
        ttk.Entry(filter_frame, textvariable=self.fg_color, width=10).grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(filter_frame, text='Select a Color', command=lambda: self.change_color('fg')).grid(row=1, column=1, padx=(100, 10), pady=2, sticky="w")

        ttk.Label(filter_frame, text="Background:").grid(row=1, column=3, sticky="w", padx=(0, 5), pady=2)
        self.bg_color = tk.StringVar(value="yellow")
        ttk.Entry(filter_frame, textvariable=self.bg_color, width=10).grid(row=1, column=4, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(filter_frame, text='Select a Color', command=lambda: self.change_color('bg')).grid(row=1, column=5, padx=(0, 10), pady=2, sticky="w")

        # Action type selection
        ttk.Label(filter_frame, text="Action:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_action_var = tk.StringVar(value="none")
        action_combo = ttk.Combobox(filter_frame, textvariable=self.filter_action_var, 
                                   values=["none", "sound", "tts", "skip", "notification", "dialog"],
                                   state="readonly", width=12)
        action_combo.grid(row=2, column=1, padx=(0, 10), pady=2, sticky="w")
        action_combo.bind('<<ComboboxSelected>>', self.on_action_changed)

        # Add filter button
        ttk.Button(filter_frame, text="Add Filter", command=self.add_enhanced_filter).grid(row=4, column=0, pady=10, sticky="w")
        
        # Update filter button (initially disabled)
        self.update_filter_btn = ttk.Button(filter_frame, text="Update Filter", command=self.update_enhanced_filter, state="disabled")
        self.update_filter_btn.grid(row=4, column=1, pady=10, sticky="w")
        
        # Action modifier
        ttk.Label(filter_frame, text="Action Modifier:").grid(row=3, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_action_modifier = tk.StringVar()
        self.action_modifier_entry = ttk.Entry(filter_frame, textvariable=self.filter_action_modifier, width=40)
        self.action_modifier_entry.grid(row=3, column=1, columnspan=2, padx=(0, 10), pady=2, sticky="w")
        
        # Sound file browser (initially hidden)
        self.browse_sound_btn = ttk.Button(filter_frame, text="Browse Sound", command=self.browse_sound_file)
        self.browse_sound_btn.grid(row=3, column=3, padx=(5, 0), pady=2)
        self.browse_sound_btn.grid_remove()  # Hide initially
 
        # Voice selection for TTS actions (using Combobox instead of Listbox)
        ttk.Label(filter_frame, text="TTS Voice:").grid(row=4, column=0, sticky="w", padx=(0, 5), pady=2)
    
        # Combobox for voice selection
        self.voice_combobox = ttk.Combobox(filter_frame, state="readonly", width=40)
        self.voice_combobox.grid(row=3, column=3, columnspan=2, sticky="w", pady=2)
        self.voice_combobox.grid_remove()  # Hide initially
        
        # Load available voices
        self.refresh_voices()
    
        # Test voice button
        self.test_voice_btn = ttk.Button(filter_frame, text="Test Voice", command=self.test_selected_voice)
        self.test_voice_btn.grid(row=3, column=5, padx=(5, 0), pady=2)
        self.test_voice_btn.grid_remove()  # Hide initially
        
        # Add filter button
        ttk.Button(filter_frame, text="Add Filter", command=self.add_enhanced_filter).grid(row=4, column=0, pady=10, sticky="w")
        
        # Filter list display
        listbox_frame = ttk.Frame(filter_frame)
        listbox_frame.grid(row=5, column=0, columnspan=6, sticky="nsew", pady=(10, 0))
        
        # Add scrollbar to listbox
        self.filter_listbox = tk.Listbox(listbox_frame, width=80, height=6)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.filter_listbox.yview)
        self.filter_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.filter_listbox.bind('<<ListboxSelect>>', self.on_filter_select)
        self.filter_listbox.bind('<<ListboxSelect>>', self.on_filter_selection_change)
        self.filter_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Remove filter button
        ttk.Button(filter_frame, text="Remove Selected Filter", command=self.remove_enhanced_filter).grid(row=6, column=0, pady=5, sticky="w")
    
        button_frame = ttk.Frame(filter_frame)
        button_frame.grid(row=4, column=0, columnspan=6, pady=10, sticky="w")
    
        ttk.Button(button_frame, text="Add Filter", command=self.add_enhanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        self.edit_filter_btn = ttk.Button(button_frame, text="Edit Selected", command=self.edit_selected_filter, state="disabled")
        self.edit_filter_btn.pack(side=tk.LEFT, padx=(0, 5))
        self.update_filter_btn = ttk.Button(button_frame, text="Update Filter", command=self.update_filter, state="disabled")
        self.update_filter_btn.pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Cancel Edit", command=self.cancel_edit).pack(side=tk.LEFT)
    
        # Make filter frame grid responsive
        filter_frame.columnconfigure(1, weight=1)
     
    # ****************************************************************************

    def create_advanced_filters_tab(self):
        """Create advanced filters tab with collapsible sections - ENHANCED"""
        # Main container with scrollbar
        main_frame = ttk.Frame(self.advanced_filters_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Create collapsible sections
        self.builder_section = CollapsibleFrame(main_frame, text="Regex Builder")
        self.builder_section.pack(fill=tk.X, pady=(0, 5))

        self.actions_section = CollapsibleFrame(main_frame, text="Actions")
        self.actions_section.pack(fill=tk.X, pady=(0, 5))

        self.saved_section = CollapsibleFrame(main_frame, text="Saved Advanced Filters")
        self.saved_section.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Build each section
        self.build_regex_builder_section()
        self.build_actions_section()
        self.actions_section.toggle()
        self.build_saved_filters_section()
        self.saved_section.toggle()

        # Control buttons at bottom (always visible)
        self.build_control_buttons(main_frame)
        # Initialize with one empty field
        self.root.after(100, self.initialize_advanced_filters)  # Small delay to ensure UI is built

    def initialize_advanced_filters(self):
        """Initialize advanced filters tab with default state"""
        # Add one empty field to start
        if not self.regex_fields:
            self.add_regex_field()
    
        # Load advanced filters if auto-load is enabled
        if self.config_manager.get("auto_load_config", True):
            self.auto_load_advanced_filters()

    def auto_load_advanced_filters(self):
        """Auto-load advanced filters on startup"""
        try:
            advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_file and os.path.exists(advanced_filters_file):
                self.advanced_filters_file_var.set(advanced_filters_file)
                self.load_advanced_filters_auto()
        except Exception as e:
            print(f"Auto-load advanced filters error: {e}")

    def build_regex_builder_section(self):
    
        """Build the regex builder section with common patterns combobox"""
        builder_frame = self.builder_section.get_content_frame()

        # TOP BAR: Common patterns combobox and controls
        top_bar_frame = ttk.Frame(builder_frame)
        top_bar_frame.pack(fill=tk.X, pady=(0, 10))

        # Common patterns combobox on the right
        ttk.Label(top_bar_frame, text="Common Patterns:").pack(side=tk.LEFT, padx=(0, 5))

        self.common_patterns_var = tk.StringVar()
        self.common_patterns_combo = ttk.Combobox(
            top_bar_frame, 
            textvariable=self.common_patterns_var,
            values=list(self.predefined_patterns.keys()),
            state="readonly",
            width=20
        )
        self.common_patterns_combo.pack(side=tk.LEFT, padx=(0, 5))
        self.common_patterns_combo.set("Select a pattern")  # Default text
    
        # Insert pattern button
        ttk.Button(
            top_bar_frame, 
            text="Insert Pattern", 
            command=self.insert_common_pattern
        ).pack(side=tk.LEFT, padx=(0, 10))
    
        # Preview pattern button
        ttk.Button(
            top_bar_frame, 
            text="Preview", 
            command=self.preview_common_pattern
        ).pack(side=tk.LEFT, padx=(0, 10))

        # Help text on the left
        help_text = "Tip: Use commas to separate multiple terms in 'as string' and 'as word' modifiers"
        help_label = ttk.Label(top_bar_frame, text=help_text, font=("Arial", 8), foreground="blue")
        help_label.pack(side=tk.RIGHT)

        # Rest of your existing builder section code...
        name_frame = ttk.Frame(builder_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        """Build the regex builder section"""
        builder_frame = self.builder_section.get_content_frame()

        # Filter name and enabled
        name_frame = ttk.Frame(builder_frame)
        name_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(name_frame, text="Filter Name:").pack(side=tk.LEFT, padx=(0, 5))
        self.advanced_filter_name = tk.StringVar()
        ttk.Entry(name_frame, textvariable=self.advanced_filter_name, width=30).pack(side=tk.LEFT, padx=(0, 15))

        self.advanced_filter_enabled = tk.BooleanVar(value=True)
        ttk.Checkbutton(name_frame, text="Enabled", variable=self.advanced_filter_enabled).pack(side=tk.LEFT)

        # Regex fields container with scrollbar
        fields_container = ttk.Frame(builder_frame)
        fields_container.pack(fill=tk.BOTH, expand=True)

        # Create scrollable canvas for fields
        self.fields_canvas = tk.Canvas(fields_container, height=150)
        fields_scrollbar = ttk.Scrollbar(fields_container, orient="vertical", command=self.fields_canvas.yview)
        self.fields_scrollable_frame = ttk.Frame(self.fields_canvas)

        self.fields_scrollable_frame.bind("<Configure>", lambda e: self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all")))

        self.fields_canvas.create_window((0, 0), window=self.fields_scrollable_frame, anchor="nw")
        self.fields_canvas.configure(yscrollcommand=fields_scrollbar.set)

        self.fields_canvas.pack(side="left", fill="both", expand=True)
        fields_scrollbar.pack(side="right", fill="y")

        # Add field button
        ttk.Button(builder_frame, text="Add Field", command=self.add_regex_field).pack(pady=(10, 0))
    
        # Generated Regex Display
        regex_display_frame = ttk.LabelFrame(builder_frame, text="Generated Regex", padding="5")
        regex_display_frame.pack(fill=tk.X, pady=(10, 0))

        self.generated_regex = tk.StringVar()
        regex_entry = ttk.Entry(regex_display_frame, textvariable=self.generated_regex, font=("Courier", 9), state="readonly")
        regex_entry.pack(fill=tk.X, padx=5, pady=2)

        # Test regex button - ENHANCED
        test_button_frame = ttk.Frame(regex_display_frame)
        test_button_frame.pack(fill=tk.X, pady=(5, 2))
    
        ttk.Button(test_button_frame, text="Test Regex Pattern", command=self.test_generated_regex).pack(side=tk.LEFT)

        # Add a button to copy regex to clipboard
        ttk.Button(test_button_frame, text="Copy to Clipboard", command=lambda: self.copy_to_clipboard(self.generated_regex.get())).pack(side=tk.LEFT, padx=(10, 0))

    def build_actions_section(self):
        """Build the actions section"""
        actions_frame = self.actions_section.get_content_frame()
    
        # Use grid for better alignment in actions section
        # Colors
        ttk.Label(actions_frame, text="Text Color:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_fg_color = tk.StringVar(value="black")
        ttk.Entry(actions_frame, textvariable=self.advanced_fg_color, width=10).grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(actions_frame, text='Select', command=lambda: self.change_color('advanced_fg')).grid(row=0, column=2, pady=2, sticky="w")

        ttk.Label(actions_frame, text="Background:").grid(row=0, column=3, sticky="w", padx=(20, 5), pady=2)
        self.advanced_bg_color = tk.StringVar(value="yellow")
        ttk.Entry(actions_frame, textvariable=self.advanced_bg_color, width=10).grid(row=0, column=4, padx=(0, 10), pady=2, sticky="w")
        ttk.Button(actions_frame, text='Select', command=lambda: self.change_color('advanced_bg')).grid(row=0, column=5, pady=2, sticky="w")
    
        # Action type selection
        ttk.Label(actions_frame, text="Additional Action:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_action_var = tk.StringVar(value="none")
        action_combo = ttk.Combobox(actions_frame, textvariable=self.advanced_action_var,
                               values=["none", "sound", "tts", "notification", "dialog"],
                               state="readonly", width=12)
        action_combo.grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        action_combo.bind('<<ComboboxSelected>>', self.on_advanced_action_changed)

        # Action modifier
        ttk.Label(actions_frame, text="Action Details:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_action_modifier = tk.StringVar()
        self.advanced_action_modifier_entry = ttk.Entry(actions_frame, textvariable=self.advanced_action_modifier, width=40)
        self.advanced_action_modifier_entry.grid(row=2, column=1, columnspan=3, padx=(0, 10), pady=2, sticky="w")

        # Advanced TTS voice selection
        ttk.Label(actions_frame, text="TTS Voice:").grid(row=3, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_voice_combobox = ttk.Combobox(actions_frame, state="readonly", width=30)
        self.advanced_voice_combobox.grid(row=3, column=1, columnspan=2, padx=(0, 10), pady=2, sticky="w")
        self.advanced_voice_combobox.grid_remove()  # Hide initially

    def build_saved_filters_section(self):
        """Build the saved filters section"""
        saved_frame = self.saved_section.get_content_frame()

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(saved_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True)

        self.advanced_filters_listbox = tk.Listbox(listbox_frame, height=6)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.advanced_filters_listbox.yview)
        self.advanced_filters_listbox.configure(yscrollcommand=scrollbar.set)

        self.advanced_filters_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Filter management buttons
        mgmt_frame = ttk.Frame(saved_frame)
        mgmt_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(mgmt_frame, text="Load Selected", command=self.load_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(mgmt_frame, text="Delete Selected", command=self.delete_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(mgmt_frame, text="Toggle Enabled", command=self.toggle_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))

    def build_control_buttons(self, parent_frame):
        """Build the control buttons (always visible)"""
        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="Store Advanced Filter", command=self.store_advanced_filter).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Clear Form", command=self.clear_advanced_form).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Collapse All", command=self.collapse_all_sections).pack(side=tk.RIGHT, padx=(5, 0))
        ttk.Button(button_frame, text="Expand All", command=self.expand_all_sections).pack(side=tk.RIGHT, padx=(0, 5))
        ttk.Button(button_frame, text="Test", command=self.debug_advanced_filters).pack(side=tk.RIGHT, padx=(0, 5))

    def collapse_all_sections(self):
        """Collapse all collapsible sections"""
        if hasattr(self, 'builder_section') and self.builder_section.is_expanded:
            self.builder_section.toggle()
        if hasattr(self, 'actions_section') and self.actions_section.is_expanded:
            self.actions_section.toggle()
        if hasattr(self, 'saved_section') and self.saved_section.is_expanded:
            self.saved_section.toggle()

    def expand_all_sections(self):
        """Expand all collapsible sections"""
        if hasattr(self, 'builder_section') and not self.builder_section.is_expanded:
            self.builder_section.toggle()
        if hasattr(self, 'actions_section') and not self.actions_section.is_expanded:
            self.actions_section.toggle()
        if hasattr(self, 'saved_section') and not self.saved_section.is_expanded:
            self.saved_section.toggle()

    def insert_common_pattern(self):
        """Insert the selected common pattern into the currently focused field"""
        pattern_name = self.common_patterns_var.get()
        if not pattern_name or pattern_name == "Select a pattern":
            self.messages(2, 3, "Please select a pattern first")
            return

        pattern = self.predefined_patterns.get(pattern_name)
        if not pattern:
            self.messages(2, 3, "Selected pattern not found")
            return

        # Find the currently focused field
        focused_widget = self.root.focus_get()
    
        # Search through all regex fields to find the focused entry
        for field_frame in self.regex_fields:
            for widget in field_frame.winfo_children():
                if widget == focused_widget and isinstance(widget, ttk.Entry):
                    # Found the focused entry widget
                    current_text = widget.get()
                    if current_text:
                        # Insert at cursor position or replace selection
                        try:
                            # Get selection range
                            sel_range = widget.selection_get()
                            if sel_range:
                                # Replace selection
                                start = widget.index(tk.SEL_FIRST)
                                end = widget.index(tk.SEL_LAST)
                                widget.delete(start, end)
                                widget.insert(start, pattern)
                            else:
                                # Insert at cursor
                                cursor_pos = widget.index(tk.INSERT)
                                widget.insert(cursor_pos, pattern)
                        except tk.TclError:
                            # No selection, insert at end
                            widget.insert(tk.END, pattern)
                    else:
                        # Field is empty, just set the pattern
                        widget.delete(0, tk.END)
                        widget.insert(0, pattern)
                
                    # Update the generated regex
                    self.update_generated_regex()
                    self.messages(2, 9, f"Pattern '{pattern_name}' inserted")
                    return
    
        # If no focused field found, insert into the first field
        if self.regex_fields:
            first_field = self.regex_fields[0]
            field_entry = None
            for widget in first_field.winfo_children():
                if isinstance(widget, ttk.Entry):
                    field_entry = widget
                    break
        
            if field_entry:
                field_entry.delete(0, tk.END)
                field_entry.insert(0, pattern)
                self.update_generated_regex()
                self.messages(2, 9, f"Pattern '{pattern_name}' inserted into first field")
            else:
                self.messages(2, 3, "No field found to insert pattern")
        else:
            self.messages(2, 3, "No regex fields available")

    def preview_common_pattern(self):
        """Show a preview of the selected common pattern"""
        pattern_name = self.common_patterns_var.get()
        if not pattern_name or pattern_name == "Select a pattern":
            self.messages(2, 3, "Please select a pattern first")
            return

        pattern = self.predefined_patterns.get(pattern_name)
        if not pattern:
            self.messages(2, 3, "Selected pattern not found")
            return

        # Create preview dialog
        preview_window = tk.Toplevel(self.root)
        preview_window.title(f"Pattern Preview: {pattern_name}")
        preview_window.geometry("500x300")
        preview_window.transient(self.root)

        main_frame = ttk.Frame(preview_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Pattern display
        ttk.Label(main_frame, text="Pattern:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        pattern_text = tk.Text(main_frame, height=3, wrap=tk.WORD, font=("Courier", 9))
        pattern_text.pack(fill=tk.X, pady=(0, 10))
        pattern_text.insert(1.0, pattern)
        pattern_text.config(state=tk.DISABLED)

        # Description
        ttk.Label(main_frame, text="Description:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        desc_frame = ttk.Frame(main_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 10))
    
        descriptions = {
            "Date (YYYY-MM-DD)": "Matches dates in YYYY-MM-DD format",
            "Date (MM/DD/YYYY)": "Matches dates in MM/DD/YYYY format", 
            "Time (HH:MM:SS)": "Matches times in HH:MM:SS format",
            "IPv4 Address": "Matches IPv4 addresses",
            "IPv6 Address": "Matches IPv6 addresses",
            "Email Address": "Matches email addresses",
            "Phone Number": "Matches phone numbers",
            "URL": "Matches URLs starting with http/https",
            "Hex Color": "Matches hexadecimal color codes",
            "MAC Address": "Matches MAC addresses",
            "Credit Card": "Matches credit card numbers",
            "UUID": "Matches UUIDs",
            "Log Level": "Matches common log levels (DEBUG, INFO, WARN, etc.)",
            "Number": "Matches numbers",
            "Word": "Matches words"
        }
    
        desc_text = tk.Text(desc_frame, height=2, wrap=tk.WORD)
        desc_text.pack(fill=tk.X)
        desc_text.insert(1.0, descriptions.get(pattern_name, "No description available"))
        desc_text.config(state=tk.DISABLED)

        # Example matches
        ttk.Label(main_frame, text="Example Matches:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        examples_frame = ttk.Frame(main_frame)
        examples_frame.pack(fill=tk.BOTH, expand=True)
    
        examples_text = tk.Text(examples_frame, wrap=tk.WORD)
        examples_text.pack(fill=tk.BOTH, expand=True)
    
        # Generate examples based on pattern type
        examples = self.generate_pattern_examples(pattern_name, pattern)
        examples_text.insert(1.0, "\n".join(examples))
        examples_text.config(state=tk.DISABLED)

        ttk.Button(main_frame, text="Close", command=preview_window.destroy).pack(pady=(10, 0))

    def generate_pattern_examples(self, pattern_name, pattern):
        """Generate example matches for common patterns"""
        examples = {
            "Date (YYYY-MM-DD)": ["2024-01-15", "1999-12-31", "2023-03-08"],
            "Date (MM/DD/YYYY)": ["12/31/2023", "01/15/2024", "03/08/2023"],
            "Time (HH:MM:SS)": ["14:30:25", "09:15:00", "23:59:59"],
            "IPv4 Address": ["192.168.1.1", "10.0.0.1", "172.16.254.1"],
            "IPv6 Address": ["2001:0db8:85a3:0000:0000:8a2e:0370:7334", "::1", "2001:db8::1"],
            "Email Address": ["user@example.com", "test.email+tag@domain.co.uk", "name@company.org"],
            "Phone Number": ["555-123-4567", "555.123.4567", "5551234567"],
            "URL": ["https://example.com", "http://sub.domain.co.uk/path", "https://www.google.com"],
            "Hex Color": ["#ff0000", "#abc", "#123456", "#f0f0f0"],
            "MAC Address": ["00:1B:44:11:3A:B7", "00-1B-44-11-3A-B7", "001B44113AB7"],
            "Credit Card": ["4111-1111-1111-1111", "5500 0000 0000 0004", "340000000000009"],
            "UUID": ["123e4567-e89b-12d3-a456-426614174000", "00000000-0000-0000-0000-000000000000"],
            "Log Level": ["DEBUG: Starting process", "ERROR: File not found", "INFO: Operation completed"],
            "Number": ["123", "0", "999999", "42"],
            "Word": ["hello", "test", "example", "word"]
        }
    
        return examples.get(pattern_name, ["No examples available"])

    # ****************************************************************************    

    def create_config_tab(self):
        """Create configuration tab with file management"""
        # Main container with scrollbar if needed
        main_frame = ttk.Frame(self.config_tab)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # File Settings Section
        file_frame = ttk.LabelFrame(main_frame, text="File Settings", padding="10")
        file_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Log file selection
        ttk.Label(file_frame, text="Default Log File:").grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.log_file_var = tk.StringVar(value=self.config_manager.get("log_file", ""))
        ttk.Entry(file_frame, textvariable=self.log_file_var, width=50).grid(row=0, column=1, padx=(0, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=self.browse_log_file).grid(row=0, column=2, pady=2)
        
        # Filters file selection
        ttk.Label(file_frame, text="Filters File:").grid(row=1, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filters_file_var = tk.StringVar(value=self.config_manager.get("filters_file", ""))
        ttk.Entry(file_frame, textvariable=self.filters_file_var, width=50).grid(row=1, column=1, padx=(0, 5), pady=2)
        # Load filters button
        ttk.Button(file_frame, text="Load", command=lambda: self.browse_filter_file("filters_file")).grid(row=1, column=2, pady=2)
  
        # Save as default filters button
        ttk.Button(file_frame, text="Save", command=lambda: self.save_filters(True)).grid(row=1, column=3, sticky="e", pady=2)
      
        # Advanced filters file selection
        ttk.Label(file_frame, text="Advanced Filters File:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_filters_file_var = tk.StringVar(value=self.config_manager.get("advanced_filters_file", ""))
        ttk.Entry(file_frame, textvariable=self.advanced_filters_file_var, width=50).grid(row=2, column=1, padx=(0, 5), pady=2)
        ttk.Button(file_frame, text="Load", command=lambda: self.browse_filter_file("advanced_filters_file")).grid(row=2, column=2, pady=2)
        ttk.Button(file_frame, text="Save", command=lambda: self.save_advanced_filters(True)).grid(row=2, column=3, sticky="e", pady=2)
        
        # Application Settings Section
        app_frame = ttk.LabelFrame(main_frame, text="Application Settings", padding="10")
        app_frame.pack(fill=tk.X, pady=(0, 10))

        # Initial lines
        ttk.Label(app_frame, text="Initial Lines:").grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.initial_lines_var = tk.StringVar(value=str(self.config_manager.get("initial_lines", 50)))
        ttk.Entry(app_frame, textvariable=self.initial_lines_var, width=10).grid(row=0, column=1, sticky="w", pady=2)
        
        # Refresh interval
        ttk.Label(app_frame, text="Refresh Interval (ms):").grid(row=0, column=2, sticky="w", padx=(20, 10), pady=2)
        self.refresh_interval_var = tk.StringVar(value=str(self.config_manager.get("refresh_interval", 100)))
        ttk.Entry(app_frame, textvariable=self.refresh_interval_var, width=10).grid(row=0, column=3, sticky="w", pady=2)
        
        # Auto-load checkbox
        self.auto_load_var = tk.BooleanVar(value=self.config_manager.get("auto_load_config", True))
        ttk.Checkbutton(app_frame, text="Auto-load last configuration and filters on startup", variable=self.auto_load_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=10)
       
        # Styling
        #self.auto_style_var = tk.BooleanVar(value=self.config_manager.get("auto_style", True))
        self.auto_style_var = tk.BooleanVar(value=self.config_manager.get("auto_style", False))
        #ttk.Checkbutton(app_frame, text="Apply custom styling", variable=self.auto_style_var).grid(row=2, column=0, columnspan=1, sticky="w", pady=10)
       
        self.style = ttk.Style()
        available_themes = self.style.theme_names()

        self.style_list_combo = ttk.Combobox(app_frame, values=available_themes, width=50)
        self.style_list_combo.grid(row=2, column=1, padx=(10, 5), pady=2)
        self.style_list_combo.current(0)
        
        ttk.Button(app_frame, text="Change theme", command=lambda: self.change_theme(self.style_list_combo.get(),self.auto_style_var), style='Danger.TButton').grid(row=2, column=2, pady=2)
       
        # Recent Files Section
        recent_frame = ttk.LabelFrame(main_frame, text="Recent Files", padding="10")
        recent_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Recent filters
        ttk.Label(recent_frame, text="Recent Filters:").grid(row=0, column=0, sticky="w", pady=2)
        self.recent_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_filters", []), width=50)
        self.recent_filters_combo.grid(row=0, column=1, padx=(10, 5), pady=2)
        ttk.Button(recent_frame, text="Load", command=lambda: self.on_recent_filters_selected(self.recent_filters_combo.get())).grid(row=0, column=3, pady=2)

        # Recent advanced filters
        ttk.Label(recent_frame, text="Recent Advanced Filters:").grid(row=1, column=0, sticky="w", pady=2)
        self.recent_adv_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_advanced_filters", []), width=50)
        self.recent_adv_filters_combo.grid(row=1, column=1, padx=(10, 5), pady=2)
        ttk.Button(recent_frame, text="Load", command=lambda: self.on_recent_adv_filters_selected(self.recent_adv_filters_combo.get())).grid(row=1, column=3, pady=2)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save Configuration", command=self.save_configuration_dialog).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Load Configuration", command=self.load_configuration_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_configuration).pack(side=tk.LEFT)

    # *************************************************************************

    def create_plugins_tab(self):
        """Create the plugins management tab"""
        main_frame = ttk.Frame(self.plugins_tab, style='Primary.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(title_frame, text="Plugin Manager", style='Title.TLabel').pack(anchor=tk.W)
        ttk.Label(title_frame, text="Extend ETail functionality with plugins", 
                 style='Subtitle.TLabel').pack(anchor=tk.W)
        
        # Plugin discovery and controls
        controls_frame = ttk.LabelFrame(main_frame, text="Plugin Controls", style='Custom.TLabelframe')
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        control_buttons = ttk.Frame(controls_frame)
        control_buttons.pack(fill=tk.X, pady=5)
        
        ttk.Button(control_buttons, text="Discover Plugins", 
                  command=self.discover_plugins, style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_buttons, text="Reload All", 
                  command=self.reload_plugins).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_buttons, text="Open Plugins Folder", 
                  command=self.open_plugins_folder).pack(side=tk.LEFT)
        
        # Plugins list
        list_frame = ttk.LabelFrame(main_frame, text="Available Plugins", style='Custom.TLabelframe')
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create treeview for plugins
        columns = ('name', 'version', 'description', 'status')
        self.plugins_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=8)
        
        # Configure columns
        self.plugins_tree.heading('name', text='Plugin Name')
        self.plugins_tree.heading('version', text='Version')
        self.plugins_tree.heading('description', text='Description')
        self.plugins_tree.heading('status', text='Status')
        
        self.plugins_tree.column('name', width=150)
        self.plugins_tree.column('version', width=80)
        self.plugins_tree.column('description', width=300)
        self.plugins_tree.column('status', width=100)
        
        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.plugins_tree.yview)
        self.plugins_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.plugins_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Plugin actions frame
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.enable_button = ttk.Button(actions_frame, text="Enable Plugin", 
                                       command=self.enable_selected_plugin, 
                                       style='Success.TButton', state='disabled')
        self.enable_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disable_button = ttk.Button(actions_frame, text="Disable Plugin", 
                                        command=self.disable_selected_plugin, 
                                        style='Danger.TButton', state='disabled')
        self.disable_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.settings_button = ttk.Button(actions_frame, text="Settings", 
                                         command=self.show_plugin_settings, 
                                         state='disabled')
        self.settings_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Plugin info frame
        self.info_frame = ttk.LabelFrame(main_frame, text="Plugin Information", style='Custom.TLabelframe')
        self.info_frame.pack(fill=tk.X)
        
        self.plugin_info_text = scrolledtext.ScrolledText(self.info_frame, height=4, wrap=tk.WORD)
        self.plugin_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.plugin_info_text.config(state=tk.DISABLED)
        
        # Bind selection event
        self.plugins_tree.bind('<<TreeviewSelect>>', self.on_plugin_selection_changed)
        
        # Initial plugin discovery
        self.root.after(1000, self.discover_plugins)  # Delay to let UI load first

    def discover_plugins(self):
        """Discover and list available plugins"""
        self.plugin_manager.discover_plugins()
        
        # DEBUG: Check what the plugin manager actually found
        print(f"DEBUG: Plugin manager found {len(self.plugin_manager.plugins)} plugins")
        for plugin_name, plugin_info in self.plugin_manager.plugins.items():
            print(f"DEBUG: Plugin: {plugin_name} -> {plugin_info}")

        self.refresh_plugins_list()
        self.messages(2, 9, f"Found {len(self.plugin_manager.plugins)} plugins")

    def refresh_plugins_list(self):
        """Refresh the plugins treeview"""
        # Clear existing items
        for item in self.plugins_tree.get_children():
            self.plugins_tree.delete(item)
        
        # Add plugins to treeview
        for plugin_name, plugin_info in self.plugin_manager.plugins.items():
            plugin_class = plugin_info['class']
            plugin_instance = plugin_class(self)  # Temporary instance for info
            
            status = "Enabled" if plugin_info['enabled'] else "Disabled"
            
            self.plugins_tree.insert('', tk.END, values=(
                plugin_instance.name,
                plugin_instance.version,
                plugin_instance.description,
                status
            ), tags=(plugin_name,))

    def on_plugin_selection_changed(self, event):
        """Handle plugin selection change"""
        selection = self.plugins_tree.selection()
        if not selection:
            self.enable_button.config(state='disabled')
            self.disable_button.config(state='disabled')
            self.settings_button.config(state='disabled')
            return
        
        item = selection[0]
        plugin_name = self.plugins_tree.item(item, 'tags')[0]
        plugin_info = self.plugin_manager.plugins.get(plugin_name)
        
        if plugin_info:
            # Update action buttons
            if plugin_info['enabled']:
                self.enable_button.config(state='disabled')
                self.disable_button.config(state='normal')
            else:
                self.enable_button.config(state='normal')
                self.disable_button.config(state='disabled')
            
            self.settings_button.config(state='normal')
            
            # Update info text
            plugin_class = plugin_info['class']
            plugin_instance = plugin_class(self)
            
            info_text = f"Name: {plugin_instance.name}\n"
            info_text += f"Version: {plugin_instance.version}\n"
            info_text += f"Description: {plugin_instance.description}\n"
            info_text += f"File: {plugin_info['file'].name}\n"
            info_text += f"Status: {'Enabled' if plugin_info['enabled'] else 'Disabled'}"
            
            self.plugin_info_text.config(state=tk.NORMAL)
            self.plugin_info_text.delete(1.0, tk.END)
            self.plugin_info_text.insert(1.0, info_text)
            self.plugin_info_text.config(state=tk.DISABLED)

    def enable_selected_plugin(self):
        """Enable the selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            if self.plugin_manager.load_plugin(plugin_name):
                self.refresh_plugins_list()

    def disable_selected_plugin(self):
        """Disable the selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            if self.plugin_manager.unload_plugin(plugin_name):
                self.refresh_plugins_list()

    def show_plugin_settings(self):
        """Show settings for selected plugin"""
        selection = self.plugins_tree.selection()
        if selection:
            item = selection[0]
            plugin_name = self.plugins_tree.item(item, 'tags')[0]
            plugin_instance = self.plugin_manager.loaded_plugins.get(plugin_name)
            
            if plugin_instance:
                settings_widget = plugin_instance.get_settings_widget(self.plugins_tab)
                if settings_widget:
                    # Create settings dialog
                    settings_window = tk.Toplevel(self.root)
                    settings_window.title(f"Settings - {plugin_instance.name}")
                    settings_window.geometry("400x300")
                    settings_window.transient(self.root)
                    
                    settings_widget(settings_window).pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                else:
                    self.messages(2, 3, "This plugin has no settings")

    def open_plugins_folder(self):
        """Open the plugins folder in file explorer"""
        try:
            os.startfile(str(self.plugin_manager.plugins_dir))  # Windows
        except:
            try:
                import subprocess
                subprocess.run(['open', str(self.plugin_manager.plugins_dir)])  # macOS
            except:
                try:
                    subprocess.run(['xdg-open', str(self.plugin_manager.plugins_dir)])  # Linux
                except:
                    self.messages(2, 3, "Could not open plugins folder")

    def reload_plugins(self):
        """Reload all plugins"""
        # Unload all currently loaded plugins
        for plugin_name in list(self.plugin_manager.loaded_plugins.keys()):
            self.plugin_manager.unload_plugin(plugin_name)
        
        # Rediscover and reload enabled plugins
        self.discover_plugins()
        self.messages(2, 9, "All plugins reloaded")

    # *************************************************************************
    # *************************** Button Actions*******************************
    # *************************************************************************

    def change_color(self,wich):
        colors = askcolor(title="Tkinter Color Chooser")
        match wich:
            case "fg":
                self.fg_color.set(colors[1])
            case "bg":
                self.bg_color.set(colors[1])
            case "advanced_fg":
                self.advanced_fg_color.set(colors[1])
            case "advanced_bg":
                self.advanced_bg_color.set(colors[1])

        print(f"Colors {wich}{colors}{colors[1]}")
    
    def clear_display(self):
        """Clear the log display area."""
        self.log_text.delete(1.0, tk.END)

    def search_log(self):
        """Search for text in the log display and highlight matches"""
        search_text = self.search_var.get().strip()
        if not search_text:
            self.clear_search()
            return

        # Remove previous search highlights
        self.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.log_text.tag_remove("search_current", "1.0", tk.END)
    
        # Reset search state
        self.search_matches = []
        self.current_match_index = -1

        # Search for matches (case-insensitive)
        content = self.log_text.get("1.0", tk.END).lower()
        search_lower = search_text.lower()
    
        start_pos = "1.0"
        while True:
            start_pos = self.log_text.search(search_text, start_pos, tk.END, nocase=1)
            if not start_pos:
                break
            
            end_pos = f"{start_pos}+{len(search_text)}c"

            # Add to matches list
            self.search_matches.append(start_pos)

            # Apply highlight tag
            self.log_text.tag_add("search_highlight", start_pos, end_pos)
        
            start_pos = end_pos

        # Update UI based on results
        match_count = len(self.search_matches)
        if match_count > 0:
            self.messages(2, 9, f"Found {match_count} match(es)")
            self.prev_button.config(state="normal")
            self.next_button.config(state="normal")
            self.jump_to_match(0)  # Jump to first match
        else:
            self.messages(2, 3, "No matches found")
            self.prev_button.config(state="disabled")
            self.next_button.config(state="disabled")

    def search_next(self):
        """Jump to the next search match"""
        if not self.search_matches:
            return

        self.current_match_index = (self.current_match_index + 1) % len(self.search_matches)
        self.jump_to_match(self.current_match_index)

    def search_previous(self):
        """Jump to the previous search match"""
        if not self.search_matches:
            return
        
        self.current_match_index = (self.current_match_index - 1) % len(self.search_matches)
        self.jump_to_match(self.current_match_index)

    def jump_to_match(self, index):
        """Jump to a specific match and highlight it"""
        if not self.search_matches or index < 0 or index >= len(self.search_matches):
            return
        
        # Remove current match highlighting
        self.log_text.tag_remove("search_current", "1.0", tk.END)
    
        # Get match position
        match_pos = self.search_matches[index]
        end_pos = f"{match_pos}+{len(self.search_var.get())}c"
    
        # Highlight current match
        self.log_text.tag_add("search_current", match_pos, end_pos)
    
        # Scroll to make the match visible
        self.log_text.see(match_pos)
    
        # Update status
        self.current_match_index = index
        self.messages(2, 2, f"Match {index + 1} of {len(self.search_matches)}")

    def clear_search(self):
        """Clear search highlights and reset search state"""
        self.log_text.tag_remove("search_highlight", "1.0", tk.END)
        self.log_text.tag_remove("search_current", "1.0", tk.END)
        self.search_var.set("")
        self.search_matches = []
        self.current_match_index = -1
        self.prev_button.config(state="disabled")
        self.next_button.config(state="disabled")
        self.messages(2, 2, "Search cleared")
    
    # ****************************************************************************
    # *************************** Filter Actions**********************************
    # ****************************************************************************

    def on_filter_select(self, event):
        """When a filter is selected from the listbox, load its data into the form."""
        selection = self.filter_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        # Get the filter key from the index
        filter_keys = list(self.filters.keys())
        if index >= len(filter_keys):
            return
        
        filter_key = filter_keys[index]
        filter_data = self.filters[filter_key]
        
        # Store the current edit filter key
        self.current_edit_filter_key = filter_key
        
        # Load the filter data into the form
        self.filter_string.set(filter_data['pattern'])
        self.filter_regex_var.set(filter_data.get('is_regex', False))
        self.fg_color.set(filter_data['fg_color'])
        self.bg_color.set(filter_data['bg_color'])
        self.filter_action_var.set(filter_data['action'])
        
        # For the action modifier, we need to set the modifier and also handle the voice if TTS
        action_modifier = filter_data.get('action_modifier', '')
        self.filter_action_modifier.set(action_modifier)
        
        # If the action is TTS, we also have a voice_id, so we need to set the voice combobox
        if filter_data['action'] == 'tts':
            voice_id = filter_data.get('voice_id')
            if voice_id:
                # Find the voice name by id and set the combobox
                for voice_info in self.available_voices:
                    if voice_info['id'] == voice_id:
                        self.voice_combobox.set(voice_info['name'])
                        break
            else:
                self.voice_combobox.set('')
        else:
            self.voice_combobox.set('')
        
        # Trigger the action changed to update the UI
        self.on_action_changed()
        
        # Enable the update button
        self.update_filter_btn.config(state="normal")

    def update_enhanced_filter(self):
        """Update the currently selected filter with the form data."""
        if not self.current_edit_filter_key:
            self.messages(2, 3, "No filter selected for editing")
            return

        # Get the current form data
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()

        if not filter_pattern:
            self.messages(2, 3, "Filter pattern cannot be empty")
            return

        # Create the new filter key from the current form data
        new_filter_key = f"{filter_pattern}|{action}|{action_modifier}"

        # Prepare filter data
        filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }

        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                filter_data['voice_id'] = voice_id

        # Remove the old filter (by the old key)
        old_filter_key = self.current_edit_filter_key
        if old_filter_key in self.filters:
            del self.filters[old_filter_key]

        # Remove the old filter from the listbox
        # We don't know the index of the old one, so we will refresh the entire listbox
        self.filter_listbox.delete(0, tk.END)
        for key, data in self.filters.items():
            action_display = data['action'] if data['action'] != "none" else "color only"
            modifier_display = f" ({data['action_modifier']})" if data.get('action_modifier') else ""
            if data['action'] == 'tts' and data.get('voice_id'):
                voice_name = self.get_voice_name_by_id(data['voice_id'])
                modifier_display += f" [Voice: {voice_name}]"
            display_text = f"{data['pattern']} → {action_display}{modifier_display}"
            self.filter_listbox.insert(tk.END, display_text)

        # Now add the new filter
        self.filters[new_filter_key] = filter_data

        # Also add the new filter to the listbox (we just refreshed, so we can add the new one)
        action_display = action if action != "none" else "color only"
        modifier_display = f" ({action_modifier})" if action_modifier else ""
        if action == "tts" and voice_id:
            voice_name = self.get_voice_name_by_id(voice_id)
            modifier_display += f" [Voice: {voice_name}]"
        display_text = f"{filter_pattern} → {action_display}{modifier_display}"
        self.filter_listbox.insert(tk.END, display_text)

        # Update the text widget tags: remove the old tag and add the new one
        self.log_text.tag_delete(old_filter_key)
        self.log_text.tag_configure(new_filter_key, foreground=fg, background=bg)

        # Save the filters to disk
        self.save_filters()

        # Clear the form and reset the edit state
        self.clear_filter_form()
        self.current_edit_filter_key = None
        self.update_filter_btn.config(state="disabled")

        self.messages(2, 9, "Filter updated successfully")

    def clear_filter_form(self):
        """Clear the filter form fields."""
        self.filter_string.set("")
        self.filter_regex_var.set(False)
        self.fg_color.set("black")
        self.bg_color.set("yellow")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.voice_combobox.set("")
        self.on_action_changed()

    def refresh_voices(self):
        """Populate the voice combobox with available voices"""
        self.available_voices = self.action_handler.get_available_voices()
        if not self.available_voices:
            self.messages(2, 3, "No TTS voices available")
            return
            # Create display names for the combobox
        voice_names = []
        for voice_info in self.available_voices:
            voice_names.append(voice_info['name'])

        # Update combobox values
        self.voice_combobox['values'] = voice_names

        # Auto-select first voice if available
        if voice_names:
            self.voice_combobox.set(voice_names[0])

    def get_selected_voice_id(self):
        """Get the voice ID of the currently selected voice from combobox"""
        selected_name = self.voice_combobox.get()
        self.messages(2,2,f"Voice selected: {selected_name}")
        if selected_name and self.available_voices:
            for voice_info in self.available_voices:
                if voice_info['name'] == selected_name:
                    return voice_info['id']
        return None

    def get_voice_name_by_id(self, voice_id):
        """Get voice display name by voice ID"""
        for voice_info in self.available_voices:
            if voice_info['id'] == voice_id:
                return voice_info['name']
        return "Unknown Voice"

    def test_selected_voice(self):
        """Test the selected voice with sample text"""
        voice_id = self.get_selected_voice_id()
        if not self.action_handler.tts_engine:
            self.messages(2, 3, "TTS engine not initialized")
            return
        if voice_id and self.action_handler.tts_engine:
            # Use threading to prevent GUI freezing :cite[9]
            import threading
            def speak_test():
                try:
                    if self.action_handler.tts_engine:
                        self.action_handler.tts_engine.startLoop(False)
                        if self.action_handler.tts_engine._inLoop:
                            self.action_handler.tts_engine.endLoop()
                        self.original_voice = self.action_handler.tts_engine.getProperty('voice')
                        self.action_handler.tts_engine.setProperty('voice', voice_id)
                        self.action_handler.tts_engine.say("This is a test of the selected voice")
                        self.action_handler.tts_engine.runAndWait()                 
                        self.action_handler.tts_engine.setProperty('voice', self.original_voice)
                except Exception as e:
                    self.messages(2,3,f"TTS: {e} voice: {voice_id}")
            thread = threading.Thread(target=speak_test)
            thread.daemon = True
            thread.start()

    def get_voice_name_by_id(self, voice_id):
        """Get voice name by voice id."""
        for voice_info in self.available_voices:
            if voice_info['id'] == voice_id:
                return voice_info['name']
        return ""

    def on_action_changed(self, event=None):
        """Show/hide relevant controls based on selected action"""
        action = self.filter_action_var.get()
        
        # Hide sound, tts and other by default
        self.browse_sound_btn.grid_remove()
        self.voice_combobox.grid_remove()
        self.test_voice_btn.grid_remove()
        
        # Clear modifier field
        self.filter_action_modifier.set("")
        
        # Show sound browser only for sound action
        if action == "sound":
            self.browse_sound_btn.grid()
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Click 'Browse Sound' or enter file path")
        elif action == "tts":
            self.voice_combobox.grid()  # Show voice selection for TTS
            self.test_voice_btn.grid()
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Text to speak when filter matches")
        elif action == "notification":
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Notification message")
        elif action == "dialog":
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Dialog message")
        elif action == "skip":
            self.action_modifier_entry.config(state="disabled")
            self.filter_action_modifier.set("")  # No modifier needed for skip
        else:  # "none"
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("")  # No action modifier
    
    def browse_sound_file(self):
        """Browse for sound files"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Select Sound File",
            initialdir=initial_dir,
            filetypes=[("Sound files", "*.wav *.mp3 *.ogg"), ("All files", "*.*")]
        )
        if filename:
            self.filter_action_modifier.set(filename)

    def edit_selected_filter(self):
        """Load the selected filter into the form for editing"""
        try:
            selection = self.filter_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No filter selected for editing")
                return
            
            index = selection[0]
            filter_keys = list(self.filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
            
            # Get the filter key and data
            self.original_filter_key = filter_keys[index]
            filter_data = self.filters[self.original_filter_key]
        
            # Store the key we're editing
            self.editing_filter_key = self.original_filter_key
        
            # Load filter data into form fields
            self.filter_string.set(filter_data['pattern'])
            self.filter_regex_var.set(filter_data.get('is_regex', False))
            self.fg_color.set(filter_data['fg_color'])
            self.bg_color.set(filter_data['bg_color'])
            self.filter_action_var.set(filter_data['action'])
            self.on_action_changed()
            # Refresh UI based on action type
            action_modifier = filter_data.get('action_modifier', '')
            print(f"action_modifier {filter_data.get('action_modifier', '')}")
            self.filter_action_modifier.set(filter_data['action_modifier'])
            # Load voice if it's a TTS filter
            if filter_data['action'] == 'tts' and 'voice_id' in filter_data:
                voice_id = filter_data['voice_id']
                # Find and select the voice in combobox
                for voice_info in self.available_voices:
                    if voice_info['id'] == voice_id:
                        self.voice_combobox.set(voice_info['name'])
                        break
        
            # Update UI state
            self.update_filter_btn.config(state="normal")
            self.edit_filter_btn.config(state="disabled")
        
            self.messages(2, 2, f"Editing filter: {filter_data['pattern']}")
        
        except Exception as e:
            self.messages(2, 3, f"Error loading filter for editing: {e}")

    def update_filter(self):
        """Update the currently edited filter with form values"""
        if not self.editing_filter_key:
            self.messages(2, 3, "No filter being edited")
            return
        
        # Get current form values
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()
    
        if not filter_pattern:
            self.messages(2, 3, "Filter pattern cannot be empty")
            return
    
        # Create new filter key (might be different if pattern changed)
        new_filter_key = f"{filter_pattern}|{action}|{action_modifier}"
    
        # Prepare updated filter data
        updated_filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }
    
        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                updated_filter_data['voice_id'] = voice_id
    
        # Remove the old filter and add the updated one
        if self.original_filter_key in self.filters:
            del self.filters[self.original_filter_key]
    
        # Add the updated filter (with potentially new key)
        self.filters[new_filter_key] = updated_filter_data
    
        # Refresh the listbox display
        self.refresh_filter_listbox()
    
        # Update text widget tags
        self.log_text.tag_delete(self.original_filter_key)  # Remove old tag
        self.log_text.tag_configure(new_filter_key, foreground=fg, background=bg)
    
        # Save to file
        self.save_filters()
    
        # Reset editing state
        self.cancel_edit()
    
        self.messages(2, 9, f"Filter updated: {filter_pattern}")

    def cancel_edit(self):
        """Cancel the current edit operation and clear the form"""
        self.editing_filter_key = None
        self.original_filter_key = None
    
        # Clear form fields
        self.filter_string.set("")
        self.filter_regex_var.set(False)
        self.fg_color.set("black")
        self.bg_color.set("yellow")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.voice_combobox.set("")
    
        # Reset UI state
        self.on_action_changed()
        self.update_filter_btn.config(state="disabled")
        self.edit_filter_btn.config(state="normal")
    
        # Clear listbox selection
        self.filter_listbox.selection_clear(0, tk.END)
    
        self.messages(2, 2, "Edit cancelled")
    
    def add_enhanced_filter(self):
        # If we're in edit mode, cancel it first
        if self.editing_filter_key:
            self.cancel_edit()    
        """Add a new enhanced filter with actions"""
        self.current_edit_filter_key = None
        self.update_filter_btn.config(state="disabled")
        
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()
    
        if not filter_pattern:
            self.messages(2,3,f"Filter pattern cannot be empty")
            return
    
        # Create unique key for the filter
        filter_key = f"{filter_pattern}|{action}|{action_modifier}"
    
        # Prepare filter data
        filter_data = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }
    
        # Add voice ID for TTS actions
        if action == "tts":
            voice_id = self.get_selected_voice_id()
            if voice_id:
                filter_data['voice_id'] = voice_id
    
        # Store the enhanced filter
        self.filters[filter_key] = filter_data
    
        # Update the listbox display
        action_display = action if action != "none" else "color only"
        modifier_display = f" ({action_modifier})" if action_modifier else ""
    
        # Add voice info to display for TTS filters
        if action == "tts" and voice_id:
            voice_name = self.voice_combobox.get()
            modifier_display += f" [Voice: {voice_name}]"
    
        display_text = f"{filter_pattern} → {action_display}{modifier_display}"
        self.filter_listbox.insert(tk.END, display_text)
    
        # Configure text widget tag for coloring
        self.log_text.tag_configure(filter_key, foreground=fg, background=bg)
    
        # Save filters to file
        self.save_filters(False)
    
        # Clear input fields
        self.filter_string.set("")
        self.filter_action_var.set("none")
        self.filter_action_modifier.set("")
        self.on_action_changed()  # Reset UI state
    
        self.messages(2,9,f"Filter added: {filter_pattern}")
 
    def remove_enhanced_filter(self):
        """Remove the selected enhanced filter"""
        try:
            selection = self.filter_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No filter selected")
                return
                
            index = selection[0]
            filter_key = list(self.filters.keys())[index]
            
            # Remove from filters dict
            del self.filters[filter_key]
            
            # Remove from listbox
            self.filter_listbox.delete(index)
            
            # Remove tag from text widget
            self.log_text.tag_delete(filter_key)
            
            # Save changes
            self.save_filters(False)
            self.messages(2,9,"Filter removed")

        except IndexError:
            self.messages(2,3,"No filter selected or invalid selection")
        except Exception as e:
            self.messages(2,3,f"Error removing filter: {e}")

    def on_filter_selection_change(self, event):
        """Enable edit button when a filter is selected"""
        selection = self.filter_listbox.curselection()
        if selection and not self.editing_filter_key:
            self.edit_filter_btn.config(state="normal")
        else:
            self.edit_filter_btn.config(state="disabled")

    def refresh_filter_listbox(self):
        """Refresh the filter listbox with current filters"""
        self.filter_listbox.delete(0, tk.END)

        for filter_key, filter_data in self.filters.items():
            action_display = filter_data['action'] if filter_data['action'] != "none" else "color only"
            modifier_display = f" ({filter_data['action_modifier']})" if filter_data.get('action_modifier') else ""

            # Add voice info for TTS filters
            if filter_data['action'] == "tts" and filter_data.get('voice_id'):
                voice_name = self.get_voice_name_by_id(filter_data['voice_id'])
                modifier_display += f" [Voice: {voice_name}]"

            display_text = f"{filter_data['pattern']} → {action_display}{modifier_display}"
            self.filter_listbox.insert(tk.END, display_text)

    def save_filters(self, dialog):
        """Save current filters to the configured filters file"""
        filters_file = self.filters_file_var.get()
        # If no filters file is configured but we want to save, use default
        if not filters_file:
            self.messages(2, 3, "No filters file configured")
            return False
        try:
            filters_data = {
                "version": "1.1",
                "filters": list(self.filters.values())
            }
        
            with open(filters_file, 'w', encoding='utf-8') as f:
                json.dump(filters_data, f, indent=2, ensure_ascii=False)
        
            # Update recent filters list
            self.save_json("simple", filters_file, filters_data, dialog)
            self.config_manager.update_recent_list("recent_filters", filters_file)
            self.update_recent_combos()          
            self.messages(2, 9, "Filters saved successfully")
            
            return True
        
        except Exception as e:
            self.messages(2, 3, f"Error saving filters: {e}")
            return False

    def copy_to_clipboard(self, text):
        """Copy text to system clipboard"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.messages(2, 9, "Regex copied to clipboard")
        except Exception as e:
            self.messages(2, 3, f"Failed to copy to clipboard: {e}")
            
    # ****************************************************************************
    # *****************Advanced   Filter Actions**********************************
    # ****************************************************************************

    def add_regex_field(self, field_data=None):
        """Add a new regex field row - FIXED to properly load saved data"""
        if len(self.regex_fields) >= self.max_fields:
            self.messages(2, 3, f"Maximum {self.max_fields} fields allowed")
            return

        field_frame = ttk.Frame(self.fields_scrollable_frame)
        field_frame.pack(fill=tk.X, pady=2)

        # Field number label
        field_num = len(self.regex_fields) + 1
        ttk.Label(field_frame, text=f"Field {field_num}:").pack(side=tk.LEFT, padx=(0, 5))

        # Input field - FIXED: Use field_data if provided
        field_text = tk.StringVar(value=field_data.get("text", "") if field_data else "")
        field_entry = ttk.Entry(field_frame, textvariable=field_text, width=25)
        field_entry.pack(side=tk.LEFT, padx=(0, 5))

        # Modifier combobox - FIXED: Use field_data if provided
        modifier_var = tk.StringVar(value=field_data.get("modifier", "as_string") if field_data else "as_string")
        modifier_combo = ttk.Combobox(field_frame, textvariable=modifier_var,
                                values=["as_string", "as_word", "as_regex", "predefined"],
                                state="readonly", width=12)
        modifier_combo.pack(side=tk.LEFT, padx=(0, 5))
        modifier_combo.bind('<<ComboboxSelected>>', lambda e, f=field_frame: self.on_modifier_changed(f))

        # Predefined patterns combobox - FIXED: Use field_data if provided
        predefined_var = tk.StringVar(value=field_data.get("predefined_type", "") if field_data else "")
        predefined_combo = ttk.Combobox(field_frame, textvariable=predefined_var,
                                values=list(self.predefined_patterns.keys()),
                                state="readonly", width=15)
        predefined_combo.pack(side=tk.LEFT, padx=(0, 5))
        predefined_combo.pack_forget()

        # Predefined pattern insert button
        insert_btn = ttk.Button(field_frame, text="Insert", 
                        command=lambda: self.insert_predefined_pattern(field_entry, predefined_var))
        insert_btn.pack(side=tk.LEFT, padx=(0, 5))
        insert_btn.pack_forget()

        # Scope combobox (for between fields) - FIXED: Use field_data if provided
        if len(self.regex_fields) > 0:  # Only add scope for fields after the first one
            scope_var = tk.StringVar(value=field_data.get("scope", "anything_between") if field_data else "anything_between")
            scope_combo = ttk.Combobox(field_frame, textvariable=scope_var,
                                values=["anything_between", "immediate_after", "word_boundary_between", 
                                        "whitespace_between", "specific_separator"],
                                state="readonly", width=18)
            scope_combo.pack(side=tk.LEFT, padx=(20, 5))
        
            # Store scope reference
            field_frame.scope_var = scope_var

            # Separator entry for specific_separator scope - FIXED: Use field_data if provided
            separator_var = tk.StringVar(value=field_data.get("separator", "") if field_data else "")
            separator_entry = ttk.Entry(field_frame, textvariable=separator_var, width=8)
            separator_entry.pack(side=tk.LEFT, padx=(5, 0))
            separator_entry.pack_forget()

            field_frame.separator_var = separator_var
            field_frame.separator_entry = separator_entry

            # Show/hide separator based on scope
            scope_combo.bind('<<ComboboxSelected>>', 
                        lambda e, f=field_frame: self.on_scope_changed(f))

            # Set initial scope state
            self.on_scope_changed(field_frame)
        else:
            field_frame.scope_var = None

        # Remove button
        remove_btn = ttk.Button(field_frame, text="Remove", 
                        command=lambda: self.remove_regex_field(field_frame))
        remove_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Store references
        field_frame.field_text = field_text
        field_frame.modifier_var = modifier_var
        field_frame.predefined_var = predefined_var
        field_frame.predefined_combo = predefined_combo
        field_frame.insert_btn = insert_btn

        # Set initial modifier state
        self.on_modifier_changed(field_frame)

        # Add to tracking list
        self.regex_fields.append(field_frame)

        # Update regex display
        self.update_generated_regex()

        # Update scroll region
        self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all"))

    def remove_regex_field(self, field_frame):
        """Remove a regex field"""
        if field_frame in self.regex_fields:
            self.regex_fields.remove(field_frame)
            field_frame.destroy()
            self.renumber_fields()
            self.update_generated_regex()

    def renumber_fields(self):
        """Renumber fields after removal"""
        for i, field_frame in enumerate(self.regex_fields):
            # Update the field number label
            for widget in field_frame.winfo_children():
                if isinstance(widget, ttk.Label) and "Field" in widget.cget("text"):
                    widget.config(text=f"Field {i + 1}:")
                    break

    def on_modifier_changed(self, field_frame):
        """Show/hide predefined pattern controls based on modifier"""
        modifier = field_frame.modifier_var.get()
    
        if modifier == "predefined":
            field_frame.predefined_combo.pack(side=tk.LEFT, padx=(0, 5))
            field_frame.insert_btn.pack(side=tk.LEFT, padx=(0, 5))
        else:
            field_frame.predefined_combo.pack_forget()
            field_frame.insert_btn.pack_forget()
    
        # Update regex when modifier changes
        self.update_generated_regex()

    def insert_predefined_pattern(self, field_entry, predefined_var):
        """Insert predefined pattern into field"""
        pattern_type = predefined_var.get()
        if pattern_type in self.predefined_patterns:
            field_entry.delete(0, tk.END)
            field_entry.insert(0, self.predefined_patterns[pattern_type])
            self.update_generated_regex()

    def update_generated_regex(self):
        """Generate the final regex from all fields with positional enforcement"""
        if not self.regex_fields:
            self.generated_regex.set("")
            return
    
        regex_parts = []
        first_field = True
    
        for i, field_frame in enumerate(self.regex_fields):
            field_text = field_frame.field_text.get().strip()
            modifier = field_frame.modifier_var.get()
        
            if not field_text:
                continue
        
            processed_field = self.apply_modifier(field_text, modifier)
        
            if first_field:
                regex_parts.append(processed_field)
                first_field = False
            else:
                scope = field_frame.scope_var.get() if field_frame.scope_var else "anything_between"
                previous_pattern = regex_parts[-1]
                combined_pattern = self.apply_positional_scope(previous_pattern, processed_field, scope)
                regex_parts[-1] = combined_pattern
    
        # Add final .* to match anything after the last field
        if regex_parts:
            final_regex = regex_parts[-1] + ".*"
            self.generated_regex.set(final_regex)
        else:
            self.generated_regex.set("")

    def apply_positional_scope(self, previous_pattern, current_pattern, scope):
        """Apply positional scope between fields to enforce order"""
        if scope == "anything_between":
            # Field1 followed by anything, then Field2 (your example pattern)
            return f"{previous_pattern}.*{current_pattern}"
        elif scope == "immediate_after":
            # Field2 immediately after Field1
            return f"{previous_pattern}{current_pattern}"
        elif scope == "word_boundary_between":
            # Field1 followed by Field2 with word boundaries in between
            return f"{previous_pattern}\\b.*\\b{current_pattern}"
        elif scope == "whitespace_between":
            # Field1 followed by Field2 with whitespace in between
            return f"{previous_pattern}\\s+{current_pattern}"
        elif scope == "specific_separator":
            # Field1 followed by Field2 with a specific separator
            # We'll need to add a separator input field for this
            separator = getattr(self, 'separator_var', tk.StringVar(value="")).get()
            return f"{previous_pattern}{re.escape(separator)}{current_pattern}"
        
        return f"{previous_pattern}.*{current_pattern}"  # Default

    def on_scope_changed(self, field_frame):
        """Show/hide separator entry based on scope selection"""
        scope = field_frame.scope_var.get()
    
        if scope == "specific_separator":
            field_frame.separator_entry.pack(side=tk.LEFT, padx=(5, 0))
        else:
            field_frame.separator_entry.pack_forget()
    
        # Update regex when scope changes
        self.update_generated_regex()

    def apply_modifier(self, text, modifier):
        """Apply modifier to field text to create regex pattern, now with multi-term support"""
        if not text:
            return ""

        try:
            if modifier == "as_string":
                # Check if text contains commas for multiple terms
                if ',' in text:
                    terms = [term.strip() for term in text.split(',') if term.strip()]
                    if terms:
                        escaped_terms = [re.escape(term) for term in terms]
                        return '(' + '|'.join(escaped_terms) + ')'
                # Single term (original behavior)
                return re.escape(text)

            elif modifier == "as_word":
                # Check if text contains commas for multiple terms
                if ',' in text:
                    terms = [term.strip() for term in text.split(',') if term.strip()]
                    if terms:
                        escaped_terms = [re.escape(term) for term in terms]
                        return r'\b(' + '|'.join(escaped_terms) + r')\b'
                # Single term (original behavior)
                return r'\b' + re.escape(text) + r'\b'

            elif modifier == "as_word_start":
                # Word boundary at start only (single term only for now)
                return r'\b' + re.escape(text)

            elif modifier == "as_word_end":
                # Word boundary at end only (single term only for now)  
                return re.escape(text) + r'\b'

            elif modifier == "as_regex":
                # Use as raw regex - validate it first
                try:
                    re.compile(text)
                    return text
                except re.error:
                    # Fall back to escaped version if invalid regex
                    return re.escape(text)

            elif modifier == "predefined":
                # Already a regex pattern from predefined
                try:
                    re.compile(text)
                    return text
                except re.error:
                    return re.escape(text)

            else:
                # Default to string escaping
                return re.escape(text)

        except Exception as e:
            self.messages(2, 3, f"Error applying modifier '{modifier}' to '{text}': {e}")
            return re.escape(text)  # Fallback

    def apply_scope(self, current_pattern, scope, previous_pattern):
        """Apply scope between fields"""
        if scope == "search_all":
            # Just concatenate (implicit AND)
            return current_pattern
        elif scope == "search_between":
            # Match anything between previous and current
            return r".*?" + current_pattern
        elif scope == "search_after":
            # Match current pattern after previous
            return r"(?<=" + previous_pattern + r")" + current_pattern
        elif scope == "search_before":
            # Match current pattern before previous
            return current_pattern + r"(?=" + previous_pattern + r")"
        return current_pattern

    def store_advanced_filter(self):
        """Store the current advanced filter with TTS voice support"""
        filter_name = self.advanced_filter_name.get().strip()
        if not filter_name:
            self.messages(2, 3, "Advanced filter name cannot be empty")
            return

        # Collect field data
        fields_data = []
        for field_frame in self.regex_fields:
            field_data = {
                "text": field_frame.field_text.get(),
                "modifier": field_frame.modifier_var.get(),
                "predefined_type": field_frame.predefined_var.get(),
            }

            if field_frame.scope_var:
                field_data["scope"] = field_frame.scope_var.get()
                if hasattr(field_frame, 'separator_var'):
                    field_data["separator"] = field_frame.separator_var.get()

            fields_data.append(field_data)

        # Build actions with TTS voice support
        actions = {
            "bg_color": self.advanced_bg_color.get(),
            "fg_color": self.advanced_fg_color.get(),
            "action": self.advanced_action_var.get(),
            "action_modifier": self.advanced_action_modifier.get(),
        }

        # Add TTS voice ID if available and action is TTS
        if self.advanced_action_var.get() == "tts" and hasattr(self, 'advanced_voice_combobox'):
            selected_voice_name = self.advanced_voice_combobox.get()
            if selected_voice_name and hasattr(self, 'advanced_available_voices'):
                for voice_info in self.advanced_available_voices:
                    if voice_info['name'] == selected_voice_name:
                        actions["voice_id"] = voice_info['id']
                        actions["voice_name"] = voice_info['name']
                        break

        # Create filter
        filter_key = f"advanced_{filter_name}"
        self.advanced_filters[filter_key] = {
            "name": filter_name,
            "enabled": self.advanced_filter_enabled.get(),
            "fields": fields_data,
            "generated_regex": self.generated_regex.get(),
            "actions": actions
        }

        self.refresh_advanced_filters_listbox()
        self.save_advanced_filters(False)
        self.messages(2, 9, f"Advanced filter stored: {filter_name}")

    def save_advanced_filters(self, dialog=False):
        """Save advanced filters to the configured file - FIXED VERSION"""
        advanced_filters_file = self.advanced_filters_file_var.get()

        # If no file is set but we're not using dialog, try to get from config
        if not advanced_filters_file and not dialog:
            advanced_filters_file = self.config_manager.get("advanced_filters_file", "")
            if advanced_filters_file:
                self.advanced_filters_file_var.set(advanced_filters_file)

        # If still no file and we're not using dialog, show error
        if not advanced_filters_file:
            if dialog:
                # Let the save_json handle the dialog
                pass
            else:
                self.messages(2, 3, "No advanced filters file configured")
                return False

        try:
            filters_data = {
                "version": "1.0",
                "advanced_filters": self.advanced_filters  # Direct assignment
            }

            print(f"DEBUG: Saving {len(self.advanced_filters)} advanced filters")  # Debug

            # Use the existing save_json method
            return self.save_json("advanced", advanced_filters_file, filters_data, dialog)

        except Exception as e:
            self.messages(2, 3, f"Error saving advanced filters: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_advanced_filters_auto(self):
        """Load advanced filters from the configured file - FIXED VERSION"""
        advanced_filters_file = self.advanced_filters_file_var.get()
        if not advanced_filters_file or not os.path.exists(advanced_filters_file):
            return

        try:
            with open(advanced_filters_file, 'r', encoding='utf-8') as f:
                filters_data = json.load(f)

            # Clear current advanced filters
            self.advanced_filters.clear()
        
            # Load new advanced filters - FIXED: Proper access to nested structure
            advanced_filters_data = filters_data.get("advanced_filters", {})
            print(f"DEBUG: Found {len(advanced_filters_data)} advanced filters in file")  # Debug

            for filter_key, filter_data in advanced_filters_data.items():
                self.advanced_filters[filter_key] = filter_data
                print(f"DEBUG: Loaded filter: {filter_data.get('name', 'Unnamed')}")  # Debug

            # Refresh listbox
            self.refresh_advanced_filters_listbox()

            # Update recent filters list
            self.config_manager.update_recent_list("recent_advanced_filters", advanced_filters_file)
            self.update_recent_combos()

            self.messages(2, 9, f"Loaded {len(self.advanced_filters)} advanced filters")

        except Exception as e:
            self.messages(2, 3, f"Error loading advanced filters: {e}")
            import traceback
            traceback.print_exc()  # This will show the exact error

    def load_advanced_filter(self):
        """Load selected advanced filter into form with TTS voice support"""
        selection = self.advanced_filters_listbox.curselection()
        if not selection:
            self.messages(2, 3, "No advanced filter selected")
            return

        index = selection[0]
        filter_keys = list(self.advanced_filters.keys())
        if index >= len(filter_keys):
            self.messages(2, 3, "Invalid filter selection")
            return

        filter_key = filter_keys[index]
        filter_data = self.advanced_filters[filter_key]

        # Clear current form
        self.clear_advanced_form()

        # Load basic info
        self.advanced_filter_name.set(filter_data.get("name", ""))
        self.advanced_filter_enabled.set(filter_data.get("enabled", True))

        # Load fields
        fields_data = filter_data.get("fields", [])
        self.clear_all_regex_fields()
    
        for field_data in fields_data:
            self.add_regex_field(field_data)

        # Load actions with TTS voice support
        actions = filter_data.get("actions", {})
        self.advanced_bg_color.set(actions.get("bg_color", "yellow"))
        self.advanced_fg_color.set(actions.get("fg_color", "black"))
        self.advanced_action_var.set(actions.get("action", "none"))
        self.advanced_action_modifier.set(actions.get("action_modifier", ""))

        # Load TTS voice if available
        if actions.get("action") == "tts" and "voice_id" in actions:
            voice_id = actions["voice_id"]
            # Set the voice in the combobox
            if hasattr(self, 'advanced_voice_combobox') and hasattr(self, 'advanced_available_voices'):
                for voice_info in self.advanced_available_voices:
                    if voice_info['id'] == voice_id:
                        self.advanced_voice_combobox.set(voice_info['name'])
                        break

        # Load generated regex
        if "generated_regex" in filter_data:
            self.generated_regex.set(filter_data["generated_regex"])

        # Update UI for action type
        self.on_advanced_action_changed()

        self.editing_advanced_filter_key = filter_key
        self.messages(2, 2, f"Editing advanced filter: {filter_data.get('name', 'Unnamed')}")
   
    def perform_test():
        text = test_text.get(1.0, tk.END).strip()
        try:
            matches = re.findall(regex_pattern, text)
            if matches:
                result_var.set(f"✓ Found {len(matches)} match(es)")
                result_label.config(foreground="green")
            else:
                result_var.set("✗ No matches found")
                result_label.config(foreground="red")
        except re.error as e:
            result_var.set(f"✗ Regex error: {e}")
            result_label.config(foreground="red")
    
        ttk.Button(test_window, text="Test", command=perform_test).pack(pady=5)

    def clear_advanced_form(self):
        """Clear the advanced filter form - FIXED to properly reset state"""
        try:
            # Clear basic form fields
            self.advanced_filter_name.set("")
            self.advanced_filter_enabled.set(True)

            # Clear action fields
            self.advanced_fg_color.set("black")
            self.advanced_bg_color.set("yellow")
            self.advanced_action_var.set("none")
            self.advanced_action_modifier.set("")

            # Hide TTS voice selection
            if hasattr(self, 'advanced_voice_combobox'):
                self.advanced_voice_combobox.grid_remove()
                self.advanced_voice_combobox.set("")

            # Clear all regex fields
            self.clear_all_regex_fields()

            # Reset editing state
            self.editing_advanced_filter_key = None

            # Clear generated regex display
            self.generated_regex.set("")

            # Add one empty field to start fresh
            self.add_regex_field()

            # Reset UI state for actions
            self.on_advanced_action_changed()

            # Clear listbox selection
            if hasattr(self, 'advanced_filters_listbox'):
                self.advanced_filters_listbox.selection_clear(0, tk.END)

            self.messages(2, 2, "Advanced form cleared")

        except Exception as e:
            self.messages(2, 3, f"Error clearing advanced form: {e}")

    def clear_all_regex_fields(self):
        """Remove all regex field widgets from the form"""
        if hasattr(self, 'regex_fields'):
            # Destroy all field frames
            for field_frame in self.regex_fields:
                try:
                    field_frame.destroy()
                except:
                    pass  # Widget might already be destroyed
        
            # Clear the list
            self.regex_fields.clear()
    
        # Also clear the scrollable frame children
        if hasattr(self, 'fields_scrollable_frame'):
            for widget in self.fields_scrollable_frame.winfo_children():
                try:
                    widget.destroy()
                except:
                    pass
    
        # Update scroll region
        if hasattr(self, 'fields_canvas'):
            self.fields_canvas.configure(scrollregion=self.fields_canvas.bbox("all"))

    def delete_advanced_filter(self):
        """Delete the selected advanced filter"""
        try:
            selection = self.advanced_filters_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No advanced filter selected for deletion")
                return
            
            index = selection[0]
            filter_keys = list(self.advanced_filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
        
            filter_key = filter_keys[index]
            filter_name = self.advanced_filters[filter_key]["name"]
        
            # Confirm deletion
            confirm = messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the advanced filter '{filter_name}'?")
        
            if confirm:
                # Remove from dictionary
                del self.advanced_filters[filter_key]
                
                # Update listbox
                self.refresh_advanced_filters_listbox()
                
                # Save changes
                self.save_advanced_filters()
                
                # Clear form if we were editing this filter
                if self.editing_advanced_filter_key == filter_key:
                    self.clear_advanced_form()
            
                self.messages(2, 9, f"Advanced filter deleted: {filter_name}")
            
        except Exception as e:
            self.messages(2, 3, f"Error deleting advanced filter: {e}")

    def toggle_advanced_filter(self):
        """Toggle enabled/disabled state of selected advanced filter"""
        try:
            selection = self.advanced_filters_listbox.curselection()
            if not selection:
                self.messages(2, 3, "No advanced filter selected")
                return
            
            index = selection[0]
            filter_keys = list(self.advanced_filters.keys())
            if index >= len(filter_keys):
                self.messages(2, 3, "Invalid filter selection")
                return
        
            filter_key = filter_keys[index]
            filter_data = self.advanced_filters[filter_key]
        
            # Toggle enabled state
            filter_data["enabled"] = not filter_data["enabled"]
            new_state = "enabled" if filter_data["enabled"] else "disabled"
        
            # Update listbox display
            self.refresh_advanced_filters_listbox()
        
            # Save changes
            self.save_advanced_filters()
        
            self.messages(2, 9, f"Advanced filter {new_state}: {filter_data['name']}")
        
        except Exception as e:
            self.messages(2, 3, f"Error toggling advanced filter: {e}")

    def refresh_advanced_filters_listbox(self):
        """Refresh the advanced filters listbox display - FIXED VERSION"""
        if not hasattr(self, 'advanced_filters_listbox'):
            return

        self.advanced_filters_listbox.delete(0, tk.END)

        for filter_key, filter_data in self.advanced_filters.items():
            status = "✓" if filter_data.get("enabled", True) else "✗"
            filter_name = filter_data.get("name", "Unnamed Filter")
            display_text = f"{status} {filter_name}"
            self.advanced_filters_listbox.insert(tk.END, display_text)

        print(f"DEBUG: Listbox refreshed with {len(self.advanced_filters)} filters")  # Debug

    def on_advanced_action_changed(self, event=None):
        """Show/hide relevant controls based on selected advanced action - IMPROVED"""
        action = self.advanced_action_var.get()

        # Hide TTS controls by default
        if hasattr(self, 'advanced_voice_combobox'):
            self.advanced_voice_combobox.grid_remove()

        # Show voice selection for TTS actions
        if action == "tts":
            if hasattr(self, 'advanced_voice_combobox'):
                self.advanced_voice_combobox.grid()
                # Load voices if not already loaded
                if not hasattr(self, 'advanced_available_voices') or not self.advanced_available_voices:
                    self.refresh_advanced_voices()

    def refresh_advanced_voices(self):
        """Refresh available voices for advanced filters with better error handling"""
        try:
            self.advanced_available_voices = self.action_handler.get_available_voices()
            if self.advanced_available_voices:
                voice_names = [voice['name'] for voice in self.advanced_available_voices]
                self.advanced_voice_combobox['values'] = voice_names
                # Don't auto-select, preserve current selection if any
            else:
                self.messages(2, 3, "No TTS voices available")
        except Exception as e:
            self.messages(2, 3, f"Error loading voices: {e}")

    def test_generated_regex(self):
        """Test the generated regex with sample input - COMPLETE IMPLEMENTATION"""
        regex_pattern = self.generated_regex.get()
        if not regex_pattern:
            self.messages(2, 3, "No regex generated to test")
            return

        # Create test dialog
        test_window = tk.Toplevel(self.root)
        test_window.title("Test Regex Pattern")
        test_window.geometry("600x400")
        test_window.transient(self.root)
        test_window.grab_set()

        # Main content frame
        main_frame = ttk.Frame(test_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Regex pattern display
        ttk.Label(main_frame, text="Regex Pattern to Test:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(0, 5))

        pattern_frame = ttk.Frame(main_frame)
        pattern_frame.pack(fill=tk.X, pady=(0, 10))
    
        pattern_text = tk.Text(pattern_frame, height=2, wrap=tk.WORD, font=("Courier", 9))
        pattern_text.pack(side=tk.LEFT, fill=tk.X, expand=True)
        pattern_text.insert(1.0, regex_pattern)
        pattern_text.config(state=tk.DISABLED)  # Make it read-only
    
        # Test input area
        ttk.Label(main_frame, text="Enter text to test against the regex:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
        test_text = tk.Text(main_frame, height=8, wrap=tk.WORD)
        test_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
    
        # Add some sample text for quick testing
        sample_text = "This is sample text. You can enter your own text here to test the regex pattern.\nExample: This line contains uno and dos"
        test_text.insert(1.0, sample_text)

        # Results area
        result_frame = ttk.LabelFrame(main_frame, text="Test Results", padding="5")
        result_frame.pack(fill=tk.X, pady=(0, 10))

        self.test_result_var = tk.StringVar(value="Click 'Run Test' to see results")
        result_label = ttk.Label(result_frame, textvariable=self.test_result_var, wraplength=550)
        result_label.pack(fill=tk.X)

        # Match details
        self.match_details_var = tk.StringVar(value="")
        match_details_label = ttk.Label(result_frame, textvariable=self.match_details_var, 
                                    foreground="blue", wraplength=550)
        match_details_label.pack(fill=tk.X)

        # Button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)

        def perform_test():
            """Execute the regex test and display results"""
            text = test_text.get(1.0, tk.END).strip()
            if not text:
                self.test_result_var.set("Please enter some text to test")
                result_label.config(foreground="red")
                return

            try:
                # Test the regex
                pattern = self.generated_regex.get()
                matches = list(re.finditer(pattern, text, re.MULTILINE | re.DOTALL))

                if matches:
                    # Show successful results
                    self.test_result_var.set(f"✓ SUCCESS: Found {len(matches)} match(es)")
                    result_label.config(foreground="green")
                
                    # Show match details
                    match_info = []
                    for i, match in enumerate(matches, 1):
                        match_text = match.group(0)
                        # Truncate long matches for display
                        if len(match_text) > 100:
                            match_text = match_text[:100] + "..."
                        match_info.append(f"Match {i}: '{match_text}' (position {match.start()}-{match.end()})")

                    self.match_details_var.set("\n".join(match_info))

                else:
                    # No matches found
                    self.test_result_var.set("✗ NO MATCHES: The regex pattern did not match any text")
                    result_label.config(foreground="red")
                    self.match_details_var.set("")

            except re.error as e:
                # Regex syntax error
                self.test_result_var.set(f"✗ REGEX ERROR: {e}")
                result_label.config(foreground="red")
                self.match_details_var.set("")
            except Exception as e:
                # Other errors
                self.test_result_var.set(f"✗ TEST ERROR: {e}")
                result_label.config(foreground="red")
                self.match_details_var.set("")

        def clear_input():
            """Clear the test input area"""
            test_text.delete(1.0, tk.END)

        def use_current_log_line():
            """Use the currently selected line from the log as test input"""
            try:
                # Try to get selected text from log display
                selected_text = self.log_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if selected_text:
                    test_text.delete(1.0, tk.END)
                    test_text.insert(1.0, selected_text)
                else:
                    # If no selection, get the last line from log
                    last_line = self.log_text.get("end-2l linestart", "end-1l lineend")
                    if last_line.strip():
                        test_text.delete(1.0, tk.END)
                        test_text.insert(1.0, last_line)
                    else:
                        self.messages(2, 3, "No text available in log")
            except tk.TclError:
                # No text selected
                self.messages(2, 3, "No text selected in log")
    # Buttons
        ttk.Button(button_frame, text="Run Test", command=perform_test).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Clear Input", command=clear_input).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Use Log Text", command=use_current_log_line).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Close", command=test_window.destroy).pack(side=tk.RIGHT)

        # Set focus to test text area
        test_text.focus_set()
    
        # Run initial test with sample text
        test_window.after(100, perform_test)

    # ****************************************************************************
    # *************************** Config Actions  ********************************
    # ****************************************************************************

    def browse_log_file(self):
        """Browse for log file and update last directory"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Select Log File",
            initialdir=initial_dir
        )
        if filename:
            self.log_file_var.set(str(Path(filename)))
            self.config_manager.set("last_directory", str(Path(filename).parent))
    
    def browse_filter_file(self, config_type):
        """Browse for configuration files - ENHANCED for advanced filters"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title=f"Select {config_type.replace('_', ' ').title()}",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.config_manager.set("last_directory", str(Path(filename).parent))

            if config_type == "filters_file":
                self.filters_file_var.set(filename)
                self.load_filters()
                self.config_manager.update_recent_list("recent_filters", filename)

            elif config_type == "advanced_filters_file":
                self.advanced_filters_file_var.set(filename)
                self.load_advanced_filters_auto()  # This should now work correctly
                self.config_manager.update_recent_list("recent_advanced_filters", filename)

            self.update_recent_combos()

    def update_recent_combos(self):
        """Update the recent files comboboxes"""
        self.recent_filters_combo['values'] = self.config_manager.get("recent_filters", [])
        self.recent_adv_filters_combo['values'] = self.config_manager.get("recent_advanced_filters", [])
    
    def on_recent_filters_selected(self, event=None):
        """When a recent filters file is selected - FIXED"""
        selected_file = self.recent_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.filters_file_var.set(selected_file)
            self.load_filters()
        else:
            self.messages(2, 3, "Selected file does not exist")

    def on_recent_adv_filters_selected(self, event=None):
        """When a recent advanced filters file is selected - FIXED"""
        selected_file = self.recent_adv_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.advanced_filters_file_var.set(selected_file)
            self.load_advanced_filters_auto()
        else:
            self.messages(2, 3, "Selected file does not exist")

    def save_configuration_dialog(self):
        """Open a save dialog to choose configuration file location"""
        try:
            # Set up file types
            file_types = [
                ('JSON files', '*.json'),
                ('All Files', '*.*')
            ]
        
            # Get current directory from config manager if available
            initial_dir = self.config_manager.get("last_directory", "")
            
            # Open save file dialog
            filename = filedialog.asksaveasfilename(
                title="Save Configuration As",
                defaultextension=".json",
                filetypes=file_types,
                initialdir=initial_dir,
                initialfile="etail_config.json"  # Default file name
            )
        
            if filename:
                # Update last directory in config
                self.config_manager.set("last_directory", str(Path(filename).parent))
                
                # Call your existing save logic
                if self.save_configuration(filename):
                    self.messages(2,9,f"Configuration saved to {filename}")
                else:
                    self.messages(2,3,"Failed to save configuration 1035")
                    
        except Exception as e:
            self.messages(2,3,f"Error saving file: {e}")
    
    def save_configuration(self, config_path=None):
        """Save current configuration to file"""
        # Update config manager with current values
        self.config_manager.set("log_file", self.log_file_var.get())
        self.config_manager.set("filters_file", self.filters_file_var.get())
        self.config_manager.set("advanced_filters_file", self.advanced_filters_file_var.get())

        try:
            self.config_manager.set("initial_lines", int(self.initial_lines_var.get()))
        except ValueError:
            self.messages(2, 3, "Invalid initial lines value, using default")
            self.config_manager.set("initial_lines", 50)

        try:
            self.config_manager.set("refresh_interval", int(self.refresh_interval_var.get()))
        except ValueError:
            self.messages(2, 3, "Invalid refresh interval, using default")
            self.config_manager.set("refresh_interval", 100)
        
        self.config_manager.set("auto_load_config", self.auto_load_var.get())

        if config_path:
            self.config_manager.config_file = Path(config_path)

        if self.config_manager.save_config():
            self.messages(2, 9, "Configuration saved successfully")
            return True
        else:
            self.messages(2, 3, "Failed to save configuration")
            return False

    def load_configuration_file(self):
        """Browse for configuration files"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title="Load configuration",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            with open(filename, 'r', encoding='utf-8') as f:
                a_config = json.load(f)
            # Update default config with loaded values
            self.config_manager.config_file = Path(filename)
            self.config_manager.config.update(a_config)
            self.load_configuration()

    def load_configuration(self):
        """Load configuration from file and update UI"""
        self.config_manager.load_config()

        # Update UI with loaded values
        self.log_file_var.set(self.config_manager.get("log_file", ""))
        self.filters_file_var.set(self.config_manager.get("filters_file", ""))
        self.advanced_filters_file_var.set(self.config_manager.get("advanced_filters_file", ""))
        self.initial_lines_var.set(str(self.config_manager.get("initial_lines", 50)))
        self.refresh_interval_var.set(str(self.config_manager.get("refresh_interval", 100)))
        self.auto_load_var.set(self.config_manager.get("auto_load_config", True))
        
        self.update_recent_combos()
        self.messages(2,9,f"Configuration loaded successfully")
    
    def reset_configuration(self):
        """Reset configuration to defaults"""
        self.config_manager.config = self.config_manager.load_default_config()
        self.load_configuration()
        self.messages(2,9,f"Configuration reset to defaults")

    def create_empty_default_filters(self):
        """Create an empty default filters file"""
        try:
            default_filters_path = self.config_manager.get_default_filters_path()

            empty_filters = {
                "version": "1.1",
                "filters": []
            }
        
            with open(default_filters_path, 'w', encoding='utf-8') as f:
                json.dump(empty_filters, f, indent=2, ensure_ascii=False)
        
            self.messages(2, 9, "Created empty default filters file")
            return True

        except Exception as e:
            self.messages(2, 3, f"Error creating default filters: {e}")
            return False

    def debug_advanced_filters(self):
        """Debug method to check what's happening with advanced filters"""
        print("\n=== ADVANCED FILTERS DEBUG ===")
        print(f"Total advanced filters: {len(self.advanced_filters)}")
        print(f"Listbox items: {self.advanced_filters_listbox.size() if hasattr(self, 'advanced_filters_listbox') else 'No listbox'}")
    
        for key, data in self.advanced_filters.items():
            print(f"Filter Key: {key}")
            print(f"  Name: {data.get('name', 'Unnamed')}")
            print(f"  Enabled: {data.get('enabled', 'Unknown')}")
            print(f"  Fields: {len(data.get('fields', []))}")
            print(f"  Regex: {data.get('generated_regex', 'None')}")
            print(f"  Actions: {data.get('actions', {})}")
        print("==============================\n")
        
    def test_advanced_filter_loading(self):
        """Test method to verify advanced filters are working"""
        print("\n=== ADVANCED FILTERS TEST ===")
        print(f"Filters in memory: {len(self.advanced_filters)}")

        # Test if filters are being applied to log lines
        test_line = "This line contains uno and dos"
        for filter_key, filter_data in self.advanced_filters.items():
            if filter_data.get('enabled', True):
                regex = filter_data.get('generated_regex', '')
                if regex:
                    try:
                        match = re.search(regex, test_line)
                        if match:
                            print(f"✓ Filter '{filter_data.get('name')}' matches test line")
                        else:
                            print(f"✗ Filter '{filter_data.get('name')}' does NOT match test line")
                    except Exception as e:
                        print(f"✗ Filter '{filter_data.get('name')}' has invalid regex: {e}")

        print("=============================\n")

    # Add this temporarily to test - call it after loading filters

    # ****************************************************************************
    # *************************** Tail Actions  **********************************
    # ****************************************************************************
    def start_tail(self):
        """Start tailing the log file in a separate thread."""
        #self.config_manager.get("log_file", "") #Get from config file
        filepath = Path(self.log_file_var.get()) #Get from UI var
        if not filepath or not filepath.exists():
            self.messages(2,3,f"File {filepath} can't be accessed.")
            return
        
        # Get number of initial lines to display
        try:
            num_initial_lines = int(self.initial_lines_var.get())
        except:
            num_initial_lines = 50
        
        # Display last N lines instead of entire file
        encoding = self.simple_encoding_detect(filepath)
        last_lines = self.get_last_lines(filepath, num_initial_lines, encoding)
        if last_lines == []:
            print("Falling back to utf-8")
            encoding = "utf-8"
            last_lines = self.get_last_lines(filepath, num_initial_lines, "utf-8")
        self.encoding_label.config(text=f"Encoding: {encoding} ")
        
        self.log_text.delete(1.0, tk.END)  # Clear display
        for line in last_lines:
            self.update_display(line)
        
        # Start tailing from current end of file
        self.last_position = os.path.getsize(filepath)
        self.stop_event.clear()
        self.tail_thread = Thread(target=self.tail_loop, daemon=True)
        self.tail_thread.start()
        self.pause_button['state']="normal"
        self.stop_button['state']="normal"
        self.start_button['state']="disabled"
        self.status_label.config(text="Running", foreground="green")
        self.messages(2,0,f"Started tailing: {filepath} (showing last {num_initial_lines} lines)")

    def toggle_pause(self):
        """Pause or resume log updates."""
        self.pause_var.set(not self.pause_var.get())
        if self.pause_var.get():
            self.status_label.config(text="PAUSED", foreground="orange")
            self.messages(2,4,"")
            self.stop_button['state']="disabled"
            self.pause_button.config(text="Resume")
        else:
            self.pause_button.config(text="Pause")
            self.stop_button['state']="normal"
            self.status_label.config(text="Resumed", foreground="orange")
            self.messages(2,0,"")
            
    def stop_tail(self):
        """Stop the tailing process."""
        self.pause_button['state']="disabled"
        self.stop_button['state']="disabled"
        self.start_button['state']="normal"
        self.stop_event.set()
        if self.tail_thread and self.tail_thread.is_alive():
            self.tail_thread.join(timeout=2.0)
        self.messages(2,1,"Stopped tailing")
        self.status_label.config(text=mssgs[1], foreground="red")
    
    def tail_loop(self):
        """Efficient tailing loop that only reads new content."""
        filepath = Path(self.log_file_var.get()) #Get from UI var
        if not filepath or not os.path.exists(filepath):
            self.messages(2, 3, f"Log file not found: {filepath}")
            return

        encoding = self.simple_encoding_detect(filepath)
        error_count = 0
        max_errors = 5
        file_rotation_detected = False

        while not self.stop_event.is_set():
            try:
                if not os.path.exists(filepath):
                    self.messages(2, 3, f"Log file disappeared: {filepath}")
                    time.sleep(2)
                    continue

                current_size = os.path.getsize(filepath)

            # Handle file rotation or truncation
                if current_size < self.last_position:
                    self.messages(2, 2, "Log file was rotated/truncated, resetting position")
                    self.last_position = 0
                    file_rotation_detected = True

                # Read new content
                if current_size > self.last_position or file_rotation_detected:
                    self.status_label.config(text="Running", foreground="green")
                    with open(filepath, 'r', encoding=encoding, errors='replace') as file:
                        file.seek(self.last_position)
                        new_lines = file.readlines()

                        for line in new_lines:
                            if self.stop_event.is_set():
                                break
                            # Only process if not paused
                            if not self.pause_var.get():
                                self.root.after(0, self.update_display, line.rstrip())

                        self.last_position = file.tell()
                        file_rotation_detected = False
                    error_count = 0  # Reset error count on success

                time.sleep(0.1)  # Small sleep to prevent CPU overload

            except PermissionError:
                self.messages(2, 3, f"Permission denied accessing: {filepath}")
                time.sleep(2)

            except Exception as e:
                error_count += 1
                if error_count >= max_errors:
                    self.messages(2, 3, f"Multiple errors in tail loop, stopping: {e}")
                    break
                print(f"Error in tail loop (attempt {error_count}): {e}")
                time.sleep(1)
  
    def update_display(self, line):
        """Update the log display with highlighting and execute actions"""
        if not line:
            return

        # Call plugin on_log_line method
        self.plugin_manager.call_plugin_method('on_log_line', line)

        # Check if any filter matches and should skip the line
        should_skip = self.check_actions_before_display(line)
        if should_skip:
            return

        # Insert the line at the end
        self.log_text.insert(tk.END, line + "\n")

        # Apply coloring and execute non-skip actions
        self.apply_filters_and_actions(line)

        # Auto-scroll to the bottom
        self.log_text.see(tk.END)
        self.log_text.update()        

        """
        # Auto-scroll with less frequent updates for better performance
        if lines_count % 10 == 0:  # Scroll every 10 lines
            self.log_text.see(tk.END)
        """

        # Optional: Limit total lines to prevent memory bloat
        lines_count = int(self.log_text.index('end-1c').split('.')[0])
        if lines_count > 10000:  # Keep last 10,000 lines
            self.log_text.delete(1.0, "1000.0")  # Remove first 5,000 lines

    def check_actions_before_display(self, line):
        """Check if any filter wants to skip this line"""
        # Check simple filters
        for filter_str, filter_data in self.filters.items():
            if self.line_matches_filter(line, filter_data):
                action = filter_data.get('action', 'none')
                if action == 'skip':
                    return True
    
        # Check advanced filters for skip actions
        for filter_key, filter_data in self.advanced_filters.items():
            if filter_data.get('enabled', True):
                if self.line_matches_advanced_filter(line, filter_data):
                    actions = filter_data.get('actions', {})
                    action = actions.get('action', 'none')
                    if action == 'skip':
                        return True
        return False

    def apply_filters_and_actions(self, line):
        """Apply coloring and execute actions for matching filters (both simple and advanced)"""
        start_index = self.log_text.index("end-2l")
        end_index = self.log_text.index("end-1c")
    
        # Apply simple filters
        for filter_str, filter_data in self.filters.items():
            if self.line_matches_filter(line, filter_data):
                # Apply coloring
                self.log_text.tag_add(filter_str, start_index, end_index)

                # Call plugin on_filter_match method
                self.plugin_manager.call_plugin_method('on_filter_match', filter_data, line)

                # Execute action (if not skip, since we already handled that)
                action = filter_data.get('action', 'none')
                if action != 'skip' and action != 'none':
                    modifier = filter_data.get('action_modifier', '')
                    if action == "tts":
                        voice = filter_data.get('voice_id', '')
                        modifier = (filter_data.get('action_modifier', ''), filter_data.get('voice_id', ''))
                    self.action_handler.execute_action(action, modifier, line)

        # Apply advanced filters
        for filter_key, filter_data in self.advanced_filters.items():
            if filter_data.get('enabled', True):  # Only process enabled advanced filters
                if self.line_matches_advanced_filter(line, filter_data):
                    # Apply advanced filter coloring and actions
                    self.apply_advanced_filter_actions(filter_key, filter_data, start_index, end_index, line)

    def line_matches_advanced_filter(self, line, filter_data):
        """Check if a line matches an advanced filter pattern"""
        regex_pattern = filter_data.get('generated_regex', '')
        if not regex_pattern:
            return False
        try:
            return bool(re.search(regex_pattern, line))
        except re.error as e:
            self.messages(2, 3, f"Advanced filter regex error: {e}")
            return False

    def apply_advanced_filter_actions(self, filter_key, filter_data, start_index, end_index, line):
        """Apply coloring and actions for advanced filters"""
        actions = filter_data.get('actions', {})

        # Create a unique tag for this advanced filter
        tag_name = f"advanced_{filter_key}"
    
        # Configure the tag if not already configured
        if tag_name not in self.log_text.tag_names():
            bg_color = actions.get('bg_color', 'yellow')
            fg_color = actions.get('fg_color', 'black')
            self.log_text.tag_configure(tag_name, foreground=fg_color, background=bg_color)

        # Apply the tag
        self.log_text.tag_add(tag_name, start_index, end_index)

        # Execute advanced filter actions
        action = actions.get('action', 'none')
        if action != 'none':
            modifier = actions.get('action_modifier', '')
            if action == "tts":
                voice = actions.get('voice_id', '')
                modifier = (actions.get('action_modifier', ''), actions.get('voice_id', ''))
            self.action_handler.execute_action(action, modifier, line)

    def line_matches_filter(self, line, filter_data):
        """Check if a line matches a filter pattern"""
        pattern = filter_data['pattern']
        is_regex = filter_data.get('is_regex', False)
        if is_regex:
            try:
                return bool(re.findall(pattern, line))
            except re.error:
                return pattern in line
        else:
            return pattern in line

    def detect_log_rotation(self, filepath):
        """Detect if log file has been rotated"""
        try:
            current_inode = os.stat(filepath).st_ino
            if hasattr(self, 'last_inode'):
                if current_inode != self.last_inode:
                    self.last_inode = current_inode
                    return True
            else:
                self.last_inode = current_inode
            return False
        except:
            return False

    # ****************************************************************************
    # *************************** Main          **********************************
    # ****************************************************************************    
if __name__ == "__main__":
    root = tk.Tk()
    app = LogTailApp(root)
    root.mainloop()