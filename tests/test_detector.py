"""Tests for the detection engine."""
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path

from codex_guardian.detector import (
    Event,
    detect_infinite_loop,
    detect_token_spike,
    detect_stuck_session,
    detect_risky_pattern,
    calculate_health_score,
    analyze_session,
    estimate_session_cost,
    format_cost_alert,
    Thresholds,
    Preset,
)


def load_events(fixture_name: str) -> list[Event]:
    """Load events from a fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / f"{fixture_name}.jsonl"
    events = []
    with open(fixture_path) as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                events.append(Event.from_dict(data))
    return events


class TestEvent:
    """Tests for Event dataclass."""

    def test_from_dict_basic(self):
        data = {
            "timestamp": "2026-03-25T10:00:00Z",
            "event_type": "tool_call",
            "tool_name": "Read",
            "file_path": "src/main.py",
            "tokens": 1200,
        }
        event = Event.from_dict(data)
        assert event.tool_name == "Read"
        assert event.file_path == "src/main.py"
        assert event.tokens == 1200
        assert event.event_type == "tool_call"

    def test_from_dict_iso_timestamp(self):
        data = {
            "timestamp": "2026-03-25T10:00:00+00:00",
            "event_type": "tool_call",
            "tokens": 100,
        }
        event = Event.from_dict(data)
        assert isinstance(event.timestamp, datetime)

    def test_to_dict_roundtrip(self):
        data = {
            "timestamp": "2026-03-25T10:00:00Z",
            "event_type": "tool_call",
            "tool_name": "Write",
            "file_path": "test.py",
            "tokens": 500,
        }
        event = Event.from_dict(data)
        roundtrip = event.to_dict()
        assert roundtrip["tool_name"] == "Write"
        assert roundtrip["tokens"] == 500


class TestInfiniteLoopDetection:
    """Tests for infinite loop detection."""

    def test_normal_session_no_detection(self):
        events = load_events("normal_session")
        result = detect_infinite_loop(events)
        assert result.detected is False

    def test_infinite_loop_detected(self):
        events = load_events("infinite_loop_session")
        result = detect_infinite_loop(events)
        assert result.detected is True
        assert result.severity in ("medium", "high", "critical")
        assert "infinite loop" in result.message.lower()

    def test_empty_events_no_detection(self):
        result = detect_infinite_loop([])
        assert result.detected is False

    def test_custom_thresholds(self):
        thresholds = Thresholds(same_file_modifications=2)
        events = load_events("infinite_loop_session")
        result = detect_infinite_loop(events, thresholds)
        assert result.detected is True


class TestTokenSpikeDetection:
    """Tests for token spike detection."""

    def test_normal_session_no_spike(self):
        events = load_events("normal_session")
        result = detect_token_spike(events)
        assert result.detected is False

    def test_token_spike_detected(self):
        events = load_events("token_spike_session")
        result = detect_token_spike(events)
        assert result.detected is True
        assert result.severity in ("medium", "high", "critical")
        assert "token" in result.message.lower()

    def test_insufficient_data_no_detection(self):
        events = [
            Event(datetime.now(), "tool_call", tokens=1000),
        ]
        result = detect_token_spike(events)
        assert result.detected is False


class TestStuckSessionDetection:
    """Tests for stuck session detection."""

    def test_normal_session_not_stuck(self):
        events = load_events("normal_session")
        result = detect_stuck_session(events)
        assert result.detected is False

    def test_stuck_session_detected(self):
        events = load_events("stuck_session")
        result = detect_stuck_session(events)
        assert result.detected is True
        assert result.severity in ("medium", "high", "critical")
        assert "stuck" in result.message.lower() or "progress" in result.message.lower()

    def test_no_tool_calls(self):
        events = [
            Event(datetime.now(), "status_change", status="Working..."),
        ]
        result = detect_stuck_session(events)
        assert result.detected is True
        assert result.severity == "medium"


class TestRiskyPatternDetection:
    """Tests for risky pattern detection."""

    def test_normal_session_no_risky(self):
        events = load_events("normal_session")
        result = detect_risky_pattern(events)
        assert result.detected is False

    def test_risky_commands_detected(self):
        events = load_events("risky_command_session")
        result = detect_risky_pattern(events)
        assert result.detected is True
        assert result.severity in ("medium", "high", "critical")
        assert "risky" in result.message.lower() or "dangerous" in result.message.lower()

    def test_risky_commands_details(self):
        events = load_events("risky_command_session")
        result = detect_risky_pattern(events)
        assert len(result.details["dangerous_commands"]) > 0


class TestHealthScore:
    """Tests for health score calculation."""

    def test_normal_session_healthy(self):
        events = load_events("normal_session")
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        assert health.score >= 70
        assert "healthy" not in [r.lower() for r in health.recommendations
                                 if "healthy" in r.lower()] or len(health.recommendations) > 0

    def test_unhealthy_session_low_score(self):
        events = load_events("infinite_loop_session")
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        assert health.score < 70

    def test_health_score_factors_present(self):
        events = load_events("normal_session")
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        assert "infinite_loop" in health.factors
        assert "token_spike" in health.factors
        assert "stuck_session" in health.factors
        assert "risky_pattern" in health.factors

    def test_empty_events_graceful(self):
        session_data = {"events": []}
        health = calculate_health_score(session_data)
        assert health.score >= 0
        assert health.score <= 100


class TestAnalyzeSession:
    """Tests for the full session analysis."""

    def test_normal_session_healthy(self):
        events = load_events("normal_session")
        result = analyze_session(events)
        assert result["healthy"] is True
        assert "health_score" in result
        assert 0 <= result["health_score"] <= 100

    def test_infinite_loop_session_unhealthy(self):
        events = load_events("infinite_loop_session")
        result = analyze_session(events)
        assert result["healthy"] is False
        assert result["detections"]["infinite_loop"]["detected"] is True

    def test_all_detection_fields_present(self):
        events = load_events("normal_session")
        result = analyze_session(events)
        assert "infinite_loop" in result["detections"]
        assert "token_spike" in result["detections"]
        assert "stuck_session" in result["detections"]
        assert "risky_pattern" in result["detections"]


class TestThresholdsPresets:
    """Tests for threshold presets."""

    def test_conservative_preset(self):
        t = Thresholds.from_preset(Preset.CONSERVATIVE)
        assert t.same_file_modifications == 2
        assert t.same_tool_calls == 4
        assert t.token_spike_threshold == 3000

    def test_balanced_preset(self):
        t = Thresholds.from_preset(Preset.BALANCED)
        assert t.same_file_modifications == 3
        assert t.token_spike_threshold == 5000

    def test_aggressive_preset(self):
        t = Thresholds.from_preset(Preset.AGGRESSIVE)
        assert t.same_file_modifications == 5
        assert t.token_spike_threshold == 10000

    def test_threshold_serialization(self):
        t = Thresholds.from_preset(Preset.BALANCED)
        d = t.to_dict()
        restored = Thresholds.from_dict(d)
        assert restored.same_file_modifications == t.same_file_modifications
        assert restored.token_spike_threshold == t.token_spike_threshold


class TestCostEstimation:
    """Tests for cost estimation."""

    def test_estimate_normal_session_cost(self):
        events = load_events("normal_session")
        cost = estimate_session_cost(events)
        assert "cost_to_date" in cost
        assert "tokens_to_date" in cost
        assert "projected_hourly_cost" in cost
        assert cost["tokens_to_date"] > 0
        assert cost["cost_to_date"] > 0

    def test_estimate_empty_session(self):
        cost = estimate_session_cost([])
        assert cost["cost_to_date"] == 0.0
        assert cost["tokens_to_date"] == 0

    def test_format_cost_alert(self):
        cost_data = {
            "cost_to_date": 0.15,
            "tokens_to_date": 3100,
            "burn_rate_tokens_per_min": 62,
            "projected_hourly_cost": 0.93,
            "budget_remaining": 6900,
        }
        msg = format_cost_alert(cost_data, "abc12345")
        assert "0.1500" in msg or "0.15" in msg
        assert "3,100" in msg  # formatted with comma
        assert "abc123" in msg
