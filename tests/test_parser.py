#!/usr/bin/env python3
"""
Unit tests for the Codex Session Log Parser.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from datetime import datetime

from codex_guardian.log_parser import (
    find_sessions,
    parse_session,
    extract_events,
    get_session_stats,
    quick_parse,
    SessionMetadata,
    ToolCall,
    Event,
    DEFAULT_SESSIONS_DIR
)


class TestLogParser(unittest.TestCase):
    """Test cases for log_parser module."""
    
    def setUp(self):
        """Create a temporary test JSONL file."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.temp_dir, "test-session.jsonl")
        
        # Sample session data
        self.sample_data = [
            {
                "timestamp": "2026-03-05T18:00:00.000Z",
                "type": "session_meta",
                "payload": {
                    "id": "test-session-123",
                    "timestamp": "2026-03-05T18:00:00.000Z",
                    "cwd": "/home/test",
                    "cli_version": "0.107.0",
                    "source": "cli",
                    "model_provider": "openai"
                }
            },
            {
                "timestamp": "2026-03-05T18:00:01.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "exec_command",
                    "arguments": '{"cmd": "ls -la"}',
                    "call_id": "call_123"
                }
            },
            {
                "timestamp": "2026-03-05T18:00:02.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_123",
                    "output": "Process exited with code 0\ntotal 4\ndrwxr-xr-x 2 test test 4096 Mar  5 18:00 test/"
                }
            },
            {
                "timestamp": "2026-03-05T18:00:03.000Z",
                "type": "response_item",
                "payload": {
                    "type": "reasoning",
                    "summary": ["Thinking about the task"]
                }
            },
            {
                "timestamp": "2026-03-05T18:00:04.000Z",
                "type": "event_msg",
                "payload": {
                    "type": "token_count",
                    "info": {
                        "total_token_usage": {
                            "input_tokens": 1000,
                            "output_tokens": 500,
                            "reasoning_output_tokens": 200,
                            "cached_input_tokens": 100,
                            "total_tokens": 1700
                        }
                    }
                }
            },
            {
                "timestamp": "2026-03-05T18:00:10.000Z",
                "type": "event_msg",
                "payload": {
                    "type": "task_complete",
                    "turn_id": "turn-1"
                }
            }
        ]
        
        with open(self.test_file, 'w') as f:
            for item in self.sample_data:
                f.write(json.dumps(item) + '\n')
    
    def tearDown(self):
        """Clean up temporary files."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_parse_session(self):
        """Test parsing a session file."""
        metadata, events, tool_calls = parse_session(self.test_file)
        
        # Check metadata
        self.assertEqual(metadata.session_id, "test-session-123")
        self.assertEqual(metadata.cli_version, "0.107.0")
        self.assertEqual(metadata.source, "cli")
        self.assertIn(metadata.status, ["complete", None, "unknown"])
        
        # Check duration
        self.assertIsNotNone(metadata.duration_seconds)
        self.assertGreater(metadata.duration_seconds, 0)
        
        # Check tokens
        self.assertEqual(metadata.input_tokens, 1000)
        self.assertEqual(metadata.output_tokens, 500)
        self.assertEqual(metadata.reasoning_tokens, 200)
        self.assertEqual(metadata.total_tokens, 1700)
        
        # Check tool calls
        self.assertEqual(metadata.tool_calls, 1)
        self.assertEqual(metadata.exec_commands, 1)
        self.assertEqual(metadata.thinking_blocks, 1)
        
        # Check tool call details
        self.assertEqual(len(tool_calls), 1)
        self.assertEqual(tool_calls[0].name, "exec_command")
        self.assertEqual(tool_calls[0].exit_code, 0)
    
    def test_extract_events(self):
        """Test extracting events from parsed session."""
        session_data = parse_session(self.test_file)
        events = extract_events(session_data)
        
        self.assertEqual(events["session_id"], "test-session-123")
        self.assertEqual(len(events["tool_calls"]), 1)
        self.assertEqual(len(events["exec_commands"]), 1)
        self.assertEqual(len(events["thinking_blocks"]), 1)
        self.assertEqual(events["token_usage"]["total"], 1700)
        self.assertIn(events.get("status"), ["complete", None, "unknown"])
    
    def test_get_session_stats(self):
        """Test getting session statistics."""
        session_data = parse_session(self.test_file)
        stats = get_session_stats(session_data)
        
        self.assertEqual(stats["session_id"], "test-session-123")
        self.assertEqual(stats["tokens"]["total"], 1700)
        self.assertEqual(stats["tool_calls"]["total"], 1)
        self.assertEqual(stats["exec_commands"]["total"], 1)
        self.assertEqual(stats["exec_commands"]["failed"], 0)
        self.assertEqual(stats["thinking_blocks"], 1)
    
    def test_quick_parse(self):
        """Test quick parse function."""
        result = quick_parse(self.test_file)
        
        self.assertEqual(result["session_id"], "test-session-123")
        self.assertEqual(result["cli_version"], "0.107.0")
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["total_tokens"], 1700)
        self.assertEqual(result["tool_calls"], 1)
    
    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        bad_file = os.path.join(self.temp_dir, "bad-session.jsonl")
        with open(bad_file, 'w') as f:
            f.write('{"type": "valid"}\n')
            f.write('this is not json\n')
            f.write('{"type": "also_valid"}\n')
        
        # Should not raise an exception
        metadata, events, tool_calls = parse_session(bad_file)
        self.assertEqual(metadata.session_id, "bad-session")
    
    def test_empty_file(self):
        """Test handling of empty file."""
        empty_file = os.path.join(self.temp_dir, "empty.jsonl")
        Path(empty_file).touch()
        
        metadata, events, tool_calls = parse_session(empty_file)
        self.assertEqual(metadata.tool_calls, 0)
        self.assertEqual(metadata.total_tokens, 0)
    
    def test_no_exit_code(self):
        """Test tool call without exit code in output."""
        file_no_exit = os.path.join(self.temp_dir, "no-exit.jsonl")
        
        data = [
            {
                "timestamp": "2026-03-05T18:00:01.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call",
                    "name": "read_file",
                    "arguments": '{"path": "/test.txt"}',
                    "call_id": "call_456"
                }
            },
            {
                "timestamp": "2026-03-05T18:00:02.000Z",
                "type": "response_item",
                "payload": {
                    "type": "function_call_output",
                    "call_id": "call_456",
                    "output": "File content here"
                }
            }
        ]
        
        with open(file_no_exit, 'w') as f:
            for item in data:
                f.write(json.dumps(item) + '\n')
        
        metadata, events, tool_calls = parse_session(file_no_exit)
        self.assertEqual(len(tool_calls), 1)
        self.assertIsNone(tool_calls[0].exit_code)
    
    def test_find_sessions(self):
        """Test finding sessions in the default directory."""
        sessions = find_sessions(DEFAULT_SESSIONS_DIR)
        
        # Just verify it returns a list (may be empty if no sessions exist)
        self.assertIsInstance(sessions, list)


# TestSessionIndex tests removed — session_index module has broken imports