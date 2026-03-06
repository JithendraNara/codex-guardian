"""
Codex Guardian - Detection Thresholds Configuration
Configurable detection thresholds for runaway session detection
"""

class DetectionThresholds:
    """Class containing all detection thresholds"""
    
    def __init__(self, preset="balanced"):
        """
        Initialize thresholds based on preset
        Args:
            preset (str): "conservative", "balanced", or "aggressive"
        """
        presets = {
            "conservative": {
                "token_spike_threshold": 3000,
                "tool_calls_per_minute": 10,
                "session_duration_limit": 15,  # minutes
                "infinite_loop_file_mods": 2,
                "infinite_loop_tool_calls": 3,
                "time_window_minutes": 2,
                "stuck_session_timeout": 3,
                "risky_patterns": [
                    "rm -rf",
                    "rm -r",
                    "rm *",
                    "mv *",
                    "cp *",
                    "chmod -R 777",
                    "chown -R",
                    "find . -exec",
                    "wget -O /dev/null",
                    "curl | sh",
                    "pip install -r",
                    "npm install",
                    "docker rm -f",
                    "kubectl delete",
                    "kill -9 -1",
                    "dd if=",
                    ">:",
                    ">>:",
                ]
            },
            "balanced": {
                "token_spike_threshold": 5000,
                "tool_calls_per_minute": 20,
                "session_duration_limit": 30,  # minutes
                "infinite_loop_file_mods": 3,
                "infinite_loop_tool_calls": 5,
                "time_window_minutes": 2,
                "stuck_session_timeout": 5,
                "risky_patterns": [
                    "rm -rf",
                    "rm -r",
                    "rm *",
                    "mv *",
                    "cp *",
                    "chmod -R 777",
                    "chown -R",
                    "find . -exec",
                    "curl | sh",
                    "pip install -r",
                    "npm install",
                    "docker rm -f",
                    "kubectl delete",
                ]
            },
            "aggressive": {
                "token_spike_threshold": 10000,
                "tool_calls_per_minute": 50,
                "session_duration_limit": 60,  # minutes
                "infinite_loop_file_mods": 5,
                "infinite_loop_tool_calls": 10,
                "time_window_minutes": 5,
                "stuck_session_timeout": 10,
                "risky_patterns": [
                    "rm -rf",
                    "curl | sh",
                    "chmod -R 777",
                ]
            }
        }
        
        config = presets.get(preset, presets["balanced"])
        self.token_spike_threshold = config["token_spike_threshold"]
        self.tool_calls_per_minute = config["tool_calls_per_minute"]
        self.session_duration_limit = config["session_duration_limit"]
        self.infinite_loop_file_mods = config["infinite_loop_file_mods"]
        self.infinite_loop_tool_calls = config["infinite_loop_tool_calls"]
        self.time_window_minutes = config["time_window_minutes"]
        self.stuck_session_timeout = config["stuck_session_timeout"]
        self.risky_patterns = config["risky_patterns"]

    def get_config(self):
        """Return current configuration as dictionary"""
        return {
            "token_spike_threshold": self.token_spike_threshold,
            "tool_calls_per_minute": self.tool_calls_per_minute,
            "session_duration_limit": self.session_duration_limit,
            "infinite_loop_file_mods": self.infinite_loop_file_mods,
            "infinite_loop_tool_calls": self.infinite_loop_tool_calls,
            "time_window_minutes": self.time_window_minutes,
            "stuck_session_timeout": self.stuck_session_timeout,
            "risky_patterns": self.risky_patterns
        }

    def update_from_dict(self, config_dict):
        """Update thresholds from a configuration dictionary"""
        for key, value in config_dict.items():
            if hasattr(self, key):
                setattr(self, key, value)


# Global instance for easy access
thresholds = DetectionThresholds()

def get_thresholds(preset="balanced"):
    """Get thresholds for a specific preset"""
    return DetectionThresholds(preset)

def load_config_from_file(config_path):
    """Load configuration from a JSON file"""
    import json
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        # Create new thresholds instance and update with file config
        new_thresholds = DetectionThresholds()
        new_thresholds.update_from_dict(config)
        return new_thresholds
    except Exception as e:
        print(f"Error loading config from {config_path}: {e}")
        return DetectionThresholds()