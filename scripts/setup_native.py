# setup_native.py — JARVIS MK37 Native C Compiler Script
"""
Compiles native/jarvis_native.c into shared library (libjarvis_native.so / .dll / .dylib).
Includes multi-method auto-installer for missing C compilers (gcc/clang/cl).
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Fix terminal encoding issues on Windows
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BASE_DIR   = Path(__file__).resolve().parent
NATIVE_DIR = BASE_DIR / "native"
C_SRC      = NATIVE_DIR / "jarvis_native.c"

system = platform.system()
if system == "Windows":
    LIB_NAME = "jarvis_native.dll"
elif system == "Darwin":
    LIB_NAME = "libjarvis_native.dylib"
else:
    LIB_NAME = "libjarvis_native.so"

LIB_PATH = NATIVE_DIR / LIB_NAME


def find_compiler() -> str | None:
    """Find installed C compiler across standard system PATHs and common installation directories."""
    compiler = shutil.which("gcc") or (shutil.which("cl") if system == "Windows" else None) or shutil.which("clang")
    if compiler:
        return compiler

    # Common Windows compiler paths if not in PATH
    if system == "Windows":
        common_paths = [
            Path("C:/tools/mingw64/bin/gcc.exe"),
            Path("C:/tools/mingw32/bin/gcc.exe"),
            Path("C:/ProgramData/chocolatey/bin/gcc.exe"),
            Path("C:/ProgramData/chocolatey/lib/mingw/tools/install/mingw64/bin/gcc.exe"),
            Path("C:/msys64/ucrt64/bin/gcc.exe"),
            Path("C:/msys64/mingw64/bin/gcc.exe"),
            Path("C:/Program Files/LLVM/bin/clang.exe"),
            Path("C:/Program Files (x86)/LLVM/bin/clang.exe"),
            BASE_DIR / "native" / "compiler" / "bin" / "gcc.exe",
        ]
        for p in common_paths:
            if p.exists():
                os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
                return str(p)

    return None


def auto_install_compiler() -> str | None:
    """Attempt multi-method automatic installation of a C compiler (gcc / clang)."""
    print("[NativeBuild] 🛠️ Attempting automatic C compiler installation...")
    
    if system == "Windows":
        # Strategy 1: winget LLVM install
        if shutil.which("winget"):
            print("[NativeBuild]   ▶ Strategy 1: Installing LLVM via winget...")
            try:
                subprocess.run(
                    ["winget", "install", "--id", "LLVM.LLVM", "--silent", "--accept-package-agreements", "--accept-source-agreements"],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=180
                )
                comp = find_compiler()
                if comp:
                    print(f"[NativeBuild] ✅ C compiler successfully installed via winget: {comp}")
                    return comp
            except Exception as e:
                print(f"[NativeBuild]   ⚠ winget attempt: {e}")

        # Strategy 2: choco mingw install
        if shutil.which("choco"):
            print("[NativeBuild]   ▶ Strategy 2: Installing MinGW via Chocolatey...")
            try:
                subprocess.run(
                    ["choco", "install", "mingw", "-y"],
                    capture_output=True, encoding="utf-8", errors="replace", timeout=180
                )
                comp = find_compiler()
                if comp:
                    print(f"[NativeBuild] ✅ C compiler successfully installed via choco: {comp}")
                    return comp
            except Exception as e:
                print(f"[NativeBuild]   ⚠ choco attempt: {e}")

    elif system == "Linux":
        if shutil.which("apt-get"):
            try:
                subprocess.run(["sudo", "apt-get", "update", "-y"], capture_output=True, timeout=60)
                subprocess.run(["sudo", "apt-get", "install", "-y", "build-essential", "gcc"], capture_output=True, timeout=120)
            except Exception:
                pass
    elif system == "Darwin":
        if shutil.which("brew"):
            try:
                subprocess.run(["brew", "install", "gcc"], capture_output=True, timeout=180)
            except Exception:
                pass

    return find_compiler()


def compile_native(auto_install: bool = True) -> bool:
    """Attempt to compile native C library using gcc or clang."""
    if not C_SRC.exists():
        print(f"[NativeBuild] ⚠️ C source file not found: {C_SRC}")
        return False

    compiler = find_compiler()
    if not compiler and auto_install:
        compiler = auto_install_compiler()

    if not compiler:
        print("[NativeBuild] ℹ️ No C compiler (gcc/clang) found. Native features will use pure-Python fallbacks.")
        return False

    NATIVE_DIR.mkdir(parents=True, exist_ok=True)

    if system == "Windows" and Path(compiler).stem.lower() == "cl":
        cmd = [compiler, "/LD", str(C_SRC), f"/Fe{LIB_PATH}", "/O2"]
    else:
        flags = ["-O3", "-shared"]
        if system != "Windows":
            flags.append("-fPIC")
        if system == "Darwin":
            flags = ["-O3", "-dynamiclib"]
        cmd = [compiler] + flags + ["-o", str(LIB_PATH), str(C_SRC)]
        if system != "Windows":
            cmd.append("-lm")

    print(f"[NativeBuild] 🛠️ Compiling native library: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace", timeout=30)
        if res.returncode == 0 and LIB_PATH.exists():
            print(f"[NativeBuild] ✅ Native library successfully compiled: {LIB_PATH}")
            return True
        else:
            print("[NativeBuild] ℹ️ C compiler missing header SDKs or toolchain. Using pure-Python fallbacks.")
            return False
    except Exception as e:
        print(f"[NativeBuild] ℹ️ Compilation note: {e}. Using pure-Python fallbacks.")
        return False


if __name__ == "__main__":
    success = compile_native(auto_install=True)
    sys.exit(0 if success else 1)
