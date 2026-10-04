"""
SQLite Database Layer for OTrace.
Provides:
1. Search result caching with TTL.
2. Privacy-first audit logging (storing SHA256 hash of search queries only).
3. Feedback label storage for user interactive training data.
"""
import sqlite3
import json
import hashlib
import time
from typing import Optional, Dict, Any, List
from app.config import DB_PATH, CACHE_TTL_HOURS


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initializes SQLite database schemas."""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Cache table for collector responses
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT NOT NULL,
                created_at REAL NOT NULL,
                ttl_seconds REAL NOT NULL
            )
        """)
        
        # Audit log table (privacy-first: stores SHA256 hash of name only)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_hash TEXT NOT NULL,
                timestamp REAL NOT NULL,
                ip_address TEXT,
                results_count INTEGER
            )
        """)
        
        # Feedback labels table for dataset evaluation/export
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_labels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query_name TEXT NOT NULL,
                candidate_url TEXT NOT NULL,
                candidate_platform TEXT NOT NULL,
                is_same_person INTEGER NOT NULL,
                features_json TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        
        conn.commit()


def get_cache(cache_key: str) -> Optional[Any]:
    """Retrieve cached data if not expired."""
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT response_json, created_at, ttl_seconds FROM cache WHERE cache_key = ?",
            (cache_key,)
        )
        row = cursor.fetchone()
        if row:
            if now - row["created_at"] <= row["ttl_seconds"]:
                return json.loads(row["response_json"])
            else:
                # Expired cache entry
                cursor.execute("DELETE FROM cache WHERE cache_key = ?", (cache_key,))
                conn.commit()
    return None


def set_cache(cache_key: str, data: Any, ttl_seconds: Optional[int] = None):
    """Store data in cache with TTL."""
    if ttl_seconds is None:
        ttl_seconds = CACHE_TTL_HOURS * 3600
    now = time.time()
    json_str = json.dumps(data)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO cache (cache_key, response_json, created_at, ttl_seconds)
            VALUES (?, ?, ?, ?)
        """, (cache_key, json_str, now, ttl_seconds))
        conn.commit()


def log_search_audit(name: str, ip_address: str, results_count: int):
    """Log search audit record with SHA256 hashed name for privacy."""
    name_hash = hashlib.sha256(name.strip().lower().encode("utf-8")).hexdigest()
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_log (name_hash, timestamp, ip_address, results_count)
            VALUES (?, ?, ?, ?)
        """, (name_hash, now, ip_address, results_count))
        conn.commit()


def save_feedback(query_name: str, candidate_url: str, candidate_platform: str, is_same_person: bool, features: Dict[str, Any]):
    """Save user feedback label ('This is them' / 'Not them')."""
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feedback_labels (query_name, candidate_url, candidate_platform, is_same_person, features_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (query_name, candidate_url, candidate_platform, 1 if is_same_person else 0, json.dumps(features), now))
        conn.commit()


def get_all_feedback() -> List[Dict[str, Any]]:
    """Retrieve all feedback labels for evaluation dataset export."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM feedback_labels ORDER BY created_at DESC")
        rows = cursor.fetchall()
        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "query_name": r["query_name"],
                "candidate_url": r["candidate_url"],
                "candidate_platform": r["candidate_platform"],
                "is_same_person": bool(r["is_same_person"]),
                "features": json.loads(r["features_json"]),
                "created_at": r["created_at"]
            })
        return results


def clear_user_data():
    """Clear all cached data, audit logs, and feedback labels for data deletion compliance."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache")
        cursor.execute("DELETE FROM audit_log")
        cursor.execute("DELETE FROM feedback_labels")
        conn.commit()
