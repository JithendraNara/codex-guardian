# Codex Guardian

**Stop Codex CLI from burning your token budget.**

Codex Guardian monitors your Codex CLI sessions in real-time, detects runaway patterns, and alerts you before costs spiral out of control. Auto-terminates dangerous sessions before they drain your account.

[![PyPI Version](https://img.shields.io/pypi/v/codex-guardian.svg)](https://pypi.org/project/codex-guardian/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Stars](https://img.shields.io/github/stars/JithendraNara/codex-guardian)](https://github.com/JithendraNara/codex-guardian/stargazers)

---

## The Problem

Codex CLI sessions can burn hundreds of dollars in minutes. A buggy loop, a recursive operation, a stuck session — all can generate thousands of tokens while you're away from your keyboard.

**Real reports:**
- "I left a session running for 2 hours and it cost me $340"
- "An infinite loop ran up $1,200 before I noticed"

There's no built-in safety net. This fills that gap.

---

## How It Works

```
┌─────────────────────────┐      ┌──────────────────┐
│  Codex CLI Session      │      │  Codex Guardian  │
│  ~/.codex/sessions/     │─────▶│  Monitor Daemon  │
│  (JSONL log files)      │      └────────┬─────────┘
└─────────────────────────┘               │
                                            ▼
                              ┌────────────────────────┐
                              │   Detection Engine     │
                              │  • Infinite loop      │
                              │  • Token spike         │
                              │  • Stuck session       │
                              │  • Risky commands      │
                              │  • Health Score (0-100)│
                              └───────────┬────────────┘
                                          │
                    ┌─────────────────────┼─────────────────────┐
                    ▼                     ▼                     ▼
              ┌──────────┐         ┌──────────────┐        ┌──────────┐
              │ Telegram │         │  Discord/    │        │  Slack   │
              │  Bot     │         │  Webhooks    │        │  Webhooks│
              └──────────┘         └──────────────┘        └──────────┘
```

Codex Guardian reads session logs directly from `~/.codex/sessions/` — zero interference with Codex itself.

---

## Features

### 🔍 Detection
- **Infinite loop detection** — same file modified N times, same tool called repeatedly
- **Token spike monitoring** — alerts when burn rate exceeds threshold
- **Stuck session detection** — session with no progress for N minutes
- **Risky command flags** — detects dangerous commands (rm -rf, fork bombs, etc.)
- **Mass file operations** — flags excessive file create/delete in short window

### 📊 Health Score (0-100)
Composite score per session. Weighted algorithm across all detection signals. Auto-terminates when score drops below threshold.

### 💰 Cost Projection
Estimates cost-to-date and projects end-of-session cost based on current burn rate.

### 🚨 Multi-Channel Alerts
- Telegram bot (with chat ID support)
- Discord webhooks
- Slack webhooks
- SQLite local log (always)

### ⚙️ Configurable Everything
- Token burn rate thresholds
- Health score warning/critical levels
- Budget limits (session + monthly)
- Alert escalation percentages (50%, 75%, 90%, 100%)
- Detection sensitivity presets (conservative, balanced, aggressive)

---

## Installation

### Via pip (recommended)
```bash
pip install codex-guardian
```

### From source
```bash
git clone https://github.com/JithendraNara/codex-guardian.git
cd codex-guardian
pip install -e .
```

### Verify
```bash
codex-guardian --version
```

---

## Quick Start

### 1. Configure alerts (Telegram example)
```bash
codex-guardian config --set notification_channels.telegram.enabled=true
codex-guardian config --set notification_channels.telegram.bot_token=YOUR_BOT_TOKEN
codex-guardian config --set notification_channels.telegram.chat_id=YOUR_CHAT_ID
```

### 2. Start monitoring
```bash
codex-guardian monitor
```

### 3. Check status
```bash
codex-guardian status
codex-guardian alerts --limit 20
```

### 4. Dry-run mode (test without alerts)
```bash
codex-guardian monitor --dry-run
```

---

## Configuration

Config file: `~/.codex-guardian/config.json`

### Key settings

```json
{
  "alert_thresholds": {
    "health_score_critical": 40,
    "health_score_warning": 60,
    "token_burn_rate_warning": 1000,
    "token_burn_rate_critical": 5000,
    "runaway_detection_enabled": true,
    "budget_warning_percentages": [50, 75, 90, 100]
  },
  "budget_limits": {
    "monthly_token_limit": 100000,
    "session_token_limit": 10000
  },
  "monitoring": {
    "check_interval_seconds": 30
  }
}
```

### Presets

```bash
# Conservative — catches problems faster (more false positives)
codex-guardian thresholds --preset conservative

# Balanced — default, recommended for most users
codex-guardian thresholds --preset balanced

# Aggressive — only triggers on severe issues
codex-guardian thresholds --preset aggressive
```

### Environment variables

| Variable | Description |
|----------|-------------|
| `CODEX_GUARDIAN_CONFIG` | Custom config file path |
| `CODEX_SESSIONS_DIR` | Override Codex sessions directory |
| `CODEX_GUARDIAN_DRY_RUN` | Set to `1` for dry-run mode |

---

## CLI Reference

```
codex-guardian [command]

Commands:
  monitor        Start real-time monitoring daemon
  status         Show active sessions and health
  alerts         Show alert history
  config         Edit configuration
  thresholds     Manage detection thresholds

Examples:
  codex-guardian monitor              # Start monitoring
  codex-guardian monitor --dry-run    # Test mode (no alerts sent)
  codex-guardian status               # Check session health
  codex-guardian alerts -n 50         # Show last 50 alerts
  codex-guardian config --get alert_thresholds.health_score_critical
  codex-guardian thresholds --preset conservative
```

---

## Architecture

```
codex_guardian/
├── __init__.py           # Package init
├── cli.py                # Command-line interface
├── detector.py           # Health score + detection engine
├── log_parser.py         # JSONL session log parser
├── alerter.py            # Multi-channel alert dispatcher
├── thresholds.py         # Detection threshold configs + presets
└── config.py             # Configuration management
```

**Key components:**

- **log_parser.py** — Reads raw `rollout-*.jsonl` files from `~/.codex/sessions/`, extracts tool calls, token counts, timestamps
- **detector.py** — Applies detection rules, calculates health score (0-100)
- **alerter.py** — Sends to Telegram/Discord/Slack, persists to SQLite
- **thresholds.py** — Preset system (conservative/balanced/aggressive) with full customization
- **config.py** — JSON config at `~/.codex-guardian/config.json`

---

## Cost Calculation

Codex CLI uses OpenAI's pricing. Guardian estimates costs using:

```
Cost = (input_tokens × $0.03/1K) + (output_tokens × $0.06/1K)
```

Default session limit: 10,000 tokens ≈ **$0.90/session**

Budget warnings trigger at: 50% ($0.45), 75% ($0.68), 90% ($0.81), 100% ($0.90)

---

## Safety

- **Auto-terminate requires confirmation by default** — set `auto_terminate_confirm=false` to disable
- **Dry-run mode** — test without sending any alerts
- **Local only** — no data leaves your machine unless webhooks are configured
- **Read-only access** — Guardian only reads log files, never modifies Codex sessions
- **SQLite storage** — all data stays local in `~/.codex-guardian/`

---

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## License

MIT License — free to use, modify, distribute.
