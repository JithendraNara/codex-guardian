# Contributing to Codex Guardian

Thank you for your interest in contributing!

## Development Setup

```bash
# Clone the repo
git clone https://github.com/JithendraNara/codex-guardian.git
cd codex-guardian

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in development mode
pip install -e ".[dev]"

# Verify
codex-guardian --version
```

## Project Structure

```
codex_guardian/
├── cli.py           # CLI entry points — DO NOT add business logic here
├── detector.py      # Detection engine + health score
├── log_parser.py    # Codex JSONL parsing
├── alerter.py       # Alert dispatch + SQLite persistence
├── thresholds.py    # Threshold configs + presets
└── config.py        # Configuration management
```

**Rule:** Each module does one thing. CLI dispatches to modules. Modules never import CLI.

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=codex_guardian --cov-report=term-missing

# Run specific test file
pytest tests/test_detector.py -v
```

### Writing Tests

- Tests go in `tests/` — mirror the source structure
- Use `pytest` + `pytest-mock`
- Mock Codex JSONL fixtures — do not require a real Codex installation
- Aim for 80%+ coverage on detection logic

### Test Fixtures

JSONL fixtures are in `tests/fixtures/` — create realistic session logs for:
- Normal session
- Infinite loop (same file modified 5x)
- Token spike (burst of 8000 tokens)
- Stuck session (no activity for 10 min)
- Risky command (rm -rf in tool call)

## Pull Request Process

### 1. Branch naming
```
feature/detection-improvement
fix/token-spike-false-positive
docs/readme-upgrade
```

### 2. Before opening a PR

- [ ] `pytest` passes locally
- [ ] New tests added for new behavior
- [ ] `CHANGELOG.md` updated under `[Unreleased]`
- [ ] No lint errors (`flake8 .`)

### 3. PR description template

```markdown
## What

Brief description of the change.

## Why

What problem does this solve?

## How

Key implementation decisions.

## Testing

How was this tested?
```

### 4. Code standards

- **Python 3.10+** — use type hints, no `from __future__` imports
- **Black** for formatting — `black .`
- **isort** for imports — `isort .`
- **flake8** for linting — `flake8 .`
- Docstrings for all public functions (Google style)
- No magic numbers — extract to constants with names

### 5. Review process

- Reviews typically within 48 hours
- Address feedback by pushing additional commits (don't force push during review)
- One approval required to merge
- Squash and merge preferred

## Bug Reports

Use GitHub Issues. Include:
- Python version
- Codex Guardian version (`codex-guardian --version`)
- Codex CLI version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log snippets (anonymize session IDs)

## Feature Requests

Open a GitHub Issue with:
- Clear use case — what problem does it solve?
- Why is it important?
- Any implementation suggestions?

## Code of Conduct

Be respectful. Disagreements are fine; personal attacks are not.
