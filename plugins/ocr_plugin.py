# plugins/ocr_plugin.py
try:
    # Try to import from plugins package (source mode)
    from plugins.etail_plugin import ETailPlugin
except ImportError:
    try:
        # Try direct import (compiled mode)
        from etail_plugin import ETailPlugin
    except ImportError:
        # Fallback: define it here
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
from tkinter import ttk, filedialog, messagebox
import pyautogui
import pytesseract
from PIL import Image, ImageTk, ImageEnhance, ImageFilter
import time
import threading
import json
from pathlib import Path
import mss
import mss.tools
import win32gui
import win32ui
import win32con
import win32process
import mss
import ctypes
from ctypes import wintypes
from enum import Enum
import numpy as np
import psutil  # You'll need to: pip install psutil

#try:
#    from ocr_modules.config import ConfigManager  # NEW IMPORT
#    print("✅ Successfully imported from capture.py")
#except ImportError as e:
    #print(f"❌ Import failed: {e}")
    # Let's see what IS in the module
#    from ocr_modules.config import conf_mod  # NEW IMPORT
    #print("Available in capture module:", dir(conf_mod))

from ocr_modules.capture import WindowCapture, CaptureMethod
from ocr_modules.config import ConfigManager
from ocr_modules.region_selector import RegionSelector
from ocr_modules.ui.ui_components import PatternTTSDialog
from ocr_modules.ui.settings_tabs import SettingsTabs  # NEW IMPORT

class OCRMonitorPlugin(ETailPlugin):
    def __init__(self, app):
        super().__init__(app)
        self.name = "OCR Screen Monitor"
        self.version = "2.2"  # Updated version with capture methods
        self.description = "Monitor specific screen areas for text using OCR with multi-monitor support, gaming optimizations, color filtering, and advanced capture methods"

        # NEW: Initialize config manager
        self.config_manager = ConfigManager()
        self.config = self.config_manager.config  # Keep for compatibility

        self.profile_var = None
        self.preprocess_var = None
        self.fuzzy_var = None
        self.fuzzy_threshold_var = None
        self.performance_var = None
        self.stats_var = None

        self.color_filter_var = None
        self.color_profile_var = None
        self.tolerance_var = None
        self.profiles_listbox = None

        from ocr_modules.capture import CaptureMethod
        self.capture_methods = list(CaptureMethod)

        self.performance_stats = {
            'total_checks': 0,
            'successful_ocr': 0,
            'average_time': 0.0,
            'last_check_time': 0.0,
            'capture_method_stats': {}
        }

        self.monitoring = False
        self.monitor_thread = None
        self.regions = []
        self.region_selector = RegionSelector(app)
        self.window_capture = WindowCapture()  # Add WindowCapture instance

        self.regions_tree = None
        self.region_methods_tree = None
        self.preview_canvas = None        

        # Load regions from config
        self.regions = self.config.get("regions", [])
        self.settings_tabs = SettingsTabs(self)
        
    def setup(self):
        """Setup the OCR monitor with configuration"""
        # Verify Tesseract path
        if not self.verify_tesseract():
            self.app.messages(2, 3, "Tesseract not found. Please configure path in plugin settings.")
            return False
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.app.messages(2, 9, "OCR Screen Monitor enabled with gaming optimizations and color filtering")
        return True
 
    # REPLACE your existing load/save methods with these:
    def load_configuration(self):
        # Now handled entirely by ConfigManager
        pass
        
    def save_configuration(self):
        # Make sure regions are saved to config before saving
        self.config["regions"] = self.regions
        self.config_manager.save_configuration()
 
    def teardown(self):
        """Stop the OCR monitor and save configuration"""
        self.monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
        
        # Print performance summary if enabled
        if self.config.get("performance_monitoring", True) and self.performance_stats['total_checks'] > 0:
            success_rate = (self.performance_stats['successful_ocr'] / self.performance_stats['total_checks']) * 100
            print(f"OCR Performance Summary: {success_rate:.1f}% success rate over {self.performance_stats['total_checks']} checks")
            
        self.app.messages(2, 9, "OCR Screen Monitor disabled")
        self.save_configuration()
        self.reset_monitoring_state()
        
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
            
    def add_region(self, name, x, y, width, height, patterns, cooldown=300, color_profile=None, tts_messages=None, capture_method=None):
        """Add a screen region to monitor with optional color profile, TTS messages, and capture method"""
        region = {
            'name': name,
            'bounds': (x, y, width, height),
            'patterns': patterns,
            'cooldown': cooldown or self.config.get("default_cooldown", 300),
            'last_seen': {},
            'enabled': True,
            'color_profile': color_profile or self.config.get("current_color_profile", "default"),
            'tts_messages': tts_messages or {},  # Dictionary: pattern -> custom TTS message
            'capture_method': capture_method or self.config.get("capture_method", "auto")  # Per-region capture method
        }
        self.regions.append(region)
        self.save_configuration()
        
    def remove_region(self, region_name):
        """Remove a region by name"""
        self.regions = [r for r in self.regions if r['name'] != region_name]
        self.save_configuration()
        
    def _monitor_loop(self):
        """Optimized monitoring loop with performance tracking"""      
        while self.monitoring:
            loop_start = time.time()
            checks_this_cycle = 0
            successful_checks = 0
            for region in self.regions:
                if not region.get('enabled', True):
                    continue
                # Skip if we're in cooldown for all patterns in this region
                current_time = time.time()
                all_in_cooldown = all(
                    current_time - region['last_seen'].get(pattern, 0) < region.get('cooldown', 300)
                    for pattern in region['patterns']
                )              
                if not all_in_cooldown:
                    checks_this_cycle += 1
                    try:
                        self._check_region(region)
                        successful_checks += 1
                    except Exception as e:
                        print(f"Error checking region {region['name']}: {e}")
            
            # Update performance stats
            if checks_this_cycle > 0:
                self.performance_stats['total_checks'] += checks_this_cycle
                self.performance_stats['successful_ocr'] += successful_checks
                self.performance_stats['last_check_time'] = time.time() - loop_start
          
            # Adaptive sleep based on processing time
            processing_time = time.time() - loop_start
            sleep_time = max(0.1, self.config.get("check_interval", 2.0) - processing_time)
            time.sleep(sleep_time)
            
    def apply_color_filtering(self, image, color_profile_name="default"):
        """Extract only pixels matching target colors and create high-contrast image for OCR"""
        if not self.config.get("enable_color_filtering", True):
            return image
            
        profile = self.config["color_filters"].get(color_profile_name, 
                                                 self.config["color_filters"]["default"])
        
        # Convert PIL Image to numpy array for processing
        img_array = np.array(image)
        
        # Create a mask that starts as all False
        combined_mask = np.zeros(img_array.shape[:2], dtype=bool)
        tolerance = self.config.get("color_tolerance", 30)
        
        for target_color in profile["target_colors"]:
            # Create mask for this specific color
            r, g, b = target_color["r"], target_color["g"], target_color["b"]
            
            # Calculate distance from target color for each pixel
            color_distance = np.sqrt(
                (img_array[:, :, 0] - r) ** 2 +
                (img_array[:, :, 1] - g) ** 2 +
                (img_array[:, :, 2] - b) ** 2
            )
            
            # Add pixels within tolerance to the combined mask
            color_mask = color_distance <= tolerance
            combined_mask = combined_mask | color_mask
        
        # Create output image (white background by default)
        if profile.get("invert_after_filter", True):
            # Black text on white background (best for OCR)
            output_array = np.ones_like(img_array) * 255  # White background
            output_array[combined_mask] = [0, 0, 0]  # Black text
        else:
            # White text on black background
            output_array = np.zeros_like(img_array)  # Black background  
            output_array[combined_mask] = [255, 255, 255]  # White text
        
        return Image.fromarray(output_array)

    def extract_dominant_text_colors(self, image, num_colors=5):
        """Automatically detect dominant colors in the image that might be text"""
        # Convert to numpy array
        img_array = np.array(image)
        
        # Reshape to 2D array of pixels
        pixels = img_array.reshape(-1, 3)
        
        # Simple color grouping to find dominant colors
        from collections import Counter
        
        # Sample pixels to speed up processing
        if len(pixels) > 10000:
            indices = np.random.choice(len(pixels), 10000, replace=False)
            pixels = pixels[indices]
        
        # Group similar colors (simple approach)
        color_buckets = {}
        bucket_size = 20  # Group colors within this range
        
        for pixel in pixels:
            # Skip very dark and very light pixels (likely background)
            brightness = np.mean(pixel)
            if brightness < 30 or brightness > 220:
                continue
                
            # Quantize color
            bucket = tuple((pixel // bucket_size) * bucket_size)
            if bucket in color_buckets:
                color_buckets[bucket] += 1
            else:
                color_buckets[bucket] = 1
        
        # Get most common colors
        most_common = sorted(color_buckets.items(), key=lambda x: x[1], reverse=True)[:num_colors]
        
        dominant_colors = []
        for bucket, count in most_common:
            if count > len(pixels) * 0.01:  # At least 1% of pixels
                color = {
                    "r": int(bucket[0] + bucket_size / 2),
                    "g": int(bucket[1] + bucket_size / 2), 
                    "b": int(bucket[2] + bucket_size / 2)
                }
                dominant_colors.append(color)
        
        return dominant_colors

    def interactive_color_picker(self, region):
        """Interactive tool to pick text colors from a region"""
        try:
            x, y, w, h = region['bounds']
            
            # Capture the region
            with mss.mss() as sct:
                monitor = {"left": x, "top": y, "width": w, "height": h}
                screenshot = sct.grab(monitor)
                image = Image.frombytes('RGB', screenshot.size, screenshot.bgra, 'raw', 'BGRX')
            
            # Create color picker window
            picker_window = tk.Toplevel(self.app.root)
            picker_window.title("Color Picker - Click on Text Colors")
            picker_window.geometry(f"{w+100}x{h+200}")
            picker_window.transient(self.app.root)
            
            # Display image
            photo = ImageTk.PhotoImage(image)
            image_label = ttk.Label(picker_window, image=photo)
            image_label.image = photo
            image_label.pack(padx=10, pady=10)
            
            # Selected colors display
            colors_frame = ttk.Frame(picker_window)
            colors_frame.pack(fill=tk.X, padx=10, pady=5)
            
            ttk.Label(colors_frame, text="Selected Colors:").pack(anchor=tk.W)
            selected_colors = []
            
            colors_display = ttk.Frame(colors_frame)
            colors_display.pack(fill=tk.X, pady=5)
            
            # Auto-detect button
            def auto_detect_colors():
                nonlocal selected_colors
                dominant_colors = self.extract_dominant_text_colors(image)
                selected_colors = dominant_colors
                update_colors_display()
                
            ttk.Button(colors_frame, text="Auto-Detect Colors", 
                      command=auto_detect_colors).pack(anchor=tk.W, pady=5)
            
            def update_colors_display():
                # Clear current display
                for widget in colors_display.winfo_children():
                    widget.destroy()
                
                # Show selected colors
                for i, color in enumerate(selected_colors):
                    color_frame = ttk.Frame(colors_display)
                    color_frame.pack(fill=tk.X, pady=2)
                    
                    # Color swatch
                    color_swatch = tk.Canvas(color_frame, width=20, height=20)
                    color_swatch.create_rectangle(0, 0, 20, 20, 
                                                fill=f'#{color["r"]:02x}{color["g"]:02x}{color["b"]:02x}')
                    color_swatch.pack(side=tk.LEFT, padx=(0, 10))
                    
                    # Color values
                    color_text = f'RGB({color["r"]}, {color["g"]}, {color["b"]})'
                    ttk.Label(color_frame, text=color_text).pack(side=tk.LEFT)
                    
                    # Remove button
                    ttk.Button(color_frame, text="Remove", 
                              command=lambda idx=i: remove_color(idx)).pack(side=tk.RIGHT)
            
            def remove_color(index):
                nonlocal selected_colors
                if 0 <= index < len(selected_colors):
                    selected_colors.pop(index)
                    update_colors_display()
            
            def on_image_click(event):
                nonlocal selected_colors
                # Get clicked color
                if event.x < 0 or event.y < 0 or event.x >= w or event.y >= h:
                    return
                    
                # Get pixel color (account for image scaling in display)
                scale_x = image.width / photo.width()
                scale_y = image.height / photo.height()
                
                pixel_x = int(event.x * scale_x)
                pixel_y = int(event.y * scale_y)
                
                if pixel_x < image.width and pixel_y < image.height:
                    pixel_color = image.getpixel((pixel_x, pixel_y))
                    color = {"r": pixel_color[0], "g": pixel_color[1], "b": pixel_color[2]}
                    
                    # Add to selected colors if not already there
                    if not any(c["r"] == color["r"] and c["g"] == color["g"] and c["b"] == color["b"] 
                              for c in selected_colors):
                        selected_colors.append(color)
                        update_colors_display()
            
            def save_colors():
                if selected_colors:
                    profile_name = f"custom_{region['name']}"
                    self.config["color_filters"][profile_name] = {
                        "target_colors": selected_colors,
                        "invert_after_filter": True
                    }
                    self.config["current_color_profile"] = profile_name
                    self.app.messages(2, 9, f"Color profile '{profile_name}' saved with {len(selected_colors)} colors")
                    picker_window.destroy()
                else:
                    messagebox.showwarning("No Colors", "Please select at least one text color")
            
            def preview_filter():
                if selected_colors:
                    # Create temporary profile for preview
                    temp_profile = {
                        "target_colors": selected_colors,
                        "invert_after_filter": True
                    }
                    
                    # Apply filtering
                    filtered_image = self.apply_color_filtering_with_profile(image, temp_profile)
                    
                    # Show preview
                    preview_photo = ImageTk.PhotoImage(filtered_image)
                    image_label.configure(image=preview_photo)
                    image_label.image = preview_photo
            
            # Bind click event
            image_label.bind("<Button-1>", on_image_click)
            
            # Control buttons
            button_frame = ttk.Frame(picker_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(button_frame, text="Preview Filter", 
                      command=preview_filter).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Save Colors", 
                      command=save_colors, style='Success.TButton').pack(side=tk.LEFT)
            ttk.Button(button_frame, text="Cancel", 
                      command=picker_window.destroy).pack(side=tk.RIGHT)
            
        except Exception as e:
            messagebox.showerror("Color Picker Error", f"Failed to open color picker: {e}")

    def apply_color_filtering_with_profile(self, image, profile):
        """Apply color filtering with a specific profile"""
        # Convert PIL Image to numpy array
        img_array = np.array(image)
        
        # Create mask
        combined_mask = np.zeros(img_array.shape[:2], dtype=bool)
        tolerance = self.config.get("color_tolerance", 30)
        
        for target_color in profile["target_colors"]:
            r, g, b = target_color["r"], target_color["g"], target_color["b"]
            
            color_distance = np.sqrt(
                (img_array[:, :, 0] - r) ** 2 +
                (img_array[:, :, 1] - g) ** 2 +
                (img_array[:, :, 2] - b) ** 2
            )
            
            color_mask = color_distance <= tolerance
            combined_mask = combined_mask | color_mask
        
        # Create output image
        if profile.get("invert_after_filter", True):
            output_array = np.ones_like(img_array) * 255
            output_array[combined_mask] = [0, 0, 0]
        else:
            output_array = np.zeros_like(img_array)
            output_array[combined_mask] = [255, 255, 255]
        
        return Image.fromarray(output_array)

    def preprocess_image_for_gaming(self, image, region_name=None):
        """Enhanced pre-processing with color filtering"""
        if not self.config.get("enable_preprocessing", True):
            return image
        
        try:
            # Step 1: Apply color filtering if enabled
            if self.config.get("enable_color_filtering", True) and region_name:
                # Find region to get its color profile
                region = next((r for r in self.regions if r['name'] == region_name), None)
                if region and region.get('color_profile'):
                    profile_name = region['color_profile']
                else:
                    profile_name = self.config.get("current_color_profile", "default")
                
                profile = self.config["color_filters"].get(profile_name)
                if profile:
                    image = self.apply_color_filtering_with_profile(image, profile)
            
            # Step 2: Convert to grayscale if not already
            if image.mode != 'L':
                image = image.convert('L')
            
            # Step 3: Get current profile settings for other processing
            profile_name = self.config.get("current_profile", "default")
            profile_settings = self.config["game_profiles"].get(profile_name, {})
            
            # Step 4: Apply scaling
            scale_factor = profile_settings.get("scale_factor", 1.0)
            if scale_factor != 1.0:
                new_width = int(image.width * scale_factor)
                new_height = int(image.height * scale_factor)
                image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Step 5: Enhance contrast
            contrast_level = profile_settings.get("contrast", 1.5)
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(contrast_level)
            
            # Step 6: Enhance sharpness
            sharpness_enhancer = ImageEnhance.Sharpness(image)
            image = sharpness_enhancer.enhance(1.2)
            
            return image
            
        except Exception as e:
            print(f"Enhanced pre-processing error: {e}")
            return image
            
    def _check_region(self, region):
        """Enhanced region checking with sub-region support"""
        current_cooldown = region.get('cooldown', 300)
        try:
            # Set capture method
            capture_method = region.get('capture_method', self.config.get("capture_method", "auto"))
            self.window_capture.set_method(capture_method)

            pil_image = None

            # Handle window regions
            if region.get('type') == 'window':
                # Find the window dynamically
                hwnd = self.find_best_window_match(region)

                if hwnd:
                    # Update window bounds in region (for display purposes)
                    try:
                        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                        width = right - left
                        height = bottom - top
                        region['bounds'] = (left, top, width, height)
                        region['current_hwnd'] = hwnd  # Temporary, for this session only
                    except:
                        pass

                    # Capture the window (with sub-region support)
                    if region.get('subregion_bounds'):
                        # Capture sub-region of the window
                        sub_x, sub_y, sub_w, sub_h = region['subregion_bounds']
                        print(f"DEBUG: Capturing subregion: {sub_x}, {sub_y}, {sub_w}, {sub_h} from window bounds: {left}, {top}, {width}, {height}")
                    
                        # Create region dict for the sub-region (absolute screen coordinates)
                        region_dict = {
                            "left": left + sub_x,
                            "top": top + sub_y, 
                            "width": sub_w,
                            "height": sub_h
                        }
                        print(f"DEBUG: Absolute subregion coordinates: {region_dict}")
                        subregion_bounds=region['subregion_bounds']
                        pil_image = self.window_capture.capture_region(hwnd=hwnd, subregion_bounds=subregion_bounds)
                        if pil_image:
                            print(f"DEBUG: Subregion capture successful: {pil_image.width}x{pil_image.height}")
                        else:
                            print("DEBUG: Subregion capture failed")
                    else:
                        # Capture entire window
                        print("DEBUG: Capturing entire window (no subregion)")
                        pil_image = self.window_capture.capture_region(hwnd=hwnd)

                    if not pil_image:
                        print(f"Window capture failed for {region['name']}. Window might be minimized or inaccessible.")
                else:
                    print(f"Window not found for region: {region['name']}")
                    return
            else:
                # Screen region capture (existing code)
                x, y, width, height = region['bounds']
                region_dict = {
                    "left": x,
                    "top": y,
                    "width": width,
                    "height": height
                }
                pil_image = self.window_capture.capture_region(region=region_dict)

            if pil_image is None:
                return

            # Enhanced image pre-processing for games with color filtering
            processed_image = self.preprocess_image_for_gaming(pil_image, region['name'])

            # OCR with game-optimized configuration
            ocr_config = self._get_ocr_config()
            text = pytesseract.image_to_string(processed_image, config=ocr_config)

            # Enhanced pattern matching
            if text.strip():
                self._enhanced_pattern_matching(region, text)

        except Exception as e:
            print(f"OCR Error in {region['name']}: {e}")

    def _test_region(self):
        """Test the selected region with proper window region support"""
        print("DEBUG: _test_region method called 587")
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            region = next((r for r in self.regions if r['name'] == region_name), None)

            if region:
                print(f"DEBUG: Testing region: {region['name']}, type: {region.get('type', 'screen')}594")
            
                # Create enhanced test dialog that works for both screen and window regions
                self._create_enhanced_region_test_dialog(region)

    def _create_region_test_dialog(self, region):
        """Create an enhanced test dialog with real-time preview"""
        try:
            preview = tk.Toplevel(self.app.root)
            preview.title(f"OCR Test - {region['name']}")
            preview.geometry("900x700")
            preview.transient(self.app.root)
            preview.minsize(800, 600)

            # Center the window
            preview.update_idletasks()
            screen_width = preview.winfo_screenwidth()
            screen_height = preview.winfo_screenheight()
            x_pos = (screen_width // 2) - (900 // 2)
            y_pos = (screen_height // 2) - (700 // 2)
            preview.geometry(f"900x700+{x_pos}+{y_pos}")

            main_container = ttk.Frame(preview)
            main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Control Panel
            control_frame = ttk.LabelFrame(main_container, text="Capture Controls", padding=10)
            control_frame.pack(fill=tk.X, pady=(0, 10))

            # Method selection with live preview option
            method_row = ttk.Frame(control_frame)
            method_row.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(method_row, text="Capture Method:").pack(side=tk.LEFT)

            self.test_method_var = tk.StringVar(
                value=region.get('capture_method', self.config.get("capture_method", "auto"))
            )
            method_combo = ttk.Combobox(method_row, textvariable=self.test_method_var,
                                    values=[method.value for method in CaptureMethod],
                                    state="readonly", width=20)
            method_combo.pack(side=tk.LEFT, padx=(10, 20))

            # Live preview checkbox
            self.live_preview_var = tk.BooleanVar(value=False)
            live_preview_cb = ttk.Checkbutton(method_row, text="Live Preview",
                                            variable=self.live_preview_var)
            live_preview_cb.pack(side=tk.LEFT, padx=(0, 10))

            # Test button
            test_btn = ttk.Button(method_row, text="Capture & Test", 
                                command=lambda: self._perform_capture_test(region, preview))
            test_btn.pack(side=tk.LEFT)

            # Status indicator
            self.test_status_var = tk.StringVar(value="Ready to test")
            status_label = ttk.Label(control_frame, textvariable=self.test_status_var,
                                foreground="gray", font=("Arial", 9))
            status_label.pack(anchor=tk.W)

            # Results notebook
            results_notebook = ttk.Notebook(main_container)
            results_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # Create tabs
            self.test_tabs = {
                'original': ttk.Frame(results_notebook),
                'processed': ttk.Frame(results_notebook),
                'ocr': ttk.Frame(results_notebook)
            }

            for tab_name, tab_frame in self.test_tabs.items():
                results_notebook.add(tab_frame, text=tab_name.title())

            # Action buttons
            button_frame = ttk.Frame(main_container)
            button_frame.pack(fill=tk.X)

            ttk.Button(button_frame, text="Apply Method to Region", 
                    command=lambda: self._apply_test_method(region),
                    style='Success.TButton').pack(side=tk.LEFT, padx=(0, 10))

            ttk.Button(button_frame, text="Close", 
                    command=preview.destroy).pack(side=tk.RIGHT)

            # Start live preview if enabled
            def toggle_live_preview():
                if self.live_preview_var.get():
                    self._start_live_preview(region, preview)
                else:
                    self._stop_live_preview()

            self.live_preview_var.trace('w', lambda *args: toggle_live_preview())

        except Exception as e:
            messagebox.showerror("Test Failed", f"Error creating test dialog: {e}")

    def _create_enhanced_region_test_dialog(self, region):
        """Create an enhanced test dialog that properly handles window regions"""
        print(f"DEBUG: Testing region: {region['name']}, type: {region.get('type')} 693")
        try:
            preview = tk.Toplevel(self.app.root)
            preview.title(f"OCR Test - {region['name']}")
            preview.geometry("900x700")
            preview.transient(self.app.root)
            preview.minsize(800, 600)

            # Center the window
            preview.update_idletasks()
            screen_width = preview.winfo_screenwidth()
            screen_height = preview.winfo_screenheight()
            x_pos = (screen_width // 2) - (900 // 2)
            y_pos = (screen_height // 2) - (700 // 2)
            preview.geometry(f"900x700+{x_pos}+{y_pos}")

            main_container = ttk.Frame(preview)
            main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Control Panel
            control_frame = ttk.LabelFrame(main_container, text="Capture Controls", padding=10)
            control_frame.pack(fill=tk.X, pady=(0, 10))

            # Method selection
            method_row = ttk.Frame(control_frame)
            method_row.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(method_row, text="Capture Method:").pack(side=tk.LEFT)

            self.test_method_var = tk.StringVar(
                value=region.get('capture_method', self.config.get("capture_method", "auto"))
            )
            method_combo = ttk.Combobox(method_row, textvariable=self.test_method_var,
                                    values=[method.value for method in CaptureMethod],
                                    state="readonly", width=20)
            method_combo.pack(side=tk.LEFT, padx=(10, 20))

            # Test button
            test_btn = ttk.Button(method_row, text="Capture & Test", 
                                command=lambda: self._perform_enhanced_capture_test(region, preview))
            test_btn.pack(side=tk.LEFT)

            # Status indicator
            self.test_status_var = tk.StringVar(value="Ready to test")
            status_label = ttk.Label(control_frame, textvariable=self.test_status_var,
                                foreground="gray", font=("Arial", 9))
            status_label.pack(anchor=tk.W)

            # Region info
            info_text = f"Region: {region['name']} | Type: {region.get('type', 'screen')}"
            if region.get('type') == 'window':
                info_text += f" | Window: {region.get('window_title', 'Unknown')}"
            ttk.Label(control_frame, text=info_text, font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(5, 0))

            # Results notebook
            results_notebook = ttk.Notebook(main_container)
            results_notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            # Create tabs
            self.test_tabs = {
                'original': ttk.Frame(results_notebook),
                'processed': ttk.Frame(results_notebook),
                'ocr': ttk.Frame(results_notebook)
            }

            for tab_name, tab_frame in self.test_tabs.items():
                results_notebook.add(tab_frame, text=tab_name.title())

            # Action buttons
            button_frame = ttk.Frame(main_container)
            button_frame.pack(fill=tk.X)

            ttk.Button(button_frame, text="Apply Method to Region", 
                    command=lambda: self._apply_test_method(region),
                    style='Success.TButton').pack(side=tk.LEFT, padx=(0, 10))

            ttk.Button(button_frame, text="Close", 
                    command=preview.destroy).pack(side=tk.RIGHT)
            print(f"DEBUG: Testing region: {region['name']}, type: {region.get('type')} 770")
            # Auto-test on dialog open for window regions
            if region.get('type') == 'window':
                print(f"DEBUG: Testing region: {region['name']}, type: {region.get('type')} 773")
                preview.after(500, lambda: self._perform_enhanced_capture_test(region, preview))

        except Exception as e:
            messagebox.showerror("Test Failed", f"Error creating test dialog: {e}")

    def _perform_enhanced_capture_test(self, region, parent):
        """Perform capture test that properly handles both screen and window regions with subregions"""
        try:
            self.test_status_var.set("Capturing...")
            parent.update()
    
            # Set capture method
            self.window_capture.set_method(self.test_method_var.get())

            image = None
            capture_success = False

            # Handle window regions
            if region.get('type') == 'window':
                print(f"DEBUG: Capturing window region: {region.get('window_title', 'Unknown')}")
                print(f"DEBUG: Subregion bounds: {region.get('subregion_bounds', 'None')}")
        
                # Try to find the window if hwnd is not available or invalid
                hwnd = region.get('hwnd')
                if not hwnd or not self._is_window_valid(hwnd):
                    print("DEBUG: Finding window dynamically...")
                    hwnd = self.find_best_window_match(region)
                    if hwnd:
                        region['hwnd'] = hwnd
                        print(f"DEBUG: Found window: {hwnd}")
                    else:
                        self.test_status_var.set("❌ Window not found")
                        messagebox.showerror("Window Not Found", 
                                        f"Could not find window for region '{region['name']}'. "
                                        f"The window might be closed or minimized.")
                        return
        
                # Capture the window - WITH SUBREGION SUPPORT USING WINDOW CAPTURE
                if region.get('subregion_bounds'):
                    # Use the new method that captures subregion using window capture
                    subregion_bounds = region['subregion_bounds']
                    print(f"DEBUG: Capturing window subregion: hwnd={hwnd}, subregion={subregion_bounds}")
                    image = self.window_capture.capture_region(
                        hwnd=hwnd, 
                        subregion_bounds=subregion_bounds
                    )

                    if image:
                        capture_success = True
                        print(f"DEBUG: Window subregion capture successful: {image.width}x{image.height}")
                    else:
                        print("DEBUG: Window subregion capture failed")
                        # Fallback to screen capture for subregion
                        print("DEBUG: Falling back to screen capture for subregion")
                        window_x, window_y, window_w, window_h = region['bounds']
                        sub_x, sub_y, sub_w, sub_h = subregion_bounds
                        region_dict = {
                            "left": window_x + sub_x,
                            "top": window_y + sub_y, 
                            "width": sub_w,
                            "height": sub_h
                        }
                        image = self.window_capture.capture_region(region=region_dict)
                        if image:
                            capture_success = True
                            print(f"DEBUG: Screen subregion capture successful: {image.width}x{image.height}")
                else:
                    # Capture entire window
                    print("DEBUG: Capturing entire window (no subregion)")
                    image = self.window_capture.capture_region(hwnd=hwnd)
                    if image:
                        capture_success = True
                        print(f"DEBUG: Full window capture successful: {image.width}x{image.height}")

                if not capture_success:
                    self.test_status_var.set("❌ Window capture failed")
                    messagebox.showerror("Capture Failed", 
                                    "Could not capture window. The window might be minimized, "
                                    "covered, or inaccessible. Try a different capture method.")
                    return
                
            else:
                # Screen region capture (existing code)
                x, y, w, h = region['bounds']
                region_dict = {"left": x, "top": y, "width": w, "height": h}
                print(f"DEBUG: Capturing screen region: {region_dict}")

                image = self.window_capture.capture_region(region=region_dict)

                if image:
                    capture_success = True
                    print(f"DEBUG: Screen capture successful: {image.width}x{image.height}")
                else:
                    self.test_status_var.set("❌ Screen capture failed")
                    messagebox.showerror("Capture Failed", "Could not capture screen region.")
                    return
    
            if capture_success and image:
                # Process image
                processed_image = self.preprocess_image_for_gaming(image, region['name'])
        
                # Perform OCR
                ocr_config = self._get_ocr_config()
                processed_text = pytesseract.image_to_string(processed_image, config=ocr_config)
        
                # Display results with region information including subregion
                self._display_enhanced_test_results(image, processed_image, "", processed_text, region)
                self.test_status_var.set("✅ Test completed successfully")
        
        except Exception as e:
            self.test_status_var.set("❌ Test failed")
            error_msg = f"Error during test: {str(e)}"
            print(f"DEBUG: {error_msg}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Test Error", error_msg)

    def _is_window_valid(self, hwnd):
        """Check if a window handle is valid and the window is visible"""
        try:
            import win32gui
            if not hwnd or not win32gui.IsWindow(hwnd):
                print(f"DEBUG: not hwnd or not win32gui.IsWindow(hwnd){hwnd}")
                return False
        
            # Check if window is visible and not minimized
            if not win32gui.IsWindowVisible(hwnd):
                print(f"DEBUG: not win32gui.IsWindowVisible(hwnd){hwnd}")
                return False
            
            # Check if window is iconic (minimized)
            if win32gui.IsIconic(hwnd):
                print(f"DEBUG: win32gui.IsIconic(hwnd){hwnd}")
                return False
            
            return True
        
        except Exception as e:
            print(f"DEBUG: Window validation failed: {e}")
            return False

    def _display_enhanced_test_results(self, original_img, processed_img, original_text, processed_text, region):
        """Display test results with region information"""
        # Display original image
        self._display_image_tab(self.test_tabs['original'], original_img, 
                            f"Original Image - {region['name']}")
    
        # Display processed image  
        self._display_image_tab(self.test_tabs['processed'], processed_img, 
                            f"Processed Image - {region['name']}")
    
        # Display OCR results with region context
        self._display_enhanced_ocr_tab(self.test_tabs['ocr'], original_text, processed_text, region)

    def _display_enhanced_ocr_tab(self, tab, original_text, processed_text, region):
        """Display OCR results with region context including subregion info"""
        # Clear existing content
        for widget in tab.winfo_children():
            widget.destroy()
    
        # Create notebook for OCR results
        ocr_notebook = ttk.Notebook(tab)
        ocr_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Region info frame
        info_frame = ttk.Frame(ocr_notebook)
        ocr_notebook.add(info_frame, text="Region Info")

        # Display region information with subregion details
        info_text = f"Region: {region['name']}\n"
        info_text += f"Type: {region.get('type', 'screen')}\n"
    
        if region.get('type') == 'window':
            info_text += f"Window: {region.get('window_title', 'Unknown')}\n"
            info_text += f"Process: {region.get('process_name', 'Unknown')}\n"
            info_text += f"Capture Method: {region.get('capture_method', 'auto')}\n"
        
            # ADD SUBREGION INFO
            if region.get('subregion_bounds'):
                sub_x, sub_y, sub_w, sub_h = region['subregion_bounds']
                info_text += f"Subregion: {sub_w}x{sub_h} at ({sub_x},{sub_y})\n"
            else:
                info_text += "Subregion: Entire window\n"
            
            info_text += f"Window Bounds: {region['bounds']}\n"
        else:
            info_text += f"Bounds: {region['bounds']}\n"
    
        info_text += f"Patterns: {', '.join(region['patterns'])}\n"
        info_text += f"Cooldown: {region.get('cooldown', 300)}s\n"
        info_text += f"Color Profile: {region.get('color_profile', 'default')}"
    
        info_text_widget = tk.Text(info_frame, wrap=tk.WORD, width=80, height=8)
        info_scrollbar = ttk.Scrollbar(info_frame, orient=tk.VERTICAL, command=info_text_widget.yview)
        info_text_widget.configure(yscrollcommand=info_scrollbar.set)
    
        info_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        info_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        info_text_widget.insert(1.0, info_text)
        info_text_widget.config(state=tk.DISABLED)
    
        # Original OCR tab
        orig_ocr_tab = ttk.Frame(ocr_notebook)
        ocr_notebook.add(orig_ocr_tab, text="Original OCR")
    
        orig_text_widget = tk.Text(orig_ocr_tab, wrap=tk.WORD, width=80, height=15)
        orig_scrollbar = ttk.Scrollbar(orig_ocr_tab, orient=tk.VERTICAL, command=orig_text_widget.yview)
        orig_text_widget.configure(yscrollcommand=orig_scrollbar.set)
    
        orig_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        orig_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        orig_text_widget.insert(1.0, original_text if original_text.strip() else "No text detected")
        orig_text_widget.config(state=tk.DISABLED)
    
        # Processed OCR tab
        proc_ocr_tab = ttk.Frame(ocr_notebook)
        ocr_notebook.add(proc_ocr_tab, text="Processed OCR")
    
        proc_text_widget = tk.Text(proc_ocr_tab, wrap=tk.WORD, width=80, height=15)
        proc_scrollbar = ttk.Scrollbar(proc_ocr_tab, orient=tk.VERTICAL, command=proc_text_widget.yview)
        proc_text_widget.configure(yscrollcommand=proc_scrollbar.set)
    
        proc_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        proc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
        proc_text_widget.insert(1.0, processed_text if processed_text.strip() else "No text detected")
        proc_text_widget.config(state=tk.DISABLED)

    def _start_live_preview(self, region, parent):
        """Start live preview of the region"""
        self.live_preview_active = True
        self._update_live_preview(region, parent)

    def _stop_live_preview(self):
        """Stop live preview"""
        self.live_preview_active = False

    def _update_live_preview(self, region, parent):
        """Update live preview"""
        if not self.live_preview_active:
            return
        
        try:
            # Capture with current method
            self.window_capture.set_method(self.test_method_var.get())
            x, y, w, h = region['bounds']
            region_dict = {"left": x, "top": y, "width": w, "height": h}
            image = self.window_capture.capture_region(region=region_dict)
        
            if image:
                # Update original tab
                self._display_image_tab(self.test_tabs['original'], image, "Live Preview - Original")
            
                # Update processed tab
                processed_image = self.preprocess_image_for_gaming(image, region['name'])
                self._display_image_tab(self.test_tabs['processed'], processed_image, "Live Preview - Processed")
            
                self.test_status_var.set("Live preview active")
            else:
                self.test_status_var.set("Live preview failed - cannot capture")
            
        except Exception as e:
            self.test_status_var.set(f"Live preview error: {str(e)}")
    
        # Schedule next update
        if self.live_preview_active:
            parent.after(1000, lambda: self._update_live_preview(region, parent))

    def _perform_capture_test(self):
        """Perform a single capture test that handles both screen and window regions"""
        try:
            self.status_var.set("Capturing...")
            self.dialog.update()
        
            # Set capture method
            self.plugin.window_capture.set_method(self.method_var.get())
        
            # Capture based on region type
            image = None
            if self.region.get('type') == 'window' and self.region.get('hwnd'):
                # Window region capture
                print(f"DEBUG: Capturing window region with hwnd: {self.region['hwnd']}")
                image = self.plugin.window_capture.capture_region(hwnd=self.region['hwnd'])
            
                # If window capture fails, try to find the window again
                if image is None:
                    print("DEBUG: Window capture failed, trying to find window...")
                    hwnd = self.plugin.find_best_window_match(self.region)
                    if hwnd:
                        self.region['hwnd'] = hwnd
                        image = self.plugin.window_capture.capture_region(hwnd=hwnd)
            else:
                # Screen region capture
                x, y, w, h = self.region['bounds']
                region_dict = {"left": x, "top": y, "width": w, "height": h}
                print(f"DEBUG: Capturing screen region: {region_dict}")
                image = self.plugin.window_capture.capture_region(region=region_dict)
        
            if image is None:
                self.status_var.set("❌ Capture failed")
                messagebox.showerror("Capture Failed", "Could not capture region image.")
                return
        
            # Process image
            processed_image = self.plugin.preprocess_image_for_gaming(image, self.region['name'])
        
            # Perform OCR
            import pytesseract
            ocr_config = self.plugin._get_ocr_config()
            processed_text = pytesseract.image_to_string(processed_image, config=ocr_config)
        
            # Display results
            self._display_test_results(image, processed_image, original_text="", processed_text=processed_text)
            self.status_var.set("✅ Test completed successfully")
        
        except Exception as e:
            self.status_var.set("❌ Test failed")
            messagebox.showerror("Test Error", f"Error during test: {str(e)}")
            import traceback
            traceback.print_exc()

    def _display_test_results(self, original_img, processed_img, original_text, processed_text):
        """Display test results in the preview window"""
        # Display original image
        self._display_image_tab(self.test_tabs['original'], original_img, "Original Image")
        
        # Display processed image  
        self._display_image_tab(self.test_tabs['processed'], processed_img, "Processed Image")
        
        # Display OCR results
        self._display_ocr_tab(self.test_tabs['ocr'], original_text, processed_text)

    def _display_image_tab(self, tab, image, title):
        """Display image in a tab with proper horizontal and vertical scrolling"""
        # Clear existing content
        for widget in tab.winfo_children():
            widget.destroy()
    
        # Create main container
        main_container = ttk.Frame(tab)
        main_container.pack(fill=tk.BOTH, expand=True)
    
        # Create a frame for the image and info
        content_frame = ttk.Frame(main_container)
        content_frame.pack(fill=tk.BOTH, expand=True)
    
        # Create canvas with both scrollbars
        canvas = tk.Canvas(content_frame, highlightthickness=0)
    
        # Create scrollbars
        v_scrollbar = ttk.Scrollbar(content_frame, orient=tk.VERTICAL, command=canvas.yview)
        h_scrollbar = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=canvas.xview)
    
        # Configure canvas
        canvas.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
    
        # Create frame inside canvas for the image
        image_frame = ttk.Frame(canvas)
    
        def configure_scrollregion(event=None):
            # Update the scrollregion to encompass the inner frame
            bbox = canvas.bbox("all")
            if bbox:
                canvas.configure(scrollregion=bbox)
    
        image_frame.bind("<Configure>", configure_scrollregion)
    
        # Add image frame to canvas
        canvas_window = canvas.create_window((0, 0), window=image_frame, anchor="nw")
    
        # Function to resize canvas window when canvas is resized
        def on_canvas_configure(event):
            # Set the canvas window width to the canvas width
            #canvas.itemconfig(canvas_window, width=event.width) Commented to make the scroll work.
            configure_scrollregion()
    
        canvas.bind("<Configure>", on_canvas_configure)
    
        # Pack canvas and scrollbars with proper grid layout
        canvas.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
    
        # Configure grid weights for proper expansion
        content_frame.grid_rowconfigure(0, weight=1)
        content_frame.grid_columnconfigure(0, weight=1)
    
        # Display image
        photo = ImageTk.PhotoImage(image)
        label = ttk.Label(image_frame, image=photo)
        label.image = photo  # Keep a reference
        label.pack(padx=10, pady=10)
    
        # Image info
        info_text = f"{title}: {image.width} x {image.height} pixels"
        ttk.Label(image_frame, text=info_text, font=("Arial", 9, "bold")).pack(pady=(0, 10))
    
        # Instructions for scrolling
        if image.width > 600 or image.height > 400:
            scroll_info = "Use scrollbars to navigate the image"
            ttk.Label(image_frame, text=scroll_info, font=("Arial", 8), foreground="gray").pack(pady=(0, 5))
    
        # Force initial scrollregion configuration
        tab.update_idletasks()
        configure_scrollregion()

    def _display_ocr_tab(self, tab, original_text, processed_text):
        """Display OCR results in tab"""
        # Clear existing content
        for widget in tab.winfo_children():
            widget.destroy()
            
        # Create notebook for OCR results
        ocr_notebook = ttk.Notebook(tab)
        ocr_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Original OCR tab
        orig_ocr_tab = ttk.Frame(ocr_notebook)
        ocr_notebook.add(orig_ocr_tab, text="Original OCR")
        
        orig_text_widget = tk.Text(orig_ocr_tab, wrap=tk.WORD, width=80, height=15)
        orig_scrollbar = ttk.Scrollbar(orig_ocr_tab, orient=tk.VERTICAL, command=orig_text_widget.yview)
        orig_text_widget.configure(yscrollcommand=orig_scrollbar.set)
        
        orig_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        orig_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        orig_text_widget.insert(1.0, original_text if original_text.strip() else "No text detected")
        orig_text_widget.config(state=tk.DISABLED)
        
        # Processed OCR tab
        proc_ocr_tab = ttk.Frame(ocr_notebook)
        ocr_notebook.add(proc_ocr_tab, text="Processed OCR")
        
        proc_text_widget = tk.Text(proc_ocr_tab, wrap=tk.WORD, width=80, height=15)
        proc_scrollbar = ttk.Scrollbar(proc_ocr_tab, orient=tk.VERTICAL, command=proc_text_widget.yview)
        proc_text_widget.configure(yscrollcommand=proc_scrollbar.set)
        
        proc_text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        proc_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        proc_text_widget.insert(1.0, processed_text if processed_text.strip() else "No text detected")
        proc_text_widget.config(state=tk.DISABLED)

    def _apply_test_method(self, region):
        """Apply the tested capture method to the region"""
        new_method = self.test_method_var.get()
        region['capture_method'] = new_method
        self._refresh_regions_tree()
        messagebox.showinfo("Success", f"Capture method '{new_method}' applied to region '{region['name']}'")

    def _enhanced_pattern_matching(self, region, text):
        """Enhanced pattern matching that groups detections by region"""
        clean_text = text.lower()
        detected_patterns = []
    
        print(f"DEBUG: Checking region '{region['name']}' - Text: {text.strip()}")
        
        for pattern in region['patterns']:
            pattern_lower = pattern.lower()
            print(f"DEBUG: Looking for pattern '{pattern}' in text")

            # Exact match
            if pattern_lower in clean_text:
                detected_patterns.append(pattern)
                print(f"DEBUG: Exact match found for '{pattern}'")
                continue

            # Fuzzy matching for game text variations
            if self.config.get("enable_fuzzy_matching", False):
                if self._check_fuzzy_match(pattern, clean_text):
                    print(f"DEBUG: Fuzzy match found for '{pattern}'")
                    detected_patterns.append(pattern)

        # Send one alert for all patterns detected in this region
        if detected_patterns:
            print(f"DEBUG: Patterns detected: {detected_patterns}")
            self._trigger_region_alert(region, detected_patterns, text)
        else:
            print(f"DEBUG: No patterns detected in region '{region['name']}'")

        return detected_patterns

    def _trigger_region_alert(self, region, patterns, text):
        """Handle region detection with consolidated alert"""
        current_time = time.time()

        # Check cooldown for the region (not individual patterns)
        last_region_alert = region.get('last_region_alert', 0)
        cooldown = region.get('cooldown', 300)

        print(f"DEBUG: Cooldown check - Last: {last_region_alert}, Current: {current_time}, Diff: {current_time - last_region_alert}, Cooldown: {cooldown}")

        if current_time - last_region_alert > cooldown:
            region['last_region_alert'] = current_time

            # Update last_seen for individual patterns (for tracking)
            for pattern in patterns:
                region['last_seen'][pattern] = current_time

            # Create consolidated message
            if len(patterns) == 1:
                message = f"OCR detected '{patterns[0]}' in {region['name']}"
            else:
                patterns_str = ", ".join(patterns)
                message = f"OCR detected {len(patterns)} patterns in {region['name']}: {patterns_str}"

            # Enhanced logging
            log_message = (
                f"Region alert for {region['name']}:\n"
                f"Patterns: {', '.join(patterns)}\n"
                f"Detected text: {text[:100]}{'...' if len(text) > 100 else ''}\n"
                f"Region bounds: {region['bounds']}"
            )
            print(f"OCR Region Alert: {log_message}")

            self._on_region_detected(region['name'], patterns, text, message)

    def _on_region_detected(self, region_name, patterns, detected_text, message):
        """Handle region detection with custom TTS messages"""
        print(f"OCR Alert: {message}")

        # Safe notification handling
        try:
            if hasattr(self.app, 'action_handler'):
                self.app.action_handler.show_notification(message)

                # TTS with custom messages
                if self.config.get("tts_alerts", False) and hasattr(self.app.action_handler, 'speak_text'):
                    # Find the region to get TTS messages
                    region = next((r for r in self.regions if r['name'] == region_name), None)

                    if region and patterns:
                        # Use custom TTS message if available, otherwise use pattern
                        tts_messages = []
                        for pattern in patterns:
                            custom_tts = region.get('tts_messages', {}).get(pattern)
                            if custom_tts:
                                tts_messages.append(custom_tts)
                            else:
                                tts_messages.append(pattern)

                        if len(tts_messages) == 1:
                            tts_text = tts_messages[0]
                        else:
                            tts_text = f"Multiple patterns detected: {', '.join(tts_messages)}"

                        self.app.action_handler.speak_text(tts_text, "")

        except Exception as e:
            print(f"Notification failed: {e}")

    def _check_fuzzy_match(self, pattern, clean_text):
        """Check for a single fuzzy match and return True if found"""
        try:
            from fuzzywuzzy import fuzz

            lines = clean_text.split('\n')
            for line in lines:
                line_clean = line.strip()
                if len(line_clean) < 3:
                    continue

                similarity = fuzz.partial_ratio(pattern.lower(), line_clean)
                threshold = self.config.get("fuzzy_threshold", 85)

                if similarity >= threshold:
                    return True  # Pattern found
            return False  # Pattern not found

        except ImportError:
            # fuzzywuzzy not installed, skip fuzzy matching
            if not hasattr(self, '_fuzzy_warning_shown'):
                print("FuzzyWuzzy not installed. Install with: pip install fuzzywuzzy python-Levenshtein")
                self._fuzzy_warning_shown = True
            return False
           
    def _trigger_pattern(self, region, pattern, text, match_type):
        """Handle pattern detection with enhanced logging"""
        current_time = time.time()
        last_seen = region['last_seen'].get(pattern, 0)
        cooldown = region.get('cooldown', 300)
        print(f"Cooldown: {cooldown}")
        if current_time - last_seen > cooldown:
            region['last_seen'][pattern] = current_time
            
            # Enhanced logging with more context
            log_message = (
                f"OCR {match_type} match: '{pattern}' in {region['name']}\n"
                f"Detected text: {text[:100]}{'...' if len(text) > 100 else ''}\n"
                f"Region bounds: {region['bounds']}\n"
                f"Profile: {self.config.get('current_profile', 'default')}\n"
                f"Cooldown: {cooldown}"
            )
            print(f"OCR Alert: {log_message}")
            print(f"Cooldown: {cooldown}")
            self._on_pattern_detected(region['name'], pattern, text)

    def _get_ocr_config(self):
        """Enhanced OCR configuration with game profiles"""
        profile = self.config.get("current_profile", "default")
        profile_settings = self.config["game_profiles"].get(profile, {})
        
        config_str = ""
        
        # Language
        lang = self.config.get("language", "eng")
        if lang and lang != "eng":
            config_str += f"-l {lang} "
            
        # Profile-specific settings
        psm = profile_settings.get("page_segmentation_mode", 
                                  self.config.get("page_segmentation_mode", 6))
        oem = profile_settings.get("ocr_engine_mode", 
                                  self.config.get("ocr_engine_mode", 3))
        config_str += f"--psm {psm} --oem {oem}"
        
        return config_str.strip()
            
    def _on_pattern_detected(self, region_name, pattern, detected_text):
        """Handle detected pattern with safe notification"""
        message = f"OCR detected '{pattern}' in {region_name}"
        print(f"OCR Alert: {message}")
    
        # Safe notification handling
        try:
            # Check if the action_handler exists and has the method
            if hasattr(self.app, 'action_handler'):
                self.app.action_handler.show_notification(message)

                # Optional: Speak alert if TTS is enabled
                if self.config.get("tts_alerts", False):
                    # Check if speak_text method exists before calling it
                    if hasattr(self.app.action_handler, 'speak_text'):
                        self.app.action_handler.speak_text(f"Alert: {pattern} detected", "")
            else:
                print("Notification system not available: action_handler not found")
            
        except Exception as e:
            print(f"DeBUG Notification failed: {e}")
            import traceback
            traceback.print_exc()

    def get_settings_widget(self, parent):
        """Enhanced settings widget with capture methods tab"""
        def create_widget(master):    
            main_frame = ttk.Frame(master)
            main_frame.pack(fill=tk.BOTH, expand=True)

            main_frame.master.minsize(500, 500)

            notebook = ttk.Notebook(main_frame)
            notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

            # Create tabs - ADD CAPTURE METHODS TAB
            tesseract_tab = self.settings_tabs.create_tesseract_tab(notebook)
            regions_tab = self.settings_tabs.create_regions_tab(notebook)
            ocr_tab = self.settings_tabs.create_ocr_tab(notebook) 
            gaming_tab = self.settings_tabs.create_gaming_tab(notebook)
            color_tab = self.settings_tabs.create_colors_tab(notebook)
            capture_tab = self.settings_tabs.create_capture_tab(notebook)

            # Add to notebook
            notebook.add(tesseract_tab, text="Tesseract")
            notebook.add(regions_tab, text="Regions")
            notebook.add(ocr_tab, text="OCR Settings")
            notebook.add(gaming_tab, text="Gaming")
            notebook.add(color_tab, text="Colors")
            notebook.add(capture_tab, text="Capture")

            return main_frame

        return create_widget

    def _create_scrollable_frame(self, parent):
        """Create a properly scrollable frame that works with notebook"""
        # Create frame for the tab
        tab_frame = ttk.Frame(parent)

        # Create canvas and scrollbar
        canvas = tk.Canvas(tab_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab_frame, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure scrolling
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Pack elements
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Update scrollregion when frame changes
        def on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", on_frame_configure)

        return scrollable_frame  # Return the inner frame for content

    def _select_window_region(self):
        """Select a window for capture"""
        self.region_selector.select_window()

    def _refresh_region_methods_tree(self):
        """Refresh the region methods treeview with existence checks"""
        if not hasattr(self, 'region_methods_tree') or self.region_methods_tree is None:
            return

        try:
            # Check if widget still exists
            if not self.region_methods_tree.winfo_exists():
                return

            # Clear existing items
            for item in self.region_methods_tree.get_children():
                self.region_methods_tree.delete(item)

            # Populate with current regions
            for region in self.regions:
                # Handle missing bounds gracefully
                if 'bounds' in region:
                    bounds_str = f"{region['bounds'][0]},{region['bounds'][1]},{region['bounds'][2]},{region['bounds'][3]}"
                else:
                    bounds_str = "No bounds"

                current_method = region.get('capture_method', self.config.get("capture_method", "auto"))

                self.region_methods_tree.insert('', tk.END, values=(
                    region['name'],
                    bounds_str,
                    current_method
                ), tags=(region['name'],))

        except (tk.TclError, KeyError, IndexError) as e:
            # Widget was destroyed or data issue, just ignore
            print(f"Region methods tree refresh failed: {e}")
            return

    def _apply_region_method(self):
        """Apply selected method to chosen region"""
        if not hasattr(self, 'region_methods_tree') or not self.region_methods_tree:
            return

        selection = self.region_methods_tree.selection()
        if selection:
            try:
                region_name = self.region_methods_tree.item(selection[0], 'tags')[0]
                new_method = self.region_method_var.get()

                for region in self.regions:
                    if region['name'] == region_name:
                        region['capture_method'] = new_method
                        break

                self.ensure_save()
                self._refresh_region_methods_tree()
                self._refresh_regions_tree()
                self.app.messages(2, 9, f"Applied '{new_method}' to region '{region_name}'")
            except Exception as e:
                print(f"Error applying region method: {e}")
        else:
            messagebox.showwarning("No Selection", "Please select a region first")

    def _reset_region_method(self):
        """Reset region method to default"""
        if not hasattr(self, 'region_methods_tree') or not self.region_methods_tree:
            return

        selection = self.region_methods_tree.selection()
        if selection:
            try:
                region_name = self.region_methods_tree.item(selection[0], 'tags')[0]

                for region in self.regions:
                    if region['name'] == region_name:
                        if 'capture_method' in region:
                            del region['capture_method']
                        break

                self.ensure_save()
                self._refresh_region_methods_tree()
                self._refresh_regions_tree()
                self.app.messages(2, 9, f"Reset capture method for region '{region_name}'")
            except Exception as e:
                print(f"Error resetting region method: {e}")
        else:
            messagebox.showwarning("No Selection", "Please select a region first")

    def _apply_capture_settings(self):
        """Apply capture settings"""
        try:
            self.config["capture_method"] = self.capture_method_var.get()
            self.ensure_save()
            self.app.messages(2, 9, "Capture settings applied")
        except Exception as e:
            self.app.messages(2, 3, f"Error applying capture settings: {e}")

    def _ensure_ui_visibility(self):
        """Ensure all UI elements are properly visible"""
        # Refresh the preview after UI is drawn
        if hasattr(self, 'preview_canvas'):
            self.app.root.after(500, self._update_preview)
    
        # Ensure treeview columns are properly sized
        if hasattr(self, 'regions_tree'):
            self.app.root.after(500, self._resize_treeview_columns)

    def _resize_treeview_columns(self):
        """Auto-resize treeview columns to fit content"""
        for col in self.regions_tree['columns']:
            self.regions_tree.column(col, width=tk.font.Font().measure(col.title()) + 20)

    def _refresh_color_profiles_list(self):
        """Refresh the color profiles listbox"""
        if hasattr(self, 'profiles_listbox'):
            self.profiles_listbox.delete(0, tk.END)
            for profile_name in self.config["color_filters"].keys():
                colors_count = len(self.config["color_filters"][profile_name]["target_colors"])
                display_text = f"{profile_name} ({colors_count} colors)"
                self.profiles_listbox.insert(tk.END, display_text)
    
    def _delete_color_profile(self):
        """Delete selected color profile"""
        selection = self.profiles_listbox.curselection()
        if selection:
            profile_index = selection[0]
            profile_name = list(self.config["color_filters"].keys())[profile_index]
            
            # Don't allow deleting built-in profiles
            if profile_name in ["default", "dark_text"]:
                messagebox.showwarning("Cannot Delete", "Cannot delete built-in color profiles")
                return
                
            if messagebox.askyesno("Confirm Delete", f"Delete color profile '{profile_name}'?"):
                del self.config["color_filters"][profile_name]
                self._refresh_color_profiles_list()
                
                # Update regions using this profile
                for region in self.regions:
                    if region.get('color_profile') == profile_name:
                        region['color_profile'] = "default"
                
                self._refresh_regions_tree()
                self.save_configuration()
                self.app.messages(2, 9, f"Color profile '{profile_name}' deleted")

    def _apply_color_settings(self):
        """Apply color filtering settings"""
        try:
            self.config["enable_color_filtering"] = self.color_filter_var.get()
            self.config["current_color_profile"] = self.color_profile_var.get()
            self.config["color_tolerance"] = int(self.tolerance_var.get())
            
            self.app.messages(2, 9, "Color filtering settings applied")
            self.save_configuration()
            
        except ValueError as e:
            self.app.messages(2, 3, f"Invalid setting value: {e}")

    def _open_color_picker_for_region(self):
        """Open color picker for the selected region"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            region = next((r for r in self.regions if r['name'] == region_name), None)
            
            if region:
                self.interactive_color_picker(region)
                # Refresh the regions tree to show updated color profile
                self._refresh_regions_tree()
            else:
                messagebox.showwarning("No Region", "Please select a valid region first")
        else:
            messagebox.showwarning("No Selection", "Please select a region first")

    def _update_performance_stats(self):
        """Update performance statistics display"""
        if self.performance_stats['total_checks'] > 0:
            success_rate = (self.performance_stats['successful_ocr'] / self.performance_stats['total_checks']) * 100
            stats_text = (f"Total Checks: {self.performance_stats['total_checks']}\n"
                        f"Success Rate: {success_rate:.1f}%\n"
                        f"Avg Check Time: {self.performance_stats['last_check_time']:.3f}s")
        else:
            stats_text = "No performance data yet\nRun the monitor to collect stats"
    
        if hasattr(self, 'stats_var') and self.stats_var:
            self.stats_var.set(stats_text)

    def _apply_gaming_settings(self):
        """Apply gaming-specific settings"""
        try:
            self.config["current_profile"] = self.profile_var.get()
            self.config["enable_preprocessing"] = self.preprocess_var.get()
            self.config["enable_fuzzy_matching"] = self.fuzzy_var.get()
            self.config["fuzzy_threshold"] = int(self.fuzzy_threshold_var.get())
            self.config["performance_monitoring"] = self.performance_var.get()
            
            self._update_performance_stats()
            self.app.messages(2, 9, "Gaming settings applied")
            self.save_configuration()

        except ValueError as e:
            self.app.messages(2, 3, f"Invalid setting value: {e}")

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
        from ocr_modules.ui.ui_components import RegionDialog
    
        dialog = RegionDialog(
            self.app.root,
            title="Add Screen Region",
            default_name=f"Region_{len(self.regions) + 1}",
            default_coords=(x, y, width, height)
        )
    
        result = dialog.show()
    
        if result:
            self.add_region(
                name=result['name'],
                x=x, y=y, width=width, height=height,
                patterns=result['patterns'],
                cooldown=result['cooldown'],
                color_profile=result['color_profile'],
                tts_messages=result['tts_messages'],
                capture_method=result.get('capture_method', 'auto')
            )
            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Region '{result['name']}' added")

    def _add_manual_region_dialog(self):
        """Dialog for manual region entry using the enhanced dialog"""
        from ocr_modules.ui.ui_components import RegionDialog

        dialog = RegionDialog(
            self.app.root,
            title="Add Manual Region", 
            default_name=f"Region_{len(self.regions) + 1}",
            default_coords=(100, 100, 400, 200)  # Default coordinates for manual entry
        )

        result = dialog.show()

        if result:
            x, y, w, h = result['bounds']
            self.add_region(
                name=result['name'],
                x=x, y=y, width=w, height=h,
                patterns=result['patterns'],
                cooldown=result['cooldown'],
                color_profile=result['color_profile'],
                tts_messages=result['tts_messages'],
                capture_method=result['capture_method']
            )
            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Region '{result['name']}' added")

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
                        
                        # For window regions with subregions, use the subregion bounds for display
                        if region.get('type') == 'window' and region.get('subregion_bounds'):
                            # Use subregion bounds instead of window bounds
                            sub_x, sub_y, sub_w, sub_h = region['subregion_bounds']
                            window_x, window_y, window_w, window_h = region['bounds']
        
                                    # Calculate absolute coordinates of subregion
                            abs_x = window_x + sub_x
                            abs_y = window_y + sub_y
                            x, y, width, height = abs_x, abs_y, sub_w, sub_h
        
                            # Add subregion indicator to the region name
                            region_display_name = f"{region['name']} (Subregion)"
                        else:
                            # Use regular bounds
                            x, y, width, height = region['bounds']
                            region_display_name = region['name']
                        
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

    def _refresh_regions_tree(self):
        """Refresh the regions treeview with context menu support"""
        if not hasattr(self, 'regions_tree') or self.regions_tree is None:
            return

        try:
            if not self.regions_tree.winfo_exists():
                return

            # Clear existing items
            for item in self.regions_tree.get_children():
                self.regions_tree.delete(item)

            # Populate with regions
            for region in self.regions:
                if region.get('hwnd') and not region.get('type'):
                    region['type'] = 'window'
                    print(f"DEBUG: Auto-set type='window' for region: {region['name']}")
                # Format bounds based on region type
                if region.get('type') == 'window':
                    bounds_str = "Dynamic (Window)"
                    region_type = f"Window: {region.get('window_title', 'Unknown')}"
                    # Add subregion info if exists
                    if region.get('subregion_bounds'):
                        sub_x, sub_y, sub_w, sub_h = region['subregion_bounds']
                        bounds_str = f"Subregion: {sub_w}x{sub_h} at ({sub_x},{sub_y})"
                        region_type += " + Subregion"
                    # Try to get current window position
                    current_hwnd = self.find_best_window_match(region)
                    if current_hwnd:
                        try:
                            left, top, right, bottom = win32gui.GetWindowRect(current_hwnd)
                            bounds_str = f"{left},{top},{right-left},{bottom-top}"
                        except:
                            bounds_str = "Window found"
                    else:
                        bounds_str = "Window not found"
                else:
                    bounds_str = f"{region['bounds'][0]},{region['bounds'][1]},{region['bounds'][2]},{region['bounds'][3]}"
                    region_type = "Screen Region"

                # Format patterns for display
                patterns_str = ", ".join(region['patterns'][:2])
                if len(region['patterns']) > 2:
                    patterns_str += f" (+{len(region['patterns']) - 2} more)"

                # TTS info
                tts_count = len(region.get('tts_messages', {}))
                tts_info = f"{tts_count} custom" if tts_count > 0 else "Default"

                # Capture method
                capture_method = region.get('capture_method', self.config.get("capture_method", "auto"))
            
                # Monitor info
                monitor_info = self._get_monitor_info(region.get('bounds', (0, 0, 100, 100)))

                # Insert with status color coding
                tags = (region['name'],)
                if not region.get('enabled', True):
                    tags += ('disabled',)
                elif region.get('type') == 'window' and not self.find_best_window_match(region):
                    tags += ('window_not_found',)

                self.regions_tree.insert('', tk.END, values=(
                    region['name'],
                    bounds_str,
                    patterns_str,
                    "Yes" if region.get('enabled', True) else "No",
                    monitor_info,
                    tts_info,
                    capture_method,
                    region_type
                ), tags=tags)

            # Configure tag styles
            self.regions_tree.tag_configure('disabled', foreground='gray')
            self.regions_tree.tag_configure('window_not_found', foreground='orange')

            # Add context menu
            self._setup_treeview_context_menu()

            # Refresh related trees
            if hasattr(self, 'region_methods_tree'):
                self._refresh_region_methods_tree()

            # Update preview
            if hasattr(self, 'preview_canvas'):
                self.app.root.after(100, self._update_preview)

        except tk.TclError as e:
            print(f"Regions tree no longer exists: {e}")

    def _setup_treeview_context_menu(self):
        """Setup right-click context menu for regions treeview"""
        if not hasattr(self, 'regions_context_menu'):
            self.regions_context_menu = tk.Menu(self.regions_tree, tearoff=0)

            self.regions_context_menu.add_command(
                label="Test Region", 
                command=self._test_region
            )
            self.regions_context_menu.add_command(
                label="Edit Region", 
                command=self._edit_region  # This should call the fixed _edit_region method
            )
            self.regions_context_menu.add_command(
                label="Toggle Enabled", 
                command=self._toggle_region
            )
            self.regions_context_menu.add_separator()
            self.regions_context_menu.add_command(
                label="Configure TTS", 
                command=self._configure_region_tts
            )
            self.regions_context_menu.add_command(
                label="Color Picker", 
                command=self._open_color_picker_for_region
            )
            self.regions_context_menu.add_separator()
            self.regions_context_menu.add_command(
                label="Remove Region", 
                command=self._remove_region
            )

        def show_context_menu(event):
            item = self.regions_tree.identify_row(event.y)
            if item:
                self.regions_tree.selection_set(item)
                self.regions_context_menu.post(event.x_root, event.y_root)
    
        self.regions_tree.bind("<Button-3>", show_context_menu)

    def _configure_region_tts(self):
        """Configure TTS messages for selected region"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            region = next((r for r in self.regions if r['name'] == region_name), None)
        
            if region:
                dialog = PatternTTSDialog(
                    self.app.root, 
                    region['patterns'], 
                    region.get('tts_messages', {})
                )
                result = dialog.show()
            
                if result is not None:
                    region['tts_messages'] = result
                    self.ensure_save()
                    self._refresh_regions_tree()
                    self.app.messages(2, 9, f"TTS messages updated for '{region_name}'")

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
        except Exception as e:
            self.tesseract_status_var.set(f"✗ Tesseract error: {e}")

    def _add_region_dialog(self):
        """Add region using simplified embedded patterns dialog"""
        from ocr_modules.ui.ui_components import RegionDialog
    
        dialog = RegionDialog(
            self.app.root,
            title="Add Screen Region",
            default_name=f"Region_{len(self.regions) + 1}",
            default_coords=(100, 100, 400, 200)
        )
    
        result = dialog.show()
    
        if result:
            self.add_region(
                name=result['name'],
                x=result['bounds'][0], y=result['bounds'][1],
                width=result['bounds'][2], height=result['bounds'][3],
                patterns=result['patterns'],
                cooldown=result['cooldown'],
                color_profile=result['color_profile'],
                tts_messages=result['tts_messages'],
                capture_method=result['capture_method']
            )
            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Region '{result['name']}' added")

    def _add_window_region_dialog(self):
        """Add window region using the new unified dialog"""
        from ocr_modules.ui.ui_components import WindowRegionDialog
    
        dialog = WindowRegionDialog(
            self.app.root,
            title="Add Window Region",
            default_name=f"Window_{len(self.regions) + 1}"
        )

        result = dialog.show()
    
        if result:
            # Use the existing add_window_region method but with the new data structure
            region = self.add_window_region(
                name=result['name'],
                hwnd=result['hwnd'],
                window_title=result['window_title'],
                capture_method=result['capture_method'],
                patterns=result['patterns'],
                cooldown=result['cooldown'],
                subregion_bounds=result.get('subregion_bounds')  # Make sure this is included
            )
            # Update additional fields that might be in the result
            if 'color_profile' in result:
                region['color_profile'] = result['color_profile']
            if 'tts_messages' in result:
                region['tts_messages'] = result['tts_messages']
            if 'process_name' in result:
                region['process_name'] = result['process_name']

            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Window region '{result['name']}' added")

    def _edit_window_region(self, region):
        """Edit window region using the new unified dialog"""
        print(f"DEBUG: Editing window region '{region['name']}'")
        print(f"DEBUG: Region data: {region}")
        print(f"DEBUG: Subregion bounds in region: {region.get('subregion_bounds')}")
        from ocr_modules.ui.ui_components import WindowRegionDialog
    
        dialog = WindowRegionDialog(
            self.app.root,
            title=f"Edit Window Region - {region['name']}",
            default_name=region['name'],
            existing_region=region  # Make sure this is passed correctly
        )
    
        result = dialog.show()
    
        if result:
            # Update the region with ALL new values including subregion
            region.update({
                'name': result['name'],
                'window_title': result['window_title'],
                'process_name': result.get('process_name', region.get('process_name', '')),
                'patterns': result['patterns'],
                'cooldown': result['cooldown'],
                'color_profile': result.get('color_profile', 'default'),
                'tts_messages': result.get('tts_messages', {}),
                'capture_method': result['capture_method'],
                'subregion_bounds': result.get('subregion_bounds')  # CRITICAL: Update subregion
            })
            self.ensure_save()
            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Window region '{result['name']}' updated")

    def _edit_region(self):
        """Edit selected region - FIXED to handle window regions properly"""
        selection = self.regions_tree.selection()
        if selection:
            region_name = self.regions_tree.item(selection[0], 'tags')[0]
            region = next((r for r in self.regions if r['name'] == region_name), None)

            if region:
                # Check if this is a window region and call the appropriate editor
                if region.get('type') == 'window':
                    print(f"DEBUG: Editing WINDOW region: {region['name']}")
                    self._edit_window_region(region)
                else:
                    print(f"DEBUG: Editing SCREEN region: {region['name']}")
                    self._edit_region_dialog(region)
            else:
                messagebox.showwarning("Error", "Region not found")
        else:
            messagebox.showwarning("No Selection", "Please select a region to edit")

    def _edit_region_dialog(self, region):
        """Edit region using simplified embedded patterns dialog"""
        from ocr_modules.ui.ui_components import RegionDialog
    
        dialog = RegionDialog(
            self.app.root,
            title=f"Edit Region - {region['name']}",
            default_name=region['name'],
            default_coords=region.get('bounds'),
            is_edit_mode=True,
            existing_region=region
        )
    
        result = dialog.show()

        if result:
            # Update region with new values
            region.update(result)
            self.ensure_save()
            self._refresh_regions_tree()
            self.app.messages(2, 9, f"Region '{result['name']}' updated")

    def _test_single_region(self, region):
        """Test a specific region"""
        try:
            if region.get('hwnd'):
                # Window capture
                self.window_capture.set_method(region.get('capture_method', 'auto'))
                image = self.window_capture.capture_region(hwnd=region['hwnd'])
            else:
                # Screen region capture
                x, y, w, h = region['bounds']
                region_dict = {'left': x, 'top': y, 'width': w, 'height': h}
                self.window_capture.set_method(region.get('capture_method', 'auto'))
                image = self.window_capture.capture_region(region=region_dict)
            
            if image:
                # Show preview
                preview = tk.Toplevel(self.app.root)
                preview.title(f"Test - {region['name']}")
                
                # Resize for display
                display_width = min(image.width, 600)
                scale_factor = display_width / image.width
                display_height = int(image.height * scale_factor)
                
                display_image = image.resize((display_width, display_height), Image.LANCZOS)
                photo = ImageTk.PhotoImage(display_image)
                
                label = ttk.Label(preview, image=photo)
                label.image = photo
                label.pack(padx=10, pady=10)
                
                # Perform OCR on the test image
                processed_image = self.preprocess_image_for_gaming(image, region['name'])
                ocr_config = self._get_ocr_config()
                text = pytesseract.image_to_string(processed_image, config=ocr_config)
                
                # Show OCR results
                text_frame = ttk.Frame(preview)
                text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
                
                ttk.Label(text_frame, text="OCR Results:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
                
                text_widget = tk.Text(text_frame, height=6, wrap=tk.WORD)
                text_scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
                text_widget.configure(yscrollcommand=text_scrollbar.set)
                
                text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
                text_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
                
                text_widget.insert(1.0, text if text.strip() else "No text detected")
                text_widget.config(state=tk.DISABLED)
            else:
                messagebox.showerror("Test Failed", "Could not capture region")
                
        except Exception as e:
            messagebox.showerror("Test Failed", f"Error: {e}")

    def add_window_region(self, name, hwnd, window_title, capture_method, patterns, cooldown=300, subregion_bounds=None):
        """Add a window-based region with proper bounds and optional sub-region"""
        try:
            # Get current window bounds for display
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top

            region = {
                'name': name,
                'type': 'window',
                'hwnd': hwnd,
                'window_title': window_title,
                'bounds': (left, top, width, height),  # Entire window bounds
                'patterns': patterns,
                'cooldown': cooldown or self.config.get("default_cooldown", 300),
                'last_seen': {},
                'enabled': True,
                'color_profile': self.config.get("current_color_profile", "default"),
                'tts_messages': {},
                'capture_method': capture_method,
                'subregion_bounds': subregion_bounds  # Can be None (entire window) or (x, y, w, h) relative to window
            }
            self.regions.append(region)
            self.ensure_save()

            return region
        except Exception as e:
            print(f"Error adding window region: {e}")
            # Fallback with default bounds
            region = {
                'name': name,
                'type': 'window', 
                'hwnd': hwnd,
                'window_title': window_title,
                'bounds': (0, 0, 100, 100),  # FALLBACK BOUNDS
                'patterns': patterns,
                'cooldown': cooldown,
                'last_seen': {},
                'enabled': True,
                'color_profile': self.config.get("current_color_profile", "default"),
                'tts_messages': {},
                'capture_method': capture_method,
                'subregion_bounds': subregion_bounds
            }
            self.regions.append(region)
            self.ensure_save()
            return region

    def find_window_by_criteria(self, window_title=None, process_name=None, window_class=None):
        """Find a window based on identification criteria"""
        try:
            windows = self.list_available_windows()

            for window in windows:
                matches = True

                # Match window title (partial match)
                if window_title:
                    if window_title.lower() not in window['title'].lower():
                        matches = False

                # Match process name (exact match)
                if process_name and matches:
                    if process_name.lower() != window['process_name'].lower():
                        matches = False

                # Match window class (exact match)
                if window_class and matches:
                    if window_class != window['class_name']:
                        matches = False

                if matches:
                    return window['hwnd']

            return None

        except Exception as e:
            print(f"Error finding window: {e}")
            return None

    def find_best_window_match(self, region):
        """Find the best matching window for a region"""
        # Try exact match first
        hwnd = self.find_window_by_criteria(
            window_title=region.get('window_title'),
            process_name=region.get('process_name'),
            window_class=region.get('window_class')
        )

        # If no exact match, try with just title and process
        if not hwnd and region.get('window_title') and region.get('process_name'):
            hwnd = self.find_window_by_criteria(
                window_title=region.get('window_title'),
                process_name=region.get('process_name')
            )

        # If still no match, try with just title
        if not hwnd and region.get('window_title'):
            hwnd = self.find_window_by_criteria(
                window_title=region.get('window_title')
            )

        return hwnd

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
            self._refresh_regions_tree()
            self.reset_monitoring_state()
            
    def _apply_ocr_settings(self):
        """Apply OCR settings from the UI"""
        try:
            self.config["check_interval"] = float(self.interval_var.get())
            self.config["language"] = self.language_var.get()
            self.config["default_cooldown"] = int(self.cooldown_var.get())
            self.config["tts_alerts"] = self.tts_alerts_var.get()
            
            self.app.messages(2, 9, "OCR settings applied")
            self.save_configuration()
            
        except ValueError as e:
            self.app.messages(2, 3, f"Invalid setting value: {e}")
            
    def reset_monitoring_state(self):
        """Reset monitoring state to clear any stuck data"""
        if self.monitoring:
            self.teardown()
            time.sleep(0.5)  # Brief pause
            self.setup()
        # Reset pattern tracking for all regions
        for region in self.regions:
            region['last_seen'] = {}
            region['last_region_alert'] = 0

    def list_available_windows(self):
        """List all available top-level windows with their details"""
        import psutil

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

                # Get window dimensions
                try:
                    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
                    width = right - left
                    height = bottom - top

                    # Only include windows of reasonable size
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
                    pass  # Skip windows that can't be measured
            return True

        win32gui.EnumWindows(enum_windows_proc, None)
        return sorted(windows, key=lambda x: x['title'])

    def get_top_parent(self, hwnd):
        """Get the top-level parent window for a handle"""
        if not hwnd or not win32gui.IsWindow(hwnd):
            return None

        parent = win32gui.GetParent(hwnd)
        while parent:
            hwnd = parent
            parent = win32gui.GetParent(hwnd)
        return hwnd

    def _select_window_from_list(self):
        """Open the new unified window region dialog instead of the old one"""
        self._add_window_region_dialog()

    def _on_window_selected(self, tree, dialog):
        """Handle window selection from the list"""
        selection = tree.selection()
        if selection:
            hwnd = tree.item(selection[0], 'tags')[0]
            dialog.destroy()
            self._configure_selected_window(hwnd)
        else:
            messagebox.showwarning("No Selection", "Please select a window from the list.")

    def _configure_selected_window(self, hwnd):
        """Configure monitoring for a selected window using identification criteria"""
        try:
            # Get window information for identification
            window_title = win32gui.GetWindowText(hwnd)
            class_name = win32gui.GetClassName(hwnd)

            # Get process name
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            try:
                process = psutil.Process(pid)
                process_name = process.name()
            except:
                process_name = "Unknown"
        
            # Create configuration dialog
            dialog = tk.Toplevel(self.app.root)
            dialog.title(f"Configure Window: {window_title[:30]}...")
            dialog.geometry("500x500")
            dialog.transient(self.app.root)

            main_frame = ttk.Frame(dialog, padding=10)
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Window information
            info_frame = ttk.LabelFrame(main_frame, text="Window Identification")
            info_frame.pack(fill=tk.X, pady=(0, 10))

            info_text = f"""Title: {window_title}
                        Process: {process_name}
                        Class: {class_name}
                        PID: {pid}

                        The window will be found dynamically using these criteria."""

            info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
            info_label.pack(padx=10, pady=10, anchor=tk.W)

            # Region name
            ttk.Label(main_frame, text="Region Name:").pack(anchor=tk.W, pady=(10, 5))
            name_var = tk.StringVar(value=window_title[:30] or f"Window_{process_name}")
            ttk.Entry(main_frame, textvariable=name_var).pack(fill=tk.X, pady=(0, 10))

            # Identification criteria (allow user to customize)
            criteria_frame = ttk.LabelFrame(main_frame, text="Identification Criteria")
            criteria_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(criteria_frame, text="Window Title:").pack(anchor=tk.W, pady=(5, 0))
            title_var = tk.StringVar(value=window_title)
            title_entry = ttk.Entry(criteria_frame, textvariable=title_var)
            title_entry.pack(fill=tk.X, padx=5, pady=(0, 5))

            ttk.Label(criteria_frame, text="Process Name:").pack(anchor=tk.W, pady=(5, 0))
            process_var = tk.StringVar(value=process_name)
            process_entry = ttk.Entry(criteria_frame, textvariable=process_var)
            process_entry.pack(fill=tk.X, padx=5, pady=(0, 5))

            ttk.Label(criteria_frame, text="Window Class (optional):").pack(anchor=tk.W, pady=(5, 0))
            class_var = tk.StringVar(value=class_name)
            class_entry = ttk.Entry(criteria_frame, textvariable=class_var)
            class_entry.pack(fill=tk.X, padx=5, pady=(0, 5))

            # Capture method
            ttk.Label(main_frame, text="Capture Method:").pack(anchor=tk.W, pady=(0, 5))
            method_var = tk.StringVar(value="auto")
            method_combo = ttk.Combobox(main_frame, textvariable=method_var,
                                    values=[method.value for method in CaptureMethod],
                                    state="readonly")
            method_combo.pack(fill=tk.X, pady=(0, 10))

            # Test capture button
            def test_capture():
                try:
                    self.window_capture.set_method(method_var.get())
                    image = self.window_capture.capture_region(hwnd=hwnd)

                    if image:
                        # Show preview
                        preview = tk.Toplevel(dialog)
                        preview.title("Capture Test")

                        display_width = min(image.width, 400)
                        scale_factor = display_width / image.width
                        display_height = int(image.height * scale_factor)

                        display_image = image.resize((display_width, display_height), Image.LANCZOS)
                        photo = ImageTk.PhotoImage(display_image)

                        label = ttk.Label(preview, image=photo)
                        label.image = photo
                        label.pack(padx=10, pady=10)

                        status = "✓ Capture successful!"
                        if image.getbbox() is None:
                            status = "⚠ Warning: Image appears to be blank/black. Try a different capture method."

                        ttk.Label(preview, text=status).pack(pady=5)
                    else:
                        messagebox.showerror("Test Failed", "Failed to capture window")

                except Exception as e:
                    messagebox.showerror("Test Failed", f"Error: {str(e)}")

            ttk.Button(main_frame, text="Test Capture", 
                    command=test_capture).pack(anchor=tk.W, pady=(0, 10))

            # Patterns
            patterns_frame = ttk.LabelFrame(main_frame, text="Patterns to Monitor")
            patterns_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

            patterns_text = tk.Text(patterns_frame, height=4)
            patterns_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            patterns_text.insert(1.0, "error\nwarning\nalert\nsuccess")

            def save_window_region():
                name = name_var.get().strip()
                if not name:
                    messagebox.showerror("Error", "Region name is required")
                    return

                patterns = [p.strip() for p in patterns_text.get(1.0, tk.END).strip().split('\n') if p.strip()]
                if not patterns:
                    messagebox.showerror("Error", "At least one pattern is required")
                    return

                # Add the window region using identification criteria
                self.add_window_region(
                    name=name,
                    hwnd=hwnd,  # Make sure hwnd is available here
                    window_title=title_var.get().strip(),
                    capture_method=method_var.get(),
                    patterns=patterns,
                    cooldown=300
                )

                dialog.destroy()
                self.app.messages(2, 9, f"Window region '{name}' added")

            ttk.Button(main_frame, text="Save Window Region", 
                    command=save_window_region, style='Success.TButton').pack(anchor=tk.E)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to configure window: {e}")

    def _select_window_interactive(self):
        """Open the new unified window region dialog instead of the old one"""
        self._add_window_region_dialog()

    # Add these to your main class or a UI helper class
    def create_labeled_combobox(self, parent, label, values, default_value, callback=None):
        """Create a consistent labeled combobox"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)
    
        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.StringVar(value=default_value)
        combo = ttk.Combobox(frame, textvariable=var, values=values, state="readonly")
        combo.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

        if callback:
            var.trace('w', callback)

        return var, combo

    def create_labeled_entry(self, parent, label, default_value, width=10):
        """Create a consistent labeled entry"""
        frame = ttk.Frame(parent)
        frame.pack(fill=tk.X, pady=2)

        ttk.Label(frame, text=label).pack(side=tk.LEFT)
        var = tk.StringVar(value=default_value)
        entry = ttk.Entry(frame, textvariable=var, width=width)
        entry.pack(side=tk.RIGHT, padx=(10, 0))

        return var

    def create_checkbox(self, parent, text, default_value, callback=None):
        """Create a consistent checkbox"""
        var = tk.BooleanVar(value=default_value)
        cb = ttk.Checkbutton(parent, text=text, variable=var)
        cb.pack(anchor=tk.W, pady=2)

        if callback:
            var.trace('w', callback)
        return var

    def ensure_save(self):
        """Ensure config is saved - call this after important changes"""
        try:
            self.config["regions"] = self.regions
            self.config_manager.save_configuration()
            print("✅ Config saved")
            self._refresh_regions_tree()
        except Exception as e:
            print(f"❌ Save failed: {e}")
