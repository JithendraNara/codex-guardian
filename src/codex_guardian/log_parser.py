#!/usr/bin/env python3
"""
Codex Session Log Parser

Parses Codex CLI session logs (JSONL format) and extracts structured data.
Supports both CLI and Cloud session formats.
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field


# Default Codex sessions directory
DEFAULT_SESSIONS_DIR = Path.home() / ".codex" / "sessions"


@dataclass
class SessionMetadata:
    """Metadata for a Codex session."""
    session_id: str
    path: str
    date: str  # YYYY-MM-DD
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_seconds: Optional[float] = None
    model: Optional[str] = None
    model_provider: Optional[str] = None
    cli_version: Optional[str] = None
    source: Optional[str] = None  # "cli" or "cloud"
    status: Optional[str] = None  # "complete", "aborted", "unknown"
    cwd: Optional[str] = None
    exit_code: Optional[int] = None
    
    # Token stats
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    cached_tokens: int = 0
    total_tokens: int = 0
    
    # Event counts
    tool_calls: int = 0
    exec_commands: int = 0
    thinking_blocks: int = 0
    turns: int = 0


@dataclass
class ToolCall:
    """Represents a tool call in a session."""
    timestamp: str
    name: str
    arguments: Dict[str, Any]
    call_id: str
    output: Optional[str] = None
    exit_code: Optional[int] = None
    duration_ms: Optional[float] = None


@dataclass
class Event:
    """Represents a generic session event."""
    timestamp: str
    event_type: str
    data: Dict[str, Any]


def find_sessions(sessions_dir: Path = DEFAULT_SESSIONS_DIR) -> List[SessionMetadata]:
    """
    Find all available Codex sessions.
    
    Args:
        sessions_dir: Path to the sessions directory
        
    Returns:
        List of SessionMetadata for each session found
    """
    sessions = []
    
    if not sessions_dir.exists():
        return sessions
    
    # Find all rollout-*.jsonl files
    for jsonl_file in sessions_dir.rglob("rollout-*.jsonl"):
        try:
            # Extract date from path: .../YYYY/MM/DD/rollout-*.jsonl
            parts = jsonl_file.parts
            # Path is: .../sessions/YYYY/MM/DD/rollout-*.jsonl
            # parts[-5] = sessions, parts[-4] = YYYY, parts[-3] = MM, parts[-2] = DD
            if len(parts) >= 5:
                date = f"{parts[-4]}-{parts[-3]}-{parts[-2]}"
            else:
                date = "unknown"
            
            session_id = jsonl_file.stem.replace("rollout-", "")
            
            sessions.append(SessionMetadata(
                session_id=session_id,
                path=str(jsonl_file),
                date=date
            ))
        except Exception as e:
            print(f"Error processing {jsonl_file}: {e}")
            continue
    
    return sessions


def parse_session(path: str) -> Tuple[SessionMetadata, List[Event], List[ToolCall]]:
    """
    Parse a single Codex session JSONL file.
    
    Args:
        path: Path to the session JSONL file
        
    Returns:
        Tuple of (SessionMetadata, List of Events, List of ToolCalls)
    """
    metadata = SessionMetadata(
        session_id=Path(path).stem.replace("rollout-", ""),
        path=path,
        date="unknown"
    )
    events = []
    tool_calls = []
    
    # Extract date from path
    parts = Path(path).parts
    if len(parts) >= 3:
        metadata.date = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
    
    # Track token counts across the session
    total_input = 0
    total_output = 0
    total_reasoning = 0
    total_cached = 0
    
    first_timestamp = None
    last_timestamp = None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    # Handle malformed JSON gracefully
                    continue
                
                # Extract timestamp
                timestamp = entry.get("timestamp", "")
                if timestamp:
                    if first_timestamp is None:
                        first_timestamp = timestamp
                    last_timestamp = timestamp
                
                entry_type = entry.get("type", "")
                payload = entry.get("payload", {})
                
                # Parse session metadata
                if entry_type == "session_meta":
                    _parse_session_meta(payload, metadata)
                
                # Parse token counts
                elif entry_type == "event_msg":
                    if payload.get("type") == "token_count":
                        token_info = payload.get("info", {})
                        usage = token_info.get("total_token_usage", {})
                        if usage:
                            total_input = usage.get("input_tokens", 0)
                            total_output = usage.get("output_tokens", 0)
                            total_reasoning = usage.get("reasoning_output_tokens", 0)
                            total_cached = usage.get("cached_input_tokens", 0)
                            metadata.total_tokens = usage.get("total_tokens", 0)
                
                # Parse task events for status
                elif entry_type == "event_msg":
                    event_subtype = payload.get("type", "")
                    if event_subtype == "task_started":
                        metadata.status = "started"
                    elif event_subtype == "task_complete":
                        metadata.status = "complete"
                    elif event_subtype == "turn_aborted":
                        metadata.status = "aborted"
                
                # Parse function calls (tool calls)
                elif entry_type == "response_item":
                    if payload.get("type") == "function_call":
                        tool_call = _parse_function_call(payload, timestamp)
                        if tool_call:
                            tool_calls.append(tool_call)
                            metadata.tool_calls += 1
                            if tool_call.name == "exec_command":
                                metadata.exec_commands += 1
                    
                    elif payload.get("type") == "reasoning":
                        metadata.thinking_blocks += 1
                        events.append(Event(
                            timestamp=timestamp,
                            event_type="reasoning",
                            data=payload
                        ))
                    
                    elif payload.get("type") == "function_call_output":
                        # Link output to tool call
                        call_id = payload.get("call_id", "")
                        output = payload.get("output", "")
                        
                        # Try to find and update matching tool call
                        for tc in tool_calls:
                            if tc.call_id == call_id:
                                tc.output = output
                                # Extract exit code from output
                                exit_code = _extract_exit_code(output)
                                if exit_code is not None:
                                    tc.exit_code = exit_code
                                break
                
                # Store other events
                events.append(Event(
                    timestamp=timestamp,
                    event_type=entry_type,
                    data=payload
                ))
        
        # Calculate duration
        if first_timestamp and last_timestamp:
            try:
                start = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
                end = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
                metadata.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass
        
        # Set final timestamps
        metadata.start_time = first_timestamp
        metadata.end_time = last_timestamp
        
        # Set token counts
        metadata.input_tokens = total_input
        metadata.output_tokens = total_output
        metadata.reasoning_tokens = total_reasoning
        metadata.cached_tokens = total_cached
        if metadata.total_tokens == 0:
            metadata.total_tokens = total_input + total_output + total_reasoning
        
    except FileNotFoundError:
        raise FileNotFoundError(f"Session file not found: {path}")
    except Exception as e:
        raise RuntimeError(f"Error parsing session {path}: {e}")
    
    return metadata, events, tool_calls


def _parse_session_meta(payload: Dict[str, Any], metadata: SessionMetadata) -> None:
    """Parse session metadata from payload."""
    session_data = payload.get("id", "")
    metadata.session_id = session_data or metadata.session_id
    
    timestamp = payload.get("timestamp", "")
    if timestamp:
        metadata.start_time = timestamp
    
    metadata.cwd = payload.get("cwd")
    metadata.cli_version = payload.get("cli_version")
    metadata.source = payload.get("source")
    
    model_info = payload.get("model_provider")
    if model_info:
        metadata.model_provider = model_info
    
    # Extract model from base_instructions if available
    base_instructions = payload.get("base_instructions", {})
    if isinstance(base_instructions, dict):
        text = base_instructions.get("text", "")
        # Try to extract model name from instructions
        if "GPT-5" in text:
            metadata.model = "gpt-5"
        elif "GPT-4" in text:
            metadata.model = "gpt-4"
        elif "o1" in text.lower():
            metadata.model = "o1"


def _parse_function_call(payload: Dict[str, Any], timestamp: str) -> Optional[ToolCall]:
    """Parse a function call entry."""
    name = payload.get("name", "")
    arguments_str = payload.get("arguments", "{}")
    call_id = payload.get("call_id", "")
    
    try:
        if isinstance(arguments_str, str):
            arguments = json.loads(arguments_str)
        else:
            arguments = arguments_str
    except json.JSONDecodeError:
        arguments = {"raw": arguments_str}
    
    return ToolCall(
        timestamp=timestamp,
        name=name,
        arguments=arguments,
        call_id=call_id
    )


def _extract_exit_code(output: str) -> Optional[int]:
    """Extract exit code from command output."""
    # Look for "Process exited with code N"
    match = re.search(r"Process exited with code (\d+)", output)
    if match:
        return int(match.group(1))
    return None


def extract_events(session_data: Tuple[SessionMetadata, List[Event], List[ToolCall]]) -> Dict[str, Any]:
    """
    Extract structured events from parsed session data.
    
    Args:
        session_data: Tuple of (SessionMetadata, List of Events, List of ToolCalls)
        
    Returns:
        Dictionary with extracted events organized by type
    """
    metadata, events, tool_calls = session_data
    
    result = {
        "session_id": metadata.session_id,
        "date": metadata.date,
        "tool_calls": [],
        "exec_commands": [],
        "thinking_blocks": [],
        "token_usage": {
            "input": metadata.input_tokens,
            "output": metadata.output_tokens,
            "reasoning": metadata.reasoning_tokens,
            "cached": metadata.cached_tokens,
            "total": metadata.total_tokens
        },
        "timestamps": {
            "start": metadata.start_time,
            "end": metadata.end_time
        },
        "duration_seconds": metadata.duration_seconds,
        "model": metadata.model,
        "model_provider": metadata.model_provider,
        "status": metadata.status,
        "cli_version": metadata.cli_version
    }
    
    # Extract tool calls
    for tc in tool_calls:
        result["tool_calls"].append({
            "timestamp": tc.timestamp,
            "name": tc.name,
            "call_id": tc.call_id,
            "arguments": tc.arguments,
            "output": tc.output[:500] if tc.output else None,  # Truncate long output
            "exit_code": tc.exit_code
        })
        
        if tc.name == "exec_command":
            cmd = tc.arguments.get("cmd", "")[:200]  # Truncate long commands
            result["exec_commands"].append({
                "timestamp": tc.timestamp,
                "call_id": tc.call_id,
                "command": cmd,
                "exit_code": tc.exit_code
            })
    
    # Extract thinking blocks
    for event in events:
        if event.event_type == "reasoning":
            content = event.data.get("content")
            summary = event.data.get("summary", [])
            result["thinking_blocks"].append({
                "timestamp": event.timestamp,
                "summary": summary,
                "has_content": content is not None
            })
    
    return result


def get_session_stats(session_data: Tuple[SessionMetadata, List[Event], List[ToolCall]]) -> Dict[str, Any]:
    """
    Calculate statistics for a session.
    
    Args:
        session_data: Tuple of (SessionMetadata, List of Events, List of ToolCalls)
        
    Returns:
        Dictionary with session statistics
    """
    metadata, events, tool_calls = session_data
    
    # Count different event types
    event_counts = {}
    for event in events:
        event_counts[event.event_type] = event_counts.get(event.event_type, 0) + 1
    
    # Count tool calls by name
    tool_name_counts = {}
    for tc in tool_calls:
        tool_name_counts[tc.name] = tool_name_counts.get(tc.name, 0) + 1
    
    # Count exec commands
    exec_count = sum(1 for tc in tool_calls if tc.name == "exec_command")
    exec_failed = sum(1 for tc in tool_calls if tc.name == "exec_command" and tc.exit_code != 0)
    
    return {
        "session_id": metadata.session_id,
        "date": metadata.date,
        "duration_seconds": metadata.duration_seconds,
        "model": metadata.model,
        "model_provider": metadata.model_provider,
        "status": metadata.status,
        "cli_version": metadata.cli_version,
        "source": metadata.source,
        "tokens": {
            "input": metadata.input_tokens,
            "output": metadata.output_tokens,
            "reasoning": metadata.reasoning_tokens,
            "cached": metadata.cached_tokens,
            "total": metadata.total_tokens
        },
        "tool_calls": {
            "total": metadata.tool_calls,
            "by_name": tool_name_counts
        },
        "exec_commands": {
            "total": exec_count,
            "failed": exec_failed,
            "success_rate": (exec_count - exec_failed) / exec_count if exec_count > 0 else 0
        },
        "thinking_blocks": metadata.thinking_blocks,
        "turns": metadata.turns,
        "event_counts": event_counts
    }


def quick_parse(path: str) -> Dict[str, Any]:
    """
    Quick parse of a session file - returns only metadata.
    Optimized for fast scanning of many sessions.
    
    Args:
        path: Path to the session JSONL file
        
    Returns:
        Dictionary with basic session metadata
    """
    metadata = SessionMetadata(
        session_id=Path(path).stem.replace("rollout-", ""),
        path=path,
        date="unknown"
    )
    
    # Extract date from path
    parts = Path(path).parts
    if len(parts) >= 3:
        metadata.date = f"{parts[-3]}-{parts[-2]}-{parts[-1]}"
    
    total_tokens = 0
    first_timestamp = None
    last_timestamp = None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                
                entry_type = entry.get("type", "")
                timestamp = entry.get("timestamp", "")
                
                if timestamp:
                    if first_timestamp is None:
                        first_timestamp = timestamp
                    last_timestamp = timestamp
                
                payload = entry.get("payload", {})
                
                if entry_type == "session_meta":
                    _parse_session_meta(payload, metadata)
                
                elif entry_type == "event_msg" and payload.get("type") == "token_count":
                    usage = payload.get("info", {}).get("total_token_usage", {})
                    if usage:
                        total_tokens = usage.get("total_tokens", 0)
                
                elif entry_type == "event_msg":
                    subtype = payload.get("type", "")
                    if subtype == "task_complete":
                        metadata.status = "complete"
                    elif subtype == "task_started":
                        metadata.status = "started"
                    elif subtype == "turn_aborted":
                        metadata.status = "aborted"
                
                elif entry_type == "response_item":
                    ptype = payload.get("type", "")
                    if ptype == "function_call":
                        metadata.tool_calls += 1
                        if payload.get("name") == "exec_command":
                            metadata.exec_commands += 1
                    elif ptype == "reasoning":
                        metadata.thinking_blocks += 1
        
        # Calculate duration
        if first_timestamp and last_timestamp:
            try:
                start = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
                end = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
                metadata.duration_seconds = (end - start).total_seconds()
            except Exception:
                pass
        
        metadata.start_time = first_timestamp
        metadata.end_time = last_timestamp
        metadata.total_tokens = total_tokens
        
    except Exception as e:
        print(f"Error in quick_parse for {path}: {e}")
    
    return {
        "session_id": metadata.session_id,
        "path": metadata.path,
        "date": metadata.date,
        "start_time": metadata.start_time,
        "end_time": metadata.end_time,
        "duration_seconds": metadata.duration_seconds,
        "model": metadata.model,
        "model_provider": metadata.model_provider,
        "status": metadata.status,
        "cli_version": metadata.cli_version,
        "source": metadata.source,
        "input_tokens": metadata.input_tokens,
        "output_tokens": metadata.output_tokens,
        "total_tokens": metadata.total_tokens,
        "tool_calls": metadata.tool_calls,
        "exec_commands": metadata.exec_commands,
        "thinking_blocks": metadata.thinking_blocks
    }


if __name__ == "__main__":
    # Test the parser
    sessions = find_sessions()
    print(f"Found {len(sessions)} sessions")
    
    if sessions:
        # Quick parse first session
        first = sessions[0]
        print(f"\nQuick parsing: {first.path}")
        result = quick_parse(first.path)
        print(f"  Date: {result['date']}")
        print(f"  Status: {result['status']}")
        print(f"  Tokens: {result['total_tokens']}")
        print(f"  Tool calls: {result['tool_calls']}")
