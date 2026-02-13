# Implementation Plan: Moisture Monitoring and Notifications

**Branch**: `001-moisture-monitoring` | **Date**: 2026-02-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-moisture-monitoring/spec.md`

## Summary

Implement MVP plant moisture monitoring system that continuously reads soil moisture from 3 capacitive sensors via ADS1115 I2C interface, compares readings against configurable thresholds (default 40%), and sends notifications to ntfy.sh when plants need watering. System includes notification throttling (once per 6 hours per plant), hysteresis buffer (5%) to prevent flapping, and graceful error handling for sensor/network failures. Technical approach: Python 3.9+ with I2C libraries, long-running process with configurable sampling interval (default 30 seconds), structured logging (INFO/DEBUG levels), and in-memory throttle state.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**:
- `adafruit-circuitpython-ads1x15` or `Adafruit_ADS1x15` (ADS1115 I2C interface)
- `smbus2` or `board` + `busio` (I2C communication)
- `requests` (ntfy.sh HTTP API)
- Standard library: `time`, `logging`, `configparser` or `python-dotenv`

**Storage**: In-memory for throttle state; configuration file (INI or .env) for settings; future: SQLite/database for plant profiles
**Testing**: `pytest` for unit tests, integration tests for I2C mocking, contract tests for ntfy.sh API
**Target Platform**: Raspberry Pi 4B running Raspberry Pi OS (Debian-based Linux)
**Project Type**: Single IoT monitoring application (library-first design for reusability)
**Performance Goals**:
- Sensor reading within 60 seconds of moisture change
- Notification delivery within 5 seconds of detection
- 30-second sampling interval (configurable)
- Startup to first reading <30 seconds

**Constraints**:
- I2C bus shared with future BME688 sensor (address 0x76/0x77)
- ADS1115 at I2C address 0x48
- No persistent throttle state (in-memory only, cleared on restart)
- Must run as systemd service (daemonized long-running process)
- Low memory footprint (<50MB typical for Python daemon)

**Scale/Scope**:
- MVP: 3 plants, single user, local deployment
- Future: Web UI, database-backed profiles, BME688 environmental data

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Test-First (NON-NEGOTIABLE)

**Status**: ✅ COMPLIANT (with plan)

- **Requirement**: Tests must be written FIRST before implementation
- **Compliance Plan**:
  - Contract tests for ntfy.sh API (mock HTTP calls)
  - Integration tests for sensor reading logic (mock I2C bus)
  - Red-Green-Refactor cycle enforced during implementation
- **User Approval Required**: Tests must be drafted and approved before implementation begins
- **Test Strategy**: See Phase 1 contracts/ for ntfy.sh API contract; integration tests will verify throttle logic, hysteresis buffer, and error handling

### II. Library-First

**Status**: ✅ COMPLIANT

- **Requirement**: Feature must be modular, self-contained library
- **Compliance Plan**:
  - Core monitoring logic separated into `src/lib/moisture_monitor.py` (reusable library)
  - CLI entry point in `src/cli/monitor.py` (uses library)
  - Clear interfaces: `read_sensors()`, `check_thresholds()`, `send_notification()`
  - Minimal external coupling: I2C and HTTP dependencies injected
  - Future-ready: Database integration via dependency injection (CR-007)

### III. Observability

**Status**: ✅ COMPLIANT

- **Requirement**: Structured logging, debuggability, text I/O
- **Compliance Plan**:
  - Configurable log levels (INFO: notifications/errors; DEBUG: all readings)
  - Structured log format: `[TIMESTAMP] [LEVEL] [PLANT_ID] message` (machine-parseable)
  - Text-based configuration (INI or .env file)
  - Notification messages include context: "Plant-A needs watering (moisture: 35%)"
  - Error messages include sensor ID and invalid values for diagnosis

**Constitution Gate**: ✅ PASSED - All principles satisfied

## Project Structure

### Documentation (this feature)

```text
specs/001-moisture-monitoring/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 research findings
├── data-model.md        # Phase 1 data model
├── quickstart.md        # Phase 1 usage guide
├── contracts/           # Phase 1 API contracts
│   └── ntfy-api.md      # ntfy.sh HTTP API contract
└── tasks.md             # Phase 2 (/speckit.tasks output)
```

### Source Code (repository root)

```text
src/
├── lib/
│   ├── __init__.py
│   ├── moisture_monitor.py    # Core monitoring library
│   ├── sensor.py               # ADS1115 sensor interface
│   ├── notifier.py             # ntfy.sh notification client
│   └── config.py               # Configuration loader
├── cli/
│   └── monitor.py              # CLI entry point (daemonizable)
└── models/
    └── plant.py                # Plant data model (in-memory)

tests/
├── contract/
│   └── test_ntfy_api.py        # ntfy.sh API contract tests
├── integration/
│   ├── test_monitoring_loop.py # Full monitoring cycle
│   └── test_throttle_logic.py  # Throttle + hysteresis tests
└── unit/
    ├── test_sensor.py          # Sensor reading logic (mocked I2C)
    └── test_notifier.py        # Notification logic (mocked HTTP)

config/
└── monitor.env.example         # Example configuration file
```

**Structure Decision**: Single project layout chosen (Option 1 from template). Rationale:
- MVP is a single monitoring daemon, no separate frontend yet
- Library-first design isolates reusable components in `src/lib/`
- Clear separation: `lib/` (reusable), `cli/` (entry point), `models/` (data structures)
- Future web UI will add `web/` directory but won't modify existing structure

## Complexity Tracking

No constitutional violations requiring justification. All principles satisfied by design.

---

## Phase 0: Research (COMPLETE)

**Status**: ✅ All unknowns resolved

**Research Areas**:
1. ✅ ADS1115 Python Library → Decision: adafruit-circuitpython-ads1x15
2. ✅ Sensor Calibration → Decision: Two-point linear calibration (dry/wet)
3. ✅ ntfy.sh API → Decision: requests library with retry logic
4. ✅ Python Daemon → Decision: Simple while loop + systemd (no python-daemon)

**Output**: research.md ([link](./research.md))

---

## Phase 1: Design & Contracts (COMPLETE)

**Status**: ✅ All design artifacts generated

**Artifacts Created**:
1. ✅ data-model.md - Plant, SensorReading, NotificationEvent entities ([link](./data-model.md))
2. ✅ contracts/ntfy-api.md - ntfy.sh HTTP API contract ([link](./contracts/ntfy-api.md))
3. ✅ quickstart.md - User setup and usage guide ([link](./quickstart.md))
4. ✅ CLAUDE.md - Agent context updated with Python 3.9+ stack

**Design Decisions**:
- **Data Storage**: In-memory (no database for MVP)
- **Configuration**: .env file with shared sensor calibration
- **Daemon Architecture**: systemd service with graceful shutdown handling
- **Notification Format**: "Plant-A needs watering (moisture: 35%)" with priority 4
- **Throttle Strategy**: In-memory state, 6-hour window, reset at threshold+5%

**Constitution Re-Check**: ✅ PASSED
- Test-First: Contract tests planned for ntfy.sh API, integration tests for monitoring loop
- Library-First: Core logic in src/lib/, CLI in src/cli/
- Observability: Configurable log levels (INFO/DEBUG), structured logging

---

## Phase 2: Task Generation

**Status**: ⏸️ READY (use `/speckit.tasks` command)

**Prerequisites**: ✅ All complete
- [x] Feature specification (spec.md)
- [x] Implementation plan (plan.md)
- [x] Research findings (research.md)
- [x] Data model (data-model.md)
- [x] API contracts (contracts/ntfy-api.md)
- [x] Quickstart guide (quickstart.md)

**Next Command**: `/speckit.tasks` to generate tasks.md with dependency-ordered implementation tasks
