"""
System validation module for Minecraft Launcher.
Performs pre-flight checks to ensure system is ready.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


class ValidationIssue:
    """Represents a validation issue."""

    def __init__(self, message: str, level: str = "error", fix_hint: str = None):
        """
        Initialize validation issue.

        Args:
            message: Description of the issue
            level: 'error' (blocking) or 'warning' (non-blocking)
            fix_hint: Optional suggestion for fixing the issue
        """
        self.message = message
        self.level = level
        self.fix_hint = fix_hint

    def is_blocking(self) -> bool:
        """Check if this issue prevents startup."""
        return self.level == "error"


def validate_system(config: Dict[str, str]) -> Tuple[bool, List[ValidationIssue]]:
    """
    Perform all validation checks.

    Args:
        config: Configuration dict

    Returns:
        tuple: (is_valid, list_of_issues)
    """
    issues = []

    # Run all validation checks
    issues.extend(_check_runtime(config))
    issues.extend(_check_gpu(config))
    issues.extend(_check_display(config))
    issues.extend(_check_audio(config))
    issues.extend(_check_compose_files(config))
    issues.extend(_check_xhost(config))

    # System is valid only if there are no blocking errors
    has_errors = any(issue.is_blocking() for issue in issues)

    return not has_errors, issues


def _check_runtime(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if container runtime is available."""
    issues = []
    runtime = config["runtime"]

    if not shutil.which(runtime):
        issues.append(
            ValidationIssue(
                f"{runtime} is not installed or not in PATH",
                level="error",
                fix_hint=f"Install {runtime}: https://{runtime}.io/getting-started/installation",
            )
        )
    else:
        # Try to run runtime --version to ensure it works
        try:
            result = subprocess.run([runtime, "--version"], capture_output=True, timeout=5)
            if result.returncode != 0:
                issues.append(
                    ValidationIssue(
                        f"{runtime} is installed but not working properly",
                        level="error",
                        fix_hint=f"Try running '{runtime} --version' manually to see the error",
                    )
                )
        except subprocess.TimeoutExpired:
            issues.append(ValidationIssue(f"{runtime} command timed out", level="warning"))
        except Exception as e:
            issues.append(ValidationIssue(f"Error checking {runtime}: {str(e)}", level="warning"))

    return issues


def _check_gpu(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if GPU devices exist."""
    issues = []
    gpu = config["gpu"]

    if gpu == "nvidia":
        if not Path("/dev/nvidia0").exists():
            issues.append(
                ValidationIssue(
                    "NVIDIA GPU selected but /dev/nvidia0 not found",
                    level="error",
                    fix_hint="Install NVIDIA drivers or select 'amd' GPU type",
                )
            )
        if not Path("/dev/nvidiactl").exists():
            issues.append(
                ValidationIssue(
                    "/dev/nvidiactl device not found",
                    level="warning",
                    fix_hint="NVIDIA drivers may not be properly installed",
                )
            )
    elif gpu == "amd":
        if not Path("/dev/dri").exists():
            issues.append(
                ValidationIssue(
                    "/dev/dri not found - no GPU acceleration available",
                    level="warning",
                    fix_hint="Install Mesa drivers for GPU acceleration",
                )
            )

    return issues


def _check_display(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if display server is available."""
    issues = []
    display = config["display"]

    if display == "x11":
        if not os.environ.get("DISPLAY"):
            issues.append(
                ValidationIssue(
                    "X11 selected but DISPLAY environment variable not set",
                    level="error",
                    fix_hint="Ensure you're running in an X11 session",
                )
            )
        if not Path("/tmp/.X11-unix").exists():
            issues.append(
                ValidationIssue("X11 socket directory /tmp/.X11-unix not found", level="warning")
            )
    elif display == "wayland":
        if not os.environ.get("WAYLAND_DISPLAY"):
            issues.append(
                ValidationIssue(
                    "Wayland selected but WAYLAND_DISPLAY not set",
                    level="warning",
                    fix_hint="Ensure you're running in a Wayland session",
                )
            )

    return issues


def _check_audio(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if audio system is available."""
    issues = []
    audio = config["audio"]

    if audio == "pulseaudio":
        uid = os.getuid()
        pulse_socket = Path(f"/run/user/{uid}/pulse/native")

        if not pulse_socket.exists():
            issues.append(
                ValidationIssue(
                    f"PulseAudio socket not found at {pulse_socket}",
                    level="warning",
                    fix_hint="Audio may not work. Start PulseAudio/PipeWire or select 'none' for audio",
                )
            )

        if not Path("/dev/snd").exists():
            issues.append(
                ValidationIssue(
                    "/dev/snd not found - ALSA devices unavailable",
                    level="warning",
                    fix_hint="Audio hardware may not be accessible",
                )
            )

    return issues


def _check_compose_files(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if all compose files exist."""
    from .composer import get_compose_directory, validate_compose_files_exist

    issues = []
    all_exist, missing = validate_compose_files_exist(config)

    if not all_exist:
        compose_dir = get_compose_directory()
        for f in missing:
            issues.append(
                ValidationIssue(
                    f"Compose file not found: {compose_dir / f}",
                    level="error",
                    fix_hint=f"Ensure {f} exists in {compose_dir}",
                )
            )

    return issues


def _check_xhost(config: Dict[str, str]) -> List[ValidationIssue]:
    """Check if xhost permissions are set for X11."""
    issues = []

    if config["display"] == "x11" and config.get("auto_xhost", True):
        # Check if xhost command is available
        if not shutil.which("xhost"):
            issues.append(
                ValidationIssue(
                    "xhost command not found",
                    level="warning",
                    fix_hint="Install xhost or manually allow X11 access",
                )
            )
        else:
            # Try to run xhost to check current access control
            try:
                result = subprocess.run(["xhost"], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    # Check if localuser access is already granted
                    if "SI:localuser:" not in result.stdout:
                        issues.append(
                            ValidationIssue(
                                "X11 access may need to be granted",
                                level="warning",
                                fix_hint="Will attempt to run: xhost +SI:localuser:$USER",
                            )
                        )
            except Exception:
                pass

    return issues


def run_xhost_if_needed(config: Dict[str, str]) -> bool:
    """
    Run xhost command to allow X11 access if needed.

    Args:
        config: Configuration dict

    Returns:
        bool: True if successful or not needed
    """
    if config["display"] != "x11" or not config.get("auto_xhost", True):
        return True

    if not shutil.which("xhost"):
        return False

    try:
        username = os.getenv("USER", os.getenv("USERNAME", ""))
        if not username:
            return False

        result = subprocess.run(
            ["xhost", f"+SI:localuser:{username}"], capture_output=True, timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False
