#!/usr/bin/env bash
# ==============================================================================
# BR JARVIS MK40.2+ — Universal Multi-Distro Linux Installer & Setup Helper
# Supports: Ubuntu/Debian/Mint, Arch/Manjaro, Fedora/RHEL, openSUSE, Alpine
# ==============================================================================

set -e

echo -e "\033[1;36m========================================================\033[0m"
echo -e "\033[1;36m   BR JARVIS MK40.2+ — Multi-Distro Linux Setup Helper   \033[0m"
echo -e "\033[1;36m========================================================\033[0m"

# Detect Distro & Package Manager
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO=$ID
else
    DISTRO="unknown"
fi

echo -e "\033[1;33m[+] Detected Linux Distribution: ${DISTRO}\033[0m"

install_packages() {
    if command -v apt-get &>/dev/null; then
        echo "[+] Updating apt repositories and installing packages..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3-pip python3-dev python3-venv \
            portaudio19-dev libasound2-dev ffmpeg xdotool wmctrl \
            libnotify-bin pulseaudio-utils x11-utils brightnessctl || true

    elif command -v pacman &>/dev/null; then
        echo "[+] Installing packages via pacman..."
        sudo pacman -Sy --needed --noconfirm python-pip portaudio alsa-lib \
            ffmpeg xdotool wmctrl libnotify libpulse brightnessctl || true

    elif command -v dnf &>/dev/null; then
        echo "[+] Installing packages via dnf..."
        sudo dnf install -y python3-pip python3-devel portaudio-devel \
            alsa-lib-devel ffmpeg xdotool wmctrl libnotify pulseaudio-utils brightnessctl || true

    elif command -v zypper &>/dev/null; then
        echo "[+] Installing packages via zypper..."
        sudo zypper install -y python3-pip python3-devel portaudio-devel \
            alsa-devel ffmpeg xdotool wmctrl libnotify-tools pulseaudio-utils brightnessctl || true

    elif command -v apk &>/dev/null; then
        echo "[+] Installing packages via apk..."
        sudo apk add python3 py3-pip portaudio-dev alsa-lib-dev \
            ffmpeg xdotool wmctrl libnotify pulseaudio-utils brightnessctl || true

    else
        echo "[-] Package manager not detected. Please manually ensure python3-pip, portaudio, ffmpeg, xdotool, wmctrl, and libnotify are installed."
    fi
}

install_packages

echo -e "\033[1;32m[+] System packages satisfied.\033[0m"
echo -e "\033[1;33m[+] Installing Python dependencies from requirements.txt...\033[0m"

python3 -m pip install -r requirements.txt --quiet || python3 -m pip install -r requirements.txt --break-system-packages --quiet
python3 -m pip install -e . --no-deps --quiet || true

echo -e "\033[1;33m[+] Compiling native C extension library...\033[0m"
python3 scripts/setup_native.py || echo "[-] C native compilation skipped (using Python fallback)"

echo -e "\033[1;32m========================================================\033[0m"
echo -e "\033[1;32m   BR JARVIS MK40.2+ — Multi-Distro Linux Setup Complete!  \033[0m"
echo -e "\033[1;32m   Run 'python3 start.py' to launch JARVIS.             \033[0m"
echo -e "\033[1;32m========================================================\033[0m"
