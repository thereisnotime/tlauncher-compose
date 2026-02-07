"""
System detection module for Minecraft Launcher.
Auto-detects container runtime, GPU type, display server, and audio system.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict


def detect_system() -> Dict[str, str]:
    """
    Auto-detect all system configuration.

    Returns:
        dict: Configuration with keys: runtime, gpu, display, audio
    """
    return {
        "runtime": detect_runtime(),
        "gpu": detect_gpu(),
        "display": detect_display(),
        "audio": detect_audio(),
    }


def detect_runtime() -> str:
    """
    Detect container runtime (podman or docker).

    Returns:
        str: 'podman' or 'docker'
    """
    # Prefer podman if available
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    return "podman"  # Default, will fail validation later


def detect_gpu() -> str:
    """
    Detect GPU type (nvidia or amd).

    Returns:
        str: 'nvidia' or 'amd'
    """
    # Check for NVIDIA devices
    if Path("/dev/nvidia0").exists() or Path("/dev/nvidiactl").exists():
        return "nvidia"

    # Check for AMD/Intel DRI devices
    if Path("/dev/dri").exists():
        dri_cards = list(Path("/dev/dri").glob("card*"))
        if dri_cards:
            return "amd"

    # Fallback: Try lspci
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=2)
        output = result.stdout.lower()

        if "nvidia" in output or "geforce" in output or "quadro" in output or "rtx" in output:
            return "nvidia"
        if "amd" in output or "radeon" in output:
            return "amd"
        if "intel" in output and "vga" in output:
            return "amd"  # Intel uses same driver path as AMD
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Default to amd (more common, broader compatibility)
    return "amd"


def detect_display() -> str:
    """
    Detect display server (x11 or wayland).

    Returns:
        str: 'x11' or 'wayland'
    """
    # Check XDG_SESSION_TYPE environment variable
    session_type = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if session_type in ["x11", "wayland"]:
        return session_type

    # Fallback: Check which display socket exists
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"

    # Default to x11 (more common)
    return "x11"


def detect_audio() -> str:
    """
    Detect audio system (pulseaudio or none).

    Returns:
        str: 'pulseaudio' or 'none'
    """
    # Check if PulseAudio/PipeWire socket exists
    uid = os.getuid()
    pulse_socket = Path(f"/run/user/{uid}/pulse/native")

    if pulse_socket.exists():
        return "pulseaudio"

    # Try pactl command
    try:
        result = subprocess.run(["pactl", "info"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0 and "Server Name:" in result.stdout:
            return "pulseaudio"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Default to none (container will run without audio)
    return "none"


def get_detection_details() -> Dict[str, Dict[str, any]]:
    """
    Get detailed detection information for display to user.

    Returns:
        dict: Detailed info about each detected component
    """
    runtime = detect_runtime()
    runtime_path = shutil.which(runtime) if shutil.which(runtime) else "Not found"

    gpu = detect_gpu()
    gpu_details = _get_gpu_details(gpu)

    display = detect_display()
    display_value = (
        os.environ.get("DISPLAY") if display == "x11" else os.environ.get("WAYLAND_DISPLAY", "")
    )

    audio = detect_audio()
    audio_details = _get_audio_details()

    return {
        "runtime": {
            "value": runtime,
            "path": runtime_path,
            "available": shutil.which(runtime) is not None,
        },
        "gpu": {"value": gpu, "details": gpu_details, "devices_exist": _check_gpu_devices(gpu)},
        "display": {
            "value": display,
            "session_type": os.environ.get("XDG_SESSION_TYPE", "unknown"),
            "display_var": display_value,
        },
        "audio": {"value": audio, "details": audio_details},
    }


def _get_gpu_details(gpu_type: str) -> str:
    """Get GPU model details from lspci."""
    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=2)
        for line in result.stdout.split("\n"):
            line_lower = line.lower()
            if "vga" in line_lower or "3d" in line_lower:
                if (gpu_type == "nvidia" and "nvidia" in line_lower) or (
                    gpu_type == "amd" and ("amd" in line_lower or "radeon" in line_lower)
                ):
                    # Extract GPU name from line
                    parts = line.split(": ", 1)
                    if len(parts) > 1:
                        return parts[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return f"{gpu_type.upper()} GPU"


def _check_gpu_devices(gpu_type: str) -> bool:
    """Check if GPU devices actually exist."""
    if gpu_type == "nvidia":
        return Path("/dev/nvidia0").exists()
    if gpu_type == "amd":
        return Path("/dev/dri").exists()
    return False


def _get_audio_details() -> str:
    """Get audio server details."""
    try:
        result = subprocess.run(["pactl", "info"], capture_output=True, text=True, timeout=2)
        if result.returncode == 0:
            for line in result.stdout.split("\n"):
                if "Server Name:" in line:
                    return line.split(":", 1)[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return "No audio detected"
