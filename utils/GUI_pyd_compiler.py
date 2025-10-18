#!/usr/bin/env python3
"""
GUI PYD Compiler - Visual interface for compiling Python files to PYD
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import sys
import shutil
import threading
from pathlib import Path
from datetime import datetime

try:
    from setuptools import setup, Extension
    from Cython.Build import cythonize
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False

class PYDCompiler:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.is_cancelled = False
        
    def log(self, message: str, level="INFO"):
        """Log message with callback to GUI"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        
        if self.log_callback:
            self.log_callback(log_entry, level)
        else:
            print(log_entry)
    
    def cancel(self):
        """Cancel the compilation process"""
        self.is_cancelled = True
        self.log("Compilation cancelled by user", "WARNING")
    
    def verify_cython(self):
        """Verify Cython is available"""
        if not CYTHON_AVAILABLE:
            self.log("Error: Cython is not installed!", "ERROR")
            self.log("Please install Cython: pip install cython", "ERROR")
            return False
        return True
    
    def compile_to_pyd(self, source_file: Path, output_dir: Path, plugin_name: str = None):
        """Compile a single Python file to .pyd"""
        
        if not self.verify_cython():
            return False
        
        if not source_file.exists():
            self.log(f"Error: Source file {source_file} not found!", "ERROR")
            return False
        
        # Use provided plugin name or derive from filename
        if not plugin_name:
            plugin_name = source_file.stem
        
        self.log(f"Starting compilation of {source_file.name}...")
        
        # Create temporary build directory
        build_dir = Path("temp_build")
        build_dir.mkdir(exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Create extension
            extension = Extension(
                plugin_name,
                [str(source_file)],
                extra_compile_args=["/O2"],  # Optimization for Windows
                language="c",
            )
            
            # Run setup
            setup(
                name=plugin_name,
                ext_modules=cythonize(
                    [extension],
                    compiler_directives={
                        'language_level': 3,
                    }
                ),
                script_args=[
                    'build_ext', 
                    '--inplace',
                    f'--build-lib={build_dir}'
                ]
            )
            
            if self.is_cancelled:
                self.log("Compilation cancelled", "WARNING")
                return False
            
            # Find and copy the compiled file
            compiled_files = []
            for file in build_dir.iterdir():
                if file.name.startswith(plugin_name) and (file.suffix in ['.pyd', '.so']):
                    compiled_files.append(file)
                    output_file = output_dir / file.name
                    shutil.copy2(file, output_file)
                    self.log(f"✓ Compiled: {output_file}", "SUCCESS")
            
            if compiled_files:
                self.log(f"✓ Successfully compiled {len(compiled_files)} files", "SUCCESS")
                
                # Clean up build directory
                try:
                    shutil.rmtree(build_dir)
                    # Also remove the build folder created by setuptools
                    build_temp = Path("build")
                    if build_temp.exists():
                        shutil.rmtree(build_temp)
                except:
                    pass
                
                return True
            else:
                self.log("✗ No compiled files found", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"✗ Compilation failed: {e}", "ERROR")
            import traceback
            self.log(traceback.format_exc(), "ERROR")
            return False
    
    def check_plugin_interface(self, source_file: Path):
        """Check if the file has plugin-like structure"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            checks = {
                'has_class': 'class ' in content,
                'has_plugin_flag': 'is_etail_plugin = True' in content or 'is_plugin = True' in content,
                'has_plugin_class': 'ETailPlugin' in content or 'Plugin' in content
            }
            
            return checks
        except Exception as e:
            self.log(f"Error checking plugin interface: {e}", "WARNING")
            return {}

class PYDCompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PYD Compiler GUI")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Variables
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "compiled_plugins"))
        self.is_processing = False
        self.compiler = None
        self.current_file = None
        
        self.setup_styles()
        self.setup_ui()
        
        # Check Cython availability
        if not CYTHON_AVAILABLE:
            messagebox.showwarning(
                "Cython Not Found", 
                "Cython is not installed!\n\nPlease install it with:\npip install cython"
            )
    
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
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(6, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="PYD Compiler", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Source directory selection
        ttk.Label(main_frame, text="Source Directory:").grid(row=1, column=0, sticky=tk.W, pady=5)
        source_entry = ttk.Entry(main_frame, textvariable=self.source_dir, width=60)
        source_entry.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_source_dir).grid(row=1, column=2, pady=5)
        
        # Output directory selection
        ttk.Label(main_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, pady=5)
        output_entry = ttk.Entry(main_frame, textvariable=self.output_dir, width=60)
        output_entry.grid(row=2, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        ttk.Button(main_frame, text="Browse", 
                  command=self.browse_output_dir).grid(row=2, column=2, pady=5)
        
        # File list frame
        list_frame = ttk.LabelFrame(main_frame, text="Python Files", padding="5")
        list_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # File list with scrollbar
        list_control_frame = ttk.Frame(list_frame)
        list_control_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_control_frame.columnconfigure(0, weight=1)
        
        self.file_listbox = tk.Listbox(list_control_frame, height=8, selectmode=tk.SINGLE)
        self.file_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        list_scrollbar = ttk.Scrollbar(list_control_frame, orient=tk.VERTICAL, command=self.file_listbox.yview)
        list_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.file_listbox.configure(yscrollcommand=list_scrollbar.set)
        
        # File list buttons
        list_buttons_frame = ttk.Frame(list_control_frame)
        list_buttons_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        ttk.Button(list_buttons_frame, text="Refresh Files", 
                  command=self.refresh_file_list).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons_frame, text="Check Plugin Interface", 
                  command=self.check_selected_file).pack(side=tk.LEFT, padx=2)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=3, pady=15)
        
        # Compile button
        self.compile_btn = tk.Button(
            button_frame, 
            text="🚀 COMPILE SELECTED FILE", 
            command=self.compile_selected_file,
            bg="#4CAF50", 
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            width=25
        )
        self.compile_btn.pack(side=tk.LEFT, padx=10)
        
        # Other buttons
        other_buttons_frame = ttk.Frame(button_frame)
        other_buttons_frame.pack(side=tk.LEFT, padx=20)
        
        self.cancel_btn = ttk.Button(other_buttons_frame, text="Cancel", 
                                    command=self.cancel_compilation, state="disabled")
        self.cancel_btn.grid(row=0, column=0, padx=5, pady=2)
        
        self.open_output_btn = ttk.Button(other_buttons_frame, text="Open Output Folder", 
                                         command=self.open_output_folder)
        self.open_output_btn.grid(row=1, column=0, padx=5, pady=2)
        
        # Progress frame
        progress_frame = ttk.LabelFrame(main_frame, text="Progress", padding="5")
        progress_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready to compile")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Compilation Log", padding="5")
        log_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure tags for colored logging
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        
        # Bind double-click to select and check file
        self.file_listbox.bind("<Double-1>", self.on_file_double_click)
        
        # Auto-refresh if source directory is set via browse
        self.source_dir.trace('w', self.on_source_dir_changed)
    
    def on_source_dir_changed(self, *args):
        """Auto-refresh file list when source directory changes"""
        if self.source_dir.get() and Path(self.source_dir.get()).exists():
            self.refresh_file_list()
    
    def on_file_double_click(self, event):
        """Handle double-click on file list"""
        self.check_selected_file()
    
    def browse_source_dir(self):
        """Browse for source directory"""
        directory = filedialog.askdirectory(title="Select Source Directory with Python Files")
        if directory:
            self.source_dir.set(directory)
    
    def browse_output_dir(self):
        """Browse for output directory"""
        directory = filedialog.askdirectory(title="Select Output Directory for PYD Files")
        if directory:
            self.output_dir.set(directory)
    
    def refresh_file_list(self):
        """Refresh the list of Python files"""
        if not self.source_dir.get() or not Path(self.source_dir.get()).exists():
            messagebox.showwarning("Warning", "Please select a valid source directory first.")
            return
        
        source_path = Path(self.source_dir.get())
        
        # Clear existing list
        self.file_listbox.delete(0, tk.END)
        
        # Find all Python files
        python_files = list(source_path.glob("*.py"))
        python_files = [f for f in python_files if not f.name.startswith('_')]
        
        if not python_files:
            self.log_message("No Python files found in source directory", "WARNING")
            return
        
        # Add files to listbox
        for py_file in sorted(python_files):
            self.file_listbox.insert(tk.END, py_file.name)
        
        self.log_message(f"Found {len(python_files)} Python files", "SUCCESS")
    
    def get_selected_file(self):
        """Get the currently selected file"""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a file from the list.")
            return None
        
        filename = self.file_listbox.get(selection[0])
        source_path = Path(self.source_dir.get())
        return source_path / filename
    
    def check_selected_file(self):
        """Check the selected file for plugin interface"""
        source_file = self.get_selected_file()
        if not source_file:
            return
        
        self.log_message(f"Checking plugin interface: {source_file.name}", "INFO")
        
        checks = self.compiler.check_plugin_interface(source_file) if self.compiler else {}
        
        if checks:
            self.log_message("Plugin interface check:", "INFO")
            self.log_message(f"  • Contains class: {'✓' if checks.get('has_class') else '✗'}", 
                           "SUCCESS" if checks.get('has_class') else "WARNING")
            self.log_message(f"  • Has plugin flag: {'✓' if checks.get('has_plugin_flag') else '✗'}", 
                           "SUCCESS" if checks.get('has_plugin_flag') else "WARNING")
            self.log_message(f"  • Has plugin class: {'✓' if checks.get('has_plugin_class') else '✗'}", 
                           "SUCCESS" if checks.get('has_plugin_class') else "WARNING")
        else:
            self.log_message("Could not read file for interface check", "ERROR")
    
    def compile_selected_file(self):
        """Compile the selected file to PYD"""
        if not CYTHON_AVAILABLE:
            messagebox.showerror(
                "Cython Required", 
                "Cython is not installed!\n\nPlease install it with:\npip install cython"
            )
            return
        
        source_file = self.get_selected_file()
        if not source_file:
            return
        
        if not self.output_dir.get():
            messagebox.showerror("Error", "Please specify an output directory.")
            return
        
        # Clear log
        self.log_text.delete(1.0, tk.END)
        
        # Disable buttons during processing
        self.set_ui_state(False)
        self.is_processing = True
        self.current_file = source_file
        self.status_var.set("Compilation in progress...")
        
        # Start compilation in separate thread
        thread = threading.Thread(target=self.run_compilation, args=(source_file,))
        thread.daemon = True
        thread.start()
        
        # Start progress monitoring
        self.monitor_progress()
    
    def set_ui_state(self, enabled: bool):
        """Enable/disable UI controls"""
        state = "normal" if enabled else "disabled"
        self.compile_btn.config(state=state)
        self.open_output_btn.config(state=state)
        self.cancel_btn.config(state="normal" if not enabled else "disabled")
    
    def run_compilation(self, source_file: Path):
        """Run the compilation process in background thread"""
        try:
            self.compiler = PYDCompiler(log_callback=self.log_message)
            
            output_dir = Path(self.output_dir.get())
            success = self.compiler.compile_to_pyd(source_file, output_dir)
            
            if success:
                self.status_var.set("Compilation completed successfully!")
                self.log_message("Compilation process finished successfully!", "SUCCESS")
                
                # Show success message
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", 
                    f"File compiled successfully!\n\nOutput: {output_dir / source_file.stem}.pyd"
                ))
            else:
                self.status_var.set("Compilation failed")
                self.log_message("Compilation process failed!", "ERROR")
                
        except Exception as e:
            self.status_var.set("Compilation failed with error")
            self.log_message(f"Compilation error: {str(e)}", "ERROR")
        
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.set_ui_state(True))
    
    def cancel_compilation(self):
        """Cancel the ongoing compilation process"""
        if self.compiler and self.is_processing:
            self.compiler.cancel()
            self.status_var.set("Cancelling...")
            self.log_message("Cancellation requested...", "WARNING")
    
    def monitor_progress(self):
        """Monitor and update progress"""
        if self.is_processing:
            current_progress = self.progress_var.get()
            if current_progress < 90:
                self.progress_var.set(current_progress + 2)
            
            self.root.after(500, self.monitor_progress)
        else:
            self.progress_var.set(100)
    
    def open_output_folder(self):
        """Open the output folder in file explorer"""
        if not self.output_dir.get() or not Path(self.output_dir.get()).exists():
            messagebox.showwarning("Warning", "Output directory does not exist.")
            return
        
        output_path = Path(self.output_dir.get())
        try:
            if sys.platform == "win32":
                os.startfile(output_path)
            elif sys.platform == "darwin":  # macOS
                os.system(f'open "{output_path}"')
            else:  # Linux
                os.system(f'xdg-open "{output_path}"')
        except Exception as e:
            self.log_message(f"Could not open output folder: {e}", "WARNING")
    
    def log_message(self, message: str, level: str = "INFO"):
        """Add message to log with colored tags"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry, level)
        self.log_text.see(tk.END)
        self.log_text.update_idletasks()
        
        # Also print to console
        print(f"[{level}] {message}")

def main():
    """Main function to run the GUI"""
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except:
        pass
    
    root = tk.Tk()
    app = PYDCompilerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()