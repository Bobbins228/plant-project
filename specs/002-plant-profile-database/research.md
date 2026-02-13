# Research: Plant Profile Database

**Feature**: 002-plant-profile-database
**Date**: 2026-02-13
**Phase**: 0 (Outline & Research)

## Overview

This document consolidates technical research for implementing a SQLite-based plant profile database on Raspberry Pi for the plant monitoring system. All unknowns from Technical Context have been resolved.

## Research Areas

### 1. SQLite Database Design for Embedded Systems

**Decision**: Use SQLite3 with single-file database in project data directory

**Rationale**:
- **Zero-configuration**: SQLite requires no server setup, perfect for Raspberry Pi embedded use case
- **File-based**: Single file (`data/plants.db`) is easy to backup, version, and transfer
- **ACID compliant**: Built-in transaction support ensures data integrity even on power loss
- **Python stdlib**: sqlite3 module included in Python 3.9+, no external dependencies
- **Resource-efficient**: Minimal memory footprint (<1MB for our 3-profile use case)

**Alternatives Considered**:
1. **PostgreSQL/MySQL**: Rejected - excessive overhead for 3 profiles; requires server process
2. **JSON file**: Rejected - no ACID guarantees, manual locking required, no schema validation
3. **Pickle file**: Rejected - binary format harms observability, no schema enforcement
4. **CSV file**: Rejected - no concurrent access safety, manual parsing, no data types

**Best Practices Applied**:
- Use `AUTOCOMMIT` mode for single-process write access (no transaction overhead)
- Enable `PRAGMA journal_mode=WAL` for better concurrency (read-while-write)
- Add `PRAGMA foreign_keys=ON` to enforce referential integrity
- Use parameterized queries to prevent SQL injection
- Close connections properly to release file locks

**References**:
- SQLite documentation: https://www.sqlite.org/whentouse.html (embedded devices use case)
- Python sqlite3 module: https://docs.python.org/3/library/sqlite3.html

---

### 2. Python Database Connection Management

**Decision**: Use context manager pattern with connection pooling avoided (single-process access)

**Rationale**:
- **Context managers** (`with` statement) ensure connections are closed even on exceptions
- **No connection pooling**: Single monitoring process makes pooling unnecessary overhead
- **Lazy initialization**: Database connection created on first use, not at import time
- **Graceful degradation**: Catch `sqlite3.Error` and fall back to environment defaults

**Pattern**:
```python
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_db_connection(db_path: str):
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        yield conn
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        raise
    finally:
        if conn:
            conn.close()
```

**Alternatives Considered**:
1. **SQLAlchemy ORM**: Rejected - excessive abstraction for 3 profiles, adds dependency
2. **Global connection**: Rejected - poor testability, harder to mock
3. **Connection pooling**: Rejected - single process doesn't benefit

**Best Practices Applied**:
- Use `sqlite3.Row` for dict-like result access (observability)
- Always use parameterized queries (`?` placeholders)
- Catch specific exceptions (`sqlite3.IntegrityError`, `sqlite3.OperationalError`)
- Log errors with full context (operation, plant name, error message)

---

### 3. Database Schema Design

**Decision**: Single `plant_profiles` table with all attributes, sensor_channel as unique constraint

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS plant_profiles (
    plant_name TEXT PRIMARY KEY,
    sensor_channel INTEGER NOT NULL UNIQUE,
    acceptable_moisture_level REAL NOT NULL,
    current_moisture_level REAL,
    needs_watering INTEGER NOT NULL DEFAULT 0,  -- Boolean as 0/1
    date_last_watered TEXT,  -- ISO 8601 format (YYYY-MM-DD)
    CHECK (sensor_channel IN (0, 1, 2)),
    CHECK (acceptable_moisture_level >= 0.0 AND acceptable_moisture_level <= 100.0),
    CHECK (current_moisture_level IS NULL OR (current_moisture_level >= 0.0 AND current_moisture_level <= 100.0))
);
```

**Rationale**:
- **Primary key on plant_name**: User-friendly identifier, enforces uniqueness
- **Unique constraint on sensor_channel**: Prevents multiple plants assigned to same sensor (FR-014)
- **CHECK constraints**: Schema-level validation for percentage ranges and valid channels
- **REAL type for floats**: Native support for moisture percentages
- **TEXT for dates**: ISO 8601 string format (YYYY-MM-DD) for simplicity and readability
- **INTEGER for boolean**: SQLite doesn't have native boolean, 0/1 is standard pattern

**Alternatives Considered**:
1. **Separate sensor_mapping table**: Rejected - over-normalization for 1:1 relationship
2. **Timestamp instead of date**: Rejected - spec requests DATE format, not datetime
3. **NULL vs 0 for needs_watering**: Rejected - boolean flag should never be NULL

**Index Strategy**:
- No additional indexes needed (only 3 rows, primary key + unique constraint sufficient)

---

### 4. Interactive CLI Design Best Practices

**Decision**: Use Python `input()` with validation loop, clear prompts, confirmation step

**Pattern**:
```python
def prompt_plant_name() -> str:
    """Prompt for plant name with validation."""
    while True:
        name = input("Enter plant name (e.g., Basil, Tomato): ").strip()
        if not name:
            print("❌ Plant name cannot be empty.")
            continue
        if len(name) > 50:
            print("❌ Plant name too long (max 50 characters).")
            continue
        return name
```

**Rationale**:
- **Validation loops**: Retry on invalid input instead of aborting
- **Clear prompts**: Show examples, explain constraints
- **Visual feedback**: Use ✅/❌ symbols for success/error (better UX)
- **Confirmation step**: Show all inputs before saving to database

**Alternatives Considered**:
1. **argparse for CLI args**: Rejected - interactive prompts better for setup wizard
2. **Rich library for TUI**: Rejected - adds dependency, overkill for simple setup
3. **YAML config file**: Rejected - CLI prompts are more user-friendly for initial setup

**Best Practices Applied**:
- Validate input immediately (fail fast)
- Show clear error messages with corrective guidance
- Confirm before writing to database
- Print success message with next steps

---

### 5. Database Write Failure Handling

**Decision**: Log error and continue monitoring without database updates (Option A from clarification)

**Pattern**:
```python
def update_plant_moisture(plant_name: str, moisture: float) -> bool:
    """Update plant moisture level. Returns True on success, False on failure."""
    try:
        with get_db_connection(DB_PATH) as conn:
            conn.execute(
                "UPDATE plant_profiles SET current_moisture_level = ? WHERE plant_name = ?",
                (moisture, plant_name)
            )
            conn.commit()
        return True
    except sqlite3.Error as e:
        logger.error(f"Failed to update moisture for {plant_name}: {e}")
        return False  # Continue monitoring despite DB failure
```

**Rationale**:
- **Non-blocking**: Database failure doesn't stop sensor readings or notifications (FR-017)
- **Graceful degradation**: Monitoring continues with stale profile data
- **Clear logging**: ERROR level for database failures with context
- **Retry on next cycle**: No in-memory queue, simplifies state management

**Alternatives Considered**:
1. **Retry with backoff**: Rejected - adds complexity, may delay monitoring cycle
2. **Halt monitoring**: Rejected - prioritizes historical data over real-time alerts
3. **In-memory queue**: Rejected - complexity, data loss on restart

---

## Implementation Checklist

- [x] SQLite database design researched and validated
- [x] Python connection management pattern selected
- [x] Database schema designed with constraints
- [x] Interactive CLI design pattern chosen
- [x] Error handling strategy defined
- [x] All "NEEDS CLARIFICATION" items from Technical Context resolved

**Status**: ✅ Research complete, ready for Phase 1 (Design & Contracts)
