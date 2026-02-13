# Data Model: Moisture Monitoring and Notifications

**Feature**: 001-moisture-monitoring
**Date**: 2026-02-13
**Purpose**: Define in-memory data structures for MVP plant monitoring

## Overview

The MVP uses **in-memory data structures** (no database persistence). State includes:
- Plant configuration (hardcoded, configurable via config file)
- Current sensor readings (volatile, read on each cycle)
- Throttle state (last notification timestamps, cleared on restart)

## Entity Definitions

### Plant

Represents a monitored plant with its configuration and runtime state.

**Attributes**:
- `id` (str): Plant identifier - "Plant-A", "Plant-B", or "Plant-C"
- `ads_channel` (int): ADS1115 ADC channel number (0, 1, or 2)
- `min_moisture_threshold` (float): Minimum acceptable moisture percentage (default: 40.0)
- `current_moisture` (float | None): Most recent moisture reading in percentage (0-100), None if invalid/no reading
- `last_notification_time` (datetime | None): Timestamp of last watering notification sent, None if never notified
- `needs_water` (bool): Derived state - True if current_moisture < min_moisture_threshold

**Validation Rules**:
- `id` must be one of: "Plant-A", "Plant-B", "Plant-C"
- `ads_channel` must be 0, 1, or 2 (maps to ADS1115.P0, P1, P2)
- `min_moisture_threshold` must be 0.0 to 100.0 (typically 20-60%)
- `current_moisture` must be 0.0 to 100.0 if present (invalid readings rejected)

**State Transitions**:
1. **Initial State**: current_moisture=None, last_notification_time=None, needs_water=False
2. **First Reading**: current_moisture updated from sensor
3. **Dry Detection**: If current_moisture < threshold → needs_water=True
4. **Notification Sent**: last_notification_time set to now
5. **Watering Detected**: If current_moisture rises above (threshold + 5% buffer) → needs_water=False, throttle reset
6. **Restart**: last_notification_time=None (throttle cleared), current_moisture=None (re-read sensors)

**Relationships**:
- One Plant has zero-to-many SensorReadings (temporal relationship, readings not persisted in MVP)
- One Plant has zero-to-many NotificationEvents (temporal relationship, events not persisted in MVP)

**In-Memory Representation** (Python):
```python
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Plant:
    """In-memory plant configuration and state"""
    id: str  # "Plant-A", "Plant-B", "Plant-C"
    ads_channel: int  # 0, 1, 2
    min_moisture_threshold: float = 40.0  # percentage
    current_moisture: Optional[float] = None  # percentage or None
    last_notification_time: Optional[datetime] = None

    @property
    def needs_water(self) -> bool:
        """True if current moisture below threshold"""
        if self.current_moisture is None:
            return False
        return self.current_moisture < self.min_moisture_threshold

    @property
    def throttle_reset_threshold(self) -> float:
        """Moisture level that resets throttle timer (threshold + 5%)"""
        return self.min_moisture_threshold + 5.0
```

---

### SensorReading

Represents a single moisture measurement from an ADS1115 channel.

**Attributes**:
- `plant_id` (str): Which plant this reading belongs to ("Plant-A", "Plant-B", "Plant-C")
- `timestamp` (datetime): When the reading was taken (UTC)
- `raw_adc_value` (int): Raw ADC count from ADS1115 (0-32767 for 16-bit resolution)
- `voltage` (float): Converted voltage reading (0.0-4.096V range with gain=1)
- `moisture_percent` (float | None): Converted moisture percentage (0-100), None if conversion failed

**Validation Rules**:
- `raw_adc_value` must be 0 to 32767 (16-bit signed ADC)
- `voltage` must be 0.0 to 4.096 (ADS1115 gain=1 range)
- `moisture_percent` must be 0.0 to 100.0 if present
- Readings with moisture_percent < 0 or > 100 are marked invalid (None)

**Lifecycle**:
1. **Created**: Every monitoring cycle (default: 30 seconds)
2. **Validated**: Check moisture_percent in valid range [0, 100] with ±5% margin
3. **Applied**: Update Plant.current_moisture if valid
4. **Discarded**: Not persisted in MVP (future: store in database for historical trends)

**Conversion Logic**:
```
voltage = (raw_adc_value / 32767) * 4.096  # For gain=1
moisture_percent = ((voltage_dry - voltage) / (voltage_dry - voltage_wet)) * 100.0
# Clamp to [0.0, 100.0] for valid readings
# Set to None if outside [-5.0, 105.0] margin (sensor failure)
```

**In-Memory Representation** (Python):
```python
@dataclass
class SensorReading:
    """Single sensor measurement"""
    plant_id: str
    timestamp: datetime
    raw_adc_value: int
    voltage: float
    moisture_percent: Optional[float]  # None if invalid

    @property
    def is_valid(self) -> bool:
        """True if moisture reading is in valid range"""
        if self.moisture_percent is None:
            return False
        # Allow ±5% margin for sensor variance
        return -5.0 <= self.moisture_percent <= 105.0
```

---

### NotificationEvent

Represents a watering alert sent to ntfy.sh.

**Attributes**:
- `plant_id` (str): Which plant needs watering ("Plant-A", "Plant-B", "Plant-C")
- `timestamp` (datetime): When notification was sent (UTC)
- `moisture_percent` (float): Current moisture level that triggered alert
- `message` (str): Notification message body (e.g., "Plant-A needs watering (moisture: 35%)")
- `success` (bool): True if ntfy.sh API returned 200 OK, False if failed
- `error_message` (str | None): Error details if success=False, None otherwise

**Validation Rules**:
- `moisture_percent` must be 0.0 to 100.0
- `message` must be non-empty string
- `success` and `error_message` are mutually exclusive: if success=True then error_message=None

**Lifecycle**:
1. **Created**: When plant moisture < threshold AND throttle allows (6 hours since last notification)
2. **Sent**: POST to ntfy.sh API with message
3. **Recorded**: Update Plant.last_notification_time if success=True
4. **Logged**: Write to log file (INFO for success, ERROR for failure)
5. **Discarded**: Not persisted in MVP (future: store in database for notification history)

**Message Format** (from clarifications):
```
Title: "Plant Alert"
Body: "{plant_id} needs watering (moisture: {moisture_percent:.0f}%)"
Priority: 4 (high)
Topic: {configured_topic} (default: "mark-test-watering-monitor")
```

**In-Memory Representation** (Python):
```python
@dataclass
class NotificationEvent:
    """Watering notification sent to ntfy.sh"""
    plant_id: str
    timestamp: datetime
    moisture_percent: float
    message: str
    success: bool
    error_message: Optional[str] = None

    @classmethod
    def create_message(cls, plant_id: str, moisture_percent: float) -> str:
        """Generate notification message text"""
        return f"{plant_id} needs watering (moisture: {moisture_percent:.0f}%)"
```

---

## Configuration Model

Configuration loaded from environment variables or .env file (not a runtime entity, but defines system behavior).

**Configuration Parameters**:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `MOISTURE_THRESHOLD` | float | 40.0 | Minimum moisture % (applies to all plants) |
| `MOISTURE_VOLTAGE_DRY` | float | 3.0 | Voltage in air (0% moisture calibration) |
| `MOISTURE_VOLTAGE_WET` | float | 1.6 | Voltage in water (100% moisture calibration) |
| `SAMPLING_INTERVAL` | int | 30 | Seconds between sensor readings |
| `THROTTLE_DURATION` | int | 21600 | Seconds between notifications (6 hours) |
| `NTFY_TOPIC` | str | "mark-test-watering-monitor" | ntfy.sh topic name |
| `NTFY_URL` | str | "https://ntfy.sh" | ntfy.sh base URL |
| `LOG_LEVEL` | str | "INFO" | Log level (INFO or DEBUG) |
| `ADS1115_ADDRESS` | int | 0x48 | I2C address of ADS1115 |
| `ADS1115_GAIN` | int | 1 | Gain setting (1 = ±4.096V) |

**File Format** (config/monitor.env):
```ini
# Plant Monitoring Configuration

# Moisture thresholds
MOISTURE_THRESHOLD=40.0
MOISTURE_VOLTAGE_DRY=3.0
MOISTURE_VOLTAGE_WET=1.6

# Monitoring behavior
SAMPLING_INTERVAL=30
THROTTLE_DURATION=21600

# Notifications
NTFY_TOPIC=mark-test-watering-monitor
NTFY_URL=https://ntfy.sh

# Logging
LOG_LEVEL=INFO

# Hardware
ADS1115_ADDRESS=0x48
ADS1115_GAIN=1
```

---

## Data Flow

```
┌─────────────────────────────────────────────────────────┐
│                  Monitoring Loop (30s)                   │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ 1. Read Sensors (ADS1115 via I2C)                       │
│    - Read voltage from channels 0, 1, 2                 │
│    - Create SensorReading objects                       │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ 2. Convert & Validate                                    │
│    - voltage → moisture_percent (calibration formula)   │
│    - Reject if outside [0, 100] ± margin                │
│    - Log invalid readings (ERROR level)                 │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ 3. Update Plant State                                    │
│    - Update Plant.current_moisture (if valid)           │
│    - Calculate Plant.needs_water property               │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ 4. Check Notification Conditions (per plant)             │
│    - IF needs_water == True                             │
│    - AND (last_notification_time is None OR             │
│           time since last notification > THROTTLE)      │
└───────────────┬─────────────────────────────────────────┘
                │
                ▼ (if conditions met)
┌─────────────────────────────────────────────────────────┐
│ 5. Send Notification                                     │
│    - Create NotificationEvent                           │
│    - POST to ntfy.sh API                                │
│    - Update Plant.last_notification_time (if success)   │
│    - Log notification (INFO or ERROR)                   │
└─────────────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────┐
│ 6. Check Throttle Reset (per plant)                      │
│    - IF current_moisture > (threshold + 5%)             │
│    - THEN reset Plant.last_notification_time = None     │
│    - (Allows immediate notification if moisture drops)  │
└─────────────────────────────────────────────────────────┘
                │
                ▼
         (Sleep 30s, repeat)
```

---

## Future Database Schema (Post-MVP)

When database persistence is added (future feature), entities will map to tables:

**plants table**:
```sql
CREATE TABLE plants (
    id TEXT PRIMARY KEY,  -- "Plant-A", "Plant-B", "Plant-C"
    name TEXT NOT NULL,  -- User-friendly name (e.g., "Basil", "Tomato")
    ads_channel INTEGER NOT NULL,
    min_moisture_threshold REAL NOT NULL DEFAULT 40.0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

**sensor_readings table** (historical data):
```sql
CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_id TEXT NOT NULL REFERENCES plants(id),
    timestamp TIMESTAMP NOT NULL,
    voltage REAL NOT NULL,
    moisture_percent REAL,
    FOREIGN KEY (plant_id) REFERENCES plants(id)
);
CREATE INDEX idx_readings_plant_time ON sensor_readings(plant_id, timestamp DESC);
```

**notification_events table** (notification history):
```sql
CREATE TABLE notification_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plant_id TEXT NOT NULL REFERENCES plants(id),
    timestamp TIMESTAMP NOT NULL,
    moisture_percent REAL NOT NULL,
    message TEXT NOT NULL,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    FOREIGN KEY (plant_id) REFERENCES plants(id)
);
CREATE INDEX idx_notifications_plant_time ON notification_events(plant_id, timestamp DESC);
```

---

## Summary

**MVP Scope**:
- All entities in-memory (no database)
- Configuration from .env file
- State cleared on restart (throttle timers, current readings)
- No historical data retention

**Future Enhancements** (Database Integration):
- Persist plant profiles (custom names, per-plant thresholds)
- Store sensor reading history (charts, trends)
- Store notification log (audit trail)
- Web UI for editing plant profiles
