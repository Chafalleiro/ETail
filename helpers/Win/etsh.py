#The following example lists the names of all logs.
#wevtutil el

import sys
import os
import json
import subprocess
import signal
import psutil
from pathlib import Path
from datetime import datetime
import threading
import queue

# PyQt6 imports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, 
                            QHBoxLayout, QPushButton, QListWidget, QListWidgetItem, 
                            QLabel, QLineEdit, QSpinBox, QCheckBox, QGroupBox, 
                            QMessageBox, QSystemTrayIcon, QMenu, QDialog, QDialogButtonBox,
                            QFormLayout, QComboBox, QSplitter, QTextEdit, QScrollArea,
                            QTreeWidget, QTreeWidgetItem, QHeaderView, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QProcess, QSettings
from PyQt6.QtGui import QIcon, QAction, QFont, QPixmap  # Added QPixmap

# Windows event log imports
try:
    import win32evtlog
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

# Configuration classes
class ProcessConfig:
    def __init__(self, name="", type="", host="127.0.0.1", port=21327, password="", 
                 service_name="", exe_name="", log_type="Application", 
                 monitor_processes="", process_threshold=5, poll_interval=5, 
                 use_ssl=True, run_as_admin=False, use_exe=False,
                 log_files="", tail_lines=50, encoding="utf-8",
                 use_fahrenheit=False, refresh_interval=5):  # Hardware monitor fields
        self.name = name
        self.type = type  # "service_monitor", "event_logger", "text_logger", or "hardware_monitor"
        self.host = host
        self.port = port
        self.password = password
        self.service_name = service_name
        self.exe_name = exe_name
        self.log_type = log_type
        self.monitor_processes = monitor_processes
        self.process_threshold = process_threshold
        self.poll_interval = poll_interval
        self.use_ssl = use_ssl
        self.run_as_admin = run_as_admin
        self.use_exe = use_exe
        # Text log specific fields
        self.log_files = log_files
        self.tail_lines = tail_lines
        self.encoding = encoding
        # Hardware monitor specific fields
        self.use_fahrenheit = use_fahrenheit
        self.refresh_interval = refresh_interval
        self.process = None
        self.pid = None
        self.status = "Stopped"
        self.start_time = None

    def to_dict(self):
        return {
            'name': self.name,
            'type': self.type,
            'host': self.host,
            'port': self.port,
            'password': self.password,
            'service_name': self.service_name,
            'exe_name': self.exe_name,
            'log_type': self.log_type,
            'monitor_processes': self.monitor_processes,
            'process_threshold': self.process_threshold,
            'poll_interval': self.poll_interval,
            'use_ssl': self.use_ssl,
            'run_as_admin': self.run_as_admin,
            'use_exe': self.use_exe,
            'log_files': self.log_files,
            'tail_lines': self.tail_lines,
            'encoding': self.encoding,
            'use_fahrenheit': self.use_fahrenheit,
            'refresh_interval': self.refresh_interval
        }

    @classmethod
    def from_dict(cls, data):
        config = cls()
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        return config

class ServiceMonitorConfigDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config or ProcessConfig()
        self.config.type = "service_monitor"
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Service Monitor Configuration")
        self.setModal(True)
        self.resize(500, 550)  # Increased height for new fields

        layout = QVBoxLayout()

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.config.name)
        basic_layout.addRow("Name:", self.name_edit)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Connection settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.host_edit = QLineEdit(self.config.host)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.config.port)
        self.password_edit = QLineEdit(self.config.password)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssl_check = QCheckBox()
        self.ssl_check.setChecked(self.config.use_ssl)
        
        conn_layout.addRow("Host:", self.host_edit)
        conn_layout.addRow("Port:", self.port_spin)
        conn_layout.addRow("Password:", self.password_edit)
        conn_layout.addRow("Use SSL:", self.ssl_check)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Service monitor settings
        service_group = QGroupBox("Service Monitor Settings")
        service_layout = QFormLayout()
        
        self.service_edit = QLineEdit(self.config.service_name)
        self.exe_edit = QLineEdit(self.config.exe_name)
        
        service_layout.addRow("Service Name:", self.service_edit)
        service_layout.addRow("Executable Name:", self.exe_edit)
        service_group.setLayout(service_layout)
        layout.addWidget(service_group)

        # Process monitoring settings
        process_group = QGroupBox("Process Monitoring")
        process_layout = QFormLayout()
        
        self.monitor_processes_edit = QLineEdit(self.config.monitor_processes)
        self.monitor_processes_edit.setPlaceholderText("e.g., chrome.exe,notepad.exe")
        self.process_threshold_spin = QSpinBox()
        self.process_threshold_spin.setRange(1, 100)
        self.process_threshold_spin.setValue(self.config.process_threshold)
        
        process_layout.addRow("Processes to monitor (comma-separated):", self.monitor_processes_edit)
        process_layout.addRow("Process threshold:", self.process_threshold_spin)
        process_group.setLayout(process_layout)
        layout.addWidget(process_group)

        # Advanced settings
        adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()
        
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(1, 60)
        self.poll_spin.setValue(self.config.poll_interval)
        self.admin_check = QCheckBox()
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check = QCheckBox("Use executable instead of Python script")
        self.use_exe_check.setChecked(self.config.use_exe)
        
        adv_layout.addRow("Poll Interval (s):", self.poll_spin)
        adv_layout.addRow("Run as Admin:", self.admin_check)
        adv_layout.addRow("", self.use_exe_check)
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.load_config()

    def load_config(self):
        self.name_edit.setText(self.config.name)
        self.host_edit.setText(self.config.host)
        self.port_spin.setValue(self.config.port)
        self.password_edit.setText(self.config.password)
        self.ssl_check.setChecked(self.config.use_ssl)
        self.service_edit.setText(self.config.service_name)
        self.exe_edit.setText(self.config.exe_name)
        self.monitor_processes_edit.setText(self.config.monitor_processes)
        self.process_threshold_spin.setValue(self.config.process_threshold)
        self.poll_spin.setValue(self.config.poll_interval)
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check.setChecked(self.config.use_exe)

    def get_config(self):
        config = ProcessConfig()
        config.type = "service_monitor"
        config.name = self.name_edit.text()
        config.host = self.host_edit.text()
        config.port = self.port_spin.value()
        config.password = self.password_edit.text()
        config.use_ssl = self.ssl_check.isChecked()
        config.service_name = self.service_edit.text()
        config.exe_name = self.exe_edit.text()
        config.monitor_processes = self.monitor_processes_edit.text()
        config.process_threshold = self.process_threshold_spin.value()
        config.poll_interval = self.poll_spin.value()
        config.run_as_admin = self.admin_check.isChecked()
        config.use_exe = self.use_exe_check.isChecked()
        
        return config

class EventLoggerConfigDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config or ProcessConfig()
        self.config.type = "event_logger"
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Event Logger Configuration")
        self.setModal(True)
        self.resize(600, 600)

        layout = QVBoxLayout()

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.config.name)
        basic_layout.addRow("Name:", self.name_edit)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Connection settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.host_edit = QLineEdit(self.config.host)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.config.port)
        self.password_edit = QLineEdit(self.config.password)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssl_check = QCheckBox()
        self.ssl_check.setChecked(self.config.use_ssl)
        
        conn_layout.addRow("Host:", self.host_edit)
        conn_layout.addRow("Port:", self.port_spin)
        conn_layout.addRow("Password:", self.password_edit)
        conn_layout.addRow("Use SSL:", self.ssl_check)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Event log selection
        log_group = QGroupBox("Event Log Selection")
        log_layout = QVBoxLayout()
        
        # Quick selection combo
        quick_select_layout = QHBoxLayout()
        quick_select_layout.addWidget(QLabel("Common Logs:"))
        self.quick_combo = QComboBox()
        self.quick_combo.addItems([
            "Application", "System", "Security", 
            "Setup", "ForwardedEvents", "Windows PowerShell"
        ])
        self.quick_combo.currentTextChanged.connect(self.on_quick_select)
        quick_select_layout.addWidget(self.quick_combo)
        quick_select_layout.addStretch()
        log_layout.addLayout(quick_select_layout)
        
        # Search box
        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search:"))
        self.search_edit = QLineEdit()
        self.search_edit.textChanged.connect(self.filter_logs)
        search_layout.addWidget(self.search_edit)
        log_layout.addLayout(search_layout)
        
        # Event logs tree
        self.logs_tree = QTreeWidget()
        self.logs_tree.setHeaderLabels(["Event Log Name", "Records"])
        self.logs_tree.itemDoubleClicked.connect(self.on_log_selected)
        self.logs_tree.setSortingEnabled(True)
        log_layout.addWidget(self.logs_tree)
        
        # Manual entry
        manual_layout = QHBoxLayout()
        manual_layout.addWidget(QLabel("Or enter manually:"))
        self.manual_edit = QLineEdit(self.config.log_type)
        manual_layout.addWidget(self.manual_edit)
        log_layout.addLayout(manual_layout)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Advanced settings
        adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()
        
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(1, 60)
        self.poll_spin.setValue(self.config.poll_interval)
        self.admin_check = QCheckBox()
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check = QCheckBox("Use executable instead of Python script")
        self.use_exe_check.setChecked(self.config.use_exe)
        
        adv_layout.addRow("Poll Interval (s):", self.poll_spin)
        adv_layout.addRow("Run as Admin:", self.admin_check)
        adv_layout.addRow("", self.use_exe_check)
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.load_event_logs()
        self.load_config()

    def load_event_logs(self):
        """Load available Windows event logs"""
        if not HAS_WIN32:
            self.logs_tree.addTopLevelItem(QTreeWidgetItem(["win32evtlog not available", ""]))
            return
            
        try:
            # Get list of event logs
            logs = win32evtlog.EvtGetLogNames()
            self.all_logs = []
            
            for log_name in logs:
                try:
                    # Try to get record count
                    log_handle = win32evtlog.OpenEventLog(None, log_name)
                    record_count = win32evtlog.GetNumberOfEventLogRecords(log_handle)
                    win32evtlog.CloseEventLog(log_handle)
                    
                    item = QTreeWidgetItem([log_name, str(record_count)])
                    self.all_logs.append(item)
                    
                except Exception:
                    # If we can't open the log, just show it without record count
                    item = QTreeWidgetItem([log_name, "N/A"])
                    self.all_logs.append(item)
            
            # Add all items to tree
            self.logs_tree.addTopLevelItems(self.all_logs)
            self.logs_tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            
        except Exception as e:
            self.logs_tree.addTopLevelItem(QTreeWidgetItem([f"Error loading logs: {str(e)}", ""]))

    def filter_logs(self, text):
        """Filter event logs based on search text"""
        if not hasattr(self, 'all_logs'):
            return
            
        self.logs_tree.clear()
        if not text.strip():
            self.logs_tree.addTopLevelItems(self.all_logs)
        else:
            filtered = [item for item in self.all_logs 
                       if text.lower() in item.text(0).lower()]
            self.logs_tree.addTopLevelItems(filtered)

    def on_quick_select(self, log_name):
        """Handle quick selection from combo box"""
        self.manual_edit.setText(log_name)

    def on_log_selected(self, item, column):
        """Handle log selection from tree"""
        log_name = item.text(0)
        self.manual_edit.setText(log_name)

    def load_config(self):
        self.name_edit.setText(self.config.name)
        self.host_edit.setText(self.config.host)
        self.port_spin.setValue(self.config.port)
        self.password_edit.setText(self.config.password)
        self.ssl_check.setChecked(self.config.use_ssl)
        self.manual_edit.setText(self.config.log_type)
        self.poll_spin.setValue(self.config.poll_interval)
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check.setChecked(self.config.use_exe)

    def get_config(self):
        config = ProcessConfig()
        config.type = "event_logger"
        config.name = self.name_edit.text()
        config.host = self.host_edit.text()
        config.port = self.port_spin.value()
        config.password = self.password_edit.text()
        config.use_ssl = self.ssl_check.isChecked()
        config.log_type = self.manual_edit.text()
        config.poll_interval = self.poll_spin.value()
        config.run_as_admin = self.admin_check.isChecked()
        config.use_exe = self.use_exe_check.isChecked()
        
        return config

class TextLogConfigDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config or ProcessConfig()
        self.config.type = "text_logger"
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Text Log Monitor Configuration")
        self.setModal(True)
        self.resize(600, 500)

        layout = QVBoxLayout()

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.config.name)
        basic_layout.addRow("Name:", self.name_edit)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Connection settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.host_edit = QLineEdit(self.config.host)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.config.port)
        self.password_edit = QLineEdit(self.config.password)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssl_check = QCheckBox()
        self.ssl_check.setChecked(self.config.use_ssl)
        
        conn_layout.addRow("Host:", self.host_edit)
        conn_layout.addRow("Port:", self.port_spin)
        conn_layout.addRow("Password:", self.password_edit)
        conn_layout.addRow("Use SSL:", self.ssl_check)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Log file selection
        log_group = QGroupBox("Log File Selection")
        log_layout = QVBoxLayout()
        
        # Log files list
        log_files_layout = QHBoxLayout()
        log_files_layout.addWidget(QLabel("Log Files:"))
        self.log_files_edit = QLineEdit(self.config.log_files or "")
        self.log_files_edit.setPlaceholderText("C:\\path\\to\\log1.log, C:\\path\\to\\log2.log")
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_log_files)
        
        log_files_layout.addWidget(self.log_files_edit)
        log_files_layout.addWidget(self.browse_btn)
        log_layout.addLayout(log_files_layout)
        
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Advanced settings
        adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()
        
        self.tail_spin = QSpinBox()
        self.tail_spin.setRange(1, 1000)
        self.tail_spin.setValue(self.config.tail_lines or 50)
        self.poll_spin = QSpinBox()
        self.poll_spin.setRange(1, 60)
        self.poll_spin.setValue(self.config.poll_interval)
        self.encoding_combo = QComboBox()
        self.encoding_combo.addItems(['utf-8', 'utf-16', 'latin-1', 'cp1252'])
        self.encoding_combo.setCurrentText(self.config.encoding or 'utf-8')
        self.admin_check = QCheckBox()
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check = QCheckBox("Use executable instead of Python script")
        self.use_exe_check.setChecked(self.config.use_exe)
        
        adv_layout.addRow("Initial Lines:", self.tail_spin)
        adv_layout.addRow("Poll Interval (s):", self.poll_spin)
        adv_layout.addRow("File Encoding:", self.encoding_combo)
        adv_layout.addRow("Run as Admin:", self.admin_check)
        adv_layout.addRow("", self.use_exe_check)
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.load_config()

    def browse_log_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Log Files",
            "",
            "Log Files (*.log *.txt);;All Files (*.*)"
        )
        if files:
            self.log_files_edit.setText(', '.join(files))

    def load_config(self):
        self.name_edit.setText(self.config.name)
        self.host_edit.setText(self.config.host)
        self.port_spin.setValue(self.config.port)
        self.password_edit.setText(self.config.password)
        self.ssl_check.setChecked(self.config.use_ssl)
        self.log_files_edit.setText(self.config.log_files or "")
        self.tail_spin.setValue(self.config.tail_lines or 50)
        self.poll_spin.setValue(self.config.poll_interval)
        self.encoding_combo.setCurrentText(self.config.encoding or 'utf-8')
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check.setChecked(self.config.use_exe)

    def get_config(self):
        config = ProcessConfig()
        config.type = "text_logger"
        config.name = self.name_edit.text()
        config.host = self.host_edit.text()
        config.port = self.port_spin.value()
        config.password = self.password_edit.text()
        config.use_ssl = self.ssl_check.isChecked()
        config.log_files = self.log_files_edit.text()
        config.tail_lines = self.tail_spin.value()
        config.poll_interval = self.poll_spin.value()
        config.encoding = self.encoding_combo.currentText()
        config.run_as_admin = self.admin_check.isChecked()
        config.use_exe = self.use_exe_check.isChecked()
        
        return config

# Add to your etsh.py file
class HardwareMonitorConfigDialog(QDialog):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self.config = config or ProcessConfig()
        self.config.type = "hardware_monitor"
        self.setup_ui()

    def setup_ui(self):
        self.setWindowTitle("Hardware Monitor Configuration")
        self.setModal(True)
        self.resize(500, 400)

        layout = QVBoxLayout()

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        
        self.name_edit = QLineEdit(self.config.name)
        basic_layout.addRow("Name:", self.name_edit)
        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Connection settings
        conn_group = QGroupBox("Connection Settings")
        conn_layout = QFormLayout()
        
        self.host_edit = QLineEdit(self.config.host)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(self.config.port)
        self.password_edit = QLineEdit(self.config.password)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.ssl_check = QCheckBox()
        self.ssl_check.setChecked(self.config.use_ssl)
        
        conn_layout.addRow("Host:", self.host_edit)
        conn_layout.addRow("Port:", self.port_spin)
        conn_layout.addRow("Password:", self.password_edit)
        conn_layout.addRow("Use SSL:", self.ssl_check)
        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        # Hardware monitoring settings
        hardware_group = QGroupBox("Hardware Monitoring Settings")
        hardware_layout = QFormLayout()
        
        self.fahrenheit_check = QCheckBox("Use Fahrenheit temperature")
        self.fahrenheit_check.setChecked(getattr(self.config, 'use_fahrenheit', False))
        
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 300)
        self.refresh_spin.setValue(getattr(self.config, 'refresh_interval', 5))
        self.refresh_spin.setSuffix(" seconds")
        
        hardware_layout.addRow("Temperature Unit:", self.fahrenheit_check)
        hardware_layout.addRow("Refresh Interval:", self.refresh_spin)
        hardware_group.setLayout(hardware_layout)
        layout.addWidget(hardware_group)

        # Advanced settings
        adv_group = QGroupBox("Advanced Settings")
        adv_layout = QFormLayout()
        
        self.admin_check = QCheckBox()
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check = QCheckBox("Use executable instead of Python script")
        self.use_exe_check.setChecked(self.config.use_exe)
        
        adv_layout.addRow("Run as Admin:", self.admin_check)
        adv_layout.addRow("", self.use_exe_check)
        adv_group.setLayout(adv_layout)
        layout.addWidget(adv_group)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        self.setLayout(layout)
        self.load_config()

    def load_config(self):
        self.name_edit.setText(self.config.name)
        self.host_edit.setText(self.config.host)
        self.port_spin.setValue(self.config.port)
        self.password_edit.setText(self.config.password)
        self.ssl_check.setChecked(self.config.use_ssl)
        self.fahrenheit_check.setChecked(getattr(self.config, 'use_fahrenheit', False))
        self.refresh_spin.setValue(getattr(self.config, 'refresh_interval', 5))
        self.admin_check.setChecked(self.config.run_as_admin)
        self.use_exe_check.setChecked(self.config.use_exe)

    def get_config(self):
        config = ProcessConfig()
        config.type = "hardware_monitor"
        config.name = self.name_edit.text()
        config.host = self.host_edit.text()
        config.port = self.port_spin.value()
        config.password = self.password_edit.text()
        config.use_ssl = self.ssl_check.isChecked()
        config.use_fahrenheit = self.fahrenheit_check.isChecked()
        config.refresh_interval = self.refresh_spin.value()
        config.run_as_admin = self.admin_check.isChecked()
        config.use_exe = self.use_exe_check.isChecked()
        
        return config

class ProcessManager(QWidget):
    process_started = pyqtSignal(ProcessConfig)
    process_stopped = pyqtSignal(ProcessConfig)
    output_received = pyqtSignal(str, str)  # process_name, output
    
    def __init__(self, config_type):
        super().__init__()
        self.config_type = config_type  # "service_monitor" or "event_logger"
        self.processes = []
        self.config_file = Path(f"{config_type}_configs.json")
        self.output_queues = {}  # process_name -> queue
        self.output_threads = {}  # process_name -> thread
        self.load_configs()
        self.setup_ui()
        
        # Connect output signal to log method
        self.output_received.connect(self.on_output_received)

    def setup_ui(self):
        layout = QVBoxLayout()

        # Toolbar
        toolbar = QHBoxLayout()
        self.add_btn = QPushButton("Add")
        self.edit_btn = QPushButton("Edit")
        self.delete_btn = QPushButton("Delete")
        self.start_btn = QPushButton("Start")
        self.stop_btn = QPushButton("Stop")
        self.restart_btn = QPushButton("Restart")
        
        self.add_btn.clicked.connect(self.add_config)
        self.edit_btn.clicked.connect(self.edit_config)
        self.delete_btn.clicked.connect(self.delete_config)
        self.start_btn.clicked.connect(self.start_selected)
        self.stop_btn.clicked.connect(self.stop_selected)
        self.restart_btn.clicked.connect(self.restart_selected)
        
        toolbar.addWidget(self.add_btn)
        toolbar.addWidget(self.edit_btn)
        toolbar.addWidget(self.delete_btn)
        toolbar.addWidget(self.start_btn)
        toolbar.addWidget(self.stop_btn)
        toolbar.addWidget(self.restart_btn)
        toolbar.addStretch()
        
        layout.addLayout(toolbar)

        # Process list
        self.process_list = QListWidget()
        self.process_list.itemSelectionChanged.connect(self.on_selection_changed)
        layout.addWidget(self.process_list)

        # Status area
        self.status_text = QTextEdit()
        self.status_text.setMaximumHeight(200)
        self.status_text.setReadOnly(True)
        layout.addWidget(QLabel("Process Output:"))
        layout.addWidget(self.status_text)

        self.setLayout(layout)
        self.refresh_list()

    def on_output_received(self, process_name, output):
        """Handle output received from processes"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {process_name}: {output}")
        
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def add_config(self):
        if self.config_type == "service_monitor":
            dialog = ServiceMonitorConfigDialog()
        elif self.config_type == "event_logger":
            dialog = EventLoggerConfigDialog()
        elif self.config_type == "text_logger":
            dialog = TextLogConfigDialog()
        else:  # hardware_monitor
            dialog = HardwareMonitorConfigDialog()
            
        if dialog.exec() == QDialog.DialogCode.Accepted:
            config = dialog.get_config()
            self.processes.append(config)
            self.save_configs()
            self.refresh_list()

    def edit_config(self):
        current = self.get_selected_config()
        if current:
            if self.config_type == "service_monitor":
                dialog = ServiceMonitorConfigDialog(current)
            elif self.config_type == "event_logger":
                dialog = EventLoggerConfigDialog(current)
            elif self.config_type == "text_logger":
                dialog = TextLogConfigDialog(current)
            else:  # hardware_monitor
                dialog = HardwareMonitorConfigDialog(current)
                
            if dialog.exec() == QDialog.DialogCode.Accepted:
                new_config = dialog.get_config()
                # Update the existing config
                index = self.processes.index(current)
                self.processes[index] = new_config
                self.save_configs()
                self.refresh_list()

    def delete_config(self):
        current = self.get_selected_config()
        if current:
            if current.status == "Running":
                QMessageBox.warning(self, "Warning", "Please stop the process before deleting.")
                return
                
            reply = QMessageBox.question(self, "Confirm Delete", 
                                       f"Delete configuration '{current.name}'?")
            if reply == QMessageBox.StandardButton.Yes:
                # Clean up output monitoring
                if current.name in self.output_queues:
                    del self.output_queues[current.name]
                if current.name in self.output_threads:
                    self.output_threads[current.name].stop()
                    del self.output_threads[current.name]
                
                self.processes.remove(current)
                self.save_configs()
                self.refresh_list()

    def start_selected(self):
        config = self.get_selected_config()
        if config and config.status == "Stopped":
            self.start_process(config)

    def stop_selected(self):
        config = self.get_selected_config()
        if config and config.status == "Running":
            self.stop_process(config)

    def restart_selected(self):
        config = self.get_selected_config()
        if config:
            if config.status == "Running":
                self.stop_process(config)
            # Use a timer to start after a short delay
            QTimer.singleShot(1000, lambda: self.start_process(config))

    def get_selected_config(self):
        items = self.process_list.selectedItems()
        if items:
            return items[0].data(Qt.ItemDataRole.UserRole)
        return None

    def on_selection_changed(self):
        config = self.get_selected_config()
        self.edit_btn.setEnabled(config is not None)
        self.delete_btn.setEnabled(config is not None)
        self.start_btn.setEnabled(config is not None and config.status == "Stopped")
        self.stop_btn.setEnabled(config is not None and config.status == "Running")
        self.restart_btn.setEnabled(config is not None)

    def refresh_list(self):
        self.process_list.clear()
        for config in self.processes:
            status_icon = "🟢" if config.status == "Running" else "🔴"
            item_text = f"{status_icon} {config.name}"
            if config.status == "Running" and config.pid:
                item_text += f" (PID: {config.pid})"
                
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, config)
            
            # Color coding
            if config.status == "Running":
                item.setForeground(Qt.GlobalColor.darkGreen)
            elif config.status == "Error":
                item.setForeground(Qt.GlobalColor.red)
                
            self.process_list.addItem(item)

    def start_process(self, config):
        try:
            if config.type == "service_monitor":
                # Determine whether to use executable or Python script
                if config.use_exe:
                    script = "process_mon.exe"
                else:
                    script = "process_mon.py"
                    
                args = [
                    "--host", config.host,
                    "--port", str(config.port),
                    "--password", config.password,
                    "--service-name", config.service_name,
                    "--exe-name", config.exe_name,
                    "--process-threshold", str(config.process_threshold),
                    "--poll-interval", str(config.poll_interval)
                ]
                
                # Add monitor processes if specified
                if config.monitor_processes:
                    args.extend(["--monitor-processes", config.monitor_processes])
                    
                if not config.use_ssl:
                    args.append("--no-ssl")
                    
            elif config.type == "event_logger":
                # Determine whether to use executable or Python script
                if config.use_exe:
                    script = "event_logger.exe"
                else:
                    script = "event_logger.py"
                    
                args = [
                    "--host", config.host,
                    "--port", str(config.port),
                    "--password", config.password,
                    "--log-type", config.log_type,
                    "--poll-interval", str(config.poll_interval)
                ]
                if not config.use_ssl:
                    args.append("--no-ssl")

            elif config.type == "text_logger":
                # Determine whether to use executable or Python script
                if config.use_exe:
                    script = "windows_log_client.exe"
                else:
                    script = "windows_log_client.py"
                    
                args = [
                    "--host", config.host,
                    "--port", str(config.port),
                    "--password", config.password,
                    "--poll-interval", str(config.poll_interval),
                    "--tail-lines", str(config.tail_lines),
                    "--encoding", config.encoding
                ]
                
                # Add log files
                if config.log_files:
                    log_files_list = [f.strip() for f in config.log_files.split(',') if f.strip()]
                    args.extend(["--log-files"] + log_files_list)
                    
                if not config.use_ssl:
                    args.append("--no-ssl")

            else:  # hardware_monitor
                # Determine whether to use executable or Python script
                if config.use_exe:
                    script = "hardware_mon.exe"
                else:
                    script = "hardware_mon.py"
                    
                args = [
                    "--host", config.host,
                    "--port", str(config.port),
                    "--password", config.password,
                    "--refresh-interval", str(config.refresh_interval)
                ]
                
                if config.use_fahrenheit:
                    args.append("--fahrenheit")
                    
                if not config.use_ssl:
                    args.append("--no-ssl")

            # Create subprocess with proper output handling
            creation_flags = 0
            if os.name == 'nt':
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            # Use the appropriate command based on whether it's an executable
            if config.use_exe:
                command = [script] + args
            else:
                command = [sys.executable, script] + args

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creation_flags
            )

            config.process = process
            config.pid = process.pid
            config.status = "Running"
            config.start_time = datetime.now()
            
            self.process_started.emit(config)
            self.refresh_list()
            self.log_output(f"Started {config.name} (PID: {config.pid})")
            
            # Start output monitoring
            self.start_output_monitoring(config)
            
        except Exception as e:
            config.status = "Error"
            self.log_output(f"❌ Error starting {config.name}: {str(e)}")
            self.refresh_list()

    def start_output_monitoring(self, config):
        """Start monitoring stdout and stderr for the process"""
        if config.name in self.output_threads:
            # Stop existing monitoring
            self.output_threads[config.name].stop()
            
        # Create new output queue and thread
        output_queue = queue.Queue()
        self.output_queues[config.name] = output_queue
        
        # Start stdout monitoring
        stdout_thread = OutputMonitorThread(config.process.stdout, output_queue, config.name)
        stdout_thread.start()
        
        # Start stderr monitoring  
        stderr_thread = OutputMonitorThread(config.process.stderr, output_queue, config.name)
        stderr_thread.start()
        
        # Start queue processor
        processor_thread = OutputProcessorThread(output_queue, self.output_received)
        processor_thread.start()
        
        self.output_threads[config.name] = processor_thread

    def stop_process(self, config):
        try:
            # Stop output monitoring first
            if config.name in self.output_threads:
                self.output_threads[config.name].stop()
                del self.output_threads[config.name]
            if config.name in self.output_queues:
                del self.output_queues[config.name]

            if config.process:
                # Try graceful termination first
                config.process.terminate()
                try:
                    config.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if not responding
                    config.process.kill()
                    config.process.wait()
                
            # Also try to kill by PID in case the process tree has child processes
            if config.pid:
                try:
                    parent = psutil.Process(config.pid)
                    for child in parent.children(recursive=True):
                        try:
                            child.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    try:
                        parent.terminate()
                    except psutil.NoSuchProcess:
                        pass
                except psutil.NoSuchProcess:
                    pass
            
            config.process = None
            config.pid = None
            config.status = "Stopped"
            
            self.process_stopped.emit(config)
            self.refresh_list()
            self.log_output(f"Stopped {config.name}")
            
        except Exception as e:
            self.log_output(f"❌ Error stopping {config.name}: {str(e)}")

    def log_output(self, message):
        """Log internal management messages"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.status_text.append(f"[{timestamp}] {message}")

    def load_configs(self):
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.processes = [ProcessConfig.from_dict(item) for item in data]
            except Exception as e:
                QMessageBox.warning(self, "Load Error", f"Error loading configs: {str(e)}")

    def save_configs(self):
        try:
            data = [config.to_dict() for config in self.processes]
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Save Error", f"Error saving configs: {str(e)}")

class OutputMonitorThread(threading.Thread):
    """Thread to monitor process output streams"""
    def __init__(self, stream, output_queue, process_name):
        super().__init__()
        self.stream = stream
        self.output_queue = output_queue
        self.process_name = process_name
        self._stop_event = threading.Event()
        self.daemon = True

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                line = self.stream.readline()
                if line:
                    self.output_queue.put((self.process_name, line.strip()))
                else:
                    # End of stream
                    break
            except (ValueError, IOError):
                break

class OutputProcessorThread(threading.Thread):
    """Thread to process output from the queue and emit signals"""
    def __init__(self, output_queue, output_signal):
        super().__init__()
        self.output_queue = output_queue
        self.output_signal = output_signal
        self._stop_event = threading.Event()
        self.daemon = True

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                # Wait for output with timeout to allow checking stop event
                try:
                    process_name, output = self.output_queue.get(timeout=0.1)
                    if output:
                        self.output_signal.emit(process_name, output)
                except queue.Empty:
                    continue
            except Exception:
                break

class SystemToolsTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # System tools group
        tools_group = QGroupBox("Windows System Tools")
        tools_layout = QVBoxLayout()

        self.services_btn = QPushButton("Open Services Manager")
        self.event_viewer_btn = QPushButton("Open Event Viewer")
        self.task_manager_btn = QPushButton("Open Task Manager")

        self.services_btn.clicked.connect(self.open_services)
        self.event_viewer_btn.clicked.connect(self.open_event_viewer)
        self.task_manager_btn.clicked.connect(self.open_task_manager)

        tools_layout.addWidget(self.services_btn)
        tools_layout.addWidget(self.event_viewer_btn)
        tools_layout.addWidget(self.task_manager_btn)
        tools_group.setLayout(tools_layout)
        layout.addWidget(tools_group)

        # Application settings group
        settings_group = QGroupBox("Application Settings")
        settings_layout = QFormLayout()

        self.start_minimized = QCheckBox()
        self.close_to_tray = QCheckBox()

        settings_layout.addRow("Start Minimized:", self.start_minimized)
        settings_layout.addRow("Close to Tray:", self.close_to_tray)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)

        layout.addStretch()
        self.setLayout(layout)

    def open_services(self):
        try:
            if os.name == 'nt':
                os.system("services.msc")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open Services: {str(e)}")

    def open_event_viewer(self):
        try:
            if os.name == 'nt':
                os.system("eventvwr.msc")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open Event Viewer: {str(e)}")

    def open_task_manager(self):
        try:
            if os.name == 'nt':
                os.system("taskmgr")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open Task Manager: {str(e)}")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.tray_icon = "EtMaps.ico"
        self.settings = QSettings("ProcessManager", "App")
        self.setup_ui()
        self.setup_tray()
        self.load_settings()

    def setup_ui(self):
        self.setWindowTitle("ETail Helpers Manager")
        self.setGeometry(100, 100, 900, 700)

        self.setWindowIcon(self.get_icon())

        # Create tab widget
        self.tabs = QTabWidget()
        
        
        # Service Monitor tab
        self.service_tab = ProcessManager("service_monitor")
        self.service_tab.process_started.connect(self.on_process_started)
        self.service_tab.process_stopped.connect(self.on_process_stopped)
        self.tabs.addTab(self.service_tab, "Service Monitors")

        # Event Logger tab  
        self.event_tab = ProcessManager("event_logger")
        self.event_tab.process_started.connect(self.on_process_started)
        self.event_tab.process_stopped.connect(self.on_process_stopped)
        self.tabs.addTab(self.event_tab, "Event Loggers")

        # Text Log Monitor tab
        self.text_log_tab = ProcessManager("text_logger")
        self.text_log_tab.process_started.connect(self.on_process_started)
        self.text_log_tab.process_stopped.connect(self.on_process_stopped)
        self.tabs.addTab(self.text_log_tab, "Text Log Monitors")

        # Hardware Monitor tab
        self.hardware_tab = ProcessManager("hardware_monitor")
        self.hardware_tab.process_started.connect(self.on_process_started)
        self.hardware_tab.process_stopped.connect(self.on_process_stopped)
        self.tabs.addTab(self.hardware_tab, "Hardware Monitors")

        # System Tools tab
        self.tools_tab = SystemToolsTab()
        self.tabs.addTab(self.tools_tab, "System Tools")

        self.setCentralWidget(self.tabs)

    def get_icon(self):
        """Get the application icon from various possible locations"""
        # Try different possible icon locations
        icon_paths = [
            "EtMaps.ico",
            "resources/EtMaps.ico",
            "images/EtMaps.ico",
            "../EtMaps.ico"
        ]
        
        for path in icon_paths:
            if os.path.exists(path):
                return QIcon(path)
        
        # If no icon file found, create a simple default icon
        print("Warning: No icon file found. Using default icon.")
        return self.create_default_icon()

    def create_default_icon(self):
        """Create a simple default icon programmatically"""
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.blue)
        return QIcon(pixmap)


    def setup_tray(self):
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            self.tray_icon.setIcon(self.get_icon())
            
            # Create tray menu
            tray_menu = QMenu()
            
            show_action = QAction("Show", self)
            show_action.triggered.connect(self.show)
            tray_menu.addAction(show_action)
            
            tray_menu.addSeparator()
            
            # Will be populated with running processes
            self.process_menu = QMenu("Running Processes")
            tray_menu.addMenu(self.process_menu)
            
            tray_menu.addSeparator()
            
            quit_action = QAction("Quit", self)
            quit_action.triggered.connect(self.quit_application)
            tray_menu.addAction(quit_action)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            
            # Set tooltip
            self.tray_icon.setToolTip("Process Manager")
            
            self.tray_icon.show()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.activateWindow()

    def on_process_started(self, config):
        self.update_tray_menu()

    def on_process_stopped(self, config):
        self.update_tray_menu()

    def update_tray_menu(self):
        if not self.tray_icon:
            return
            
        self.process_menu.clear()
        
        # Get all running processes from both tabs
        running_processes = []
        for config in self.service_tab.processes + self.event_tab.processes:
            if config.status == "Running":
                running_processes.append(config)
        
        if not running_processes:
            action = QAction("No running processes", self)
            action.setEnabled(False)
            self.process_menu.addAction(action)
        else:
            for config in running_processes:
                action = QAction(f"Stop {config.name}", self)
                action.triggered.connect(lambda checked, c=config: self.stop_via_tray(c))
                self.process_menu.addAction(action)

    def stop_via_tray(self, config):
        # Find which tab this config belongs to and stop it
        if config in self.service_tab.processes:
            self.service_tab.stop_process(config)
        elif config in self.event_tab.processes:
            self.event_tab.stop_process(config)

    def closeEvent(self, event):
        if self.tools_tab.close_to_tray.isChecked() and self.tray_icon:
            self.hide()
            event.ignore()
        else:
            self.quit_application()

    def load_settings(self):
        self.tools_tab.start_minimized.setChecked(
            self.settings.value("start_minimized", False, type=bool)
        )
        self.tools_tab.close_to_tray.setChecked(
            self.settings.value("close_to_tray", True, type=bool)
        )
        
        if self.tools_tab.start_minimized.isChecked():
            self.hide()

    def save_settings(self):
        self.settings.setValue("start_minimized", 
                             self.tools_tab.start_minimized.isChecked())
        self.settings.setValue("close_to_tray", 
                             self.tools_tab.close_to_tray.isChecked())

    def quit_application(self):
        # Stop all running processes
        for config in (self.service_tab.processes + self.event_tab.processes):
            if config.status == "Running":
                if config in self.service_tab.processes:
                    self.service_tab.stop_process(config)
                else:
                    self.event_tab.stop_process(config)
        
        self.save_settings()
        QApplication.quit()

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    # Set application icon
    app_icon = QIcon("EtMaps.ico")
    if not app_icon.isNull():
        app.setWindowIcon(app_icon)
    else:
        print("Warning: app_icon.ico not found. Application will use default icon.")
    
    # Check if we're on Windows and if admin rights are needed
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.shell32.IsUserAnAdmin():
            print("Running with administrator privileges")
        else:
            print("Running without administrator privileges - some features may not work")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()