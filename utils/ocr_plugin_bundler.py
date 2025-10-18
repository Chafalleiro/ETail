#!/usr/bin/env python3
"""
OCR Plugin Bundler - Complete version with file tree and import fixes
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import threading
import time
from pathlib import Path
import re
from datetime import datetime

class OCRPluginBundler:
    def __init__(self, plugin_root: str, output_file: str, log_callback=None, exclude_patterns=None):
        self.plugin_root = Path(plugin_root)
        self.output_file = Path(output_file)
        self.processed_files = set()
        self.bundled_content = []
        self.import_map = {}
        self.log_callback = log_callback
        self.is_cancelled = False
        self.exclude_patterns = exclude_patterns or ['__pycache__', '*.pyc', '__init__.py']
        
    def log(self, message: str, level="INFO"):
        """Log message with callback to GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if self.log_callback:
            self.log_callback(log_entry, level)
        else:
            print(log_entry)
    
    def should_exclude_file(self, file_path: Path) -> bool:
        """Check if file should be excluded based on patterns"""
        file_str = str(file_path)
        for pattern in self.exclude_patterns:
            if pattern in file_str:
                return True
        return False
    
    def cancel(self):
        """Cancel the bundling process"""
        self.is_cancelled = True
        self.log("Bundling cancelled by user", "WARNING")
    
    def find_all_python_files(self):
        """Find all Python files in the plugin structure"""
        python_files = list(self.plugin_root.rglob("*.py"))
        python_files = [f for f in python_files if not self.should_exclude_file(f)]
        return python_files
    
    def analyze_import_structure(self):
        """Analyze the import structure and find all dependencies"""
        self.log("Analyzing import structure...")
        
        # Find all Python files
        python_files = self.find_all_python_files()
        self.log(f"Found {len(python_files)} Python files in plugin structure")
        
        # Map module names to file paths
        for py_file in python_files:
            rel_path = py_file.relative_to(self.plugin_root)
            module_path = str(rel_path).replace('\\', '.').replace('/', '.').replace('.py', '')
            self.import_map[module_path] = str(py_file)
            
            # Map without ocr_plugin prefix
            if module_path.startswith('ocr_plugin.'):
                short_path = module_path[11:]
                self.import_map[short_path] = str(py_file)
            
            # Map individual module names
            if 'ocr_modules' in module_path:
                parts = module_path.split('.')
                if len(parts) >= 2:
                    module_name = parts[-1]
                    self.import_map[module_name] = str(py_file)
    
    def extract_imports_from_line(self, line: str):
        """Extract import information from a single line"""
        imports = []
        
        # Skip lines that are inside strings or comments
        stripped = line.strip()
        if stripped.startswith('#') or not stripped:
            return imports
        
        # Pattern for: from module import name (including relative imports)
        from_pattern = r'^\s*from\s+((?:\.+\s*)*[\w\.]*)\s+import\s+([\w\*, ]+)'
        from_match = re.match(from_pattern, line)
        if from_match:
            module = from_match.group(1).replace(' ', '')  # Remove spaces from dots
            imports.append(('from', module, from_match.group(2)))
            return imports
        
        # Pattern for: import module (including relative imports)
        import_pattern = r'^\s*import\s+((?:\.+\s*)*[\w\., ]+)'
        import_match = re.match(import_pattern, line)
        if import_match:
            modules = [m.strip().replace(' ', '') for m in import_match.group(1).split(',')]
            for module in modules:
                imports.append(('import', module, None))
            return imports
        
        return imports
    
    def is_plugin_import(self, module_name: str):
        """Check if this is an import from our plugin"""
        # Check for absolute imports
        plugin_patterns = [
            'ocr_modules',
            'ocr_plugin',
        ]
        
        # Check for relative imports (any that start with .)
        if module_name.startswith('.'):
            return True
            
        return any(pattern in module_name for pattern in plugin_patterns)
    
    def resolve_plugin_import(self, module_name: str, current_file: Path):
        """Resolve a plugin import to a file path"""
        # Handle relative imports
        if module_name.startswith('.'):
            # Count dots for relative level
            dots = len(module_name) - len(module_name.lstrip('.'))
            base_module = module_name[dots:]
            
            # Get current file's directory
            current_dir = current_file.parent
            
            # Go up appropriate number of levels
            for _ in range(dots - 1):
                current_dir = current_dir.parent
            
            # Try to find the file
            if base_module:
                possible_paths = [
                    current_dir / f"{base_module}.py",
                    current_dir / base_module / "__init__.py"
                ]
            else:
                # This is "from . import something" - look for __init__.py in current dir
                possible_paths = [current_dir / "__init__.py"]
            
            for path in possible_paths:
                if path.exists() and not self.should_exclude_file(path):
                    return path
        
        # Try direct mapping first
        if module_name in self.import_map:
            return Path(self.import_map[module_name])
        
        # Try common patterns
        possible_paths = [
            self.plugin_root / f"{module_name}.py",
            self.plugin_root / "ocr_modules" / f"{module_name}.py",
            self.plugin_root / "ocr_modules" / "ui" / f"{module_name}.py",
        ]
        
        for path in possible_paths:
            if path.exists() and not self.should_exclude_file(path):
                return path
        
        return None
    
    def read_file_content(self, file_path: Path):
        """Read file content with proper encoding"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                self.log(f"Failed to read {file_path}: {e}", "ERROR")
                return ""
    
    def is_inside_string(self, line: str, in_triple_single: bool, in_triple_double: bool):
        """Check if we're inside a triple-quoted string"""
        # Count triple quotes in the line
        triple_single_count = line.count("'''")
        triple_double_count = line.count('"""')
        
        # If we have an odd number of triple quotes, we're toggling the state
        if triple_single_count % 2 == 1:
            in_triple_single = not in_triple_single
        if triple_double_count % 2 == 1:
            in_triple_double = not in_triple_double
            
        return in_triple_single or in_triple_double, in_triple_single, in_triple_double
    
    def process_file(self, file_path: Path):
        """Process a file and handle its imports, being careful with strings"""
        if self.is_cancelled:
            return
            
        if file_path in self.processed_files:
            return
            
        if not file_path.exists():
            self.log(f"File not found: {file_path}", "WARNING")
            return
            
        if self.should_exclude_file(file_path):
            self.log(f"Excluded: {file_path}", "INFO")
            return
        
        self.log(f"Processing: {file_path.relative_to(self.plugin_root)}")
        self.processed_files.add(file_path)
        
        content = self.read_file_content(file_path)
        if not content:
            return
        
        # Add simple file header using only # comments
        self.bundled_content.append("")
        self.bundled_content.append("# " + "=" * 78)
        self.bundled_content.append(f"# File: {file_path.relative_to(self.plugin_root)}")
        self.bundled_content.append("# " + "=" * 78)
        self.bundled_content.append("")
        
        lines = content.split('\n')
        in_triple_single = False
        in_triple_double = False
        
        for i, line in enumerate(lines):
            if self.is_cancelled:
                return
            
            # Check if we're inside a triple-quoted string
            inside_string, in_triple_single, in_triple_double = self.is_inside_string(
                line, in_triple_single, in_triple_double
            )
            
            # Only process imports if we're not inside a string
            if not inside_string and line.strip().startswith(('import ', 'from ')):
                imports = self.extract_imports_from_line(line)
                
                should_include_line = True
                for import_type, module, names in imports:
                    if self.is_plugin_import(module):
                        # This is a plugin import - resolve and process the file
                        resolved_path = self.resolve_plugin_import(module, file_path)
                        if resolved_path and resolved_path not in self.processed_files:
                            self.process_file(resolved_path)
                        # We'll remove plugin import lines
                        should_include_line = False
                        self.log(f"Removing plugin import: {line.strip()}", "INFO")
                        break
                
                if should_include_line:
                    # Keep external imports
                    self.bundled_content.append(line)
                else:
                    # Comment out internal imports instead of removing
                    self.bundled_content.append(f"# {line}  # internal import removed")
            else:
                # Regular code line (or inside string)
                self.bundled_content.append(line)
    
    def include_missing_files(self):
        """Include any Python files that weren't processed through imports"""
        all_files = self.find_all_python_files()
        missing_files = [f for f in all_files if f not in self.processed_files]
        
        if missing_files:
            self.log(f"Found {len(missing_files)} files not imported, including them...")
            
            for file_path in missing_files:
                if self.is_cancelled:
                    return
                    
                self.log(f"Including missing file: {file_path.relative_to(self.plugin_root)}")
                self.processed_files.add(file_path)
                
                content = self.read_file_content(file_path)
                if not content:
                    continue
                
                # Add simple file header
                self.bundled_content.append("")
                self.bundled_content.append("# " + "=" * 78)
                self.bundled_content.append(f"# File: {file_path.relative_to(self.plugin_root)}")
                self.bundled_content.append("# " + "=" * 78)
                self.bundled_content.append("")
                
                self.bundled_content.append(content)
    
    def remove_duplicate_classes(self):
        """Remove duplicate class definitions"""
        self.log("Checking for duplicate classes...")
        
        cleaned_content = []
        seen_classes = set()
        duplicate_count = 0
        in_triple_single = False
        in_triple_double = False
        
        for line in self.bundled_content:
            if self.is_cancelled:
                return
                
            # Check if we're inside a string
            inside_string, in_triple_single, in_triple_double = self.is_inside_string(
                line, in_triple_single, in_triple_double
            )
            
            stripped = line.strip()
            
            # Only check for class definitions outside of strings
            if not inside_string and stripped.startswith('class '):
                class_name = stripped.split()[1].split('(')[0]
                if class_name not in seen_classes:
                    seen_classes.add(class_name)
                    cleaned_content.append(line)
                else:
                    cleaned_content.append(f"# {line}  # DUPLICATE CLASS REMOVED")
                    duplicate_count += 1
                    self.log(f"Removed duplicate class: {class_name}", "WARNING")
            else:
                cleaned_content.append(line)
        
        self.bundled_content = cleaned_content
        if duplicate_count > 0:
            self.log(f"Removed {duplicate_count} duplicate classes", "WARNING")
    
    def fix_remaining_imports(self):
        """Fix any remaining relative imports that weren't caught"""
        self.log("Fixing remaining relative imports...")
        
        fixed_content = []
        fixed_count = 0
        
        for line in self.bundled_content:
            stripped = line.strip()
            
            # Look for relative imports that might have been missed
            if (stripped.startswith('from .') or stripped.startswith('import .')) and not line.startswith('#'):
                # This is a relative import that wasn't processed - comment it out
                fixed_content.append(f"# {line}  # relative import removed")
                fixed_count += 1
                self.log(f"Fixed missed relative import: {stripped}", "WARNING")
            else:
                fixed_content.append(line)
        
        self.bundled_content = fixed_content
        if fixed_count > 0:
            self.log(f"Fixed {fixed_count} remaining relative imports", "WARNING")
    
    def bundle(self):
        """Main bundling method"""
        try:
            self.log("Starting OCR plugin bundling...")
            
            # Analyze structure first
            self.analyze_import_structure()
            
            # Start from main plugin file
            main_file = self.plugin_root / "ocr_plugin.py"
            if not main_file.exists():
                raise FileNotFoundError(f"Main plugin file not found: {main_file}")
            
            self.process_file(main_file)
            
            if self.is_cancelled:
                self.log("Bundling cancelled", "WARNING")
                return False
            
            # Include any files that weren't imported
            self.include_missing_files()
            
            if self.is_cancelled:
                self.log("Bundling cancelled", "WARNING")
                return False
            
            # Remove duplicate classes
            self.remove_duplicate_classes()
            
            # Fix any remaining relative imports
            self.fix_remaining_imports()
            
            if self.is_cancelled:
                self.log("Bundling cancelled", "WARNING")
                return False
            
            # Write the bundled file with simple header
            with open(self.output_file, 'w', encoding='utf-8') as f:
                f.write("# " + "=" * 78 + "\n")
                f.write("# Bundled OCR Plugin\n")
                f.write(f"# Source: {self.plugin_root}\n")
                f.write(f"# Files included: {len(self.processed_files)}\n")
                f.write(f"# Excluded patterns: {self.exclude_patterns}\n")
                f.write(f"# Generated by OCR Plugin Bundler\n")
                f.write("# " + "=" * 78 + "\n")
                f.write("# Note: All internal and relative imports have been removed\n")
                f.write("# " + "=" * 78 + "\n\n")
                
                f.write('\n'.join(self.bundled_content))
            
            self.log(f"Successfully bundled {len(self.processed_files)} files into: {self.output_file}", "SUCCESS")
            
            # Create a summary
            self._create_summary()
            return True
            
        except Exception as e:
            self.log(f"Bundling failed: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    def _create_summary(self):
        """Create a bundling summary"""
        summary_file = self.output_file.parent / "bundling_summary.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("OCR Plugin Bundling Summary\n")
            f.write("=" * 50 + "\n")
            f.write(f"Plugin root: {self.plugin_root}\n")
            f.write(f"Output file: {self.output_file}\n")
            f.write(f"Files processed: {len(self.processed_files)}\n")
            f.write(f"Excluded patterns: {self.exclude_patterns}\n\n")
            
            f.write("Processed files:\n")
            for file_path in sorted(self.processed_files):
                rel_path = file_path.relative_to(self.plugin_root)
                f.write(f"  - {rel_path}\n")
        
        self.log(f"Summary saved to: {summary_file}")

class OCRBundlerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("OCR Plugin Bundler - Complete")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Variables
        self.plugin_root = tk.StringVar()
        self.output_file = tk.StringVar(value="bundled_ocr_plugin.py")
        self.is_processing = False
        self.bundler = None
        self.excluded_files = set()
        self.exclude_patterns = ['__pycache__', '*.pyc', '__init__.py']
        
        self.setup_styles()
        self.setup_ui()
    
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.configure("Success.TLabel", foreground="green")
        style.configure("Error.TLabel", foreground="red")
        style.configure("Warning.TLabel", foreground="orange")
        style.configure("Accent.TButton", font=("Arial", 10, "bold"))
        
    def setup_ui(self):
        """Create the main UI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(5, weight=1)
        main_frame.rowconfigure(7, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="OCR Plugin Bundler - Complete", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Plugin directory selection
        ttk.Label(main_frame, text="Plugin Root Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        plugin_entry = ttk.Entry(main_frame, textvariable=self.plugin_root, width=60)
        plugin_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_plugin_dir).grid(row=1, column=2, pady=5)
        
        # Output file selection
        ttk.Label(main_frame, text="Output File:").grid(row=2, column=0, sticky=tk.W, pady=5)
        output_entry = ttk.Entry(main_frame, textvariable=self.output_file, width=60)
        output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_output_file).grid(row=2, column=2, pady=5)
        
        # File tree preview with checkboxes
        tree_frame = ttk.LabelFrame(main_frame, text="Plugin Structure - Check files to include/exclude", padding="5")
        tree_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)
        
        # Create a frame for tree and buttons
        tree_control_frame = ttk.Frame(tree_frame)
        tree_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        tree_control_frame.columnconfigure(0, weight=1)
        
        # Treeview with checkboxes
        self.tree = ttk.Treeview(tree_control_frame, height=10, show="tree", selectmode="none")
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Add scrollbar to tree
        tree_scrollbar = ttk.Scrollbar(tree_control_frame, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Tree control buttons
        tree_buttons_frame = ttk.Frame(tree_control_frame)
        tree_buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(tree_buttons_frame, text="Select All", 
                  command=self.select_all_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(tree_buttons_frame, text="Deselect All", 
                  command=self.deselect_all_files).pack(side=tk.LEFT, padx=2)
        ttk.Button(tree_buttons_frame, text="Toggle Selection", 
                  command=self.toggle_selection).pack(side=tk.LEFT, padx=2)
        ttk.Button(tree_buttons_frame, text="Exclude __pycache__", 
                  command=self.exclude_pycache).pack(side=tk.LEFT, padx=2)
        
        # Exclusion patterns
        exclude_frame = ttk.LabelFrame(main_frame, text="Exclusion Patterns", padding="5")
        exclude_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        exclude_frame.columnconfigure(0, weight=1)
        
        ttk.Label(exclude_frame, text="Patterns (comma-separated):").grid(row=0, column=0, sticky=tk.W)
        self.exclude_var = tk.StringVar(value=", ".join(self.exclude_patterns))
        exclude_entry = ttk.Entry(exclude_frame, textvariable=self.exclude_var, width=80)
        exclude_entry.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(exclude_frame, text="Files matching these patterns will be excluded. Use * for wildcards.").grid(
            row=2, column=0, sticky=tk.W)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=5, column=0, columnspan=3, pady=15)
        
        # Make Start Bundling button more prominent
        self.bundle_btn = tk.Button(
            button_frame, 
            text="🚀 START BUNDLING", 
            command=self.start_bundling,
            bg="#4CAF50", 
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            width=20
        )
        self.bundle_btn.pack(side=tk.LEFT, padx=10)
        
        # Other buttons
        other_buttons_frame = ttk.Frame(button_frame)
        other_buttons_frame.pack(side=tk.LEFT, padx=20)
        
        self.scan_btn = ttk.Button(other_buttons_frame, text="Rescan Structure", 
                                  command=self.scan_plugin_structure)
        self.scan_btn.grid(row=0, column=0, padx=5, pady=2)
        
        self.cancel_btn = ttk.Button(other_buttons_frame, text="Cancel", 
                                    command=self.cancel_bundling, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=5, pady=2)
        
        self.debug_btn = ttk.Button(other_buttons_frame, text="Test Bundled File", 
                                   command=self.test_bundled_file)
        self.debug_btn.grid(row=1, column=0, columnspan=2, padx=5, pady=2)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready to bundle")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Bundling Log", padding="5")
        log_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure tags for colored logging
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        
        # Bind double-click to toggle selection
        self.tree.bind("<Double-1>", self.on_tree_double_click)
    
    def on_tree_double_click(self, event):
        """Handle double-click on tree items to toggle selection"""
        item = self.tree.selection()[0] if self.tree.selection() else None
        if item:
            self.toggle_file_selection(item)
    
    def toggle_file_selection(self, item):
        """Toggle file selection in tree"""
        current_text = self.tree.item(item, "text")
        if current_text.startswith("✅ "):
            # Currently selected, deselect it
            new_text = current_text[2:]
            file_path = self.tree.item(item, "values")[0]
            if file_path in self.excluded_files:
                self.excluded_files.remove(file_path)
        else:
            # Currently not selected, select it
            new_text = "✅ " + current_text
            file_path = self.tree.item(item, "values")[0]
            self.excluded_files.add(file_path)
        
        self.tree.item(item, text=new_text)
    
    def select_all_files(self):
        """Select all files in the tree"""
        for item in self.tree.get_children():
            current_text = self.tree.item(item, "text")
            if not current_text.startswith("✅ "):
                self.tree.item(item, text="✅ " + current_text)
                file_path = self.tree.item(item, "values")[0]
                self.excluded_files.add(file_path)
    
    def deselect_all_files(self):
        """Deselect all files in the tree"""
        for item in self.tree.get_children():
            current_text = self.tree.item(item, "text")
            if current_text.startswith("✅ "):
                self.tree.item(item, text=current_text[2:])
                file_path = self.tree.item(item, "values")[0]
                if file_path in self.excluded_files:
                    self.excluded_files.remove(file_path)
    
    def toggle_selection(self):
        """Toggle all file selections"""
        for item in self.tree.get_children():
            self.toggle_file_selection(item)
    
    def exclude_pycache(self):
        """Automatically exclude __pycache__ directories"""
        for item in self.tree.get_children():
            file_path = self.tree.item(item, "values")[0]
            if '__pycache__' in file_path:
                current_text = self.tree.item(item, "text")
                if not current_text.startswith("✅ "):
                    self.tree.item(item, text="✅ " + current_text)
                    self.excluded_files.add(file_path)
        
        # Also add to patterns
        current_patterns = [p.strip() for p in self.exclude_var.get().split(",")]
        if '__pycache__' not in current_patterns:
            current_patterns.append('__pycache__')
            self.exclude_var.set(", ".join(current_patterns))
    
    def browse_plugin_dir(self):
        """Browse for plugin root directory"""
        directory = filedialog.askdirectory(title="Select OCR Plugin Root Directory")
        if directory:
            self.plugin_root.set(directory)
            self.scan_plugin_structure()
    
    def browse_output_file(self):
        """Browse for output file location"""
        filename = filedialog.asksaveasfilename(
            title="Save Bundled Plugin As",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            self.output_file.set(filename)
    
    def scan_plugin_structure(self):
        """Scan and display the plugin file structure"""
        if not self.plugin_root.get() or not Path(self.plugin_root.get()).exists():
            messagebox.showwarning("Warning", "Please select a valid plugin directory first.")
            return
        
        plugin_path = Path(self.plugin_root.get())
        
        # Clear existing tree and exclusions
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.excluded_files.clear()
        
        # Build file tree
        self._build_file_tree(plugin_path, "")
        
        self.log_message("Plugin structure scanned successfully", "SUCCESS")
        self.status_var.set("Ready to bundle - files scanned")
    
    def _build_file_tree(self, directory, parent):
        """Recursively build file tree"""
        try:
            # Get all Python files and sort them
            py_files = list(directory.glob("*.py"))
            subdirs = [d for d in directory.iterdir() if d.is_dir() and not d.name.startswith('.')]
            
            # Add Python files first
            for py_file in sorted(py_files):
                # Check if file should be excluded by default patterns
                excluded_by_default = any(pattern in str(py_file) for pattern in self.exclude_patterns)
                
                if excluded_by_default:
                    item_id = self.tree.insert(parent, "end", text=f"✅ 📄 {py_file.name}", 
                                             values=[str(py_file)])
                    self.excluded_files.add(str(py_file))
                else:
                    item_id = self.tree.insert(parent, "end", text=f"📄 {py_file.name}", 
                                             values=[str(py_file)])
            
            # Add subdirectories
            for subdir in sorted(subdirs):
                # Check if directory should be excluded by default patterns
                excluded_by_default = any(pattern in str(subdir) for pattern in self.exclude_patterns)
                
                if excluded_by_default:
                    dir_id = self.tree.insert(parent, "end", text=f"✅ 📁 {subdir.name}", 
                                            values=[str(subdir)])
                    self.excluded_files.add(str(subdir))
                else:
                    dir_id = self.tree.insert(parent, "end", text=f"📁 {subdir.name}", 
                                            values=[str(subdir)])
                self._build_file_tree(subdir, dir_id)
                
        except Exception as e:
            self.log_message(f"Error scanning directory {directory}: {e}", "ERROR")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log with colored tags"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, level)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()
        
        # Also print to console
        print(f"[{level}] {message}")
    
    def start_bundling(self):
        """Start the bundling process"""
        if not self.plugin_root.get():
            messagebox.showerror("Error", "Please select a plugin root directory.")
            return
        
        if not self.output_file.get():
            messagebox.showerror("Error", "Please specify an output file.")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Get exclusion patterns from entry
        patterns = [p.strip() for p in self.exclude_var.get().split(",") if p.strip()]
        
        # Add manually excluded files as patterns
        for excluded_file in self.excluded_files:
            # Convert absolute path to relative pattern
            try:
                rel_path = Path(excluded_file).relative_to(self.plugin_root.get())
                patterns.append(str(rel_path))
            except ValueError:
                patterns.append(excluded_file)
        
        # Disable buttons during processing
        self.set_ui_state(False)
        self.is_processing = True
        self.status_var.set("Bundling in progress...")
        
        # Start bundling in separate thread
        thread = threading.Thread(target=self.run_bundling, args=(patterns,))
        thread.daemon = True
        thread.start()
        
        # Start progress monitoring
        self.monitor_progress()
    
    def set_ui_state(self, enabled: bool):
        """Enable/disable UI controls"""
        state = "normal" if enabled else "disabled"
        self.scan_btn.config(state=state)
        self.bundle_btn.config(state=state)
        self.debug_btn.config(state=state)
        self.cancel_btn.config(state="normal" if not enabled else "disabled")
    
    def run_bundling(self, exclude_patterns):
        """Run the bundling process in background thread"""
        try:
            self.bundler = OCRPluginBundler(
                plugin_root=self.plugin_root.get(),
                output_file=self.output_file.get(),
                log_callback=self.log_message,
                exclude_patterns=exclude_patterns
            )
            
            success = self.bundler.bundle()
            
            if success:
                self.status_var.set("Bundling completed successfully!")
                self.log_message("Bundling process finished successfully!", "SUCCESS")
            else:
                self.status_var.set("Bundling failed")
                self.log_message("Bundling process failed!", "ERROR")
                
        except Exception as e:
            self.status_var.set("Bundling failed with error")
            self.log_message(f"Bundling error: {str(e)}", "ERROR")
        
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.set_ui_state(True))
    
    def cancel_bundling(self):
        """Cancel the ongoing bundling process"""
        if self.bundler and self.is_processing:
            self.bundler.cancel()
            self.status_var.set("Cancelling...")
            self.log_message("Cancellation requested...", "WARNING")
    
    def monitor_progress(self):
        """Monitor and update progress"""
        if self.is_processing:
            current_progress = self.progress_var.get()
            if current_progress < 90:
                self.progress_var.set(current_progress + 5)
            
            self.root.after(500, self.monitor_progress)
        else:
            self.progress_var.set(100)
    
    def test_bundled_file(self):
        """Test the bundled file for basic functionality"""
        if not self.output_file.get() or not Path(self.output_file.get()).exists():
            messagebox.showwarning("Warning", "No bundled file found. Please run bundling first.")
            return
        
        self.log_message("Testing bundled file...", "INFO")
        
        thread = threading.Thread(target=self.run_bundled_test)
        thread.daemon = True
        thread.start()
    
    def run_bundled_test(self):
        """Run comprehensive tests on the bundled file"""
        try:
            bundled_path = Path(self.output_file.get())
            
            # Test 1: Syntax check
            self.log_message("1. Checking syntax...", "INFO")
            with open(bundled_path, 'r', encoding='utf-8') as f:
                source = f.read()
            compile(source, bundled_path.name, 'exec')
            self.log_message("   ✅ Syntax is valid", "SUCCESS")
            
            # Test 2: Check for relative imports
            self.log_message("2. Checking for relative imports...", "INFO")
            relative_imports_found = []
            lines = source.split('\n')
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                if (stripped.startswith('from .') or stripped.startswith('import .')) and not line.startswith('#'):
                    relative_imports_found.append((i, stripped))
            
            if relative_imports_found:
                for line_num, import_line in relative_imports_found:
                    self.log_message(f"   ❌ Relative import at line {line_num}: {import_line}", "ERROR")
                self.log_message("   ⚠ Relative imports found - these will cause errors!", "ERROR")
            else:
                self.log_message("   ✅ No relative imports found", "SUCCESS")
            
            # Test 3: Check for main classes
            self.log_message("3. Checking main classes...", "INFO")
            test_namespace = {}
            try:
                exec(source, test_namespace)
                
                main_classes = [
                    'WindowCapture', 'CaptureMethod', 'ConfigManager', 
                    'RegionSelector', 'SettingsTabs', 'PatternTTSDialog',
                    'RegionDialog', 'WindowRegionDialog'
                ]
                
                missing_classes = []
                for class_name in main_classes:
                    if class_name in test_namespace:
                        self.log_message(f"   ✅ {class_name} found", "SUCCESS")
                    else:
                        missing_classes.append(class_name)
                        self.log_message(f"   ❌ {class_name} NOT found", "WARNING")
                
                if missing_classes:
                    self.log_message(f"   ⚠ Missing classes: {missing_classes}", "WARNING")
                else:
                    self.log_message("   ✅ All main classes found", "SUCCESS")
                    
            except Exception as e:
                self.log_message(f"   ❌ Execution test failed: {e}", "ERROR")
            
            self.log_message("Testing completed", "INFO")
            
        except Exception as e:
            self.log_message(f"Test failed: {str(e)}", "ERROR")

def main():
    """Main function to run the GUI"""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    root = tk.Tk()
    app = OCRBundlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()