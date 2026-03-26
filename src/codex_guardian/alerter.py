"""
Alert engine for Codex Guardian.
Handles notifications via Telegram, Discord, Slack and persists alerts to SQLite.
"""

import sqlite3
import requests
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

# Database path
DB_PATH = Path.home() / ".codex-guardian" / "alerts.db"

# Ensure database directory exists
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_db():
    """Initialize the alerts database."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            data TEXT,
            channels_notified TEXT
        )
    """)
    conn.commit()
    conn.close()


def send_telegram_alert(message: str, chat_id: str, bot_token: str) -> bool:
    """
    Send a Telegram notification.
    
    Args:
        message: The alert message to send
        chat_id: Telegram chat ID
        bot_token: Telegram bot token
    
    Returns:
        True if successful, False otherwise
    """
    if not bot_token or not chat_id:
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def send_discord_alert(message: str, webhook_url: str) -> bool:
    """
    Send a Discord webhook notification.
    
    Args:
        message: The alert message to send
        webhook_url: Discord webhook URL
    
    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        return False
    
    payload = {
        "content": message,
        "username": "Codex Guardian",
        "avatar_url": "https://i.imgur.com/AfFp7pu.png"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code in (200, 204)
    except Exception:
        return False


def send_slack_alert(message: str, webhook_url: str) -> bool:
    """
    Send a Slack webhook notification.
    
    Args:
        message: The alert message to send
        webhook_url: Slack webhook URL
    
    Returns:
        True if successful, False otherwise
    """
    if not webhook_url:
        return False
    
    payload = {
        "text": message,
        "username": "Codex Guardian",
        "icon_emoji": ":warning:"
    }
    
    try:
        response = requests.post(webhook_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception:
        return False


def log_alert(alert_data: Dict[str, Any]) -> int:
    """
    Persist an alert to the local SQLite database.
    
    Args:
        alert_data: Dictionary containing alert details:
            - alert_type: Type of alert (health, budget, runaway, token_burn)
            - severity: Severity level (critical, warning, info)
            - message: Human-readable message
            - data: Additional JSON-serializable data
            - channels_notified: List of channels that were notified
    
    Returns:
        The ID of the inserted alert
    """
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    timestamp = datetime.now().isoformat()
    alert_type = alert_data.get("alert_type", "unknown")
    severity = alert_data.get("severity", "info")
    message = alert_data.get("message", "")
    data = json.dumps(alert_data.get("data", {}))
    channels = json.dumps(alert_data.get("channels_notified", []))
    
    cursor.execute(
        """INSERT INTO alerts (timestamp, alert_type, severity, message, data, channels_notified)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (timestamp, alert_type, severity, message, data, channels)
    )
    
    alert_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return alert_id


def get_alert_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    Retrieve recent alerts from the database.
    
    Args:
        limit: Maximum number of alerts to retrieve (default 50)
    
    Returns:
        List of alert dictionaries
    """
    init_db()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute(
        """SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?""",
        (limit,)
    )
    
    alerts = []
    for row in cursor.fetchall():
        alert = {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "alert_type": row["alert_type"],
            "severity": row["severity"],
            "message": row["message"],
            "data": json.loads(row["data"]) if row["data"] else {},
            "channels_notified": json.loads(row["channels_notified"]) if row["channels_notified"] else []
        }
        alerts.append(alert)
    
    conn.close()
    return alerts


def send_alert(alert_data: Dict[str, Any], config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send an alert through all configured channels and persist to database.
    
    Args:
        alert_data: Alert details
        config: Configuration dictionary with notification settings
    
    Returns:
        Dictionary with send results for each channel
    """
    results = {
        "telegram": False,
        "discord": False,
        "slack": False,
        "logged": False
    }
    
    channels = config.get("notification_channels", {})
    
    # Build the alert message with severity emoji
    severity = alert_data.get("severity", "info")
    emoji = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "ℹ️"
    }.get(severity, "ℹ️")
    
    message = f"{emoji} <b>Codex Guardian Alert</b>\n\n"
    message += f"<b>Type:</b> {alert_data.get('alert_type', 'unknown')}\n"
    message += f"<b>Severity:</b> {severity.upper()}\n"
    message += f"<b>Message:</b> {alert_data.get('message', '')}\n"
    
    if alert_data.get("data"):
        message += f"\n<b>Details:</b>\n<pre>{json.dumps(alert_data['data'], indent=2)}</pre>"
    
    # Send to Telegram
    telegram_config = channels.get("telegram", {})
    if telegram_config.get("enabled") and telegram_config.get("bot_token"):
        results["telegram"] = send_telegram_alert(
            message,
            telegram_config.get("chat_id", ""),
            telegram_config.get("bot_token", "")
        )
    
    # Send to Discord
    discord_config = channels.get("discord", {})
    if discord_config.get("enabled") and discord_config.get("webhook_url"):
        results["discord"] = send_discord_alert(
            message,
            discord_config.get("webhook_url", "")
        )
    
    # Send to Slack
    slack_config = channels.get("slack", {})
    if slack_config.get("enabled") and slack_config.get("webhook_url"):
        results["slack"] = send_slack_alert(
            message,
            slack_config.get("webhook_url", "")
        )
    
    # Log to database
    alert_data["channels_notified"] = [k for k, v in results.items() if v]
    alert_data["logged"] = True
    results["logged"] = True
    
    log_alert(alert_data)
    
    return results


# Initialize database on module load
init_db()
