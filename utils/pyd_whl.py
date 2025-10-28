#!/usr/bin/env python3
"""
Complete Plugin Compiler with Dependency Management for Main App
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext, simpledialog
import os
import sys
import shutil
import threading
import subprocess
import importlib.util
import importlib.metadata
import ast
import re
import inspect
import zipfile
from pathlib import Path
from datetime import datetime

try:
    from setuptools import setup, Extension
    from Cython.Build import cythonize
    CYTHON_AVAILABLE = True
except ImportError:
    CYTHON_AVAILABLE = False

class DependencyManager:
    """Manages plugin dependencies and requirements with proper package mapping"""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.standard_libraries = self._get_standard_libraries()
        self.import_to_package_map = self._get_import_to_package_map()
    
    def _get_standard_libraries(self):
        """Get list of Python standard library modules"""
        import sys
        standard_libs = set(sys.builtin_module_names)
        
        # Add common standard library packages
        stdlib_packages = {
            'os', 'sys', 'json', 're', 'datetime', 'time', 'math', 'collections',
            'itertools', 'functools', 'threading', 'multiprocessing', 'subprocess',
            'pathlib', 'shutil', 'glob', 'tempfile', 'logging', 'argparse',
            'configparser', 'csv', 'html', 'xml', 'email', 'uuid', 'base64',
            'hashlib', 'ssl', 'socket', 'http', 'urllib', 'ftplib', 'smtplib',
            'sqlite3', 'zipfile', 'tarfile', 'gzip', 'pickle', 'shelve',
            'traceback', 'inspect', 'ast', 'typing', 'dataclasses', 'enum',
            'calendar', 'decimal', 'fractions', 'random', 'statistics',
            'doctest', 'unittest', 'pdb', 'profile', 'timeit', 'trace',
            'abc', 'ctypes', 'tkinter', 'winreg', 'msvcrt', 'winsound'
        }
        standard_libs.update(stdlib_packages)
        return standard_libs
    
    def _get_import_to_package_map(self):
        """Map import names to PyPI package names"""
        return {
            # Imaging
            'PIL': 'Pillow',
            'Image': 'Pillow',
            'ImageDraw': 'Pillow',
            'ImageFont': 'Pillow',
            
            # Windows API
            'win32con': 'pywin32',
            'win32gui': 'pywin32', 
            'win32process': 'pywin32',
            'win32ui': 'pywin32',
            'win32api': 'pywin32',
            'win32event': 'pywin32',
            'win32file': 'pywin32',
            'win32com': 'pywin32',
            
            # Common mappings
            'cv2': 'opencv-python',
            'yaml': 'PyYAML',
            'dateutil': 'python-dateutil',
            'sklearn': 'scikit-learn',
            'bs4': 'beautifulsoup4',
            'serial': 'pyserial',
            'pandas': 'pandas',
            'numpy': 'numpy',
            'requests': 'requests',
            'psutil': 'psutil',
            'pyautogui': 'pyautogui',
            'pytesseract': 'pytesseract',
            'mss': 'mss',
            'fuzzywuzzy': 'fuzzywuzzy',
            
            # Local/custom packages (skip these)
            'etail_plugin': None,
            'plugins': None,
            'local_module': None,
        }
    
    def log(self, message: str, level="INFO"):
        """Log message with callback to GUI"""
        if self.log_callback:
            self.log_callback(message, level)
    
    def is_standard_library(self, package_name: str) -> bool:
        """Check if a package is part of Python standard library"""
        base_package = package_name.split('.')[0]
        return base_package in self.standard_libraries
    
    def map_import_to_package(self, import_name: str):
        """Map import name to PyPI package name"""
        base_name = import_name.split('.')[0]
        
        # Check if it's a standard library
        if self.is_standard_library(base_name):
            return None, 'standard_library'
        
        # Check mapping
        if base_name in self.import_to_package_map:
            mapped_name = self.import_to_package_map[base_name]
            if mapped_name is None:
                return None, 'local_package'
            return mapped_name, 'mapped'
        
        # If not mapped, assume the import name is the package name
        return base_name, 'direct'

    def get_installed_version(self, package_name: str):
        """Get the installed version of a package"""
        try:
            return importlib.metadata.version(package_name)
        except:
            return "unknown"

    def parse_requirements_file(self, requirements_path: Path):
        """Parse requirements.txt file and return package list with version handling"""
        if not requirements_path.exists():
            self.log(f"Requirements file not found: {requirements_path}", "WARNING")
            return []
        
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                requirements = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if line and not line.startswith('#'):
                        package_name = self._extract_package_name(line)
                        
                        # Map to correct PyPI name
                        mapped_name, reason = self.map_import_to_package(package_name)
                        
                        if mapped_name is None:
                            self.log(f"Skipping {package_name} ({reason})", "INFO")
                            continue
                        
                        requirements.append({
                            'original': line,
                            'import_name': package_name,
                            'package': mapped_name,
                            'version_spec': line.replace(package_name, '').strip(),
                            'line_number': line_num,
                            'mapping_reason': reason
                        })
                return requirements
        except Exception as e:
            self.log(f"Error parsing requirements file: {e}", "ERROR")
            return []
    
    def _extract_package_name(self, requirement_line: str) -> str:
        """Extract package name from requirement line"""
        # Remove version specifiers and extras
        line = requirement_line.split(';')[0]  # Remove environment markers
        line = line.split('#')[0]  # Remove comments
        
        # Remove extras [optional]
        if '[' in line and ']' in line:
            line = line.split('[')[0] + line.split(']')[1]
        
        # Remove version specifiers
        for spec in ['==', '>=', '<=', '>', '<', '~=', '!=']:
            if spec in line:
                line = line.split(spec)[0]
        
        return line.strip()
    
    def analyze_imports(self, source_file: Path):
        """Analyze Python source file to detect imports, with proper package mapping"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST
            tree = ast.parse(content)
            
            import_names = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        import_names.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:  # Handle "from module import ..."
                        import_names.add(node.module.split('.')[0])
            
            # Map import names to packages
            packages = {}
            for import_name in import_names:
                package_name, reason = self.map_import_to_package(import_name)
                if package_name:
                    packages[package_name] = {
                        'import_name': import_name,
                        'reason': reason,
                        'installed_version': self.get_installed_version(package_name)
                    }
            
            return packages
            
        except Exception as e:
            self.log(f"Error analyzing imports: {e}", "ERROR")
            return {}
    
    def check_installed_packages(self, packages):
        """Check which packages are installed and their versions"""
        installed = []
        missing = []
        
        for package in packages:
            package_name = package['package']
            
            installed_version = self.get_installed_version(package_name)
            
            if installed_version != "unknown":
                installed.append({
                    'package': package_name,
                    'import_name': package.get('import_name', package_name),
                    'installed_version': installed_version,
                    'requirement': package['original'],
                    'satisfied': True,
                    'mapping_reason': package.get('mapping_reason', 'direct')
                })
            else:
                missing.append(package)
        
        return installed, missing
    
    def generate_requirements_file(self, source_file: Path, output_path: Path, include_versions=True):
        """Generate a requirements.txt file from source file imports with correct package names"""
        packages = self.analyze_imports(source_file)
        
        if not packages:
            self.log("No external imports found to generate requirements", "INFO")
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("# Auto-generated requirements file\n")
                f.write(f"# Source: {source_file.name}\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("# Standard library and local modules are automatically excluded\n\n")
                
                for package_name, info in sorted(packages.items()):
                    if include_versions and info.get('installed_version'):
                        f.write(f"{package_name}=={info['installed_version']}\n")
                    else:
                        f.write(f"{package_name}\n")
                
                # Add mapping comments
                f.write("\n# Import mappings:\n")
                for package_name, info in sorted(packages.items()):
                    if info['reason'] == 'mapped':
                        f.write(f"# {info['import_name']} -> {package_name}\n")
            
            self.log(f"Generated requirements file: {output_path}", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Error generating requirements file: {e}", "ERROR")
            return False
    
    def download_dependency_wheel(self, package, output_dir: Path) -> bool:
        """Download platform-specific wheel for a dependency"""
        package_name = package['package']
        
        try:
            self.log(f"Downloading wheel for: {package_name}", "INFO")
            
            # Build pip download command for specific platform
            cmd = [
                sys.executable, '-m', 'pip', 'download',
                '--only-binary=:all:',
                '--dest', str(output_dir),
                '--no-deps',
                '--platform', self.get_platform_tag(),
                '--python-version', f'{sys.version_info.major}{sys.version_info.minor}',
                package_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                # Find the downloaded wheel
                wheels = list(output_dir.glob(f"{package_name}*.whl"))
                if wheels:
                    self.log(f"✓ Downloaded wheel: {wheels[0].name}", "SUCCESS")
                    return True
                else:
                    # Try without platform restrictions
                    self.log(f"Trying universal wheel for: {package_name}", "INFO")
                    return self.download_universal_wheel(package_name, output_dir)
            else:
                self.log(f"Platform-specific wheel failed, trying universal: {package_name}", "WARNING")
                return self.download_universal_wheel(package_name, output_dir)
                
        except subprocess.TimeoutExpired:
            self.log(f"Timeout downloading: {package_name}", "WARNING")
            return False
        except Exception as e:
            self.log(f"Error downloading {package_name}: {e}", "WARNING")
            return False

    def download_universal_wheel(self, package_name: str, output_dir: Path) -> bool:
        """Download universal wheel or copy package if no wheel available"""
        try:
            # First try to download a universal wheel
            cmd = [
                sys.executable, '-m', 'pip', 'download',
                '--only-binary=:all:',
                '--dest', str(output_dir),
                '--no-deps',
                package_name
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                wheels = list(output_dir.glob(f"{package_name}*.whl"))
                if wheels:
                    self.log(f"✓ Downloaded universal wheel: {wheels[0].name}", "SUCCESS")
                    return True
            
            # If no wheel available, try to copy the package directly
            self.log(f"No wheel available for {package_name}, attempting to copy package...", "WARNING")
            return self.copy_package_directly(package_name, output_dir)
            
        except Exception as e:
            self.log(f"Error processing {package_name}: {e}", "WARNING")
            return False

    def copy_package_directly(self, package_name: str, output_dir: Path) -> bool:
        """Copy package directly from site-packages when no wheel is available"""
        try:
            # Create a packages directory for direct copies
            packages_dir = output_dir / "direct_packages"
            packages_dir.mkdir(exist_ok=True)
            
            # Try to import the package to find its location
            try:
                module = __import__(package_name)
                package_path = Path(module.__file__).parent if hasattr(module, '__file__') else None
            except:
                package_path = None
            
            # Try common installation locations
            if not package_path:
                for path in sys.path:
                    potential_path = Path(path) / package_name
                    if potential_path.exists():
                        package_path = potential_path
                        break
            
            if package_path and package_path.exists():
                dest_path = packages_dir / package_name
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                
                if package_path.is_dir():
                    shutil.copytree(package_path, dest_path, 
                                  ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.dist-info'))
                else:
                    shutil.copy2(package_path, dest_path)
                
                self.log(f"✓ Copied package directly: {package_name}", "SUCCESS")
                return True
            else:
                self.log(f"✗ Could not locate package: {package_name}", "WARNING")
                return False
                
        except Exception as e:
            self.log(f"Error copying package {package_name}: {e}", "WARNING")
            return False

    def get_platform_tag(self) -> str:
        """Get platform tag for wheel downloads"""
        if sys.platform == "win32":
            if sys.maxsize > 2**32:
                return "win_amd64"
            else:
                return "win32"
        elif sys.platform == "linux":
            return "manylinux2014_x86_64"
        elif sys.platform == "darwin":
            return "macosx_10_9_x86_64"
        else:
            return "any"

class PYDCompiler:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.dependency_manager = DependencyManager(log_callback)
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

    def verify_main_app_compatibility(self, source_file: Path) -> bool:
        """Verify the plugin matches the main app's ETailPlugin interface"""
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for main app's required elements
            required_elements = [
                r'class\s+\w+.*:',  # Class definition
                r'def\s+__init__.*app.*\)',  # Constructor with app parameter
                r'def\s+setup\s*\(',  # setup method
                r'def\s+teardown\s*\(',  # teardown method
                r'self\.name\s*=',  # name attribute
                r'self\.version\s*=',  # version attribute
                r'self\.description\s*='  # description attribute
            ]
            
            missing_elements = []
            for i, element in enumerate(required_elements):
                if not re.search(element, content):
                    element_names = [
                        "Class definition",
                        "__init__(self, app) method", 
                        "setup() method",
                        "teardown() method",
                        "self.name attribute",
                        "self.version attribute", 
                        "self.description attribute"
                    ]
                    missing_elements.append(element_names[i])
            
            if missing_elements:
                self.log("Plugin missing required elements for main app:", "WARNING")
                for missing in missing_elements:
                    self.log(f"  ✗ {missing}", "WARNING")
                return False
            
            self.log("✓ Plugin compatible with main app interface", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Error verifying main app compatibility: {e}", "ERROR")
            return False

    def create_plugin_template(self, output_path: Path, plugin_name: str):
        """Create a plugin template that matches the main app's ETailPlugin interface"""
        class_name = ''.join(word.capitalize() for word in plugin_name.split('_'))
        plugin_display_name = plugin_name.replace('_', ' ').title()
        
        template_content = f'''
"""
{plugin_display_name} - Auto-generated plugin template
"""

class {class_name}:
    """Plugin implementation for main app"""
    
    def __init__(self, app):
        self.app = app
        self.name = "{plugin_display_name}"
        self.version = "1.0.0"
        self.description = "Auto-generated plugin"
        self.enabled = False
        
        # Plugin-specific initialization
        self.filters = {{}}  # Store registered filters
    
    def setup(self):
        """Setup the plugin - called when plugin is loaded"""
        try:
            print(f"[{{self.name}}] Setting up plugin")
            
            # Example: Register a filter pattern
            filter_id = "example_pattern"
            filter_pattern = r"\\d+\\s+.*"  # Example regex pattern
            
            # Register with main app's filter system
            success = self.app.register_plugin_filter(
                self.name, 
                filter_pattern, 
                filter_id, 
                self.handle_filter_match
            )
            
            if success:
                self.filters[filter_id] = filter_pattern
                print(f"[{{self.name}}] Registered filter: {{filter_id}}")
            else:
                print(f"[{{self.name}}] Failed to register filter")
            
            return True
            
        except Exception as e:
            print(f"[{{self.name}}] Setup failed: {{e}}")
            return False
    
    def teardown(self):
        """Cleanup when plugin is unloaded"""
        try:
            print(f"[{{self.name}}] Tearing down plugin")
            
            # Remove all registered filters
            for filter_id in list(self.filters.keys()):
                self.app.remove_plugin_filter(self.name, filter_id)
                print(f"[{{self.name}}] Removed filter: {{filter_id}}")
            
            self.filters.clear()
            return True
            
        except Exception as e:
            print(f"[{{self.name}}] Teardown failed: {{e}}")
            return False
    
    def handle_filter_match(self, filter_id, matches, line):
        """Callback for when a filter pattern matches"""
        try:
            print(f"[{{self.name}}] Filter {{filter_id}} matched: {{matches}}")
            print(f"[{{self.name}}] Line: {{line}}")
            
            # Process the match data here
            # You can call other methods or store data
            
        except Exception as e:
            print(f"[{{self.name}}] Error handling filter match: {{e}}")
    
    def on_regex_data(self, match_data):
        """Handle regex match data from main app's broadcast system"""
        try:
            print(f"[{{self.name}}] Received regex data:")
            print(f"  Fields: {{match_data.get('fields', [])}}")
            print(f"  Pattern: {{match_data.get('pattern', '')}}")
            print(f"  Line: {{match_data.get('line', '')}}")
            
            # Process the match data as needed
            # This method is called by main app's broadcast_regex_match
            
        except Exception as e:
            print(f"[{{self.name}}] Error processing regex data: {{e}}")

    # Add any additional methods your plugin needs
    def custom_method(self, data):
        """Example custom method that can be called via call_plugin_method"""
        print(f"[{{self.name}}] Custom method called with: {{data}}")
        return {{"status": "processed", "original_data": data}}
'''
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template_content)
        
        self.log(f"Created main app compatible template: {output_path}", "SUCCESS")

class PYDCompilerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PYD Compiler GUI - With Dependency Management")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Variables
        self.source_dir = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "compiled_plugins"))
        self.requirements_file = tk.StringVar()
        self.is_processing = False
        self.compiler = None
        self.current_file = None
        
        # Dependency management variables
        self.auto_analyze_imports = tk.BooleanVar(value=True)
        self.download_wheels = tk.BooleanVar(value=False)
        self.include_dependencies = tk.BooleanVar(value=True)
        
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
        style.configure("Dependency.TFrame", background="#f0f8ff")
        
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
        title_label = ttk.Label(main_frame, text="PYD Compiler with Dependency Management", 
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
        
        # Requirements file selection
        ttk.Label(main_frame, text="Requirements File:").grid(row=3, column=0, sticky=tk.W, pady=5)
        req_entry = ttk.Entry(main_frame, textvariable=self.requirements_file, width=60)
        req_entry.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=(5, 5))
        req_button_frame = ttk.Frame(main_frame)
        req_button_frame.grid(row=3, column=2, pady=5)
        ttk.Button(req_button_frame, text="Browse", 
                  command=self.browse_requirements_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(req_button_frame, text="Auto Generate", 
                  command=self.auto_generate_requirements).pack(side=tk.LEFT, padx=2)
        
        # Dependency management frame
        dep_frame = ttk.LabelFrame(main_frame, text="Dependency Management", padding="10")
        dep_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        dep_frame.columnconfigure(0, weight=1)
        
        # Dependency options
        dep_options_frame = ttk.Frame(dep_frame)
        dep_options_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Checkbutton(dep_options_frame, text="Auto-analyze imports", 
                       variable=self.auto_analyze_imports).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(dep_options_frame, text="Download dependency wheels", 
                       variable=self.download_wheels).pack(side=tk.LEFT, padx=10)
        ttk.Checkbutton(dep_options_frame, text="Include dependencies in output", 
                       variable=self.include_dependencies).pack(side=tk.LEFT, padx=10)
        
        # Dependency analysis buttons
        dep_buttons_frame = ttk.Frame(dep_frame)
        dep_buttons_frame.grid(row=1, column=0, sticky=tk.W, pady=5)
        
        ttk.Button(dep_buttons_frame, text="Analyze Dependencies", 
                  command=self.analyze_dependencies).pack(side=tk.LEFT, padx=5)
        ttk.Button(dep_buttons_frame, text="Check Installed Packages", 
                  command=self.check_installed_packages).pack(side=tk.LEFT, padx=5)
        
        # File list frame
        list_frame = ttk.LabelFrame(main_frame, text="Python Files", padding="5")
        list_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
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
        ttk.Button(list_buttons_frame, text="Check Main App Compatibility", 
                  command=self.verify_main_app_compatibility).pack(side=tk.LEFT, padx=2)
        ttk.Button(list_buttons_frame, text="Create Main App Template", 
                  command=self.create_main_app_template).pack(side=tk.LEFT, padx=2)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=3, pady=15)
        
        # Compile button
        self.compile_btn = tk.Button(
            button_frame, 
            text="🚀 COMPILE WITH DEPENDENCIES", 
            command=self.compile_selected_file,
            bg="#4CAF50", 
            fg="white",
            font=("Arial", 12, "bold"),
            height=2,
            width=30
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
        progress_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        progress_frame.columnconfigure(0, weight=1)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        self.status_var = tk.StringVar(value="Ready to compile")
        self.status_label = ttk.Label(progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        
        # Log area
        log_frame = ttk.LabelFrame(main_frame, text="Compilation Log", padding="5")
        log_frame.grid(row=8, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(10, 0))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure tags for colored logging
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("SUCCESS", foreground="green")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        
        # Configure grid weights for main frame
        main_frame.rowconfigure(8, weight=1)
        
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
    
    def browse_requirements_file(self):
        """Browse for requirements file"""
        filename = filedialog.askopenfilename(
            title="Select Requirements File",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.requirements_file.set(filename)
    
    def auto_generate_requirements(self):
        """Auto-generate requirements file from selected plugin"""
        source_file = self.get_selected_file()
        if not source_file:
            messagebox.showwarning("Warning", "Please select a Python file first.")
            return
        
        # Suggest output path for requirements file
        requirements_path = source_file.parent / f"{source_file.stem}_requirements.txt"
        
        # Ask user for confirmation
        if messagebox.askyesno("Generate Requirements", 
                             f"Generate requirements file at:\n{requirements_path}"):
            self.compiler = PYDCompiler(log_callback=self.log_message)
            success = self.compiler.dependency_manager.generate_requirements_file(
                source_file, requirements_path
            )
            if success:
                self.requirements_file.set(str(requirements_path))
    
    def analyze_dependencies(self):
        """Analyze dependencies for selected file"""
        source_file = self.get_selected_file()
        if not source_file:
            messagebox.showwarning("Warning", "Please select a Python file first.")
            return
        
        self.log_message(f"Analyzing dependencies for: {source_file.name}", "INFO")
        
        if not self.compiler:
            self.compiler = PYDCompiler(log_callback=self.log_message)
        
        # Analyze imports from source
        packages = self.compiler.dependency_manager.analyze_imports(source_file)
        
        if packages:
            self.log_message("Detected imports:", "INFO")
            for pkg_name, info in packages.items():
                self.log_message(f"  • {info['import_name']} -> {pkg_name} ({info['reason']})", "INFO")
        else:
            self.log_message("No external imports detected", "INFO")
        
        # Also check requirements file if specified
        if self.requirements_file.get():
            req_path = Path(self.requirements_file.get())
            requirements = self.compiler.dependency_manager.parse_requirements_file(req_path)
            
            if requirements:
                self.log_message("Requirements file packages:", "INFO")
                for req in requirements:
                    self.log_message(f"  • {req['package']} {req['version_spec']}", "INFO")
    
    def check_installed_packages(self):
        """Check which required packages are installed"""
        if not self.requirements_file.get():
            messagebox.showwarning("Warning", "Please select a requirements file first.")
            return
        
        req_path = Path(self.requirements_file.get())
        
        if not self.compiler:
            self.compiler = PYDCompiler(log_callback=self.log_message)
        
        requirements = self.compiler.dependency_manager.parse_requirements_file(req_path)
        
        if not requirements:
            self.log_message("No requirements found to check", "WARNING")
            return
        
        self.log_message("Checking installed packages...", "INFO")
        
        installed, missing = self.compiler.dependency_manager.check_installed_packages(requirements)
        
        if installed:
            self.log_message(f"Found {len(installed)} installed packages", "SUCCESS")
            for pkg in installed:
                self.log_message(f"  ✓ {pkg['package']} {pkg['installed_version']}", "SUCCESS")
        
        if missing:
            self.log_message(f"Found {len(missing)} missing packages", "WARNING")
            for pkg in missing:
                self.log_message(f"  ✗ {pkg['package']} {pkg.get('version_spec', '')}", "WARNING")
    
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
        
        if not self.compiler:
            self.compiler = PYDCompiler(log_callback=self.log_message)
        
        checks = self.compiler.check_plugin_interface(source_file)
        
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
    
    def verify_main_app_compatibility(self):
        """Verify selected plugin matches main app interface"""
        source_file = self.get_selected_file()
        if not source_file:
            return
        
        if not self.compiler:
            self.compiler = PYDCompiler(log_callback=self.log_message)
        
        if self.compiler.verify_main_app_compatibility(source_file):
            messagebox.showinfo("Compatibility Check", 
                              "Plugin is compatible with main app interface!")
        else:
            messagebox.showwarning("Compatibility Check", 
                                 "Plugin is NOT compatible with main app!\n\n" +
                                 "Required:\n" +
                                 "- __init__(self, app) method\n" +
                                 "- setup() method\n" + 
                                 "- teardown() method\n" +
                                 "- self.name, version, description attributes")
    
    def create_main_app_template(self):
        """Create a plugin template for the main app"""
        plugin_name = simpledialog.askstring("Create Main App Plugin", 
                                        "Enter plugin name (snake_case):")
        if plugin_name:
            output_path = Path(self.source_dir.get()) / f"{plugin_name}.py"
            self.compiler = PYDCompiler(log_callback=self.log_message)
            self.compiler.create_plugin_template(output_path, plugin_name)
            self.refresh_file_list()
            messagebox.showinfo("Success", 
                              f"Main app template created: {output_path.name}\n\n" +
                              "This plugin will work with your main app's plugin system.")
    
    def compile_selected_file(self):
        """Compile the selected file to PYD with dependency management"""
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
        thread = threading.Thread(target=self.run_compilation_with_deps, args=(source_file,))
        thread.daemon = True
        thread.start()
        
        # Start progress monitoring
        self.monitor_progress()
    
    def run_compilation_with_deps(self, source_file: Path):
        """Run compilation with dependency bundling"""
        try:
            self.compiler = PYDCompiler(log_callback=self.log_message)
            
            output_dir = Path(self.output_dir.get())
            
            # Step 1: Compile the plugin
            self.log_message("Step 1: Compiling plugin...", "INFO")
            self.status_var.set("Compiling plugin...")
            success = self.compiler.compile_to_pyd(source_file, output_dir)
            
            if not success:
                self.status_var.set("Compilation failed")
                return
            
            # Step 2: Bundle dependencies
            if self.include_dependencies.get():
                self.log_message("Step 2: Bundling dependencies...", "INFO")
                self.status_var.set("Bundling dependencies...")
                self.handle_dependencies(source_file, output_dir)
            
            self.status_var.set("Deployment package created successfully!")
            self.log_message("Plugin compilation and dependency bundling finished!", "SUCCESS")
            
            # Show success message with package info
            deployment_dir = output_dir / "deployment_package"
            bundled_items = []
            if deployment_dir.exists():
                plugins_dir = deployment_dir / "plugins"
                if plugins_dir.exists():
                    bundled_items = [item.name for item in plugins_dir.iterdir()]
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Deployment Package Ready", 
                f"Plugin deployment package created!\n\n"
                f"Output: {output_dir}\n"
                f"Bundled: {len(bundled_items)} items\n"
                f"See deployment_package/ folder for complete setup."
            ))
            
        except Exception as e:
            self.status_var.set("Compilation failed with error")
            self.log_message(f"Compilation error: {str(e)}", "ERROR")
        
        finally:
            self.is_processing = False
            self.root.after(0, lambda: self.set_ui_state(True))
    
    def handle_dependencies(self, source_file: Path, output_dir: Path):
        """Handle plugin dependencies for compiled executable deployment"""
        deployment_dir = output_dir / "deployment_package"
        deployment_dir.mkdir(exist_ok=True)
        
        requirements = []
        
        # Get requirements from file if specified
        if self.requirements_file.get():
            req_path = Path(self.requirements_file.get())
            requirements = self.compiler.dependency_manager.parse_requirements_file(req_path)
            self.log_message(f"Loaded {len(requirements)} requirements from file", "INFO")
        
        # Auto-analyze imports if enabled and no requirements file
        elif self.auto_analyze_imports.get():
            self.log_message("Auto-analyzing imports...", "INFO")
            packages = self.compiler.dependency_manager.analyze_imports(source_file)
            requirements = [{
                'original': pkg_name,
                'package': pkg_name,
                'import_name': info['import_name'],
                'mapping_reason': info['reason']
            } for pkg_name, info in packages.items()]
            self.log_message(f"Found {len(requirements)} imports to analyze", "INFO")
        
        if not requirements:
            self.log_message("No dependencies to process", "INFO")
            return
        
        # Check which packages are installed
        installed, missing = self.compiler.dependency_manager.check_installed_packages(requirements)
        
        if installed:
            self.log_message(f"Found {len(installed)} installed packages", "SUCCESS")
        
        if missing:
            self.log_message(f"Found {len(missing)} missing packages", "WARNING")
        
        # BUNDLE FOR COMPILED EXECUTABLE
        if self.include_dependencies.get():
            self.bundle_for_compiled_executable(installed, deployment_dir, source_file)
        
        # Generate deployment files
        self.generate_executable_deployment_files(requirements, deployment_dir, source_file)
    
    def bundle_for_compiled_executable(self, installed_packages, deployment_dir: Path, source_file: Path):
        """Bundle dependencies in a way that works with compiled Python executables"""
        self.log_message("Creating deployment package for compiled executable...", "INFO")
        
        # Create directory structure
        plugin_dir = deployment_dir / "plugins"
        plugin_dir.mkdir(exist_ok=True)
        
        dependency_dir = deployment_dir / "dependencies"
        dependency_dir.mkdir(exist_ok=True)
        
        bundled_count = 0
        
        # Copy the compiled plugin
        plugin_files = list(Path(self.output_dir.get()).glob(f"{source_file.stem}*.pyd"))
        for plugin_file in plugin_files:
            # Use simple name for main app compatibility
            simple_name = f"{source_file.stem}.pyd"
            shutil.copy2(plugin_file, plugin_dir / simple_name)
            self.log_message(f"✓ Bundled plugin: {simple_name}", "SUCCESS")
        
        # Bundle dependency wheels
        if self.download_wheels.get():
            for package in installed_packages:
                package_name = package['package']
                
                # Skip standard libraries and local packages
                if package.get('mapping_reason') in ['standard_library', 'local_package']:
                    self.log_message(f"Skipping {package_name} ({package.get('mapping_reason')})", "INFO")
                    continue
                
                try:
                    # Download wheel for this package
                    if self.compiler.dependency_manager.download_dependency_wheel(package, dependency_dir):
                        bundled_count += 1
                    else:
                        self.log_message(f"✗ Could not get wheel for: {package_name}", "WARNING")
                        
                except Exception as e:
                    self.log_message(f"✗ Error processing {package_name}: {e}", "WARNING")
        
        self.log_message(f"Deployment package created: {bundled_count} dependency wheels + plugin", "SUCCESS")
    
    def generate_executable_deployment_files(self, requirements, deployment_dir: Path, source_file: Path):
        """Generate files specifically for compiled executable deployment"""
        # Generate requirements file
        req_output = deployment_dir / "requirements.txt"
        try:
            with open(req_output, 'w', encoding='utf-8') as f:
                f.write(f"# Requirements for {source_file.stem}\n")
                f.write(f"# Main app should install these using the provided installer\n\n")
                
                for req in requirements:
                    if req.get('mapping_reason') not in ['standard_library', 'local_package']:
                        f.write(f"{req['package']}\n")
            
            self.log_message(f"Generated requirements: {req_output}", "SUCCESS")
        except Exception as e:
            self.log_message(f"Error generating requirements: {e}", "ERROR")
        
        # Generate main app integration guide
        self.create_main_app_integration_guide(deployment_dir, source_file)
    
    def create_main_app_integration_guide(self, deployment_dir: Path, source_file: Path):
        """Create guide for integrating with the main compiled executable"""
        guide_content = f'''
MAIN APP INTEGRATION GUIDE
==========================

For: {source_file.stem} Plugin

DEPLOYMENT STRUCTURE:
- deployment_package/
  ├── plugins/              # Contains your compiled .pyd file
  ├── dependencies/         # Contains .whl files for installation
  └── requirements.txt     # List of required packages

INTEGRATION STEPS:
1. Copy the entire "{deployment_dir.name}" folder to your main app
2. Ensure your main app's plugin manager can load .pyd files
3. The plugin should be automatically discovered

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
'''
        guide_path = deployment_dir / "MAIN_APP_INTEGRATION_GUIDE.txt"
        try:
            with open(guide_path, 'w', encoding='utf-8') as f:
                f.write(guide_content)
            self.log_message(f"Created integration guide: {guide_path}", "SUCCESS")
        except Exception as e:
            self.log_message(f"Error creating integration guide: {e}", "ERROR")
    
    def set_ui_state(self, enabled: bool):
        """Enable/disable UI controls"""
        state = "normal" if enabled else "disabled"
        self.compile_btn.config(state=state)
        self.open_output_btn.config(state=state)
        self.cancel_btn.config(state="normal" if not enabled else "disabled")
    
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