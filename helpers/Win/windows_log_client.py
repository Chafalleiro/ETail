# windows_log_client.py --host 127.0.0.1 --password "patata"
import socket
import ssl
import hashlib
import time
import threading
import os
import sys
import signal
import traceback
from pathlib import Path
from datetime import datetime
import configparser
import queue
import json
import gzip
import win32file
import win32event
import win32con
import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class WindowsLogClient:
    def __init__(self, server_host='', server_port=0, password='', log_files=None, 
                 use_ssl=True, encoding='utf-8', tail_lines=50, 
                 buffer_size=10000, buffer_file=None,
                 max_reconnect_attempts=10, reconnect_delay=5):
        
        # Basic attributes
        self.server_host = server_host
        self.server_port = server_port
        self.password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self.log_files = log_files if isinstance(log_files, list) else (log_files or [])
        self.use_ssl = use_ssl
        self.encoding = encoding
        self.tail_lines = tail_lines
        
        # Resilience attributes
        self.buffer_size = buffer_size
        self.buffer_file = buffer_file or os.path.join(os.getenv('TEMP', ''), 'log_client_buffer.json.gz')
        self.message_buffer = queue.Queue(maxsize=buffer_size)
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay = reconnect_delay
        self.reconnect_attempts = 0
        self.last_reconnect_attempt = 0
        
        # Connection attributes
        self.socket = None
        self.connected = False
        self.running = False
        self.file_handles = {}
        self.change_handles = {}
        self.client_name = os.environ.get('COMPUTERNAME', 'Windows-PC')
        
    def load_config(self, config_file=None):
        """Load configuration from config file"""
        if config_file is None:
            config_file = os.path.join(os.path.dirname(__file__), 'windows-log-monitor.conf')
            
        if not os.path.exists(config_file):
            return False
            
        try:
            config = configparser.ConfigParser()
            config.read(config_file)
            
            # Server settings
            if config.has_section('Server'):
                if config.has_option('Server', 'host'):
                    self.server_host = config.get('Server', 'host')
                if config.has_option('Server', 'port'):
                    self.server_port = config.getint('Server', 'port')
                if config.has_option('Server', 'password'):
                    password = config.get('Server', 'password')
                    self.password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Log files
            if config.has_section('LogFiles'):
                if config.has_option('LogFiles', 'paths'):
                    paths = config.get('LogFiles', 'paths')
                    self.log_files = [path.strip() for path in paths.split(',') if path.strip()]
            
            # SSL settings
            if config.has_section('SSL'):
                if config.has_option('SSL', 'use_ssl'):
                    self.use_ssl = config.getboolean('SSL', 'use_ssl')
            
            # Client settings
            if config.has_section('Client'):
                if config.has_option('Client', 'encoding'):
                    self.encoding = config.get('Client', 'encoding')
                if config.has_option('Client', 'tail_lines'):
                    self.tail_lines = config.getint('Client', 'tail_lines')
                # Resilience settings
                if config.has_option('Client', 'buffer_size'):
                    self.buffer_size = config.getint('Client', 'buffer_size')
                if config.has_option('Client', 'max_reconnect_attempts'):
                    self.max_reconnect_attempts = config.getint('Client', 'max_reconnect_attempts')
                if config.has_option('Client', 'reconnect_delay'):
                    self.reconnect_delay = config.getfloat('Client', 'reconnect_delay')
            
            print(f"✓ Loaded configuration from {config_file}")
            return True
            
        except Exception as e:
            print(f"❌ Error loading config file {config_file}: {e}")
            return False

    def buffer_log_line(self, log_line, source_file):
        """Buffer log line when server is down"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'line': log_line,
                'source': source_file,
                'client': self.client_name
            }
            
            # Try in-memory buffer first
            if self.message_buffer.full():
                # Save to disk if memory buffer is full
                self._save_to_disk_buffer(log_entry)
            else:
                self.message_buffer.put(log_entry)
                
            return True
        except Exception as e:
            print(f"❌ Failed to buffer log line: {e}")
            return False
    
    def _save_to_disk_buffer(self, log_entry):
        """Save log entry to disk when memory buffer is full"""
        try:
            # Create compressed buffer file
            buffer_path = Path(self.buffer_file)
            buffer_path.parent.mkdir(parents=True, exist_ok=True)
            
            mode = 'ab' if buffer_path.exists() else 'wb'
            with gzip.open(self.buffer_file, mode) as f:
                f.write((json.dumps(log_entry) + '\n').encode('utf-8'))
                
        except Exception as e:
            print(f"❌ Failed to save to disk buffer: {e}")
    
    def _load_disk_buffer(self):
        """Load buffered messages from disk"""
        try:
            if not os.path.exists(self.buffer_file):
                return
                
            with gzip.open(self.buffer_file, 'rb') as f:
                for line in f:
                    log_entry = json.loads(line.decode('utf-8').strip())
                    if not self.message_buffer.full():
                        self.message_buffer.put(log_entry)
            
            # Clear the file after loading
            os.remove(self.buffer_file)
            print("✓ Loaded buffered messages from disk")
            
        except Exception as e:
            print(f"❌ Failed to load disk buffer: {e}")
    
    def attempt_reconnection(self):
        """Attempt to reconnect to server with backoff"""
        current_time = time.time()
        
        # Rate limiting reconnection attempts
        if current_time - self.last_reconnect_attempt < self.reconnect_delay:
            return False
            
        self.last_reconnect_attempt = current_time
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            print(f"❌ Max reconnection attempts ({self.max_reconnect_attempts}) exceeded")
            return False
        
        print(f"🔄 Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}...")
        
        try:
            if self.connect():
                print("✅ Reconnected successfully!")
                self.reconnect_attempts = 0
                return True
            else:
                # Exponential backoff
                self.reconnect_delay = min(self.reconnect_delay * 1.5, 300)  # Max 5 minutes
                print(f"⏳ Next reconnection in {self.reconnect_delay:.1f}s")
                return False
        except Exception as e:
            print(f"❌ Reconnection failed: {e}")
            return False
    
    def flush_buffered_messages(self):
        """Send all buffered messages after reconnection"""
        if self.message_buffer.empty():
            return True
            
        print(f"📦 Flushing {self.message_buffer.qsize()} buffered messages...")
        successful_flush = True
        
        while not self.message_buffer.empty():
            try:
                log_entry = self.message_buffer.get_nowait()
                if not self.send_log_line_direct(log_entry['line'], log_entry['source']):
                    # If sending fails, put back in queue and stop
                    self.message_buffer.put(log_entry)
                    successful_flush = False
                    break
                time.sleep(0.01)  # Small delay to avoid overwhelming server
            except queue.Empty:
                break
        
        # Try to load any disk-buffered messages
        self._load_disk_buffer()
        
        remaining = self.message_buffer.qsize()
        if remaining > 0:
            print(f"⚠️  {remaining} messages still in buffer")
        else:
            print("✅ All buffered messages sent successfully")
            
        return successful_flush

    def check_permissions(self):
        """Check if we have permission to read all log files"""
        inaccessible_files = []
        for log_file in self.log_files:
            if not os.path.exists(log_file):
                inaccessible_files.append(f"{log_file} (does not exist)")
                continue
                
            try:
                # Try to open the file for reading
                with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                    f.read(1)  # Try to read one character
            except PermissionError as e:
                inaccessible_files.append(f"{log_file} (no read permission: {e})")
            except Exception as e:
                inaccessible_files.append(f"{log_file} (error: {e})")
        
        return inaccessible_files
    
    def detect_encoding(self, file_path):
        """Detect file encoding"""
        try:
            # Try common encodings
            encodings = ['utf-8', 'utf-16', 'latin-1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        f.read(1024)
                    return encoding
                except UnicodeDecodeError:
                    continue
            return 'utf-8'
        except PermissionError:
            print(f"❌ Permission denied reading {file_path}")
            return 'utf-8'
    
    def connect(self):
        """Connect to the log server"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            
            if self.use_ssl:
                context = ssl.create_default_context()
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
                self.socket = context.wrap_socket(self.socket, server_hostname=self.server_host)
                print("✓ SSL/TLS connection established")
            else:
                print("Using plaintext connection")
            
            print(f"Connecting to {self.server_host}:{self.server_port}...")
            self.socket.connect((self.server_host, self.server_port))
            print(f"✓ Connected! Local port: {self.socket.getsockname()[1]}")
            
            if self.password_hash:
                self.socket.send(self.password_hash.encode('utf-8'))
                response = self.socket.recv(1024).decode('utf-8')
                if response != "AUTH_SUCCESS":
                    raise Exception(f"Authentication failed. Server response: {response}")
                print("✓ Authentication successful")
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None

    def send_log_line_direct(self, log_line, source_file):
        """Send a log line directly (without buffering) - used for flushing buffer"""
        if not self.connected:
            return False
            
        try:
            formatted_line = f"[{source_file}] {log_line}"
            
            if not formatted_line.endswith('\n'):
                formatted_line += '\n'
                
            self.socket.send(formatted_line.encode('utf-8'))
            
            self.socket.settimeout(5)
            confirmation = self.socket.recv(4096).decode('utf-8').strip()
            self.socket.settimeout(10)
            
            if confirmation != formatted_line.strip():
                print(f"Confirmation mismatch. Sent: {formatted_line.strip()}, Received: {confirmation}")
                return False
                
            return True
            
        except socket.timeout:
            print("⚠️ Timeout waiting for confirmation")
            return False
        except Exception as e:
            print(f"Error sending log line: {e}")
            self.connected = False
            return False
    
    def send_log_line(self, log_line, source_file):
        """Send a log line to the server with reconnection and buffering"""
        if not self.connected:
            # Buffer the message and attempt reconnection
            self.buffer_log_line(log_line, source_file)
            if not self.attempt_reconnection():
                return False
            else:
                # We reconnected, now flush buffer and send this message
                self.flush_buffered_messages()
        
        try:
            formatted_line = f"[{source_file}] {log_line}"
            
            if not formatted_line.endswith('\n'):
                formatted_line += '\n'
                
            self.socket.send(formatted_line.encode('utf-8'))
            
            self.socket.settimeout(5)
            confirmation = self.socket.recv(4096).decode('utf-8').strip()
            self.socket.settimeout(10)
            
            if confirmation != formatted_line.strip():
                print(f"⚠️ Confirmation mismatch. Sent: {formatted_line.strip()}, Received: {confirmation}")
                # Buffer the message as we're not sure it was received
                self.buffer_log_line(log_line, source_file)
                self.connected = False
                return False
                
            return True
            
        except (socket.timeout, socket.error, ConnectionError, BrokenPipeError) as e:
            print(f"⚠️ Connection error: {e}")
            self.buffer_log_line(log_line, source_file)
            self.connected = False
            self.disconnect()
            return False
        except Exception as e:
            print(f"❌ Error sending log line: {e}")
            self.buffer_log_line(log_line, source_file)
            self.connected = False
            return False
    
    def tail_file(self, file_path, lines=50):
        """Tail a file - get last N lines (Windows optimized)"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return []
                
            encoding = self.detect_encoding(file_path)
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                return []
            
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                # For small files, just read all lines
                if file_size < 1024 * 1024:  # 1MB
                    all_lines = f.readlines()
                    return [line.strip() for line in all_lines[-lines:] if line.strip()]
                
                # For larger files, seek from the end
                f.seek(0, 2)
                position = f.tell()
                lines_found = []
                buffer_size = 8192
                
                while position > 0 and len(lines_found) < lines:
                    # Move position back
                    position = max(0, position - buffer_size)
                    f.seek(position)
                    
                    # Read and process chunk
                    chunk = f.read(min(buffer_size, file_size - position))
                    lines_found = chunk.splitlines() + lines_found
                    
                    # If we have enough lines, break
                    if len(lines_found) >= lines:
                        lines_found = lines_found[-lines:]
                        break
                
                return [line.strip() for line in lines_found if line.strip()]
                
        except PermissionError as e:
            print(f"❌ Permission denied reading {file_path}: {e}")
            return []
        except Exception as e:
            print(f"Error tailing file {file_path}: {e}")
            return []
    
    def setup_file_monitoring(self):
        """Set up file monitoring using Windows change notifications"""
        self.file_handles = {}
        self.change_handles = {}
        accessible_files = 0
        
        for log_file in self.log_files:
            file_path = Path(log_file)
            if not file_path.exists():
                print(f"⚠️  Log file not found: {log_file}")
                continue
            
            try:
                # Open file for reading
                file_handle = win32file.CreateFile(
                    str(file_path),
                    win32file.GENERIC_READ,
                    win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE,
                    None,
                    win32file.OPEN_EXISTING,
                    win32file.FILE_ATTRIBUTE_NORMAL,
                    None
                )
                
                # Create change notification handle
                dir_path = str(file_path.parent)
                change_handle = win32file.FindFirstChangeNotification(
                    dir_path,
                    False,  # Watch directory only, not subtree
                    win32con.FILE_NOTIFY_CHANGE_LAST_WRITE | 
                    win32con.FILE_NOTIFY_CHANGE_SIZE |
                    win32con.FILE_NOTIFY_CHANGE_FILE_NAME
                )
                
                self.file_handles[log_file] = {
                    'handle': file_handle,
                    'path': str(file_path),
                    'size': win32file.GetFileSize(file_handle),
                    'position': 0
                }
                
                self.change_handles[log_file] = change_handle
                
                print(f"📁 Monitoring: {log_file}")
                accessible_files += 1
                
            except Exception as e:
                print(f"❌ Error setting up monitoring for {log_file}: {e}")
        
        return accessible_files > 0
    
    def read_new_lines(self, file_info):
        """Read new lines from a file using Windows API"""
        try:
            file_handle = file_info['handle']
            current_position = file_info['position']
            current_size = win32file.GetFileSize(file_handle)
            
            # Check if file was truncated or rotated
            if current_size < current_position:
                current_position = 0
                file_info['position'] = 0
            
            # Read new data if available
            if current_size > current_position:
                win32file.SetFilePointer(file_handle, current_position, win32file.FILE_BEGIN)
                
                bytes_to_read = current_size - current_position
                hr, data = win32file.ReadFile(file_handle, bytes_to_read)
                
                if data:
                    try:
                        text = data.decode(self.encoding, errors='replace')
                        lines = [line.strip() for line in text.splitlines() if line.strip()]
                        file_info['position'] = current_position + len(data)
                        return lines
                    except Exception as e:
                        print(f"Error decoding data from {file_info['path']}: {e}")
            
            return []
            
        except Exception as e:
            print(f"Error reading from {file_info['path']}: {e}")
            return []
    
    def monitor_logs(self, poll_interval=1):
        """Monitor log files with reconnection and buffering support"""
        print(f"🚀 Starting log file monitoring on {self.client_name}...")
        
        # Check permissions first
        inaccessible_files = self.check_permissions()
        if inaccessible_files:
            print("⚠️  Permission issues found:")
            for file_info in inaccessible_files:
                print(f"   - {file_info}")
        
        print(f"📁 Files: {', '.join(self.log_files)}")
        print(f"⏰ Poll interval: {poll_interval} seconds")
        print(f"💾 Buffer size: {self.buffer_size} messages")
        print("🛑 Use Ctrl+C to stop monitoring")
        
        try:
            # Connect to server
            if not self.connect():
                print("❌ Failed to connect to server")
                return
            
            # Load any previously buffered messages
            self._load_disk_buffer()
            
            # Flush any buffered messages from previous session
            if not self.message_buffer.empty():
                print("🔄 Flushing messages from previous session...")
                self.flush_buffered_messages()
            
            # Send startup message
            startup_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{self.client_name}] "
                f"[MONITOR_START] Starting log file monitoring: {', '.join(self.log_files)}"
            )
            
            if self.connected:
                self.send_log_line(startup_message, "SYSTEM")
            
            # Send initial tail of each accessible file
            for log_file in self.log_files:
                if os.path.exists(log_file):
                    initial_lines = self.tail_file(log_file, self.tail_lines)
                    for line in initial_lines:
                        if self.connected:
                            self.send_log_line(line, f"INITIAL:{log_file}")
                    print(f"📊 Sent {len(initial_lines)} initial lines from {log_file}")
                else:
                    print(f"⚠️  Skipping initial tail for {log_file} (file not found)")
            
            print("📈 Now monitoring for new lines...")
            
            # Set up file monitoring
            if not self.setup_file_monitoring():
                print("❌ No accessible log files to monitor")
                return
            
            self.running = True
            iteration = 0
            
            while self.running:
                try:
                    iteration += 1
                    
                    # Attempt reconnection if disconnected and have buffered messages
                    if not self.connected and not self.message_buffer.empty():
                        if self.attempt_reconnection():
                            self.flush_buffered_messages()
                    
                    # Check for file changes using Windows notifications
                    if self.change_handles:
                        handles = list(self.change_handles.values())
                        result = win32event.WaitForMultipleObjects(
                            handles, False, int(poll_interval * 1000)
                        )
                        
                        if result != win32event.WAIT_TIMEOUT:
                            changed_index = result - win32event.WAIT_OBJECT_0
                            if 0 <= changed_index < len(handles):
                                # Find which file changed
                                changed_files = list(self.change_handles.keys())
                                changed_file = changed_files[changed_index]
                                
                                # Read new lines from changed file
                                file_info = self.file_handles.get(changed_file)
                                if file_info:
                                    new_lines = self.read_new_lines(file_info)
                                    for line in new_lines:
                                        if not self.running:
                                            break
                                        self.send_log_line(line, changed_file)
                                
                                # Reset the change notification
                                win32file.FindNextChangeNotification(handles[changed_index])
                    
                    # Enhanced heartbeat with buffer status
                    if iteration % 30 == 0 and self.running:
                        buffer_size = self.message_buffer.qsize()
                        status = "CONNECTED" if self.connected else f"DISCONNECTED ({buffer_size} buffered)"
                        
                        heartbeat = (
                            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{self.client_name}] "
                            f"[HEARTBEAT] Status: {status}, Iteration: {iteration}, Buffer: {buffer_size}"
                        )
                        
                        if self.connected:
                            self.send_log_line(heartbeat, "SYSTEM")
                        else:
                            print(f"💓 Heartbeat (disconnected) - {buffer_size} messages buffered")
                    
                    time.sleep(0.1)
                    
                except Exception as e:
                    if self.running:
                        print(f"❌ Error in monitoring loop: {e}")
                    time.sleep(poll_interval)
            
            # Send shutdown message
            if self.connected:
                shutdown_message = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{self.client_name}] "
                    f"[MONITOR_STOP] Log file monitoring stopped"
                )
                self.send_log_line(shutdown_message, "SYSTEM")
            
            print("✅ Log monitoring stopped")
            
        except Exception as e:
            print(f"💥 FATAL ERROR in monitor_logs: {e}")
            traceback.print_exc()
        finally:
            # Clean up Windows handles
            for file_info in self.file_handles.values():
                try:
                    win32file.CloseHandle(file_info['handle'])
                except:
                    pass
            
            for change_handle in self.change_handles.values():
                try:
                    win32file.FindCloseChangeNotification(change_handle)
                except:
                    pass
            
            self.file_handles.clear()
            self.change_handles.clear()
            self.disconnect()
    
    def stop_monitoring(self):
        """Stop the monitoring"""
        print("\n🛑 Stopping monitor...")
        self.running = False

    def start_monitoring(self, poll_interval=1):
        """Start monitoring in a separate thread"""
        monitor_thread = threading.Thread(
            target=self.monitor_logs, 
            args=(poll_interval,),
            daemon=False
        )
        monitor_thread.start()
        return monitor_thread

# Global client instance for signal handling
windows_client_instance = None

def windows_signal_handler(sig, frame):
    """Handle termination signals"""
    print(f'\n🛑 Received signal {sig}, shutting down gracefully...')
    if windows_client_instance:
        windows_client_instance.stop_monitoring()
    time.sleep(1)
    sys.exit(0)

def create_sample_config():
    """Create a sample configuration file"""
    sample_config = """[Server]
# Server connection details
host = your-log-server.com
port = 21327
password = your-secret-password

[LogFiles]
# Comma-separated list of log files to monitor
# Common Windows log locations:
paths = C:\\Windows\\Logs\\Application.evtx, C:\\Windows\\Logs\\System.evtx, C:\\ProgramData\\YourApp\\logs\\app.log

[SSL]
# Use SSL/TLS for secure connection (true/false)
use_ssl = true

[Client]
# File encoding
encoding = utf-8

# Number of recent lines to send when starting
tail_lines = 50

# Resilience settings
buffer_size = 10000
max_reconnect_attempts = 10
reconnect_delay = 5
"""
    config_path = 'windows-log-monitor.conf'
    try:
        with open(config_path, 'w') as f:
            f.write(sample_config)
        print(f"✓ Sample configuration created at {config_path}")
        print("⚠️  Remember to edit the file with your actual settings!")
    except Exception as e:
        print(f"❌ Error creating sample config: {e}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows Log File to Log Server Client')
    parser.add_argument('--host', help='Server hostname (overrides config file)')
    parser.add_argument('--port', type=int, help='Server port (overrides config file)')
    parser.add_argument('--password', help='Server password (overrides config file)')
    parser.add_argument('--log-files', nargs='+', 
                       help='Log files to monitor (space separated, overrides config file)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL (overrides config file)')
    parser.add_argument('--poll-interval', type=float, default=1.0, 
                       help='Polling interval in seconds (default: 1.0)')
    parser.add_argument('--tail-lines', type=int, default=50,
                       help='Number of recent lines to send initially (default: 50)')
    parser.add_argument('--encoding', default='utf-8',
                       help='File encoding (default: utf-8)')
    parser.add_argument('--config', 
                       help='Configuration file path')
    parser.add_argument('--create-sample-config', action='store_true',
                       help='Create a sample configuration file and exit')
    
    args = parser.parse_args()
    
    # Create sample config if requested
    if args.create_sample_config:
        create_sample_config()
        sys.exit(0)
    
    global windows_client_instance
    
    # Create client with default values
    client = WindowsLogClient()
    
    # Load configuration from file if specified
    if args.config:
        config_loaded = client.load_config(args.config)
    
    # Override with command line arguments if provided
    if args.host:
        client.server_host = args.host
    if args.port:
        client.server_port = args.port
    if args.password:
        client.password_hash = hashlib.sha256(args.password.encode()).hexdigest()
    if args.log_files:
        client.log_files = args.log_files
    if args.no_ssl:
        client.use_ssl = False
    if args.encoding:
        client.encoding = args.encoding
    if args.tail_lines:
        client.tail_lines = args.tail_lines
    
    # Validate required settings
    if not client.server_host:
        print("❌ Server host is required. Use --host or config file.")
        sys.exit(1)
    if not client.server_port:
        print("❌ Server port is required. Use --port or config file.")
        sys.exit(1)
    if not client.password_hash:
        print("❌ Password is required. Use --password or config file.")
        sys.exit(1)
    if not client.log_files:
        print("❌ Log files are required. Use --log-files or config file.")
        sys.exit(1)
    
    windows_client_instance = client
    
    # Print configuration summary
    print("\n📋 Configuration Summary:")
    print(f"   Server: {client.server_host}:{client.server_port}")
    print(f"   SSL: {'Enabled' if client.use_ssl else 'Disabled'}")
    print(f"   Log Files: {len(client.log_files)} files")
    for log_file in client.log_files:
        print(f"     - {log_file}")
    print(f"   Initial Lines: {client.tail_lines}")
    print(f"   Encoding: {client.encoding}")
    print(f"   Buffer Size: {client.buffer_size} messages")
    print(f"   Max Reconnect Attempts: {client.max_reconnect_attempts}")
    print()
    
    # Register signal handlers
    signal.signal(signal.SIGINT, windows_signal_handler)
    
    print(f"🔍 Monitoring log files on {client.client_name}...")
    print(f"📁 Files: {', '.join(client.log_files)}")
    print(f"⏰ Poll interval: {args.poll_interval} seconds")
    print(f"📊 Initial lines: {client.tail_lines}")
    print(f"💾 Buffer size: {client.buffer_size} messages")
    print("🛑 Press Ctrl+C to stop monitoring")
    
    try:
        # Start monitoring
        monitor_thread = client.start_monitoring(poll_interval=args.poll_interval)
        
        # Keep main thread alive
        while client.running and monitor_thread.is_alive():
            time.sleep(0.5)
            
        print("✅ Monitoring completed normally")
            
    except KeyboardInterrupt:
        windows_signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        client.stop_monitoring()
    finally:
        client.running = False

if __name__ == "__main__":
    main()