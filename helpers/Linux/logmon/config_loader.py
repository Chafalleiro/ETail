# config_loader.py
import configparser
import argparse
import os
from pathlib import Path

def load_config(config_file=None):
    """Load configuration from file and command line"""
    
    # Default configuration
    config = {
        'host': 'localhost',
        'port': 21327,
        'password': None,
        'log-files': [],
        'poll-interval': 1.0,
        'tail-lines': 50,
        'encoding': 'utf-8',
        'use-ssl': True,
        'drop-privileges': False,
        'run-as-user': 'nobody'
    }
    
    # Load from config file if specified
    if config_file and os.path.exists(config_file):
        parser = configparser.ConfigParser()
        parser.read(config_file)
        
        if 'DEFAULT' in parser:
            for key in config.keys():
                if key in parser['DEFAULT']:
                    if key in ['port', 'tail-lines']:
                        config[key] = parser['DEFAULT'].getint(key)
                    elif key in ['poll-interval']:
                        config[key] = parser['DEFAULT'].getfloat(key)
                    elif key in ['use-ssl', 'drop-privileges']:
                        config[key] = parser['DEFAULT'].getboolean(key)
                    elif key == 'log-files':
                        config[key] = parser['DEFAULT'][key].split()
                    else:
                        config[key] = parser['DEFAULT'][key]
    
    # Override with command line arguments
    arg_parser = argparse.ArgumentParser(description='Linux Log File Monitor')
    arg_parser.add_argument('--config', help='Configuration file')
    arg_parser.add_argument('--host', help='Server hostname')
    arg_parser.add_argument('--port', type=int, help='Server port')
    arg_parser.add_argument('--password', help='Server password')
    arg_parser.add_argument('--log-files', nargs='+', help='Log files to monitor')
    arg_parser.add_argument('--poll-interval', type=float, help='Polling interval')
    arg_parser.add_argument('--tail-lines', type=int, help='Initial lines to send')
    arg_parser.add_argument('--encoding', help='File encoding')
    arg_parser.add_argument('--no-ssl', action='store_true', help='Disable SSL')
    arg_parser.add_argument('--drop-privileges', action='store_true', 
                          help='Drop privileges after startup')
    arg_parser.add_argument('--run-as-user', help='User to run as after dropping privileges')
    
    args = arg_parser.parse_args()
    
    # Update config with command line args
    if args.host:
        config['host'] = args.host
    if args.port:
        config['port'] = args.port
    if args.password:
        config['password'] = args.password
    if args.log_files:
        config['log-files'] = args.log_files
    if args.poll_interval:
        config['poll-interval'] = args.poll_interval
    if args.tail_lines:
        config['tail-lines'] = args.tail_lines
    if args.encoding:
        config['encoding'] = args.encoding
    if args.no_ssl:
        config['use-ssl'] = False
    if args.drop_privileges:
        config['drop-privileges'] = True
    if args.run_as_user:
        config['run-as-user'] = args.run_as_user
    
    return config

# Update main() in linux_log_client.py to use config loader:
def main():
    """Main function with configuration file support"""
    import signal
    
    # Load configuration
    config = load_config()
    
    # Check required settings
    if not config['host']:
        print("❌ Server host is required")
        sys.exit(1)
    if not config['password']:
        print("❌ Server password is required")
        sys.exit(1)
    if not config['log-files']:
        print("❌ No log files specified")
        sys.exit(1)
    
    global linux_client_instance
    
    # Create and start client
    client = LinuxLogClient(
        server_host=config['host'],
        server_port=config['port'],
        password=config['password'],
        log_files=config['log-files'],
        use_ssl=config['use-ssl'],
        encoding=config['encoding'],
        tail_lines=config['tail-lines'],
        drop_privileges=config['drop-privileges'],
        run_as_user=config['run-as-user']
    )
    
    linux_client_instance = client
    
    # Register signal handlers
    signal.signal(signal.SIGINT, linux_signal_handler)
    signal.signal(signal.SIGTERM, linux_signal_handler)
    
    # Connect to server
    if not client.connect():
        print("❌ Failed to connect to server. Exiting.")
        sys.exit(1)
    
    print(f"🔍 Monitoring log files on {client.client_name}...")
    print(f"📁 Files: {', '.join(config['log-files'])}")
    print(f"⏰ Poll interval: {config['poll-interval']} seconds")
    print(f"📊 Initial lines: {config['tail-lines']}")
    print("🛑 Press Ctrl+C to stop monitoring")
    
    try:
        # Start monitoring
        monitor_thread = client.start_monitoring(poll_interval=config['poll-interval'])
        
        # Keep main thread alive
        while client.running and monitor_thread.is_alive():
            time.sleep(0.5)
            
        print("✅ Monitoring completed normally")
            
    except KeyboardInterrupt:
        linux_signal_handler(signal.SIGINT, None)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        traceback.print_exc()
        client.stop_monitoring()
    finally:
        client.running = False
