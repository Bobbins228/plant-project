# Data Model: BME688 Environmental Monitoring

**Date**: 2026-02-13
**Feature**: 003-bme688-environmental

## Overview

This document defines the data models for environmental sensor readings. Environmental data is ephemeral (live display only) and not persisted to the database.

## Entities

### EnvironmentalReading

**Purpose**: Represents a snapshot of environmental conditions at a specific point in time

**Attributes**:

| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `temperature` | `Optional[float]` | -40.0 to 85.0 (sensor range) | Temperature in degrees Celsius, None if read failed |
| `humidity` | `Optional[float]` | 0.0 to 100.0 | Relative humidity as percentage, None if read failed |
| `pressure` | `Optional[float]` | 300.0 to 1100.0 (sensor range) | Atmospheric pressure in hectopascals (hPa), None if read failed |
| `gas_resistance` | `Optional[float]` | ≥ 0.0 | Gas resistance in ohms (Ω), None if read failed |
| `timestamp` | `datetime` | UTC timezone | When the reading was captured |
| `is_valid` | `bool` | Computed property | True if at least one reading succeeded |

**Validation Rules**:

- Temperature out-of-range (< -10°C or > 50°C): Mark with warning flag, do not reject
- Humidity out-of-range (< 0% or > 100%): Sensor limits, should never occur
- Pressure out-of-range (< 900 hPa or > 1100 hPa): Mark with warning flag, do not reject
- Gas resistance: No fixed range - highly variable based on air quality
- If all four readings are None: `is_valid = False`
- If any reading succeeded: `is_valid = True`

**Example Valid Reading**:
```python
EnvironmentalReading(
    temperature=22.45,
    humidity=55.67,
    pressure=1013.25,
    gas_resistance=12345.67,
    timestamp=datetime(2026, 2, 13, 15, 30, 0, tzinfo=timezone.utc),
    is_valid=True
)
```

**Example Partial Failure** (temperature and humidity failed):
```python
EnvironmentalReading(
    temperature=None,
    humidity=None,
    pressure=1013.25,
    gas_resistance=12345.67,
    timestamp=datetime(2026, 2, 13, 15, 30, 5, tzinfo=timezone.utc),
    is_valid=True  # pressure and gas succeeded
)
```

**Example Complete Failure**:
```python
EnvironmentalReading(
    temperature=None,
    humidity=None,
    pressure=None,
    gas_resistance=None,
    timestamp=datetime(2026, 2, 13, 15, 30, 10, tzinfo=timezone.utc),
    is_valid=False
)
```

### Helper Methods

**`format_for_display()`**:
- Returns formatted string for console output
- Format: `"Temp: 22.45°C, Humidity: 55.67%, Pressure: 1013.25 hPa, Gas: 12345.67 Ω"`
- Shows "ERROR" for None values
- Adds "⚠️ OUT OF RANGE" suffix for values outside expected ranges

**`has_out_of_range_values()`**:
- Returns True if any reading is outside expected indoor range
- Expected ranges: temperature -10°C to 50°C, pressure 900-1100 hPa
- Gas resistance and humidity have no "out of range" concept

## Relationships

**None** - EnvironmentalReading is standalone, not related to plant profiles or moisture readings. Environmental data is displayed alongside plant data but stored separately in memory (not in database).

## State Transitions

**None** - EnvironmentalReading is immutable once created. Each monitoring cycle creates a new reading instance.

## Data Volume

**No persistence** - Environmental readings are created, displayed, and discarded each monitoring cycle. Maximum 1 reading per cycle in memory (every 30 seconds default).

## Implementation Notes

- Use Python `dataclass` with `@dataclass` decorator
- All float values formatted to 2 decimal places for display
- Timestamp uses UTC to match existing sensor reading pattern
- `is_valid` property derived from presence of at least one non-None reading
- No database schema changes required (data never stored)
