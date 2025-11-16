# windows_service_monitor.py
#python process_mon.py --host 127.0.0.1 --password "patata" --service-name MystLauncherHelper2 --exe-name myst-launcher-svc.exe
import socket
import ssl
import hashlib
import time
import threading
from datetime import datetime, timedelta
import win32evtlog
import win32evtlogutil
import win32con
import win32service
import win32serviceutil
import psutil
import sys
import signal
import traceback
import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class WindowsServiceMonitor:
    def __init__(self, server_host, server_port, password, 
                 target_service_name, target_exe_name, 
                 monitor_processes=None,  # New: list of processes to monitor
                 server_name='localhost', use_ssl=True):
        self.server_host = server_host
        self.server_port = server_port
        self.password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self.target_service_name = target_service_name
        self.target_exe_name = target_exe_name
        self.monitor_processes = monitor_processes or []  # Processes to monitor count for
        self.server_name = server_name
        self.use_ssl = use_ssl
        self.socket = None
        self.connected = False
        self.running = False
        self.last_event_id = None
        self.process_counts = {}  # Track counts for each monitored process
        self.max_process_threshold = 5  # Default threshold
        
    def connect(self):
        """Connect to the log server"""
        try:
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)  # 10 second timeout
            
            # Wrap with SSL if enabled
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
            
            # Authenticate
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
        print("Disconnected from server")
    
    def send_log_line(self, log_line):
        """Send a log line to the server"""
        if not self.connected:
            print("Not connected to server")
            return False
            
        try:
            # Ensure the line ends with newline for consistency
            if not log_line.endswith('\n'):
                log_line += '\n'
                
            self.socket.send(log_line.encode('utf-8'))
            
            # Wait for confirmation
            confirmation = self.socket.recv(4096).decode('utf-8').strip()
            
            if confirmation != log_line.strip():
                print(f"Confirmation mismatch. Sent: {log_line.strip()}, Received: {confirmation}")
                return False
                
            return True
            
        except Exception as e:
            print(f"Error sending log line: {e}")
            self.connected = False
            return False

    def check_service_status(self):
        """Check the current status of the target service"""
        try:
            sc_manager = win32service.OpenSCManager(self.server_name, None, win32service.SC_MANAGER_ALL_ACCESS)
            service_handle = win32service.OpenService(sc_manager, self.target_service_name, win32service.SERVICE_QUERY_STATUS)
            
            status = win32service.QueryServiceStatus(service_handle)
            service_state = status[1]
            
            win32service.CloseServiceHandle(service_handle)
            win32service.CloseServiceHandle(sc_manager)
            
            state_names = {
                win32service.SERVICE_STOPPED: "STOPPED",
                win32service.SERVICE_START_PENDING: "START_PENDING",
                win32service.SERVICE_STOP_PENDING: "STOP_PENDING",
                win32service.SERVICE_RUNNING: "RUNNING",
                win32service.SERVICE_CONTINUE_PENDING: "CONTINUE_PENDING",
                win32service.SERVICE_PAUSE_PENDING: "PAUSE_PENDING",
                win32service.SERVICE_PAUSED: "PAUSED"
            }
            
            return state_names.get(service_state, f"UNKNOWN({service_state})")
            
        except Exception as e:
            print(f"Error checking service status: {e}")
            return f"ERROR: {str(e)}"

    def count_process_instances(self, process_name):
        """Count how many instances of a specific process are running"""
        try:
            count = 0
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    if (proc.info['name'] and process_name.lower() in proc.info['name'].lower()) or \
                       (proc.info['exe'] and process_name.lower() in proc.info['exe'].lower()):
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return count
        except Exception as e:
            print(f"Error counting {process_name} processes: {e}")
            return 0

    def get_recent_service_events(self, last_minutes=5):
        """Get recent service-related events from System log"""
        events_to_send = []
        try:
            hand = win32evtlog.OpenEventLog(self.server_name, "System")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
            
            for event in events:
                # Check if event is recent enough
                event_time = event.TimeGenerated
                if event_time < cutoff_time:
                    break
                    
                # Look for service control events (Event ID 7036)
                if event.EventID == 7036:
                    try:
                        event_message = win32evtlogutil.SafeFormatMessage(event, "System")
                        if self.target_service_name.lower() in event_message.lower():
                            formatted_event = self.format_service_event(event, event_message)
                            events_to_send.append(formatted_event)
                    except:
                        pass
                        
        except Exception as e:
            print(f"Error reading service events: {e}")
            
        return events_to_send

    def format_service_event(self, event, message):
        """Format a service event as a string"""
        time_generated = event.TimeGenerated.Format()
        computer = event.ComputerName
        
        # Clean up the message
        message = ' '.join(message.split())
        
        return f"[{time_generated}] [{computer}] [SERVICE_EVENT] {message}"

    def get_recent_application_events(self, last_minutes=5):
        """Get recent application events related to the target executable"""
        events_to_send = []
        try:
            hand = win32evtlog.OpenEventLog(self.server_name, "Application")
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            cutoff_time = datetime.now() - timedelta(minutes=last_minutes)
            
            for event in events:
                # Check if event is recent enough
                event_time = event.TimeGenerated
                if event_time < cutoff_time:
                    break
                    
                # Look for events from the target executable
                if (event.SourceName and 
                    self.target_exe_name.lower() in event.SourceName.lower()):
                    
                    try:
                        message = win32evtlogutil.SafeFormatMessage(event, "Application")
                        message = ' '.join(message.split())
                    except:
                        message = "Could not retrieve message"
                    
                    formatted_event = (
                        f"[{event.TimeGenerated.Format()}] [{event.ComputerName}] "
                        f"[APP_EVENT] [{event.SourceName}] [EventID: {event.EventID}] {message}"
                    )
                    events_to_send.append(formatted_event)
                        
        except Exception as e:
            print(f"Error reading application events: {e}")
            
        return events_to_send

    def monitor_system(self, poll_interval=5):
        """Monitor the system for service status and process counts"""
        print(f"🚀 Starting system monitoring for:")
        print(f"   Service: '{self.target_service_name}'")
        print(f"   Executable: '{self.target_exe_name}'")
        if self.monitor_processes:
            print(f"   Monitored processes: {', '.join(self.monitor_processes)}")
        print(f"   Poll interval: {poll_interval} seconds")
        
        try:
            # Send initial status
            initial_status = self.check_service_status()
            
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            computer = socket.gethostname()
            
            # Count all monitored processes initially
            initial_counts = {}
            for process in self.monitor_processes:
                initial_counts[process] = self.count_process_instances(process)
            
            initial_message = (
                f"[{timestamp}] [{computer}] [MONITOR_START] "
                f"Service: {initial_status}, "
                f"Monitored processes: {initial_counts}"
            )
            
            if self.connected:
                if not self.send_log_line(initial_message):
                    print("❌ Failed to send initial message")
            
            print(f"📊 Initial status: Service={initial_status}, Process counts={initial_counts}")
            
            last_service_status = initial_status
            last_process_counts = initial_counts.copy()
            
            self.running = True
            iteration = 0
            
            while self.running:
                try:
                    iteration += 1
                    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Check service status
                    current_service_status = self.check_service_status()
                    if current_service_status != last_service_status:
                        status_message = (
                            f"[{current_time}] [{computer}] [SERVICE_STATUS_CHANGE] "
                            f"Service '{self.target_service_name}' changed: {last_service_status} → {current_service_status}"
                        )
                        print(f"🔄 {status_message}")
                        
                        if self.connected:
                            if not self.send_log_line(status_message):
                                print("⚠️  Failed to send status message")
                        
                        last_service_status = current_service_status
                    
                    # Check monitored processes
                    current_process_counts = {}
                    for process in self.monitor_processes:
                        current_process_counts[process] = self.count_process_instances(process)
                    
                    # Check for changes in process counts
                    for process, current_count in current_process_counts.items():
                        last_count = last_process_counts.get(process, 0)
                        
                        if current_count != last_count:
                            process_message = (
                                f"[{current_time}] [{computer}] [PROCESS_COUNT_CHANGE] "
                                f"Process '{process}' changed: {last_count} → {current_count}"
                            )
                            print(f"📈 {process_message}")
                            
                            if self.connected:
                                if not self.send_log_line(process_message):
                                    print("⚠️  Failed to send process message")
                            
                            # Alert if threshold exceeded
                            if current_count > self.max_process_threshold:
                                alert_message = (
                                    f"[{current_time}] [{computer}] [ALERT] "
                                    f"HIGH PROCESS COUNT for '{process}': {current_count} (threshold: {self.max_process_threshold})"
                                )
                                print(f"🚨 {alert_message}")
                                
                                if self.connected:
                                    self.send_log_line(alert_message)
                    
                    last_process_counts = current_process_counts.copy()
                    
                    # Every 10 iterations, check for recent events
                    if iteration % 10 == 0:
                        # Check for recent service events
                        service_events = self.get_recent_service_events(last_minutes=2)
                        for event in service_events:
                            print(f"📋 Service event: {event}")
                            if self.connected:
                                self.send_log_line(event)
                    
                    # Wait before next poll
                    time.sleep(poll_interval)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Monitoring stopped by user")
                    self.running = False
                    break
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    traceback.print_exc()
                    time.sleep(poll_interval)
            
            # Send shutdown message
            if self.connected:
                shutdown_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{computer}] [MONITOR_STOP] Monitoring stopped"
                self.send_log_line(shutdown_message)
            
            print("✅ Monitoring stopped")
            
        except Exception as e:
            print(f"💥 FATAL ERROR in monitor_system: {e}")
            traceback.print_exc()
        finally:
            self.disconnect()

    def start_monitoring(self, poll_interval=5):
        """Start monitoring in a separate thread"""
        # Use non-daemon thread to prevent the stdout lock issue
        monitor_thread = threading.Thread(
            target=self.monitor_system, 
            args=(poll_interval,),
            daemon=False  # Changed to False to prevent daemon thread issues
        )
        monitor_thread.start()
        return monitor_thread

def signal_handler(sig, frame):
    """Handle various termination signals including Ctrl+Break"""
    signal_names = {
        signal.SIGINT: "Ctrl+C", 
        signal.SIGTERM: "SIGTERM",
    }
    
    # On Windows, Ctrl+Break might come as SIGBREAK if available
    if hasattr(signal, 'SIGBREAK'):
        signal_names[signal.SIGBREAK] = "Ctrl+Break"
    
    signal_name = signal_names.get(sig, f"signal {sig}")
    
    print(f'\n🛑 Received {signal_name}, shutting down gracefully...')
    
    if client_instance:
        client_instance.stop_monitoring()
    
    # Quick exit to avoid hanging
    sys.exit(0)
def register_signal_handlers():
    """Register all possible signal handlers"""
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination
    
    # Windows-specific signals
    if hasattr(signal, 'SIGBREAK'):
        signal.signal(signal.SIGBREAK, signal_handler)  # Ctrl+Break
    
    # Try to set up console control handler for Windows
    try:
        if sys.platform == "win32":
            import ctypes
            # Define the console control handler type
            PHANDLER_ROUTINE = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
            
            @PHANDLER_ROUTINE
            def console_handler(ctrl_type):
                if ctrl_type in (0, 1, 2, 6):  # CTRL_C_EVENT, CTRL_BREAK_EVENT, etc.
                    print(f"\n🛑 Console control event {ctrl_type}, shutting down...")
                    shutdown_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{computer}] [MONITOR_STOP] Monitoring stopped"
                    self.send_log_line(shutdown_message)

                    shutdown_message = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{computer}] [MONITOR_STOP] Monitoring stopped"
                    self.send_log_line(shutdown_message)
                    if client_instance:
                        client_instance.stop_monitoring()
                    return True  # We handled it
                return False  # Let other handlers process it
            
            # Set the console control handler
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleCtrlHandler(console_handler, True)
    except Exception as e:
        print(f"Note: Could not set advanced console handler: {e}")

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows Service and Process Monitor')
    parser.add_argument('--host', default='localhost', help='Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=21327, help='Server port (default: 21327)')
    parser.add_argument('--password', required=True, help='Server password')
    parser.add_argument('--service-name', required=True, help='Name of the service to monitor')
    parser.add_argument('--exe-name', required=True, help='Name of the executable to monitor')
    parser.add_argument('--monitor-processes', type=str, default='', 
                       help='Comma-separated list of process names to monitor (e.g., "chrome.exe,notepad.exe")')
    parser.add_argument('--process-threshold', type=int, default=5, 
                       help='Alert threshold for process instances (default: 5)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL')
    parser.add_argument('--poll-interval', type=float, default=5.0, 
                       help='Polling interval in seconds (default: 5.0)')
    
    args = parser.parse_args()
    
    # Parse monitor processes
    monitor_processes = []
    if args.monitor_processes:
        monitor_processes = [p.strip() for p in args.monitor_processes.split(',') if p.strip()]
    
    # Create and start client
    client = WindowsServiceMonitor(
        server_host=args.host,
        server_port=args.port,
        password=args.password,
        target_service_name=args.service_name,
        target_exe_name=args.exe_name,
        monitor_processes=monitor_processes,
        use_ssl=not args.no_ssl
    )
    
    client.max_process_threshold = args.process_threshold
    
    # Connect to server
    if not client.connect():
        print("❌ Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print(f"🔍 Monitoring service: {args.service_name}")
    print(f"🔍 Monitoring executable: {args.exe_name}")
    print(f"📊 App alert threshold: {args.monitor_processes}")
    print(f"⏰ Poll interval: {args.poll_interval} seconds")
    print("🛑 Press Ctrl+C to stop monitoring")
    
    try:
        # Start monitoring (this will run in a separate thread)
        monitor_thread = client.start_monitoring(poll_interval=args.poll_interval)
        
        # Keep main thread alive while monitoring is running
        while client.running and monitor_thread.is_alive():
            time.sleep(1)
            
        print("✅ Monitoring completed normally")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitor...")
        client.running = False
        # Wait for monitoring thread to finish
        monitor_thread.join(timeout=10)
        print("✅ Monitoring stopped gracefully")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
    finally:
        client.running = False

if __name__ == "__main__":
    main()