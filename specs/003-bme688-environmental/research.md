# Research: BME688 Environmental Monitoring

**Date**: 2026-02-13
**Feature**: 003-bme688-environmental

## Overview

This document captures technical research and decisions for integrating BME688 environmental sensor monitoring into the existing plant monitoring system.

## Research Questions

### Q1: BME680 Library Selection and API Usage

**Decision**: Use `bme680` Python package (Pimoroni library)

**Rationale**:
- Well-maintained library specifically for BME680/BME688 sensors
- Native Python support with simple API
- Handles I2C communication, sensor configuration, and data reading
- Supports forced mode for one-shot readings (ideal for periodic monitoring)
- Returns calibrated values for temperature, humidity, pressure, and gas resistance

**API Pattern**:
```python
import bme680
sensor = bme680.BME680(bme680.I2C_ADDR_PRIMARY)  # or I2C_ADDR_SECONDARY
sensor.set_temperature_oversample(bme680.OS_8X)
sensor.set_humidity_oversample(bme680.OS_2X)
sensor.set_pressure_oversample(bme680.OS_4X)
sensor.set_filter(bme680.FILTER_SIZE_3)

if sensor.get_sensor_data():
    temp = sensor.data.temperature
    humidity = sensor.data.humidity
    pressure = sensor.data.pressure
    gas = sensor.data.gas_resistance
```

**Alternatives Considered**:
- **Adafruit CircuitPython BME680**: More complex setup, requires CircuitPython environment
- **Direct I2C communication**: Would require implementing sensor calibration and data processing - significant complexity
- **REJECTED**: Both alternatives add unnecessary complexity for a straightforward sensor reading task

### Q2: I2C Bus Sharing Strategy

**Decision**: Sequential sensor reading with explicit ordering (moisture sensors → environmental sensor)

**Rationale**:
- Prevents I2C bus conflicts by ensuring only one sensor communicates at a time
- Simple to implement and debug - no locking or arbitration needed
- Moisture sensor reading already established, environmental sensor added after
- Performance impact negligible (environmental reading ~50-100ms total)

**Implementation Pattern**:
1. Read all moisture sensors (ADS1115 channels 0, 1, 2)
2. Wait for moisture reads to complete
3. Read environmental sensor (BME688)
4. Display combined results

**Alternatives Considered**:
- **Concurrent reading with I2C locking**: Complex, error-prone, no performance benefit for 30-second monitoring cycles
- **Environmental sensor first**: No technical advantage, would disrupt existing moisture sensor reading logic
- **REJECTED**: Added complexity without benefit

### Q3: Timeout and Error Handling Strategy

**Decision**: Implement timeout with skip-on-failure approach

**Timeout Threshold**: 2 seconds for environmental sensor read

**Rationale**:
- BME688 forced mode reading typically completes in 50-100ms
- 2-second timeout provides 20x margin for I2C delays, sensor warm-up
- Timeout prevents hung sensor from blocking plant monitoring
- Skip-on-failure ensures plant monitoring continues (environmental data is supplementary)

**Error Handling Pattern**:
```python
try:
    with timeout(2.0):
        reading = environmental_sensor.read()
except TimeoutError:
    logger.warning("Environmental sensor read timeout - skipping this cycle")
    reading = None
except IOError as e:
    logger.error(f"Environmental sensor I/O error: {e}")
    reading = None
```

**Alternatives Considered**:
- **Retry on failure**: Delays monitoring cycle, unlikely to succeed if first attempt fails
- **Indefinite wait**: Violates constraint to avoid delaying plant monitoring
- **REJECTED**: Both alternatives risk disrupting core plant monitoring function

### Q4: Sensor Initialization and Warm-up

**Decision**: Initialize sensor at system startup with basic configuration, no warm-up delay required

**Initialization Sequence**:
1. Detect sensor presence on I2C bus (address 0x76 or 0x77)
2. Configure oversampling rates (temperature: 8x, humidity: 2x, pressure: 4x)
3. Set filter size to 3 for noise reduction
4. Set gas heater (300°C for 150ms) - required for gas resistance reading
5. Log initialization success/failure

**Warm-up Behavior**:
- No warm-up delay at startup (sensor ready immediately in forced mode)
- First reading may show inaccurate gas resistance - acceptable for live display
- Gas resistance stabilizes after 2-3 readings (~1-2 minutes in 30-second cycles)

**Rationale**:
- BME688 forced mode designed for low-power periodic readings
- Forced mode performs sensor reading on-demand (no continuous operation)
- No warm-up delay keeps system startup fast
- First reading accuracy sufficient for live monitoring (not recording data)

**Alternatives Considered**:
- **Continuous mode with always-on sensor**: Higher power consumption, unnecessary for 30-second intervals
- **30-second warm-up at startup**: Delays monitoring start, no significant benefit
- **REJECTED**: Forced mode with on-demand readings is optimal for this use case

### Q5: Out-of-Range Value Validation

**Decision**: Display out-of-range values with warning indicator, do not reject

**Range Checking**:
- Temperature: -10°C to 50°C (typical indoor range)
- Humidity: 0% to 100% (sensor physical limits)
- Pressure: 900 hPa to 1100 hPa (sea level to high altitude)
- Gas Resistance: 0 Ω to 10,000,000 Ω (no fixed range - highly variable)

**Display Pattern**:
```
Temperature: 55.23°C ⚠️ OUT OF RANGE
Humidity: 45.67%
Pressure: 1013.25 hPa
Gas Resistance: 12345.67 Ω
```

**Rationale**:
- Out-of-range values may indicate actual environmental conditions (extreme heat, altitude)
- Warning indicator alerts user to unusual values without hiding data
- Gas resistance has no fixed range - depends on air quality, volatile compounds
- Users should see actual sensor readings for diagnostic purposes

**Alternatives Considered**:
- **Reject out-of-range readings**: Hides potentially valid data from unusual conditions
- **No warning indicator**: Users may not notice unusual values
- **REJECTED**: Displaying with warning provides maximum information and awareness

## Technical Decisions Summary

| Decision Area | Choice | Key Rationale |
|---------------|--------|---------------|
| Python Library | bme680 (Pimoroni) | Simple API, handles calibration, well-maintained |
| I2C Bus Sharing | Sequential reads (moisture → environmental) | Prevents conflicts, simple implementation |
| Timeout Threshold | 2 seconds | 20x typical read time, prevents hung sensor |
| Error Handling | Skip on failure, continue plant monitoring | Environmental data supplementary, not critical |
| Sensor Mode | Forced mode (on-demand reads) | Low power, ideal for periodic monitoring |
| Initialization | At startup, no warm-up delay | Fast startup, forced mode ready immediately |
| Out-of-Range Values | Display with warning indicator | Maximum information, user awareness |

## Dependencies

**New Dependency**: `bme680` Python package
- Install: `pip install bme680` or `uv pip install bme680`
- License: MIT
- Repository: https://github.com/pimoroni/bme680-python
- Version: Latest stable (1.x)

**Existing Dependencies** (no changes):
- ADS1x15-ADC (moisture sensors)
- ntfy.sh client (notifications)
- SQLite (plant profiles)

## Integration Points

**Modified Components**:
1. `src/lib/moisture_monitor.py`: Add environmental sensor reading to monitoring cycle
2. `src/cli/monitor.py`: Display environmental data in monitoring output

**New Components**:
1. `src/lib/environmental_sensor.py`: BME688 sensor reader library
2. `src/models/environmental_reading.py`: Environmental data model

**No Changes Required**:
- Database schema (environmental data not stored)
- Configuration (no new config parameters needed)
- Notification system (environmental data informational only)
- Plant profile setup (independent of environmental monitoring)
