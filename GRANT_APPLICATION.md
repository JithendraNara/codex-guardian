# Codex Guardian - OpenAI Codex Open Source Fund Application

---

## Project Information

**Project Name:** Codex Guardian  
**GitHub Repository:** https://github.com/JithendraNara/codex-guardian  
**Applicant:** Jithendra Nara  
**Contact:** [Your Email]  
**Date:** March 6, 2026

---

## Project Summary (2-3 sentences)

Codex Guardian is a real-time monitoring and protection tool for OpenAI Codex CLI that prevents runaway token burn from infinite loops, stuck sessions, and risky operations. It provides instant alerts via Telegram/Discord/Slack and auto-terminates dangerous sessions before users lose significant money.

---

## Problem Statement

Codex CLI users face a critical problem: **runaway sessions can burn hundreds of dollars in tokens before users notice**. Common failure modes include:

1. **Infinite loops** - Repeated tool calls or file edits with no progress
2. **Stuck sessions** - "Working..." state for hours with no output
3. **Token spikes** - Sudden bursts of 10,000+ tokens/minute
4. **Risky operations** - Mass file deletions, recursive commands without confirmation

The Codex CLI has **no built-in budget alerts, spending limits, or runaway detection**. Users only discover problems when they receive their bill or manually check usage.

Community evidence:
- GitHub issues #7179-7182: "Codex CLI hangs indefinitely"
- Reddit r/codex: "Token burn rate massively increased", "Codex cli is disappointing"
- OpenAI Community: "Usage limits... primarily because of Codex CLI missteps"

---

## Solution

Codex Guardian provides **proactive session protection**:

### Core Features

| Feature | Description |
|---------|-------------|
| **Real-time Monitoring** | Watches all active Codex CLI sessions live |
| **Runaway Detection** | Catches infinite loops, token spikes, stuck states |
| **Budget Alerts** | Notifications at 50%, 75%, 90%, 100% of budget |
| **Auto-terminate** | Kills sessions exceeding safety thresholds |
| **Health Scoring** | 0-100 session health score with risk assessment |
| **Multi-channel Alerts** | Telegram, Discord, Slack, local log |

### How It Works

1. **Log Parsing** - Reads `~/.codex/sessions/*/rollout-*.jsonl` files in real-time
2. **Event Extraction** - Parses tool calls, token usage, exec commands, thinking blocks
3. **Pattern Detection** - Runs detection algorithms on live event streams
4. **Alerting** - Sends notifications when thresholds exceeded
5. **Protection** - Auto-terminates sessions that exceed safety limits

---

## Why Codex CLI Is Integral

Codex Guardian is **built specifically for Codex CLI** and cannot function without it:

- **Log Format** - Parses Codex-specific JSONL session format (`rollout-*.jsonl`)
- **Session Structure** - Understands Codex session lifecycle (start, tool calls, completion)
- **Token Accounting** - Uses Codex token counting methodology (input, output, reasoning, cache)
- **CLI Integration** - Extends Codex CLI with `codex-guardian` commands
- **Config Location** - Stores config at `~/.codex-guardian/` alongside Codex

This is **not a generic AI monitoring tool** - it's purpose-built for the Codex ecosystem.

---

## Ecosystem Impact

### Who Benefits

1. **Individual Developers** - Protect personal budgets from accidental burn
2. **Teams Using Codex** - Enforce spending limits across team members
3. **Open Source Projects** - Safe CI/CD integration with Codex
4. **Codex Itself** - Reduces negative user experiences from bill shock

### Measurable Impact

- **Prevents financial loss** - Users protected from $100-500+ runaway sessions
- **Improves Codex adoption** - Makes Codex safer for production use
- **Reduces support burden** - Fewer "my bill is huge" complaints to OpenAI
- **Educational value** - Teaches users about token usage patterns

### Target Users

- Codex CLI users (estimated 10,000+ based on GitHub stars + community activity)
- Teams running Codex in CI/CD pipelines
- Developers on Pro/Plus plans with usage limits
- Open source projects using Codex for automation

---

## Technical Architecture

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

### Components

1. **Log Parser** (`src/log_parser.py`)
   - Finds and parses Codex session JSONL files
   - Extracts events: tool calls, tokens, timestamps, model info
   - Builds SQLite index for fast querying

2. **Detection Engine** (`src/detector.py`)
   - Infinite loop detection (repeated operations)
   - Token spike detection (>5000 tokens/min)
   - Stuck session detection (no progress for 5+ min)
   - Risky pattern flags (mass deletes, recursive ops)
   - Health score calculation (0-100)

3. **Alert System** (`src/alerter.py`)
   - Telegram bot integration
   - Discord webhook support
   - Slack webhook support
   - Local alert history (SQLite)

4. **CLI** (`src/cli.py`)
   - `codex-guardian monitor` - Start monitoring daemon
   - `codex-guardian status` - Show active sessions
   - `codex-guardian alerts` - View alert history
   - `codex-guardian config` - Configuration editor

---

## Implementation Plan

### Phase 1: Core Infrastructure (Week 1)
- [x] Project setup and structure
- [ ] Log parser with JSONL reader
- [ ] Session index (SQLite)
- [ ] Basic detection algorithms

### Phase 2: Detection & Alerts (Week 2)
- [ ] Runaway detection engine
- [ ] Health score calculator
- [ ] Telegram/Discord/Slack integrations
- [ ] Alert history and configuration

### Phase 3: Polish & Launch (Week 3)
- [ ] CLI interface polish
- [ ] Documentation and examples
- [ ] Test suite and CI/CD
- [ ] GitHub release and grant application

**Current Status:** Phase 1 in progress (subagents building core components)

---

## Funding Request

**Amount:** $10,000 in API credits  
**Justification:**

1. **Development & Testing** - Extensive testing with real Codex sessions requires API usage
2. **CI/CD Integration** - Automated testing on every commit
3. **Community Support** - Dogfooding Codex Guardian to protect our own development
4. **Feature Expansion** - Adding support for Codex Cloud and IDE extension sessions

**How Credits Will Be Used:**
- 40% - Development and testing (building detection algorithms)
- 30% - CI/CD pipelines (automated testing on PRs)
- 20% - Community support (helping users integrate)
- 10% - Buffer for unexpected needs

---

## Sustainability Plan

### Post-Funding Maintenance

1. **Active Development** - Ongoing feature improvements based on user feedback
2. **Community Contributions** - Welcome PRs for new alert channels, detection rules
3. **Documentation** - Maintain comprehensive docs and examples
4. **Support** - GitHub Issues response within 48 hours

### Long-Term Viability

- **Open Source License** - MIT (permissive, encourages adoption)
- **Low Maintenance** - Once stable, requires minimal upkeep
- **Clear Value** - Solves real pain point, users will advocate for it
- **Extensible** - Easy to add new features (new alert channels, detection rules)

---

## About the Author

**Jithendra Nara** - Software Engineer, OpenClaw power user, and AI automation enthusiast.

**Relevant Experience:**
- Built and maintain multiple AI-powered tools (RAG system, auto-issue-fixer, IT dashboard)
- Deep experience with AI agent orchestration and monitoring
- Active contributor to AI/ML open source ecosystem
- Personal motivation: Lost money to runaway Codex sessions, built solution to prevent recurrence

**Why Me:**
I use Codex CLI daily for building AI automation tools. I've experienced the pain of runaway sessions firsthand and have the technical skills to build a robust solution. This isn't a theoretical project - I'm building the tool I need, which means I'll maintain it long-term.

---

## Links

- **GitHub Repository:** https://github.com/JithendraNara/codex-guardian
- **Codex CLI:** https://github.com/openai/codex
- **OpenAI Codex Fund:** https://openai.com/form/codex-open-source-fund

---

## Appendix: Detection Rules

### Infinite Loop Detection
- Same file modified 3+ times in 2 minutes
- Same tool call repeated 5+ times
- Circular file edits (A→B→C→A pattern)

### Token Spike Detection
- >5,000 tokens/minute sustained for 2+ minutes
- >10,000 tokens in single tool call
- Exponential growth pattern in token usage

### Stuck Session Detection
- No tool call progress for 5+ minutes
- "Working..." state with no output
- Repeated failed exec commands

### Risky Pattern Detection
- `rm -rf` or mass delete operations
- Recursive operations without confirmation
- Network calls to unknown endpoints
- Large file generation (>10MB)

---

*This application is submitted as part of the OpenAI Codex Open Source Fund, a $1 million initiative supporting open source projects that use Codex CLI and OpenAI models.*
