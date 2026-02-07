#!/usr/bin/env python3
"""
Minecraft Launcher - Dual GUI/CLI interface for containerized TLauncher.

This launcher auto-detects your system and provides both graphical and
terminal interfaces for running Minecraft in a container.

Usage:
    # GUI mode (default when launched without arguments)
    ./minecraft.py

    # CLI mode
    ./minecraft.py start           # Start with auto-detection
    ./minecraft.py stop            # Stop container
    ./minecraft.py doctor          # Check system
    ./minecraft.py --no-gui start  # Force CLI mode
"""

import os
import sys


def should_use_gui() -> bool:
    """
    Determine if GUI or CLI mode should be used.

    GUI mode is used when:
    - No command-line arguments provided (double-click launch)
    - Display is available (DISPLAY env var or Windows)

    CLI mode is used when:
    - --no-gui flag is present
    - Any other command-line arguments provided
    - No display available (headless/SSH)

    Returns:
        bool: True for GUI mode, False for CLI mode
    """
    # Force CLI if --no-gui flag
    if "--no-gui" in sys.argv:
        return False

    # CLI mode if any other arguments passed
    if len(sys.argv) > 1:
        return False

    # Check if display is available
    if os.environ.get("DISPLAY") or sys.platform == "win32":
        # GUI mode possible, check if tkinter is available
        try:
            import tkinter  # noqa: F401

            return True
        except ImportError:
            # Tkinter not available, fall back to CLI
            return False

    # Default to CLI for headless/SSH
    return False


def main():
    """Main entry point for the launcher."""
    if should_use_gui():
        # Launch GUI mode
        try:
            from gui import MinecraftLauncherGUI

            app = MinecraftLauncherGUI()
            app.run()
        except ImportError as e:
            print(f"Error: Could not import GUI module: {e}")
            print("Falling back to CLI mode...")
            launch_cli()
        except Exception as e:
            print(f"Error starting GUI: {e}")
            sys.exit(1)
    else:
        # Launch CLI mode
        launch_cli()


def launch_cli():
    """Launch CLI mode with argument parsing."""
    import argparse

    from cli import run_cli

    parser = argparse.ArgumentParser(
        description="Minecraft Launcher - Containerized TLauncher with auto-detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start                    Start Minecraft (auto-detect system)
  %(prog)s start --detached         Start in background
  %(prog)s start --runtime docker   Override runtime detection
  %(prog)s stop                     Stop container
  %(prog)s doctor                   Check system configuration
  %(prog)s stats                    Show resource usage (CPU, RAM, GPU)
  %(prog)s profiles list            List all Minecraft profiles
  %(prog)s profiles export MC02     Export profile to ZIP file
  %(prog)s profiles import file.zip Import profile from ZIP file
  %(prog)s --no-gui start           Force CLI mode (skip GUI)
        """,
    )

    # Subcommands
    parser.add_argument(
        "command",
        nargs="?",
        default="start",
        choices=["start", "stop", "restart", "logs", "status", "doctor", "stats", "profiles"],
        help="Command to execute (default: start)",
    )

    # Profile subcommand (for profiles list/export/import/delete)
    parser.add_argument(
        "profile_action", nargs="?", help="Profile action: list, export, import, delete"
    )

    # Profile name or file argument
    parser.add_argument(
        "profile_arg",
        nargs="?",
        help="Profile name (for export/delete) or ZIP file path (for import)",
    )

    # Configuration overrides
    parser.add_argument(
        "--runtime", choices=["podman", "docker"], help="Override runtime detection"
    )
    parser.add_argument("--gpu", choices=["nvidia", "amd"], help="Override GPU detection")
    parser.add_argument(
        "--display", choices=["x11", "wayland"], help="Override display server detection"
    )
    parser.add_argument(
        "--audio", choices=["pulseaudio", "none"], help="Override audio system detection"
    )

    # Behavior flags
    parser.add_argument(
        "--detached",
        "-d",
        action="store_true",
        help="Run container in background (for start command)",
    )
    parser.add_argument(
        "--force-recreate",
        action="store_true",
        help="Force recreate containers (for start command)",
    )
    parser.add_argument(
        "--follow", "-f", action="store_true", help="Follow log output (for logs command)"
    )
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation prompts")

    # Mode selection
    parser.add_argument("--no-gui", action="store_true", help="Force CLI mode (disable GUI)")

    args = parser.parse_args()

    # Run CLI with parsed arguments
    try:
        run_cli(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
