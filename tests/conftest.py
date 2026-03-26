"""Pytest fixtures and helpers for Codex Guardian tests."""
import sys
from pathlib import Path

# Ensure src/ is on path so 'from codex_guardian import ...' works
_repo_root = Path(__file__).parent.parent
_src = _repo_root / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
