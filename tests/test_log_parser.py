"""Tests for the JSONL log parser."""
import json
import pytest
import tempfile
import os
from pathlib import Path

from codex_guardian.log_parser import (
    SessionMetadata,
    Event,
    ToolCall,
    find_sessions,
    parse_session,
    quick_parse,
    get_session_stats,
)


class TestSessionMetadata:
    """Tests for SessionMetadata."""

    def test_metadata_required_fields(self):
        """SessionMetadata requires session_id, path, date."""
        meta = SessionMetadata(
            session_id="test-123",
            path="/path/to/session",
            date="2026-03-25",
        )
        assert meta.session_id == "test-123"
        assert meta.path == "/path/to/session"
        assert meta.date == "2026-03-25"

    def test_metadata_optional_fields(self):
        """SessionMetadata has optional fields with defaults."""
        meta = SessionMetadata(
            session_id="test-456",
            path="/path",
            date="2026-03-25",
            model="claude-opus-4-6",
            status="complete",
        )
        assert meta.model == "claude-opus-4-6"
        assert meta.status == "complete"
        assert meta.input_tokens == 0


class TestToolCall:
    """Tests for ToolCall class."""

    def test_tool_call_required_fields(self):
        """ToolCall requires timestamp, name, arguments, call_id."""
        tc = ToolCall(
            timestamp="2026-03-25T10:00:00Z",
            name="Read",
            arguments={"file_path": "test.py"},
            call_id="call_abc123",
        )
        assert tc.name == "Read"
        assert tc.arguments["file_path"] == "test.py"


class TestEvent:
    """Tests for Event class."""

    def test_event_required_fields(self):
        """Event requires timestamp, event_type, data."""
        ev = Event(
            timestamp="2026-03-25T10:00:00Z",
            event_type="tool_call",
            data={"tool": "Read"},
        )
        assert ev.event_type == "tool_call"
        assert ev.data["tool"] == "Read"


class TestFindSessions:
    """Tests for session discovery."""

    def test_find_sessions_nonexistent_dir(self, tmp_path):
        """Returns empty list when directory does not exist."""
        sessions = find_sessions(tmp_path / "nonexistent")
        assert sessions == []

    def test_find_sessions_empty_dir(self, tmp_path):
        """Returns empty list for empty directory."""
        sessions = find_sessions(tmp_path)
        assert sessions == []


class TestQuickParse:
    """Tests for quick session parsing."""

    def test_quick_parse_nonexistent_file(self):
        """Returns dict with null fields for missing file."""
        result = quick_parse("/nonexistent/file.jsonl")
        # Returns a dict (possibly with null/None values) not an exception
        assert isinstance(result, dict)
        assert "session_id" in result

    def test_quick_parse_valid_file(self, tmp_path):
        """Parses a valid JSONL session file."""
        test_file = tmp_path / "rollout-test123.jsonl"
        test_file.write_text(
            json.dumps({
                "type": "session_meta",
                "timestamp": "2026-03-25T10:00:00Z",
                "payload": {"model": "claude-opus-4-6"}
            }) + "\n"
        )
        result = quick_parse(str(test_file))
        assert isinstance(result, dict)


class TestParseSession:
    """Tests for full session parsing."""

    def test_parse_session_nonexistent(self):
        """Raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            parse_session("/nonexistent/file.jsonl")

    def test_parse_session_invalid_jsonl(self, tmp_path):
        """Handles malformed JSONL gracefully."""
        test_file = tmp_path / "malformed.jsonl"
        test_file.write_text('''{"valid": "json"}
{"also": "valid"}
not json at all
''')
        meta, events, tools = parse_session(str(test_file))
        assert isinstance(meta, SessionMetadata)


class TestGetSessionStats:
    """Tests for session statistics."""

    def test_stats_empty_session(self):
        """Handles empty session data gracefully."""
        meta = SessionMetadata(
            session_id="empty-test",
            path="/test",
            date="2026-03-25",
        )
        result = get_session_stats((meta, [], []))
        assert result["session_id"] == "empty-test"
        assert result["event_counts"] == {}
        assert result["tool_calls"]["total"] == 0  # tool_calls nested
