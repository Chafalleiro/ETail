import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os
import chardet
from threading import Thread, Event
import time
import re

class LogTailApp:
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
    
    def __init__(self, root):
        self.root = root
        self.root.title("Etail 0.3")
        root.iconbitmap('Etail.ico')
        
        # Control variables
        self.stop_event = Event()
        self.tail_thread = None
        self.last_position = 0  # Track file position
        self.filters = {}
        
        self.setup_encoding_detector()
        self.create_widgets()
        self.messages(2,2,"")
    
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
        self.str_out = f"{self.mssgs[par_2]} {par_3}"
        match par_1:
            case 0:
                print(self.str_out)
            case 1:
                self.update_status(self.str_out)
            case 2:
                print(self.str_out)
                self.update_status(self.str_out)


        
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
            
            return encoding if encoding and confidence > 0.5 else 'utf-8'
                
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
            print(f"Error reading last lines: {e}")
            self.messages(2,3,f"Error reading last lines: {e}")
            return []
    
    def create_widgets(self):
        """Create and arrange the GUI components with tabs."""
        # Create notebook (tab container)
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
        # Create tabs
        self.log_tab = ttk.Frame(notebook)
        self.config_tab = ttk.Frame(notebook)
        
        notebook.add(self.log_tab, text="Log View")
        notebook.add(self.config_tab, text="Configuration")
        
        self.create_log_tab()
        self.create_config_tab()
        self.create_status_bar()
        
    def create_status_bar(self):
        # Create status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()

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
    
        # Log display area - takes most of the space
        log_display_frame = ttk.Frame(self.log_tab)
        log_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        self.log_text = scrolledtext.ScrolledText(log_display_frame, wrap=tk.WORD, width=80, height=25)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
        # Configure default text tag
        self.log_text.tag_configure("default", foreground="black")
    
    def create__simple_filters_tab(self):
        """Create simple filters tab content."""
        
    def create__adv_filters_tab(self):
        """Create adv filters tab content."""
        
    def create_config_tab(self):
        """Create configuration tab content."""
        # File selection
        file_frame = ttk.LabelFrame(self.config_tab, text="Log File Settings", padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
    
        ttk.Label(file_frame, text="Log File:").grid(row=0, column=0, sticky="w", padx=(0, 5))
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=50).grid(row=0, column=1, padx=(0, 5))
        ttk.Button(file_frame, text="Browse", command=self.browse_file).grid(row=0, column=2)
    
        # Initial lines configuration
        ttk.Label(file_frame, text="Initial Lines:").grid(row=1, column=0, sticky="w", padx=(0, 5))
        self.initial_lines = tk.StringVar(value="50")
        ttk.Entry(file_frame, textvariable=self.initial_lines, width=10).grid(row=1, column=1, sticky="w", padx=(0, 10))
    
        # Filter configuration
        filter_frame = ttk.LabelFrame(self.config_tab, text="Highlighting Filters", padding="10")
        filter_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
        ttk.Label(filter_frame, text="String:").grid(row=0, column=0, padx=(0, 5))
        self.filter_string = tk.StringVar()
        ttk.Entry(filter_frame, textvariable=self.filter_string).grid(row=0, column=1, padx=(0, 10))
    
        ttk.Label(filter_frame, text="Text Color:").grid(row=0, column=2, padx=(0, 5))
        self.fg_color = tk.StringVar(value="black")
        ttk.Entry(filter_frame, textvariable=self.fg_color, width=8).grid(row=0, column=3, padx=(0, 10))
    
        ttk.Label(filter_frame, text="Background:").grid(row=0, column=4, padx=(0, 5))
        self.bg_color = tk.StringVar(value="yellow")
        ttk.Entry(filter_frame, textvariable=self.bg_color, width=8).grid(row=0, column=5, padx=(0, 10))
    
        ttk.Button(filter_frame, text="Add Filter", command=self.add_filter).grid(row=0, column=6, padx=(10, 0))
    
        # Filter list display
        self.filter_listbox = tk.Listbox(filter_frame, width=80, height=8)
        self.filter_listbox.grid(row=1, column=0, columnspan=7, sticky="nsew", pady=(10, 0))
        ttk.Button(filter_frame, text="Remove Selected", command=self.remove_filter).grid(row=2, column=6, sticky="e", pady=(5, 0))
    
        # Make filter frame expandable
        filter_frame.columnconfigure(1, weight=1)
        filter_frame.rowconfigure(1, weight=1)

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
    
    def start_tail(self):
        """Start tailing the log file in a separate thread."""
        filepath = self.file_path.get()
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
        self.status_label.config(text=self.mssgs[1], foreground="red")
    
    def tail_loop(self):
        """Efficient tailing loop that only reads new content."""
        filepath = self.file_path.get()
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
        """Update the log display with highlighting."""
        if not line:
            return
        
        # Insert the line
        self.log_text.insert(tk.END, line + "\n")
        
        # Apply highlighting
        for filter_str, (fg, bg) in self.filters.items():
            result = re.search(filter_str, line)
            if result:
                print(f"Checking Regex: {filter_str}")
                start_index = self.log_text.index("end-2l")
                end_index = self.log_text.index("end-1c")
                self.log_text.tag_add(filter_str, start_index, end_index)
                break
        # Auto-scroll and limit lines to prevent memory issues
        self.log_text.see(tk.END)
        
        # Optional: Limit total lines to prevent memory bloat
        lines_count = int(self.log_text.index('end-1c').split('.')[0])
        if lines_count > 10000:  # Keep last 10,000 lines
            self.log_text.delete(1.0, "5000.0")  # Remove first 5,000 lines

if __name__ == "__main__":
    root = tk.Tk()
    app = LogTailApp(root)

    root = tk.mainloop()
