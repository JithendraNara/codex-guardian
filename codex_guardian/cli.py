#!/usr/bin/env python3
"""
Command-line interface for Codex Guardian.
Provides commands for monitoring, status, alerts, and configuration.
"""

import argparse
import sys
import os
import json
import time
import sqlite3
import threading
from pathlib import Path
from datetime import datetime

# Add package to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from codex_guardian.alerter import get_alert_history, send_alert, init_db
from codex_guardian.config import load_config, save_config, get_config_value, set_config_value, DEFAULT_CONFIG


# Session database path
SESSIONS_DB = Path.home() / ".codex-guardian" / "sessions.db"


def init_sessions_db():
    """Initialize the sessions database."""
    SESSIONS_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(SESSIONS_DB))
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            start_time TEXT NOT NULL,
            last_update TEXT NOT NULL,
            health_score REAL,
            tokens_used INTEGER,
            status TEXT DEFAULT 'active'
        )
    """)
    conn.commit()
    conn.close()


def get_active_sessions():
    """Get all active sessions."""
    init_sessions_db()
    conn = sqlite3.connect(str(SESSIONS_DB))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE status = 'active' ORDER BY last_update DESC")
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions


def cmd_monitor(args):
    """Start the real-time monitoring daemon."""
    print("Starting Codex Guardian monitoring daemon...")
    print("Press Ctrl+C to stop")
    
    config = load_config()
    monitoring_config = config.get("monitoring", {})
    thresholds = config.get("alert_thresholds", {})
    budget_limits = config.get("budget_limits", {})
    
    check_interval = monitoring_config.get("check_interval_seconds", 30)
    last_budget_warnings = {}  # Track which warnings have been sent
    
    try:
        while True:
            # Check sessions
            sessions = get_active_sessions()
            
            for session in sessions:
                session_id = session["session_id"]
                health = session.get("health_score", 100)
                tokens_used = session.get("tokens_used", 0)
                
                # Check health score threshold
                health_threshold = thresholds.get("health_score_critical", 40)
                if health < health_threshold:
                    alert_data = {
                        "alert_type": "health",
                        "severity": "critical",
                        "message": f"Session {session_id[:8]} health score dropped to {health:.1f}",
                        "data": {
                            "session_id": session_id,
                            "health_score": health,
                            "threshold": health_threshold
                        }
                    }
                    send_alert(alert_data, config)
                    print(f"[ALERT] Health critical: {session_id[:8]} - {health:.1f}")
                
                # Check token burn rate (would need burn rate tracking)
                # For now, check total tokens against session limit
                session_limit = budget_limits.get("session_token_limit", 10000)
                token_percent = (tokens_used / session_limit) * 100 if session_limit > 0 else 0
                
                budget_warnings = thresholds.get("budget_warning_percentages", [50, 75, 90, 100])
                for warn_percent in budget_warnings:
                    key = f"{session_id}:{warn_percent}"
                    if token_percent >= warn_percent and last_budget_warnings.get(key, False) is False:
                        severity = "critical" if warn_percent == 100 else "warning"
                        alert_data = {
                            "alert_type": "budget",
                            "severity": severity,
                            "message": f"Session {session_id[:8]} reached {warn_percent}% of token budget",
                            "data": {
                                "session_id": session_id,
                                "tokens_used": tokens_used,
                                "limit": session_limit,
                                "percentage": warn_percent
                            }
                        }
                        send_alert(alert_data, config)
                        print(f"[ALERT] Budget {warn_percent}%: {session_id[:8]} - {tokens_used}/{session_limit}")
                        last_budget_warnings[key] = True
            
            # Check for runaway detection
            if thresholds.get("runaway_detection_enabled"):
                # Check for sessions with abnormal token usage patterns
                for session in sessions:
                    tokens = session.get("tokens_used", 0)
                    # Simple heuristic: if tokens > 5x session limit, likely runaway
                    if tokens > budget_limits.get("session_token_limit", 10000) * 5:
                        alert_data = {
                            "alert_type": "runaway",
                            "severity": "critical",
                            "message": f"Potential runaway session detected: {session['session_id'][:8]}",
                            "data": {
                                "session_id": session["session_id"],
                                "tokens_used": tokens
                            }
                        }
                        send_alert(alert_data, config)
                        print(f"[ALERT] Runaway detected: {session['session_id'][:8]} - {tokens} tokens")
            
            time.sleep(check_interval)
    
    except KeyboardInterrupt:
        print("\nMonitoring stopped.")


def cmd_status(args):
    """Show active sessions and health status."""
    sessions = get_active_sessions()
    
    if not sessions:
        print("No active sessions found.")
        return
    
    config = load_config()
    thresholds = config.get("alert_thresholds", {})
    budget_limits = config.get("budget_limits", {})
    
    print(f"\n{'='*60}")
    print(f"Codex Guardian Status")
    print(f"{'='*60}")
    print(f"Active Sessions: {len(sessions)}")
    print()
    
    health_threshold = thresholds.get("health_score_critical", 40)
    
    for session in sessions:
        sid = session["session_id"]
        health = session.get("health_score", 100)
        tokens = session.get("tokens_used", 0)
        last_update = session.get("last_update", "unknown")
        
        # Health status
        if health < health_threshold:
            status = "🔴 CRITICAL"
        elif health < thresholds.get("health_score_warning", 60):
            status = "🟡 WARNING"
        else:
            status = "🟢 OK"
        
        # Token status
        session_limit = budget_limits.get("session_token_limit", 10000)
        token_percent = (tokens / session_limit) * 100 if session_limit > 0 else 0
        
        print(f"Session: {sid[:16]}...")
        print(f"  Status: {status}")
        print(f"  Health: {health:.1f}")
        print(f"  Tokens: {tokens:,} / {session_limit:,} ({token_percent:.1f}%)")
        print(f"  Last Update: {last_update}")
        print()
    
    # Show config health thresholds
    print(f"Thresholds:")
    print(f"  Health Critical: < {health_threshold}")
    print(f"  Health Warning: < {thresholds.get('health_score_warning', 60)}")
    print(f"  Token Burn Warning: > {thresholds.get('token_burn_rate_warning', 1000)}/min")
    print()


def cmd_alerts(args):
    """Show alert history."""
    limit = args.limit
    alerts = get_alert_history(limit)
    
    if not alerts:
        print("No alerts found.")
        return
    
    print(f"\n{'='*60}")
    print(f"Alert History (showing {len(alerts)} of {limit})")
    print(f"{'='*60}\n")
    
    severity_emoji = {
        "critical": "🔴",
        "warning": "🟡",
        "info": "ℹ️"
    }
    
    for alert in alerts:
        emoji = severity_emoji.get(alert["severity"], "ℹ️")
        timestamp = alert["timestamp"][:19].replace("T", " ")
        
        print(f"{emoji} [{alert['severity'].upper()}] {timestamp}")
        print(f"   Type: {alert['alert_type']}")
        print(f"   Message: {alert['message']}")
        
        if alert.get("channels_notified"):
            print(f"   Notified: {', '.join(alert['channels_notified'])}")
        
        print()


def cmd_config(args):
    """Interactive configuration editor."""
    if args.reset:
        confirm = input("Reset all config to defaults? (yes/no): ")
        if confirm.lower() == "yes":
            save_config(DEFAULT_CONFIG)
            print("Config reset to defaults.")
        return
    
    if args.set:
        # Set a specific value
        key, _, value = args.set.partition("=")
        if not value:
            print("Error: Use format key=value")
            return
        
        # Try to parse value as JSON (for booleans, numbers, lists)
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            pass  # Keep as string
        
        if set_config_value(key, value):
            print(f"Set {key} = {value}")
        else:
            print(f"Failed to set {key}")
        return
    
    if args.get:
        value = get_config_value(args.get)
        print(f"{args.get} = {value}")
        return
    
    # Interactive mode
    config = load_config()
    
    print(f"\n{'='*60}")
    print(f"Codex Guardian Configuration")
    print(f"{'='*60}\n")
    
    # Show current config
    print("Current Configuration:")
    print(json.dumps(config, indent=2))
    print()
    
    # Offer to edit
    print("Options:")
    print("  1. Edit alert thresholds")
    print("  2. Edit notification channels")
    print("  3. Edit budget limits")
    print("  4. Edit monitoring settings")
    print("  5. Save and exit")
    print("  6. Exit without saving")
    print()
    
    choice = input("Select option (1-6): ").strip()
    
    if choice == "1":
        edit_alert_thresholds(config)
    elif choice == "2":
        edit_notification_channels(config)
    elif choice == "3":
        edit_budget_limits(config)
    elif choice == "4":
        edit_monitoring_settings(config)
    elif choice == "5":
        save_config(config)
        print("Configuration saved.")
        return
    
    print("Exiting without saving.")


def edit_alert_thresholds(config):
    """Edit alert threshold settings."""
    thresholds = config.get("alert_thresholds", {})
    
    print("\nAlert Thresholds:")
    
    for key in ["health_score_critical", "health_score_warning", 
                "token_burn_rate_warning", "token_burn_rate_critical"]:
        current = thresholds.get(key, 0)
        new_val = input(f"  {key} (current: {current}): ").strip()
        if new_val:
            try:
                thresholds[key] = int(new_val)
            except ValueError:
                print(f"  Invalid value, keeping {current}")
    
    # Boolean options
    for key in ["runaway_detection_enabled"]:
        current = thresholds.get(key, True)
        new_val = input(f"  {key} (current: {current}): ").strip().lower()
        if new_val in ("true", "1", "yes"):
            thresholds[key] = True
        elif new_val in ("false", "0", "no"):
            thresholds[key] = False
    
    # Budget warnings
    current = thresholds.get("budget_warning_percentages", [50, 75, 90, 100])
    new_val = input(f"  budget_warning_percentages (current: {current}): ").strip()
    if new_val:
        try:
            thresholds["budget_warning_percentages"] = json.loads(new_val)
        except:
            print(f"  Invalid value, keeping {current}")
    
    config["alert_thresholds"] = thresholds


def edit_notification_channels(config):
    """Edit notification channel settings."""
    channels = config.get("notification_channels", {})
    
    for channel in ["telegram", "discord", "slack"]:
        print(f"\n{channel.capitalize()} Settings:")
        channel_config = channels.get(channel, {})
        
        enabled = channel_config.get("enabled", False)
        new_val = input(f"  enabled (current: {enabled}): ").strip().lower()
        if new_val in ("true", "1", "yes"):
            channel_config["enabled"] = True
        elif new_val in ("false", "0", "no"):
            channel_config["enabled"] = False
        
        if channel == "telegram":
            for key in ["bot_token", "chat_id"]:
                current = channel_config.get(key, "")
                new_val = input(f"  {key} (current: {'*' * len(current) if current else 'empty'}): ").strip()
                if new_val:
                    channel_config[key] = new_val
        else:
            current = channel_config.get("webhook_url", "")
            new_val = input(f"  webhook_url (current: {'*' * 20 if current else 'empty'}): ").strip()
            if new_val:
                channel_config["webhook_url"] = new_val
        
        channels[channel] = channel_config
    
    config["notification_channels"] = channels


def edit_budget_limits(config):
    """Edit budget limit settings."""
    budget = config.get("budget_limits", {})
    
    print("\nBudget Limits:")
    
    for key in ["monthly_token_limit", "session_token_limit"]:
        current = budget.get(key, 0)
        new_val = input(f"  {key} (current: {current}): ").strip()
        if new_val:
            try:
                budget[key] = int(new_val)
            except ValueError:
                print(f"  Invalid value, keeping {current}")
    
    current = budget.get("warn_at_percent", 80)
    new_val = input(f"  warn_at_percent (current: {current}): ").strip()
    if new_val:
        try:
            budget["warn_at_percent"] = int(new_val)
        except ValueError:
            print(f"  Invalid value, keeping {current}")
    
    config["budget_limits"] = budget


def edit_monitoring_settings(config):
    """Edit monitoring settings."""
    monitoring = config.get("monitoring", {})
    
    print("\nMonitoring Settings:")
    
    # Interval
    current = monitoring.get("check_interval_seconds", 30)
    new_val = input(f"  check_interval_seconds (current: {current}): ").strip()
    if new_val:
        try:
            monitoring["check_interval_seconds"] = int(new_val)
        except ValueError:
            print(f"  Invalid value, keeping {current}")
    
    # Boolean options
    for key in ["health_check_enabled", "budget_check_enabled", 
                "token_burn_check_enabled", "runaway_check_enabled"]:
        current = monitoring.get(key, True)
        new_val = input(f"  {key} (current: {current}): ").strip().lower()
        if new_val in ("true", "1", "yes"):
            monitoring[key] = True
        elif new_val in ("false", "0", "no"):
            monitoring[key] = False
    
    config["monitoring"] = monitoring


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Codex Guardian - AI Session Protection System",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Start real-time monitoring daemon")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Show active sessions and health")
    
    # Alerts command
    alerts_parser = subparsers.add_parser("alerts", help="Show alert history")
    alerts_parser.add_argument("-n", "--limit", type=int, default=50, help="Number of alerts to show")
    
    # Config command
    config_parser = subparsers.add_parser("config", help="Interactive config editor")
    config_parser.add_argument("--get", type=str, help="Get a config value (dot notation)")
    config_parser.add_argument("--set", type=str, help="Set a config value (key=value)")
    config_parser.add_argument("--reset", action="store_true", help="Reset config to defaults")
    
    args = parser.parse_args()
    
    if args.command == "monitor":
        cmd_monitor(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "alerts":
        cmd_alerts(args)
    elif args.command == "config":
        cmd_config(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
