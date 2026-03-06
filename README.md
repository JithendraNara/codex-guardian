# Codex Guardian 🛡️

**Protect your Codex CLI sessions from runaway token burn.**

Real-time monitoring, runaway detection, and budget alerts for OpenAI Codex CLI.

---

## The Problem

Codex CLI can burn through your token budget fast when sessions go wrong:
- Infinite loops with repeated tool calls
- Stuck sessions showing "Working..." for hours
- Runaway exec commands burning tokens
- No built-in budget alerts or spending limits

Users report **hundreds of dollars** in unexpected charges from single bad sessions.

---

## The Solution

Codex Guardian watches your Codex CLI sessions in real-time and:

- **Detects runaways early** - Catches infinite loops, token spikes, stuck states
- **Alerts you instantly** - Telegram, Discord, Slack notifications
- **Auto-terminates** - Kills sessions that exceed safety thresholds
- **Tracks spending** - Real-time budget monitoring with alerts at 50%, 75%, 90%, 100%

---

## Quick Start

```bash
# Install
pip install codex-guardian

# Configure (interactive)
codex-guardian config

# Start monitoring
codex-guardian monitor

# Check status
codex-guardian status
```

---

## Features

### Runaway Detection
- Infinite loop detection (repeated file edits, tool calls)
- Token burn rate monitoring (alerts on spikes)
- Stuck session detection (no progress for N minutes)
- Risky pattern flags (mass deletes, recursive ops)

### Alerts
- Telegram bot notifications
- Discord webhooks
- Slack webhooks
- Local alert history (SQLite)

### Budget Protection
- Configurable spending limits
- Percentage-based alerts (50%, 75%, 90%, 100%)
- Auto-terminate on hard limits
- Daily/weekly/monthly tracking

### Session Health
- Health score (0-100) for each active session
- Risk assessment before sessions spiral
- Historical session analytics

---

## Configuration

Edit `~/.codex-guardian/config.json`:

```json
{
  "budget": {
    "daily_limit_usd": 10.0,
    "alert_thresholds": [50, 75, 90, 100]
  },
  "detection": {
    "token_spike_threshold": 5000,
    "stuck_session_minutes": 5,
    "infinite_loop_calls": 5
  },
  "alerts": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID"
    },
    "discord": {
      "enabled": false,
      "webhook_url": ""
    }
  },
  "auto_terminate": {
    "enabled": true,
    "health_score_threshold": 20
  }
}
```

---

## CLI Commands

```bash
codex-guardian monitor      # Start real-time monitoring daemon
codex-guardian status       # Show active sessions and health scores
codex-guardian alerts       # View alert history
codex-guardian config       # Interactive config editor
codex-guardian sessions     # List all sessions with stats
codex-guardian analyze <id> # Deep dive on a specific session
```

---

## How It Works

1. **Log Parsing** - Reads `~/.codex/sessions/*/rollout-*.jsonl` files
2. **Event Extraction** - Parses tool calls, token usage, exec commands
3. **Pattern Detection** - Runs detection algorithms on live events
4. **Alerting** - Sends notifications when thresholds exceeded
5. **Protection** - Auto-terminates sessions that exceed safety limits

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Codex CLI      │────▶│  Log Parser      │────▶│  Detection      │
│  Sessions       │     │  (JSONL Reader)  │     │  Engine         │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Telegram/      │◀────│  Alert Engine    │◀────│  Health Score   │
│  Discord/Slack  │     │  Notifications   │     │  Calculator     │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

---

## Requirements

- Python 3.10+
- Codex CLI installed and configured
- Optional: Telegram bot token / Discord webhook / Slack webhook

---

## License

MIT License - See LICENSE file

---

## Support

- GitHub Issues: https://github.com/JithendraNara/codex-guardian/issues
- Documentation: https://github.com/JithendraNara/codex-guardian/docs

---

## Status

**✅ v0.1.0 Complete** - All core components built and tested:
- Log parser with JSONL reader
- Session index (SQLite)
- Runaway detection engine
- Alert system (Telegram/Discord/Slack)
- CLI interface

**Next Steps:**
1. Push to GitHub
2. Submit grant application
3. Community testing and feedback

---

*Built for the OpenAI Codex Open Source Fund application*
