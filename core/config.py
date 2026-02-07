"""
Configuration management module for Minecraft Launcher.
Handles loading, saving, and merging user preferences.
"""

from pathlib import Path
from typing import Dict

import yaml

# Configuration file location
CONFIG_DIR = Path.home() / ".config" / "minecraft-launcher"
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def load_config() -> Dict[str, str]:
    """
    Load saved configuration from file.

    Returns:
        dict: Saved configuration, or empty dict if file doesn't exist
    """
    if not CONFIG_FILE.exists():
        return {}

    try:
        with open(CONFIG_FILE) as f:
            config = yaml.safe_load(f) or {}
            # Ensure all expected keys exist with empty string defaults
            return {
                "runtime": config.get("runtime", ""),
                "gpu": config.get("gpu", ""),
                "display": config.get("display", ""),
                "audio": config.get("audio", ""),
                "auto_xhost": config.get("auto_xhost", True),
            }
    except Exception as e:
        print(f"Warning: Could not load config file: {e}")
        return {}


def save_config(config: Dict[str, any]) -> bool:
    """
    Save configuration to file.

    Args:
        config: Configuration dictionary to save

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create config directory if it doesn't exist
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)

        # Filter out None values and convert to save format
        save_data = {
            "runtime": config.get("runtime", ""),
            "gpu": config.get("gpu", ""),
            "display": config.get("display", ""),
            "audio": config.get("audio", ""),
            "auto_xhost": config.get("auto_xhost", True),
        }

        with open(CONFIG_FILE, "w") as f:
            yaml.dump(save_data, f, default_flow_style=False)

        return True
    except Exception as e:
        print(f"Error: Could not save config file: {e}")
        return False


def merge_config(detected: Dict[str, str], saved: Dict[str, str]) -> Dict[str, str]:
    """
    Merge detected and saved configurations.
    Saved config overrides detection for non-empty values.

    Args:
        detected: Auto-detected configuration
        saved: User-saved configuration

    Returns:
        dict: Merged configuration
    """
    merged = detected.copy()

    # Override with saved config if value is not empty
    for key in ["runtime", "gpu", "display", "audio"]:
        saved_value = saved.get(key, "")
        if saved_value and saved_value.strip():
            merged[key] = saved_value

    # Add auto_xhost setting
    merged["auto_xhost"] = saved.get("auto_xhost", True)

    return merged


def get_config_path() -> Path:
    """
    Get the configuration file path.

    Returns:
        Path: Path to config file
    """
    return CONFIG_FILE


def config_exists() -> bool:
    """
    Check if configuration file exists.

    Returns:
        bool: True if config file exists
    """
    return CONFIG_FILE.exists()


def reset_config() -> bool:
    """
    Delete the configuration file.

    Returns:
        bool: True if successful or file didn't exist
    """
    try:
        if CONFIG_FILE.exists():
            CONFIG_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error: Could not delete config file: {e}")
        return False


def create_default_config() -> Dict[str, any]:
    """
    Create a default configuration template.

    Returns:
        dict: Default configuration
    """
    return {
        "runtime": "",  # Empty means auto-detect
        "gpu": "",
        "display": "",
        "audio": "",
        "auto_xhost": True,
    }
