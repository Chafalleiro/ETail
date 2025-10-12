# plugins/ocr_plugin.py
from etail_plugin import ETailPlugin
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pyautogui
import pytesseract
from PIL import Image, ImageTk
import time
import threading
import json
from pathlib import Path
import mss
import mss.tools

class RegionSelector:
    """Visual region selector with proper multi-monitor support"""
    def __init__(self, app):
        self.app = app
        self.selector_window = None
        self.canvas = None
        self.start_x = None
        self.start_y = None
        self.rect = None
        self.screenshot = None
        self.photo = None
        self.selected_region = None
        self.monitors = []
        
    def get_all_monitors(self):
        """Get information about all connected monitors"""
        with mss.mss() as sct:
            # Get primary monitor (monitor 1)
            primary = sct.monitors[1]
            self.monitors = [primary]
            
            # Get all monitors (including secondary)
            for i, monitor in enumerate(sct.monitors[1:], 1):
                monitor_info = {
                    'index': i,
                    'left': monitor['left'],
                    'top': monitor['top'], 
                    'width': monitor['width'],
                    'height': monitor['height'],
                    'right': monitor['left'] + monitor['width'],
                    'bottom': monitor['top'] + monitor['height']
                }
                self.monitors.append(monitor_info)
            
            print(f"DEBUG: Found {len(self.monitors)} monitors:")
            for i, monitor in enumerate(self.monitors):
                print(f"  Monitor {i}: {monitor['width']}x{monitor['height']} at ({monitor['left']}, {monitor['top']})")
                
            return self.monitors
        
    def capture_all_monitors(self):
        """Capture screenshot of all monitors combined"""
        with mss.mss() as sct:
            # Calculate bounding box that contains all monitors
            all_left = min(monitor['left'] for monitor in self.monitors)
            all_top = min(monitor['top'] for monitor in self.monitors)
            all_right = max(monitor['right'] for monitor in self.monitors)
            all_bottom = max(monitor['bottom'] for monitor in self.monitors)
            
            total_width = all_right - all_left
            total_height = all_bottom - all_top
            
            # Capture the entire virtual screen
            bbox = {
                'left': all_left,
                'top': all_top, 
                'width': total_width,
                'height': total_height
            }
            
            print(f"DEBUG: Capturing virtual screen: {bbox}")
            screenshot = sct.grab(bbox)
            
            # Convert to PIL Image
            return Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
        
    def select_region(self):
        """Open region selector covering all monitors"""
        try:
            # Get monitor information first
            self.get_all_monitors()
            
            # Capture screenshot of all monitors
            self.screenshot = self.capture_all_monitors()
            
            # Calculate virtual screen bounds
            all_left = min(monitor['left'] for monitor in self.monitors)
            all_top = min(monitor['top'] for monitor in self.monitors)
            all_right = max(monitor['right'] for monitor in self.monitors)
            all_bottom = max(monitor['bottom'] for monitor in self.monitors)
            
            total_width = all_right - all_left
            total_height = all_bottom - all_top
            
            # Create fullscreen selection window
            self.selector_window = tk.Toplevel(self.app.root)
            self.selector_window.attributes('-fullscreen', True)
            self.selector_window.attributes('-alpha', 0.7)
            self.selector_window.attributes('-topmost', True)
            self.selector_window.configure(cursor='crosshair')
            self.selector_window.configure(background='black')
            
            # Create canvas covering virtual screen
            self.canvas = tk.Canvas(self.selector_window, 
                                   width=total_width, 
                                   height=total_height,
                                   highlightthickness=0)
            self.canvas.pack(fill=tk.BOTH, expand=True)
            
            # Display screenshot
            self.photo = ImageTk.PhotoImage(self.screenshot)
            self.canvas.create_image(-all_left, -all_top, anchor=tk.NW, image=self.photo)
            
            # Draw monitor boundaries
            self._draw_monitor_boundaries(all_left, all_top)
            
            # Bind mouse events
            self.canvas.bind('<Button-1>', self.on_mouse_down)
            self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
            self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
            self.selector_window.bind('<Escape>', self.cancel_selection)
            
            # Instructions
            instructions = self.canvas.create_text(
                total_width // 2, 30,
                text="Drag to select region on any monitor. Press ESC to cancel.",
                fill="white",
                font=("Arial", 14, "bold"),
                justify=tk.CENTER
            )
            self.canvas.tag_raise(instructions)
            
            # Wait for selection
            self.selector_window.wait_window()
            return self.selected_region
            
        except Exception as e:
            print(f"Error in region selection: {e}")
            # Fallback to single monitor
            return self._fallback_select_region()
            
    def _draw_monitor_boundaries(self, offset_x, offset_y):
        """Draw boundaries around each monitor"""
        for i, monitor in enumerate(self.monitors):
            x1 = monitor['left'] - offset_x
            y1 = monitor['top'] - offset_y
            x2 = x1 + monitor['width']
            y2 = y1 + monitor['height']
            
            # Draw monitor border
            self.canvas.create_rectangle(
                x1, y1, x2, y2,
                outline='yellow', width=3, dash=(5, 5)
            )
            
            # Add monitor label
            monitor_text = f"Monitor {i+1}"
            if i == 0:
                monitor_text += " (Primary)"
                
            self.canvas.create_text(
                x1 + 10, y1 + 20,
                text=monitor_text,
                fill="yellow",
                font=("Arial", 10, "bold"),
                anchor=tk.W
            )
            
    def _fallback_select_region(self):
        """Fallback method using pyautogui (single monitor only)"""
        print("DEBUG: Using fallback single-monitor selection")
        self.screenshot = pyautogui.screenshot()
        
        # Create fullscreen selection window
        self.selector_window = tk.Toplevel(self.app.root)
        self.selector_window.attributes('-fullscreen', True)
        self.selector_window.attributes('-alpha', 0.7)
        self.selector_window.attributes('-topmost', True)
        self.selector_window.configure(cursor='crosshair')
        
        screen_width = self.screenshot.width
        screen_height = self.screenshot.height
        
        self.canvas = tk.Canvas(self.selector_window, 
                               width=screen_width, 
                               height=screen_height,
                               highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        
        # Display screenshot
        self.photo = ImageTk.PhotoImage(self.screenshot)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        
        # Bind mouse events
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)
        self.selector_window.bind('<Escape>', self.cancel_selection)
        
        # Instructions
        self.canvas.create_text(
            screen_width // 2, 30,
            text="Drag to select region (Single monitor mode). Press ESC to cancel.",
            fill="white",
            font=("Arial", 14, "bold"),
            justify=tk.CENTER
        )
        
        # Wait for selection
        self.selector_window.wait_window()
        return self.selected_region
        
    def on_mouse_down(self, event):
        """Start region selection"""
        self.start_x = event.x
        self.start_y = event.y
        self.rect = self.canvas.create_rectangle(
            self.start_x, self.start_y, self.start_x, self.start_y,
            outline='red', width=2, fill='', stipple='gray50'
        )
        
    def on_mouse_drag(self, event):
        """Update selection rectangle"""
        if self.rect:
            self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)
            
    def on_mouse_up(self, event):
        """Finish region selection"""
        if self.rect:
            # Get final coordinates
            x1, y1, x2, y2 = self.canvas.coords(self.rect)
            
            # Ensure positive width and height
            x = min(x1, x2)
            y = min(y1, y2)
            width = abs(x2 - x1)
            height = abs(y2 - y1)
            
            # Only accept regions larger than 10x10 pixels
            if width > 10 and height > 10:
                # Convert canvas coordinates to screen coordinates
                screen_x, screen_y = self._canvas_to_screen(x, y)
                
                self.selected_region = (int(screen_x), int(screen_y), int(width), int(height))
                
                # Draw final confirmation
                self.canvas.create_rectangle(
                    x, y, x + width, y + height,
                    outline='lime', width=3, fill='', stipple='gray25'
                )
                
                # Add coordinates text
                coords_text = f"Region: {int(screen_x)}, {int(screen_y)}, {int(width)}, {int(height)}"
                self.canvas.create_text(
                    x + width // 2, y + height + 20,
                    text=coords_text,
                    fill="lime",
                    font=("Arial", 10, "bold")
                )
                
                # Determine which monitor this region is on
                monitor_info = self._get_region_monitor(screen_x, screen_y, width, height)
                self.canvas.create_text(
                    x + width // 2, y + height + 40,
                    text=f"On: {monitor_info}",
                    fill="cyan",
                    font=("Arial", 9, "bold")
                )
                
                # Wait a moment so user can see the selection
                self.selector_window.after(1000, self.selector_window.destroy)
            else:
                messagebox.showwarning("Region too small", "Please select a larger region")
                self.cancel_selection()
                
    def _canvas_to_screen(self, canvas_x, canvas_y):
        """Convert canvas coordinates to actual screen coordinates"""
        # For multi-monitor setup with mss, we need to account for the virtual screen offset
        if hasattr(self, 'monitors') and self.monitors:
            all_left = min(monitor['left'] for monitor in self.monitors)
            all_top = min(monitor['top'] for monitor in self.monitors)
            screen_x = canvas_x + all_left
            screen_y = canvas_y + all_top
        else:
            # Fallback for single monitor
            screen_x = canvas_x
            screen_y = canvas_y
            
        return screen_x, screen_y
        
    def _get_region_monitor(self, x, y, width, height):
        """Determine which monitor contains the selected region"""
        region_center_x = x + width // 2
        region_center_y = y + height // 2
        
        for i, monitor in enumerate(self.monitors):
            if (monitor['left'] <= region_center_x <= monitor['right'] and
                monitor['top'] <= region_center_y <= monitor['bottom']):
                monitor_type = "Primary" if i == 0 else f"Secondary {i}"
                return f"{monitor_type} ({monitor['width']}x{monitor['height']})"
                
        return "Unknown Monitor"
                
    def cancel_selection(self, event=None):
        """Cancel region selection"""
        self.selected_region = None
        if self.selector_window:
            self.selector_window.destroy()

class OCRMonitorPlugin(ETailPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.name = "OCR Screen Monitor"
        self.version = "1.3"
        self.description = "Monitor specific screen areas for text using OCR with multi-monitor support"
        self.monitoring = False
        self.monitor_thread = None
        self.regions = []
        self.config_file = Path("~/.etail/ocr_plugin_config.json").expanduser()
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        self.region_selector = RegionSelector(app)
        
        # Default configuration
        self.config = {
            "tesseract_path": "",
            "check_interval": 2.0,
            "confidence_threshold": 70,
            "language": "eng",
            "ocr_engine_mode": 3,
            "page_segmentation_mode": 6,
            "regions": [],
            "use_mss": True  # Use mss for multi-monitor support
        }
        
        # Load configuration
        self.load_configuration()
        
    def setup(self):
        """Setup the OCR monitor with configuration"""
        # Verify Tesseract path
        if not self.verify_tesseract():
            self.app.messages(2, 3, "Tesseract not found. Please configure path in plugin settings.")
            return False
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.app.messages(2, 9, "OCR Screen Monitor enabled")
        return True
        
    def teardown(self):
        """Stop the OCR monitor and save configuration"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        self.save_configuration()
        self.app.messages(2, 9, "OCR Screen Monitor disabled")
        
    def verify_tesseract(self):
        """Verify Tesseract is accessible"""
        tesseract_path = self.config.get("tesseract_path", "")
        if tesseract_path and Path(tesseract_path).exists():
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            return True
        
        # Try to find Tesseract in common locations
        common_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            "/usr/bin/tesseract",
            "/usr/local/bin/tesseract"
        ]
        
        for path in common_paths:
            if Path(path).exists():
                self.config["tesseract_path"] = path
                pytesseract.pytesseract.tesseract_cmd = path
                return True
        
        # Last resort: try system PATH
        try:
            pytesseract.get_tesseract_version()
            return True
        except:
            return False
            
    def load_configuration(self):
        """Load plugin configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
                    
                # Restore regions from config
                self.regions = self.config.get("regions", [])
                print(f"OCR Plugin: Loaded {len(self.regions)} regions from config")
        except Exception as e:
            print(f"Error loading OCR plugin config: {e}")
            
    def save_configuration(self):
        """Save plugin configuration to file"""
        try:
            # Update config with current regions
            self.config["regions"] = self.regions
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
                
            print("OCR Plugin: Configuration saved")
        except Exception as e:
            print(f"Error saving OCR plugin config: {e}")
            
    def add_region(self, name, x, y, width, height, patterns, cooldown=300):
        """Add a screen region to monitor"""
        region = {
            'name': name,
            'bounds': (x, y, width, height),
            'patterns': patterns,
            'cooldown': cooldown,
            'last_seen': {},
            'enabled': True
        }
        self.regions.append(region)
        self.save_configuration()

        
    def remove_region(self, region_name):
        """Remove a region by name"""
        self.regions = [r for r in self.regions if r['name'] != region_name]
        self.save_configuration()
        
    def _monitor_loop(self):
        """Main monitoring loop"""
        print(f"monitoring")
        while self.monitoring:
            for region in self.regions:
                if region.get('enabled', True):
                    self._check_region(region)
            time.sleep(self.config.get("check_interval", 2.0))
            
    def _check_region(self, region):
        """Check a specific screen region for patterns with multi-monitor support"""
        try:
            x, y, width, height = region['bounds']
            
            # Use mss for screenshot if configured
            if self.config.get("use_mss", True):
                with mss.mss() as sct:
                    monitor = {
                        "left": x,
                        "top": y,
                        "width": width,
                        "height": height
                    }
                    screenshot = sct.grab(monitor)
                    pil_image = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            else:
                # Fallback to pyautogui
                screenshot = pyautogui.screenshot(region=(x, y, width, height))
                pil_image = screenshot
            
            # OCR the image
            ocr_config = self._get_ocr_config()
            text = pytesseract.image_to_string(pil_image, config=ocr_config).lower()
            
            # Check for patterns
            for pattern in region['patterns']:
                if pattern.lower() in text:
                    # Pattern found - trigger action
                    current_time = time.time()
                    last_seen = region['last_seen'].get(pattern, 0)
                    cooldown = region.get('cooldown', 300)
                    
                    if current_time - last_seen > cooldown:
                        region['last_seen'][pattern] = current_time
                        self._on_pattern_detected(region['name'], pattern, text)
                        
        except Exception as e:
            print(f"OCR Error in {region['name']}: {e}")

    def _get_ocr_config(self):
        """Get OCR configuration string"""
        config_str = ""
        
        # Language
        lang = self.config.get("language", "eng")
        if lang and lang != "eng":
            config_str += f"-l {lang} "
            
        # Page segmentation mode
        psm = self.config.get("page_segmentation_mode", 6)
        config_str += f"--psm {psm} "
        
        # OCR engine mode
        oem = self.config.get("ocr_engine_mode", 3)
        config_str += f"--oem {oem}"
        
        return config_str.strip()
            
    def _on_pattern_detected(self, region_name, pattern, detected_text):
        """Handle detected pattern"""
        message = f"OCR detected '{pattern}' in {region_name}"
        print(f"OCR Alert: {message}")
        
        # Use existing action system
        self.app.action_handler.show_notification(message)
        
        # Optional: Speak alert
        if self.config.get("tts_alerts", False):
            self.app.action_handler.speak_text(f"Alert: {pattern} detected", "")
        
    def get_settings_widget(self, parent):
        """Create comprehensive OCR settings widget"""
        def create_widget(master):
            frame = ttk.Frame(master, padding=10)
            
            # Configuration notebook for organized settings
            notebook = ttk.Notebook(frame)
            notebook.pack(fill=tk.BOTH, expand=True, pady=5)
            
            # Tab 1: Tesseract Configuration
            tesseract_tab = ttk.Frame(notebook, padding=10)
            notebook.add(tesseract_tab, text="Tesseract")
            
            self._create_tesseract_tab(tesseract_tab)
            
            # Tab 2: Regions Management
            regions_tab = ttk.Frame(notebook, padding=10)
            notebook.add(regions_tab, text="Regions")
            
            self._create_regions_tab(regions_tab)
            
            # Tab 3: OCR Settings
            ocr_tab = ttk.Frame(notebook, padding=10)
            notebook.add(ocr_tab, text="OCR Settings")
            
            self._create_ocr_tab(ocr_tab)
            
            return frame
            
        return create_widget
        
    def _create_tesseract_tab(self, parent):
        """Create Tesseract configuration tab"""
        # Tesseract path
        ttk.Label(parent, text="Tesseract Path:", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        
        path_frame = ttk.Frame(parent)
        path_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.tesseract_path_var = tk.StringVar(value=self.config.get("tesseract_path", ""))
        ttk.Entry(path_frame, textvariable=self.tesseract_path_var, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(path_frame, text="Browse", command=self._browse_tesseract).pack(side=tk.RIGHT, padx=(5, 0))
        
        # Test Tesseract button
        ttk.Button(parent, text="Test Tesseract", command=self._test_tesseract).pack(anchor=tk.W, pady=5)
        
        # Status label
        self.tesseract_status_var = tk.StringVar(value="Click 'Test Tesseract' to verify installation")
        ttk.Label(parent, textvariable=self.tesseract_status_var, foreground="blue").pack(anchor=tk.W)
        
    def _create_regions_tab(self, parent):
        """Create regions management tab with visual selection"""
        # Add region buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(button_frame, text="🎯 Select Region with Mouse", 
                  command=self._select_region_visual, 
                  style='Primary.TButton').pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(button_frame, text="➕ Add Manual Region", 
                  command=self._add_manual_region_dialog).pack(side=tk.LEFT)
        
        # Preview frame for selected regions
        preview_frame = ttk.LabelFrame(parent, text="Region Preview")
        preview_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.preview_canvas = tk.Canvas(preview_frame, height=150, bg='white')
        self.preview_canvas.pack(fill=tk.X, padx=5, pady=5)
        
        # Regions list with scrollbar
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create treeview for regions
        columns = ('name', 'bounds', 'patterns', 'enabled', 'monitor')
        self.regions_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        self.regions_tree.heading('name', text='Region Name')
        self.regions_tree.heading('bounds', text='Bounds (x,y,w,h)')
        self.regions_tree.heading('patterns', text='Patterns')
        self.regions_tree.heading('enabled', text='Enabled')
        self.regions_tree.heading('monitor', text='Monitor')
        
        self.regions_tree.column('name', width=120)
        self.regions_tree.column('bounds', width=120)
        self.regions_tree.column('patterns', width=150)
        self.regions_tree.column('enabled', width=60)
        self.regions_tree.column('monitor', width=80)
        
        # Scrollbar
        tree_scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.regions_tree.yview)
        self.regions_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.regions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Region controls
        controls_frame = ttk.Frame(parent)
        controls_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(controls_frame, text="Test Selected Region", 
                  command=self._test_region).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Edit Selected", 
                  command=self._edit_region).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Remove Selected", 
                  command=self._remove_region, style='Danger.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Toggle Enabled", 
                  command=self._toggle_region).pack(side=tk.LEFT)
        
        # Refresh regions list
        self._refresh_regions_tree()

    def _select_region_visual(self):
        """Select region using visual mouse selection"""
        try:
            # Hide main window temporarily to avoid interference
            self.app.root.withdraw()
            
            # Get region using visual selector
            region = self.region_selector.select_region()
            
            # Show main window again
            self.app.root.deiconify()
            
            if region:
                x, y, width, height = region
                self._add_region_with_coords(x, y, width, height)
            else:
                self.app.messages(2, 2, "Region selection cancelled")
                
        except Exception as e:
            self.app.root.deiconify()  # Ensure window is shown even on error
            self.app.messages(2, 3, f"Region selection failed: {e}")
            
    def _add_region_with_coords(self, x, y, width, height):
        """Add region with coordinates from visual selection"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Add Screen Region")
        dialog.geometry("400x250")
        dialog.transient(self.app.root)
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Show selected coordinates
        coords_frame = ttk.Frame(main_frame)
        coords_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(coords_frame, text="Selected Region:").pack(anchor=tk.W)
        coords_text = f"X: {x}, Y: {y}, Width: {width}, Height: {height}"
        ttk.Label(coords_frame, text=coords_text, font=("Courier", 9)).pack(anchor=tk.W)
        
        # Region name
        ttk.Label(main_frame, text="Region Name:").pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=name_var).pack(fill=tk.X, pady=(0, 10))
        
        # Patterns
        ttk.Label(main_frame, text="Patterns to detect (one per line):").pack(anchor=tk.W, pady=(0, 5))
        patterns_text = tk.Text(main_frame, height=4)
        patterns_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        patterns_text.insert(1.0, "error\nwarning\ncritical")
        
        def save_region():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Region name is required")
                return
                
            patterns = [p.strip() for p in patterns_text.get(1.0, tk.END).split('\n') if p.strip()]
            
            if not patterns:
                messagebox.showerror("Error", "At least one pattern is required")
                return
                
            self.add_region(name, x, y, width, height, patterns)
            self._refresh_regions_tree()
            self._update_preview()
            dialog.destroy()
            self.app.messages(2, 9, f"Region '{name}' added")
                
        ttk.Button(main_frame, text="Save Region", command=save_region, style='Success.TButton').pack(anchor=tk.E)
        
        # Set focus to name field
        name_var.set(f"Region_{len(self.regions) + 1}")
        dialog.after(100, lambda: name_var.set(f"Region_{len(self.regions) + 1}"))
        
    def _add_manual_region_dialog(self):
        """Dialog for manual region entry (fallback)"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Add Manual Region")
        dialog.geometry("400x300")
        dialog.transient(self.app.root)
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Region name
        ttk.Label(main_frame, text="Region Name:").pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar(value=f"Region_{len(self.regions) + 1}")
        ttk.Entry(main_frame, textvariable=name_var).pack(fill=tk.X, pady=(0, 10))
        
        # Coordinates
        coords_frame = ttk.LabelFrame(main_frame, text="Coordinates")
        coords_frame.pack(fill=tk.X, pady=(0, 10))
        
        coords_inner = ttk.Frame(coords_frame)
        coords_inner.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(coords_inner, text="X:").grid(row=0, column=0, padx=(0, 5))
        x_var = tk.StringVar(value="100")
        ttk.Entry(coords_inner, textvariable=x_var, width=6).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(coords_inner, text="Y:").grid(row=0, column=2, padx=(0, 5))
        y_var = tk.StringVar(value="100")
        ttk.Entry(coords_inner, textvariable=y_var, width=6).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(coords_inner, text="Width:").grid(row=0, column=4, padx=(0, 5))
        w_var = tk.StringVar(value="400")
        ttk.Entry(coords_inner, textvariable=w_var, width=6).grid(row=0, column=5, padx=(0, 10))
        
        ttk.Label(coords_inner, text="Height:").grid(row=0, column=6, padx=(0, 5))
        h_var = tk.StringVar(value="200")
        ttk.Entry(coords_inner, textvariable=h_var, width=6).grid(row=0, column=7)
        
        # Patterns
        ttk.Label(main_frame, text="Patterns to detect (one per line):").pack(anchor=tk.W, pady=(0, 5))
        patterns_text = tk.Text(main_frame, height=6)
        patterns_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        patterns_text.insert(1.0, "error\nwarning\ncritical")
        
        def save_region():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Region name is required")
                return
                
            try:
                x, y, w, h = int(x_var.get()), int(y_var.get()), int(w_var.get()), int(h_var.get())
                patterns = [p.strip() for p in patterns_text.get(1.0, tk.END).split('\n') if p.strip()]
                
                self.add_region(name, x, y, w, h, patterns)
                self._refresh_regions_tree()
                self._update_preview()
                dialog.destroy()
                self.app.messages(2, 9, f"Region '{name}' added")
                
            except ValueError:
                messagebox.showerror("Error", "Invalid coordinates")
                
        ttk.Button(main_frame, text="Save Region", command=save_region, style='Success.TButton').pack(anchor=tk.E)
        
    def _update_preview(self):
        """Update the region preview canvas with multi-monitor awareness"""
        if hasattr(self, 'preview_canvas'):
            self.preview_canvas.delete("all")
            
            canvas_width = self.preview_canvas.winfo_width()
            canvas_height = self.preview_canvas.winfo_height()
            
            if canvas_width > 10:
                try:
                    # Get monitor information
                    with mss.mss() as sct:
                        monitors = sct.monitors[1:]  # Skip the "all in one" monitor
                        
                    # Calculate total virtual screen size
                    all_left = min(monitor['left'] for monitor in monitors)
                    all_top = min(monitor['top'] for monitor in monitors)
                    all_right = max(monitor['left'] + monitor['width'] for monitor in monitors)
                    all_bottom = max(monitor['top'] + monitor['height'] for monitor in monitors)
                    
                    total_width = all_right - all_left
                    total_height = all_bottom - all_top
                    
                    # Scale factor for preview
                    scale_x = canvas_width / total_width
                    scale_y = canvas_height / total_height
                    scale = min(scale_x, scale_y) * 0.8
                    
                    # Calculate offset to center the preview
                    preview_width = total_width * scale
                    preview_height = total_height * scale
                    offset_x = (canvas_width - preview_width) / 2
                    offset_y = (canvas_height - preview_height) / 2
                    
                    # Draw each monitor
                    colors = ['lightgray', 'darkgray', 'lightblue', 'lightgreen']
                    for i, monitor in enumerate(monitors):
                        color = colors[i % len(colors)]
                        
                        # Scale monitor coordinates
                        mx = offset_x + (monitor['left'] - all_left) * scale
                        my = offset_y + (monitor['top'] - all_top) * scale
                        mw = monitor['width'] * scale
                        mh = monitor['height'] * scale
                        
                        # Draw monitor rectangle
                        self.preview_canvas.create_rectangle(
                            mx, my, mx + mw, my + mh,
                            outline='black', width=1, fill=color
                        )
                        
                        # Add monitor label
                        monitor_label = f"Monitor {i+1}"
                        if i == 0:
                            monitor_label += " (Primary)"
                        self.preview_canvas.create_text(
                            mx + 5, my + 15,
                            text=monitor_label,
                            fill='black',
                            font=("Arial", 7),
                            anchor=tk.W
                        )
                    
                    # Draw each region on the preview
                    region_colors = ['red', 'blue', 'green', 'orange', 'purple']
                    for i, region in enumerate(self.regions):
                        rx, ry, rw, rh = region['bounds']
                        color = region_colors[i % len(region_colors)]
                        
                        # Scale region coordinates
                        px = offset_x + (rx - all_left) * scale
                        py = offset_y + (ry - all_top) * scale
                        pw = rw * scale
                        ph = rh * scale
                        
                        # Only draw if region is visible in preview
                        if (px < canvas_width and py < canvas_height and 
                            px + pw > 0 and py + ph > 0):
                            
                            # Draw region rectangle
                            self.preview_canvas.create_rectangle(
                                px, py, px + pw, py + ph,
                                outline=color, width=2, fill='', stipple='gray50'
                            )
                            
                            # Add region name if space permits
                            if pw > 30 and ph > 15:
                                self.preview_canvas.create_text(
                                    px + pw/2, py + ph/2,
                                    text=region['name'],
                                    fill=color,
                                    font=("Arial", 6),
                                    angle=45
                                )
                                
                except Exception as e:
                    print(f"Error updating preview: {e}")
                    # Fallback to simple preview
                    self._fallback_preview()
    def _fallback_preview(self):
        """Fallback preview for single monitor"""
        canvas_width = self.preview_canvas.winfo_width()
        canvas_height = self.preview_canvas.winfo_height()
        
        if canvas_width > 10:
            # Simple rectangle representing primary monitor
            monitor_rect = self.preview_canvas.create_rectangle(
                10, 10, canvas_width - 10, canvas_height - 10,
                outline='gray', width=1
            )
            
            # Draw regions as small rectangles
            for i, region in enumerate(self.regions):
                # Simplified representation - just show relative position
                color = ['red', 'blue', 'green', 'orange', 'purple'][i % 5]
                
                # Use first 2 digits of coordinates for positioning
                x = 10 + (region['bounds'][0] % 90) * (canvas_width - 20) / 100
                y = 10 + (region['bounds'][1] % 90) * (canvas_height - 20) / 100
                w = 20
                h = 15
                
                self.preview_canvas.create_rectangle(
                    x, y, x + w, y + h,
                    outline=color, width=1, fill=color, stipple='gray50'
                )

    def _test_region(self):
        """Test the selected region by capturing and showing what OCR sees"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            region = next((r for r in self.regions if r['name'] == region_name), None)
            
            if region:
                try:
                    x, y, w, h = region['bounds']
                    screenshot = pyautogui.screenshot(region=(x, y, w, h))
                    
                    # Show preview window
                    preview = tk.Toplevel(self.app.root)
                    preview.title(f"OCR Preview - {region_name}")
                    preview.geometry(f"{w+50}x{h+100}")
                    preview.transient(self.app.root)
                    
                    # Display screenshot
                    photo = ImageTk.PhotoImage(screenshot)
                    label = ttk.Label(preview, image=photo)
                    label.image = photo  # Keep reference
                    label.pack(padx=10, pady=10)
                    
                    # Perform OCR and show results
                    ocr_config = self._get_ocr_config()
                    text = pytesseract.image_to_string(screenshot, config=ocr_config)
                    
                    # Show OCR results
                    results_frame = ttk.LabelFrame(preview, text="OCR Results")
                    results_frame.pack(fill=tk.X, padx=10, pady=5)
                    
                    results_text = tk.Text(results_frame, height=4, wrap=tk.WORD)
                    results_text.pack(fill=tk.X, padx=5, pady=5)
                    results_text.insert(1.0, text if text.strip() else "No text detected")
                    results_text.config(state=tk.DISABLED)
                    
                except Exception as e:
                    messagebox.showerror("Test Failed", f"Error testing region: {e}")
                    
    def _refresh_regions_tree(self):
        """Refresh the regions treeview with monitor info"""
        if hasattr(self, 'regions_tree'):
            for item in self.regions_tree.get_children():
                self.regions_tree.delete(item)
                
            for region in self.regions:
                bounds_str = f"{region['bounds'][0]},{region['bounds'][1]},{region['bounds'][2]},{region['bounds'][3]}"
                patterns_str = ", ".join(region['patterns'][:3])
                if len(region['patterns']) > 3:
                    patterns_str += "..."
                
                # Determine which monitor the region is on
                monitor_info = self._get_monitor_info(region['bounds'])
                    
                self.regions_tree.insert('', tk.END, values=(
                    region['name'],
                    bounds_str,
                    patterns_str,
                    "Yes" if region.get('enabled', True) else "No",
                    monitor_info
                ), tags=(region['name'],))
                
        # Update preview after a short delay to ensure UI is rendered
        if hasattr(self, 'preview_canvas'):
            self.app.root.after(100, self._update_preview)
            
    def _get_monitor_info(self, bounds):
        """Get which monitor the region is on"""
        x, y, w, h = bounds
        center_x = x + w // 2
        center_y = y + h // 2
        
        # This is a simplified version - you might want to use screeninfo library
        # for more accurate multi-monitor detection
        screen_width = pyautogui.size().width
        screen_height = pyautogui.size().height
        
        if center_x <= screen_width and center_y <= screen_height:
            return "Primary"
        else:
            return "Secondary"

    def _create_ocr_tab(self, parent):
        """Create OCR settings tab"""
        # Check interval
        ttk.Label(parent, text="Check Interval (seconds):", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.interval_var = tk.StringVar(value=str(self.config.get("check_interval", 2.0)))
        ttk.Entry(parent, textvariable=self.interval_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        # Language
        ttk.Label(parent, text="OCR Language:", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.language_var = tk.StringVar(value=self.config.get("language", "eng"))
        lang_combo = ttk.Combobox(parent, textvariable=self.language_var, 
                                 values=["eng", "spa", "fra", "deu", "ita", "por"], width=10)
        lang_combo.pack(anchor=tk.W, pady=(0, 10))
        
        # Cooldown
        ttk.Label(parent, text="Default Cooldown (seconds):", style='Subtitle.TLabel').pack(anchor=tk.W, pady=(0, 5))
        self.cooldown_var = tk.StringVar(value=str(self.config.get("default_cooldown", 300)))
        ttk.Entry(parent, textvariable=self.cooldown_var, width=10).pack(anchor=tk.W, pady=(0, 10))
        
        # TTS Alerts
        self.tts_alerts_var = tk.BooleanVar(value=self.config.get("tts_alerts", False))
        ttk.Checkbutton(parent, text="Enable TTS Alerts", variable=self.tts_alerts_var).pack(anchor=tk.W, pady=5)
        
        # Apply button
        ttk.Button(parent, text="Apply Settings", 
                  command=self._apply_ocr_settings, style='Success.TButton').pack(anchor=tk.W, pady=(10, 0))
        
    def _browse_tesseract(self):
        """Browse for Tesseract executable"""
        filename = filedialog.askopenfilename(
            title="Select Tesseract Executable",
            filetypes=[("Executable files", "*.exe"), ("All files", "*.*")],
            initialfile="tesseract.exe"
        )
        if filename:
            self.tesseract_path_var.set(filename)
            
    def _test_tesseract(self):
        """Test Tesseract installation"""
        path = self.tesseract_path_var.get()
        if path and Path(path).exists():
            pytesseract.pytesseract.tesseract_cmd = path
            
        try:
            version = pytesseract.get_tesseract_version()
            self.tesseract_status_var.set(f"✓ Tesseract {version} working correctly")
            # Update config
            self.config["tesseract_path"] = path
            self.save_configuration()
        except Exception as e:
            self.tesseract_status_var.set(f"✗ Tesseract error: {e}")
            
    def _add_region_dialog(self):
        """Dialog to add a new screen region"""
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Add Screen Region")
        dialog.geometry("400x300")
        dialog.transient(self.app.root)
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Region name
        ttk.Label(main_frame, text="Region Name:").pack(anchor=tk.W, pady=(0, 5))
        name_var = tk.StringVar()
        ttk.Entry(main_frame, textvariable=name_var).pack(fill=tk.X, pady=(0, 10))
        
        # Coordinates
        coords_frame = ttk.Frame(main_frame)
        coords_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(coords_frame, text="X:").grid(row=0, column=0, padx=(0, 5))
        x_var = tk.StringVar(value="100")
        ttk.Entry(coords_frame, textvariable=x_var, width=6).grid(row=0, column=1, padx=(0, 10))
        
        ttk.Label(coords_frame, text="Y:").grid(row=0, column=2, padx=(0, 5))
        y_var = tk.StringVar(value="100")
        ttk.Entry(coords_frame, textvariable=y_var, width=6).grid(row=0, column=3, padx=(0, 10))
        
        ttk.Label(coords_frame, text="Width:").grid(row=0, column=4, padx=(0, 5))
        w_var = tk.StringVar(value="400")
        ttk.Entry(coords_frame, textvariable=w_var, width=6).grid(row=0, column=5, padx=(0, 10))
        
        ttk.Label(coords_frame, text="Height:").grid(row=0, column=6, padx=(0, 5))
        h_var = tk.StringVar(value="200")
        ttk.Entry(coords_frame, textvariable=h_var, width=6).grid(row=0, column=7)
        
        # Patterns
        ttk.Label(main_frame, text="Patterns to detect (one per line):").pack(anchor=tk.W, pady=(0, 5))
        patterns_text = tk.Text(main_frame, height=6)
        patterns_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        patterns_text.insert(1.0, "error\nwarning\ncritical")
        
        def save_region():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Region name is required")
                return
                
            try:
                x, y, w, h = int(x_var.get()), int(y_var.get()), int(w_var.get()), int(h_var.get())
                patterns = [p.strip() for p in patterns_text.get(1.0, tk.END).split('\n') if p.strip()]
                
                self.add_region(name, x, y, w, h, patterns)
                self._refresh_regions_tree()
                dialog.destroy()
                
            except ValueError:
                messagebox.showerror("Error", "Invalid coordinates")
                
        ttk.Button(main_frame, text="Save Region", command=save_region, style='Success.TButton').pack(anchor=tk.E)
        
    def _refresh_regions_tree(self):
        """Refresh the regions treeview"""
        if hasattr(self, 'regions_tree'):
            for item in self.regions_tree.get_children():
                self.regions_tree.delete(item)
                
            for region in self.regions:
                bounds_str = f"{region['bounds'][0]},{region['bounds'][1]},{region['bounds'][2]},{region['bounds'][3]}"
                patterns_str = ", ".join(region['patterns'][:3])  # Show first 3 patterns
                if len(region['patterns']) > 3:
                    patterns_str += "..."
                    
                self.regions_tree.insert('', tk.END, values=(
                    region['name'],
                    bounds_str,
                    patterns_str,
                    "Yes" if region.get('enabled', True) else "No"
                ), tags=(region['name'],))
                
    def _edit_region(self):
        """Edit selected region"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            # Implementation similar to _add_region_dialog but with existing data
            # For brevity, this would populate the dialog with existing region data
            
    def _remove_region(self):
        """Remove selected region"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            self.remove_region(region_name)
            self._refresh_regions_tree()
            
    def _toggle_region(self):
        """Toggle region enabled state"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            for region in self.regions:
                if region['name'] == region_name:
                    region['enabled'] = not region.get('enabled', True)
                    break
            self.save_configuration()
            self._refresh_regions_tree()
            
    def _apply_ocr_settings(self):
        """Apply OCR settings from the UI"""
        try:
            self.config["check_interval"] = float(self.interval_var.get())
            self.config["language"] = self.language_var.get()
            self.config["default_cooldown"] = int(self.cooldown_var.get())
            self.config["tts_alerts"] = self.tts_alerts_var.get()
            
            self.save_configuration()
            self.app.messages(2, 9, "OCR settings applied")
            
        except ValueError as e:
            self.app.messages(2, 3, f"Invalid setting value: {e}")