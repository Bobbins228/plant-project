# Data Model: Plant Profile Database

**Feature**: 002-plant-profile-database
**Date**: 2026-02-13
**Phase**: 1 (Design & Contracts)

## Overview

This document defines the data model for the plant profile database, including the database schema, entity relationships, validation rules, and state transitions.

## Database Schema

### Table: `plant_profiles`

**Purpose**: Store plant-specific configuration and current monitoring state

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS plant_profiles (
    -- Identity & Configuration
    plant_name TEXT PRIMARY KEY,
    sensor_channel INTEGER NOT NULL UNIQUE,
    acceptable_moisture_level REAL NOT NULL,

    -- Current State
    current_moisture_level REAL,
    needs_watering INTEGER NOT NULL DEFAULT 0,
    date_last_watered TEXT,

    -- Constraints
    CHECK (sensor_channel IN (0, 1, 2)),
    CHECK (acceptable_moisture_level >= 0.0 AND acceptable_moisture_level <= 100.0),
    CHECK (current_moisture_level IS NULL OR (current_moisture_level >= 0.0 AND current_moisture_level <= 100.0))
);
```

**Indexes**:
- Primary key index on `plant_name` (automatic)
- Unique index on `sensor_channel` (automatic from UNIQUE constraint)

**Pragmas** (applied at connection initialization):
```sql
PRAGMA foreign_keys = ON;         -- Enforce referential integrity
PRAGMA journal_mode = WAL;        -- Write-ahead logging for concurrency
```

---

## Entity: PlantProfile

### Attributes

| Attribute | Type | Constraints | Description |
|-----------|------|-------------|-------------|
| `plant_name` | TEXT | PRIMARY KEY, NOT NULL | User-defined plant name (e.g., "Basil", "Tomato") |
| `sensor_channel` | INTEGER | UNIQUE, NOT NULL, IN (0,1,2) | ADS1115 ADC channel (0, 1, or 2) monitoring this plant |
| `acceptable_moisture_level` | REAL | NOT NULL, 0.0-100.0 | Moisture threshold percentage for this plant type |
| `current_moisture_level` | REAL | NULLABLE, 0.0-100.0 | Most recent moisture reading percentage |
| `needs_watering` | INTEGER | NOT NULL, DEFAULT 0 | Boolean flag (0=false, 1=true) indicating if plant needs water |
| `date_last_watered` | TEXT | NULLABLE | ISO 8601 date (YYYY-MM-DD) of last watering event |

### Validation Rules

**Schema-Level** (enforced by CHECK constraints):
1. `sensor_channel` must be 0, 1, or 2 (matching ADS1115 channels)
2. `acceptable_moisture_level` must be in range [0.0, 100.0]
3. `current_moisture_level` must be NULL or in range [0.0, 100.0]

**Application-Level** (enforced in Python):
1. `plant_name` must be non-empty and ≤50 characters
2. `plant_name` must be unique (enforced by PRIMARY KEY)
3. `sensor_channel` must be unique per profile (enforced by UNIQUE constraint)
4. `date_last_watered` must be valid ISO 8601 date format if present
5. `needs_watering` must be 0 or 1

**Invariants**:
- Each sensor channel maps to at most one plant profile
- Each plant profile maps to exactly one sensor channel
- Moisture levels are always percentages (0-100 or NULL)

---

## State Transitions

### needs_watering Flag

```
┌─────────────────────────────────────────────────────────────┐
│                     Initial State                           │
│                   needs_watering = 0                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Moisture reading < threshold
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                   DRY State                                 │
│                 needs_watering = 1                          │
│  (Notifications sent, throttle applied)                     │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ Moisture reading >= threshold
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                  WATERED State                              │
│                 needs_watering = 0                          │
│          date_last_watered = today                          │
└─────────────────────────────────────────────────────────────┘
```

**Transitions**:

1. **Initial → DRY**: When `current_moisture_level < acceptable_moisture_level`
   - Set `needs_watering = 1`
   - Log: "Plant {name} needs watering (moisture: {current}% < {threshold}%)"

2. **DRY → WATERED**: When `current_moisture_level >= acceptable_moisture_level`
   - Set `needs_watering = 0`
   - Set `date_last_watered = CURRENT_DATE`
   - Log: "Plant {name} watered (moisture: {current}% >= {threshold}%)"
   - Reset notification throttle timer

3. **WATERED → DRY**: When `current_moisture_level < acceptable_moisture_level` again
   - Set `needs_watering = 1`
   - `date_last_watered` unchanged (preserves history)

---

## Relationships

### One-to-One: PlantProfile ↔ SensorChannel

```
┌─────────────────┐         1:1         ┌──────────────────┐
│  PlantProfile   │────────────────────▶│  Sensor Channel  │
│                 │                     │  (0, 1, or 2)    │
│ - plant_name    │                     │                  │
│ - sensor_channel│◀────────────────────│  ADS1115 ADC     │
└─────────────────┘                     └──────────────────┘
```

**Cardinality**: Each plant profile is monitored by exactly one sensor channel. Each sensor channel monitors at most one plant profile.

**Enforcement**: UNIQUE constraint on `sensor_channel` column

---

## Data Access Patterns

### Read Operations

1. **Load all profiles** (monitoring cycle initialization)
   ```sql
   SELECT * FROM plant_profiles ORDER BY sensor_channel;
   ```
   Frequency: Once per monitoring cycle (every 30s)
   Expected rows: 0-3

2. **Load profile by sensor channel** (during sensor reading)
   ```sql
   SELECT * FROM plant_profiles WHERE sensor_channel = ?;
   ```
   Frequency: 3 times per monitoring cycle
   Expected rows: 0 or 1

3. **Check if sensor channel is mapped**
   ```sql
   SELECT EXISTS(SELECT 1 FROM plant_profiles WHERE sensor_channel = ?) AS is_mapped;
   ```
   Frequency: Once per sensor at startup
   Expected rows: 1 (boolean result)

### Write Operations

1. **Create new profile** (setup CLI)
   ```sql
   INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level, needs_watering)
   VALUES (?, ?, ?, 0);
   ```
   Frequency: Manual (one-time setup)

2. **Update current moisture** (every sensor reading)
   ```sql
   UPDATE plant_profiles
   SET current_moisture_level = ?
   WHERE plant_name = ?;
   ```
   Frequency: 3 times per monitoring cycle

3. **Update watering status** (threshold crossing detection)
   ```sql
   UPDATE plant_profiles
   SET needs_watering = ?
   WHERE plant_name = ?;
   ```
   Frequency: Once per state transition (infrequent)

4. **Record watering event** (moisture rises above threshold)
   ```sql
   UPDATE plant_profiles
   SET needs_watering = 0,
       date_last_watered = ?
   WHERE plant_name = ?;
   ```
   Frequency: Once per actual watering (1-3 times per day)

---

## Python Data Class

**Location**: `src/models/plant_profile.py`

```python
from dataclasses import dataclass
from datetime import date
from typing import Optional


@dataclass
class PlantProfile:
    """Plant profile with configuration and current state.

    Attributes match database schema for easy ORM-free mapping.
    """

    # Identity & Configuration
    plant_name: str
    sensor_channel: int
    acceptable_moisture_level: float

    # Current State
    current_moisture_level: Optional[float] = None
    needs_watering: bool = False
    date_last_watered: Optional[date] = None

    def __post_init__(self):
        """Validate attributes after initialization."""
        # Validate sensor channel
        if self.sensor_channel not in (0, 1, 2):
            raise ValueError(f"sensor_channel must be 0, 1, or 2, got {self.sensor_channel}")

        # Validate acceptable moisture level
        if not 0.0 <= self.acceptable_moisture_level <= 100.0:
            raise ValueError(
                f"acceptable_moisture_level must be 0-100%, got {self.acceptable_moisture_level}"
            )

        # Validate current moisture level if present
        if self.current_moisture_level is not None:
            if not 0.0 <= self.current_moisture_level <= 100.0:
                raise ValueError(
                    f"current_moisture_level must be 0-100% or None, got {self.current_moisture_level}"
                )

        # Validate plant name
        if not self.plant_name or len(self.plant_name) > 50:
            raise ValueError(f"plant_name must be 1-50 characters, got '{self.plant_name}'")

    @classmethod
    def from_db_row(cls, row: dict) -> "PlantProfile":
        """Create PlantProfile from database row (sqlite3.Row as dict)."""
        return cls(
            plant_name=row["plant_name"],
            sensor_channel=row["sensor_channel"],
            acceptable_moisture_level=row["acceptable_moisture_level"],
            current_moisture_level=row["current_moisture_level"],
            needs_watering=bool(row["needs_watering"]),
            date_last_watered=date.fromisoformat(row["date_last_watered"])
                if row["date_last_watered"] else None
        )
```

---

## Migration Strategy

**Version 1.0.0** (initial schema):
- Create table if not exists
- No migrations required (out of scope per A-002)

**Future Considerations** (out of scope):
- Schema versioning (`PRAGMA user_version`)
- Migration scripts for schema changes
- Data export/import for backup/restore

---

## Summary

- **Single table** (`plant_profiles`) with all attributes
- **Primary key** on `plant_name` (user-friendly identifier)
- **Unique constraint** on `sensor_channel` (1:1 mapping enforcement)
- **CHECK constraints** for data validation at schema level
- **Simple state machine** for `needs_watering` flag with clear transitions
- **Python dataclass** mirrors database schema for type safety
