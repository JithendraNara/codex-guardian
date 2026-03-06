"""
Detection thresholds configuration for Codex Guardian.
Configurable limits with presets for different sensitivity levels.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class Preset(Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class Thresholds:
    """Detection threshold configuration."""
    
    # Infinite loop detection
    same_file_modifications: int = 3  # Same file modified N times
    same_file_time_window_minutes: int = 2  # Within this time window
    same_tool_calls: int = 5  # Same tool called N times
    same_tool_time_window_minutes: int = 2  # Within this time window
    
    # Token spike detection
    token_spike_threshold: int = 5000  # Tokens per minute
    token_spike_sustained_minutes: int = 2  # Sustained for N minutes
    
    # Stuck session detection
    stuck_no_progress_minutes: int = 5  # No tool calls for N minutes
    stuck_require_working_status: bool = True  # Must have "Working..." status
    
    # Risky pattern detection
    risky_commands: list = None  # List of dangerous commands
    mass_file_threshold: int = 10  # N+ file operations in short time
    
    # Health score weights (must sum to 100)
    health_infinite_loop_weight: int = 25
    health_token_spike_weight: int = 25
    health_stuck_weight: int = 20
    health_risky_weight: int = 20
    health_duration_weight: int = 10
    
    # Session duration limits (minutes)
    max_session_duration_minutes: int = 120
    
    def __post_init__(self):
        if self.risky_commands is None:
            self.risky_commands = [
                "rm -rf",
                "rm -r /",
                "rm -f /",
                "del /f /s /q",
                "mkfs",
                "dd if=/dev/zero",
                ":(){:|:&};:",  # Fork bomb
                "chmod -R 777",
                "chown -R",
                "chmod 777",
            ]
    
    @classmethod
    def from_preset(cls, preset: Preset) -> "Thresholds":
        """Create thresholds from a preset."""
        presets = {
            Preset.CONSERVATIVE: cls(
                same_file_modifications=2,
                same_tool_calls=4,
                token_spike_threshold=3000,
                token_spike_sustained_minutes=1,
                stuck_no_progress_minutes=3,
                mass_file_threshold=5,
                max_session_duration_minutes=60,
            ),
            Preset.BALANCED: cls(
                same_file_modifications=3,
                same_tool_calls=5,
                token_spike_threshold=5000,
                token_spike_sustained_minutes=2,
                stuck_no_progress_minutes=5,
                mass_file_threshold=10,
                max_session_duration_minutes=120,
            ),
            Preset.AGGRESSIVE: cls(
                same_file_modifications=5,
                same_tool_calls=8,
                token_spike_threshold=10000,
                token_spike_sustained_minutes=3,
                stuck_no_progress_minutes=10,
                mass_file_threshold=20,
                max_session_duration_minutes=240,
            ),
        }
        return presets[preset]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Thresholds":
        """Create from dictionary."""
        # Handle risky_commands that might be stored as JSON string
        if isinstance(data.get("risky_commands"), str):
            data["risky_commands"] = json.loads(data["risky_commands"])
        return cls(**data)
    
    def save(self, path: Path) -> None:
        """Save to JSON file."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "Thresholds":
        """Load from JSON file."""
        with open(path) as f:
            return cls.from_dict(json.load(f))
    
    @classmethod
    def get_default_path(cls) -> Path:
        """Get default config path."""
        return Path.home() / ".config" / "codex-guardian" / "thresholds.json"
    
    @classmethod
    def load_default(cls) -> "Thresholds":
        """Load default configuration."""
        default_path = cls.get_default_path()
        if default_path.exists():
            return cls.load(default_path)
        return cls.from_preset(Preset.BALANCED)


# Default instance
default_thresholds = Thresholds.get_default_path()


def get_thresholds(config_path: Optional[Path] = None) -> Thresholds:
    """Get thresholds from config file or defaults."""
    if config_path and config_path.exists():
        return Thresholds.load(config_path)
    return Thresholds.load_default()
