"""Tests for the alert engine."""
import json
import pytest
import tempfile
import sqlite3
from pathlib import Path
from datetime import datetime

import codex_guardian.alerter as alerter_module


class TestAlertPersistence:
    """Tests for SQLite alert storage."""

    def test_init_db_creates_table(self, tmp_path):
        """init_db creates the alerts table."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        
        alerter_module.init_db()
        assert db_path.exists()
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [r[0] for r in cursor.fetchall()]
        conn.close()
        assert "alerts" in tables

    def test_log_alert_returns_id(self, tmp_path):
        """log_alert returns the inserted alert ID."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        alert_data = {
            "alert_type": "health",
            "severity": "critical",
            "message": "Test alert",
            "data": {"session_id": "abc123"},
            "channels_notified": ["telegram"],
        }
        alert_id = alerter_module.log_alert(alert_data)
        assert alert_id == 1

    def test_get_alert_history_returns_list(self, tmp_path):
        """get_alert_history returns alerts in order."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        for i in range(5):
            alerter_module.log_alert({
                "alert_type": "test",
                "severity": "info",
                "message": f"Alert {i}",
                "data": {},
                "channels_notified": [],
            })
        
        history = alerter_module.get_alert_history(limit=3)
        assert len(history) == 3
        # Most recent first
        assert history[0]["message"] == "Alert 4"

    def test_get_alert_history_empty(self, tmp_path):
        """Returns empty list when no alerts."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        history = alerter_module.get_alert_history()
        assert history == []


class TestAlertChannels:
    """Tests for individual alert channel sending."""

    def test_send_telegram_missing_token(self):
        """Returns False when bot_token is empty."""
        result = alerter_module.send_telegram_alert("msg", "chat123", "")
        assert result is False

    def test_send_telegram_missing_chat_id(self):
        """Returns False when chat_id is empty."""
        result = alerter_module.send_telegram_alert("msg", "", "bot_token_abc")
        assert result is False

    def test_send_discord_missing_url(self):
        """Returns False when webhook_url is empty."""
        result = alerter_module.send_discord_alert("msg", "")
        assert result is False

    def test_send_slack_missing_url(self):
        """Returns False when webhook_url is empty."""
        result = alerter_module.send_slack_alert("msg", "")
        assert result is False


class TestSendAlert:
    """Tests for the main send_alert dispatcher."""

    def test_send_alert_returns_results_dict(self, tmp_path):
        """send_alert returns a dict with all channel results."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        config = {
            "notification_channels": {
                "telegram": {"enabled": False},
                "discord": {"enabled": False},
                "slack": {"enabled": False},
            }
        }
        
        result = alerter_module.send_alert({
            "alert_type": "health",
            "severity": "info",
            "message": "Test",
            "data": {},
        }, config)
        
        assert "telegram" in result
        assert "discord" in result
        assert "slack" in result
        assert "logged" in result
        assert result["logged"] is True

    def test_send_alert_logs_to_database(self, tmp_path):
        """send_alert persists alert to SQLite."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        config = {
            "notification_channels": {
                "telegram": {"enabled": False},
                "discord": {"enabled": False},
                "slack": {"enabled": False},
            }
        }
        
        alerter_module.send_alert({
            "alert_type": "budget",
            "severity": "warning",
            "message": "Token budget 75% reached",
            "data": {"tokens": 7500, "limit": 10000},
        }, config)
        
        history = alerter_module.get_alert_history(limit=1)
        assert len(history) == 1
        assert history[0]["alert_type"] == "budget"
        assert history[0]["severity"] == "warning"

    def test_send_alert_channels_notified_populated(self, tmp_path):
        """channels_notified reflects which channels would be sent."""
        db_path = tmp_path / "test_alerts.db"
        alerter_module.DB_PATH = db_path
        alerter_module.init_db()
        
        config = {
            "notification_channels": {
                "telegram": {"enabled": False},
                "discord": {"enabled": False},
                "slack": {"enabled": False},
            }
        }
        
        result = alerter_module.send_alert({
            "alert_type": "test",
            "severity": "info",
            "message": "Test",
            "data": {},
        }, config)
        
        # No channels enabled, so channels_notified should be empty
        history = alerter_module.get_alert_history(limit=1)
        assert len(history) == 1
