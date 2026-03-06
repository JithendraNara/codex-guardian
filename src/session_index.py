#!/usr/bin/env python3
"""
Codex Session Index

Builds and queries an SQLite index of all Codex sessions.
Supports filtering by date range, model, status, and token usage.
"""

import os
import sqlite3
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from log_parser import find_sessions, quick_parse, DEFAULT_SESSIONS_DIR


# Database path
DEFAULT_DB_PATH = Path.home() / ".codex" / "sessions.db"


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """Get a database connection."""
    if db_path is None:
        db_path = DEFAULT_DB_PATH
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = None) -> None:
    """Initialize the database schema."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            path TEXT NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            duration_seconds REAL,
            model TEXT,
            model_provider TEXT,
            cli_version TEXT,
            source TEXT,
            status TEXT,
            input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0,
            reasoning_tokens INTEGER DEFAULT 0,
            cached_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            tool_calls INTEGER DEFAULT 0,
            exec_commands INTEGER DEFAULT 0,
            thinking_blocks INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes for common queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_status ON sessions(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_model ON sessions(model)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_total_tokens ON sessions(total_tokens)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_duration ON sessions(duration_seconds)")
    
    conn.commit()
    conn.close()


def build_index(
    sessions_dir: Path = DEFAULT_SESSIONS_DIR,
    db_path: str = None,
    force: bool = False
) -> Dict[str, Any]:
    """
    Build or update the session index.
    
    Args:
        sessions_dir: Path to sessions directory
        db_path: Path to database file
        force: If True, rebuild entire index; otherwise only add new sessions
        
    Returns:
        Dictionary with build statistics
    """
    start_time = time.time()
    
    # Initialize database
    init_db(db_path)
    
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Get existing session IDs if not forcing rebuild
    existing_ids = set()
    if not force:
        cursor.execute("SELECT session_id FROM sessions")
        existing_ids = {row[0] for row in cursor.fetchall()}
    
    # Find all sessions
    sessions = find_sessions(sessions_dir)
    
    added = 0
    skipped = 0
    errors = 0
    
    for session in sessions:
        if session.session_id in existing_ids:
            skipped += 1
            continue
        
        try:
            # Quick parse the session
            data = quick_parse(session.path)
            
            # Insert into database
            cursor.execute("""
                INSERT INTO sessions (
                    session_id, path, date, start_time, end_time,
                    duration_seconds, model, model_provider, cli_version,
                    source, status, input_tokens, output_tokens,
                    reasoning_tokens, cached_tokens, total_tokens,
                    tool_calls, exec_commands, thinking_blocks
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data["session_id"],
                data["path"],
                data["date"],
                data["start_time"],
                data["end_time"],
                data["duration_seconds"],
                data["model"],
                data["model_provider"],
                data["cli_version"],
                data["source"],
                data["status"],
                data["input_tokens"],
                data["output_tokens"],
                0,  # reasoning_tokens not in quick_parse
                0,  # cached_tokens not in quick_parse
                data["total_tokens"],
                data["tool_calls"],
                data["exec_commands"],
                data["thinking_blocks"]
            ))
            added += 1
            
        except Exception as e:
            errors += 1
            print(f"Error indexing {session.path}: {e}")
    
    conn.commit()
    conn.close()
    
    elapsed = time.time() - start_time
    
    return {
        "total_sessions": len(sessions),
        "added": added,
        "skipped": skipped,
        "errors": errors,
        "elapsed_seconds": elapsed
    }


def query_sessions(
    db_path: str = None,
    date_start: str = None,
    date_end: str = None,
    model: str = None,
    model_provider: str = None,
    status: str = None,
    min_tokens: int = None,
    max_tokens: int = None,
    min_duration: float = None,
    max_duration: float = None,
    min_tool_calls: int = None,
    max_tool_calls: int = None,
    limit: int = 100,
    order_by: str = "date",
    order_dir: str = "DESC"
) -> List[Dict[str, Any]]:
    """
    Query sessions with filters.
    
    Args:
        db_path: Path to database file
        date_start: Start date (YYYY-MM-DD)
        date_end: End date (YYYY-MM-DD)
        model: Model name (partial match)
        model_provider: Model provider (partial match)
        status: Session status (complete, aborted, started)
        min_tokens: Minimum total tokens
        max_tokens: Maximum total tokens
        min_duration: Minimum duration in seconds
        max_duration: Maximum duration in seconds
        min_tool_calls: Minimum number of tool calls
        max_tool_calls: Maximum number of tool calls
        limit: Maximum number of results
        order_by: Field to order by
        order_dir: Direction (ASC or DESC)
        
    Returns:
        List of session dictionaries
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Build query
    conditions = []
    params = []
    
    if date_start:
        conditions.append("date >= ?")
        params.append(date_start)
    
    if date_end:
        conditions.append("date <= ?")
        params.append(date_end)
    
    if model:
        conditions.append("model LIKE ?")
        params.append(f"%{model}%")
    
    if model_provider:
        conditions.append("model_provider LIKE ?")
        params.append(f"%{model_provider}%")
    
    if status:
        conditions.append("status = ?")
        params.append(status)
    
    if min_tokens is not None:
        conditions.append("total_tokens >= ?")
        params.append(min_tokens)
    
    if max_tokens is not None:
        conditions.append("total_tokens <= ?")
        params.append(max_tokens)
    
    if min_duration is not None:
        conditions.append("duration_seconds >= ?")
        params.append(min_duration)
    
    if max_duration is not None:
        conditions.append("duration_seconds <= ?")
        params.append(max_duration)
    
    if min_tool_calls is not None:
        conditions.append("tool_calls >= ?")
        params.append(min_tool_calls)
    
    if max_tool_calls is not None:
        conditions.append("tool_calls <= ?")
        params.append(max_tool_calls)
    
    # Validate order_by
    valid_columns = {
        "date", "start_time", "duration_seconds", "total_tokens",
        "tool_calls", "exec_commands", "cli_version"
    }
    if order_by not in valid_columns:
        order_by = "date"
    
    if order_dir not in ("ASC", "DESC"):
        order_dir = "DESC"
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT * FROM sessions
        WHERE {where_clause}
        ORDER BY {order_by} {order_dir}
        LIMIT ?
    """
    params.append(limit)
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    # Convert to list of dicts
    results = []
    for row in rows:
        results.append(dict(row))
    
    return results


def get_stats(db_path: str = None) -> Dict[str, Any]:
    """
    Get overall statistics about indexed sessions.
    
    Args:
        db_path: Path to database file
        
    Returns:
        Dictionary with statistics
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    stats = {}
    
    # Total sessions
    cursor.execute("SELECT COUNT(*) FROM sessions")
    stats["total_sessions"] = cursor.fetchone()[0]
    
    # By status
    cursor.execute("""
        SELECT status, COUNT(*) as count 
        FROM sessions 
        GROUP BY status
    """)
    stats["by_status"] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # By model
    cursor.execute("""
        SELECT model, COUNT(*) as count 
        FROM sessions 
        WHERE model IS NOT NULL
        GROUP BY model
    """)
    stats["by_model"] = {row[0]: row[1] for row in cursor.fetchall()}
    
    # Token stats
    cursor.execute("""
        SELECT 
            SUM(total_tokens) as total,
            AVG(total_tokens) as avg,
            MIN(total_tokens) as min,
            MAX(total_tokens) as max
        FROM sessions
    """)
    row = cursor.fetchone()
    stats["tokens"] = {
        "total": row[0] or 0,
        "average": row[1] or 0,
        "min": row[2] or 0,
        "max": row[3] or 0
    }
    
    # Duration stats
    cursor.execute("""
        SELECT 
            SUM(duration_seconds) as total,
            AVG(duration_seconds) as avg,
            MIN(duration_seconds) as min,
            MAX(duration_seconds) as max
        FROM sessions
        WHERE duration_seconds IS NOT NULL
    """)
    row = cursor.fetchone()
    stats["duration"] = {
        "total_hours": (row[0] or 0) / 3600,
        "average_minutes": (row[1] or 0) / 60,
        "min_seconds": row[2] or 0,
        "max_seconds": row[3] or 0
    }
    
    # Tool call stats
    cursor.execute("""
        SELECT 
            SUM(tool_calls) as total,
            AVG(tool_calls) as avg,
            SUM(exec_commands) as exec_total
        FROM sessions
    """)
    row = cursor.fetchone()
    stats["tool_calls"] = {
        "total": row[0] or 0,
        "average": row[1] or 0,
        "exec_commands": row[2] or 0
    }
    
    # Date range
    cursor.execute("SELECT MIN(date), MAX(date) FROM sessions")
    row = cursor.fetchone()
    stats["date_range"] = {
        "start": row[0],
        "end": row[1]
    }
    
    conn.close()
    return stats


def search_sessions(
    query: str,
    db_path: str = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    Full-text search across sessions.
    
    Args:
        query: Search query
        db_path: Path to database file
        limit: Maximum results
        
    Returns:
        List of matching sessions
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    # Search in session_id, path, model, cli_version
    search_term = f"%{query}%"
    
    cursor.execute("""
        SELECT * FROM sessions
        WHERE session_id LIKE ?
           OR path LIKE ?
           OR model LIKE ?
           OR cli_version LIKE ?
        ORDER BY date DESC
        LIMIT ?
    """, (search_term, search_term, search_term, search_term, limit))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_session_by_id(
    session_id: str,
    db_path: str = None
) -> Optional[Dict[str, Any]]:
    """
    Get a specific session by ID.
    
    Args:
        session_id: Session ID
        db_path: Path to database file
        
    Returns:
        Session dictionary or None
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    
    return dict(row) if row else None


def delete_session(
    session_id: str,
    db_path: str = None
) -> bool:
    """
    Delete a session from the index.
    
    Args:
        session_id: Session ID to delete
        db_path: Path to database file
        
    Returns:
        True if deleted, False if not found
    """
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "build":
            print("Building session index...")
            result = build_index()
            print(f"Done: {result['added']} added, {result['skipped']} skipped, {result['errors']} errors in {result['elapsed_seconds']:.2f}s")
        
        elif command == "stats":
            stats = get_stats()
            print(f"Total sessions: {stats['total_sessions']}")
            print(f"Date range: {stats['date_range']['start']} to {stats['date_range']['end']}")
            print(f"Total tokens: {stats['tokens']['total']:,}")
            print(f"Total duration: {stats['duration']['total_hours']:.1f} hours")
        
        elif command == "query":
            # Example query
            results = query_sessions(limit=10)
            for r in results:
                print(f"{r['date']}: {r['session_id'][:20]}... ({r['total_tokens']} tokens)")
        
        else:
            print(f"Unknown command: {command}")
    else:
        # Default: build index
        print("Building session index...")
        result = build_index()
        print(f"Done: {result['added']} added, {result['skipped']} skipped, {result['errors']} errors in {result['elapsed_seconds']:.2f}s")
