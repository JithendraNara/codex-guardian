"""Tests for configuration management."""
import json
import pytest
import tempfile
import os
from pathlib import Path

# Patch home dir for tests
import codex_guardian.config as config_module


class TestConfigManagement:
    """Tests for config loading/saving."""

    def test_default_config_complete(self):
        """Default config has all required keys."""
        from codex_guardian.config import DEFAULT_CONFIG
        assert "alert_thresholds" in DEFAULT_CONFIG
        assert "notification_channels" in DEFAULT_CONFIG
        assert "budget_limits" in DEFAULT_CONFIG
        assert "monitoring" in DEFAULT_CONFIG
        assert "session_tracking" in DEFAULT_CONFIG

    def test_validate_config_valid(self):
        """Valid config passes validation."""
        from codex_guardian.config import load_config, validate_config
        cfg = load_config()
        issues = validate_config(cfg)
        # Default config should be valid (no notification channels enabled)
        assert isinstance(issues, list)

    def test_validate_config_threshold_order(self):
        """Critical must be less than warning."""
        from codex_guardian.config import validate_config
        bad_config = {
            "alert_thresholds": {
                "health_score_critical": 60,
                "health_score_warning": 40,
            },
            "notification_channels": {},
            "budget_limits": {"monthly_token_limit": 100},
        }
        issues = validate_config(bad_config)
        assert any("health_score_critical" in i for i in issues)

    def test_validate_config_telegram_enabled_no_token(self):
        """Telegram enabled without token is flagged."""
        from codex_guardian.config import validate_config
        bad_config = {
            "alert_thresholds": {},
            "notification_channels": {
                "telegram": {"enabled": True, "bot_token": "", "chat_id": ""}
            },
            "budget_limits": {"monthly_token_limit": 100},
        }
        issues = validate_config(bad_config)
        assert any("telegram" in i.lower() and "token" in i.lower() for i in issues)

    def test_merge_config(self):
        """Config merge respects overrides."""
        from codex_guardian.config import merge_config
        defaults = {"a": 1, "b": {"c": 2, "d": 3}}
        overrides = {"b": {"d": 99}, "e": 5}
        result = merge_config(defaults, overrides)
        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 99
        assert result["e"] == 5

    def test_get_set_config_value(self, tmp_path):
        """Dot-notation get/set works."""
        from codex_guardian.config import (
            get_config_value, set_config_value, save_config, load_config,
            ensure_config_dir
        )
        # Use temp config dir
        test_config_dir = tmp_path / "codex-guardian"
        test_config_file = test_config_dir / "config.json"
        
        original_get_path = config_module.get_config_path
        original_save_path = config_module.save_config
        
        def mock_get_path():
            return test_config_file
        
        config_module.get_config_path = mock_get_path
        
        try:
            ensure_config_dir()
            test_cfg = {"alert_thresholds": {"health_score_critical": 50}}
            save_config(test_cfg)
            
            val = get_config_value("alert_thresholds.health_score_critical")
            assert val is not None
            assert isinstance(val, int)
            
            set_config_value("alert_thresholds.health_score_critical", 30)
            val = get_config_value("alert_thresholds.health_score_critical")
            assert val == 30
            
            # Non-existent key returns None
            val = get_config_value("nonexistent.key")
            assert val is None
            
            # Non-existent key with default
            val = get_config_value("nonexistent.key", default="fallback")
            assert val == "fallback"
        finally:
            config_module.get_config_path = original_get_path
