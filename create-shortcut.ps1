# Minecraft Launcher - Windows Shortcut Creator
# Run this script from PowerShell or WSL2 to create desktop shortcuts
#
# Usage:
#   From PowerShell:  .\create-shortcut.ps1
#   From WSL2:        powershell.exe -ExecutionPolicy Bypass -File create-shortcut.ps1

param(
    [switch]$StartMenu = $false
)

# Get the directory where this script is located
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# If running from WSL, convert WSL path to Windows path
if ($ScriptDir -match "^/mnt/([a-z])/(.*)") {
    $Drive = $matches[1].ToUpper()
    $Path = $matches[2] -replace "/", "\"
    $ScriptDir = "${Drive}:\${Path}"
}

Write-Host "Creating Minecraft Launcher shortcuts..." -ForegroundColor Cyan
Write-Host ""

# Paths
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$StartMenuPath = [Environment]::GetFolderPath("StartMenu")
$ShortcutPath = Join-Path $DesktopPath "Minecraft Launcher.lnk"
$IconPath = Join-Path $ScriptDir "icon.png"
$LauncherPath = Join-Path $ScriptDir "minecraft.py"

# Check if icon exists
if (-not (Test-Path $IconPath)) {
    Write-Host "⚠ Warning: icon.png not found. Generate it first with:" -ForegroundColor Yellow
    Write-Host "  convert icon.svg -resize 256x256 icon.png" -ForegroundColor Yellow
    Write-Host ""
}

# Create desktop shortcut
try {
    $WshShell = New-Object -ComObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut($ShortcutPath)

    # For WSL2: Use wsl.exe to launch Python in WSL
    $Shortcut.TargetPath = "wsl.exe"
    $Shortcut.Arguments = "-d Ubuntu python3 `"$LauncherPath`""
    $Shortcut.WorkingDirectory = $ScriptDir
    $Shortcut.Description = "Launch Minecraft with TLauncher in a containerized environment"

    # Set icon if it exists (Windows shortcuts need .ico, but .png works in some contexts)
    if (Test-Path $IconPath) {
        $Shortcut.IconLocation = $IconPath
    }

    $Shortcut.Save()
    Write-Host "✓ Desktop shortcut created: $ShortcutPath" -ForegroundColor Green
}
catch {
    Write-Host "✗ Failed to create desktop shortcut: $_" -ForegroundColor Red
}

# Create Start Menu shortcut if requested
if ($StartMenu) {
    $StartMenuShortcut = Join-Path $StartMenuPath "Programs\Minecraft Launcher.lnk"

    try {
        $Shortcut = $WshShell.CreateShortcut($StartMenuShortcut)
        $Shortcut.TargetPath = "wsl.exe"
        $Shortcut.Arguments = "-d Ubuntu python3 `"$LauncherPath`""
        $Shortcut.WorkingDirectory = $ScriptDir
        $Shortcut.Description = "Launch Minecraft with TLauncher in a containerized environment"

        if (Test-Path $IconPath) {
            $Shortcut.IconLocation = $IconPath
        }

        $Shortcut.Save()
        Write-Host "✓ Start Menu shortcut created: $StartMenuShortcut" -ForegroundColor Green
    }
    catch {
        Write-Host "✗ Failed to create Start Menu shortcut: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "✓ Installation complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Notes:" -ForegroundColor Cyan
Write-Host "  - Shortcut uses WSL2 to launch the Python launcher" -ForegroundColor Gray
Write-Host "  - Make sure Docker Desktop for Windows is running" -ForegroundColor Gray
Write-Host "  - Ensure X server (VcXsrv/Xming) is running for display" -ForegroundColor Gray
Write-Host ""
Write-Host "To uninstall:" -ForegroundColor Cyan
Write-Host "  Remove-Item '$ShortcutPath'" -ForegroundColor Gray

if ($StartMenu) {
    Write-Host "  Remove-Item '$StartMenuShortcut'" -ForegroundColor Gray
}

Write-Host ""
Write-Host "Alternative: Run directly from WSL2:" -ForegroundColor Yellow
Write-Host "  wsl.exe python3 $LauncherPath" -ForegroundColor Gray
