# hardware_mon.py
import socket
import ssl
import hashlib
import time
import threading
import sys
import traceback
from datetime import datetime
import psutil
import os
import clr

import io

# Fix encoding for Windows console
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# =============================================================================
# SIMPLE LIBREHARDWAREMONITOR SETUP - USING YOUR WORKING CODE APPROACH
# =============================================================================

LIBRE_AVAILABLE = False
Computer = None

try:
    # Use the exact same approach from your working code
    clr.AddReference(os.path.abspath(os.path.dirname(__file__)) + R'\LibreHardwareMonitorLib.dll')
    from LibreHardwareMonitor import Hardware
    
    Computer = Hardware.Computer
    LIBRE_AVAILABLE = True
    print("✓ LibreHardwareMonitor loaded successfully using simple approach")
    
except Exception as e:
    print(f"⚠️  Failed to load LibreHardwareMonitor: {e}")
    print("💡 Make sure LibreHardwareMonitorLib.dll is in the same folder as this script")
    LIBRE_AVAILABLE = False

# =============================================================================
# SIMPLIFIED HARDWARE MONITOR CLASS
# =============================================================================

class HardwareMonitor:
    def __init__(self, use_fahrenheit=False, refresh_interval=5):
        self.use_fahrenheit = use_fahrenheit
        self.refresh_interval = refresh_interval
        self.computer = None
        self.computer_name = os.environ.get('COMPUTERNAME', 'Unknown-PC')
        
        # Initialize LibreHardwareMonitor if available
        if LIBRE_AVAILABLE and Computer:
            self.setup_libre_hardware()
        else:
            print("⚠️  Using basic hardware monitoring (no temperatures)")
    
    def setup_libre_hardware(self):
        """Initialize LibreHardwareMonitor using the working approach"""
        try:
            self.computer = Computer()
            self.computer.IsCpuEnabled = True
            self.computer.IsGpuEnabled = True
            self.computer.IsMemoryEnabled = True
            self.computer.IsMotherboardEnabled = True
            self.computer.IsStorageEnabled = True
            self.computer.Open()
            print("✓ LibreHardwareMonitor initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize LibreHardwareMonitor: {e}")
            self.computer = None
    
    def celsius_to_fahrenheit(self, celsius):
        """Convert Celsius to Fahrenheit"""
        if celsius is None or celsius == "N/A":
            return "N/A"
        try:
            return round((celsius * 9/5) + 32, 1)
        except:
            return "N/A"
    
    def get_sensor_value(self, hardware_type, sensor_type, name_filter=None):
        """Generic method to get sensor values - based on your working code"""
        if not LIBRE_AVAILABLE or not self.computer:
            return None
            
        try:
            for hardware in self.computer.Hardware:
                hardware.Update()
                if hardware.HardwareType == hardware_type:
                    for sensor in hardware.Sensors:
                        if (sensor.SensorType == sensor_type and 
                            sensor.Value is not None):
                            # If no name filter, return first matching sensor
                            if name_filter is None:
                                return sensor.Value
                            # If name filter provided, check if it matches
                            elif name_filter in sensor.Name:
                                return sensor.Value
            return None
        except Exception as e:
            print(f"Error reading sensor {sensor_type}: {e}")
            return None
    
    def get_cpu_temperature(self):
        """Get CPU temperature - using your working code approach"""
        temp = self.get_sensor_value(
            Hardware.HardwareType.Cpu, 
            Hardware.SensorType.Temperature,
            "Core"  # Look for sensors with "Core" in name (like "Core (Tctl/Tdie)")
        )
        
        if temp is None:
            return "N/A"
        
        if self.use_fahrenheit:
            return self.celsius_to_fahrenheit(temp)
        return round(temp, 1)
    
    def get_gpu_temperature(self):
        """Get GPU temperature"""
        gpu_types = [
            Hardware.HardwareType.GpuNvidia, 
            Hardware.HardwareType.GpuAmd, 
            Hardware.HardwareType.GpuIntel
        ]
        
        for gpu_type in gpu_types:
            temp = self.get_sensor_value(gpu_type, Hardware.SensorType.Temperature)
            if temp is not None:
                if self.use_fahrenheit:
                    return self.celsius_to_fahrenheit(temp)
                return round(temp, 1)
        
        return "N/A"
    
    def get_cpu_load(self):
        """Get CPU load percentage"""
        # Try to get from LibreHardwareMonitor first
        if LIBRE_AVAILABLE:
            load = self.get_sensor_value(
                Hardware.HardwareType.Cpu,
                Hardware.SensorType.Load,
                "CPU Total"  # Get the total CPU load
            )
            if load is not None:
                return round(load, 1)
        
        # Fallback to psutil if LibreHardwareMonitor fails
        try:
            return round(psutil.cpu_percent(interval=0.5), 1)
        except:
            return "N/A"
    
    def get_cpu_cores(self):
        """Get number of CPU cores"""
        try:
            physical_cores = psutil.cpu_count(logical=False) or "N/A"
            logical_cores = psutil.cpu_count(logical=True) or "N/A"
            return f"{physical_cores}p/{logical_cores}l"
        except:
            return "N/A"
    
    def get_memory_usage(self):
        """Get memory usage"""
        try:
            memory = psutil.virtual_memory()
            total_gb = round(memory.total / (1024**3), 1)
            used_gb = round(memory.used / (1024**3), 1)
            used_percent = round(memory.percent, 1)
            return used_percent, f"{used_gb}/{total_gb}GB"
        except:
            return "N/A", "N/A"
    
    def get_disk_usage(self):
        """Get disk usage for all drives"""
        try:
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    if 'cdrom' in partition.opts or not os.path.exists(partition.mountpoint):
                        continue
                    usage = psutil.disk_usage(partition.mountpoint)
                    free_percent = round((usage.free / usage.total) * 100, 1)
                    disk_letter = partition.device.split(':')[0] if ':' in partition.device else partition.device
                    disk_info.append(f"{disk_letter}:{free_percent}%")
                except (PermissionError, OSError):
                    continue
            return " ".join(disk_info[:3])  # Limit to first 3 disks
        except Exception as e:
            return f"Error: {e}"
    
    def get_network_info(self):
        """Get network interface information"""
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            return local_ip
        except:
            return "N/A"
    
    def get_all_metrics(self):
        """Get all hardware metrics in one call"""
        mem_percent, mem_usage = self.get_memory_usage()
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'computer_name': self.computer_name,
            'computer_ip': self.get_network_info(),
            'cpu_temp': self.get_cpu_temperature(),
            'gpu_temp': self.get_gpu_temperature(),
            'cpu_cores': self.get_cpu_cores(),
            'cpu_load': self.get_cpu_load(),
            'memory_usage': mem_usage,
            'memory_free_percent': 100 - float(mem_percent) if mem_percent != "N/A" else "N/A",
            'disk_usage': self.get_disk_usage(),
            'temp_unit': '°F' if self.use_fahrenheit else '°C',
            'libre_available': LIBRE_AVAILABLE
        }
    
    def format_metrics_line(self, metrics):
        """Format metrics into a log line"""
        temp_unit = metrics['temp_unit']
        libre_status = " (Libre)" if metrics['libre_available'] else " (Basic)"
        
        line_parts = [
            f"CPU{libre_status}: {metrics['cpu_temp']}{temp_unit}",
            f"Load: {metrics['cpu_load']}%",
            f"Cores: {metrics['cpu_cores']}",
            f"GPU: {metrics['gpu_temp']}{temp_unit}",
            f"Mem: {metrics['memory_usage']} ({metrics['memory_free_percent']}% free)",
            f"Disks: {metrics['disk_usage']}"
        ]
        
        return f"[{metrics['timestamp']}] [{metrics['computer_name']}] [{metrics['computer_ip']}] " + " | ".join(line_parts)
    
    def close(self):
        """Clean up resources"""
        if self.computer:
            try:
                self.computer.Close()
            except:
                pass

# =============================================================================
# REST OF THE CODE REMAINS THE SAME (HardwareMonitorClient and main function)
# =============================================================================

class HardwareMonitorClient:
    def __init__(self, server_host, server_port, password, 
                 use_fahrenheit=False, refresh_interval=5, use_ssl=True):
        self.server_host = server_host
        self.server_port = server_port
        self.password_hash = hashlib.sha256(password.encode()).hexdigest() if password else ""
        self.use_ssl = use_ssl
        self.use_fahrenheit = use_fahrenheit
        self.refresh_interval = refresh_interval
        
        self.hardware_monitor = HardwareMonitor(use_fahrenheit, refresh_interval)
        self.socket = None
        self.connected = False
        self.running = False
        
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
    
    def send_log_line(self, log_line):
        """Send a log line to the server"""
        if not self.connected:
            return False
            
        try:
            if not log_line.endswith('\n'):
                log_line += '\n'
                
            self.socket.send(log_line.encode('utf-8'))
            
            # Wait for confirmation
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
    
    def monitor_hardware(self):
        """Monitor hardware and send metrics to server"""
        print(f"🚀 Starting hardware monitoring...")
        print(f"   Temperature unit: {'Fahrenheit' if self.use_fahrenheit else 'Celsius'}")
        print(f"   Refresh interval: {self.refresh_interval} seconds")
        print(f"   LibreHardwareMonitor: {'Available' if LIBRE_AVAILABLE else 'Not available'}")
        
        try:
            # Send startup message
            startup_message = (
                f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                f"[{self.hardware_monitor.computer_name}] "
                f"[HARDWARE_START] Hardware monitoring started - Libre: {LIBRE_AVAILABLE}"
            )
            
            if self.connected:
                self.send_log_line(startup_message)
            
            self.running = True
            iteration = 0
            
            while self.running:
                try:
                    iteration += 1
                    
                    # Get all hardware metrics
                    metrics = self.hardware_monitor.get_all_metrics()
                    log_line = self.hardware_monitor.format_metrics_line(metrics)
                    
                    print(f"📊 {log_line}")
                    
                    if self.connected:
                        if not self.send_log_line(log_line):
                            print("⚠️  Failed to send metrics")
                    
                    # Wait before next poll
                    for _ in range(int(self.refresh_interval * 10)):
                        if not self.running:
                            break
                        time.sleep(0.1)
                    
                except KeyboardInterrupt:
                    print("\n🛑 Monitoring stopped by user")
                    self.running = False
                    break
                except Exception as e:
                    print(f"❌ Error in monitoring loop: {e}")
                    time.sleep(self.refresh_interval)
            
            # Send shutdown message
            if self.connected:
                shutdown_message = (
                    f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
                    f"[{self.hardware_monitor.computer_name}] "
                    f"[HARDWARE_STOP] Hardware monitoring stopped"
                )
                self.send_log_line(shutdown_message)
            
            print("✅ Hardware monitoring stopped")
            
        except Exception as e:
            print(f"💥 FATAL ERROR in monitor_hardware: {e}")
            traceback.print_exc()
        finally:
            self.hardware_monitor.close()
            self.disconnect()
    
    def stop_monitoring(self):
        """Stop the monitoring"""
        print("\n🛑 Stopping hardware monitor...")
        self.running = False
    
    def start_monitoring(self):
        """Start monitoring in a separate thread"""
        monitor_thread = threading.Thread(
            target=self.monitor_hardware,
            daemon=False
        )
        monitor_thread.start()
        return monitor_thread

def main():
    """Main function with command line interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Hardware Monitor Client')
    parser.add_argument('--host', default='localhost', help='Server hostname (default: localhost)')
    parser.add_argument('--port', type=int, default=21327, help='Server port (default: 21327)')
    parser.add_argument('--password', required=True, help='Server password')
    parser.add_argument('--fahrenheit', action='store_true', help='Use Fahrenheit instead of Celsius')
    parser.add_argument('--refresh-interval', type=float, default=5.0, 
                       help='Refresh interval in seconds (default: 5.0)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL')
    
    args = parser.parse_args()
    
    # Create and start client
    client = HardwareMonitorClient(
        server_host=args.host,
        server_port=args.port,
        password=args.password,
        use_fahrenheit=args.fahrenheit,
        refresh_interval=args.refresh_interval,
        use_ssl=not args.no_ssl
    )
    
    # Connect to server
    if not client.connect():
        print("❌ Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print(f"🔍 Starting hardware monitoring...")
    print(f"🌡️  Temperature unit: {'Fahrenheit' if args.fahrenheit else 'Celsius'}")
    print(f"⏰ Refresh interval: {args.refresh_interval} seconds")
    print(f"📊 LibreHardwareMonitor: {'Available' if LIBRE_AVAILABLE else 'Not available - temperatures will be N/A'}")
    print("🛑 Press Ctrl+C to stop monitoring")
    
    try:
        # Start monitoring
        monitor_thread = client.start_monitoring()
        
        # Keep main thread alive while monitoring is running
        while client.running and monitor_thread.is_alive():
            time.sleep(1)
            
        print("✅ Monitoring completed normally")
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping monitor...")
        client.stop_monitoring()
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