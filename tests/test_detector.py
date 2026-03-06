"""
Unit tests for Codex Guardian Detection Engine.
"""

import unittest
from datetime import datetime, timedelta
from pathlib import Path

import sys
# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from detector import (
    Event,
    detect_infinite_loop,
    detect_token_spike,
    detect_stuck_session,
    detect_risky_pattern,
    calculate_health_score,
    analyze_session,
    normalize_path,
)
from thresholds import Thresholds, Preset


def create_event(
    minutes_ago: float,
    event_type: str = "tool_call",
    tool_name: str = "edit",
    file_path: str = None,
    command: str = None,
    tokens: int = None,
    status: str = None,
) -> Event:
    """Helper to create events with relative timestamps."""
    return Event(
        timestamp=datetime.now() - timedelta(minutes=minutes_ago),
        event_type=event_type,
        tool_name=tool_name,
        file_path=file_path,
        command=command,
        tokens=tokens,
        status=status,
    )


class TestDetectInfiniteLoop(unittest.TestCase):
    """Tests for infinite loop detection."""
    
    def test_no_loop_detected(self):
        """Normal usage should not trigger detection."""
        events = [
            create_event(10, tool_name="read", file_path="/src/main.py"),
            create_event(8, tool_name="edit", file_path="/src/utils.py"),
            create_event(5, tool_name="read", file_path="/src/config.py"),
        ]
        result = detect_infinite_loop(events)
        self.assertFalse(result.detected)
    
    def test_same_file_repeated(self):
        """Same file modified 3+ times should trigger detection."""
        now = datetime.now()
        events = [
            Event(timestamp=now - timedelta(minutes=2), event_type="tool_call", 
                  tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=1.5), event_type="tool_call",
                  tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=1), event_type="tool_call",
                  tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=0.5), event_type="tool_call",
                  tool_name="edit", file_path="/src/app.py"),
        ]
        result = detect_infinite_loop(events)
        self.assertTrue(result.detected)
        self.assertIn("app.py", result.details["repeating_files"])
    
    def test_same_tool_repeated(self):
        """Same tool called 5+ times should trigger detection."""
        events = [
            create_event(2, tool_name="read", file_path=f"/file{i}.py")
            for i in range(6)
        ]
        result = detect_infinite_loop(events)
        self.assertTrue(result.detected)
        self.assertIn("read", result.details["repeating_tools"])
    
    def test_outside_time_window(self):
        """Events outside time window should not count."""
        events = [
            create_event(10, tool_name="edit", file_path="/src/app.py"),
            create_event(9, tool_name="edit", file_path="/src/app.py"),
            create_event(8, tool_name="edit", file_path="/src/app.py"),
        ]
        result = detect_infinite_loop(events)
        self.assertFalse(result.detected)


class TestDetectTokenSpike(unittest.TestCase):
    """Tests for token spike detection."""
    
    def test_normal_token_usage(self):
        """Normal token consumption should not trigger."""
        now = datetime.now()
        events = [
            Event(timestamp=now - timedelta(minutes=10), tokens=1000),
            Event(timestamp=now, tokens=5000),  # 4000 tokens in 10 min = 400/min
        ]
        result = detect_token_spike(events)
        self.assertFalse(result.detected)
    
    def test_token_spike_detected(self):
        """High token consumption should trigger."""
        now = datetime.now()
        events = [
            Event(timestamp=now - timedelta(minutes=5), tokens=1000),
            Event(timestamp=now, tokens=35000),  # 34000 in 5 min = 6800/min
        ]
        result = detect_token_spike(events)
        self.assertTrue(result.detected)
        self.assertGreater(result.details["tokens_per_minute"], 5000)
    
    def test_sustained_spike(self):
        """Sustained high token usage should trigger."""
        thresholds = Thresholds.from_preset(Preset.BALANCED)
        now = datetime.now()
        
        # Build events showing sustained high usage
        events = []
        for i in range(10):
            events.append(Event(
                timestamp=now - timedelta(minutes=10-i),
                tokens=1000 + (i * 6000)  # 6000 tokens per minute
            ))
        
        result = detect_token_spike(events, thresholds=thresholds)
        self.assertTrue(result.detected)
    
    def test_insufficient_data(self):
        """Not enough token data should return low severity."""
        events = [
            create_event(0, tokens=1000),
        ]
        result = detect_token_spike(events)
        self.assertFalse(result.detected)
        self.assertEqual(result.severity, "low")


class TestDetectStuckSession(unittest.TestCase):
    """Tests for stuck session detection."""
    
    def test_active_session(self):
        """Active session should not be stuck."""
        events = [
            create_event(1, tool_name="read"),
            create_event(0.5, tool_name="edit"),
        ]
        result = detect_stuck_session(events)
        self.assertFalse(result.detected)
    
    def test_stuck_with_no_tool_calls(self):
        """Session with no tool calls should be flagged."""
        events = [
            create_event(10, event_type="status_change", status="Working..."),
        ]
        result = detect_stuck_session(events)
        self.assertTrue(result.detected)
        self.assertIn("No tool calls", result.message)
    
    def test_stuck_session_detected(self):
        """Session without progress for 5+ minutes should be stuck."""
        now = datetime.now()
        events = [
            Event(timestamp=now - timedelta(minutes=10), 
                  event_type="tool_call", tool_name="edit", file_path="/test.py"),
            Event(timestamp=now - timedelta(minutes=9),
                  event_type="status_change", status="Working..."),
            Event(timestamp=now - timedelta(minutes=1),
                  event_type="status_change", status="Working..."),
        ]
        result = detect_stuck_session(events)
        self.assertTrue(result.detected)
        self.assertGreater(result.details["minutes_since_last_tool"], 5)
    
    def test_not_stuck_without_working_status(self):
        """Session not in Working status should not be stuck."""
        events = [
            create_event(10, tool_name="read"),
            create_event(0, event_type="status_change", status="Idle"),
        ]
        result = detect_stuck_session(events)
        self.assertFalse(result.detected)


class TestDetectRiskyPattern(unittest.TestCase):
    """Tests for risky pattern detection."""
    
    def test_no_risky_patterns(self):
        """Normal operations should not trigger."""
        events = [
            create_event(5, tool_name="read", file_path="/src/main.py"),
            create_event(3, tool_name="edit", file_path="/src/utils.py"),
            create_event(1, tool_name="create", file_path="/src/new.py"),
        ]
        result = detect_risky_pattern(events)
        self.assertFalse(result.detected)
    
    def test_dangerous_command_detected(self):
        """Dangerous commands should trigger."""
        events = [
            create_event(5, command="rm -rf /tmp/*"),
            create_event(3, tool_name="edit", file_path="/src/main.py"),
        ]
        result = detect_risky_pattern(events)
        self.assertTrue(result.detected)
        self.assertEqual(result.severity, "critical")
    
    def test_mass_file_operations(self):
        """Mass file operations should trigger."""
        events = [
            create_event(i * 0.1, event_type="file_delete", file_path=f"/tmp/file{i}.txt")
            for i in range(15)
        ]
        result = detect_risky_pattern(events)
        self.assertTrue(result.detected)
        self.assertIn("mass_operations", result.details)
    
    def test_recursive_operations(self):
        """Recursive operations should be detected."""
        events = [
            create_event(5, command="chmod -R 777 /home"),
            create_event(3, command="find / -name '*.log'"),
            create_event(1, command="grep -r 'pattern' /src"),
        ]
        result = detect_risky_pattern(events)
        self.assertTrue(result.detected)
        self.assertGreater(len(result.details["recursive_operations"]), 0)


class TestHealthScore(unittest.TestCase):
    """Tests for health score calculation."""
    
    def test_healthy_session(self):
        """Healthy session should score high."""
        events = [
            create_event(10, tool_name="read", file_path="/src/main.py"),
            create_event(8, tool_name="edit", file_path="/src/utils.py"),
            create_event(5, tool_name="read", file_path="/src/config.py"),
            create_event(2, tool_name="edit", file_path="/src/main.py", tokens=5000),
        ]
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        self.assertGreaterEqual(health.score, 70)
    
    def test_unhealthy_session(self):
        """Problematic session should score low."""
        now = datetime.now()
        events = [
            Event(timestamp=now - timedelta(minutes=5),
                  event_type="tool_call", tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=4),
                  event_type="tool_call", tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=3),
                  event_type="tool_call", tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=2),
                  event_type="tool_call", tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now - timedelta(minutes=1),
                  event_type="tool_call", tool_name="edit", file_path="/src/app.py"),
            Event(timestamp=now, tokens=50000, status="Working..."),
        ]
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        self.assertLess(health.score, 50)
    
    def test_recommendations_generated(self):
        """Recommendations should be generated based on issues."""
        events = [
            create_event(10, command="rm -rf /"),
        ]
        session_data = {"events": events}
        health = calculate_health_score(session_data)
        self.assertIsInstance(health.recommendations, list)
        self.assertGreater(len(health.recommendations), 0)


class TestAnalyzeSession(unittest.TestCase):
    """Tests for comprehensive session analysis."""
    
    def test_comprehensive_analysis(self):
        """Should return all detection results."""
        events = [
            create_event(5, tool_name="read"),
            create_event(2, tool_name="edit"),
        ]
        result = analyze_session(events)
        
        self.assertIn("healthy", result)
        self.assertIn("health_score", result)
        self.assertIn("detections", result)
        self.assertIn("recommendations", result)
        
        # Check all detection types present
        detections = result["detections"]
        self.assertIn("infinite_loop", detections)
        self.assertIn("token_spike", detections)
        self.assertIn("stuck_session", detections)
        self.assertIn("risky_pattern", detections)


class TestThresholds(unittest.TestCase):
    """Tests for threshold configuration."""
    
    def test_preset_conservative(self):
        """Conservative preset should have stricter thresholds."""
        thresholds = Thresholds.from_preset(Preset.CONSERVATIVE)
        self.assertEqual(thresholds.same_file_modifications, 2)
        self.assertEqual(thresholds.token_spike_threshold, 3000)
    
    def test_preset_balanced(self):
        """Balanced preset should have default thresholds."""
        thresholds = Thresholds.from_preset(Preset.BALANCED)
        self.assertEqual(thresholds.same_file_modifications, 3)
        self.assertEqual(thresholds.token_spike_threshold, 5000)
    
    def test_preset_aggressive(self):
        """Aggressive preset should have lenient thresholds."""
        thresholds = Thresholds.from_preset(Preset.AGGRESSIVE)
        self.assertEqual(thresholds.same_file_modifications, 5)
        self.assertEqual(thresholds.token_spike_threshold, 10000)
    
    def test_threshold_save_load(self,):
        """Thresholds should save and load correctly."""
        import tempfile
        import os
        
        thresholds = Thresholds.from_preset(Preset.BALANCED)
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            thresholds.save(Path(temp_path))
            loaded = Thresholds.load(Path(temp_path))
            
            self.assertEqual(loaded.same_file_modifications, 
                           thresholds.same_file_modifications)
            self.assertEqual(loaded.token_spike_threshold,
                           thresholds.token_spike_threshold)
        finally:
            os.unlink(temp_path)


class TestEdgeCases(unittest.TestCase):
    """Edge case handling tests."""
    
    def test_empty_events(self):
        """Empty events should handle gracefully."""
        result = detect_infinite_loop([])
        self.assertFalse(result.detected)
        
        result = detect_token_spike([])
        self.assertFalse(result.detected)
        
        result = detect_stuck_session([])
        self.assertFalse(result.detected)
        
        result = detect_risky_pattern([])
        self.assertFalse(result.detected)
    
    def test_none_values(self):
        """None values should be handled."""
        events = [create_event(5, file_path=None, tool_name=None)]
        result = detect_infinite_loop(events)
        self.assertFalse(result.detected)
    
    def test_path_normalization(self):
        """Paths should be normalized for comparison."""
        from detector import normalize_path
        
        self.assertEqual(
            normalize_path("/home/user/project/src/main.py"),
            normalize_path("~/project/src/main.py")
        )
        self.assertEqual(
            normalize_path("/src/app.py"),
            normalize_path("/src/app.py")
        )


if __name__ == "__main__":
    unittest.main()
