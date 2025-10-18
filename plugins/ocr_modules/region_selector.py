# plugins/ocr_modules/region_selector.py
import tkinter as tk
from tkinter import ttk, messagebox
import pyautogui
from PIL import Image, ImageTk
import mss
import win32gui
import win32ui
import win32con

# Import from our other modules
from .capture import WindowCapture, CaptureMethod

class RegionSelector:
    """Visual region selector with proper multi-monitor support and capture methods"""
    
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
        self.selected_window = None
        self.monitors = []
        self.capture_manager = WindowCapture()
        self.window_selection_mode = False

    def select_window(self):
        """Select a specific window instead of screen region"""
        try:
            self.window_selection_mode = True
            self.app.root.withdraw()
            
            # Create window selection interface
            selector = tk.Toplevel()
            selector.attributes('-fullscreen', True)
            selector.attributes('-alpha', 0.3)
            selector.attributes('-topmost', True)
            selector.configure(cursor='crosshair')
            selector.configure(bg='blue')
            
            # Instructions
            label = tk.Label(selector, 
                           text="Click on the window you want to capture. Press ESC to cancel.",
                           font=("Arial", 16, "bold"), 
                           bg='blue', fg='white')
            label.place(relx=0.5, rely=0.1, anchor=tk.CENTER)
            
            def on_click(event):
                x, y = event.x_root, event.y_root
                hwnd = win32gui.WindowFromPoint((x, y))
                
                # Get window info
                window_text = win32gui.GetWindowText(hwnd)
                class_name = win32gui.GetClassName(hwnd)
                
                if hwnd and win32gui.IsWindowVisible(hwnd):
                    # Get window rect
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    width = right - left
                    height = bottom - top
                    
                    # Store window info
                    self.selected_window = {
                        'hwnd': hwnd,
                        'title': window_text,
                        'class_name': class_name,
                        'bounds': (left, top, width, height)
                    }
                    
                    print(f"Selected window: {window_text} (Class: {class_name})")
                    print(f"Window bounds: {left}, {top}, {width}, {height}")
                    
                    selector.destroy()
                    self.app.root.deiconify()
                    
                    # Open window configuration dialog
                    self._configure_window_region()
                else:
                    messagebox.showwarning("Invalid Window", "Please select a valid visible window.")
            
            def cancel_selection(event=None):
                self.selected_window = None
                selector.destroy()
                self.app.root.deiconify()
            
            selector.bind('<Button-1>', on_click)
            selector.bind('<Escape>', cancel_selection)
            selector.focus_force()
            
        except Exception as e:
            print(f"Window selection error: {e}")
            self.app.root.deiconify()

    def _configure_window_region(self):
        """Configure region for a selected window"""
        if not self.selected_window:
            return
            
        dialog = tk.Toplevel(self.app.root)
        dialog.title("Configure Window Capture")
        dialog.geometry("500x400")
        dialog.transient(self.app.root)
        
        main_frame = ttk.Frame(dialog, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Window info
        info_frame = ttk.LabelFrame(main_frame, text="Window Information")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = tk.Text(info_frame, height=4, wrap=tk.WORD)
        info_text.pack(fill=tk.X, padx=5, pady=5)
        
        window_info = self.selected_window
        info_text.insert(1.0, 
            f"Window Title: {window_info['title']}\n"
            f"Class: {window_info['class_name']}\n"
            f"Handle: {window_info['hwnd']}\n"
            f"Bounds: {window_info['bounds']}"
        )
        info_text.config(state=tk.DISABLED)
        
        # Region name
        ttk.Label(main_frame, text="Region Name:").pack(anchor=tk.W, pady=(10, 5))
        name_var = tk.StringVar(value=window_info['title'][:30] or f"Window_{window_info['hwnd']}")
        ttk.Entry(main_frame, textvariable=name_var).pack(fill=tk.X, pady=(0, 10))
        
        # Capture method for window
        ttk.Label(main_frame, text="Capture Method:").pack(anchor=tk.W, pady=(0, 5))
        method_var = tk.StringVar(value="auto")
        method_combo = ttk.Combobox(main_frame, textvariable=method_var,
                                  values=[method.value for method in CaptureMethod],
                                  state="readonly")
        method_combo.pack(fill=tk.X, pady=(0, 10))
        
        # Test capture button
        def test_capture():
            try:
                self.capture_manager.set_method(method_var.get())
                image = self.capture_manager.capture_region(hwnd=window_info['hwnd'])
                if image:
                    # Show preview
                    preview = tk.Toplevel(dialog)
                    preview.title("Capture Test")
                    
                    # Resize for preview
                    display_width = min(image.width, 400)
                    scale_factor = display_width / image.width
                    display_height = int(image.height * scale_factor)
                    
                    preview_image = image.resize((display_width, display_height), Image.LANCZOS)
                    photo = ImageTk.PhotoImage(preview_image)
                    
                    label = ttk.Label(preview, image=photo)
                    label.image = photo
                    label.pack(padx=10, pady=10)
                    
                    ttk.Label(preview, text="If you see a black screen, try a different capture method.").pack(pady=5)
                else:
                    messagebox.showerror("Test Failed", "Failed to capture window")
            except Exception as e:
                messagebox.showerror("Test Failed", f"Error: {e}")
        
        ttk.Button(main_frame, text="Test Capture", command=test_capture).pack(anchor=tk.W, pady=(0, 10))
        
        # Patterns (same as before but for window)
        patterns_frame = ttk.LabelFrame(main_frame, text="Patterns to Monitor")
        patterns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        patterns_text = tk.Text(patterns_frame, height=6)
        patterns_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        patterns_text.insert(1.0, "error\nwarning\nalert\ncritical")
        
        def save_window_region():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Region name is required")
                return
                
            patterns = [p.strip() for p in patterns_text.get(1.0, tk.END).strip().split('\n') if p.strip()]
            if not patterns:
                messagebox.showerror("Error", "At least one pattern is required")
                return
            
            # Pass window info to the plugin
            if hasattr(self.app, 'plugins') and 'OCRMonitorPlugin' in self.app.plugins:
                plugin = self.app.plugins['OCRMonitorPlugin']
                plugin.add_window_region(
                    name=name,
                    hwnd=window_info['hwnd'],
                    window_title=window_info['title'],
                    capture_method=method_var.get(),
                    patterns=patterns,
                    cooldown=300
                )
                
            dialog.destroy()
            self.app.messages(2, 9, f"Window region '{name}' added")
        
        ttk.Button(main_frame, text="Save Window Region", 
                  command=save_window_region, style='Success.TButton').pack(anchor=tk.E)

    def capture_all_monitors(self):
        """Capture screenshot of all monitors combined using WindowCapture"""
        # Make sure we have monitor data
        if not self.monitors:
            self.get_all_monitors()
            
        try:
            # Calculate bounding box that contains all monitors
            all_left = min(monitor['left'] for monitor in self.monitors)
            all_top = min(monitor['top'] for monitor in self.monitors)
            all_right = max(monitor['right'] for monitor in self.monitors)
            all_bottom = max(monitor['bottom'] for monitor in self.monitors)
            
            total_width = all_right - all_left
            total_height = all_bottom - all_top
            
            print(f"DEBUG: Virtual screen bounds: left={all_left}, top={all_top}, right={all_right}, bottom={all_bottom}")
            print(f"DEBUG: Capturing virtual screen: {total_width}x{total_height}")
            
            # Use WindowCapture to capture the region
            region = {
                'left': all_left,
                'top': all_top, 
                'width': total_width,
                'height': total_height
            }
            
            return self.capture_manager.capture_region(region=region)
            
        except Exception as e:
            print(f"Error capturing all monitors: {e}")
            raise
        
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

    def select_region_within_window(self, hwnd, window_bounds):
        """Select a region within a specific window"""
        try:
            import win32gui
            import win32con
        
            # Bring window to foreground for selection
            win32gui.SetForegroundWindow(hwnd)
        
            # Create selection window that covers only the target window
            selector = tk.Toplevel()
            selector.attributes('-fullscreen', True)
            selector.attributes('-alpha', 0.3)
            selector.configure(background='lightblue')
            selector.attributes('-topmost', True)
        
            # Position overlay to match window position and size
            x, y, width, height = window_bounds
            selector.geometry(f"{width}x{height}+{x}+{y}")

            canvas = tk.Canvas(selector, highlightthickness=0, cursor="crosshair")
            canvas.pack(fill=tk.BOTH, expand=True)

            # Draw window border
            canvas.create_rectangle(0, 0, width, height, outline='red', width=2)

            start_x, start_y = None, None
            rect = None

            def on_mouse_press(event):
                nonlocal start_x, start_y, rect
                start_x, start_y = event.x, event.y
                rect = canvas.create_rectangle(start_x, start_y, start_x, start_y, 
                                            outline='yellow', width=2, fill='blue', stipple='gray50')

            def on_mouse_drag(event):
                nonlocal rect
                if rect:
                    canvas.coords(rect, start_x, start_y, event.x, event.y)

            def on_mouse_release(event):
                nonlocal start_x, start_y
                if start_x is not None:
                    end_x, end_y = event.x, event.y

                    # Normalize coordinates
                    x1 = min(start_x, end_x)
                    y1 = min(start_y, end_y)
                    x2 = max(start_x, end_x)
                    y2 = max(start_y, end_y)

                    width = x2 - x1
                    height = y2 - y1

                    if width > 10 and height > 10:  # Minimum size
                        # Convert to screen coordinates
                        screen_x = x + x1
                        screen_y = y + y1

                        self.selected_region = (screen_x, screen_y, width, height)
                        selector.destroy()
                    else:
                        messagebox.showwarning("Too Small", "Please select a larger region.")
                        canvas.delete(rect)

            def on_escape(event):
                self.selected_region = None
                selector.destroy()

            canvas.bind("<ButtonPress-1>", on_mouse_press)
            canvas.bind("<B1-Motion>", on_mouse_drag)
            canvas.bind("<ButtonRelease-1>", on_mouse_release)
            selector.bind("<Escape>", on_escape)

            selector.wait_window()
            return self.selected_region

        except Exception as e:
            print(f"Error selecting sub-region: {e}")
            return None

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
            monitor_text = f"Monitor {i}"
            if i == 1:  # Monitor 1 is typically the primary
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
        try:
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
            
        except Exception as e:
            print(f"Error in fallback region selection: {e}")
            return None
        
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
                monitor_type = "Primary" if i == 1 else f"Monitor {i}"
                return f"{monitor_type} ({monitor['width']}x{monitor['height']})"
                
        return "Unknown Monitor"
                
    def cancel_selection(self, event=None):
        """Cancel region selection"""
        self.selected_region = None
        if self.selector_window:
            self.selector_window.destroy()

    def capture_region_for_preview(self, region_coords):
        """Capture a specific region for preview using configured method"""
        try:
            x, y, width, height = region_coords
            region = {
                'left': x,
                'top': y,
                'width': width,
                'height': height
            }
            return self.capture_manager.capture_region(region=region)
        except Exception as e:
            print(f"Error capturing region for preview: {e}")
            return None
