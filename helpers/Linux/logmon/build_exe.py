# build_exe.py
import os
import sys
import subprocess
import platform
from pathlib import Path

def build_executables():
    """Build standalone executables for all clients"""
    
    # Determine platform
    system = platform.system().lower()
    
    # Clients to build
    clients = {
        'windows_event_client.py': 'WindowsEventMonitor',
        'windows_service_monitor.py': 'WindowsServiceMonitor', 
        'linux_log_client.py': 'LinuxLogMonitor'
    }
    
    # PyInstaller options
    common_options = [
        '--onefile',
        '--console',
        '--clean',
        '--noconfirm'
    ]
    
    # Platform-specific options
    if system == 'windows':
        common_options.extend(['--uac-admin'])  # Request admin privileges on Windows
    
    print(f"Building executables for {system}...")
    
    for client_file, output_name in clients.items():
        if not Path(client_file).exists():
            print(f"⚠️  Skipping {client_file} - file not found")
            continue
            
        # Skip Linux client on Windows and vice versa (optional)
        if 'linux' in client_file.lower() and system != 'linux':
            print(f"⚠️  Skipping {client_file} - not for this platform")
            continue
        if 'windows' in client_file.lower() and system != 'windows':
            print(f"⚠️  Skipping {client_file} - not for this platform")
            continue
            
        print(f"🔨 Building {output_name} from {client_file}...")
        
        # Build command
        cmd = [
            'pyinstaller',
            *common_options,
            '--name', output_name,
            client_file
        ]
        
        try:
            # Run pyinstaller
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ Successfully built {output_name}")
            else:
                print(f"❌ Failed to build {output_name}:")
                print(result.stderr)
                
        except Exception as e:
            print(f"❌ Error building {output_name}: {e}")
    
    print("\n📦 Build process completed!")
    print("Executables are in the 'dist' directory")

def install_pyinstaller():
    """Install PyInstaller if not available"""
    try:
        import PyInstaller
        print("✅ PyInstaller is already installed")
    except ImportError:
        print("Installing PyInstaller...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])

if __name__ == "__main__":
    # Make sure we're in the virtual environment
    if not hasattr(sys, 'real_prefix') and not sys.prefix == sys.base_prefix:
        print("⚠️  Not running in a virtual environment.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    install_pyinstaller()
    build_executables()
