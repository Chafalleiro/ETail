# windows_event_client.py
#python event_logger.py --host 127.0.0.1 --password "patata" --log-type Application
import socket
import ssl
import hashlib
import time
import threading
from datetime import datetime
import win32evtlog
import win32evtlogutil
import win32con
import sys
import signal
import traceback
import os
import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

class WindowsEventLogClient:
    def __init__(self, server_host, server_port, password, log_type="Application", 
                 server_name='localhost', use_ssl=True):
        self.server_host = server_host
        self.server_port = server_port
        self.password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self.log_type = log_type
        self.server_name = server_name
        self.use_ssl = use_ssl
        self.socket = None
        self.connected = False
        self.running = False
        self.last_event_id = None
        self.monitor_thread = None
        
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
            return False
            
        try:
            # Ensure the line ends with newline for consistency
            if not log_line.endswith('\n'):
                log_line += '\n'
                
            self.socket.send(log_line.encode('utf-8'))
            
            # Wait for confirmation with timeout
            self.socket.settimeout(5)
            confirmation = self.socket.recv(4096).decode('utf-8').strip()
            self.socket.settimeout(10)
            
            if confirmation != log_line.strip():
                print(f"Confirmation mismatch. Sent: {log_line.strip()}, Received: {confirmation}")
                return False
                
            return True
            
        except socket.timeout:
            print("⚠️ Timeout waiting for confirmation")
            return False
        except Exception as e:
            print(f"Error sending log line: {e}")
            self.connected = False
            return False
    
    def format_event(self, event):
        """Format a Windows event as a string"""
        try:
            # Get basic event information
            event_id = event.EventID & 0xFFFF  # Get the lower 16 bits for the event ID
            event_type = self.get_event_type(event.EventType)
            time_generated = event.TimeGenerated.Format()
            source = event.SourceName
            computer = event.ComputerName
            
            # Get the message string
            message = "No message available"
            try:
                message = win32evtlogutil.SafeFormatMessage(event, self.log_type)
                # Clean up the message - remove extra whitespace
                message = ' '.join(message.split())
            except Exception as e:
                message = f"Could not retrieve message: {e}"
            
            # Format the log line
            formatted_event = (
                f"[{time_generated}] [{computer}] [{event_type}] [{source}] "
                f"[EventID: {event_id}] {message}"
            )
            
            return formatted_event
            
        except Exception as e:
            print(f"Error formatting event: {e}")
            return f"[ERROR] Could not format event: {e}"
    
    def get_event_type(self, event_type):
        """Convert numeric event type to string"""
        event_types = {
            win32con.EVENTLOG_SUCCESS: "SUCCESS",
            win32con.EVENTLOG_ERROR_TYPE: "ERROR", 
            win32con.EVENTLOG_WARNING_TYPE: "WARNING",
            win32con.EVENTLOG_INFORMATION_TYPE: "INFO",
            win32con.EVENTLOG_AUDIT_SUCCESS: "AUDIT_SUCCESS",
            win32con.EVENTLOG_AUDIT_FAILURE: "AUDIT_FAILURE"
        }
        return event_types.get(event_type, f"UNKNOWN({event_type})")
    
    def get_initial_events(self, count=10):
        """Get recent events to start monitoring"""
        events_to_send = []
        try:
            hand = win32evtlog.OpenEventLog(self.server_name, self.log_type)
            flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, count)
            
            if events:
                # Store the most recent event ID
                self.last_event_id = events[0].RecordNumber
                print(f"📋 Established baseline with event ID: {self.last_event_id}")
                
                # Return events in chronological order (oldest first)
                for event in reversed(events):
                    events_to_send.append(event)
                        
        except Exception as e:
            print(f"Error reading initial events: {e}")
            traceback.print_exc()
            
        return events_to_send
    
    def get_new_events(self):
        """Get new events since last check"""
        events_to_send = []
        try:
            hand = win32evtlog.OpenEventLog(self.server_name, self.log_type)
            flags = win32evtlog.EVENTLOG_FORWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
            events = win32evtlog.ReadEventLog(hand, flags, 0)
            
            for event in events:
                if self.last_event_id is None or event.RecordNumber > self.last_event_id:
                    events_to_send.append(event)
                    self.last_event_id = event.RecordNumber
                        
        except Exception as e:
            print(f"Error reading new events: {e}")
            
        return events_to_send
    
    def monitor_events(self, poll_interval=2):
        """Continuously monitor for new events"""
        print(f"🚀 Starting event log monitoring for '{self.log_type}' log...")
        print(f"⏰ Poll interval: {poll_interval} seconds")
        
        try:
            # Send startup message
            startup_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{socket.gethostname()}] "
                f"[MONITOR_START] Starting {self.log_type} event log monitoring"
            )
            
            if self.connected:
                self.send_log_line(startup_message)
            
            # Get recent events to establish baseline
            print("Getting recent events to establish baseline...")
            recent_events = self.get_initial_events(5)
            
            for event in recent_events:
                formatted_event = self.format_event(event)
                print(f"📋 Recent event: {formatted_event}")
                
                if self.connected:
                    if not self.send_log_line(formatted_event):
                        print("⚠️ Failed to send recent event")
            
            print("📊 Baseline established, now monitoring for new events...")
            
            self.running = True
            iteration = 0
            
            while self.running:
                try:
                    iteration += 1
                    
                    # Check for new events
                    new_events = self.get_new_events()
                    
                    for event in new_events:
                        formatted_event = self.format_event(event)
                        print(f"📋 New event: {formatted_event}")
                        
                        if self.connected:
                            if not self.send_log_line(formatted_event):
                                print("⚠️ Failed to send event")
                    
                    # Every 10 iterations, send a heartbeat
                    if iteration % 10 == 0 and self.connected:
                        heartbeat = (
                            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{socket.gethostname()}] "
                            f"[HEARTBEAT] {self.log_type} monitor active - {iteration} iterations"
                        )
                        self.send_log_line(heartbeat)
                        print(f"💓 Heartbeat sent - iteration {iteration}")
                    
                    # Use shorter sleeps to be more responsive to Ctrl+C
                    for _ in range(int(poll_interval * 10)):
                        if not self.running:
                            break
                        time.sleep(0.1)
                    
                except Exception as e:
                    if self.running:  # Only log errors if we're supposed to be running
                        print(f"❌ Error in monitoring loop: {e}")
                    # Use shorter sleeps to be more responsive to Ctrl+C
                    for _ in range(int(poll_interval * 10)):
                        if not self.running:
                            break
                        time.sleep(0.1)
            
            # Send shutdown message
            if self.connected:
                shutdown_message = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] [{socket.gethostname()}] "
                    f"[MONITOR_STOP] {self.log_type} event log monitoring stopped"
                )
                self.send_log_line(shutdown_message)
            
            print("✅ Event log monitoring stopped")
            
        except Exception as e:
            print(f"💥 FATAL ERROR in monitor_events: {e}")
            traceback.print_exc()
        finally:
            self.disconnect()

    def stop_monitoring(self):
        """Stop the monitoring"""
        print("\n🛑 Stopping monitor...")
        self.running = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            print("✅ Monitoring stopped")

    def start_monitoring(self, poll_interval=2):
        """Start monitoring in a separate thread"""
        # Use non-daemon thread to prevent the stdout lock issue
        self.monitor_thread = threading.Thread(
            target=self.monitor_events, 
            args=(poll_interval,),
            daemon=False
        )
        self.monitor_thread.start()
        return self.monitor_thread

# Global client instance for signal handling
client_instance = None

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    print(f'\n🛑 Received signal {sig}, shutting down gracefully...')
    if client_instance:
        client_instance.stop_monitoring()
    # Give a moment for cleanup, then exit
    time.sleep(1)
    sys.exit(0)

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows Event Log to Log Server Client')
    parser.add_argument('--host', default='localhost', help='Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=21327, help='Server port (default: 21327)')
    parser.add_argument('--password', required=True, help='Server password')
    #parser.add_argument('--log-type', default='Application', choices=['Application', 'System', 'Security'],help='Event log type to monitor (default: Application)')
    parser.add_argument('--log-type', default='Application', help='Event log type to monitor (default: Application)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL')
    parser.add_argument('--poll-interval', type=float, default=2.0, 
                       help='Polling interval in seconds (default: 2.0)')
    parser.add_argument('--initial-events', type=int, default=5,
                       help='Number of recent events to send initially (default: 5)')
    
    args = parser.parse_args()
    
    global client_instance
    
    # Create and start client
    client = WindowsEventLogClient(
        server_host=args.host,
        server_port=args.port,
        password=args.password,
        log_type=args.log_type,
        use_ssl=not args.no_ssl
    )
    
    client_instance = client
    
    # Register signal handlers for graceful shutdown

    
    # Connect to server
    if not client.connect():
        print("❌ Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print(f"🔍 Monitoring '{args.log_type}' event log...")
    print(f"⏰ Poll interval: {args.poll_interval} seconds")
    print(f"📊 Initial events: {args.initial_events}")
    print("🛑 Press Ctrl+C to stop monitoring")
    
    try:
        # Start monitoring (this will run in a separate thread)
        monitor_thread = client.start_monitoring(poll_interval=args.poll_interval)
        
        # Keep main thread alive while monitoring is running
        # Use a more responsive loop
        while client.running and monitor_thread.is_alive():
            time.sleep(0.5)  # Shorter sleep to be more responsive
            
        print("✅ Monitoring completed normally")
            
    except KeyboardInterrupt:
        # This should be caught by the signal handler, but just in case
        signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        client.stop_monitoring()
    finally:
        client.running = False

if __name__ == "__main__":
    main()