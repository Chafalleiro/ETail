# plugins/ocr_modules/ui_components.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Tuple, Callable, Optional

class PatternTTSDialog:
    """Enhanced dialog for pattern + TTS message configuration"""
    
    def __init__(self, parent, title="Patterns & TTS Messages", default_patterns=None):
        self.parent = parent
        self.title = title
        self.default_patterns = default_patterns or [
            ("error", "Error detected"),
            ("warning", "Warning found"), 
            ("critical", "Critical alert")
        ]
        self.pattern_rows = []
        self.result = None
        
    def show(self):
        """Show dialog and return (patterns, tts_messages) or None if cancelled"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.geometry("600x450")
        dialog.transient(self.parent)
        dialog.resizable(True, True)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (dialog.winfo_screenheight() // 2) - (450 // 2)
        dialog.geometry(f"600x450+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding=15)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header with instructions
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(header_frame, text="Configure Patterns & TTS Messages", 
                 font=("Arial", 11, "bold")).pack(anchor=tk.W)
        
        instruction_text = (
            "Add text patterns to monitor and their corresponding TTS messages.\n"
            "Patterns are case-insensitive. Leave TTS blank to use pattern text."
        )
        ttk.Label(header_frame, text=instruction_text, wraplength=500,
                 font=("Arial", 9), foreground="gray").pack(anchor=tk.W, pady=(5, 0))
        
        # Patterns container with scrollbar
        container_frame = ttk.LabelFrame(main_frame, text="Patterns Configuration")
        container_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Create canvas and scrollbar
        canvas = tk.Canvas(container_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Column headers
        headers_frame = ttk.Frame(self.scrollable_frame)
        headers_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        ttk.Label(headers_frame, text="Text Pattern", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 150))
        ttk.Label(headers_frame, text="TTS Message", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 50))
        ttk.Label(headers_frame, text="Actions", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Add default patterns
        for pattern, tts in self.default_patterns:
            self._add_pattern_row(pattern, tts)
        
        # Controls frame (outside scrollable area)
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Button(controls_frame, text="➕ Add Pattern", 
                  command=self._add_pattern_row).pack(side=tk.LEFT)
        
        # Status label
        self.status_var = tk.StringVar(value=f"{len(self.pattern_rows)} patterns configured")
        status_label = ttk.Label(controls_frame, textvariable=self.status_var, 
                               foreground="gray", font=("Arial", 9))
        status_label.pack(side=tk.RIGHT)
        
        # Dialog buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            patterns, tts_messages = self._get_current_patterns()
            if not patterns:
                messagebox.showwarning("No Patterns", "Please add at least one pattern to monitor.")
                return
                
            self.result = (patterns, tts_messages)
            dialog.destroy()
        
        def on_cancel():
            self.result = None
            dialog.destroy()
        
        ttk.Button(button_frame, text="OK", 
                  command=on_ok).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=on_cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to OK and Escape to Cancel
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # Set focus to first pattern field if empty
        if self.pattern_rows and not self.pattern_rows[0]['pattern_var'].get():
            self.pattern_rows[0]['pattern_entry'].focus()
        
        dialog.wait_window()
        return self.result

    def _add_pattern_row(self, pattern_text="", tts_text=""):
        """Add a new pattern row with improved layout"""
        row_index = len(self.pattern_rows)
        
        # Create frame for this row
        row_frame = ttk.Frame(self.scrollable_frame)
        row_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # Pattern entry (40% width)
        pattern_var = tk.StringVar(value=pattern_text)
        pattern_entry = ttk.Entry(row_frame, textvariable=pattern_var, 
                                 font=("Arial", 9))
        pattern_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # TTS entry (50% width)
        tts_var = tk.StringVar(value=tts_text)
        tts_entry = ttk.Entry(row_frame, textvariable=tts_var, 
                             font=("Arial", 9))
        tts_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # Remove button (fixed width)
        remove_btn = ttk.Button(row_frame, text="Remove", width=8,
                              command=lambda: self._remove_pattern_row(row_index))
        remove_btn.pack(side=tk.RIGHT)
        
        # Store row data
        row_data = {
            'frame': row_frame,
            'pattern_var': pattern_var,
            'pattern_entry': pattern_entry,
            'tts_var': tts_var,
            'tts_entry': tts_entry,
            'remove_btn': remove_btn
        }
        
        self.pattern_rows.append(row_data)
        self._update_status()

    def _remove_pattern_row(self, row_index):
        """Remove a pattern row"""
        if 0 <= row_index < len(self.pattern_rows):
            # Destroy the row frame
            self.pattern_rows[row_index]['frame'].destroy()
            
            # Remove from list
            self.pattern_rows.pop(row_index)
            
            # Update remove button commands for remaining rows
            for i, row_data in enumerate(self.pattern_rows):
                row_data['remove_btn'].configure(
                    command=lambda r=i: self._remove_pattern_row(r)
                )
            
            self._update_status()

    def _update_status(self):
        """Update status label"""
        pattern_count = len(self.pattern_rows)
        tts_count = sum(1 for row in self.pattern_rows if row['tts_var'].get().strip())
        
        status = f"{pattern_count} pattern(s)"
        if tts_count > 0:
            status += f", {tts_count} with custom TTS"
        
        self.status_var.set(status)

    def _get_current_patterns(self):
        """Get current patterns and TTS messages"""
        patterns = []
        tts_messages = {}
        
        for row_data in self.pattern_rows:
            pattern_text = row_data['pattern_var'].get().strip()
            tts_text = row_data['tts_var'].get().strip()
            
            if pattern_text:  # Only add non-empty patterns
                patterns.append(pattern_text)
                if tts_text and tts_text != pattern_text:  # Only store custom TTS
                    tts_messages[pattern_text] = tts_text
        
        return patterns, tts_messages

class RegionDialog:
    """Enhanced unified dialog for region creation/editing with embedded patterns"""
    
    def __init__(self, parent, title="Region Configuration", 
                 default_name="", default_coords=None,
                 is_edit_mode=False, existing_region=None):
        self.parent = parent
        self.title = title
        self.default_name = default_name
        self.default_coords = default_coords or (100, 100, 400, 200)
        self.is_edit_mode = is_edit_mode
        self.existing_region = existing_region
        self.result = None
        
        # Initialize patterns from existing region or defaults
        if existing_region:
            self.patterns_data = []
            for pattern in existing_region.get('patterns', []):
                tts_msg = existing_region.get('tts_messages', {}).get(pattern, "")
                self.patterns_data.append((pattern, tts_msg))
        else:
            self.patterns_data = [("error", "Error detected")]
        
        # Initialize patterns_status_var here to ensure it exists
        self.patterns_status_var = tk.StringVar(value="0 patterns configured")


    def show(self):
        """Show dialog and return region config or None if cancelled"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.geometry("700x650")  # Slightly taller to accommodate patterns
        dialog.transient(self.parent)
        dialog.resizable(True, True)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (650 // 2)
        dialog.geometry(f"700x650+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Basic Settings Tab
        basic_tab = self._create_basic_tab(notebook)
        notebook.add(basic_tab, text="Basic Settings")
        
        # Patterns Tab (now with embedded patterns)
        patterns_tab = self._create_patterns_tab(notebook)
        notebook.add(patterns_tab, text="Patterns & TTS")
        
        # Advanced Tab
        advanced_tab = self._create_advanced_tab(notebook)
        notebook.add(advanced_tab, text="Advanced")
        
        # Dialog buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            if not self._validate_and_save():
                return
            dialog.destroy()
        
        def on_cancel():
            self.result = None
            dialog.destroy()
        
        ttk.Button(button_frame, text="OK", 
                  command=on_ok).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=on_cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        dialog.wait_window()
        return self.result

    def _create_basic_tab(self, parent):
        """Create basic settings tab with editable coordinates"""
        tab = ttk.Frame(parent, padding=10)

        # Region name
        ttk.Label(tab, text="Region Name:").pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value=self.default_name)
        name_entry = ttk.Entry(tab, textvariable=self.name_var)
        name_entry.pack(fill=tk.X, pady=(0, 15))
        name_entry.focus()
    
        # Editable Coordinates
        coords_frame = ttk.LabelFrame(tab, text="Region Coordinates", padding=10)
        coords_frame.pack(fill=tk.X, pady=(0, 15))
    
        # Create grid for coordinate inputs
        coords_grid = ttk.Frame(coords_frame)
        coords_grid.pack(fill=tk.X)
    
        # Labels
        ttk.Label(coords_grid, text="X:").grid(row=0, column=0, padx=(0, 5), pady=2, sticky="w")
        ttk.Label(coords_grid, text="Y:").grid(row=0, column=2, padx=(20, 5), pady=2, sticky="w")
        ttk.Label(coords_grid, text="Width:").grid(row=1, column=0, padx=(0, 5), pady=2, sticky="w")
        ttk.Label(coords_grid, text="Height:").grid(row=1, column=2, padx=(20, 5), pady=2, sticky="w")
    
        # Coordinate entry fields
        x, y, w, h = self.default_coords
    
        self.x_var = tk.StringVar(value=str(x))
        self.y_var = tk.StringVar(value=str(y))
        self.width_var = tk.StringVar(value=str(w))
        self.height_var = tk.StringVar(value=str(h))
    
        x_entry = ttk.Entry(coords_grid, textvariable=self.x_var, width=8)
        y_entry = ttk.Entry(coords_grid, textvariable=self.y_var, width=8)
        width_entry = ttk.Entry(coords_grid, textvariable=self.width_var, width=8)
        height_entry = ttk.Entry(coords_grid, textvariable=self.height_var, width=8)
        
        x_entry.grid(row=0, column=1, padx=(0, 10), pady=2, sticky="w")
        y_entry.grid(row=0, column=3, padx=(0, 10), pady=2, sticky="w")
        width_entry.grid(row=1, column=1, padx=(0, 10), pady=2, sticky="w")
        height_entry.grid(row=1, column=3, padx=(0, 10), pady=2, sticky="w")
    
        # Quick preset buttons
        presets_frame = ttk.Frame(coords_frame)
        presets_frame.pack(fill=tk.X, pady=(10, 0))
    
        ttk.Label(presets_frame, text="Quick presets:").pack(side=tk.LEFT, padx=(0, 10))
    
        def set_preset(width, height):
            self.width_var.set(str(width))
            self.height_var.set(str(height))

        ttk.Button(presets_frame, text="Small (200x100)", command=lambda: set_preset(200, 100)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(presets_frame, text="Medium (400x200)", command=lambda: set_preset(400, 200)).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(presets_frame, text="Large (600x300)", command=lambda: set_preset(600, 300)).pack(side=tk.LEFT)
    
        # Cooldown setting
        cooldown_frame = ttk.Frame(tab)
        cooldown_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(cooldown_frame, text="Cooldown:").pack(side=tk.LEFT)
        self.cooldown_var = tk.StringVar(
            value=str(self.existing_region.get('cooldown', 300) if self.existing_region else 300)
        )
        cooldown_entry = ttk.Entry(cooldown_frame, textvariable=self.cooldown_var, 
                                width=8)
        cooldown_entry.pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(cooldown_frame, text="seconds").pack(side=tk.LEFT)
    
        # Enabled checkbox (edit mode only)
        if self.is_edit_mode:
            self.enabled_var = tk.BooleanVar(
                value=self.existing_region.get('enabled', True) if self.existing_region else True
            )
            enabled_cb = ttk.Checkbutton(tab, text="Region Enabled", 
                                    variable=self.enabled_var)
            enabled_cb.pack(anchor=tk.W, pady=(10, 0))
        else:
            self.enabled_var = tk.BooleanVar(value=True)

        return tab

    def _create_patterns_tab(self, parent):
        """Create patterns and TTS configuration tab with embedded pattern management"""
        tab = ttk.Frame(parent, padding=10)
        
        # Instructions
        instruction_text = (
            "Configure text patterns to monitor. Patterns are case-insensitive.\n"
            "Set custom TTS messages or leave blank to use pattern text."
        )
        ttk.Label(tab, text=instruction_text, wraplength=600).pack(anchor=tk.W, pady=(0, 10))
        
        # Patterns container with scrollbar
        container_frame = ttk.LabelFrame(tab, text="Patterns & TTS Messages")
        container_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create canvas and scrollbar for patterns
        canvas = tk.Canvas(container_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.patterns_scrollable_frame = ttk.Frame(canvas)
        
        self.patterns_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.patterns_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Column headers
        headers_frame = ttk.Frame(self.patterns_scrollable_frame)
        headers_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        ttk.Label(headers_frame, text="Text Pattern", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 120))
        ttk.Label(headers_frame, text="TTS Message", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 50))
        ttk.Label(headers_frame, text="Actions", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Store pattern rows
        self.pattern_rows = []
        
        # Add initial patterns
        for pattern, tts in self.patterns_data:
            self._add_pattern_row(pattern, tts)
        
        # If no patterns, add one empty row
        if not self.patterns_data:
            self._add_pattern_row()
        
        # Update the status with current count
        self._update_patterns_status()
        
        # Controls frame
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(controls_frame, text="➕ Add Pattern", 
                  command=self._add_pattern_row).pack(side=tk.LEFT)
        
        # Status label - use the already initialized patterns_status_var
        ttk.Label(controls_frame, textvariable=self.patterns_status_var, 
                 foreground="gray", font=("Arial", 9)).pack(side=tk.RIGHT)
        
        return tab

    def _add_pattern_row(self, pattern_text="", tts_text=""):
        """Add a new pattern row"""
        row_index = len(self.pattern_rows)
        
        # Create frame for this row
        row_frame = ttk.Frame(self.patterns_scrollable_frame)
        row_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # Pattern entry
        pattern_var = tk.StringVar(value=pattern_text)
        pattern_entry = ttk.Entry(row_frame, textvariable=pattern_var, 
                                 font=("Arial", 9))
        pattern_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # TTS entry
        tts_var = tk.StringVar(value=tts_text)
        tts_entry = ttk.Entry(row_frame, textvariable=tts_var, 
                             font=("Arial", 9))
        tts_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove", width=8,
                              command=lambda: self._remove_pattern_row(row_index))
        remove_btn.pack(side=tk.RIGHT)
        
        # Store row data
        row_data = {
            'frame': row_frame,
            'pattern_var': pattern_var,
            'tts_var': tts_var,
            'remove_btn': remove_btn
        }
        
        self.pattern_rows.append(row_data)
        self._update_patterns_status()

    def _remove_pattern_row(self, row_index):
        """Remove a pattern row"""
        if 0 <= row_index < len(self.pattern_rows):
            # Destroy the row frame
            self.pattern_rows[row_index]['frame'].destroy()
            
            # Remove from list
            self.pattern_rows.pop(row_index)
            
            # Update remove button commands for remaining rows
            for i, row_data in enumerate(self.pattern_rows):
                row_data['remove_btn'].configure(
                    command=lambda r=i: self._remove_pattern_row(r)
                )
            
            self._update_patterns_status()
            
            # If no patterns left, add one empty row
            if not self.pattern_rows:
                self._add_pattern_row()

    def _update_patterns_status(self):
        """Update patterns status label"""
        pattern_count = len(self.pattern_rows)
        tts_count = sum(1 for row in self.pattern_rows if row['tts_var'].get().strip())
        
        status = f"{pattern_count} pattern(s)"
        if tts_count > 0:
            status += f", {tts_count} with custom TTS"
        
        # This should now work since patterns_status_var is initialized in __init__
        self.patterns_status_var.set(status)

    def _get_current_patterns(self):
        """Get current patterns and TTS messages from embedded rows"""
        patterns = []
        tts_messages = {}
        
        for row_data in self.pattern_rows:
            pattern_text = row_data['pattern_var'].get().strip()
            tts_text = row_data['tts_var'].get().strip()
            
            if pattern_text:  # Only add non-empty patterns
                patterns.append(pattern_text)
                if tts_text and tts_text != pattern_text:  # Only store custom TTS
                    tts_messages[pattern_text] = tts_text
        
        return patterns, tts_messages

    def _create_advanced_tab(self, parent):
        """Create advanced settings tab"""
        tab = ttk.Frame(parent, padding=10)
        
        # Capture method
        ttk.Label(tab, text="Capture Method:").pack(anchor=tk.W, pady=(0, 5))
        self.method_var = tk.StringVar(
            value=self.existing_region.get('capture_method', 'auto') if self.existing_region else 'auto'
        )
        method_combo = ttk.Combobox(tab, textvariable=self.method_var,
                                  values=['auto', 'bitblt', 'printwindow', 'printwindow_full', 'mss'],
                                  state="readonly")
        method_combo.pack(fill=tk.X, pady=(0, 15))
        
        # Method description
        method_descriptions = {
            'auto': 'Automatically select best method',
            'bitblt': 'Fast traditional method',
            'printwindow': 'Works for most applications', 
            'printwindow_full': 'Best for modern apps/games',
            'mss': 'Alternative screen capture'
        }
        method_desc_var = tk.StringVar(value=method_descriptions.get(self.method_var.get(), ""))
        ttk.Label(tab, textvariable=method_desc_var, wraplength=500).pack(anchor=tk.W, pady=(0, 15))
        
        def update_method_desc(*args):
            method_desc_var.set(method_descriptions.get(self.method_var.get(), ""))
        
        self.method_var.trace('w', update_method_desc)
        
        # Color profile
        ttk.Label(tab, text="Color Profile:").pack(anchor=tk.W, pady=(0, 5))
        self.color_var = tk.StringVar(
            value=self.existing_region.get('color_profile', 'default') if self.existing_region else 'default'
        )
        color_combo = ttk.Combobox(tab, textvariable=self.color_var,
                                 values=['default', 'dark_text', 'custom'],
                                 state="readonly")
        color_combo.pack(fill=tk.X, pady=(0, 10))
        
        return tab

    def _validate_and_save(self):
        """Validate inputs and save results"""
        
        # Validate name
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Region name is required.")
            return False

        # Validate coordinates
        try:
            x = int(self.x_var.get())
            y = int(self.y_var.get())
            width = int(self.width_var.get())
            height = int(self.height_var.get())

            if width <= 0 or height <= 0:
                messagebox.showerror("Error", "Width and height must be positive numbers.")
                return False

            # Optional: Validate that region is within screen bounds
            # You might want to add this check based on your requirements
            # if x < 0 or y < 0:
            #     messagebox.showerror("Error", "Coordinates cannot be negative.")
            #     return False
            
        except ValueError:
            messagebox.showerror("Error", "Coordinates must be valid numbers.")
            return False
    
        # Validate cooldown
        try:
            cooldown = int(self.cooldown_var.get())
            if cooldown < 0:
                messagebox.showerror("Error", "Cooldown must be a positive number.")
                return False
        except ValueError:
            messagebox.showerror("Error", "Cooldown must be a valid number.")
            return False
    
        # Validate patterns
        patterns, tts_messages = self._get_current_patterns()
        if not patterns:
            messagebox.showerror("Error", "At least one pattern is required.")
            return False
    
        # Build result with updated coordinates
        self.result = {
            'name': name,
            'bounds': (x, y, width, height),  # Use the edited coordinates
            'patterns': patterns,
            'tts_messages': tts_messages,
            'cooldown': cooldown,
            'color_profile': self.color_var.get(),
            'enabled': self.enabled_var.get(),
            'capture_method': self.method_var.get()
        }
        print(f"DEBUG: on_ok pressed 276 {self.result}")  # Debug
        return True

class WindowRegionDialog:
    """Unified dialog for window region creation/editing with embedded patterns"""
    
    def __init__(self, parent, title="Window Region Configuration", 
                default_name="", existing_region=None):
        self.parent = parent
        self.title = title
        self.default_name = default_name
        self.existing_region = existing_region
        self.result = None
        self.selected_window = None

        # Initialize patterns from existing region or defaults
        if existing_region:
            self.patterns_data = []
            for pattern in existing_region.get('patterns', []):
                tts_msg = existing_region.get('tts_messages', {}).get(pattern, "")
                self.patterns_data.append((pattern, tts_msg))
        else:
            self.patterns_data = [("error", "Error detected")]
    
        # Initialize ALL Tkinter variables in __init__ to ensure they exist
        self.patterns_status_var = tk.StringVar(value="0 patterns configured")
    
        # Initialize variables that will be used in _set_selected_window
        self.window_title_var = tk.StringVar(value="")
        self.process_name_var = tk.StringVar(value="")
        self.name_var = tk.StringVar(value=default_name)
        self.cooldown_var = tk.StringVar(value="300")
        self.method_var = tk.StringVar(value="auto")
        self.color_var = tk.StringVar(value="default")
        self.enabled_var = tk.BooleanVar(value=True)
    
        # Sub-region data
        self.subregion_bounds = None

    def show(self):
        """Show dialog and return window region config or None if cancelled"""
        dialog = tk.Toplevel(self.parent)
        dialog.title(self.title)
        dialog.geometry("700x650")
        dialog.transient(self.parent)
        dialog.resizable(True, True)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (700 // 2)
        y = (dialog.winfo_screenheight() // 2) - (650 // 2)
        dialog.geometry(f"700x650+{x}+{y}")
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Window Selection Tab
        window_tab = self._create_window_tab(notebook)
        notebook.add(window_tab, text="Window Selection")
        
        # Patterns Tab (with embedded patterns)
        patterns_tab = self._create_patterns_tab(notebook)
        notebook.add(patterns_tab, text="Patterns & TTS")
        
        # Advanced Tab
        advanced_tab = self._create_advanced_tab(notebook)
        notebook.add(advanced_tab, text="Advanced")
        
        # Dialog buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        def on_ok():
            print("DEBUG: on_ok pressed 693")  # Debug        
            if not self._validate_and_save():
                print("DEBUG: on_ok pressed not found validate and save")  # Debug        
                return
            dialog.destroy()
        
        def on_cancel():
            self.result = None
            dialog.destroy()
        
        ttk.Button(button_frame, text="OK", 
                  command=on_ok).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(button_frame, text="Cancel", 
                  command=on_cancel).pack(side=tk.RIGHT)
        
        # Bind Enter key to OK
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        dialog.wait_window()
        return self.result

    def _create_window_tab(self, parent):
        """Create window selection tab with sub-region support"""
        tab = ttk.Frame(parent, padding=10)
    
        # Region name
        ttk.Label(tab, text="Region Name:").pack(anchor=tk.W, pady=(0, 5))
        self.name_var = tk.StringVar(value=self.default_name)
        name_entry = ttk.Entry(tab, textvariable=self.name_var)
        name_entry.pack(fill=tk.X, pady=(0, 15))
        name_entry.focus()
    
        # Window selection section
        window_frame = ttk.LabelFrame(tab, text="Window Selection", padding=10)
        window_frame.pack(fill=tk.X, pady=(0, 15))
    
        # Instructions
        instruction_text = (
            "Select a window to monitor. You can either:\n"
            "• Pick from a list of available windows, or\n"
            "• Click on a window directly"
        )
        ttk.Label(window_frame, text=instruction_text, wraplength=600).pack(anchor=tk.W, pady=(0, 10))

        # Selection buttons
        button_frame = ttk.Frame(window_frame)
        button_frame.pack(fill=tk.X, pady=(0, 10))
    
        ttk.Button(button_frame, text="📋 Select from List", 
                command=self._select_from_list).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🖱️ Click to Pick", 
                command=self._pick_window_interactive).pack(side=tk.LEFT)
    
        # Selected window info
        self.window_info_frame = ttk.LabelFrame(window_frame, text="Selected Window", padding=10)
        self.window_info_frame.pack(fill=tk.X, pady=(0, 10))
    
        # Initially hidden until window is selected
        self.window_info_label = ttk.Label(self.window_info_frame, text="No window selected")
        self.window_info_label.pack(anchor=tk.W)
    
        # SUB-REGION SECTION - THIS WAS MISSING!
        # Sub-region selection (initially hidden until window is selected)
        self.subregion_frame = ttk.LabelFrame(window_frame, text="Window Sub-Region", padding=10)
        # Don't pack it yet - we'll pack it when a window is selected
    
        self.subregion_info_var = tk.StringVar(value="No sub-region selected (will capture entire window)")
        ttk.Label(self.subregion_frame, textvariable=self.subregion_info_var, 
                wraplength=500).pack(anchor=tk.W, pady=(0, 5))
    
        subregion_buttons = ttk.Frame(self.subregion_frame)
        subregion_buttons.pack(fill=tk.X, pady=(0, 5))
    
        ttk.Button(subregion_buttons, text="🎯 Select Sub-Region", 
                command=self._select_subregion).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(subregion_buttons, text="🗑️ Clear Sub-Region", 
                command=self._clear_subregion).pack(side=tk.LEFT)
    
        # Test capture button (initially disabled)
        self.test_capture_btn = ttk.Button(window_frame, text="Test Capture", 
                                        command=self._test_window_capture,
                                        state="disabled")
        self.test_capture_btn.pack(anchor=tk.W, pady=(10, 0))
    
        # Cooldown setting
        cooldown_frame = ttk.Frame(tab)
        cooldown_frame.pack(fill=tk.X, pady=(0, 10))
    
        ttk.Label(cooldown_frame, text="Cooldown:").pack(side=tk.LEFT)
        self.cooldown_var = tk.StringVar(
            value=str(self.existing_region.get('cooldown', 300) if self.existing_region else 300)
        )
        cooldown_entry = ttk.Entry(cooldown_frame, textvariable=self.cooldown_var, 
                                width=8)
        cooldown_entry.pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(cooldown_frame, text="seconds").pack(side=tk.LEFT)
    
        # Enabled checkbox (edit mode only)
        if self.existing_region:
            self.enabled_var = tk.BooleanVar(
                value=self.existing_region.get('enabled', True)
            )
            enabled_cb = ttk.Checkbutton(tab, text="Region Enabled", 
                                    variable=self.enabled_var)
            enabled_cb.pack(anchor=tk.W, pady=(10, 0))
        else:
            self.enabled_var = tk.BooleanVar(value=True)
        
        # Sub-region data
        self.subregion_bounds = None
    
        # Load existing window data if editing
        if self.existing_region and self.existing_region.get('hwnd'):
            self._load_existing_window_data()
    
        return tab
   
    def _select_subregion(self):
        """Select a sub-region within the window"""
        if not self.selected_window:
            messagebox.showwarning("No Window", "Please select a window first.")
            return
    
        try:
            # Hide the dialog temporarily
            self.parent.withdraw()
        
            # Create a region selector instance
            from ocr_modules.region_selector import RegionSelector
            selector = RegionSelector(self.parent)
        
            # Get window bounds to constrain selection
            window_bounds = self.selected_window['bounds']
            x, y, width, height = window_bounds
        
            # Select region within the window
            subregion = selector.select_region_within_window(
                self.selected_window['hwnd'], 
                window_bounds
            )
        
            # Show the dialog again
            self.parent.deiconify()
        
            if subregion:
                # Convert to relative coordinates within the window
                sub_x, sub_y, sub_width, sub_height = subregion
                rel_x = sub_x - x
                rel_y = sub_y - y
            
                self.subregion_bounds = (rel_x, rel_y, sub_width, sub_height)
                self._update_subregion_display()
            
                messagebox.showinfo("Sub-Region Selected", 
                                f"Sub-region selected: {sub_width}x{sub_height} at ({rel_x}, {rel_y})")
            else:
                messagebox.showinfo("Cancelled", "Sub-region selection was cancelled.")
            
        except Exception as e:
            self.parent.deiconify()
            messagebox.showerror("Error", f"Failed to select sub-region: {e}")

    def _clear_subregion(self):
        """Clear the selected sub-region"""
        self.subregion_bounds = None
        self._update_subregion_display()
        messagebox.showinfo("Cleared", "Sub-region cleared. Will capture entire window.")

    def _update_subregion_display(self):
        """Update the sub-region information display"""
        print(f"DEBUG: _update_subregion_display called, subregion_bounds: {self.subregion_bounds}")
    
        if self.subregion_bounds:
            x, y, w, h = self.subregion_bounds
            self.subregion_info_var.set(f"Sub-region selected: {w}x{h} at ({x}, {y})")
            # Make sure the subregion frame is packed and visible
            if not self.subregion_frame.winfo_ismapped():
                print("DEBUG: Packing subregion frame (with subregion)")
                self.subregion_frame.pack(fill=tk.X, pady=(10, 0), before=self.test_capture_btn)
        else:
            self.subregion_info_var.set("No sub-region selected (will capture entire window)")
            # If no subregion, we still want to show the frame but with different text
            if not self.subregion_frame.winfo_ismapped():
                print("DEBUG: Packing subregion frame (no subregion)")
                self.subregion_frame.pack(fill=tk.X, pady=(10, 0), before=self.test_capture_btn)
    
        # Force UI update
        if hasattr(self, 'subregion_frame') and self.subregion_frame.winfo_exists():
            self.subregion_frame.update_idletasks()

    def _create_patterns_tab(self, parent):
        """Create patterns and TTS configuration tab with embedded pattern management"""
        tab = ttk.Frame(parent, padding=10)
        
        # Instructions
        instruction_text = (
            "Configure text patterns to monitor. Patterns are case-insensitive.\n"
            "Set custom TTS messages or leave blank to use pattern text."
        )
        ttk.Label(tab, text=instruction_text, wraplength=600).pack(anchor=tk.W, pady=(0, 10))
        
        # Patterns container with scrollbar
        container_frame = ttk.LabelFrame(tab, text="Patterns & TTS Messages")
        container_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Create canvas and scrollbar for patterns
        canvas = tk.Canvas(container_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container_frame, orient=tk.VERTICAL, command=canvas.yview)
        self.patterns_scrollable_frame = ttk.Frame(canvas)
        
        self.patterns_scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.patterns_scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # Column headers
        headers_frame = ttk.Frame(self.patterns_scrollable_frame)
        headers_frame.pack(fill=tk.X, padx=5, pady=(5, 10))
        
        ttk.Label(headers_frame, text="Text Pattern", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 120))
        ttk.Label(headers_frame, text="TTS Message", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(0, 50))
        ttk.Label(headers_frame, text="Actions", font=("Arial", 9, "bold")).pack(side=tk.RIGHT, padx=(0, 10))
        
        # Store pattern rows
        self.pattern_rows = []
        
        # Add initial patterns
        for pattern, tts in self.patterns_data:
            self._add_pattern_row(pattern, tts)
        
        # If no patterns, add one empty row
        if not self.patterns_data:
            self._add_pattern_row()
        
        # Update the status with current count
        self._update_patterns_status()
        
        # Controls frame
        controls_frame = ttk.Frame(tab)
        controls_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(controls_frame, text="➕ Add Pattern", 
                  command=self._add_pattern_row).pack(side=tk.LEFT)
        
        # Status label - use the already initialized patterns_status_var
        ttk.Label(controls_frame, textvariable=self.patterns_status_var, 
                 foreground="gray", font=("Arial", 9)).pack(side=tk.RIGHT)
        
        return tab

    def _create_advanced_tab(self, parent):
        """Create advanced settings tab"""
        tab = ttk.Frame(parent, padding=10)
        
        # Capture method
        ttk.Label(tab, text="Capture Method:").pack(anchor=tk.W, pady=(0, 5))
        self.method_var = tk.StringVar(
            value=self.existing_region.get('capture_method', 'auto') if self.existing_region else 'auto'
        )
        method_combo = ttk.Combobox(tab, textvariable=self.method_var,
                                  values=['auto', 'bitblt', 'printwindow', 'printwindow_full', 'mss'],
                                  state="readonly")
        method_combo.pack(fill=tk.X, pady=(0, 15))
        
        # Method description
        method_descriptions = {
            'auto': 'Automatically select best method for windows',
            'bitblt': 'Fast traditional method - may not work for all windows',
            'printwindow': 'PrintWindow API - works for most windows', 
            'printwindow_full': 'PrintWindow with full content - best for modern apps',
            'mss': 'MSS library - alternative method'
        }
        method_desc_var = tk.StringVar(value=method_descriptions.get(self.method_var.get(), ""))
        ttk.Label(tab, textvariable=method_desc_var, wraplength=500).pack(anchor=tk.W, pady=(0, 15))
        
        def update_method_desc(*args):
            method_desc_var.set(method_descriptions.get(self.method_var.get(), ""))
        
        self.method_var.trace('w', update_method_desc)
        
        # Color profile
        ttk.Label(tab, text="Color Profile:").pack(anchor=tk.W, pady=(0, 5))
        self.color_var = tk.StringVar(
            value=self.existing_region.get('color_profile', 'default') if self.existing_region else 'default'
        )
        color_combo = ttk.Combobox(tab, textvariable=self.color_var,
                                 values=['default', 'dark_text', 'custom'],
                                 state="readonly")
        color_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Window identification criteria (for advanced users)
        criteria_frame = ttk.LabelFrame(tab, text="Window Identification (Advanced)", padding=10)
        criteria_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(criteria_frame, text="Window Title:").pack(anchor=tk.W, pady=(0, 5))
        self.window_title_var = tk.StringVar(value=self.existing_region.get('window_title', '') if self.existing_region else '')
        window_title_entry = ttk.Entry(criteria_frame, textvariable=self.window_title_var)
        window_title_entry.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(criteria_frame, text="Process Name:").pack(anchor=tk.W, pady=(0, 5))
        self.process_name_var = tk.StringVar(value=self.existing_region.get('process_name', '') if self.existing_region else '')
        process_name_entry = ttk.Entry(criteria_frame, textvariable=self.process_name_var)
        process_name_entry.pack(fill=tk.X, pady=(0, 10))
        
        info_text = "These fields help identify the window if it moves or restarts.\nThey are automatically filled when you select a window."
        ttk.Label(criteria_frame, text=info_text, wraplength=500, 
                 font=("Arial", 8), foreground="gray").pack(anchor=tk.W)
        
        return tab

    def _select_from_list(self):
        """Open window selection list dialog"""
        try:
            # Import here to avoid circular imports
            from ocr_plugin import OCRMonitorPlugin

            # Create a minimal plugin instance just for window listing
            class TempPlugin:
                def __init__(self):
                    self.regions = []

                def list_available_windows(self):
                    import psutil
                    import win32gui
                    import win32process

                    windows = []
                    def enum_windows_proc(hwnd, lParam):
                        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                            _, pid = win32process.GetWindowThreadProcessId(hwnd)
                            try:
                                process = psutil.Process(pid)
                                process_name = process.name()
                            except:
                                process_name = "Unknown"

                            window_title = win32gui.GetWindowText(hwnd)
                            class_name = win32gui.GetClassName(hwnd)

                            try:
                                left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                                width = right - left
                                height = bottom - top

                                if width > 100 and height > 100:
                                    windows.append({
                                        'hwnd': hwnd,
                                        'title': window_title,
                                        'class_name': class_name,
                                        'pid': pid,
                                        'process_name': process_name,
                                        'bounds': (left, top, width, height),
                                        'size': f"{width}x{height}"
                                    })
                            except:
                                pass
                        return True

                    win32gui.EnumWindows(enum_windows_proc, None)
                    return sorted(windows, key=lambda x: x['title'])
        
            temp_plugin = TempPlugin()
            windows = temp_plugin.list_available_windows()
        
            if not windows:
                messagebox.showinfo("No Windows", "No suitable windows found.")
                return
        
            # Create selection dialog
            list_dialog = tk.Toplevel(self.parent)
            list_dialog.title("Select Window")
            list_dialog.geometry("700x500")
            list_dialog.transient(self.parent)
            list_dialog.grab_set()  # Make it modal

            main_frame = ttk.Frame(list_dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Instructions
            ttk.Label(main_frame, text="Select a window from the list below:").pack(anchor=tk.W, pady=(0, 10))
        
            # Treeview for windows
            tree_frame = ttk.Frame(main_frame)
            tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
            columns = ('title', 'process', 'size')
            tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=15)
        
            tree.heading('title', text='Window Title')
            tree.heading('process', text='Process')
            tree.heading('size', text='Size')
        
            tree.column('title', width=400)
            tree.column('process', width=150)
            tree.column('size', width=80)

            scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scrollbar.set)

            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
            # Store window data in a dictionary for easy lookup
            self.window_data_map = {}

            # Populate treeview
            for win in windows:
                item_id = tree.insert('', tk.END, values=(
                    win['title'][:80] + "..." if len(win['title']) > 80 else win['title'],
                    win['process_name'],
                    win['size']
                ), tags=(win['hwnd'],))
                # Store the window data using the item ID as key
                self.window_data_map[item_id] = win

            def on_select():
                selection = tree.selection()
                if selection:
                    try:
                        item_id = selection[0]  # Get the selected item ID
                        window_data = self.window_data_map.get(item_id)

                        if window_data:
                            self._set_selected_window(window_data)
                            list_dialog.destroy()
                        else:
                            messagebox.showerror("Error", "Could not find selected window data.")
                    except Exception as e:
                        messagebox.showerror("Error", f"Error selecting window: {e}")
                        import traceback
                        traceback.print_exc()  # Print full traceback for debugging
                else:
                    messagebox.showwarning("No Selection", "Please select a window from the list.")        

            def on_cancel():
                list_dialog.destroy()
        
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X)
        
            ttk.Button(button_frame, text="Select", 
                    command=on_select).pack(side=tk.RIGHT, padx=(10, 0))
            ttk.Button(button_frame, text="Cancel", 
                    command=on_cancel).pack(side=tk.RIGHT)

            # Double-click to select
            tree.bind('<Double-1>', lambda e: on_select())

            # Set focus to tree and select first item
            tree.focus_set()
            if tree.get_children():
                tree.selection_set(tree.get_children()[0])
                tree.focus(tree.get_children()[0])
        
            # Wait for the list dialog to close
            list_dialog.wait_window()
       
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list windows: {e}")

    def _pick_window_interactive(self):
        """Pick window by clicking on it"""
        try:
            from ocr_modules.region_selector import RegionSelector
        
            # Create a simple region selector instance
            selector = RegionSelector(self.parent)
            window_info = selector.select_window()

            if window_info and 'hwnd' in window_info:
                # Convert to the format expected by _set_selected_window
                import win32gui
                import win32process
                import psutil

                hwnd = window_info['hwnd']
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    try:
                        process = psutil.Process(pid)
                        process_name = process.name()
                    except:
                        process_name = "Unknown"

                    window_title = win32gui.GetWindowText(hwnd)
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    width = right - left
                    height = bottom - top

                    window_data = {
                        'hwnd': hwnd,
                        'title': window_title,
                        'process_name': process_name,
                        'bounds': (left, top, width, height)
                    }
                    self._set_selected_window(window_data)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to get window information: {e}")
            else:
                messagebox.showinfo("Cancelled", "Window selection was cancelled.")

        except Exception as e:
            messagebox.showerror("Error", f"Window selection failed: {e}")

    def _set_selected_window(self, window_data):
        """Set the selected window and update UI"""
        print(f"DEBUG: _set_selected_window called with: {window_data['title']}")
        self.selected_window = window_data

        # Update window info display
        for widget in self.window_info_frame.winfo_children():
            widget.destroy()
    
        info_text = f"""Window Title: {window_data['title']}
                    Process: {window_data['process_name']}
                    Size: {window_data['bounds'][2]} x {window_data['bounds'][3]}
                    Handle: {hex(window_data['hwnd'])}"""

        ttk.Label(self.window_info_frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)

        # Make sure the window info frame is visible
        self.window_info_frame.pack(fill=tk.X, pady=(0, 10))

        # Enable test button
        self.test_capture_btn.config(state="normal")

        # Auto-fill identification criteria
        self.window_title_var.set(window_data['title'])
        self.process_name_var.set(window_data['process_name'])

        # Auto-generate name if not set
        current_name = self.name_var.get().strip()
        if not current_name or current_name.startswith("Window_"):
            safe_title = "".join(c for c in window_data['title'][:30] if c.isalnum() or c in (' ', '-', '_'))
            if safe_title.strip():
                self.name_var.set(safe_title.strip())
            else:
                self.name_var.set(f"Window_{window_data['process_name']}")

        print(f"DEBUG: Window set successfully: {window_data['title']}")

        # Load existing subregion if editing
        if self.existing_region and self.existing_region.get('subregion_bounds'):
            self.subregion_bounds = self.existing_region['subregion_bounds']
    
        # Update subregion display - THIS ENSURES THE SUBREGION UI IS VISIBLE
        self._update_subregion_display()

        # Force UI update
        self.window_info_frame.update_idletasks()
    
    def _load_existing_window_data(self):
        """Load existing window data when editing"""
        if self.existing_region and self.existing_region.get('hwnd'):
            window_data = {
                'hwnd': self.existing_region.get('hwnd'),
                'title': self.existing_region.get('window_title', 'Unknown'),
                'process_name': self.existing_region.get('process_name', 'Unknown'),
                'bounds': self.existing_region.get('bounds', (0, 0, 100, 100))
            }
            self._set_selected_window(window_data)
            # Load subregion bounds if they exist
            if 'subregion_bounds' in self.existing_region:
                self.subregion_bounds = self.existing_region['subregion_bounds']
                print(f"DEBUG: Loaded existing subregion: {self.subregion_bounds}")  # Debug
            else:
                self.subregion_bounds = None
                print("DEBUG: No existing subregion found")  # Debug
        
            # CRITICAL: Update the subregion display to show existing subregion
            self._update_subregion_display()
        
            # Also make sure the subregion controls are visible
            if not self.subregion_frame.winfo_ismapped():
                self.subregion_frame.pack(fill=tk.X, pady=(10, 0), before=self.test_capture_btn)

    def _test_window_capture(self):
        """Test capture on the selected window"""
        if not self.selected_window:
            messagebox.showwarning("No Window", "Please select a window first.")
            return
        
        try:
            from ocr_plugin import OCRMonitorPlugin
            temp_plugin = OCRMonitorPlugin(None)
            temp_plugin.window_capture.set_method(self.method_var.get())
            
            image = temp_plugin.window_capture.capture_region(hwnd=self.selected_window['hwnd'])
            
            if image:
                # Show preview
                preview = tk.Toplevel(self.parent)
                preview.title("Window Capture Test")
                
                from PIL import ImageTk
                display_width = min(image.width, 500)
                scale_factor = display_width / image.width
                display_height = int(image.height * scale_factor)
                
                display_image = image.resize((display_width, display_height))
                photo = ImageTk.PhotoImage(display_image)
                
                label = ttk.Label(preview, image=photo)
                label.image = photo
                label.pack(padx=10, pady=10)
                
                status = "✓ Capture successful!"
                if image.getbbox() is None:
                    status = "⚠ Warning: Image appears blank. Try a different capture method."
                
                ttk.Label(preview, text=status).pack(pady=5)
                ttk.Label(preview, text=f"Size: {image.width} x {image.height}").pack(pady=5)
            else:
                messagebox.showerror("Test Failed", "Could not capture window. Try a different capture method.")
                
        except Exception as e:
            messagebox.showerror("Test Failed", f"Error: {str(e)}")

    # Pattern management methods (same as in RegionDialog)
    def _add_pattern_row(self, pattern_text="", tts_text=""):
        """Add a new pattern row"""
        row_index = len(self.pattern_rows)
        
        # Create frame for this row
        row_frame = ttk.Frame(self.patterns_scrollable_frame)
        row_frame.pack(fill=tk.X, padx=5, pady=3)
        
        # Pattern entry
        pattern_var = tk.StringVar(value=pattern_text)
        pattern_entry = ttk.Entry(row_frame, textvariable=pattern_var, 
                                 font=("Arial", 9))
        pattern_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # TTS entry
        tts_var = tk.StringVar(value=tts_text)
        tts_entry = ttk.Entry(row_frame, textvariable=tts_var, 
                             font=("Arial", 9))
        tts_entry.pack(side=tk.LEFT, padx=(0, 10), fill=tk.X, expand=True)
        
        # Remove button
        remove_btn = ttk.Button(row_frame, text="Remove", width=8,
                              command=lambda: self._remove_pattern_row(row_index))
        remove_btn.pack(side=tk.RIGHT)
        
        # Store row data
        row_data = {
            'frame': row_frame,
            'pattern_var': pattern_var,
            'tts_var': tts_var,
            'remove_btn': remove_btn
        }
        
        self.pattern_rows.append(row_data)
        self._update_patterns_status()

    def _remove_pattern_row(self, row_index):
        """Remove a pattern row"""
        if 0 <= row_index < len(self.pattern_rows):
            # Destroy the row frame
            self.pattern_rows[row_index]['frame'].destroy()
            
            # Remove from list
            self.pattern_rows.pop(row_index)
            
            # Update remove button commands for remaining rows
            for i, row_data in enumerate(self.pattern_rows):
                row_data['remove_btn'].configure(
                    command=lambda r=i: self._remove_pattern_row(r)
                )
            
            self._update_patterns_status()
            
            # If no patterns left, add one empty row
            if not self.pattern_rows:
                self._add_pattern_row()

    def _update_patterns_status(self):
        """Update patterns status label"""
        pattern_count = len(self.pattern_rows)
        tts_count = sum(1 for row in self.pattern_rows if row['tts_var'].get().strip())
        
        status = f"{pattern_count} pattern(s)"
        if tts_count > 0:
            status += f", {tts_count} with custom TTS"
        
        self.patterns_status_var.set(status)

    def _get_current_patterns(self):
        """Get current patterns and TTS messages from embedded rows"""
        patterns = []
        tts_messages = {}
        
        for row_data in self.pattern_rows:
            pattern_text = row_data['pattern_var'].get().strip()
            tts_text = row_data['tts_var'].get().strip()
            
            if pattern_text:  # Only add non-empty patterns
                patterns.append(pattern_text)
                if tts_text and tts_text != pattern_text:  # Only store custom TTS
                    tts_messages[pattern_text] = tts_text
        
        return patterns, tts_messages

    def _validate_and_save(self):
        """Validate inputs and save results"""
        # Validate name
        name = self.name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Region name is required.")
            return False
    
        # Validate window selection
        if not self.selected_window and not self.existing_region:
            messagebox.showerror("Error", "Please select a window to monitor.")
            return False
    
        # Validate cooldown
        try:
            cooldown = int(self.cooldown_var.get())
            if cooldown < 0:
                messagebox.showerror("Error", "Cooldown must be a positive number.")
                return False
        except ValueError:
            messagebox.showerror("Error", "Cooldown must be a valid number.")
            return False
    
        # Validate patterns
        patterns, tts_messages = self._get_current_patterns()
        if not patterns:
            messagebox.showerror("Error", "At least one pattern is required.")
            return False
    
        # Build result
        self.result = {
            'name': name,
            'type': 'window',
            'hwnd': self.selected_window['hwnd'] if self.selected_window else self.existing_region.get('hwnd'),
            'window_title': self.window_title_var.get() or (self.selected_window['title'] if self.selected_window else ''),
            'process_name': self.process_name_var.get() or (self.selected_window['process_name'] if self.selected_window else ''),
            'bounds': self.selected_window['bounds'] if self.selected_window else self.existing_region.get('bounds', (0, 0, 100, 100)),
            'patterns': patterns,
            'tts_messages': tts_messages,
            'cooldown': cooldown,
            'color_profile': self.color_var.get(),
            'enabled': self.enabled_var.get(),
            'capture_method': self.method_var.get(),
            'subregion_bounds': self.subregion_bounds  # Add the subregion bounds
        }
    
        return True

class RegionTestDialog:
    """Reusable dialog for testing regions with capture methods"""
    
    def __init__(self, parent, plugin, region):
        self.parent = parent
        self.plugin = plugin
        self.region = region
        self.live_preview_active = False
