#!/usr/bin/env python3
"""
Python File Splitter and Joiner - GUI Version
Provides a graphical interface for splitting and joining Python files.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import re
from pathlib import Path

class PythonFileManager:
    def __init__(self):
        self.imports = []
        self.global_code = []
        self.classes = {}
        self.functions = []
        
    def split_file(self, input_file, output_dir):
        """Split a Python file into separate class files"""
        try:
            # Create output directory
            Path(output_dir).mkdir(parents=True, exist_ok=True)
            
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            self._parse_content(content)
            self._write_split_files(output_dir)
            
            return True, f"Successfully split {input_file} into {len(self.classes)} classes"
        except Exception as e:
            return False, f"Error splitting file: {str(e)}"
        
    def _parse_content(self, content):
        """Parse Python content and separate classes, imports, and global code"""
        self.imports = []
        self.global_code = []
        self.classes = {}
        self.functions = []
        
        lines = content.split('\n')
        current_class = None
        class_content = []
        indent_level = 0
        in_class = False
        
        for line in lines:
            # Check for imports
            if re.match(r'^(import |from )', line.strip()):
                self.imports.append(line)
                continue
                
            # Check for class definition
            class_match = re.match(r'^(\s*)class\s+(\w+)(\(.*\))?:', line)
            if class_match and not in_class:
                # Save previous class if exists
                if current_class:
                    self.classes[current_class] = class_content
                    
                # Start new class
                current_class = class_match.group(2)
                class_content = [line]
                in_class = True
                indent_level = len(class_match.group(1))
                continue
                
            # Check for function definitions (top-level)
            func_match = re.match(r'^def\s+(\w+)\s*\(', line.strip())
            if func_match and not in_class:
                self.functions.append(line)
                continue
                
            if in_class:
                # Check if we're still in the same class
                current_indent = len(line) - len(line.lstrip())
                if line.strip() and current_indent <= indent_level and not line.strip().startswith(' '):
                    # We've left the class
                    self.classes[current_class] = class_content
                    current_class = None
                    in_class = False
                    self.global_code.append(line)
                else:
                    class_content.append(line)
            else:
                # Global code (not in class, not imports)
                if line.strip() and not line.strip().startswith('#'):
                    self.global_code.append(line)
                    
        # Don't forget the last class
        if current_class and class_content:
            self.classes[current_class] = class_content
            
    def _write_split_files(self, output_dir):
        """Write separated classes to individual files"""
        # Write main file with imports and global code
        main_file_content = '\n'.join(self.imports) + '\n\n'
        
        # Add imports for all classes
        for class_name in self.classes.keys():
            main_file_content += f'from {class_name} import {class_name}\n'
            
        if self.functions:
            main_file_content += '\n' + '\n'.join(self.functions) + '\n'
            
        if self.global_code:
            main_file_content += '\n' + '\n'.join(self.global_code)
            
        with open(os.path.join(output_dir, 'main.py'), 'w', encoding='utf-8') as f:
            f.write(main_file_content)
            
        # Write individual class files
        for class_name, class_lines in self.classes.items():
            class_file_content = '\n'.join(self.imports) + '\n\n'
            class_file_content += '\n'.join(class_lines) + '\n'
            
            with open(os.path.join(output_dir, f'{class_name}.py'), 'w', encoding='utf-8') as f:
                f.write(class_file_content)
                
        # Write __init__.py for easy importing
        init_content = ""
        for class_name in self.classes.keys():
            init_content += f'from .{class_name} import {class_name}\n'
            
        with open(os.path.join(output_dir, '__init__.py'), 'w', encoding='utf-8') as f:
            f.write(init_content)

    def join_files(self, input_dir, output_file):
        """Join split Python files back into a single file"""
        try:
            self.all_content = []
            
            # Read main file first
            main_file = os.path.join(input_dir, 'main.py')
            if os.path.exists(main_file):
                with open(main_file, 'r', encoding='utf-8') as f:
                    self.all_content.append(f.read())
                    
            # Read class files
            for file_path in Path(input_dir).glob('*.py'):
                if file_path.name not in ['main.py', '__init__.py'] and file_path.stem != '__init__':
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Remove imports (they're already in main.py)
                        lines = content.split('\n')
                        content_lines = []
                        for line in lines:
                            if not re.match(r'^(import |from )', line.strip()):
                                content_lines.append(line)
                        if content_lines:
                            self.all_content.append('\n'.join(content_lines))
                            
            # Write combined file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n\n'.join(self.all_content))
                
            return True, f"Successfully joined files into {output_file}"
        except Exception as e:
            return False, f"Error joining files: {str(e)}"

class FileSplitterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Python File Splitter & Joiner")
        self.root.geometry("600x500")
        
        self.file_manager = PythonFileManager()
        
        self.setup_ui()
        
    def setup_ui(self):
        # Create notebook for tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Split Tab
        split_frame = ttk.Frame(notebook)
        notebook.add(split_frame, text="Split File")
        
        # Join Tab
        join_frame = ttk.Frame(notebook)
        notebook.add(join_frame, text="Join Files")
        
        self.setup_split_tab(split_frame)
        self.setup_join_tab(join_frame)
        
    def setup_split_tab(self, parent):
        # Input file selection
        ttk.Label(parent, text="Select Python file to split:").pack(anchor='w', pady=(10, 5))
        
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill='x', pady=5)
        
        self.split_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.split_input_var).pack(side='left', fill='x', expand=True)
        ttk.Button(input_frame, text="Browse", command=self.browse_split_input).pack(side='left', padx=(5, 0))
        
        # Output directory selection
        ttk.Label(parent, text="Select output directory for split files:").pack(anchor='w', pady=(10, 5))
        
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill='x', pady=5)
        
        self.split_output_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.split_output_var).pack(side='left', fill='x', expand=True)
        ttk.Button(output_frame, text="Browse", command=self.browse_split_output).pack(side='left', padx=(5, 0))
        
        # Split button
        ttk.Button(parent, text="Split File", command=self.split_files).pack(pady=20)
        
        # Log area
        ttk.Label(parent, text="Log:").pack(anchor='w', pady=(10, 5))
        self.split_log = scrolledtext.ScrolledText(parent, height=10, width=70)
        self.split_log.pack(fill='both', expand=True)
        
    def setup_join_tab(self, parent):
        # Input directory selection
        ttk.Label(parent, text="Select directory with split files:").pack(anchor='w', pady=(10, 5))
        
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill='x', pady=5)
        
        self.join_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.join_input_var).pack(side='left', fill='x', expand=True)
        ttk.Button(input_frame, text="Browse", command=self.browse_join_input).pack(side='left', padx=(5, 0))
        
        # Output file selection
        ttk.Label(parent, text="Select output file for joined script:").pack(anchor='w', pady=(10, 5))
        
        output_frame = ttk.Frame(parent)
        output_frame.pack(fill='x', pady=5)
        
        self.join_output_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.join_output_var).pack(side='left', fill='x', expand=True)
        ttk.Button(output_frame, text="Browse", command=self.browse_join_output).pack(side='left', padx=(5, 0))
        
        # Join button
        ttk.Button(parent, text="Join Files", command=self.join_files).pack(pady=20)
        
        # Log area
        ttk.Label(parent, text="Log:").pack(anchor='w', pady=(10, 5))
        self.join_log = scrolledtext.ScrolledText(parent, height=10, width=70)
        self.join_log.pack(fill='both', expand=True)
        
    def browse_split_input(self):
        filename = filedialog.askopenfilename(
            title="Select Python file to split",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            self.split_input_var.set(filename)
            
    def browse_split_output(self):
        directory = filedialog.askdirectory(title="Select output directory for split files")
        if directory:
            self.split_output_var.set(directory)
            
    def browse_join_input(self):
        directory = filedialog.askdirectory(title="Select directory with split files")
        if directory:
            self.join_input_var.set(directory)
            
    def browse_join_output(self):
        filename = filedialog.asksaveasfilename(
            title="Save joined file as",
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if filename:
            self.join_output_var.set(filename)
            
    def split_files(self):
        input_file = self.split_input_var.get()
        output_dir = self.split_output_var.get()
        
        if not input_file or not output_dir:
            messagebox.showerror("Error", "Please select both input file and output directory")
            return
            
        if not os.path.exists(input_file):
            messagebox.showerror("Error", "Input file does not exist")
            return
            
        self.split_log.delete(1.0, tk.END)
        self.split_log.insert(tk.END, "Splitting file...\n")
        self.root.update()
        
        success, message = self.file_manager.split_file(input_file, output_dir)
        
        self.split_log.insert(tk.END, f"{message}\n")
        if success:
            self.split_log.insert(tk.END, f"Files created in: {output_dir}\n")
            # List created files
            if os.path.exists(output_dir):
                files = os.listdir(output_dir)
                for file in files:
                    if file.endswith('.py'):
                        self.split_log.insert(tk.END, f"  - {file}\n")
            messagebox.showinfo("Success", "File split successfully!")
        else:
            messagebox.showerror("Error", "Failed to split file")
            
    def join_files(self):
        input_dir = self.join_input_var.get()
        output_file = self.join_output_var.get()
        
        if not input_dir or not output_file:
            messagebox.showerror("Error", "Please select both input directory and output file")
            return
            
        if not os.path.exists(input_dir):
            messagebox.showerror("Error", "Input directory does not exist")
            return
            
        self.join_log.delete(1.0, tk.END)
        self.join_log.insert(tk.END, "Joining files...\n")
        self.root.update()
        
        success, message = self.file_manager.join_files(input_dir, output_file)
        
        self.join_log.insert(tk.END, f"{message}\n")
        if success:
            self.join_log.insert(tk.END, f"Output file: {output_file}\n")
            messagebox.showinfo("Success", "Files joined successfully!")
        else:
            messagebox.showerror("Error", "Failed to join files")

def main():
    root = tk.Tk()
    app = FileSplitterGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()