"""
GUI interface for Minecraft Launcher.
Provides graphical Tkinter-based interaction.
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from pathlib import Path
from typing import Dict

from core.detector import detect_system, get_detection_details
from core.config import load_config, save_config, merge_config
from core.validator import validate_system, run_xhost_if_needed
from core.container import start_container_async, ContainerManager
from core.composer import get_command_preview


class MinecraftLauncherGUI:
    """Main GUI application for Minecraft Launcher."""

    def __init__(self):
        """Initialize the GUI."""
        self.window = tk.Tk()
        self.window.title("Minecraft Launcher Launcher")
        self.window.geometry("1000x750")
        self.window.minsize(950, 700)
        self.window.resizable(True, True)

        # Modern theme and styling
        self._setup_theme()

        # X11: window icon and class so taskbar/dock shows our icon
        self._set_window_icon()
        # WM_CLASS for taskbar/dock (wm_class not available on all Tk builds)
        try:
            self.window.tk.call("wm", "class", self.window._w, "minecraft-launcher", "MinecraftLauncher")
        except (AttributeError, tk.TclError):
            pass

        self.config = {}
        self.detected = {}
        self.manager = None
        self._user_requested_stop = False
        self._monitor_enabled = False
        self._monitor_job = None
        self._container_pid = None

        self._create_widgets()
        self._detect_and_load()

    def _setup_theme(self):
        """Set up modern theme and colors."""
        style = ttk.Style()

        # Try to use a better theme if available
        available_themes = style.theme_names()
        if 'clam' in available_themes:
            style.theme_use('clam')
        elif 'alt' in available_themes:
            style.theme_use('alt')

        # Custom color scheme - Minecraft-inspired greens and modern grays
        bg_color = '#2b2b2b'          # Dark gray background
        fg_color = '#e8e8e8'          # Light text
        accent_color = '#7cbd3f'      # Minecraft grass green
        button_bg = '#3d3d3d'         # Button background
        button_active = '#4a4a4a'     # Button hover
        frame_bg = '#333333'          # Frame background

        # Configure window background
        self.window.configure(bg=bg_color)

        # Configure styles
        style.configure('TFrame', background=bg_color)
        style.configure('TLabel', background=bg_color, foreground=fg_color, font=('Segoe UI', 10))
        style.configure('TLabelframe', background=bg_color, foreground=fg_color, bordercolor=accent_color)
        style.configure('TLabelframe.Label', background=bg_color, foreground=accent_color, font=('Segoe UI', 10, 'bold'))

        # Button styling
        style.configure('TButton',
                       background=button_bg,
                       foreground=fg_color,
                       bordercolor=accent_color,
                       focuscolor=accent_color,
                       font=('Segoe UI', 9),
                       padding=8)
        style.map('TButton',
                 background=[('active', button_active), ('pressed', accent_color)],
                 foreground=[('active', fg_color)])

        # Combobox styling
        style.configure('TCombobox',
                       fieldbackground=button_bg,
                       background=button_bg,
                       foreground=fg_color,
                       arrowcolor=accent_color,
                       selectbackground=accent_color,
                       selectforeground=fg_color)

        style.map('TCombobox',
                 fieldbackground=[('readonly', button_bg)],
                 selectbackground=[('readonly', accent_color)],
                 selectforeground=[('readonly', fg_color)])

        # Configure combobox dropdown listbox colors
        self.window.option_add('*TCombobox*Listbox.background', button_bg)
        self.window.option_add('*TCombobox*Listbox.foreground', fg_color)
        self.window.option_add('*TCombobox*Listbox.selectBackground', accent_color)
        self.window.option_add('*TCombobox*Listbox.selectForeground', fg_color)
        self.window.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))

        # Configure colors for status labels
        self.colors = {
            'bg': bg_color,
            'fg': fg_color,
            'accent': accent_color,
            'success': '#4caf50',
            'warning': '#ff9800',
            'error': '#f44336',
            'info': '#2196f3'
        }

    def _set_window_icon(self):
        """Set the window icon for taskbar/dock (X11). Keeps a reference to avoid GC."""
        icon_path = Path(__file__).parent / "icon.png"
        if not icon_path.is_file():
            return
        try:
            # Try standard Tk PhotoImage (PNG supported on many Linux Tk builds)
            self._icon_photo = tk.PhotoImage(file=str(icon_path))
            self.window.iconphoto(True, self._icon_photo)
        except tk.TclError:
            try:
                # Fallback: Pillow if installed
                from PIL import Image, ImageTk
                img = Image.open(icon_path)
                self._icon_photo = ImageTk.PhotoImage(img)
                self.window.iconphoto(True, self._icon_photo)
            except (ImportError, OSError):
                pass

    def _create_widgets(self):
        """Create all GUI widgets."""
        # Main container with better padding
        main_frame = ttk.Frame(self.window, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)

        # Create left and right frames for two-column layout
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))

        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))

        main_frame.columnconfigure(0, weight=2)  # Left side for controls
        main_frame.columnconfigure(1, weight=1)  # Right side for monitor
        main_frame.rowconfigure(0, weight=1)

        # Header with title
        header_frame = ttk.Frame(left_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))

        title_label = ttk.Label(header_frame,
                               text="⛏ Minecraft Launcher Launcher",
                               font=('Segoe UI', 16, 'bold'),
                               foreground=self.colors['accent'])
        title_label.pack(side=tk.LEFT)

        subtitle_label = ttk.Label(header_frame,
                                   text="Containerized TLauncher",
                                   font=('Segoe UI', 9),
                                   foreground=self.colors['fg'])
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))

        # Configuration Frame with compact styling
        detect_frame = ttk.LabelFrame(left_frame, text="⚙ Config", padding="10")
        detect_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        # Runtime
        ttk.Label(detect_frame, text="Runtime:", font=('Segoe UI', 9)).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.runtime_var = tk.StringVar()
        self.runtime_combo = ttk.Combobox(detect_frame, textvariable=self.runtime_var,
                                          values=['auto', 'podman', 'docker'], state='readonly', width=12)
        self.runtime_combo.grid(row=0, column=1, sticky=tk.W)
        self.runtime_status_label = ttk.Label(detect_frame, text="", foreground="gray", font=('Segoe UI', 8))
        self.runtime_status_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))

        # GPU
        ttk.Label(detect_frame, text="GPU:", font=('Segoe UI', 9)).grid(row=0, column=3, sticky=tk.W, padx=(10, 5))
        self.gpu_var = tk.StringVar()
        self.gpu_combo = ttk.Combobox(detect_frame, textvariable=self.gpu_var,
                                      values=['auto', 'nvidia', 'amd'], state='readonly', width=12)
        self.gpu_combo.grid(row=0, column=4, sticky=tk.W)
        self.gpu_status_label = ttk.Label(detect_frame, text="", foreground="gray", font=('Segoe UI', 8))
        self.gpu_status_label.grid(row=0, column=5, sticky=tk.W, padx=(5, 0))

        # Display
        ttk.Label(detect_frame, text="Display:", font=('Segoe UI', 9)).grid(row=1, column=0, sticky=tk.W, padx=(0, 5), pady=(5, 0))
        self.display_var = tk.StringVar()
        self.display_combo = ttk.Combobox(detect_frame, textvariable=self.display_var,
                                          values=['auto', 'x11', 'wayland'], state='readonly', width=12)
        self.display_combo.grid(row=1, column=1, sticky=tk.W, pady=(5, 0))
        self.display_status_label = ttk.Label(detect_frame, text="", foreground="gray", font=('Segoe UI', 8))
        self.display_status_label.grid(row=1, column=2, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        # Audio
        ttk.Label(detect_frame, text="Audio:", font=('Segoe UI', 9)).grid(row=1, column=3, sticky=tk.W, padx=(10, 5), pady=(5, 0))
        self.audio_var = tk.StringVar()
        self.audio_combo = ttk.Combobox(detect_frame, textvariable=self.audio_var,
                                        values=['auto', 'pulseaudio', 'none'], state='readonly', width=12)
        self.audio_combo.grid(row=1, column=4, sticky=tk.W, pady=(5, 0))
        self.audio_status_label = ttk.Label(detect_frame, text="", foreground="gray", font=('Segoe UI', 8))
        self.audio_status_label.grid(row=1, column=5, sticky=tk.W, padx=(5, 0), pady=(5, 0))

        detect_frame.columnconfigure(5, weight=1)

        # Control Buttons Frame
        control_frame = ttk.Frame(left_frame)
        control_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))

        self.btn_start = ttk.Button(control_frame, text="Start", command=self.start_minecraft, width=12)
        self.btn_start.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_stop = ttk.Button(control_frame, text="Stop", command=self.stop_minecraft,
                                    state=tk.DISABLED, width=12)
        self.btn_stop.pack(side=tk.LEFT, padx=5)

        self.btn_restart = ttk.Button(control_frame, text="Restart", command=self.restart_minecraft,
                                      state=tk.DISABLED, width=12)
        self.btn_restart.pack(side=tk.LEFT, padx=5)

        self.btn_doctor = ttk.Button(control_frame, text="Doctor", command=self.run_doctor, width=12)
        self.btn_doctor.pack(side=tk.LEFT, padx=5)

        self.btn_save = ttk.Button(control_frame, text="Save Config", command=self.save_configuration, width=12)
        self.btn_save.pack(side=tk.LEFT, padx=5)

        self.btn_edit = ttk.Button(control_frame, text="Edit Config", command=self.edit_configuration, width=12)
        self.btn_edit.pack(side=tk.LEFT, padx=5)

        # Make left_frame columns expand properly
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=1)
        left_frame.rowconfigure(4, weight=1)  # Log frame expands

        # Status Label with icon and better styling
        status_frame = ttk.Frame(left_frame)
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))

        self.status_label = ttk.Label(status_frame,
                                      text="● Ready",
                                      font=('Segoe UI', 11, 'bold'),
                                      foreground=self.colors['success'])
        self.status_label.pack(side=tk.LEFT)

        # Log Output Frame with better styling
        log_frame = ttk.LabelFrame(left_frame, text="📋 Console Output", padding="15")
        log_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        # Styled scrolled text with dark theme
        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                  height=20,
                                                  wrap=tk.WORD,
                                                  bg='#1e1e1e',
                                                  fg='#d4d4d4',
                                                  insertbackground='#7cbd3f',
                                                  selectbackground='#3d3d3d',
                                                  font=('Consolas', 9),
                                                  relief=tk.FLAT,
                                                  borderwidth=0)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=2, pady=2)

        # Log buttons in a frame so they stay visible and aren't cut off
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(8, 2))
        btn_clear = ttk.Button(log_btn_frame, text="Clear Logs", command=self.clear_logs)
        btn_clear.pack(side=tk.LEFT, padx=(0, 5))
        btn_copy = ttk.Button(log_btn_frame, text="Copy all logs", command=self.copy_logs)
        btn_copy.pack(side=tk.LEFT)

        # Right side: Resource Monitor
        self._create_resource_monitor(right_frame)

    def _create_resource_monitor(self, parent_frame):
        """Create resource monitoring panel."""
        monitor_frame = ttk.LabelFrame(parent_frame, text="📊 Resource Monitor", padding="15")
        monitor_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Toggle button
        self.btn_monitor_toggle = ttk.Button(monitor_frame, text="Enable Monitor",
                                             command=self.toggle_monitor, width=15)
        self.btn_monitor_toggle.pack(pady=(0, 10))

        # Stats display
        stats_frame = ttk.Frame(monitor_frame)
        stats_frame.pack(fill=tk.BOTH, expand=True)

        # CPU
        ttk.Label(stats_frame, text="CPU:", font=('Segoe UI', 9, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=5)
        self.cpu_label = ttk.Label(stats_frame, text="--", foreground=self.colors['info'])
        self.cpu_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))

        # Memory
        ttk.Label(stats_frame, text="RAM:", font=('Segoe UI', 9, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=5)
        self.mem_label = ttk.Label(stats_frame, text="--", foreground=self.colors['info'])
        self.mem_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))

        # I/O Read
        ttk.Label(stats_frame, text="I/O Read:", font=('Segoe UI', 9, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=5)
        self.io_read_label = ttk.Label(stats_frame, text="--", foreground=self.colors['info'])
        self.io_read_label.grid(row=2, column=1, sticky=tk.W, padx=(10, 0))

        # I/O Write
        ttk.Label(stats_frame, text="I/O Write:", font=('Segoe UI', 9, 'bold')).grid(row=3, column=0, sticky=tk.W, pady=5)
        self.io_write_label = ttk.Label(stats_frame, text="--", foreground=self.colors['info'])
        self.io_write_label.grid(row=3, column=1, sticky=tk.W, padx=(10, 0))

        # GPU (if available)
        ttk.Label(stats_frame, text="GPU:", font=('Segoe UI', 9, 'bold')).grid(row=4, column=0, sticky=tk.W, pady=5)
        self.gpu_label = ttk.Label(stats_frame, text="--", foreground=self.colors['info'])
        self.gpu_label.grid(row=4, column=1, sticky=tk.W, padx=(10, 0))

        # Status
        self.monitor_status = ttk.Label(monitor_frame, text="Monitor disabled",
                                       font=('Segoe UI', 8), foreground='gray')
        self.monitor_status.pack(pady=(10, 0))

    def toggle_monitor(self):
        """Toggle resource monitoring on/off."""
        self._monitor_enabled = not self._monitor_enabled

        if self._monitor_enabled:
            self.btn_monitor_toggle.config(text="Disable Monitor")
            self.monitor_status.config(text="Monitoring active", foreground=self.colors['success'])
            self._update_resource_stats()
        else:
            self.btn_monitor_toggle.config(text="Enable Monitor")
            self.monitor_status.config(text="Monitor disabled", foreground='gray')
            if self._monitor_job:
                self.window.after_cancel(self._monitor_job)
                self._monitor_job = None
            # Reset labels
            self.cpu_label.config(text="--")
            self.mem_label.config(text="--")
            self.io_read_label.config(text="--")
            self.io_write_label.config(text="--")
            self.gpu_label.config(text="--")

    def _update_resource_stats(self):
        """Update resource statistics using container stats."""
        if not self._monitor_enabled:
            return

        try:
            import subprocess
            import re

            # Get container configuration
            config = self._gather_config()
            runtime = config.get('runtime', 'podman')
            container_name = "tlauncher"

            try:
                # Get container stats (one-shot, no stream)
                result = subprocess.run(
                    [runtime, 'stats', '--no-stream', '--format',
                     'json' if runtime == 'podman' else 'table',
                     container_name],
                    capture_output=True, text=True, timeout=3
                )

                if result.returncode == 0 and result.stdout.strip():
                    output = result.stdout.strip()

                    if runtime == 'podman':
                        # Podman outputs JSON array with one object
                        import json
                        stats_list = json.loads(output)

                        # Get first (and only) container stats
                        if isinstance(stats_list, list) and len(stats_list) > 0:
                            stats = stats_list[0]
                        else:
                            stats = stats_list if isinstance(stats_list, dict) else {}

                        # CPU % (Podman uses 'cpu_percent' not 'CPU')
                        cpu = stats.get('cpu_percent', '0%').replace('%', '')
                        self.cpu_label.config(text=f"{cpu}%")

                        # Memory (Podman uses 'mem_usage' not 'MemUsage')
                        mem_usage = stats.get('mem_usage', '0B / 0B')
                        mem_parts = mem_usage.split('/')
                        if mem_parts:
                            self.mem_label.config(text=mem_parts[0].strip())

                        # Network I/O (Podman uses 'net_io' not 'NetIO')
                        net_io = stats.get('net_io', '0B / 0B')
                        net_parts = net_io.split('/')
                        if len(net_parts) == 2:
                            self.io_read_label.config(text=f"↓ {net_parts[0].strip()}")
                            self.io_write_label.config(text=f"↑ {net_parts[1].strip()}")

                    else:
                        # Docker outputs table format
                        # Parse the output line (skip header if present)
                        lines = output.split('\n')
                        data_line = lines[-1] if len(lines) > 0 else ""

                        # Format: CONTAINER ID   NAME   CPU %   MEM USAGE / LIMIT   MEM %   NET I/O   BLOCK I/O   PIDS
                        parts = re.split(r'\s{2,}', data_line.strip())

                        if len(parts) >= 3:
                            # CPU % (index 2)
                            cpu = parts[2].replace('%', '')
                            self.cpu_label.config(text=f"{cpu}%")

                            # MEM USAGE (index 3)
                            if len(parts) >= 4:
                                mem_usage = parts[3].split('/')[0].strip()
                                self.mem_label.config(text=mem_usage)

                            # NET I/O (index 5)
                            if len(parts) >= 6:
                                net_io = parts[5]
                                net_parts = net_io.split('/')
                                if len(net_parts) == 2:
                                    self.io_read_label.config(text=f"↓ {net_parts[0].strip()}")
                                    self.io_write_label.config(text=f"↑ {net_parts[1].strip()}")

                    # GPU stats (NVIDIA only)
                    try:
                        if config.get('gpu') == 'nvidia':
                            gpu_result = subprocess.run(
                                ['nvidia-smi', '--query-gpu=utilization.gpu',
                                 '--format=csv,noheader,nounits'],
                                capture_output=True, text=True, timeout=1
                            )
                            if gpu_result.returncode == 0:
                                gpu_util = gpu_result.stdout.strip()
                                self.gpu_label.config(text=f"{gpu_util}%")
                            else:
                                self.gpu_label.config(text="--")
                        else:
                            self.gpu_label.config(text="N/A")
                    except (FileNotFoundError, subprocess.TimeoutExpired):
                        self.gpu_label.config(text="--")

                else:
                    # Container not running or not found
                    self._reset_monitor_labels()

            except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as e:
                self._reset_monitor_labels()

        except Exception as e:
            self.log(f"Monitor error: {e}")

        # Schedule next update (2 seconds)
        if self._monitor_enabled:
            self._monitor_job = self.window.after(2000, self._update_resource_stats)

    def _reset_monitor_labels(self):
        """Reset monitor labels when container is not running."""
        self.cpu_label.config(text="--")
        self.mem_label.config(text="--")
        self.io_read_label.config(text="--")
        self.io_write_label.config(text="--")
        self.gpu_label.config(text="--")

    def _detect_and_load(self):
        """Detect system and load configuration."""
        self.log("Detecting system configuration...")

        # Detect system
        self.detected = detect_system()

        # Load saved config
        saved = load_config()

        # Merge (saved overrides detection)
        self.config = merge_config(self.detected, saved)

        # Update UI
        self._update_ui_from_config()

        self.log(f"✓ Runtime: {self.detected['runtime']}")
        self.log(f"✓ GPU: {self.detected['gpu']}")
        self.log(f"✓ Display: {self.detected['display']}")
        self.log(f"✓ Audio: {self.detected['audio']}")

        # Check if container is already running
        self._check_existing_container()

    def _check_existing_container(self):
        """Check if the container is already running and update UI accordingly."""
        try:
            import subprocess
            runtime = self.detected.get('runtime', 'podman')
            container_name = "tlauncher"

            # Check container status
            result = subprocess.run(
                [runtime, 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=3
            )

            if result.returncode == 0 and container_name in result.stdout:
                # Container is already running
                self.log("\n⚠️  Detected existing Minecraft instance!")
                self.log("Container is already running.")
                self._update_status("Already Running", "warning")

                # Disable start button, enable stop button
                self.btn_start.config(state='disabled')
                self.btn_stop.config(state='normal')
                self.btn_restart.config(state='normal')

                # Create manager instance for the running container
                self.manager = ContainerManager(self.config)
            else:
                # Container not running
                self.log("\n🚀 Ready to start!")
                self._update_status("Ready", "success")

        except Exception as e:
            # If check fails, assume not running
            self.log("\n🚀 Ready to start!")
            self._update_status("Ready", "success")

    def _update_ui_from_config(self):
        """Update UI dropdowns from current config."""
        self.runtime_var.set('auto' if not self.config.get('runtime') or self.config['runtime'] == self.detected['runtime'] else self.config['runtime'])
        self.gpu_var.set('auto' if not self.config.get('gpu') or self.config['gpu'] == self.detected['gpu'] else self.config['gpu'])
        self.display_var.set('auto' if not self.config.get('display') or self.config['display'] == self.detected['display'] else self.config['display'])
        self.audio_var.set('auto' if not self.config.get('audio') or self.config['audio'] == self.detected['audio'] else self.config['audio'])

        # Update status labels
        self.runtime_status_label.config(text=f"(detected: {self.detected['runtime']})")
        self.gpu_status_label.config(text=f"(detected: {self.detected['gpu']})")
        self.display_status_label.config(text=f"(detected: {self.detected['display']})")
        self.audio_status_label.config(text=f"(detected: {self.detected['audio']})")

    def _gather_config(self) -> Dict[str, str]:
        """Gather configuration from UI."""
        runtime = self.runtime_var.get()
        gpu = self.gpu_var.get()
        display = self.display_var.get()
        audio = self.audio_var.get()

        # Convert 'auto' back to detected values
        return {
            'runtime': self.detected['runtime'] if runtime == 'auto' else runtime,
            'gpu': self.detected['gpu'] if gpu == 'auto' else gpu,
            'display': self.detected['display'] if display == 'auto' else display,
            'audio': self.detected['audio'] if audio == 'auto' else audio,
            'auto_xhost': True
        }

    def start_minecraft(self):
        """Start button handler."""
        # Check if already running
        try:
            import subprocess
            runtime = self.detected.get('runtime', 'podman')
            result = subprocess.run(
                [runtime, 'ps', '--filter', 'name=tlauncher', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and 'tlauncher' in result.stdout:
                self.log("\n⚠️  Container is already running!")
                messagebox.showinfo("Already Running",
                                   "Minecraft container is already running.\nUse Stop to stop it first.")
                return
        except Exception:
            pass  # If check fails, continue with start

        config = self._gather_config()

        # Validate
        self.log("\n" + "="*50)
        self.log("Validating system...")
        valid, issues = validate_system(config)

        if issues:
            for issue in issues:
                symbol = "✗" if issue.is_blocking() else "⚠"
                self.log(f"{symbol} {issue.message}")
                if issue.fix_hint:
                    self.log(f"  → {issue.fix_hint}")

        if not valid:
            self.log("\n✗ Validation failed. Cannot start.")
            self._update_status("Validation failed", "error")
            messagebox.showerror("Validation Failed",
                                "System validation failed. Check the output for details.")
            return

        self.log("✓ Validation passed")

        # Run xhost if needed
        if config['display'] == 'x11' and config.get('auto_xhost', True):
            self.log("Setting X11 permissions...")
            if run_xhost_if_needed(config):
                self.log("✓ X11 permissions set")
            else:
                self.log("⚠ Could not set X11 permissions automatically")

        # Show command
        self.log(f"\nCommand: {get_command_preview(config, 'up')}\n")

        # Update UI state
        self._update_status("Starting...", "warning")
        self.btn_start.config(state=tk.DISABLED)
        self.btn_doctor.config(state=tk.DISABLED)

        # Start container in background thread
        def output_callback(line):
            self.log(line)

        def started_callback():
            # Launcher GUI is up; run UI update on main thread
            def _on_started():
                self._update_status("Running", "success")
                self.btn_stop.config(state=tk.NORMAL)
                self.btn_restart.config(state=tk.NORMAL)
                self.log("\n✓ Container started successfully")

            self.window.after(0, _on_started)

        def completion_callback(success):
            # Container process exited; run UI update on main thread
            def _on_exited():
                self._update_status("Stopped", "gray")
                self.btn_start.config(state=tk.NORMAL)
                self.btn_stop.config(state=tk.DISABLED)
                self.btn_restart.config(state=tk.DISABLED)
                self.btn_doctor.config(state=tk.NORMAL)
                if self._user_requested_stop:
                    self._user_requested_stop = False
                    # Don't log "exited with error" — we intentionally stopped it
                elif success:
                    self.log("\n✓ Container stopped")
                else:
                    self.log("\n✗ Container exited with error")

            self.window.after(0, _on_exited)

        start_container_async(config, detached=False,
                              output_callback=output_callback,
                              started_callback=started_callback,
                              completion_callback=completion_callback)

    def stop_minecraft(self):
        """Stop button handler."""
        config = self._gather_config()

        self._user_requested_stop = True
        self.log("\n" + "="*50)
        self.log("Stopping container...")
        self._update_status("Stopping...", "warning")

        def stop_worker():
            manager = ContainerManager(config)
            success = manager.stop()

            def _on_stop_done():
                if success:
                    self._update_status("Stopped", "gray")
                    self.btn_start.config(state=tk.NORMAL)
                    self.btn_stop.config(state=tk.DISABLED)
                    self.btn_restart.config(state=tk.DISABLED)
                    self.btn_doctor.config(state=tk.NORMAL)
                    self.log("✓ Container stopped")
                else:
                    self._update_status("Running", "success")
                    self.log("✗ Failed to stop container")

            self.window.after(0, _on_stop_done)

        threading.Thread(target=stop_worker, daemon=True).start()

    def restart_minecraft(self):
        """Restart button handler."""
        config = self._gather_config()

        self.log("\n" + "="*50)
        self.log("Restarting container...")
        self._update_status("Restarting...", "warning")

        def restart_worker():
            manager = ContainerManager(config)

            def output_callback(line):
                self.log(line)

            success = manager.restart(output_callback=output_callback)

            if success:
                self._update_status("Running", "success")
                self.log("\n✓ Container restarted")
            else:
                self._update_status("Failed", "error")
                self.log("\n✗ Failed to restart container")

        threading.Thread(target=restart_worker, daemon=True).start()

    def run_doctor(self):
        """Doctor button handler - run validation."""
        self.log("\n" + "="*50)
        self.log("Running system diagnostics...\n")

        details = get_detection_details()

        # Show detection details
        rt = details['runtime']
        self.log(f"Runtime: {rt['value']} ({rt['path']})")

        gpu = details['gpu']
        self.log(f"GPU: {gpu['details']}")

        disp = details['display']
        self.log(f"Display: {disp['value']} (session: {disp['session_type']})")

        aud = details['audio']
        self.log(f"Audio: {aud['details']}")

        # Validate
        config = self._gather_config()
        self.log("\nValidation:")
        valid, issues = validate_system(config)

        if issues:
            for issue in issues:
                symbol = "✗" if issue.is_blocking() else "⚠"
                self.log(f"{symbol} {issue.message}")
                if issue.fix_hint:
                    self.log(f"  → {issue.fix_hint}")
        else:
            self.log("✓ No issues found")

        if valid:
            self.log("\n✓ System ready!")
            messagebox.showinfo("System Check", "System is ready to run Minecraft!")
        else:
            self.log("\n✗ System has errors")
            messagebox.showwarning("System Check", "System has validation errors. Check the output for details.")

    def save_configuration(self):
        """Save current configuration."""
        config = self._gather_config()

        # Save with 'auto' converted to empty strings
        save_data = {
            'runtime': '' if self.runtime_var.get() == 'auto' else config['runtime'],
            'gpu': '' if self.gpu_var.get() == 'auto' else config['gpu'],
            'display': '' if self.display_var.get() == 'auto' else config['display'],
            'audio': '' if self.audio_var.get() == 'auto' else config['audio'],
            'auto_xhost': True
        }

        if save_config(save_data):
            self.log("\n✓ Configuration saved")
            messagebox.showinfo("Configuration Saved", "Your configuration has been saved.")
        else:
            self.log("\n✗ Failed to save configuration")
            messagebox.showerror("Save Failed", "Could not save configuration.")

    def edit_configuration(self):
        """Open configuration file in text editor."""
        import subprocess
        import os
        from pathlib import Path

        # Get config file path
        config_dir = Path.home() / '.config' / 'minecraft-launcher'
        config_file = config_dir / 'config.yaml'

        # Create config directory if it doesn't exist
        config_dir.mkdir(parents=True, exist_ok=True)

        # Create empty config file if it doesn't exist
        if not config_file.exists():
            config_file.write_text("# Minecraft Launcher Launcher Configuration\n# Leave values empty to use auto-detection\n\nruntime: ''\ngpu: ''\ndisplay: ''\naudio: ''\nauto_xhost: true\n")
            self.log("\n✓ Created new config file")

        # Open in default text editor
        try:
            if os.name == 'posix':  # Linux/Unix
                subprocess.Popen(['xdg-open', str(config_file)])
            elif os.name == 'nt':  # Windows
                os.startfile(str(config_file))
            else:
                messagebox.showinfo("Config Location", f"Config file location:\n{config_file}")
                return

            self.log(f"\n✓ Opening config file: {config_file}")
            messagebox.showinfo("Config Editor", f"Opening config file in your default editor:\n{config_file}\n\nEdit and save the file, then restart the launcher to apply changes.")
        except Exception as e:
            self.log(f"\n✗ Failed to open config file: {e}")
            messagebox.showerror("Failed to Open", f"Could not open config file.\nLocation: {config_file}\n\nError: {e}")

    def clear_logs(self):
        """Clear the log output."""
        self.log_text.delete('1.0', tk.END)

    def copy_logs(self):
        """Copy full log content to the clipboard."""
        content = self.log_text.get('1.0', tk.END)
        if content.strip():
            self.window.clipboard_clear()
            self.window.clipboard_append(content)
            self.window.update_idletasks()
            self.log("(Logs copied to clipboard)")

    def log(self, message: str):
        """Append message to log output."""
        self.log_text.insert(tk.END, message + '\n')
        self.log_text.see(tk.END)
        self.log_text.update()

    def _update_status(self, text: str, color: str = "success"):
        """Update status label with colored indicator."""
        # Map color names to actual colors
        color_map = {
            'success': self.colors['success'],
            'green': self.colors['success'],
            'warning': self.colors['warning'],
            'orange': self.colors['warning'],
            'error': self.colors['error'],
            'red': self.colors['error'],
            'info': self.colors['info'],
            'gray': '#888888',
            'black': self.colors['fg']
        }

        actual_color = color_map.get(color, color)

        # Add status indicator dot
        if 'Running' in text:
            status_text = "● " + text.replace("Status: ", "")
        elif 'Starting' in text or 'Stopping' in text or 'Restarting' in text:
            status_text = "◐ " + text.replace("Status: ", "")
        elif 'Stopped' in text or 'Ready' in text:
            status_text = "○ " + text.replace("Status: ", "")
        elif 'Failed' in text or 'Error' in text:
            status_text = "✗ " + text.replace("Status: ", "")
        else:
            status_text = "● " + text.replace("Status: ", "")

        self.status_label.config(text=status_text, foreground=actual_color)

    def run(self):
        """Start the GUI main loop."""
        self.window.mainloop()
