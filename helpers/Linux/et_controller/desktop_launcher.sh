# Create .desktop file
cat > ~/.local/share/applications/etail-monitor-controller.desktop << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ETail Monitor Controller
Comment=Manage ETail hardware and log monitors
Exec=/usr/local/bin/etail-monitor-controller
Icon=utilities-system-monitor
Categories=System;Monitor;
Terminal=false
StartupNotify=true
EOF
