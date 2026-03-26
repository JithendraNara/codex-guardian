"""
Runaway Detection Engine for Codex Guardian.
Detects problematic Codex CLI sessions before they burn through tokens.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from collections import Counter, defaultdict
import re

from .thresholds import Thresholds, Preset


@dataclass
class DetectionResult:
    """Result of a detection check."""
    detected: bool
    severity: str  # "low", "medium", "high", "critical"
    message: str
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class HealthScore:
    """Health score result."""
    score: int  # 0-100, lower = more risky
    factors: Dict[str, Any]  # Breakdown of factors
    recommendations: List[str]  # Suggested actions


class Event:
    """Represents a session event from Codex CLI."""
    
    def __init__(
        self,
        timestamp: datetime,
        event_type: str,  # "tool_call", "status_change", "token_update"
        tool_name: str = None,
        file_path: str = None,
        command: str = None,
        tokens: int = None,
        status: str = None,
    ):
        self.timestamp = timestamp
        self.event_type = event_type
        self.tool_name = tool_name
        self.file_path = file_path
        self.command = command
        self.tokens = tokens
        self.status = status
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create Event from dictionary."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        elif timestamp is None:
            timestamp = datetime.now()
        
        return cls(
            timestamp=timestamp,
            event_type=data.get("event_type", "unknown"),
            tool_name=data.get("tool_name"),
            file_path=data.get("file_path"),
            command=data.get("command"),
            tokens=data.get("tokens"),
            status=data.get("status"),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type,
            "tool_name": self.tool_name,
            "file_path": self.file_path,
            "command": self.command,
            "tokens": self.tokens,
            "status": self.status,
        }


def normalize_path(path: str) -> str:
    """Normalize file path for comparison."""
    if not path:
        return ""
    # Remove trailing slashes, normalize home directory
    path = path.rstrip("/")
    path = re.sub(r"^~/", "/home/user/", path)
    # Get just the filename for comparison
    return path.split("/")[-1]


def detect_infinite_loop(
    events: List[Event],
    thresholds: Thresholds = None
) -> DetectionResult:
    """
    Detect repeated tool calls, circular file edits, stuck states.
    
    Rules:
    - Same file modified 3+ times in 2 minutes
    - Same tool call 5+ times in 2 minutes
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    if not events:
        return DetectionResult(
            detected=False,
            severity="low",
            message="No events to analyze"
        )
    
    # Sort events by timestamp
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    
    # Check for same file modifications
    now = sorted_events[-1].timestamp
    window_start = now - timedelta(minutes=thresholds.same_file_time_window_minutes)
    
    recent_file_events = [
        e for e in sorted_events
        if e.timestamp >= window_start and e.file_path
    ]
    
    file_counts = Counter(normalize_path(e.file_path) for e in recent_file_events)
    
    repeating_files = {
        f: count for f, count in file_counts.items()
        if count >= thresholds.same_file_modifications
    }
    
    # Check for same tool calls
    recent_tool_events = [
        e for e in sorted_events
        if e.timestamp >= window_start and e.tool_name
    ]
    
    tool_counts = Counter(e.tool_name for e in recent_tool_events)
    
    repeating_tools = {
        t: count for t, count in tool_counts.items()
        if count >= thresholds.same_tool_calls
    }
    
    # Determine severity
    max_repeats = max(
        max(repeating_files.values(), default=0),
        max(repeating_tools.values(), default=0)
    )
    
    if max_repeats >= thresholds.same_file_modifications + 2:
        severity = "critical"
    elif max_repeats >= thresholds.same_file_modifications:
        severity = "high"
    elif repeating_files or repeating_tools:
        severity = "medium"
    else:
        return DetectionResult(
            detected=False,
            severity="low",
            message="No infinite loop patterns detected"
        )
    
    details = {
        "repeating_files": repeating_files,
        "repeating_tools": repeating_tools,
        "time_window_minutes": thresholds.same_file_time_window_minutes,
    }
    
    message = f"Infinite loop detected: {len(repeating_files)} files, {len(repeating_tools)} tools repeating"
    
    return DetectionResult(
        detected=True,
        severity=severity,
        message=message,
        details=details
    )


def detect_token_spike(
    events: List[Event],
    threshold: int = 10000,
    thresholds: Thresholds = None
) -> DetectionResult:
    """
    Flag sessions burning tokens too fast.
    
    Rules:
    - >5000 tokens/min sustained for N minutes
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    threshold = thresholds.token_spike_threshold
    
    # Get events with token information
    token_events = [e for e in events if e.tokens is not None]
    
    if len(token_events) < 2:
        return DetectionResult(
            detected=False,
            severity="low",
            message="Insufficient token data to analyze"
        )
    
    sorted_events = sorted(token_events, key=lambda e: e.timestamp)
    
    # Calculate token consumption rate
    first_event = sorted_events[0]
    last_event = sorted_events[-1]
    
    duration_minutes = (last_event.timestamp - first_event.timestamp).total_seconds() / 60
    if duration_minutes < 0.1:
        duration_minutes = 0.1  # Minimum to avoid division issues
    
    tokens_consumed = last_event.tokens - first_event.tokens
    tokens_per_minute = tokens_consumed / duration_minutes
    
    # Check for sustained spike (recent window)
    now = last_event.timestamp
    window_start = now - timedelta(minutes=thresholds.token_spike_sustained_minutes)
    
    recent_token_events = [e for e in sorted_events if e.timestamp >= window_start]
    
    if len(recent_token_events) >= 2:
        recent_first = recent_token_events[0]
        recent_last = recent_token_events[-1]
        recent_duration = (recent_last.timestamp - recent_first.timestamp).total_seconds() / 60
        
        if recent_duration > 0:
            recent_tokens = recent_last.tokens - recent_first.tokens
            recent_tokens_per_minute = recent_tokens / recent_duration
            
            # Use the higher of overall or recent rate
            tokens_per_minute = max(tokens_per_minute, recent_tokens_per_minute)
    
    # Determine severity
    if tokens_per_minute > threshold * 2:
        severity = "critical"
    elif tokens_per_minute > threshold:
        severity = "high"
    elif tokens_per_minute > threshold * 0.7:
        severity = "medium"
    else:
        return DetectionResult(
            detected=False,
            severity="low",
            message="Token consumption within normal limits"
        )
    
    details = {
        "tokens_per_minute": int(tokens_per_minute),
        "total_tokens": tokens_consumed,
        "duration_minutes": round(duration_minutes, 2),
        "threshold": threshold,
    }
    
    return DetectionResult(
        detected=True,
        severity=severity,
        message=f"Token spike detected: {int(tokens_per_minute)} tokens/min",
        details=details
    )


def detect_stuck_session(
    events: List[Event],
    minutes: int = 5,
    thresholds: Thresholds = None
) -> DetectionResult:
    """
    Detect sessions with no progress for N minutes while 'Working...'.
    
    Rules:
    - No tool call progress for 5+ minutes while "Working..."
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    minutes = thresholds.stuck_no_progress_minutes
    
    if not events:
        return DetectionResult(
            detected=False,
            severity="low",
            message="No events to analyze"
        )
    
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    now = sorted_events[-1].timestamp
    window_start = now - timedelta(minutes=minutes)
    
    # Find last tool call
    tool_calls = [e for e in sorted_events if e.event_type == "tool_call"]
    
    if not tool_calls:
        # No tool calls at all - could be stuck at start
        return DetectionResult(
            detected=True,
            severity="medium",
            message="No tool calls detected in session",
            details={"total_events": len(events)}
        )
    
    last_tool_call = tool_calls[-1]
    time_since_last_tool = (now - last_tool_call.timestamp).total_seconds() / 60
    
    # Check if stuck
    if time_since_last_tool < minutes:
        return DetectionResult(
            detected=False,
            severity="low",
            message=f"Last tool call {time_since_last_tool:.1f} minutes ago"
        )
    
    # Check status if required
    if thresholds.stuck_require_working_status:
        recent_events = [e for e in sorted_events if e.timestamp >= window_start]
        working_statuses = [
            e for e in recent_events
            if e.status and "working" in e.status.lower()
        ]
        
        if not working_statuses:
            return DetectionResult(
                detected=False,
                severity="low",
                message="Session not in 'Working...' state"
            )
    
    # Determine severity
    if time_since_last_tool > minutes * 2:
        severity = "critical"
    elif time_since_last_tool > minutes * 1.5:
        severity = "high"
    else:
        severity = "medium"
    
    details = {
        "minutes_since_last_tool": round(time_since_last_tool, 2),
        "last_tool": last_tool_call.tool_name,
        "threshold_minutes": minutes,
    }
    
    return DetectionResult(
        detected=True,
        severity=severity,
        message=f"Stuck session detected: {time_since_last_tool:.1f} minutes without progress",
        details=details
    )


def detect_risky_pattern(events: List[Event], thresholds: Thresholds = None) -> DetectionResult:
    """
    Detect dangerous commands and risky operations.
    
    Rules:
    - rm -rf, mass deletes, recursive operations
    - N+ file operations in short time
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    if not events:
        return DetectionResult(
            detected=False,
            severity="low",
            message="No events to analyze"
        )
    
    sorted_events = sorted(events, key=lambda e: e.timestamp)
    now = sorted_events[-1].timestamp
    
    # Check for dangerous commands
    dangerous_found = []
    
    for event in sorted_events:
        command = event.command or ""
        tool_name = event.tool_name or ""
        
        for dangerous_cmd in thresholds.risky_commands:
            if dangerous_cmd.lower() in command.lower():
                dangerous_found.append({
                    "command": dangerous_cmd,
                    "full_command": command,
                    "timestamp": event.timestamp.isoformat(),
                    "tool": tool_name,
                })
    
    # Check for mass file operations
    recent_window = now - timedelta(minutes=5)
    file_ops = [
        e for e in sorted_events
        if e.timestamp >= recent_window
        and e.event_type in ("file_write", "file_delete", "file_create")
        and e.file_path
    ]
    
    # Group by operation type
    file_op_counts = Counter(e.event_type for e in file_ops)
    
    mass_operations = []
    if len(file_ops) >= thresholds.mass_file_threshold:
        mass_operations = {
            "total_operations": len(file_ops),
            "by_type": dict(file_op_counts),
            "time_window_minutes": 5,
        }
    
    # Check for recursive patterns in commands
    recursive_patterns = [
        r"-R\s", r"-r\s", r"--recursive",
        r"find\s+/", r"grep\s+-r\s", r"chmod\s+-R",
    ]
    
    recursive_found = []
    for event in sorted_events:
        command = event.command or ""
        for pattern in recursive_patterns:
            if re.search(pattern, command):
                recursive_found.append({
                    "pattern": pattern,
                    "command": command[:100],
                    "timestamp": event.timestamp.isoformat(),
                })
    
    # Determine if any risky patterns found
    if not dangerous_found and not mass_operations and not recursive_found:
        return DetectionResult(
            detected=False,
            severity="low",
            message="No risky patterns detected"
        )
    
    # Determine severity
    if len(dangerous_found) > 0 or len(recursive_found) > 2:
        severity = "critical"
    elif mass_operations or recursive_found:
        severity = "high"
    else:
        severity = "medium"
    
    details = {
        "dangerous_commands": dangerous_found[:10],  # Limit to 10
        "mass_operations": mass_operations,
        "recursive_operations": recursive_found[:10],
    }
    
    message = f"Risky patterns detected: {len(dangerous_found)} dangerous commands, {len(recursive_found)} recursive ops"
    
    return DetectionResult(
        detected=True,
        severity=severity,
        message=message,
        details=details
    )


def calculate_health_score(
    session_data: Dict[str, Any],
    thresholds: Thresholds = None
) -> HealthScore:
    """
    Calculate overall session health score (0-100).
    Lower score = more risky.
    
    Factors:
    - Infinite loop detection (25%)
    - Token spike (25%)
    - Stuck session (20%)
    - Risky patterns (20%)
    - Session duration (10%)
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    events = session_data.get("events", [])
    if isinstance(events, list) and len(events) > 0:
        if isinstance(events[0], dict):
            events = [Event.from_dict(e) for e in events]
    else:
        events = []
    
    # Run all detections
    loop_result = detect_infinite_loop(events, thresholds)
    token_result = detect_token_spike(events, thresholds=thresholds)
    stuck_result = detect_stuck_session(events, thresholds=thresholds)
    risky_result = detect_risky_pattern(events, thresholds)
    
    # Calculate factor scores (0-100 each)
    factors = {}
    
    # Infinite loop factor
    if loop_result.detected:
        loop_score = {"critical": 0, "high": 25, "medium": 50}.get(loop_result.severity, 75)
    else:
        loop_score = 100
    factors["infinite_loop"] = loop_score
    
    # Token spike factor
    if token_result.detected:
        token_score = {"critical": 0, "high": 20, "medium": 50}.get(token_result.severity, 70)
    else:
        token_score = 100
    factors["token_spike"] = token_score
    
    # Stuck session factor
    if stuck_result.detected:
        stuck_score = {"critical": 0, "high": 30, "medium": 60}.get(stuck_result.severity, 80)
    else:
        stuck_score = 100
    factors["stuck_session"] = stuck_score
    
    # Risky pattern factor
    if risky_result.detected:
        risky_score = {"critical": 0, "high": 25, "medium": 50}.get(risky_result.severity, 75)
    else:
        risky_score = 100
    factors["risky_pattern"] = risky_score
    
    # Duration factor
    if events:
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        duration_minutes = (
            sorted_events[-1].timestamp - sorted_events[0].timestamp
        ).total_seconds() / 60
        
        if duration_minutes > thresholds.max_session_duration_minutes:
            duration_score = 0
        elif duration_minutes > thresholds.max_session_duration_minutes * 0.8:
            duration_score = 50
        elif duration_minutes > thresholds.max_session_duration_minutes * 0.5:
            duration_score = 75
        else:
            duration_score = 100
    else:
        duration_score = 100
    factors["duration"] = duration_score
    
    # Calculate weighted score
    weights = {
        "infinite_loop": thresholds.health_infinite_loop_weight,
        "token_spike": thresholds.health_token_spike_weight,
        "stuck_session": thresholds.health_stuck_weight,
        "risky_pattern": thresholds.health_risky_weight,
        "duration": thresholds.health_duration_weight,
    }
    
    total_score = sum(
        factors[factor] * weight / 100
        for factor, weight in weights.items()
    )
    
    score = int(total_score)
    
    # Generate recommendations
    recommendations = []
    if loop_result.detected:
        recommendations.append("Investigate potential infinite loop - same file/tool repeated")
    if token_result.detected:
        recommendations.append(f"High token consumption: {token_result.details.get('tokens_per_minute', '?')} tokens/min")
    if stuck_result.detected:
        recommendations.append("Session appears stuck - check for deadlocks or waiting for input")
    if risky_result.detected:
        recommendations.append("Risky commands detected - review for destructive operations")
    if duration_minutes > thresholds.max_session_duration_minutes * 0.8:
        recommendations.append("Session approaching max duration - consider saving and restarting")
    
    if not recommendations:
        recommendations.append("Session looks healthy - continue monitoring")
    
    return HealthScore(
        score=score,
        factors=factors,
        recommendations=recommendations
    )


# --- Cost Calculation ---
# Codex CLI uses OpenAI's pricing model
# Input: $0.03/1K tokens | Output: $0.06/1K tokens
CODEX_INPUT_COST_PER_1K = 0.03
CODEX_OUTPUT_COST_PER_1K = 0.06

# Rough assumption: 30% input, 70% output
INPUT_OUTPUT_RATIO = 0.30


def estimate_session_cost(
    events: List[Event],
    session_id: str = None
) -> Dict[str, Any]:
    """
    Estimate cost of a Codex session based on token usage.

    Returns:
        cost_to_date: Estimated cost so far
        tokens_to_date: Total tokens consumed
        projected_session_cost: Cost if session continues at current rate
        projected_hourly_cost: Estimated cost per hour
        budget_remaining: How much of session budget remains
        session_limit: Configured session token limit
    """
    # Get token events
    token_events = [e for e in events if e.tokens is not None]

    if len(token_events) < 2:
        return {
            "cost_to_date": 0.0,
            "tokens_to_date": 0,
            "projected_session_cost": 0.0,
            "projected_hourly_cost": 0.0,
            "budget_remaining": 10000,
            "session_limit": 10000,
            "burn_rate_tokens_per_min": 0,
        }

    sorted_events = sorted(token_events, key=lambda e: e.timestamp)
    first_event = sorted_events[0]
    last_event = sorted_events[-1]

    tokens_to_date = last_event.tokens - first_event.tokens
    duration_minutes = (last_event.timestamp - first_event.timestamp).total_seconds() / 60

    # Calculate cost
    input_tokens = int(tokens_to_date * INPUT_OUTPUT_RATIO)
    output_tokens = int(tokens_to_date * (1 - INPUT_OUTPUT_RATIO))
    cost_to_date = (input_tokens * CODEX_INPUT_COST_PER_1K / 1000) + \
                   (output_tokens * CODEX_OUTPUT_COST_PER_1K / 1000)

    # Project cost if session continues at current rate
    if duration_minutes > 0.1:
        burn_rate_per_min = tokens_to_date / duration_minutes
        projected_hourly_cost = (burn_rate_per_min * 60 / 1000) * \
            (input_tokens/tokens_to_date * CODEX_INPUT_COST_PER_1K +
             (1 - input_tokens/tokens_to_date) * CODEX_OUTPUT_COST_PER_1K) \
            if tokens_to_date > 0 else 0

        # Assume 1-hour session remaining
        session_duration_estimate = max(duration_minutes, 60)
        total_projected_tokens = int(burn_rate_per_min * session_duration_estimate)
        total_input = int(total_projected_tokens * INPUT_OUTPUT_RATIO)
        total_output = total_projected_tokens - total_input
        projected_session_cost = (total_input * CODEX_INPUT_COST_PER_1K / 1000) + \
                                (total_output * CODEX_OUTPUT_COST_PER_1K / 1000)
    else:
        burn_rate_per_min = 0
        projected_hourly_cost = 0
        projected_session_cost = cost_to_date

    # Budget tracking
    session_limit = 10000  # default
    budget_remaining = max(0, session_limit - tokens_to_date)

    return {
        "cost_to_date": round(cost_to_date, 4),
        "tokens_to_date": tokens_to_date,
        "projected_session_cost": round(projected_session_cost, 4),
        "projected_hourly_cost": round(projected_hourly_cost, 2),
        "budget_remaining": budget_remaining,
        "session_limit": session_limit,
        "burn_rate_tokens_per_min": int(burn_rate_per_min),
        "duration_minutes": round(duration_minutes, 1),
    }


def format_cost_alert(cost_data: Dict[str, Any], session_id: str = None) -> str:
    """Format cost data as a readable alert message."""
    msg = f"💰 Cost Estimate"
    if session_id:
        msg += f" | Session: {session_id[:8]}"
    msg += f"\n  Spent so far: ${cost_data['cost_to_date']:.4f}"
    msg += f"\n  Tokens used: {cost_data['tokens_to_date']:,}"
    msg += f"\n  Burn rate: {cost_data['burn_rate_tokens_per_min']} tokens/min"
    msg += f"\n  Projected (1hr): ${cost_data['projected_hourly_cost']:.2f}/hr"
    msg += f"\n  Budget remaining: {cost_data['budget_remaining']:,} tokens"
    return msg


# Convenience function for quick detection
def analyze_session(
    events: List[Event],
    thresholds: Thresholds = None
) -> Dict[str, Any]:
    """
    Run all detections and return comprehensive analysis.
    """
    if thresholds is None:
        thresholds = Thresholds()
    
    if isinstance(events, list) and len(events) > 0:
        if isinstance(events[0], dict):
            events = [Event.from_dict(e) for e in events]
    
    loop_result = detect_infinite_loop(events, thresholds)
    token_result = detect_token_spike(events, thresholds=thresholds)
    stuck_result = detect_stuck_session(events, thresholds=thresholds)
    risky_result = detect_risky_pattern(events, thresholds)
    
    session_data = {"events": events}
    health = calculate_health_score(session_data, thresholds)
    
    return {
        "healthy": health.score >= 70,
        "health_score": health.score,
        "detections": {
            "infinite_loop": {
                "detected": loop_result.detected,
                "severity": loop_result.severity,
                "message": loop_result.message,
            },
            "token_spike": {
                "detected": token_result.detected,
                "severity": token_result.severity,
                "message": token_result.message,
            },
            "stuck_session": {
                "detected": stuck_result.detected,
                "severity": stuck_result.severity,
                "message": stuck_result.message,
            },
            "risky_pattern": {
                "detected": risky_result.detected,
                "severity": risky_result.severity,
                "message": risky_result.message,
            },
        },
        "recommendations": health.recommendations,
    }
