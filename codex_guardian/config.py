"""
Configuration management for Codex Guardian.
Handles loading/saving config from ~/.codex-guardian/config.json
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Default configuration
DEFAULT_CONFIG = {
    "alert_thresholds": {
        "health_score_critical": 40,
        "health_score_warning": 60,
        "token_burn_rate_warning": 1000,
        "token_burn_rate_critical": 5000,
        "runaway_detection_enabled": True,
        "budget_warning_percentages": [50, 75, 90, 100]
    },
    "notification_channels": {
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": ""
        },
        "discord": {
            "enabled": False,
            "webhook_url": ""
        },
        "slack": {
            "enabled": False,
            "webhook_url": ""
        }
    },
    "budget_limits": {
        "monthly_token_limit": 100000,
        "session_token_limit": 10000,
        "warn_at_percent": 80
    },
    "monitoring": {
        "check_interval_seconds": 30,
        "health_check_enabled": True,
        "budget_check_enabled": True,
        "token_burn_check_enabled": True,
        "runaway_check_enabled": True
    },
    "session_tracking": {
        "db_path": "~/.codex-guardian/sessions.db",
        "max_sessions": 100,
        "session_timeout_minutes": 60
    }
}


def get_config_path() -> Path:
    """Get the path to the config file."""
    return Path.home() / ".codex-guardian" / "config.json"


def ensure_config_dir():
    """Ensure the config directory exists."""
    config_dir = Path.home() / ".codex-guardian"
    config_dir.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    """
    Load configuration from the config file.
    
    Returns:
        Configuration dictionary, or default config if file doesn't exist
    """
    config_path = get_config_path()
    
    if not config_path.exists():
        # Create default config
        save_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        # Merge with defaults to ensure all keys exist
        return merge_config(DEFAULT_CONFIG, config)
    except (json.JSONDecodeError, IOError):
        return DEFAULT_CONFIG.copy()


def save_config(config: Dict[str, Any]) -> bool:
    """
    Save configuration to the config file.
    
    Args:
        config: Configuration dictionary to save
    
    Returns:
        True if successful, False otherwise
    """
    ensure_config_dir()
    config_path = get_config_path()
    
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError:
        return False


def merge_config(defaults: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge two configuration dictionaries.
    
    Args:
        defaults: Default configuration
        overrides: Overrides to apply
    
    Returns:
        Merged configuration
    """
    result = defaults.copy()
    
    for key, value in overrides.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_config(result[key], value)
        else:
            result[key] = value
    
    return result


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get a specific config value using dot notation.
    
    Args:
        key_path: Dot-separated path (e.g., "alert_thresholds.health_score_critical")
        default: Default value if key doesn't exist
    
    Returns:
        The config value or default
    """
    config = load_config()
    keys = key_path.split(".")
    
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    
    return value


def set_config_value(key_path: str, value: Any) -> bool:
    """
    Set a specific config value using dot notation.
    
    Args:
        key_path: Dot-separated path (e.g., "alert_thresholds.health_score_critical")
        value: Value to set
    
    Returns:
        True if successful, False otherwise
    """
    config = load_config()
    keys = key_path.split(".")
    
    # Navigate to the nested dict
    current = config
    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # Set the value
    current[keys[-1]] = value
    
    return save_config(config)


def reset_config() -> bool:
    """
    Reset configuration to defaults.
    
    Returns:
        True if successful
    """
    return save_config(DEFAULT_CONFIG)


def validate_config(config: Dict[str, Any]) -> list:
    """
    Validate configuration and return list of issues.
    
    Args:
        config: Configuration to validate
    
    Returns:
        List of validation issues (empty if valid)
    """
    issues = []
    
    # Check notification channels
    channels = config.get("notification_channels", {})
    for channel in ["telegram", "discord", "slack"]:
        channel_config = channels.get(channel, {})
        if channel_config.get("enabled"):
            if channel == "telegram":
                if not channel_config.get("bot_token"):
                    issues.append(f"Telegram enabled but bot_token is empty")
                if not channel_config.get("chat_id"):
                    issues.append(f"Telegram enabled but chat_id is empty")
            else:
                if not channel_config.get("webhook_url"):
                    issues.append(f"{channel.capitalize()} enabled but webhook_url is empty")
    
    # Check thresholds
    thresholds = config.get("alert_thresholds", {})
    if thresholds.get("health_score_critical", 0) >= thresholds.get("health_score_warning", 100):
        issues.append("health_score_critical must be less than health_score_warning")
    
    if thresholds.get("token_burn_rate_critical", 0) <= thresholds.get("token_burn_rate_warning", 0):
        issues.append("token_burn_rate_critical must be greater than token_burn_rate_warning")
    
    # Check budget limits
    budget = config.get("budget_limits", {})
    if budget.get("month_token_limit", 0) <= 0:
        issues.append("monthly_token_limit must be positive")
    
    return issues


# Initialize with default config if needed
ensure_config_dir()
if not get_config_path().exists():
    save_config(DEFAULT_CONFIG)
