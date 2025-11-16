#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import json
import os
import subprocess
import sys
import threading
from pathlib import Path
import psutil
import time

class ETailMonitorController:
    def __init__(self, root):
        self.root = root
        self.root.title("ETail Monitor Controller")
        self.root.geometry("1200x800")
        
        # Application data directory
        self.app_dir = Path.home() / ".config" / "etail-monitor-controller"
        self.app_dir.mkdir(parents=True, exist_ok=True)
        
        # Config files
        self.config_file = self.app_dir / "managed_monitors.json"
        self.status_file = self.app_dir / "status.json"
        
        self.config = self.load_config()
        
        self.setup_gui()
        self.refresh_all()
        
    def setup_gui(self):
        """Setup the main GUI interface"""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Managed Services tab
        self.services_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.services_frame, text="Managed Services")
        self.setup_services_tab()
        
        # Managed Processes tab  
        self.processes_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.processes_frame, text="Managed Processes")
        self.setup_processes_tab()
        
        # System View tab (read-only)
        self.system_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.system_frame, text="System View")
        self.setup_system_tab()
        
        # Process Tree tab
        self.tree_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tree_frame, text="Process Trees")
        self.setup_tree_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_var.set("Ready")

    def setup_tree_tab(self):
        """Setup process tree visualization tab"""
        ttk.Label(self.tree_frame, text="ETail Process Trees", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Treeview for process hierarchy
        columns = ('pid', 'ppid', 'name', 'user', 'command', 'tree_id')
        self.tree_tree = ttk.Treeview(self.tree_frame, columns=columns, show='headings')
        self.tree_tree.heading('pid', text='PID')
        self.tree_tree.heading('ppid', text='Parent PID')
        self.tree_tree.heading('name', text='Name')
        self.tree_tree.heading('user', text='User')
        self.tree_tree.heading('command', text='Command')
        self.tree_tree.heading('tree_id', text='Tree ID')
        
        self.tree_tree.column('pid', width=80)
        self.tree_tree.column('ppid', width=80)
        self.tree_tree.column('name', width=150)
        self.tree_tree.column('user', width=100)
        self.tree_tree.column('command', width=400)
        self.tree_tree.column('tree_id', width=100)
        
        self.tree_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Controls
        btn_frame = ttk.Frame(self.tree_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Refresh Trees", command=self.refresh_process_trees).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Kill Tree", command=self.kill_process_tree).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Show Details", command=self.show_tree_details).pack(side=tk.LEFT, padx=2)
        
        # Info label
        info_label = ttk.Label(self.tree_frame, 
                              text="Shows process trees for ETail applications. Red rows indicate potential duplicates.",
                              foreground="gray")
        info_label.pack(pady=5)

    def refresh_process_trees(self):
        """Refresh process tree view"""
        for item in self.tree_tree.get_children():
            self.tree_tree.delete(item)
            
        # Get all ETail process trees
        trees = self.get_etail_process_trees()
        
        for tree_id, processes in trees.items():
            # Check for duplicates within the same tree
            commands = [p['command'] for p in processes]
            has_duplicates = len(commands) != len(set(commands))
            
            for proc in processes:
                tags = ()
                if has_duplicates:
                    tags = ('duplicate',)
                    
                self.tree_tree.insert('', 'end', values=(
                    proc['pid'],
                    proc['ppid'],
                    proc['name'],
                    proc['user'],
                    proc['command'][:200] + "..." if len(proc['command']) > 200 else proc['command'],
                    tree_id
                ), tags=tags)
        
        # Configure tag for duplicates
        self.tree_tree.tag_configure('duplicate', background='#ffdddd')

    def get_etail_process_trees(self):
        """Get all ETail processes organized by process tree"""
        etail_processes = self.find_etail_processes_detailed()
        trees = {}
        
        for proc in etail_processes:
            # Find the root of the process tree
            root_pid = self.find_process_tree_root(proc['pid'])
            
            if root_pid not in trees:
                trees[root_pid] = []
            
            trees[root_pid].append(proc)
        
        return trees
 
    def find_process_tree_root(self, pid):
        """Find the root PID of a process tree"""
        try:
            current_pid = pid
            while True:
                proc = psutil.Process(current_pid)
                parent = proc.parent()
                if parent is None or parent.pid == 1:  # Reached init or no parent
                    return current_pid
                current_pid = parent.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return pid
 
    def find_etail_processes_detailed(self):
        """Find all ETail-related processes with detailed information"""
        processes = []
        etail_patterns = ["et_hardware_mon_linux", "LinuxLogMonitor"]
        
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username', 'cmdline', 'create_time']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                for pattern in etail_patterns:
                    if pattern in cmdline:
                        processes.append({
                            "pid": proc.info['pid'],
                            "ppid": proc.info['ppid'],
                            "name": pattern,
                            "user": proc.info['username'],
                            "command": cmdline,
                            "create_time": proc.info['create_time']
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return processes
    
    def kill_process_tree(self):
        """Kill an entire process tree"""
        selected = self.tree_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process tree to kill")
            return
        
        item = self.tree_tree.item(selected[0])
        tree_id = item['values'][5]  # tree_id column
        pid = item['values'][0]  # pid column
        
        if messagebox.askyesno("Confirm", f"Kill entire process tree starting from PID {pid}?\nThis will terminate all related processes."):
            try:
                self.kill_process_tree_recursive(int(pid))
                self.refresh_process_trees()
                self.refresh_system_view()
                self.status_var.set(f"Killed process tree: {tree_id}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to kill process tree: {e}")
    
    def kill_process_tree_recursive(self, pid):
        """Recursively kill a process tree"""
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            
            # Kill children first
            for child in children:
                try:
                    child.terminate()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # Kill parent
            try:
                parent.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            
            # Wait for processes to terminate
            gone, alive = psutil.wait_procs(children + [parent], timeout=5)
            
            # Force kill any remaining processes
            for p in alive:
                try:
                    p.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                    
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            raise Exception(f"Cannot access process {pid}: {e}")
    
    def show_tree_details(self):
        """Show detailed information about a process tree"""
        selected = self.tree_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process tree")
            return
        
        item = self.tree_tree.item(selected[0])
        tree_id = item['values'][5]
        
        # Get tree details
        trees = self.get_etail_process_trees()
        if tree_id in trees:
            processes = trees[tree_id]
            
            details = f"Process Tree {tree_id} - {len(processes)} processes:\n\n"
            for proc in processes:
                details += f"PID: {proc['pid']} (Parent: {proc['ppid']})\n"
                details += f"User: {proc['user']}\n"
                details += f"Command: {proc['command']}\n"
                details += f"Created: {proc['create_time']}\n"
                details += "-" * 50 + "\n"
            
            # Show in a scrollable text dialog
            self.show_scrollable_dialog("Process Tree Details", details)
  
    def show_scrollable_dialog(self, title, content):
        """Show content in a scrollable dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.geometry("800x600")
        dialog.transient(self.root)
        
        text_frame = ttk.Frame(dialog)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        text_widget.insert('1.0', content)
        text_widget.config(state=tk.DISABLED)
        
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    # Enhanced process management with duplicate detection
    def is_duplicate_process_running(self, process_config):
        """Check if a process with identical parameters is already running"""
        expected_command = self.get_process_command(process_config)
        etail_processes = self.find_etail_processes_detailed()
        
        for proc in etail_processes:
            # Normalize commands for comparison
            current_cmd = self.normalize_command(proc['command'])
            expected_cmd = self.normalize_command(expected_command)
            
            if current_cmd == expected_cmd:
                return True, proc['pid']
        
        return False, None


    def normalize_command(self, command):
        """Normalize command for comparison (remove extra spaces, sort parameters)"""
        # Split command into parts
        parts = command.split()
        if not parts:
            return command
        
        # The executable is the first part
        executable = parts[0]
        
        # Parse parameters
        params = []
        i = 1
        while i < len(parts):
            if parts[i].startswith('--'):
                param = parts[i]
                if i + 1 < len(parts) and not parts[i + 1].startswith('--'):
                    params.append(f"{param}={parts[i + 1]}")
                    i += 2
                else:
                    params.append(param)
                    i += 1
            else:
                i += 1
        
        # Sort parameters for consistent comparison
        params.sort()
        
        return executable + ' ' + ' '.join(params)

    def setup_services_tab(self):
        """Setup managed services tab"""
        # Title
        ttk.Label(self.services_frame, text="ETail Managed Services", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Treeview for managed services
        columns = ('name', 'status', 'pid', 'service_name')
        self.services_tree = ttk.Treeview(self.services_frame, columns=columns, show='headings')
        self.services_tree.heading('name', text='Display Name')
        self.services_tree.heading('status', text='Status')
        self.services_tree.heading('pid', text='PID')
        self.services_tree.heading('service_name', text='Service Name')
        
        self.services_tree.column('name', width=200)
        self.services_tree.column('status', width=100)
        self.services_tree.column('pid', width=80)
        self.services_tree.column('service_name', width=150)
        
        self.services_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Service controls
        btn_frame = ttk.Frame(self.services_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Add Service", command=self.add_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Edit", command=self.edit_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Start", command=self.start_managed_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Stop", command=self.stop_managed_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Restart", command=self.restart_managed_service).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=2)
        
    def setup_processes_tab(self):
        """Setup managed processes tab"""
        ttk.Label(self.processes_frame, text="ETail Managed Processes", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Treeview for managed processes
        columns = ('name', 'status', 'pid', 'command')
        self.processes_tree = ttk.Treeview(self.processes_frame, columns=columns, show='headings')
        self.processes_tree.heading('name', text='Display Name')
        self.processes_tree.heading('status', text='Status')
        self.processes_tree.heading('pid', text='PID')
        self.processes_tree.heading('command', text='Command')
        
        self.processes_tree.column('name', width=200)
        self.processes_tree.column('status', width=100)
        self.processes_tree.column('pid', width=80)
        self.processes_tree.column('command', width=300)
        
        self.processes_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Process controls
        btn_frame = ttk.Frame(self.processes_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Add Process", command=self.add_process).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Edit", command=self.edit_process).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Delete", command=self.delete_process).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Start", command=self.start_managed_process).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Stop", command=self.stop_managed_process).pack(side=tk.LEFT, padx=2)
        ttk.Button(btn_frame, text="Refresh", command=self.refresh_all).pack(side=tk.RIGHT, padx=2)
        
    def setup_system_tab(self):
        """Setup system view tab (read-only)"""
        ttk.Label(self.system_frame, text="System Overview (Read-Only)", 
                 font=('Arial', 12, 'bold')).pack(anchor=tk.W, pady=5)
        
        # Treeview for system processes
        columns = ('name', 'status', 'pid', 'user', 'command')
        self.system_tree = ttk.Treeview(self.system_frame, columns=columns, show='headings')
        self.system_tree.heading('name', text='Process Name')
        self.system_tree.heading('status', text='Status')
        self.system_tree.heading('pid', text='PID')
        self.system_tree.heading('user', text='User')
        self.system_tree.heading('command', text='Command')
        
        self.system_tree.column('name', width=150)
        self.system_tree.column('status', width=80)
        self.system_tree.column('pid', width=80)
        self.system_tree.column('user', width=100)
        self.system_tree.column('command', width=300)
        
        self.system_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Info label
        info_label = ttk.Label(self.system_frame, 
                              text="This tab shows all ETail-related processes on the system. These are read-only and cannot be modified.",
                              foreground="gray")
        info_label.pack(pady=5)
        
        ttk.Button(self.system_frame, text="Refresh", command=self.refresh_system_view).pack(pady=5)
        
    def load_config(self):
        """Load configuration from file"""
        default_config = {
            "managed_services": [],
            "managed_processes": []
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading config: {e}")
                
        return default_config
    
    def save_config(self):
        """Save configuration to file - FIXED VERSION"""
        try:
            # Ensure directory exists
            self.app_dir.mkdir(parents=True, exist_ok=True)
            
            # Save main config
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            
            # Update status file
            self.save_status_file()
            
            print(f"DEBUG: Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to save config: {e}"
            print(f"DEBUG: {error_msg}")
            return False

    def save_status_file(self):
        """Save current status for widget communication - FIXED VERSION"""
        try:
            status_data = {
                "last_update": time.strftime('%Y-%m-%d %H:%M:%S'),
                "managed_services": [],
                "managed_processes": []
            }
            
            # Add managed services status
            for service in self.config.get("managed_services", []):
                status = self.get_service_status(service.get("service_name", ""))
                status_data["managed_services"].append({
                    "name": service.get("name", ""),
                    "service_name": service.get("service_name", ""),
                    "status": status,
                    "pid": self.get_service_pid(service.get("service_name", ""))
                })
            
            # Add managed processes status
            for process in self.config.get("managed_processes", []):
                pid = process.get("pid")
                status = "running" if pid and self.is_pid_running(pid) else "stopped"
                status_data["managed_processes"].append({
                    "name": process.get("name", ""),
                    "pid": pid,
                    "status": status
                })
            
            with open(self.status_file, 'w') as f:
                json.dump(status_data, f, indent=2, ensure_ascii=False)
                
            print(f"DEBUG: Status file saved to {self.status_file}")
            
        except Exception as e:
            print(f"DEBUG: Could not save status file: {e}")
    

    def refresh_all(self):
        """Refresh all views"""
        self.refresh_services_view()
        self.refresh_processes_view()
        self.refresh_system_view()
        self.save_status_file()
        self.status_var.set("Status updated")
    
    def refresh_services_view(self):
        """Refresh managed services view"""
        for item in self.services_tree.get_children():
            self.services_tree.delete(item)
            
        for service in self.config.get("managed_services", []):
            status = self.get_service_status(service.get("service_name", ""))
            pid = self.get_service_pid(service.get("service_name", ""))
            
            self.services_tree.insert('', 'end', values=(
                service.get("name", "Unknown"),
                status,
                pid or "N/A",
                service.get("service_name", "")
            ))
    
    def refresh_processes_view(self):
        """Refresh managed processes view"""
        for item in self.processes_tree.get_children():
            self.processes_tree.delete(item)
            
        for process in self.config.get("managed_processes", []):
            pid = process.get("pid")
            status = "running" if pid and self.is_pid_running(pid) else "stopped"
            
            self.processes_tree.insert('', 'end', values=(
                process.get("name", "Unknown"),
                status,
                pid or "N/A",
                self.get_process_command(process)
            ))
    
    # Enhanced system view with tree information
    def refresh_system_view(self):
        """Refresh system view with tree awareness"""
        for item in self.system_tree.get_children():
            self.system_tree.delete(item)
        
        etail_processes = self.find_etail_processes_detailed()
        trees = self.get_etail_process_trees()
        
        for proc in etail_processes:
            # Find which tree this process belongs to
            tree_id = self.find_process_tree_root(proc['pid'])
            tree_size = len(trees.get(tree_id, []))
            
            self.system_tree.insert('', 'end', values=(
                proc["name"],
                "running",
                proc["pid"],
                proc["user"],
                f"{proc['command'][:100]}..." if len(proc['command']) > 100 else proc['command'],
                f"Tree:{tree_id}({tree_size})"
            ))

    def find_etail_processes(self):
        """Find all ETail-related processes on the system"""
        processes = []
        etail_patterns = ["et_hardware_mon_linux", "LinuxLogMonitor"]
        
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
            try:
                cmdline = ' '.join(proc.info['cmdline'] or [])
                for pattern in etail_patterns:
                    if pattern in cmdline:
                        processes.append({
                            "name": pattern,
                            "status": "running",
                            "pid": proc.info['pid'],
                            "user": proc.info['username'],
                            "command": cmdline[:100] + "..." if len(cmdline) > 100 else cmdline
                        })
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return processes
    
    def get_service_status(self, service_name):
        """Get service status"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() or 'inactive'
        except:
            return 'unknown'
    
    def get_service_pid(self, service_name):
        """Get main PID of a service"""
        try:
            result = subprocess.run(
                ['systemctl', 'show', '--property=MainPID', '--value', service_name],
                capture_output=True, text=True, timeout=5
            )
            pid = result.stdout.strip()
            return pid if pid and pid != '0' else None
        except:
            return None
    
    def is_pid_running(self, pid):
        """Check if a PID is running"""
        try:
            return psutil.pid_exists(int(pid))
        except:
            return False
    
    def get_process_command(self, process_config):
        """Generate command string from process config - FIXED VERSION"""
        executable = process_config.get("executable", "").strip()
        config = process_config.get("config", {})
        
        print(f"DEBUG: Generating command for executable: '{executable}'")
        
        # Validate executable
        if not executable:
            raise ValueError("Executable path is empty")
        
        if not os.path.exists(executable):
            raise FileNotFoundError(f"Executable not found: {executable}")
        
        cmd_parts = [executable]
        
        # Common parameters
        if config.get("host"):
            cmd_parts.extend(["--host", str(config["host"])])
        
        if config.get("port"):
            cmd_parts.extend(["--port", str(config["port"])])
        
        if config.get("password"):
            cmd_parts.extend(["--password", str(config["password"])])
        
        # SSL option
        if not config.get("ssl", True):
            cmd_parts.append("--no-ssl")
        
        # Type-specific parameters
        if "refresh_interval" in config:
            cmd_parts.extend(["--refresh-interval", str(config["refresh_interval"])])
        
        if "poll_interval" in config:
            cmd_parts.extend(["--poll-interval", str(config["poll_interval"])])
        
        if "tail_lines" in config:
            cmd_parts.extend(["--tail-lines", str(config["tail_lines"])])
        
        # Log files (can be multiple)
        log_files = config.get("log_files", [])
        if log_files:
            if isinstance(log_files, list):
                for log_file in log_files:
                    cmd_parts.extend(["--log-files", str(log_file)])
            else:
                cmd_parts.extend(["--log-files", str(log_files)])
        
        # Build the final command
        command = ' '.join(cmd_parts)
        print(f"DEBUG: Final command: {command}")
        return command

    def add_service(self):
        """Add a new managed service - FIXED wait_window"""
        dialog = ServiceDialog(self.root, "Add Service")
        dialog.wait_window()  # FIXED: Use dialog.wait_window() instead of self.wait_window(dialog)
        
        if dialog.result:
            # Ensure we have the basic structure
            service_config = {
                "name": dialog.result.get("name", ""),
                "type": "service",
                "service_name": dialog.result.get("service_name", ""),
                "executable": dialog.result.get("executable", ""),
                "config": dialog.result.get("config", {}),
                "pid": None
            }
            
            # Add to config and save
            if "managed_services" not in self.config:
                self.config["managed_services"] = []
            
            self.config["managed_services"].append(service_config)
            
            if self.save_config():
                # Create systemd service file
                self.create_systemd_service(service_config)
                self.refresh_services_view()
                self.status_var.set(f"Added service: {service_config['name']}")
            else:
                messagebox.showerror("Error", "Failed to save service configuration")

    def create_systemd_service(self, service_config):
        """Create systemd service file - FIXED VERSION"""
        try:
            service_name = service_config.get("service_name", "")
            if not service_name:
                messagebox.showerror("Error", "Service name is required")
                return False
            
            # Build the command
            command = self.get_process_command(service_config)
            print(f"DEBUG: Creating service with command: {command}")
            
            service_content = f"""[Unit]
    Description=ETail {service_config.get('name', 'Unknown')}
    After=network.target
    
    [Service]
    Type=simple
    ExecStart={command}
    Restart=always
    RestartSec=10
    User=root
    StandardOutput=journal
    StandardError=journal
    
    [Install]
    WantedBy=multi-user.target
    """
            
            # Write to temporary file
            temp_file = f"/tmp/{service_name}.service"
            with open(temp_file, 'w') as f:
                f.write(service_content)
            
            # Copy to systemd directory
            result = subprocess.run(
                ['sudo', 'cp', temp_file, f'/etc/systemd/system/{service_name}.service'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to copy service file: {result.stderr}")
            
            # Reload systemd
            result = subprocess.run(
                ['sudo', 'systemctl', 'daemon-reload'],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                raise Exception(f"Failed to reload systemd: {result.stderr}")
            
            # Enable the service
            result = subprocess.run(
                ['sudo', 'systemctl', 'enable', service_name],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"Warning: Failed to enable service: {result.stderr}")
            
            print(f"DEBUG: Service created successfully: {service_name}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to create systemd service: {str(e)}"
            print(f"DEBUG: {error_msg}")
            messagebox.showerror("Error", error_msg)
            return False

    def edit_service(self):
        """Edit selected managed service - FIXED wait_window"""
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a service to edit")
            return
        
        item = self.services_tree.item(selected[0])
        service_name = item['values'][3]  # service_name column
        
        # Find the service in config
        for i, service in enumerate(self.config["managed_services"]):
            if service.get("service_name") == service_name:
                dialog = ServiceDialog(self.root, "Edit Service", service)
                dialog.wait_window()  # FIXED: Use dialog.wait_window() instead of self.wait_window(dialog)
                
                if dialog.result:
                    # Update the service configuration
                    self.config["managed_services"][i] = {
                        "name": dialog.result.get("name", ""),
                        "type": "service",
                        "service_name": dialog.result.get("service_name", ""),
                        "executable": dialog.result.get("executable", ""),
                        "config": dialog.result.get("config", {}),
                        "pid": service.get("pid")  # Preserve existing PID
                    }
                    
                    if self.save_config():
                        # Update systemd service file
                        self.create_systemd_service(self.config["managed_services"][i])
                        self.refresh_services_view()
                        self.status_var.set(f"Updated service: {dialog.result['name']}")
                    else:
                        messagebox.showerror("Error", "Failed to save service configuration")
                break

    def delete_service(self):
        """Delete selected managed service"""
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a service to delete")
            return
        
        item = self.services_tree.item(selected[0])
        service_name = item['values'][3]
        
        if messagebox.askyesno("Confirm", f"Delete service '{service_name}'?"):
            self.config["managed_services"] = [
                s for s in self.config["managed_services"] 
                if s.get("service_name") != service_name
            ]
            if self.save_config():
                self.refresh_services_view()
    
    def start_managed_service(self):
        """Start selected managed service"""
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a service to start")
            return
        
        item = self.services_tree.item(selected[0])
        service_name = item['values'][3]
        
        try:
            subprocess.run(['sudo', 'systemctl', 'start', service_name], check=True)
            self.refresh_services_view()
            self.status_var.set(f"Started service: {service_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start service: {e}")
    
    def stop_managed_service(self):
        """Stop selected managed service"""
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a service to stop")
            return
        
        item = self.services_tree.item(selected[0])
        service_name = item['values'][3]
        
        try:
            subprocess.run(['sudo', 'systemctl', 'stop', service_name], check=True)
            self.refresh_services_view()
            self.status_var.set(f"Stopped service: {service_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop service: {e}")
    
    def restart_managed_service(self):
        """Restart selected managed service"""
        selected = self.services_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a service to restart")
            return
        
        item = self.services_tree.item(selected[0])
        service_name = item['values'][3]
        
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', service_name], check=True)
            self.refresh_services_view()
            self.status_var.set(f"Restarted service: {service_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to restart service: {e}")
    
    def add_process(self):
        """Add a new managed process - FIXED wait_window"""
        dialog = ProcessDialog(self.root, "Add Process")
        dialog.wait_window()  # FIXED: Use dialog.wait_window() instead of self.wait_window(dialog)
        
        if dialog.result:
            # Ensure we have the basic structure
            process_config = {
                "name": dialog.result.get("name", ""),
                "type": "process",
                "executable": dialog.result.get("executable", ""),
                "config": dialog.result.get("config", {}),
                "auto_start": dialog.result.get("auto_start", False),
                "pid": None
            }
            
            # Add to config and save
            if "managed_processes" not in self.config:
                self.config["managed_processes"] = []
            
            self.config["managed_processes"].append(process_config)
            
            if self.save_config():
                self.refresh_processes_view()
                self.status_var.set(f"Added process: {process_config['name']}")
                
                # Auto-start if configured
                if process_config["auto_start"]:
                    self.start_specific_process(process_config)
            else:
                messagebox.showerror("Error", "Failed to save process configuration")

    def edit_process(self):
        """Edit selected managed process - FIXED wait_window"""
        selected = self.processes_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to edit")
            return
        
        item = self.processes_tree.item(selected[0])
        process_name = item['values'][0]
        
        for i, process in enumerate(self.config["managed_processes"]):
            if process.get("name") == process_name:
                dialog = ProcessDialog(self.root, "Edit Process", process)
                dialog.wait_window()  # FIXED: Use dialog.wait_window() instead of self.wait_window(dialog)
                
                if dialog.result:
                    # Update the process configuration
                    self.config["managed_processes"][i] = {
                        "name": dialog.result.get("name", ""),
                        "type": "process", 
                        "executable": dialog.result.get("executable", ""),
                        "config": dialog.result.get("config", {}),
                        "auto_start": dialog.result.get("auto_start", False),
                        "pid": process.get("pid")  # Preserve existing PID
                    }
                    
                    if self.save_config():
                        self.refresh_processes_view()
                        self.status_var.set(f"Updated process: {dialog.result['name']}")
                    else:
                        messagebox.showerror("Error", "Failed to save process configuration")
                break

    def delete_process(self):
        selected = self.processes_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to delete")
            return
        
        item = self.processes_tree.item(selected[0])
        process_name = item['values'][0]
        
        if messagebox.askyesno("Confirm", f"Delete process '{process_name}'?"):
            self.config["managed_processes"] = [
                p for p in self.config["managed_processes"] 
                if p.get("name") != process_name
            ]
            if self.save_config():
                self.refresh_processes_view()
  
    def start_managed_process(self):
        """Start managed process with duplicate checking - FIXED VERSION"""
        selected = self.processes_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to start")
            return
        
        item = self.processes_tree.item(selected[0])
        process_name = item['values'][0]
        
        # Find the process config
        for process in self.config["managed_processes"]:
            if process.get("name") == process_name:
                self.start_specific_process(process)
                break

    def stop_managed_process(self):
        """Stop managed process and its entire tree"""
        selected = self.processes_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a process to stop")
            return
        
        item = self.processes_tree.item(selected[0])
        process_name = item['values'][0]
        pid = item['values'][2]
        
        if pid and pid != 'N/A':
            if messagebox.askyesno("Confirm", f"Stop process '{process_name}' and its entire process tree?"):
                try:
                    self.kill_process_tree_recursive(int(pid))
                    # Update config
                    for process in self.config["managed_processes"]:
                        if process.get("name") == process_name:
                            process["pid"] = None
                            process.pop("start_time", None)
                            break
                    if self.save_config():
                        self.refresh_all()
                        self.status_var.set(f"Stopped process: {process_name}")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to stop process: {e}")

    def start_specific_process(self, process_config):
        """Start a specific process with full error handling - FIXED VERSION"""
        process_name = process_config.get("name", "Unknown")
        
        try:
            print(f"DEBUG: Starting process: {process_name}")
            print(f"DEBUG: Process config: {process_config}")
            
            # Validate executable first
            executable = process_config.get("executable", "").strip()
            if not executable:
                raise ValueError("Executable path is empty")
            
            if not os.path.exists(executable):
                raise FileNotFoundError(f"Executable not found: {executable}")
            
            if not os.access(executable, os.X_OK):
                raise PermissionError(f"Executable not executable: {executable}")
            
            # Check for duplicates
            is_duplicate, existing_pid = self.is_duplicate_process_running(process_config)
            if is_duplicate:
                response = messagebox.askyesno(
                    "Duplicate Process", 
                    f"A process with identical parameters is already running (PID: {existing_pid}).\n\n"
                    f"Do you want to stop the existing process and start a new one?"
                )
                if response:
                    try:
                        self.kill_process_tree_recursive(int(existing_pid))
                        time.sleep(2)  # Wait for process to fully stop
                    except Exception as e:
                        messagebox.showerror("Error", f"Failed to stop existing process: {e}")
                        return
                else:
                    return
            
            # Build the command
            command = self.get_process_command(process_config)
            print(f"DEBUG: Final command to execute: {command}")
            
            # Split command properly
            import shlex
            command_parts = shlex.split(command)
            print(f"DEBUG: Command parts: {command_parts}")
            
            # Start process in background with proper error handling
            proc = subprocess.Popen(
                command_parts,
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment to see if process starts successfully
            time.sleep(2)
            return_code = proc.poll()
            
            if return_code is not None:
                # Process exited immediately - get error output
                stdout, stderr = proc.communicate()
                error_msg = f"Process failed to start (return code: {return_code})"
                if stdout:
                    error_msg += f"\nStdout: {stdout.strip()}"
                if stderr:
                    error_msg += f"\nStderr: {stderr.strip()}"
                raise Exception(error_msg)
            
            # Process is running - update config
            process_config["pid"] = proc.pid
            process_config["start_time"] = time.time()
            
            if self.save_config():
                self.refresh_all()
                self.status_var.set(f"Started process: {process_name} (PID: {proc.pid})")
                print(f"DEBUG: Process started successfully with PID: {proc.pid}")
            else:
                # Kill the process if we couldn't save config
                proc.terminate()
                messagebox.showerror("Error", "Failed to save process configuration")
                
        except FileNotFoundError as e:
            error_msg = f"Executable not found: {process_config.get('executable', 'Unknown')}\n\nPlease check the executable path in the process configuration."
            print(f"DEBUG: {error_msg}")
            messagebox.showerror("Error", error_msg)
        except PermissionError as e:
            error_msg = f"Permission denied for executable: {process_config.get('executable', 'Unknown')}\n\nMake sure the file has execute permissions."
            print(f"DEBUG: {error_msg}")
            messagebox.showerror("Error", error_msg)
        except Exception as e:
            error_msg = f"Failed to start process '{process_name}': {str(e)}"
            print(f"DEBUG: {error_msg}")
            messagebox.showerror("Error", error_msg)


class ServiceDialog(tk.Toplevel):
    def __init__(self, parent, title, service_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("600x700")
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.service_data = service_data or {}
        
        self.setup_gui()
        
        # Load existing data if editing
        if service_data:
            self.load_existing_data()
    
    def setup_gui(self):
        """Setup the service dialog form"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Service basic info
        ttk.Label(main_frame, text="Service Configuration", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Display Name
        ttk.Label(main_frame, text="Display Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.display_name = ttk.Entry(main_frame, width=40)
        self.display_name.grid(row=1, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Service Name
        ttk.Label(main_frame, text="Systemd Service Name:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.service_name = ttk.Entry(main_frame, width=40)
        self.service_name.grid(row=2, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Executable Path with validation
        ttk.Label(main_frame, text="Executable Path:").grid(row=3, column=0, sticky=tk.W, pady=2)
        exec_frame = ttk.Frame(main_frame)
        exec_frame.grid(row=3, column=1, sticky=tk.W+tk.E, pady=2)
        self.executable = ttk.Entry(exec_frame, width=35)
        self.executable.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(exec_frame, text="Browse", command=self.browse_executable).pack(side=tk.RIGHT, padx=5)
        
        # Add validation label
        self.executable_status = ttk.Label(main_frame, text="", foreground="red")
        self.executable_status.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Validate on change
        self.executable.bind('<KeyRelease>', self.validate_executable)

        # Service Type
        ttk.Label(main_frame, text="Service Type:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.service_type = ttk.Combobox(main_frame, values=["hardware_monitor", "log_monitor", "custom"], width=37)
        self.service_type.grid(row=4, column=1, sticky=tk.W, pady=2)
        self.service_type.set("hardware_monitor")
        self.service_type.bind('<<ComboboxSelected>>', self.on_service_type_change)
        
        # Configuration frame
        ttk.Label(main_frame, text="Service Parameters", 
                 font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        config_frame = ttk.Frame(main_frame)
        config_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W+tk.E)
        
        # Server settings (common to both)
        ttk.Label(config_frame, text="Server Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host = ttk.Entry(config_frame, width=30)
        self.host.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.host.insert(0, "127.0.0.1")
        
        ttk.Label(config_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port = ttk.Entry(config_frame, width=30)
        self.port.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.port.insert(0, "21327")
        
        ttk.Label(config_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password = ttk.Entry(config_frame, width=30, show="*")
        self.password.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Hardware Monitor specific settings
        self.hw_frame = ttk.Frame(config_frame)
        self.hw_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(self.hw_frame, text="Refresh Interval (seconds):").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.refresh_interval = ttk.Entry(self.hw_frame, width=30)
        self.refresh_interval.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.refresh_interval.insert(0, "5")
        
        # Log Monitor specific settings
        self.log_frame = ttk.Frame(config_frame)
        self.log_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(self.log_frame, text="Log Files:").grid(row=0, column=0, sticky=tk.W, pady=2)
        log_files_frame = ttk.Frame(self.log_frame)
        log_files_frame.grid(row=0, column=1, sticky=tk.W+tk.E, pady=2)
        self.log_files = tk.Text(log_files_frame, width=30, height=3)
        self.log_files.pack(side=tk.LEFT, fill=tk.X, expand=True)
        scrollbar = ttk.Scrollbar(log_files_frame, command=self.log_files.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_files.config(yscrollcommand=scrollbar.set)
        self.log_files.insert('1.0', "/var/log/syslog")
        
        ttk.Label(self.log_frame, text="Poll Interval:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.poll_interval = ttk.Entry(self.log_frame, width=30)
        self.poll_interval.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.poll_interval.insert(0, "1.0")
        
        ttk.Label(self.log_frame, text="Tail Lines:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.tail_lines = ttk.Entry(self.log_frame, width=30)
        self.tail_lines.grid(row=2, column=1, sticky=tk.W, pady=2)
        self.tail_lines.insert(0, "50")
        
        # SSL option (common)
        self.ssl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Use SSL", variable=self.ssl_var).grid(row=5, column=1, sticky=tk.W, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Initialize visibility
        self.on_service_type_change()
        
        # Make columns resizable
        main_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(1, weight=1)
    
    def on_service_type_change(self, event=None):
        """Show/hide configuration based on service type - FIXED VERSION"""
        service_type = self.service_type.get()
        
        if service_type == "hardware_monitor":
            self.hw_frame.grid()
            self.log_frame.grid_remove()
            if not self.service_data:
                self.display_name.delete(0, tk.END)
                self.display_name.insert(0, "ETail Hardware Monitor")
                self.service_name.delete(0, tk.END)
                self.service_name.insert(0, "et-hardware-monitor")
                self.executable.delete(0, tk.END)
                self.executable.insert(0, "/usr/local/bin/et_hardware_mon_linux")
                self.validate_executable()
        elif service_type == "log_monitor":
            self.hw_frame.grid_remove()
            self.log_frame.grid()
            if not self.service_data:
                self.display_name.delete(0, tk.END)
                self.display_name.insert(0, "ETail Log Monitor")
                self.service_name.delete(0, tk.END)
                self.service_name.insert(0, "linux-log-monitor")
                self.executable.delete(0, tk.END)
                self.executable.insert(0, "/usr/local/bin/LinuxLogMonitor")
                self.validate_executable()
        else:  # custom
            self.hw_frame.grid_remove()
            self.log_frame.grid_remove()

    def validate_executable(self, event=None):
        """Validate the executable path"""
        path = self.executable.get().strip()
        if not path:
            self.executable_status.config(text="")
            return
        
        if os.path.exists(path) and os.access(path, os.X_OK):
            self.executable_status.config(text="✅ Valid executable", foreground="green")
        else:
            self.executable_status.config(text="❌ File not found or not executable", foreground="red")
    
    def browse_executable(self):
        """Browse for executable file - FIXED VERSION"""
        filename = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executable files", "*"), ("All files", "*.*")]
        )
        if filename:
            self.executable.delete(0, tk.END)
            self.executable.insert(0, filename)
            self.validate_executable()
    
    def load_existing_data(self):
        """Load existing service data into form"""
        self.display_name.insert(0, self.service_data.get("name", ""))
        self.service_name.insert(0, self.service_data.get("service_name", ""))
        self.executable.insert(0, self.service_data.get("executable", ""))
        
        # Set service type based on executable
        executable = self.service_data.get("executable", "")
        if "et_hardware_mon_linux" in executable:
            self.service_type.set("hardware_monitor")
        elif "LinuxLogMonitor" in executable:
            self.service_type.set("log_monitor")
        else:
            self.service_type.set("custom")
        
        # Load configuration
        config = self.service_data.get("config", {})
        self.host.delete(0, tk.END)
        self.host.insert(0, config.get("host", "127.0.0.1"))
        self.port.delete(0, tk.END)
        self.port.insert(0, config.get("port", "21327"))
        self.password.insert(0, config.get("password", ""))
        self.ssl_var.set(config.get("ssl", True))
        
        # Hardware monitor config
        self.refresh_interval.delete(0, tk.END)
        self.refresh_interval.insert(0, config.get("refresh_interval", "5"))
        
        # Log monitor config
        self.log_files.delete('1.0', tk.END)
        log_files = config.get("log_files", ["/var/log/syslog"])
        self.log_files.insert('1.0', '\n'.join(log_files))
        self.poll_interval.delete(0, tk.END)
        self.poll_interval.insert(0, config.get("poll_interval", "1.0"))
        self.tail_lines.delete(0, tk.END)
        self.tail_lines.insert(0, config.get("tail_lines", "50"))
        
        self.on_service_type_change()
    
    def on_ok(self):
        """Validate and save service configuration"""
        # Validate required fields
        if not self.display_name.get().strip():
            messagebox.showerror("Error", "Display name is required")
            return
        
        if not self.service_name.get().strip():
            messagebox.showerror("Error", "Service name is required")
            return
            
        if not self.executable.get().strip():
            messagebox.showerror("Error", "Executable path is required")
            return
        
        # Build configuration based on service type
        config = {
            "host": self.host.get(),
            "port": int(self.port.get()),
            "password": self.password.get(),
            "ssl": self.ssl_var.get()
        }
        
        service_type = self.service_type.get()
        if service_type == "hardware_monitor":
            config["refresh_interval"] = float(self.refresh_interval.get())
        elif service_type == "log_monitor":
            log_files_text = self.log_files.get('1.0', tk.END).strip()
            config["log_files"] = [f.strip() for f in log_files_text.split('\n') if f.strip()]
            config["poll_interval"] = float(self.poll_interval.get())
            config["tail_lines"] = int(self.tail_lines.get())
        
        self.result = {
            "name": self.display_name.get().strip(),
            "type": "service",
            "service_name": self.service_name.get().strip(),
            "executable": self.executable.get().strip(),
            "config": config,
            "pid": self.service_data.get("pid") if self.service_data else None
        }
        
        self.destroy()
    
    def on_cancel(self):
        """Cancel dialog"""
        self.destroy()


class ProcessDialog(tk.Toplevel):
    def __init__(self, parent, title, process_data=None):
        super().__init__(parent)
        self.title(title)
        self.geometry("500x400")
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.process_data = process_data or {}
        
        self.setup_gui()
        
        # Load existing data if editing
        if process_data:
            self.load_existing_data()
    
    def setup_gui(self):
        """Setup the process dialog form"""
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Process basic info
        ttk.Label(main_frame, text="Process Configuration", 
                 font=('Arial', 12, 'bold')).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        # Display Name
        ttk.Label(main_frame, text="Display Name:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.display_name = ttk.Entry(main_frame, width=40)
        self.display_name.grid(row=1, column=1, sticky=tk.W+tk.E, pady=2)
        
        # Executable Path with validation
        ttk.Label(main_frame, text="Executable Path:").grid(row=2, column=0, sticky=tk.W, pady=2)
        exec_frame = ttk.Frame(main_frame)
        exec_frame.grid(row=2, column=1, sticky=tk.W+tk.E, pady=2)
        self.executable = ttk.Entry(exec_frame, width=35)
        self.executable.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(exec_frame, text="Browse", command=self.browse_executable).pack(side=tk.RIGHT, padx=5)
        
        # Add validation label
        self.executable_status = ttk.Label(main_frame, text="", foreground="red")
        self.executable_status.grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Validate on change
        self.executable.bind('<KeyRelease>', self.validate_executable)
        
        # Process Type
        ttk.Label(main_frame, text="Process Type:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.process_type = ttk.Combobox(main_frame, values=["hardware_monitor", "log_monitor", "custom"], width=37)
        self.process_type.grid(row=3, column=1, sticky=tk.W, pady=2)
        self.process_type.set("hardware_monitor")
        self.process_type.bind('<<ComboboxSelected>>', self.on_process_type_change)
        
        # Auto-start option
        self.auto_start_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(main_frame, text="Auto-start with controller", 
                       variable=self.auto_start_var).grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Configuration frame
        ttk.Label(main_frame, text="Process Parameters", 
                 font=('Arial', 10, 'bold')).grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=10)
        
        config_frame = ttk.Frame(main_frame)
        config_frame.grid(row=6, column=0, columnspan=2, sticky=tk.W+tk.E)
        
        # Server settings
        ttk.Label(config_frame, text="Server Host:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.host = ttk.Entry(config_frame, width=30)
        self.host.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.host.insert(0, "127.0.0.1")
        
        ttk.Label(config_frame, text="Server Port:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.port = ttk.Entry(config_frame, width=30)
        self.port.grid(row=1, column=1, sticky=tk.W, pady=2)
        self.port.insert(0, "21327")
        
        ttk.Label(config_frame, text="Password:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.password = ttk.Entry(config_frame, width=30, show="*")
        self.password.grid(row=2, column=1, sticky=tk.W, pady=2)
        
        # Hardware Monitor specific
        self.hw_frame = ttk.Frame(config_frame)
        self.hw_frame.grid(row=3, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(self.hw_frame, text="Refresh Interval:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.refresh_interval = ttk.Entry(self.hw_frame, width=30)
        self.refresh_interval.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.refresh_interval.insert(0, "5")
        
        # Log Monitor specific
        self.log_frame = ttk.Frame(config_frame)
        self.log_frame.grid(row=4, column=0, columnspan=2, sticky=tk.W+tk.E, pady=5)
        
        ttk.Label(self.log_frame, text="Log Files:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.log_files = ttk.Entry(self.log_frame, width=30)
        self.log_files.grid(row=0, column=1, sticky=tk.W, pady=2)
        self.log_files.insert(0, "/var/log/syslog")
        
        # SSL option
        self.ssl_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(config_frame, text="Use SSL", variable=self.ssl_var).grid(row=5, column=1, sticky=tk.W, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=7, column=0, columnspan=2, pady=20)
        
        ttk.Button(btn_frame, text="OK", command=self.on_ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.on_cancel).pack(side=tk.LEFT, padx=5)
        
        # Initialize visibility
        self.on_process_type_change()
        
        # Make columns resizable
        main_frame.columnconfigure(1, weight=1)
        config_frame.columnconfigure(1, weight=1)
    
    def validate_executable(self, event=None):
        """Validate the executable path"""
        path = self.executable.get().strip()
        if not path:
            self.executable_status.config(text="")
            return
        
        if os.path.exists(path) and os.access(path, os.X_OK):
            self.executable_status.config(text="✅ Valid executable", foreground="green")
        else:
            self.executable_status.config(text="❌ File not found or not executable", foreground="red")
    
    def browse_executable(self):
        """Browse for executable file - FIXED VERSION"""
        filename = filedialog.askopenfilename(
            title="Select executable",
            filetypes=[("Executable files", "*"), ("All files", "*.*")]
        )
        if filename:
            self.executable.delete(0, tk.END)
            self.executable.insert(0, filename)
            self.validate_executable()
    
    def load_existing_data(self):
        """Load existing process data into form"""
        self.display_name.insert(0, self.process_data.get("name", ""))
        self.executable.insert(0, self.process_data.get("executable", ""))
        self.auto_start_var.set(self.process_data.get("auto_start", False))
        
        # Set process type based on executable
        executable = self.process_data.get("executable", "")
        if "et_hardware_mon_linux" in executable:
            self.process_type.set("hardware_monitor")
        elif "LinuxLogMonitor" in executable:
            self.process_type.set("log_monitor")
        else:
            self.process_type.set("custom")
        
        # Load configuration
        config = self.process_data.get("config", {})
        self.host.delete(0, tk.END)
        self.host.insert(0, config.get("host", "127.0.0.1"))
        self.port.delete(0, tk.END)
        self.port.insert(0, config.get("port", "21327"))
        self.password.insert(0, config.get("password", ""))
        self.ssl_var.set(config.get("ssl", True))
        
        # Hardware monitor config
        self.refresh_interval.delete(0, tk.END)
        self.refresh_interval.insert(0, config.get("refresh_interval", "5"))
        
        # Log monitor config
        log_files = config.get("log_files", ["/var/log/syslog"])
        self.log_files.delete(0, tk.END)
        self.log_files.insert(0, ' '.join(log_files))
        
        self.on_process_type_change()
    
    def on_ok(self):
        """Validate and save process configuration"""
        # Validate required fields
        if not self.display_name.get().strip():
            messagebox.showerror("Error", "Display name is required")
            return
            
        if not self.executable.get().strip():
            messagebox.showerror("Error", "Executable path is required")
            return
        
        # Build configuration based on process type
        config = {
            "host": self.host.get(),
            "port": int(self.port.get()),
            "password": self.password.get(),
            "ssl": self.ssl_var.get()
        }
        
        process_type = self.process_type.get()
        if process_type == "hardware_monitor":
            config["refresh_interval"] = float(self.refresh_interval.get())
        elif process_type == "log_monitor":
            log_files_text = self.log_files.get().strip()
            config["log_files"] = [f.strip() for f in log_files_text.split() if f.strip()]
        
        self.result = {
            "name": self.display_name.get().strip(),
            "type": "process",
            "executable": self.executable.get().strip(),
            "config": config,
            "auto_start": self.auto_start_var.get(),
            "pid": self.process_data.get("pid") if self.process_data else None
        }
        
        self.destroy()
    
    def on_cancel(self):
        """Cancel dialog"""
        self.destroy() 

    def on_process_type_change(self, event=None):
        """Show/hide configuration based on process type - FIXED VERSION"""
        process_type = self.process_type.get()
        
        if process_type == "hardware_monitor":
            self.hw_frame.grid()
            self.log_frame.grid_remove()
            if not self.process_data:
                self.display_name.delete(0, tk.END)
                self.display_name.insert(0, "ETail Hardware Monitor")
                self.executable.delete(0, tk.END)
                self.executable.insert(0, "/usr/local/bin/et_hardware_mon_linux")
                self.validate_executable()
        elif process_type == "log_monitor":
            self.hw_frame.grid_remove()
            self.log_frame.grid()
            if not self.process_data:
                self.display_name.delete(0, tk.END)
                self.display_name.insert(0, "ETail Log Monitor")
                self.executable.delete(0, tk.END)
                self.executable.insert(0, "/usr/local/bin/LinuxLogMonitor")
                self.validate_executable()
        else:  # custom
            self.hw_frame.grid_remove()
            self.log_frame.grid_remove()

def main():
    root = tk.Tk()
    app = ETailMonitorController(root)
    root.mainloop()

if __name__ == "__main__":
    main()
