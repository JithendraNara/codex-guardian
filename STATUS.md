# Codex Guardian - Component 3 Status

## ✅ Completed

**Alert System & Notifications (Component 3)** - Built successfully.

### Deliverables Created

1. **`src/alerter.py`** / **`codex_guardian/alerter.py`**
   - `send_telegram_alert(message, chat_id, bot_token)` ✅
   - `send_discord_alert(message, webhook_url)` ✅
   - `send_slack_alert(message, webhook_url)` ✅
   - `log_alert(alert_data)` ✅
   - `get_alert_history(limit=50)` ✅

2. **`src/config.py`** / **`codex_guardian/config.py`**
   - Load/save config from `~/.codex-guardian/config.json` ✅
   - Alert thresholds, notification channels, budget limits ✅
   - Default config with sensible values ✅

3. **`src/cli.py`** / **`codex_guardian/cli.py`**
   - `codex-guardian monitor` - Start real-time monitoring daemon ✅
   - `codex-guardian status` - Show active sessions and health ✅
   - `codex-guardian alerts` - Show alert history ✅
   - `codex-guardian config` - Interactive config editor ✅

4. **`requirements.txt`** ✅

### Supported Notification Channels

- **Telegram** - Bot notifications via bot_token + chat_id
- **Discord** - Webhook notifications via webhook_url
- **Slack** - Webhook notifications via webhook_url

### Alert Triggers Implemented

- Session health score drops below 40 ✅
- Token burn rate exceeds threshold ✅
- Runaway detection fires ✅
- Budget limit reached (50%, 75%, 90%, 100%) ✅

---

## Setup Instructions

### 1. Install Dependencies

```bash
cd /home/jithendra/.openclaw/workspace/codex-guardian
pip install -r requirements.txt
```

### 2. Configure Notification Channels

Run interactive config editor:
```bash
python -m codex_guardian.cli config
```

Or manually edit `~/.codex-guardian/config.json`:

```json
{
  "notification_channels": {
    "telegram": {
      "enabled": true,
      "bot_token": "YOUR_TELEGRAM_BOT_TOKEN",
      "chat_id": "YOUR_CHAT_ID"
    },
    "discord": {
      "enabled": true,
      "webhook_url": "https://discord.com/api/webhooks/..."
    },
    "slack": {
      "enabled": true,
      "webhook_url": "https://hooks.slack.com/services/..."
    }
  }
}
```

### 3. Get Telegram Bot Token

1. Open Telegram and message @BotFather
2. Create new bot: `/newbot`
3. Get the bot token
4. Start a chat with your bot, then get chat ID:
   - Message `@userinfobot` to get your chat ID

### 4. Get Discord Webhook

1. Server Settings → Integrations → Webhooks
2. Create webhook, copy URL

### 5. Get Slack Webhook

1. Apps → Incoming Webhooks
2. Add new webhook, select channel, copy URL

### 6. Run Commands

```bash
# View current config
python -m codex_guardian.cli config --get alert_thresholds

# Check status
python -m codex_guardian.cli status

# View alerts
python -m codex_guardian.cli alerts

# Start monitoring (requires session tracking from Component 1-2)
python -m codex_guardian.cli monitor
```

---

## Testing Notifications

```python
from codex_guardian.alerter import send_alert
from codex_guardian.config import load_config

config = load_config()

# Send test alert
alert_data = {
    "alert_type": "test",
    "severity": "info",
    "message": "Test alert from Codex Guardian",
    "data": {"test": True}
}

result = send_alert(alert_data, config)
print(result)
```

---

## Config Location

All config and data stored in: `~/.codex-guardian/`
- `config.json` - Configuration
- `alerts.db` - Alert history (SQLite)
- `sessions.db` - Session tracking (SQLite)

---

**Component 3 Complete** 🦞
