import sys
import os
import subprocess
import threading
from pathlib import Path

# PyQt6 imports
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                            QWidget, QLabel, QLineEdit, QPushButton, QTextEdit,
                            QCheckBox, QGroupBox, QFormLayout, QFileDialog, 
                            QMessageBox, QProgressBar, QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QPixmap  # Added QPixmap

class BuildThread(QThread):
    """Thread to run PyInstaller build process"""
    output_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, script_path, output_dir, icon_path, console, onefile, additional_files):
        super().__init__()
        self.script_path = script_path
        self.output_dir = output_dir
        self.icon_path = icon_path
        self.console = console
        self.onefile = onefile
        self.additional_files = additional_files
        
    def run(self):
        try:
            self.output_signal.emit("Starting build process...")
            
            # Build PyInstaller command
            cmd = ['pyinstaller', '--noconfirm']
            
            if self.onefile:
                cmd.append('--onefile')
            else:
                cmd.append('--onedir')
                
            if not self.console:
                cmd.append('--noconsole')
                
            if self.icon_path:
                cmd.extend(['--icon', self.icon_path])
                
            if self.output_dir:
                cmd.extend(['--distpath', self.output_dir])
                
            # Add additional files
            for file in self.additional_files:
                cmd.extend(['--add-data', f'{file};.'])
                
            # Add the main script
            cmd.append(self.script_path)
            
            self.output_signal.emit(f"Command: {' '.join(cmd)}")
            self.output_signal.emit("Building executable... This may take a few minutes.")
            
            # Run PyInstaller
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            for line in process.stdout:
                self.output_signal.emit(line.strip())
                
            process.wait()
            
            if process.returncode == 0:
                self.finished_signal.emit(True, "Build completed successfully!")
            else:
                self.finished_signal.emit(False, f"Build failed with return code: {process.returncode}")
                
        except Exception as e:
            self.finished_signal.emit(False, f"Build error: {str(e)}")

class PyInstallerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.build_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        self.setWindowTitle("PyInstaller GUI - Executable Builder")
        self.setGeometry(100, 100, 800, 700)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Title
        title = QLabel("PyInstaller Executable Builder")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # File selection group
        file_group = QGroupBox("File Selection")
        file_layout = QFormLayout()
        
        # Python script selection
        self.script_edit = QLineEdit()
        self.script_btn = QPushButton("Browse...")
        self.script_btn.clicked.connect(self.select_script)
        script_layout = QHBoxLayout()
        script_layout.addWidget(self.script_edit)
        script_layout.addWidget(self.script_btn)
        file_layout.addRow("Python Script:", script_layout)
        
        # Output directory selection
        self.output_edit = QLineEdit()
        self.output_btn = QPushButton("Browse...")
        self.output_btn.clicked.connect(self.select_output_dir)
        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_edit)
        output_layout.addWidget(self.output_btn)
        file_layout.addRow("Output Directory:", output_layout)
        
        # Icon file selection
        self.icon_edit = QLineEdit()
        self.icon_btn = QPushButton("Browse...")
        self.icon_btn.clicked.connect(self.select_icon)
        icon_layout = QHBoxLayout()
        icon_layout.addWidget(self.icon_edit)
        icon_layout.addWidget(self.icon_btn)
        file_layout.addRow("Icon File (optional):", icon_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        # Build options group
        options_group = QGroupBox("Build Options")
        options_layout = QFormLayout()
        
        self.console_check = QCheckBox("Show console window")
        self.console_check.setChecked(False)
        options_layout.addRow(self.console_check)
        
        self.onefile_check = QCheckBox("Create single executable")
        self.onefile_check.setChecked(True)
        options_layout.addRow(self.onefile_check)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Additional files group
        additional_group = QGroupBox("Additional Files")
        additional_layout = QVBoxLayout()
        
        self.additional_list = QListWidget()
        additional_layout.addWidget(self.additional_list)
        
        add_files_btn = QPushButton("Add Files/Folders")
        add_files_btn.clicked.connect(self.add_additional_files)
        remove_files_btn = QPushButton("Remove Selected")
        remove_files_btn.clicked.connect(self.remove_additional_files)
        
        btn_layout = QHBoxLayout()
        btn_layout.addWidget(add_files_btn)
        btn_layout.addWidget(remove_files_btn)
        additional_layout.addLayout(btn_layout)
        
        additional_group.setLayout(additional_layout)
        layout.addWidget(additional_group)
        
        # Build button
        self.build_btn = QPushButton("Build Executable")
        self.build_btn.clicked.connect(self.start_build)
        self.build_btn.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(self.build_btn)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Output log
        self.output_text = QTextEdit()
        self.output_text.setPlaceholderText("Build output will appear here...")
        self.output_text.setReadOnly(True)
        layout.addWidget(self.output_text)
        
        # Status bar equivalent
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
    def select_script(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Python Script", 
            "", 
            "Python Files (*.py)"
        )
        if file_path:
            self.script_edit.setText(file_path)
            # Auto-set output directory to script directory if not set
            if not self.output_edit.text():
                script_dir = os.path.dirname(file_path)
                self.output_edit.setText(os.path.join(script_dir, "dist"))
    
    def select_output_dir(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory"
        )
        if dir_path:
            self.output_edit.setText(dir_path)
    
    def select_icon(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Icon File",
            "",
            "Icon Files (*.ico);;All Files (*)"
        )
        if file_path:
            self.icon_edit.setText(file_path)
    
    def add_additional_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Additional Files",
            "",
            "All Files (*)"
        )
        for file_path in files:
            item = QListWidgetItem(file_path)
            self.additional_list.addItem(item)
    
    def remove_additional_files(self):
        for item in self.additional_list.selectedItems():
            self.additional_list.takeItem(self.additional_list.row(item))
    
    def start_build(self):
        # Validate inputs
        script_path = self.script_edit.text()
        if not script_path:
            QMessageBox.warning(self, "Error", "Please select a Python script to build.")
            return
        
        if not os.path.exists(script_path):
            QMessageBox.warning(self, "Error", "Selected Python script does not exist.")
            return
        
        output_dir = self.output_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "Error", "Please select an output directory.")
            return
        
        icon_path = self.icon_edit.text()
        if icon_path and not os.path.exists(icon_path):
            QMessageBox.warning(self, "Error", "Selected icon file does not exist.")
            return
        
        # Get additional files
        additional_files = []
        for i in range(self.additional_list.count()):
            item = self.additional_list.item(i)
            additional_files.append(item.text())
        
        # Check if PyInstaller is available
        try:
            subprocess.run(['pyinstaller', '--version'], 
                         capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            reply = QMessageBox.question(
                self,
                "PyInstaller Not Found",
                "PyInstaller is not installed. Would you like to install it now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.install_pyinstaller()
            return
        
        # Disable build button during build
        self.build_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        
        # Clear output
        self.output_text.clear()
        self.status_label.setText("Building...")
        
        # Start build thread
        self.build_thread = BuildThread(
            script_path=script_path,
            output_dir=output_dir,
            icon_path=icon_path,
            console=self.console_check.isChecked(),
            onefile=self.onefile_check.isChecked(),
            additional_files=additional_files
        )
        
        self.build_thread.output_signal.connect(self.update_output)
        self.build_thread.finished_signal.connect(self.build_finished)
        self.build_thread.start()
    
    def install_pyinstaller(self):
        """Install PyInstaller"""
        try:
            self.status_label.setText("Installing PyInstaller...")
            subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'], 
                         check=True, capture_output=True, text=True)
            QMessageBox.information(self, "Success", "PyInstaller installed successfully!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to install PyInstaller: {str(e)}")
        finally:
            self.status_label.setText("Ready")
    
    def update_output(self, message):
        self.output_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.output_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def build_finished(self, success, message):
        self.progress_bar.setVisible(False)
        self.build_btn.setEnabled(True)
        
        if success:
            self.status_label.setText("Build completed successfully!")
            QMessageBox.information(self, "Success", message)
            
            # Open output directory in file explorer
            output_dir = self.output_edit.text()
            if output_dir and os.path.exists(output_dir):
                try:
                    if os.name == 'nt':  # Windows
                        os.startfile(output_dir)
                    elif os.name == 'posix':  # macOS, Linux
                        subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', output_dir])
                except Exception as e:
                    self.update_output(f"Could not open output directory: {e}")
        else:
            self.status_label.setText("Build failed!")
            QMessageBox.critical(self, "Build Failed", message)

def main():
    app = QApplication(sys.argv)
    window = PyInstallerGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()