# Minecraft with TLauncher - Containerized Setup

Run Minecraft safely in an isolated container with full GPU acceleration, audio support, and automatic system detection.

## What Is This?

This project lets you run **Minecraft via TLauncher** inside a container (like a lightweight virtual machine) that:

✅ **Isolates Minecraft** from your main system (safer, cleaner)
✅ **Auto-detects** your GPU, display server, and audio system
✅ **Works out-of-the-box** with NVIDIA/AMD GPUs
✅ **Provides both GUI and CLI** interfaces
✅ **Runs on Linux and Windows** (via WSL2)

---

## Three Ways to Run

### 🎮 Option 1: Easy Launcher (Recommended)

**Best for:** Everyone, especially non-technical users

A Python wrapper with graphical interface and automatic detection.

```bash
./minecraft.py          # Opens GUI window
./minecraft.py start    # Or use terminal

# Add to application menu:
./create-shortcut.sh
```

**Features:**

- Double-click to launch
- Auto-detects everything
- One-click start/stop buttons
- Save your preferences
- Real-time log display

👉 **See:** [Setup Guide for Linux](SETUP-LINUX.md) | [Setup Guide for Windows](SETUP-WINDOWS.md)

---

### 🐳 Option 2: Direct Container Commands

**Best for:** Users comfortable with Docker/Podman

Use compose commands directly without the wrapper.

```bash
# Example: Podman + NVIDIA + X11 + Audio
xhost +SI:localuser:$USER
podman compose -f compose.base.yaml -f compose.podman.yaml \
  -f compose.nvidia.yaml -f compose.x11.yaml \
  -f compose.audio-pulseaudio.yaml up
```

👉 **See:** [Manual Compose Guide](manual-runbook.md)

---

### ⚙️ Option 3: Custom Configuration

**Best for:** Advanced users who want full control

Combine modular compose files for your exact setup.

```bash
# Mix and match:
# - Runtime: podman or docker
# - GPU: nvidia or amd
# - Display: x11 or wayland
# - Audio: pulseaudio or none

docker compose -f compose.base.yaml -f compose.docker.yaml \
  -f compose.amd.yaml -f compose.wayland.yaml \
  -f compose.audio-none.yaml up
```

---

## Quick Start

### 🐧 Linux Users

**1. Install dependencies:**

```bash
# Fedora/RHEL/CentOS
sudo dnf install podman python3-pyyaml

# Ubuntu/Debian
sudo apt install podman python3-yaml

# Arch
sudo pacman -S podman python-yaml
```

**2. Clone and build:**

```bash
cd ~/Games
git clone <this-repo> Minecraft
cd Minecraft
podman build -t tlauncher-java .
```

**3. Launch:**

```bash
./minecraft.py
```

👉 **Detailed guide:** [SETUP-LINUX.md](SETUP-LINUX.md)

---

### 🪟 Windows Users (WSL2)

**1. Install WSL2 with Ubuntu:**

```powershell
wsl --install -d Ubuntu
```

**2. Inside WSL2, install Docker Desktop:**

Follow: <https://docs.docker.com/desktop/wsl/>

**3. Clone and build:**

```bash
cd ~
git clone <this-repo> Minecraft
cd Minecraft
docker build -t tlauncher-java .
```

**4. Set up X server (VcXsrv or Xming):** See detailed guide below.

**5. Set DISPLAY variable:**

```bash
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

**6. Launch:**

```bash
./minecraft.py
```

**Optional: Create Windows desktop shortcut:**

```powershell
# From PowerShell (run as Administrator):
.\create-shortcut.ps1
```

👉 **Detailed guide:** [SETUP-WINDOWS.md](SETUP-WINDOWS.md)

---

## How It Works

### Architecture

```text
┌─────────────────────────────────────────┐
│  Your Computer (Host)                   │
│                                         │
│  ┌──────────────────────────────────┐  │
│  │  Container (Isolated)            │  │
│  │                                  │  │
│  │  ├─ TLauncher                   │  │
│  │  ├─ Minecraft                   │  │
│  │  ├─ Java Runtime                │  │
│  │  └─ Your Worlds & Mods          │  │
│  │                                  │  │
│  └──────────────────────────────────┘  │
│         ▲                                │
│         │ Shared:                        │
│         ├─ GPU (for graphics)           │
│         ├─ Audio (for sound)            │
│         └─ Display (for window)         │
└─────────────────────────────────────────┘
```

### File Organization

```text
Minecraft/
├── minecraft.py              # 🚀 Launcher (GUI + CLI)
├── compose.*.yaml            # 🐳 Container configurations
├── Containerfile             # 📦 Container image recipe
├── entrypoint.sh             # ⚙️  Startup script
│
├── launcher/                 # TLauncher app (auto-downloads)
├── home/                     # 🎮 Your worlds, mods, saves
└── tlauncher-data/          # 📝 TLauncher cache & logs
```

Your Minecraft data is stored in `./home/` - back this up regularly!

---

## Features

### 🎮 Easy Launcher Features

**GUI Mode** (graphical window):

- Auto-detects your system configuration
- Dropdown menus to override settings
- One-click start/stop/restart buttons
- Real-time log display
- Built-in system validation ("Doctor" button)
- Save preferences for next launch

**CLI Mode** (terminal):

- Rich terminal output with colors and tables
- Interactive confirmation menus
- Commands: start, stop, restart, logs, status, doctor
- Flag-based overrides: `--runtime docker --gpu amd`
- Works over SSH

### 🔒 Security

- Read-only container filesystem
- No privileged containers
- Isolated from host system
- All capabilities dropped
- Resource limits (CPU, memory, processes)

### 🎯 Auto-Detection

Automatically detects:

- Container runtime (Podman or Docker)
- GPU type (NVIDIA or AMD/Intel)
- Display server (X11 or Wayland)
- Audio system (PulseAudio/PipeWire or none)

### 🔧 Customization

Override any detection:

- **GUI:** Change dropdowns from "auto" to specific values
- **CLI:** Use flags: `--runtime docker --gpu amd --display wayland`
- **Config file:** Save preferences to `~/.config/minecraft-launcher/`

---

## Platform Support

| Platform        | Container Runtime | Display | Audio      | Status          |
|-----------------|-------------------|---------|------------|-----------------|
| Linux (X11)     | Podman, Docker    | ✅      | ✅         | Full support    |
| Linux (Wayland) | Podman, Docker    | ✅      | ✅         | Full support    |
| Windows (WSL2)  | Docker Desktop    | ✅      | ⚠️ Limited | Experimental    |
| macOS           | Docker Desktop    | ❌      | ❌         | Not supported   |

---

## Documentation

### For Users

- **[SETUP-LINUX.md](SETUP-LINUX.md)** - Step-by-step Linux installation
- **[SETUP-WINDOWS.md](SETUP-WINDOWS.md)** - Step-by-step Windows (WSL2) installation
- **[manual-runbook.md](manual-runbook.md)** - Manual compose commands reference

### For Developers

- **[WRAPPER-STRUCTURE.md](WRAPPER-STRUCTURE.md)** - Launcher architecture and code structure
- **[TLAUNCHER-STRUCTURE.md](TLAUNCHER-STRUCTURE.md)** - Minecraft data organization

---

## Troubleshooting

### No display window appears

**Linux:**

```bash
# For X11, grant access:
xhost +SI:localuser:$USER
./minecraft.py start
```

**Windows WSL2:**

```bash
# Ensure X server (VcXsrv) is running
# Set DISPLAY variable:
export DISPLAY=$(cat /etc/resolv.conf | grep nameserver | awk '{print $2}'):0
```

### No GPU acceleration

```bash
# Check detection:
./minecraft.py doctor

# Verify devices exist:
ls -la /dev/nvidia*   # For NVIDIA
ls -la /dev/dri       # For AMD/Intel
```

### No audio

```bash
# Check if audio system is running:
pactl info

# Verify socket exists:
ls -la /run/user/$(id -u)/pulse/native

# Try without audio:
./minecraft.py start --audio none
```

### Container fails to start

```bash
# Run system check:
./minecraft.py doctor

# Check compose files exist:
ls -la compose.*.yaml

# View detailed errors:
./minecraft.py start --yes
```

---

## FAQ

**Q: Do I need to install Minecraft separately?**
A: No! TLauncher downloads and manages Minecraft automatically.

**Q: Where are my worlds saved?**
A: In `./home/saves/` on your host machine (not inside the container).

**Q: Can I use mods?**
A: Yes! Place mods in `./home/mods/` - see [TLAUNCHER-STRUCTURE.md](TLAUNCHER-STRUCTURE.md)

**Q: Is this legal?**
A: Yes, TLauncher is a third-party launcher. Own a Minecraft account for full features.

**Q: Does this work with vanilla Minecraft?**
A: Yes, TLauncher supports vanilla Minecraft and modded versions (Forge, Fabric).

**Q: Can I run multiple instances?**
A: Yes, copy the entire directory and run each separately.

**Q: How do I update Minecraft?**
A: TLauncher handles updates automatically when you launch it.

**Q: What if I don't want the launcher wrapper?**
A: Use compose commands directly - see [manual-runbook.md](manual-runbook.md)

---

## Contributing

Found a bug or have a suggestion? Open an issue or pull request!

---

## License

This setup is provided as-is. Minecraft and TLauncher are separate projects with their own licenses.

---

## Credits

- **Minecraft** by Mojang Studios
- **TLauncher** by TLauncher Team
- **Container setup** by this repository's contributors

---

## Getting Help

1. **System check:** Run `./minecraft.py doctor` first
2. **Check logs:** Look in `./tlauncher-data/logs/`
3. **Platform guides:** [Linux](SETUP-LINUX.md) | [Windows](SETUP-WINDOWS.md)
4. **Issues:** Open a GitHub issue with doctor output

---

**Ready to play?** → [Linux Setup Guide](SETUP-LINUX.md) | [Windows Setup Guide](SETUP-WINDOWS.md)
