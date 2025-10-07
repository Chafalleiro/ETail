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
from pathlib import Path
import pygame
import pyttsx3
import platform

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
# *************************** Config******************************************
# ****************************************************************************
class ConfigManager:
    def __init__(self, config_file="~/.etail/config.json"):
        self.config_file = Path(config_file).expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.config = self.load_default_config()
        self.load_config()
        
    def __getitem__(self, key):
        """Allow dictionary-style access: config_manager['log_file']"""
        return self.config.get(key)

    def __setitem__(self, key, value):
        """Allow dictionary-style assignment: config_manager['log_file'] = 'path'"""
        self.config[key] = value

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
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"Configuration saved successfully")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False
    
    def update_recent_list(self, list_name, file_path, max_entries=5):
        """Update a recent files list, maintaining max entries"""
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
    
    def get(self, key, default=None):
        return self.config.get(key, default)
    
    def set(self, key, value):
        self.config[key] = value

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
        """Initialize text-to-speech engine"""
        try:
            self.tts_engine = pyttsx3.init("sapi5")
            self.voices = self.tts_engine.getProperty('voices')
            for voice in self.voices:
                print(f"voices: {voice.id}")
                print(f"voices: {voice.name}")
            # Set speech properties
            self.tts_engine.setProperty('rate', 150)
            self.tts_engine.setProperty('volume', 0.8)          
        except Exception as e:
            print(f"TTS initialization failed: {e}")
            self.tts_engine = None
    
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
                text = modifier if modifier else line_content
                self.speak_text(text)
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
    
    def speak_text(self, text):
        """Speak text using TTS in a separate thread"""
        def _speak():
            try:
                if self.tts_engine:
                    self.tts_engine.startLoop(False)
                    if self.tts_engine._inLoop:
                        self.tts_engine.endLoop()
                    self.tts_engine.setProperty('voice', self.voices[1].id)
                    self.tts_engine.say(text)
                    self.tts_engine.runAndWait()
            except Exception as e:
                print(f"TTS error: {e} filter: {text} 5")
        tts_thread = threading.Thread(target=_speak, daemon=True)
        tts_thread.start()
    
    def show_notification(self, message):
        """Show a system notification"""
        # For now, we'll use a simple dialog. Could be enhanced with toast notifications
        self.root.after(0, lambda: messagebox.showinfo("ETail Notification", message))
    
    def show_dialog(self, message):
        """Show a dialog window"""
        self.root.after(0, lambda: messagebox.showwarning("ETail Alert", message))

class LogTailApp:
# ****************************************************************************
# *************************** Inits*******************************************
# ****************************************************************************

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
    
    def __init__(self, root):
        self.root = root
        self.root.title("Etail 0.3")
        root.iconbitmap('Etail.ico')
        
        # Initialize configuration manager
        self.config_manager = ConfigManager()
        # Initialize Action manager
        self.action_handler = ActionHandler(root)
        # Control variables
        self.stop_event = Event()
        self.tail_thread = None
        self.last_position = 0  # Track file position
        self.filters = {}
        
        self.setup_encoding_detector()
        self.create_widgets()
        self.messages(2,2,"")
        # Auto-load if enabled
        if self.config_manager.get("auto_load_config", True):
            self.load_configuration()
    def messages(self,par_1,par_2,par_3):
        """
        Display controlled status and error messages
        First arg is the index of the message.
        If "Custom" is passed then second arg is a string with the message to display.
        
        Second arg where to display
        0 - Console
        1 - Status bar
        2 - Both
        
        Third is a aditional variable for messages, filename, line, or other runtime info.
        
        Example:
        self.test = "test"
        self.messages(2,2,f"reading last lines:{self.test}")
        """
        self.str_out = f"{mssgs[par_2]} {par_3}"
        match par_1:
            case 0:
                print(self.str_out)
            case 1:
                self.update_status(self.str_out)
            case 2:
                print(self.str_out)
                self.update_status(self.str_out)

# *********************************************************************
    def setup_encoding_detector(self):
        """Initialize the encoding detection function."""
        self.detect_encoding = self.simple_encoding_detect

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
# *********************************************************************
# ****************************************************************************
# *************************** Screen******************************************
# ****************************************************************************   
    def create_widgets(self):
        """Create and arrange the GUI components with tabs."""
        # Create notebook (tab container)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        # Create tabs
        self.log_tab = ttk.Frame(notebook)
        self.config_tab = ttk.Frame(notebook)
        self.simple_filters_tab = ttk.Frame(notebook)
        
        notebook.add(self.log_tab, text="Log View")
        notebook.add(self.config_tab, text="Configuration")
        notebook.add(self.simple_filters_tab, text="Simple Filters")
        
        self.create_log_tab()
        self.create_config_tab()
        self.create_simple_filters_tab()
        self.create_status_bar()
# ****************************************************************************
    def create_status_bar(self):
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
# ****************************************************************************
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
# ****************************************************************************
    def create_log_tab(self):
        """Create log viewing tab content."""
        # Controls frame at top of log tab
        controls_frame = ttk.Frame(self.log_tab)
        controls_frame.pack(fill=tk.X, padx=5, pady=5)
    
        ttk.Button(controls_frame, text="Start Tail", command=self.start_tail).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Stop Tail", command=self.stop_tail).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Clear Display", command=self.clear_display).pack(side=tk.LEFT, padx=(0, 5))
    
        # Add a pause/resume button
        self.pause_var = tk.BooleanVar(value=False)
        self.pause_button = ttk.Button(controls_frame, text="Pause", command=self.toggle_pause)
        self.pause_button.pack(side=tk.LEFT, padx=(20, 5))
    
        # Status indicator
        self.status_label = ttk.Label(controls_frame, text="Ready", foreground="green")
        self.status_label.pack(side=tk.RIGHT)

        # Encoding indicator
        self.encoding_label = ttk.Label(controls_frame, text="")
        self.encoding_label.pack(side=tk.RIGHT)
    
        # Log display area - takes most of the space
        log_display_frame = ttk.Frame(self.log_tab)
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        self.log_text = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, width=80, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
        # Configure default text tag
        self.log_text.tag_configure("default", foreground="black")
# ****************************************************************************
    def create_simple_filters_tab(self):
        """Create simple filters tab content."""
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
        ttk.Checkbutton(filter_frame, text="Use Regex", 
                       variable=self.filter_regex_var).grid(row=0, column=2, pady=2, sticky="w")
        
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
        
        # Action modifier
        ttk.Label(filter_frame, text="Action Modifier:").grid(row=3, column=0, sticky="w", padx=(0, 5), pady=2)
        self.filter_action_modifier = tk.StringVar()
        self.action_modifier_entry = ttk.Entry(filter_frame, textvariable=self.filter_action_modifier, width=40)
        self.action_modifier_entry.grid(row=3, column=1, columnspan=2, padx=(0, 10), pady=2, sticky="w")
        
        # Sound file browser (initially hidden)
        self.browse_sound_btn = ttk.Button(filter_frame, text="Browse Sound", 
                                          command=self.browse_sound_file)
        self.browse_sound_btn.grid(row=3, column=3, padx=(5, 0), pady=2)
        self.browse_sound_btn.grid_remove()  # Hide initially
        
        # Add filter button
        ttk.Button(filter_frame, text="Add Filter", 
                  command=self.add_enhanced_filter).grid(row=4, column=0, pady=10, sticky="w")
        
        # Filter list display
        listbox_frame = ttk.Frame(filter_frame)
        listbox_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(10, 0))
        
        # Add scrollbar to listbox
        self.filter_listbox = tk.Listbox(listbox_frame, width=80, height=6)
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.filter_listbox.yview)
        self.filter_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.filter_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Remove filter button
        ttk.Button(filter_frame, text="Remove Selected Filter", 
                  command=self.remove_enhanced_filter).grid(row=6, column=0, pady=5, sticky="w")
        
        # Make filter frame grid responsive
        filter_frame.columnconfigure(1, weight=1)
     
# ****************************************************************************
    def create__adv_filters_tab(self):
        """Create adv filters tab content."""
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
        ttk.Button(file_frame, text="Browse", command=lambda: self.browse_config_file("filters_file")).grid(row=1, column=2, pady=2)
        
        # Advanced filters file selection
        ttk.Label(file_frame, text="Advanced Filters File:").grid(row=2, column=0, sticky="w", padx=(0, 5), pady=2)
        self.advanced_filters_file_var = tk.StringVar(value=self.config_manager.get("advanced_filters_file", ""))
        ttk.Entry(file_frame, textvariable=self.advanced_filters_file_var, width=50).grid(row=2, column=1, padx=(0, 5), pady=2)
        ttk.Button(file_frame, text="Browse", command=lambda: self.browse_config_file("advanced_filters_file")).grid(row=2, column=2, pady=2)
        
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
        ttk.Checkbutton(app_frame, text="Auto-load last configuration and filters on startup", 
                       variable=self.auto_load_var).grid(row=1, column=0, columnspan=4, sticky="w", pady=10)
        
        # Recent Files Section
        recent_frame = ttk.LabelFrame(main_frame, text="Recent Files", padding="10")
        recent_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Recent filters
        ttk.Label(recent_frame, text="Recent Filters:").grid(row=0, column=0, sticky="w", pady=2)
        self.recent_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_filters", []), width=50)
        self.recent_filters_combo.grid(row=0, column=1, padx=(10, 5), pady=2)
        self.recent_filters_combo.bind('<<ComboboxSelected>>', self.on_recent_filters_selected)
        
        # Recent advanced filters
        ttk.Label(recent_frame, text="Recent Advanced Filters:").grid(row=1, column=0, sticky="w", pady=2)
        self.recent_adv_filters_combo = ttk.Combobox(recent_frame, values=self.config_manager.get("recent_advanced_filters", []), width=50)
        self.recent_adv_filters_combo.grid(row=1, column=1, padx=(10, 5), pady=2)
        self.recent_adv_filters_combo.bind('<<ComboboxSelected>>', self.on_recent_adv_filters_selected)
        
        # Control Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Save Configuration", command=self.save_configuration).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Load Configuration", command=self.load_configuration_file).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Reset to Defaults", command=self.reset_configuration).pack(side=tk.LEFT)
# ****************************************************************************
# *************************** Button Actions**********************************
# ****************************************************************************

    def toggle_pause(self):
        """Pause or resume log updates."""
        self.pause_var.set(not self.pause_var.get())
        if self.pause_var.get():
            self.status_label.config(text="PAUSED", foreground="red")
            self.messages(2,4,"")
            self.pause_button.config(text="Resume")
        else:
            self.pause_button.config(text="Pause") 
            self.status_label.config(text="Running", foreground="green")
            self.messages(2,0,"")
    
    def browse_file(self):
        """Open a file dialog to select a log file."""
        filename = filedialog.askopenfilename(title="Select Log File")
        if filename:
            self.file_path.set(filename)
            encoding = self.simple_encoding_detect(filename)
            self.messages(2,5,f"{encoding}")

    def change_color(self,wich):
        colors = askcolor(title="Tkinter Color Chooser")
        match wich:
            case "fg":
                self.fg_color.set(colors[1])
            case "bg":
                self.bg_color.set(colors[1])
        print(f"Colors {wich}{colors}{colors[1]}")

    def add_filter(self):
        """Add a new string filter with its colors."""
        filter_str = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        
        if filter_str:
            self.filters[filter_str] = (fg, bg)
            display_text = f"String: '{filter_str}' -> Text: {fg}, Background: {bg}"
            self.filter_listbox.insert(tk.END, display_text)
            self.log_text.tag_configure(filter_str, foreground=fg, background=bg)
            self.filter_string.set("")
            self.messages(2,6,"")
    
    def remove_filter(self):
        """Remove the selected filter."""
        try:
            index = self.filter_listbox.curselection()[0]
            filter_str = list(self.filters.keys())[index]
            del self.filters[filter_str]
            self.filter_listbox.delete(index)
            self.messages(2,7,"")

        except IndexError:
            self.messages(2,8,f"#{index} not available.")
            pass
    
    def clear_display(self):
        """Clear the log display area."""
        self.log_text.delete(1.0, tk.END)

# ****************************************************************************
# *************************** Filter Actions**********************************
# ****************************************************************************

    def on_action_changed(self, event=None):
        """Show/hide relevant controls based on selected action"""
        action = self.filter_action_var.get()
        
        # Hide sound browser by default
        self.browse_sound_btn.grid_remove()
        
        # Clear modifier field
        self.filter_action_modifier.set("")
        
        # Show sound browser only for sound action
        if action == "sound":
            self.browse_sound_btn.grid()
            self.action_modifier_entry.config(state="normal")
            self.filter_action_modifier.set("Click 'Browse Sound' or enter file path")
        elif action == "tts":
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
    
    def add_enhanced_filter(self):
        """Add a new enhanced filter with actions"""
        filter_pattern = self.filter_string.get().strip()
        fg = self.fg_color.get().strip()
        bg = self.bg_color.get().strip()
        action = self.filter_action_var.get()
        action_modifier = self.filter_action_modifier.get().strip()
        
        if not filter_pattern:
            self.messages(2,3,"Filter pattern cannot be empty")
            return
        
        # Validate sound file exists for sound action
        if action == "sound" and action_modifier and not os.path.exists(action_modifier):
            self.messages(2,3,f"Sound file not found: {action_modifier}")
            return
        
        # Create unique key for the filter (pattern + action to allow duplicates with different actions)
        filter_key = f"{filter_pattern}|{action}|{action_modifier}"
        
        # Store the enhanced filter
        self.filters[filter_key] = {
            'pattern': filter_pattern,
            'is_regex': self.filter_regex_var.get(),
            'fg_color': fg,
            'bg_color': bg,
            'action': action,
            'action_modifier': action_modifier
        }
        
        # Update the listbox display
        action_display = action if action != "none" else "color only"
        modifier_display = f" ({action_modifier})" if action_modifier else ""
        display_text = f"{filter_pattern} → {action_display}{modifier_display}"
        self.filter_listbox.insert(tk.END, display_text)
        
        # Configure text widget tag for coloring
        self.log_text.tag_configure(filter_key, foreground=fg, background=bg)
        
        # Save filters to file
        self.save_filters()
        
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
                self.show_status_message("No filter selected", "error")
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
            self.save_filters()
            
            self.show_status_message("Filter removed", "success")
            
        except IndexError:
            self.show_status_message("No filter selected or invalid selection", "error")
        except Exception as e:
            self.show_status_message(f"Error removing filter: {e}", "error")
    
    def save_filters(self):
        """Save current filters to the configured filters file"""
        filters_file = self.filters_file_var.get()
        if not filters_file:
            self.messages(2,3,"No filters file configured")
            return
        
        try:
            filters_data = {
                "version": "1.1",
                "filters": list(self.filters.values())
            }
            
            with open(filters_file, 'w', encoding='utf-8') as f:
                json.dump(filters_data, f, indent=2, ensure_ascii=False)
            
            # Update recent filters list
            self.config_manager.update_recent_list("recent_filters", filters_file)
            self.update_recent_combos()
            
            self.show_status_message("Filters saved successfully", "success")
        except Exception as e:
            self.show_status_message(f"Error saving filters: {e}", "error")
    
    def load_filters(self):
        """Load filters from the configured filters file"""
        filters_file = self.filters_file_var.get()
        if not filters_file or not os.path.exists(filters_file):
            self.show_status_message("Filters file not found", "error")
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
            
            self.show_status_message("Filters loaded successfully", "success")
        except Exception as e:
            self.show_status_message(f"Error loading filters: {e}", "error")
    
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
            self.log_file_var.set(filename)
            self.config_manager.set("last_directory", str(Path(filename).parent))
    
    def browse_config_file(self, config_type):
        """Browse for configuration files"""
        initial_dir = self.config_manager.get("last_directory", str(Path.home()))
        filename = filedialog.askopenfilename(
            title=f"Select {config_type.replace('_', ' ').title()}",
            initialdir=initial_dir,
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            if config_type == "filters_file":
                self.filters_file_var.set(filename)
                self.config_manager.update_recent_list("recent_filters", filename)
                self.update_recent_combos()
            elif config_type == "advanced_filters_file":
                self.advanced_filters_file_var.set(filename)
                self.config_manager.update_recent_list("recent_advanced_filters", filename)
                self.update_recent_combos()
            
            self.config_manager.set("last_directory", str(Path(filename).parent))
    
    def update_recent_combos(self):
        """Update the recent files comboboxes"""
        self.recent_filters_combo['values'] = self.config_manager.get("recent_filters", [])
        self.recent_adv_filters_combo['values'] = self.config_manager.get("recent_advanced_filters", [])
    
    def on_recent_filters_selected(self, event):
        """When a recent filters file is selected"""
        selected_file = self.recent_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.filters_file_var.set(selected_file)
    
    def on_recent_adv_filters_selected(self, event):
        """When a recent advanced filters file is selected"""
        selected_file = self.recent_adv_filters_combo.get()
        if selected_file and os.path.exists(selected_file):
            self.advanced_filters_file_var.set(selected_file)
    
    def save_configuration(self):
        """Save current configuration to file"""
        # Update config manager with current values
        self.config_manager.set("log_file", self.log_file_var.get())
        self.config_manager.set("filters_file", self.filters_file_var.get())
        self.config_manager.set("advanced_filters_file", self.advanced_filters_file_var.get())
        
        try:
            self.config_manager.set("initial_lines", int(self.initial_lines_var.get()))
        except ValueError:
            self.messages(2,3,f"Invalid initial lines value.")
            return
        
        try:
            self.config_manager.set("refresh_interval", int(self.refresh_interval_var.get()))
        except ValueError:
            self.messages(2,3,f"Invalid refresh interval")
            return
        
        self.config_manager.set("auto_load_config", self.auto_load_var.get())
        
        if self.config_manager.save_config():
            self.messages(2,9,f"Configuration saved successfully")
        else:
            self.messages(2,3,f" saving configuration")

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
# ****************************************************************************
# *************************** Tail Actions  **********************************
# ****************************************************************************
    def start_tail(self):
        """Start tailing the log file in a separate thread."""
        filepath = self.config_manager.get("log_file", "")
        if not filepath or not os.path.exists(filepath):
            messages(0,1)
            self.messages(2,3,f"File {filepath} can't be accessed.")
            return
        
        # Get number of initial lines to display
        try:
            num_initial_lines = int(self.initial_lines.get())
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
        print(f"Started tailing: {filepath} (showing last {num_initial_lines} lines)")
        self.update_status(f"Started tailing: {filepath} (showing last {num_initial_lines} lines)")
    
    def stop_tail(self):
        """Stop the tailing process."""
        self.stop_event.set()
        if self.tail_thread and self.tail_thread.is_alive():
            self.tail_thread.join(timeout=2.0)
        self.messages(2,1,"")
        self.status_label.config(text=mssgs[1], foreground="red")
    
    def tail_loop(self):
        """Efficient tailing loop that only reads new content."""
        filepath = self.config_manager.get("log_file", "")
        encoding = self.simple_encoding_detect(filepath)
        
        while not self.stop_event.is_set():
            try:
                current_size = os.path.getsize(filepath)
                
                # If file was truncated, reset position
                if current_size < self.last_position:
                    self.last_position = 0
                
                # Read only new content
                if current_size > self.last_position:
                    with open(filepath, 'r', encoding=encoding, errors='replace') as file:
                        file.seek(self.last_position)
                        new_lines = file.readlines()
                        
                        for line in new_lines:
                            if self.stop_event.is_set():
                                break
                            self.root.after(0, self.update_display, line.rstrip())
                        
                        self.last_position = file.tell()
                
                time.sleep(0.1)  # Small sleep to prevent CPU overload
                
            except Exception as e:
                print(f"Error in tail loop: {e}")
                time.sleep(1)
    
    def update_display(self, line):
        """Update the log display with highlighting and execute actions"""
        if not line:
            return

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
            
        # Optional: Limit total lines to prevent memory bloat
        lines_count = int(self.log_text.index('end-1c').split('.')[0])
        if lines_count > 10000:  # Keep last 10,000 lines
            self.log_text.delete(1.0, "5000.0")  # Remove first 5,000 lines

    def check_actions_before_display(self, line):
        """Check if any filter wants to skip this line"""
        for filter_str, filter_data in self.filters.items():
            if self.line_matches_filter(line, filter_data):
                action = filter_data.get('action', 'none')
                if action == 'skip':
                    return True
        return False
    
    def apply_filters_and_actions(self, line):
        """Apply coloring and execute actions for matching filters"""
        start_index = self.log_text.index("end-2l")
        end_index = self.log_text.index("end-1c")
        
        for filter_str, filter_data in self.filters.items():
            if self.line_matches_filter(line, filter_data):
                # Apply coloring
                self.log_text.tag_add(filter_str, start_index, end_index)
                
                # Execute action (if not skip, since we already handled that)
                action = filter_data.get('action', 'none')
                if action != 'skip' and action != 'none':
                    modifier = filter_data.get('action_modifier', '')
                    self.action_handler.execute_action(action, modifier, line)
    
    def line_matches_filter(self, line, filter_data):
        """Check if a line matches a filter pattern"""
        pattern = filter_data['pattern']
        is_regex = filter_data.get('is_regex', False)
        
        if is_regex:
            try:
                import re
                return bool(re.search(pattern, line))
            except re.error:
                return pattern in line
        else:
            return pattern in line
# ****************************************************************************
# *************************** Main          **********************************
# ****************************************************************************    
if __name__ == "__main__":
    root = tk.Tk()
    app = LogTailApp(root)
    root = tk.mainloop()