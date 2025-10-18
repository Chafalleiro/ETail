# plugins/ocr_modules/ui/settings_tabs.py
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable

class SettingsTabs:
    """Container for all settings tab creation methods"""
    
    def __init__(self, plugin):
        self.plugin = plugin
    
    def create_tesseract_tab(self, parent):
        """Create Tesseract configuration tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tesseract path section
        path_frame = ttk.LabelFrame(main_frame, text="Tesseract Configuration")
        path_frame.pack(fill=tk.X, pady=(0, 15))

        inner_frame = ttk.Frame(path_frame)
        inner_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(inner_frame, text="Tesseract Path:").grid(row=0, column=0, sticky="w", pady=5)

        path_entry_frame = ttk.Frame(inner_frame)
        path_entry_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        path_entry_frame.columnconfigure(0, weight=1)

        self.plugin.tesseract_path_var = tk.StringVar(value=self.plugin.config.get("tesseract_path", ""))
        path_entry = ttk.Entry(path_entry_frame, textvariable=self.plugin.tesseract_path_var, width=50)
        path_entry.grid(row=1, column=0, columnspan=4, sticky="ew", padx=(0, 5))

        ttk.Button(path_entry_frame, text="Browse", 
                  command=self.plugin._browse_tesseract, width=10).grid(row=1, column=5)

        # Test button and status
        ttk.Button(path_entry_frame, text="Test Tesseract", 
                  command=self.plugin._test_tesseract).grid(row=2, column=0)

        self.plugin.tesseract_status_var = tk.StringVar(value="Click 'Test Tesseract' to verify")
        ttk.Label(inner_frame, textvariable=self.plugin.tesseract_status_var).grid(row=2, column=0)

        return main_frame

    def create_ocr_tab(self, parent):
        """Create OCR settings tab using helper methods"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Use the plugin's UI helper methods
        self.plugin.interval_var = self.plugin.create_labeled_entry(
            main_frame, "Check Interval (seconds):", 
            str(self.plugin.config.get("check_interval", 2.0))
        )
        
        self.plugin.language_var, _ = self.plugin.create_labeled_combobox(
            main_frame, "OCR Language:",
            ["eng", "spa", "fra", "deu", "ita", "por"],
            self.plugin.config.get("language", "eng")
        )
        
        self.plugin.cooldown_var = self.plugin.create_labeled_entry(
            main_frame, "Default Cooldown (seconds):",
            str(self.plugin.config.get("default_cooldown", 300))
        )
        
        self.plugin.tts_alerts_var = self.plugin.create_checkbox(
            main_frame, "Enable TTS Alerts",
            self.plugin.config.get("tts_alerts", False)
        )
        
        ttk.Button(main_frame, text="Apply Settings", 
                  command=self.plugin._apply_ocr_settings, 
                  style='Success.TButton').pack(anchor=tk.W, pady=(20, 0))
        
        return main_frame

    def create_gaming_tab(self, parent):
        """Create gaming optimization settings tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Profile selection
        profile_frame = ttk.LabelFrame(main_frame, text="Game Text Profile")
        profile_frame.pack(fill=tk.X, pady=(0, 15))

        inner_profile = ttk.Frame(profile_frame)
        inner_profile.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(inner_profile, text="Profile:").grid(row=0, column=0, sticky="w", pady=5)

        self.plugin.profile_var = tk.StringVar(value=self.plugin.config.get("current_profile", "default"))
        profile_combo = ttk.Combobox(inner_profile, textvariable=self.plugin.profile_var, 
                                    values=list(self.plugin.config["game_profiles"].keys()),
                                    state="readonly", width=20)
        profile_combo.grid(row=0, column=1, sticky="w", padx=(10, 0), pady=5)

        # Profile descriptions
        desc_text = (
            "• Default: Balanced settings\n"
            "• Small Text: 2x scale, high contrast\n" 
            "• Console Text: 1.5x scale, medium contrast\n"
            "• UI Text: No scaling, low contrast"
        )
        desc_label = ttk.Label(inner_profile, text=desc_text, justify=tk.LEFT)
        desc_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=10)

        # Optimization settings
        optim_frame = ttk.LabelFrame(main_frame, text="Optimization Settings")
        optim_frame.pack(fill=tk.X, pady=(0, 15))

        inner_optim = ttk.Frame(optim_frame)
        inner_optim.pack(fill=tk.X, padx=10, pady=10)

        self.plugin.preprocess_var = tk.BooleanVar(value=self.plugin.config.get("enable_preprocessing", True))
        ttk.Checkbutton(inner_optim, text="Enable Image Pre-processing", 
                    variable=self.plugin.preprocess_var).pack(anchor="w", pady=2)

        self.plugin.fuzzy_var = tk.BooleanVar(value=self.plugin.config.get("enable_fuzzy_matching", False))
        ttk.Checkbutton(inner_optim, text="Enable Fuzzy Text Matching", 
                    variable=self.plugin.fuzzy_var).pack(anchor="w", pady=2)

        # Fuzzy threshold
        fuzzy_frame = ttk.Frame(inner_optim)
        fuzzy_frame.pack(fill=tk.X, pady=5)

        ttk.Label(fuzzy_frame, text="Fuzzy Threshold:").pack(side=tk.LEFT)
        self.plugin.fuzzy_threshold_var = tk.StringVar(value=str(self.plugin.config.get("fuzzy_threshold", 85)))
        ttk.Entry(fuzzy_frame, textvariable=self.plugin.fuzzy_threshold_var, width=5).pack(side=tk.LEFT, padx=(5, 2))
        ttk.Label(fuzzy_frame, text="%").pack(side=tk.LEFT)

        # Performance monitoring
        self.plugin.performance_var = tk.BooleanVar(value=self.plugin.config.get("performance_monitoring", True))
        ttk.Checkbutton(inner_optim, text="Enable Performance Monitoring", 
                    variable=self.plugin.performance_var).pack(anchor="w", pady=2)

        # Performance stats
        stats_frame = ttk.LabelFrame(main_frame, text="Performance Statistics")
        stats_frame.pack(fill=tk.X, pady=(0, 15))

        self.plugin.stats_var = tk.StringVar(value="Run monitor to collect stats")
        stats_label = ttk.Label(stats_frame, textvariable=self.plugin.stats_var, font=("Courier", 9))
        stats_label.pack(padx=10, pady=10)

        # Apply button
        ttk.Button(main_frame, text="Apply Gaming Settings", 
                command=self.plugin._apply_gaming_settings, 
                style='Success.TButton').pack(anchor="e", pady=(10, 0))

        # Update stats display
        self.plugin._update_performance_stats()
    
        return main_frame

    def create_colors_tab(self, parent):
        """Create color filtering settings tab"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Enable color filtering
        self.plugin.color_filter_var = tk.BooleanVar(value=self.plugin.config.get("enable_color_filtering", True))
        ttk.Checkbutton(main_frame, text="Enable Color Filtering", 
                    variable=self.plugin.color_filter_var).pack(anchor=tk.W, pady=(0, 15))

        # Color profile selection
        ttk.Label(main_frame, text="Default Color Profile:").pack(anchor=tk.W, pady=(0, 5))
        self.plugin.color_profile_var = tk.StringVar(value=self.plugin.config.get("current_color_profile", "default"))
        color_profiles = list(self.plugin.config["color_filters"].keys())
        color_combo = ttk.Combobox(main_frame, textvariable=self.plugin.color_profile_var, 
                                values=color_profiles, state="readonly")
        color_combo.pack(fill=tk.X, pady=(0, 15))

        # Color tolerance
        tolerance_frame = ttk.Frame(main_frame)
        tolerance_frame.pack(fill=tk.X, pady=(0, 15))
        ttk.Label(tolerance_frame, text="Color Tolerance:").pack(side=tk.LEFT)
        self.plugin.tolerance_var = tk.StringVar(value=str(self.plugin.config.get("color_tolerance", 30)))
        ttk.Entry(tolerance_frame, textvariable=self.plugin.tolerance_var, width=5).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(tolerance_frame, text="(0-100, lower = more precise)").pack(side=tk.LEFT, padx=(5, 0))

        # Available color profiles
        profiles_frame = ttk.LabelFrame(main_frame, text="Available Color Profiles")
        profiles_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Create listbox for color profiles
        self.plugin.profiles_listbox = tk.Listbox(profiles_frame, height=6)
        self.plugin.profiles_listbox.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Refresh profiles list
        self._refresh_color_profiles_list()

        # Profile controls
        profile_controls = ttk.Frame(profiles_frame)
        profile_controls.pack(fill=tk.X, padx=5, pady=5)

        ttk.Button(profile_controls, text="Delete Selected Profile", 
                command=self.plugin._delete_color_profile).pack(side=tk.LEFT)
    
        # Apply button
        ttk.Button(main_frame, text="Apply Color Settings", 
                command=self.plugin._apply_color_settings, 
                style='Success.TButton').pack(anchor=tk.W, pady=(10, 0))
        return main_frame

    def _refresh_color_profiles_list(self):
        """Refresh the color profiles listbox"""
        if hasattr(self.plugin, 'profiles_listbox'):
            self.plugin.profiles_listbox.delete(0, tk.END)
            for profile_name in self.plugin.config["color_filters"].keys():
                colors_count = len(self.plugin.config["color_filters"][profile_name]["target_colors"])
                display_text = f"{profile_name} ({colors_count} colors)"
                self.plugin.profiles_listbox.insert(tk.END, display_text)

    def create_capture_tab(self, parent):
        """Create the capture methods tab with better organization"""
        tab = ttk.Frame(parent)

        # Main container with scrollbar
        canvas = tk.Canvas(tab, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Default Capture Method
        default_frame = ttk.LabelFrame(scrollable_frame, text="Default Capture Method", padding=15)
        default_frame.pack(fill=tk.X, pady=(0, 10), padx=5)

        ttk.Label(default_frame, 
                text="Select the default capture method for new regions:",
                wraplength=400).pack(anchor=tk.W, pady=(0, 10))

        self.plugin.capture_method_var = tk.StringVar(
            value=self.plugin.config.get("capture_method", "auto")
        )

        method_combo = ttk.Combobox(default_frame, textvariable=self.plugin.capture_method_var,
                                values=[method.value for method in self.plugin.capture_methods],
                                state="readonly", width=20)
        method_combo.pack(anchor=tk.W, pady=(0, 10))

        # Method descriptions
        desc_frame = ttk.Frame(default_frame)
        desc_frame.pack(fill=tk.X, pady=(0, 10))

        method_descriptions = {
            "auto": "Automatically select the best method based on window type",
            "bitblt": "Fast traditional method, may show black screens for some applications",
            "printwindow": "Works for most problematic windows and applications",
            "printwindow_full": "Best for modern apps and games, captures full content",
            "mss": "Alternative screen capture method, good for full-screen applications"
        }

        self.plugin.method_desc_var = tk.StringVar(value="Select a method to see description")
        desc_label = ttk.Label(desc_frame, textvariable=self.plugin.method_desc_var, 
                            wraplength=400, justify=tk.LEFT, foreground="gray")
        desc_label.pack(anchor=tk.W)

        def update_method_desc(*args):
            method = self.plugin.capture_method_var.get()
            self.plugin.method_desc_var.set(method_descriptions.get(method, ""))

        self.plugin.capture_method_var.trace('w', update_method_desc)
        update_method_desc()  # Initial update

        ttk.Button(default_frame, text="Apply Default Method",
                command=self.plugin._apply_capture_settings).pack(anchor=tk.W)

        # Region-specific Methods
        regions_frame = ttk.LabelFrame(scrollable_frame, text="Region-Specific Methods", padding=15)
        regions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10), padx=5)

        ttk.Label(regions_frame, 
                text="Configure capture methods for individual regions:",
                wraplength=400).pack(anchor=tk.W, pady=(0, 10))

        # Create treeview for region methods
        columns = ('name', 'bounds', 'current_method')
        self.plugin.region_methods_tree = ttk.Treeview(regions_frame, columns=columns, 
                                                    show='headings', height=8)

        self.plugin.region_methods_tree.heading('name', text='Region Name')
        self.plugin.region_methods_tree.heading('bounds', text='Bounds')
        self.plugin.region_methods_tree.heading('current_method', text='Current Method')

        self.plugin.region_methods_tree.column('name', width=150)
        self.plugin.region_methods_tree.column('bounds', width=120)
        self.plugin.region_methods_tree.column('current_method', width=120)

        # Scrollbar for treeview
        tree_scrollbar = ttk.Scrollbar(regions_frame, orient=tk.VERTICAL, 
                                    command=self.plugin.region_methods_tree.yview)
        self.plugin.region_methods_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.plugin.region_methods_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Method selection for regions
        method_control_frame = ttk.Frame(regions_frame)
        method_control_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Label(method_control_frame, text="Set Method:").pack(side=tk.LEFT, padx=(0, 5))

        self.plugin.region_method_var = tk.StringVar(value="auto")
        region_method_combo = ttk.Combobox(method_control_frame, 
                                        textvariable=self.plugin.region_method_var,
                                        values=[method.value for method in  self.plugin.capture_methods],
                                        state="readonly", width=15)
        region_method_combo.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(method_control_frame, text="Apply to Selected",
                command=self.plugin._apply_region_method).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(method_control_frame, text="Reset to Default",
                command=self.plugin._reset_region_method).pack(side=tk.LEFT)

        # Refresh button
        refresh_frame = ttk.Frame(regions_frame)
        refresh_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(refresh_frame, text="🔄 Refresh List",
                command=self.plugin._refresh_region_methods_tree).pack(anchor=tk.W)
    
        # Initial population
        self.plugin._refresh_region_methods_tree()

        return tab
    
    def create_regions_tab(self, parent):
        """Create regions management tab with improved layout"""
        main_frame = ttk.Frame(parent)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Button frame - fixed sizing
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Button(button_frame, text="🎯 Select Region", 
                command=self.plugin._select_region_visual, 
                width=20).pack(side=tk.LEFT, padx=(0, 10))
    
        ttk.Button(button_frame, text="🪟 Select Window (List)", 
            command=self.plugin._select_window_from_list,
            width=20).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="🪟 Select Window", 
                command=self.plugin._select_window_region,
                width=15).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="➕ Add Manual", 
                command=self.plugin._add_manual_region_dialog,
                width=15).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(button_frame, text="🎨 Pick Colors", 
                command=self.plugin._open_color_picker_for_region,
                width=15).pack(side=tk.LEFT)

        # Preview frame - fixed height
        preview_frame = ttk.LabelFrame(main_frame, text="Region Preview")
        preview_frame.pack(fill=tk.X, pady=(0, 15))

        self.plugin.preview_canvas = tk.Canvas(preview_frame, height=125, bg='white')
        self.plugin.preview_canvas.pack(fill=tk.X, padx=10, pady=10)

        # Regions list with proper expansion
        list_frame = ttk.LabelFrame(main_frame, text="Configured Regions")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        # Treeview with scrollbar
        tree_frame = ttk.Frame(list_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Configure columns
        columns = ('name', 'bounds', 'patterns', 'enabled', 'monitor', 'tts_info', 'capture_method','type')
        self.plugin.regions_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', height=3)

        # Configure columns
        self.plugin.regions_tree.heading('name', text='Name')
        self.plugin.regions_tree.heading('bounds', text='Bounds')
        self.plugin.regions_tree.heading('patterns', text='Patterns')
        self.plugin.regions_tree.heading('enabled', text='Enabled')
        self.plugin.regions_tree.heading('monitor', text='Monitor')
        self.plugin.regions_tree.heading('tts_info', text='TTS Messages')
        self.plugin.regions_tree.heading('capture_method', text='Capture Method')
        self.plugin.regions_tree.heading('type', text='Type')

        self.plugin.regions_tree.column('name', width=120)
        self.plugin.regions_tree.column('bounds', width=120)
        self.plugin.regions_tree.column('patterns', width=150)
        self.plugin.regions_tree.column('enabled', width=80)
        self.plugin.regions_tree.column('monitor', width=80)
        self.plugin.regions_tree.column('tts_info', width=80)
        self.plugin.regions_tree.column('capture_method', width=100)
        self.plugin.regions_tree.column('type', width=120)

        # Scrollbar for treeview
        tree_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.plugin.regions_tree.yview)
        self.plugin.regions_tree.configure(yscrollcommand=tree_scroll.set)

        self.plugin.regions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        tree_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Control buttons - fixed at bottom
        controls_frame = ttk.Frame(main_frame)
        controls_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(controls_frame, text="Test Region", 
                command=self.plugin._test_region).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Edit", 
                command=self.plugin._edit_region).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Remove", 
                command=self.plugin._remove_region).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(controls_frame, text="Toggle", 
                command=self.plugin._toggle_region).pack(side=tk.LEFT)

        # Initial refresh
        self.plugin._refresh_regions_tree()
        # Update preview after a short delay to ensure UI is rendered
        if hasattr(self.plugin, 'app') and hasattr(self.plugin.app, 'root'):
            self.plugin.app.root.after(100, self.plugin._update_preview)

        return main_frame

