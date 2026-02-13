# Implementation Plan: Plant Profile Database

**Branch**: `002-plant-profile-database` | **Date**: 2026-02-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-plant-profile-database/spec.md`

## Summary

Add SQLite database to store plant-specific profiles with custom names and moisture thresholds, replacing hardcoded plant identifiers. Each profile includes plant name (unique key), acceptable moisture threshold, current moisture level, watering status flag, last watered date, and sensor channel mapping. The monitoring system will read profiles before each cycle and use plant-specific thresholds instead of global defaults. Includes interactive CLI setup script for profile creation and graceful fallback to environment defaults when database is unavailable.

## Technical Context

**Language/Version**: Python 3.9+
**Primary Dependencies**: sqlite3 (stdlib), ADS1x15-ADC (existing), python-dotenv (existing)
**Storage**: SQLite database file in project data directory (`data/plants.db`)
**Testing**: pytest (existing test framework)
**Target Platform**: Raspberry Pi (Linux/Raspberry Pi OS)
**Project Type**: Single embedded IoT monitoring application
**Performance Goals**: Database operations complete within 30s monitoring cycle (target <100ms per profile read/write)
**Constraints**: Must not block sensor readings; graceful degradation when database unavailable
**Scale/Scope**: Maximum 3 plant profiles (limited by 3 hardware sensor channels); single-process access; no concurrent writes

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Test-First (NON-NEGOTIABLE)

**Status**: ✅ COMPLIANT

- All database operations will have contract tests (create profile, read profile, update profile)
- Integration tests for monitoring script database interactions
- CLI setup script will have integration tests for the interactive flow
- Test-first workflow: Write tests for database schema, CRUD operations, fallback behavior before implementation

**Plan**:
1. Write contract tests for database schema creation
2. Write contract tests for CRUD operations (create, read, update plant profiles)
3. Write integration tests for monitoring script database integration
4. Write integration tests for CLI setup script
5. Implement database layer to pass tests
6. Implement CLI setup script to pass tests
7. Integrate with monitoring script

### Principle II: Library-First

**Status**: ✅ COMPLIANT

- Database operations will be in `src/lib/database.py` as a self-contained library
- CLI setup script will be in `src/cli/setup_plants.py` with clear text I/O
- Monitoring integration through existing `src/lib/moisture_monitor.py` (update to load from database)
- Each component independently testable with mock/fake database

**Justification**: Database layer is a reusable library for plant profile management. CLI script follows text I/O protocol (stdin/stdout). No organizational-only modules.

### Principle III: Observability

**Status**: ✅ COMPLIANT

- Structured logging for all database operations (DEBUG level for reads, INFO for writes, ERROR for failures)
- Database file path logged at startup
- Clear error messages for database unavailability, schema validation failures, constraint violations
- CLI setup script provides clear feedback for each operation
- Monitoring script logs profile load status and fallback behavior

**Plan**:
- Use Python `logging` module with consistent levels
- Log database file location at initialization
- Log profile load success/failure with plant names
- Log fallback to environment defaults when database unavailable

### Constitution Violations

**Status**: ✅ NO VIOLATIONS

## Project Structure

### Documentation (this feature)

```text
specs/002-plant-profile-database/
├── spec.md              # Feature specification
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   └── database.yaml    # Database schema and CRUD operation contracts
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Single project structure (existing)
src/
├── models/
│   └── plant_profile.py       # NEW: PlantProfile data class
├── lib/
│   ├── database.py            # NEW: Database operations library
│   ├── moisture_monitor.py    # MODIFIED: Load profiles from database
│   ├── sensor.py              # EXISTING: No changes
│   ├── config.py              # EXISTING: Fallback defaults
│   └── notifier.py            # EXISTING: No changes
└── cli/
    ├── monitor.py             # EXISTING: No changes
    ├── calibrate.py           # EXISTING: No changes
    └── setup_plants.py        # NEW: Interactive profile setup CLI

data/
└── plants.db                  # NEW: SQLite database file (gitignored)

tests/
├── contract/
│   ├── test_database_schema.py           # NEW: Schema contract tests
│   └── test_database_operations.py       # NEW: CRUD contract tests
├── integration/
│   ├── test_monitoring_with_database.py  # NEW: Monitor + DB integration
│   └── test_setup_cli.py                 # NEW: CLI setup integration tests
└── unit/
    └── test_plant_profile_model.py       # NEW: PlantProfile model validation tests
```

**Structure Decision**: Using existing single project structure. New database layer (`src/lib/database.py`) follows library-first pattern. CLI setup script (`src/cli/setup_plants.py`) added alongside existing CLI tools. Database file stored in new `data/` directory at project root (user-writable, no elevated permissions required).

## Complexity Tracking

> **No constitutional violations to justify**

This feature follows all constitutional principles without requiring exceptions. The design is intentionally simple: single library for database operations, straightforward CLI script, and integration with existing monitoring infrastructure.
