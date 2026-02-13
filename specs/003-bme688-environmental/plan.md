# Implementation Plan: BME688 Environmental Monitoring

**Branch**: `003-bme688-environmental` | **Date**: 2026-02-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-bme688-environmental/spec.md`

## Summary

Add real-time environmental monitoring (temperature, humidity, gas resistance, atmospheric pressure) from a BME688 sensor to the existing plant monitoring system. Environmental data will be displayed alongside plant moisture levels during each monitoring cycle, formatted to 2 decimal places. The system will use sequential I2C bus access (moisture sensors first, then environmental sensor) to prevent conflicts, with graceful degradation ensuring plant monitoring continues even if the environmental sensor fails.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: bme680 (environmental sensor library), existing dependencies (ADS1x15-ADC for moisture sensors)
**Storage**: None (environmental data is live/ephemeral only, existing SQLite for plant profiles unchanged)
**Testing**: pytest (existing test infrastructure)
**Target Platform**: Raspberry Pi (same as existing system)
**Project Type**: Single project (extending existing plant monitoring system)
**Performance Goals**: Environmental sensor reading must complete within timeout threshold (2 seconds) to avoid delaying monitoring cycles
**Constraints**: Sequential I2C bus access required (moisture sensors → environmental sensor), timeout handling mandatory, graceful degradation on sensor failures
**Scale/Scope**: Single environmental sensor reading per monitoring cycle (every 30 seconds by default), 4 environmental metrics displayed

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Test-First (NON-NEGOTIABLE)

**Status**: ✅ PASS

- Tests will be written FIRST before implementation
- Contract tests for sensor reading interface
- Integration tests for monitoring cycle with environmental data
- Unit tests for environmental reading data model

**Justification**: Standard test-first workflow applies. Contract tests verify sensor communication interface, integration tests verify environmental data appears in monitoring output without disrupting plant monitoring.

### II. Library-First

**Status**: ✅ PASS

- Environmental sensor reading will be implemented as a modular library component (`src/lib/environmental_sensor.py`)
- Clear interface: `EnvironmentalSensorReader` class with `read()` method returning `EnvironmentalReading`
- Self-contained with timeout handling and error management
- Independently testable without requiring physical hardware (mock sensor for dev)

**Justification**: Library-first approach enables testing without hardware, clear separation of concerns, and potential reuse in other monitoring contexts.

### III. Observability

**Status**: ✅ PASS

- Structured logging for sensor initialization, reading success/failure, timeouts
- Environmental data displayed in text format alongside plant moisture levels
- Error messages include sensor status (not detected, timeout, partial failure, out-of-range)
- Clear distinction between plant monitoring errors and environmental sensor errors

**Justification**: Observability critical for diagnosing I2C bus issues, sensor failures, and understanding why environmental data may be missing.

## Project Structure

### Documentation (this feature)

```text
specs/003-bme688-environmental/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── models/
│   ├── plant.py                      # Existing
│   ├── plant_profile.py              # Existing
│   ├── sensor_reading.py             # Existing
│   ├── notification_event.py         # Existing
│   └── environmental_reading.py      # NEW - Environmental data model
├── lib/
│   ├── sensor.py                     # Existing - Moisture sensor (ADS1115)
│   ├── environmental_sensor.py       # NEW - BME688 sensor reader
│   ├── moisture_monitor.py           # MODIFY - Add environmental reading
│   ├── database.py                   # Existing - No changes
│   ├── config.py                     # Existing - No changes
│   └── notifier.py                   # Existing - No changes
└── cli/
    ├── monitor.py                    # MODIFY - Display environmental data
    ├── calibrate.py                  # Existing - No changes
    └── setup_plants.py               # Existing - No changes

tests/
├── contract/
│   ├── test_environmental_sensor_interface.py  # NEW - Sensor contract tests
│   └── [existing test files]
├── integration/
│   ├── test_monitoring_with_environmental.py   # NEW - Full monitoring cycle tests
│   └── [existing test files]
└── unit/
    ├── test_environmental_reading_model.py     # NEW - Data model tests
    └── [existing test files]
```

**Structure Decision**: Single project structure (existing). This feature extends the current monitoring system by adding a new sensor reader library and data model. No architectural changes required - environmental sensor reading fits naturally into the existing monitoring cycle workflow.

## Complexity Tracking

No constitutional violations - all principles satisfied without justification needed.
