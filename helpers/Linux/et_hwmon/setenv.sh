#!/bin/bash
echo "Setting up Linux Hardware Monitor environment..."

# Check if virtual environment already exists
if [ -d "build_venv" ]; then
    echo "✅ Build environment already exists"
    echo "💡 To rebuild environment: rm -rf build_venv && ./setup_build_env.sh"
    exit 0
fi

# Create virtual environment
python3 -m venv hardware_monitor_venv
source hardware_monitor_venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install psutil pyinstaller

# Install lm-sensors system package
echo "Installing system packages (may require sudo password)..."
sudo apt update
sudo apt install -y lm-sensors

# Detect sensors
echo "Detecting hardware sensors..."
sudo sensors-detect --auto

echo "✅ Setup complete!"
echo "🔧 Activate virtual environment: source hardware_monitor_venv/bin/activate"
echo "🚀 Run the monitor: python hardware_mon_linux.py"
