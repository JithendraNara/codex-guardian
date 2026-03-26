# Changelog

All notable changes to Codex Guardian will be documented here.

## [0.2.0] — 2026-03-25

### Added
- **Dry-run mode** — test detection without sending alerts: `codex-guardian monitor --dry-run`
- **Cost projection** — estimates current session cost and projects end-of-session burn
- **Auto-terminate confirmation** — safety-first: sessions won't be killed without confirmation by default
- **Environment variable support** — `CODEX_GUARDIAN_DRY_RUN`, `CODEX_SESSIONS_DIR`, `CODEX_GUARDIAN_CONFIG`
- **GitHub Actions CI** — automated testing on every push
- **Comprehensive README** — architecture diagrams, quick start, CLI reference
- **CONTRIBUTING guide** — pull request process, coding standards, testing requirements

### Improved
- **Health score algorithm** — refined weighting to reduce false positives
- **Threshold presets** — clearer distinction between conservative/balanced/aggressive
- **Config validation** — catches misconfigured thresholds on startup
- **Error handling** — graceful degradation when Codex sessions dir is missing

## [0.1.0] — 2026-03-20

### Added
- Initial release
- Infinite loop detection (same-file modification tracking)
- Token spike monitoring
- Stuck session detection
- Risky command pattern detection
- Health score calculation (0-100)
- Telegram alert channel
- Discord webhook channel
- Slack webhook channel
- SQLite alert log
- Interactive CLI config editor
- Detection threshold presets (conservative, balanced, aggressive)
