"""
CLI interface for Minecraft Launcher.
Provides terminal-based interaction with rich formatting.
"""

import sys
from typing import Dict

# Try importing rich libraries with fallback
try:
    from rich.console import Console
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import questionary

    QUESTIONARY_AVAILABLE = True
except ImportError:
    QUESTIONARY_AVAILABLE = False

from core.composer import get_command_preview
from core.config import load_config, merge_config
from core.container import ContainerManager
from core.detector import detect_system, get_detection_details
from core.validator import run_xhost_if_needed, validate_system


def run_cli(args):
    """
    Main CLI entry point.

    Args:
        args: Parsed command-line arguments from argparse
    """
    # Handle different commands
    if args.command == "doctor":
        run_doctor(args)
    elif args.command == "status":
        run_status(args)
    elif args.command == "stop":
        run_stop(args)
    elif args.command == "logs":
        run_logs(args)
    elif args.command == "restart":
        run_restart(args)
    elif args.command == "stats":
        run_stats(args)
    elif args.command == "profiles":
        run_profiles(args)
    elif args.command == "start":
        run_start(args)
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


def run_start(args):
    """Handle 'start' command."""
    console = Console() if RICH_AVAILABLE else None

    # Step 1: Detect system
    _print(console, "[yellow]Detecting system configuration...[/yellow]")
    detected = detect_system()

    # Step 2: Load saved config
    saved = load_config()

    # Step 3: Apply command-line overrides
    if args.runtime:
        saved["runtime"] = args.runtime
    if args.gpu:
        saved["gpu"] = args.gpu
    if args.display:
        saved["display"] = args.display
    if args.audio:
        saved["audio"] = args.audio

    # Step 4: Merge configurations
    config = merge_config(detected, saved)

    # Step 5: Show configuration
    _show_configuration(console, config, detected, saved)

    # Step 6: Confirm (unless --yes)
    if not args.yes:
        if not _confirm_start(console, config):
            _print(console, "Cancelled.")
            return

    # Step 7: Validate system
    _print(console, "\n[yellow]Validating system...[/yellow]")
    valid, issues = validate_system(config)

    if issues:
        _show_validation_issues(console, issues)

    if not valid:
        _print(console, "[red]✗ System validation failed. Cannot start.[/red]")
        sys.exit(1)

    # Step 8: Run xhost if needed
    if config["display"] == "x11" and config.get("auto_xhost", True):
        _print(console, "[yellow]Setting X11 permissions...[/yellow]")
        if run_xhost_if_needed(config):
            _print(console, "[green]✓ X11 permissions set[/green]")
        else:
            _print(console, "[yellow]⚠ Could not set X11 permissions automatically[/yellow]")

    # Step 9: Start container
    _print(console, "\n[green]Starting Minecraft...[/green]")
    _print(console, f"[dim]Command: {get_command_preview(config, 'up')}[/dim]\n")

    manager = ContainerManager(config)

    def output_handler(line):
        print(line)

    success = manager.start(
        detached=args.detached,
        force_recreate=getattr(args, "force_recreate", False),
        output_callback=output_handler,
    )

    if success:
        if args.detached:
            _print(console, "\n[green]✓ Container started in background[/green]")
            _print(console, f"View logs: {sys.argv[0]} --no-gui logs -f")
        else:
            _print(console, "\n[green]✓ Container stopped[/green]")
    else:
        _print(console, "\n[red]✗ Failed to start container[/red]")
        sys.exit(1)


def run_stop(args):
    """Handle 'stop' command."""
    console = Console() if RICH_AVAILABLE else None

    # Use current/saved config to know which runtime to use
    saved = load_config()
    detected = detect_system()
    config = merge_config(detected, saved)

    _print(console, "[yellow]Stopping container...[/yellow]")

    manager = ContainerManager(config)
    if manager.stop():
        _print(console, "[green]✓ Container stopped[/green]")
    else:
        _print(console, "[red]✗ Failed to stop container[/red]")
        sys.exit(1)


def run_restart(args):
    """Handle 'restart' command."""
    console = Console() if RICH_AVAILABLE else None

    saved = load_config()
    detected = detect_system()
    config = merge_config(detected, saved)

    _print(console, "[yellow]Restarting container...[/yellow]")

    manager = ContainerManager(config)

    def output_handler(line):
        print(line)

    if manager.restart(output_callback=output_handler):
        _print(console, "[green]✓ Container restarted[/green]")
    else:
        _print(console, "[red]✗ Failed to restart container[/red]")
        sys.exit(1)


def run_logs(args):
    """Handle 'logs' command."""
    saved = load_config()
    detected = detect_system()
    config = merge_config(detected, saved)

    manager = ContainerManager(config)

    try:
        for line in manager.logs(follow=getattr(args, "follow", False)):
            print(line)
    except KeyboardInterrupt:
        pass


def run_status(args):
    """Handle 'status' command."""
    console = Console() if RICH_AVAILABLE else None

    saved = load_config()
    detected = detect_system()
    config = merge_config(detected, saved)

    manager = ContainerManager(config)
    status = manager.status()

    if status["running"]:
        _print(console, "[green]✓ Container is running[/green]")
    else:
        _print(console, "[yellow]Container is not running[/yellow]")

    if status.get("output"):
        print("\n" + status["output"])


def run_doctor(args):
    """Handle 'doctor' command - system validation."""
    console = Console() if RICH_AVAILABLE else None

    _print(console, "[bold]Minecraft Launcher - System Check[/bold]\n")

    # Detect system
    detected = detect_system()
    details = get_detection_details()
    saved = load_config()
    config = merge_config(detected, saved)

    # Show detection results
    _show_doctor_detection(console, details)

    # Validate
    _print(console, "\n[bold]Validation:[/bold]")
    valid, issues = validate_system(config)

    if issues:
        _show_validation_issues(console, issues)
    else:
        _print(console, "[green]✓ No issues found[/green]")

    if valid:
        _print(console, "\n[green bold]✓ System ready![/green bold]")
    else:
        _print(console, "\n[red bold]✗ System has errors[/red bold]")
        sys.exit(1)


def run_stats(args):
    """Handle 'stats' command - show resource usage."""
    import json
    import subprocess
    import time

    console = Console() if RICH_AVAILABLE else None

    # Get runtime
    saved = load_config()
    detected = detect_system()
    config = merge_config(detected, saved)
    runtime = config.get("runtime", "podman")

    _print(console, "[bold]Resource Usage Monitor[/bold]\n")
    _print(console, "Press Ctrl+C to exit\n")

    try:
        while True:
            # Get container stats
            result = subprocess.run(
                [
                    runtime,
                    "stats",
                    "--no-stream",
                    "--format",
                    "json" if runtime == "podman" else "table",
                    "tlauncher",
                ],
                capture_output=True,
                text=True,
                timeout=3,
            )

            if result.returncode != 0 or not result.stdout.strip():
                _print(console, "[yellow]Container not running[/yellow]")
                return

            # Parse stats
            if RICH_AVAILABLE:
                table = Table(title="Container Resources")
                table.add_column("Metric", style="cyan")
                table.add_column("Value", style="green")

                if runtime == "podman":
                    stats_list = json.loads(result.stdout.strip())
                    stats = stats_list[0] if isinstance(stats_list, list) else stats_list

                    table.add_row("CPU", stats.get("cpu_percent", "--"))
                    table.add_row("Memory", stats.get("mem_usage", "--").split("/")[0].strip())
                    table.add_row("Network In", stats.get("net_io", "--").split("/")[0].strip())
                    table.add_row(
                        "Network Out",
                        stats.get("net_io", "--").split("/")[1].strip()
                        if "/" in stats.get("net_io", "")
                        else "--",
                    )
                else:
                    # Docker table format
                    lines = result.stdout.strip().split("\n")
                    data_line = lines[-1] if lines else ""
                    import re

                    parts = re.split(r"\s{2,}", data_line.strip())

                    if len(parts) >= 6:
                        table.add_row("CPU", parts[2])
                        table.add_row("Memory", parts[3].split("/")[0].strip())
                        table.add_row(
                            "Network In",
                            parts[5].split("/")[0].strip() if "/" in parts[5] else "--",
                        )
                        table.add_row(
                            "Network Out",
                            parts[5].split("/")[1].strip() if "/" in parts[5] else "--",
                        )

                # GPU stats (NVIDIA only)
                if config.get("gpu") == "nvidia":
                    try:
                        gpu_result = subprocess.run(
                            [
                                "nvidia-smi",
                                "--query-gpu=utilization.gpu",
                                "--format=csv,noheader,nounits",
                            ],
                            capture_output=True,
                            text=True,
                            timeout=1,
                        )
                        if gpu_result.returncode == 0:
                            table.add_row("GPU", f"{gpu_result.stdout.strip()}%")
                    except FileNotFoundError:
                        pass

                console.print(table)
            else:
                # Plain text output
                print(result.stdout)

            # One-shot mode if not in interactive terminal
            if not sys.stdout.isatty():
                break

            time.sleep(2)
            if RICH_AVAILABLE:
                console.clear()

    except KeyboardInterrupt:
        _print(console, "\n[yellow]Stopped monitoring[/yellow]")


def run_profiles(args):
    """Handle 'profiles' command - profile management."""

    console = Console() if RICH_AVAILABLE else None

    action = args.profile_action
    profile_arg = args.profile_arg

    if not action or action == "list":
        # List all profiles
        _profiles_list(console)
    elif action == "export":
        # Export profile
        if not profile_arg:
            _print(console, "[red]Error: Profile name required[/red]")
            _print(console, "Usage: profiles export <profile-name>")
            sys.exit(1)
        _profiles_export(console, profile_arg)
    elif action == "import":
        # Import profile
        if not profile_arg:
            _print(console, "[red]Error: ZIP file path required[/red]")
            _print(console, "Usage: profiles import <file.zip>")
            sys.exit(1)
        _profiles_import(console, profile_arg)
    elif action == "delete":
        # Delete profile
        if not profile_arg:
            _print(console, "[red]Error: Profile name required[/red]")
            _print(console, "Usage: profiles delete <profile-name>")
            sys.exit(1)
        _profiles_delete(console, profile_arg)
    else:
        _print(console, f"[red]Unknown profile action: {action}[/red]")
        _print(console, "Available actions: list, export, import, delete")
        sys.exit(1)


def _profiles_list(console):
    """List all Minecraft profiles."""
    import json
    from pathlib import Path

    profiles_file = Path(__file__).parent / "home" / "launcher_profiles.json"

    if not profiles_file.exists():
        _print(console, "[yellow]No profiles found[/yellow]")
        return

    with open(profiles_file) as f:
        data = json.load(f)

    profiles = data.get("profiles", {})
    if not profiles:
        _print(console, "[yellow]No profiles found[/yellow]")
        return

    _print(console, "[bold]Minecraft Profiles:[/bold]\n")

    if RICH_AVAILABLE:
        table = Table()
        table.add_column("Name", style="cyan")
        table.add_column("Version", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Selected", style="magenta")

        selected_profile = data.get("selectedProfile")
        for profile_id, profile_data in profiles.items():
            name = profile_data.get("name", profile_id)
            version = profile_data.get("lastVersionId", "unknown")
            profile_type = profile_data.get("type", "custom")
            is_selected = "✓" if name == selected_profile or profile_id == selected_profile else ""

            table.add_row(name, version, profile_type, is_selected)

        console.print(table)
    else:
        selected_profile = data.get("selectedProfile")
        for profile_id, profile_data in profiles.items():
            name = profile_data.get("name", profile_id)
            version = profile_data.get("lastVersionId", "unknown")
            profile_type = profile_data.get("type", "custom")
            is_selected = (
                " [SELECTED]" if name == selected_profile or profile_id == selected_profile else ""
            )
            print(f"  {name} (v{version}) [{profile_type}]{is_selected}")


def _profiles_export(console, profile_name: str):
    """Export profile to ZIP file."""
    import json
    import zipfile
    from pathlib import Path

    profiles_file = Path(__file__).parent / "home" / "launcher_profiles.json"

    if not profiles_file.exists():
        _print(console, "[red]Error: No profiles found[/red]")
        sys.exit(1)

    with open(profiles_file) as f:
        data = json.load(f)

    profiles = data.get("profiles", {})

    # Find profile by name
    profile_id = None
    profile_data = None

    for pid, pdata in profiles.items():
        if pdata.get("name") == profile_name or pid == profile_name:
            profile_id = pid
            profile_data = pdata
            break

    if not profile_data:
        _print(console, f"[red]Error: Profile '{profile_name}' not found[/red]")
        _print(console, "Available profiles:")
        for pid, pdata in profiles.items():
            print(f"  - {pdata.get('name', pid)}")
        sys.exit(1)

    version_id = profile_data.get("lastVersionId", "unknown")
    output_file = f"{profile_name}_{version_id}.mcprofile.zip"

    _print(console, f"[yellow]Exporting profile: {profile_name}[/yellow]")

    # Create ZIP file
    with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Add metadata
        metadata = {
            "profile_id": profile_id,
            "profile_data": profile_data,
            "version_id": version_id,
            "export_version": "1.0",
        }
        zipf.writestr("profile_metadata.json", json.dumps(metadata, indent=2))

        # Add version files
        version_dir = Path(__file__).parent / "home" / "versions" / version_id
        if version_dir.exists():
            for file_path in version_dir.rglob("*"):
                if file_path.is_file():
                    arcname = f"version/{file_path.relative_to(version_dir)}"
                    zipf.write(file_path, arcname)

    _print(console, f"[green]✓ Exported to: {output_file}[/green]")


def _profiles_import(console, zip_path: str):
    """Import profile from ZIP file."""
    import json
    import zipfile
    from pathlib import Path

    zip_file = Path(zip_path)
    if not zip_file.exists():
        _print(console, f"[red]Error: File not found: {zip_path}[/red]")
        sys.exit(1)

    _print(console, f"[yellow]Importing profile from: {zip_file.name}[/yellow]")

    with zipfile.ZipFile(zip_file, "r") as zipf:
        # Read metadata
        if "profile_metadata.json" not in zipf.namelist():
            _print(console, "[red]Error: Invalid profile archive (missing metadata)[/red]")
            sys.exit(1)

        metadata_content = zipf.read("profile_metadata.json").decode("utf-8")
        metadata = json.loads(metadata_content)

        profile_data = metadata.get("profile_data", {})
        version_id = metadata.get("version_id", "unknown")
        profile_name = profile_data.get("name", "Imported Profile")

        _print(console, f"  Profile: {profile_name}")
        _print(console, f"  Version: {version_id}")

        # Extract version files
        version_dir = Path(__file__).parent / "home" / "versions" / version_id
        version_dir.mkdir(parents=True, exist_ok=True)

        for item in zipf.namelist():
            if item.startswith("version/"):
                target_path = version_dir / item.replace("version/", "")
                target_path.parent.mkdir(parents=True, exist_ok=True)

                with zipf.open(item) as source, open(target_path, "wb") as target:
                    target.write(source.read())

        # Update launcher_profiles.json
        profiles_file = Path(__file__).parent / "home" / "launcher_profiles.json"

        if profiles_file.exists():
            with open(profiles_file) as f:
                launcher_data = json.load(f)
        else:
            launcher_data = {"clientToken": "imported", "profiles": {}}

        # Generate unique profile ID
        base_id = profile_data.get("name", version_id).replace(" ", "_")
        profile_id = base_id
        counter = 1
        while profile_id in launcher_data.get("profiles", {}):
            profile_id = f"{base_id}_{counter}"
            counter += 1

        # Add profile
        new_profile = {
            "name": profile_data.get("name", version_id),
            "type": profile_data.get("type", "custom"),
            "created": profile_data.get("created", "2024-01-01T00:00:00.000Z"),
            "lastUsed": profile_data.get("lastUsed", "2024-01-01T00:00:00.000Z"),
            "lastVersionId": version_id,
        }

        if profile_data.get("gameDir"):
            new_profile["gameDir"] = f"/home/app/.minecraft/versions/{version_id}"

        launcher_data.setdefault("profiles", {})[profile_id] = new_profile

        # Save
        with open(profiles_file, "w") as f:
            json.dump(launcher_data, f, indent=2)

    _print(console, f"[green]✓ Profile '{profile_name}' imported successfully![/green]")


def _profiles_delete(console, profile_name: str):
    """Delete a profile."""
    import json
    from pathlib import Path

    profiles_file = Path(__file__).parent / "home" / "launcher_profiles.json"

    if not profiles_file.exists():
        _print(console, "[red]Error: No profiles found[/red]")
        sys.exit(1)

    with open(profiles_file) as f:
        data = json.load(f)

    profiles = data.get("profiles", {})

    # Find profile by name
    profile_id = None
    profile_data = None

    for pid, pdata in profiles.items():
        if pdata.get("name") == profile_name or pid == profile_name:
            profile_id = pid
            profile_data = pdata
            break

    if not profile_data:
        _print(console, f"[red]Error: Profile '{profile_name}' not found[/red]")
        sys.exit(1)

    # Confirm deletion
    _print(console, f"[yellow]Delete profile '{profile_name}'?[/yellow]")
    _print(console, "[dim]This will remove the profile entry from TLauncher.[/dim]")
    _print(console, "[dim]Version files will NOT be deleted.[/dim]")

    if QUESTIONARY_AVAILABLE:
        confirmed = questionary.confirm("Proceed?", default=False).ask()
    else:
        response = input("\nProceed? [y/N] ")
        confirmed = response.lower() in ["y", "yes"]

    if not confirmed:
        _print(console, "Cancelled")
        return

    # Remove from profiles
    del profiles[profile_id]

    # Update selected profile if needed
    if data.get("selectedProfile") == profile_id:
        if profiles:
            data["selectedProfile"] = list(profiles.keys())[0]
        else:
            data["selectedProfile"] = None

    # Save
    with open(profiles_file, "w") as f:
        json.dump(data, f, indent=2)

    _print(console, f"[green]✓ Profile '{profile_name}' deleted[/green]")


def _show_configuration(console, config: Dict, detected: Dict, saved: Dict):
    """Display configuration table."""
    if not RICH_AVAILABLE:
        print("\nConfiguration:")
        for key, value in config.items():
            if key == "auto_xhost":
                continue
            source = " (saved)" if saved.get(key) else " (detected)"
            print(f"  {key.capitalize()}: {value}{source}")
        return

    table = Table(title="System Configuration")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="green")
    table.add_column("Source", style="dim")

    for key in ["runtime", "gpu", "display", "audio"]:
        value = config[key]
        source = "saved" if saved.get(key) and saved[key] == value else "detected"
        table.add_row(key.capitalize(), value, source)

    console.print(table)


def _show_validation_issues(console, issues):
    """Display validation issues."""
    for issue in issues:
        symbol = "✗" if issue.is_blocking() else "⚠"
        color = "red" if issue.is_blocking() else "yellow"

        _print(console, f"[{color}]{symbol} {issue.message}[/{color}]")

        if issue.fix_hint:
            _print(console, f"  [dim]→ {issue.fix_hint}[/dim]")


def _show_doctor_detection(console, details: Dict):
    """Show detailed detection results for doctor command."""
    _print(console, "[bold]Detection Results:[/bold]")

    # Runtime
    rt = details["runtime"]
    status = "✓" if rt["available"] else "✗"
    _print(console, f"{status} Runtime: {rt['value']} ({rt['path']})")

    # GPU
    gpu = details["gpu"]
    status = "✓" if gpu["devices_exist"] else "⚠"
    _print(console, f"{status} GPU: {gpu['details']}")

    # Display
    disp = details["display"]
    _print(
        console,
        f"✓ Display: {disp['value']} (session: {disp['session_type']}, var: {disp['display_var']})",
    )

    # Audio
    aud = details["audio"]
    _print(console, f"  Audio: {aud['details']}")


def _confirm_start(console, config: Dict) -> bool:
    """Ask user to confirm start."""
    if QUESTIONARY_AVAILABLE:
        return questionary.confirm("Start Minecraft with these settings?", default=True).ask()
    # Fallback to simple input
    response = input("\nStart Minecraft with these settings? [Y/n] ")
    return response.lower() in ["", "y", "yes"]


def _print(console, text: str):
    """Print with rich if available, plain otherwise."""
    if console:
        console.print(text)
    else:
        # Strip rich markup for plain printing
        import re

        plain_text = re.sub(r"\[.*?\]", "", text)
        print(plain_text)
