#!/bin/bash
# setup_dev_env.sh

echo "Setting up Python development environment for log monitor clients..."

# Create virtual environment
python3 -m venv log_monitor_env
source log_monitor_env/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip

# Common dependencies
pip install chardet

# Windows-specific dependencies (if on Windows)
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    pip install pywin32 psutil
fi

# Create requirements file
cat > requirements.txt << EOF
chardet>=5.0.0
pywin32>=300; sys_platform == 'win32'
psutil>=5.9.0; sys_platform == 'win32'
EOF

echo "Development environment setup complete!"
echo "To activate the environment: source log_monitor_env/bin/activate"
