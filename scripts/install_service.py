#!/usr/bin/env python3
"""
Install AIAgentHub as a system service.

macOS: Creates a launchd plist
Linux: Creates a systemd unit file
"""

import os
import sys
import platform

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON = sys.executable


def install_macos(mode="serve"):
    """Install macOS launchd service"""
    label = f"com.aiagent.{mode}"
    script = "server.py" if mode == "serve" else "worker.py"
    plist_path = os.path.expanduser(f"~/Library/LaunchAgents/{label}.plist")

    plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON}</string>
        <string>{os.path.join(PROJECT_DIR, script)}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{PROJECT_DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>{os.path.join(PROJECT_DIR, f'{mode}.log')}</string>
    <key>StandardErrorPath</key>
    <string>{os.path.join(PROJECT_DIR, f'{mode}.error.log')}</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>
"""

    with open(plist_path, "w") as f:
        f.write(plist)

    print(f"Created: {plist_path}")
    print(f"Load:    launchctl load {plist_path}")
    print(f"Unload:  launchctl unload {plist_path}")
    print(f"Status:  launchctl list | grep {label}")


def install_linux(mode="serve"):
    """Install Linux systemd service"""
    service_name = f"aiagent-{mode}"
    script = "server.py" if mode == "serve" else "worker.py"
    unit_path = f"/etc/systemd/system/{service_name}.service"

    unit = f"""[Unit]
Description=AIAgentHub {mode}
After=network.target mongodb.service

[Service]
Type=simple
User={os.environ.get('USER', 'root')}
WorkingDirectory={PROJECT_DIR}
ExecStart={PYTHON} {os.path.join(PROJECT_DIR, script)}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
"""

    print(f"Write this to {unit_path}:")
    print(unit)
    print(f"\nThen run:")
    print(f"  sudo systemctl daemon-reload")
    print(f"  sudo systemctl enable {service_name}")
    print(f"  sudo systemctl start {service_name}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "serve"

    if platform.system() == "Darwin":
        install_macos(mode)
    else:
        install_linux(mode)
