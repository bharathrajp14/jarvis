# install_startup.py
"""
Installs BR JARVIS MK37 into auto-startup across Windows, Linux, and macOS.
- On Linux: Creates XDG Autostart entry (~/.config/autostart/br-jarvis.desktop)
  and systemd user service (~/.config/systemd/user/br-jarvis.service) configured for voice assistant.
- On Windows: Creates VBScript & BAT launchers in Windows Startup folder configured for voice assistant.
- On macOS: Creates LaunchAgent (~/Library/LaunchAgents/com.br.jarvis.plist) configured for voice assistant.

Usage:
    python3 install_startup.py            # Install auto-startup
    python3 install_startup.py --remove   # Remove auto-startup
    python3 install_startup.py --status   # Check if installed
"""

import logging
import os
import sys
import platform
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_OS = platform.system()


def get_project_dir() -> Path:
    return Path(__file__).resolve().parent.parent


def install_linux():
    project_dir = get_project_dir()
    py_exec = sys.executable
    start_py = project_dir / "start.py"

    # 1. Create XDG Autostart entry
    autostart_dir = Path.home() / ".config" / "autostart"
    autostart_dir.mkdir(parents=True, exist_ok=True)
    desktop_file = autostart_dir / "br-jarvis.desktop"

    desktop_content = f"""[Desktop Entry]
Type=Application
Name=BR JARVIS MK37
Comment=BR JARVIS Autonomous AI Voice Assistant
Exec={py_exec} {start_py} voice
Path={project_dir}
Terminal=false
Categories=Utility;Automation;
X-GNOME-Autostart-enabled=true
"""
    desktop_file.write_text(desktop_content, encoding="utf-8")

    # 2. Create Systemd user service
    systemd_dir = Path.home() / ".config" / "systemd" / "user"
    systemd_dir.mkdir(parents=True, exist_ok=True)
    service_file = systemd_dir / "br-jarvis.service"

    service_content = f"""[Unit]
Description=BR JARVIS Autonomous AI Voice Assistant Core Daemon
After=network.target sound.target

[Service]
Type=simple
WorkingDirectory={project_dir}
ExecStart={py_exec} {start_py} voice
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    service_file.write_text(service_content, encoding="utf-8")

    # Enable systemd user service if systemctl is available
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", "br-jarvis.service"], capture_output=True)
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    print("=" * 55)
    print("  BR — Auto-Startup Installed (Linux)")
    print("=" * 55)
    print(f"  Desktop Autostart   : {desktop_file}")
    print(f"  Systemd User Service: {service_file}")
    print(f"  Default Mode        : Voice Assistant")
    print("=" * 55)


def install_mac():
    project_dir = get_project_dir()
    py_exec = sys.executable
    start_py = project_dir / "start.py"

    launch_agents_dir = Path.home() / "Library" / "LaunchAgents"
    launch_agents_dir.mkdir(parents=True, exist_ok=True)
    plist_file = launch_agents_dir / "com.br.jarvis.plist"

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.br.jarvis</string>
    <key>ProgramArguments</key>
    <array>
        <string>{py_exec}</string>
        <string>{start_py}</string>
        <string>voice</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>WorkingDirectory</key>
    <string>{project_dir}</string>
    <key>StandardOutPath</key>
    <string>{project_dir}/logs/mac_autostart.log</string>
    <key>StandardErrorPath</key>
    <string>{project_dir}/logs/mac_autostart_err.log</string>
</dict>
</plist>
"""
    plist_file.write_text(plist_content, encoding="utf-8")

    try:
        subprocess.run(["launchctl", "unload", str(plist_file)], capture_output=True)
        subprocess.run(["launchctl", "load", str(plist_file)], capture_output=True)
    except Exception as e:
        logger.debug('Suppressed exception: %s', e)
    print("=" * 55)
    print("  BR — Auto-Startup Installed (macOS)")
    print("=" * 55)
    print(f"  LaunchAgent Plist  : {plist_file}")
    print(f"  Default Mode        : Voice Assistant")
    print("=" * 55)


def install_windows():
    raw_appdata = os.environ.get("APPDATA", "").strip("\r\n \t")
    if not raw_appdata:
        raw_appdata = str(Path.home() / "AppData" / "Roaming")
    startup_dir = Path(raw_appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    project_dir = get_project_dir()
    bat_source = project_dir / "startup.bat"

    vbs_file = startup_dir / "BR.vbs"
    quote = chr(34)
    vbs_content = (
        'Set WShell = CreateObject("WScript.Shell")\r\n'
        f'WShell.CurrentDirectory = "{project_dir}"\r\n'
        f'WShell.Run "{quote}{quote}{bat_source}{quote}{quote} --silent", 0, False\r\n'
    )

    # Clean up duplicate/legacy startup scripts in Windows Startup folder
    for legacy in ("BR.bat", "JARVIS_MK37.vbs", "JARVIS_MK37.bat"):
        legacy_file = startup_dir / legacy
        if legacy_file.exists():
            try:
                legacy_file.unlink()
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
    vbs_file.write_text(vbs_content, encoding="utf-8")

    print("=" * 55)
    print("  BR — Auto-Startup Installed (Windows)")
    print("=" * 55)
    print(f"  VBS Launcher : {vbs_file}")
    print(f"  Default Mode : Voice Assistant")
    print("=" * 55)


def install():
    if _OS == "Linux":
        install_linux()
    elif _OS == "Darwin":
        install_mac()
    else:
        install_windows()


def remove():
    if _OS == "Linux":
        desktop_file = Path.home() / ".config" / "autostart" / "br-jarvis.desktop"
        service_file = Path.home() / ".config" / "systemd" / "user" / "br-jarvis.service"
        if desktop_file.exists():
            desktop_file.unlink()
        if service_file.exists():
            service_file.unlink()
        try:
            subprocess.run(["systemctl", "--user", "disable", "br-jarvis.service"], capture_output=True)
        except Exception as e:
            logger.debug('Suppressed exception: %s', e)
        print("[OK] BR Linux auto-startup removed.")
    elif _OS == "Darwin":
        plist_file = Path.home() / "Library" / "LaunchAgents" / "com.br.jarvis.plist"
        if plist_file.exists():
            try:
                subprocess.run(["launchctl", "unload", str(plist_file)], capture_output=True)
            except Exception as e:
                logger.debug('Suppressed exception: %s', e)
            plist_file.unlink()
        print("[OK] BR macOS auto-startup removed.")
    else:
        raw_appdata = os.environ.get("APPDATA", "").strip("\r\n \t")
        if not raw_appdata:
            raw_appdata = str(Path.home() / "AppData" / "Roaming")
        startup_dir = Path(raw_appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        for name in ("BR.vbs", "BR.bat", "JARVIS_MK37.vbs", "JARVIS_MK37.bat"):
            f = startup_dir / name
            if f.exists():
                f.unlink()
        print("[OK] BR Windows auto-startup removed.")


def status():
    print("=" * 50)
    print(f"  BR — Auto-Startup Status ({_OS})")
    print("=" * 50)
    if _OS == "Linux":
        desktop_file = Path.home() / ".config" / "autostart" / "br-jarvis.desktop"
        service_file = Path.home() / ".config" / "systemd" / "user" / "br-jarvis.service"
        print(f"  Desktop entry: {'INSTALLED' if desktop_file.exists() else 'not found'}")
        print(f"  Systemd service: {'INSTALLED' if service_file.exists() else 'not found'}")
    elif _OS == "Darwin":
        plist_file = Path.home() / "Library" / "LaunchAgents" / "com.br.jarvis.plist"
        print(f"  macOS LaunchAgent: {'INSTALLED' if plist_file.exists() else 'not found'}")
    else:
        raw_appdata = os.environ.get("APPDATA", "").strip("\r\n \t")
        if not raw_appdata:
            raw_appdata = str(Path.home() / "AppData" / "Roaming")
        startup_dir = Path(raw_appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        vbs = startup_dir / "BR.vbs"
        print(f"  Windows VBS: {'INSTALLED' if vbs.exists() else 'not found'}")
    print("=" * 50)


if __name__ == "__main__":
    if "--remove" in sys.argv or "--uninstall" in sys.argv:
        remove()
    elif "--status" in sys.argv:
        status()
    else:
        install()
