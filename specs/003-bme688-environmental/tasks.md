# Tasks: BME688 Environmental Monitoring

**Input**: Design documents from `/specs/003-bme688-environmental/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test-First is NON-NEGOTIABLE per project constitution. All tests MUST be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify test directories exist (already created in earlier features)

- [x] T001 Verify tests/contract/ directory exists for contract tests
- [x] T002 [P] Verify tests/integration/ directory exists for integration tests
- [x] T003 [P] Verify tests/unit/ directory exists for unit tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data model that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Components

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T004 [P] Unit test for EnvironmentalReading model validation in tests/unit/test_environmental_reading_model.py
- [x] T005 [P] Unit test for EnvironmentalReading.is_valid property logic in tests/unit/test_environmental_reading_model.py
- [x] T006 [P] Unit test for EnvironmentalReading.format_for_display() method in tests/unit/test_environmental_reading_model.py
- [x] T007 [P] Unit test for EnvironmentalReading.has_out_of_range_values() method in tests/unit/test_environmental_reading_model.py

### Implementation for Foundational Components

- [x] T008 Create EnvironmentalReading dataclass in src/models/environmental_reading.py
- [x] T009 Implement is_valid property (True if any reading not None) in src/models/environmental_reading.py
- [x] T010 Implement format_for_display() method (2 decimal places, ERROR for None, warning for out-of-range) in src/models/environmental_reading.py
- [x] T011 Implement has_out_of_range_values() method (temperature < -10 or > 50, pressure < 900 or > 1100) in src/models/environmental_reading.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View Real-Time Environmental Conditions (Priority: P1) 🎯 MVP

**Goal**: Display temperature, humidity, gas resistance, and atmospheric pressure alongside plant moisture levels during each monitoring cycle, formatted to 2 decimal places

**Independent Test**: Can be fully tested by running the monitoring system with an environmental sensor connected and verifying that temperature, humidity, gas resistance, and pressure readings appear in the monitoring output at each cycle, formatted to 2 decimal places

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T012 [P] [US1] Contract test for EnvironmentalSensorReader initialization in tests/contract/test_environmental_sensor_interface.py
- [ ] T013 [P] [US1] Contract test for EnvironmentalSensorReader.read() successful read in tests/contract/test_environmental_sensor_interface.py
- [ ] T014 [P] [US1] Contract test for EnvironmentalSensorReader.read() timeout handling in tests/contract/test_environmental_sensor_interface.py
- [ ] T015 [P] [US1] Contract test for EnvironmentalSensorReader.read() partial read failure in tests/contract/test_environmental_sensor_interface.py
- [ ] T016 [P] [US1] Contract test for EnvironmentalSensorReader.is_available() method in tests/contract/test_environmental_sensor_interface.py
- [x] T017 [US1] Integration test for monitoring cycle with environmental sensor connected in tests/integration/test_monitoring_with_environmental.py
- [x] T018 [US1] Integration test for environmental data display alongside plant moisture in tests/integration/test_monitoring_with_environmental.py
- [x] T019 [US1] Integration test for environmental readings reflect current conditions in tests/integration/test_monitoring_with_environmental.py
- [x] T020 [US1] Integration test for out-of-range value display with warning indicator in tests/integration/test_monitoring_with_environmental.py

### Implementation for User Story 1

- [x] T021 [US1] Implement EnvironmentalSensorReader class initialization with timeout parameter in src/lib/environmental_sensor.py
- [x] T022 [US1] Configure BME688 sensor (oversampling, filter, gas heater) in src/lib/environmental_sensor.py
- [x] T023 [US1] Implement EnvironmentalSensorReader.read() method with timeout handling in src/lib/environmental_sensor.py
- [x] T024 [US1] Implement EnvironmentalSensorReader.is_available() method in src/lib/environmental_sensor.py
- [x] T025 [US1] Add logging for sensor initialization status in src/lib/environmental_sensor.py
- [x] T026 [US1] Add logging for read timeout and errors in src/lib/environmental_sensor.py
- [x] T027 [US1] Modify MoistureMonitor.__init__() to initialize environmental sensor in src/lib/moisture_monitor.py
- [x] T028 [US1] Modify MoistureMonitor.monitor_cycle() to read environmental sensor after moisture sensors in src/lib/moisture_monitor.py
- [x] T029 [US1] Add environmental reading display logic in src/lib/moisture_monitor.py
- [x] T030 [US1] Update monitor.py CLI to display environmental data in monitoring output in src/cli/monitor.py

**Checkpoint**: At this point, User Story 1 should be fully functional - environmental data displays alongside plant moisture

---

## Phase 4: User Story 2 - Continue Plant Monitoring on Environmental Sensor Failure (Priority: P2)

**Goal**: Ensure plant monitoring continues without interruption even when environmental sensor fails, is disconnected, or encounters errors

**Independent Test**: Can be tested by disconnecting the environmental sensor or simulating sensor errors while the monitoring system runs, and verifying that plant moisture readings and watering notifications continue to function normally with appropriate warnings about environmental sensor status

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T031 [P] [US2] Contract test for sensor not detected during initialization in tests/contract/test_environmental_sensor_interface.py
- [ ] T032 [P] [US2] Contract test for I2C communication error during read in tests/contract/test_environmental_sensor_interface.py
- [x] T033 [US2] Integration test for plant monitoring continues when environmental sensor disconnected in tests/integration/test_monitoring_with_environmental.py
- [x] T034 [US2] Integration test for error logging when environmental sensor fails in tests/integration/test_monitoring_with_environmental.py
- [x] T035 [US2] Integration test for plant moisture display when environmental sensor unavailable in tests/integration/test_monitoring_with_environmental.py

### Implementation for User Story 2

- [x] T036 [US2] Add IOError exception handling in EnvironmentalSensorReader.read() in src/lib/environmental_sensor.py
- [x] T037 [US2] Return invalid EnvironmentalReading (all None) on sensor not detected in src/lib/environmental_sensor.py
- [x] T038 [US2] Ensure no exceptions raised from EnvironmentalSensorReader methods in src/lib/environmental_sensor.py
- [x] T039 [US2] Add try-except wrapper for environmental sensor read in monitor_cycle() in src/lib/moisture_monitor.py
- [x] T040 [US2] Log warning when environmental sensor unavailable and continue monitoring in src/lib/moisture_monitor.py
- [x] T041 [US2] Display "UNAVAILABLE" or "ERROR" when environmental reading fails in src/lib/moisture_monitor.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - environmental data displays when available, plant monitoring continues when environmental sensor fails

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, validation, and final checks

- [x] T042 [P] Add bme680 dependency to project requirements/dependencies file
- [x] T043 [P] Verify sequential sensor reading (moisture → environmental) prevents I2C bus conflicts
- [x] T044 Verify all environmental values formatted to exactly 2 decimal places
- [x] T045 Verify out-of-range values display with ⚠️ warning indicator
- [x] T046 Verify partial sensor failures display successful readings with ERROR for failed ones
- [x] T047 Verify environmental sensor timeout logged and monitoring continues
- [x] T048 Update quickstart.md with actual sensor wiring diagram if needed
- [x] T049 Validate monitoring startup logs show environmental sensor initialization status

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately (directories already exist)
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Can start after Phase 2
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 - Can start after Phase 3 (US2 adds failure handling to US1 components)
- **Polish (Phase 5)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundation (Phase 2) - BLOCKS ALL STORIES
    ↓
    └─→ US1 (Phase 3) - View Real-Time Environmental Conditions
            ↓
            └─→ US2 (Phase 4) - Continue on Sensor Failure (extends US1 with error handling)
```

**Critical Path**: Foundation → US1 → US2

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Test-First principle)
- Contract tests before implementation
- Integration tests before implementation
- Unit tests before implementation
- Model implementation before sensor reader implementation
- Sensor reader implementation before monitoring integration
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks T001-T003 can run in parallel

**Phase 2 (Foundational Tests)**: All tests T004-T007 can run in parallel

**Phase 3 (US1 Tests)**: Contract tests T012-T016 can run in parallel

**Phase 3 (US1 Implementation)**: T021-T026 can run in parallel (all in environmental_sensor.py)

**Phase 4 (US2 Tests)**: T031-T032 can run in parallel (contract tests), T033-T035 can run in parallel (integration tests)

**Phase 5 (Polish)**: T042-T043 can run in parallel

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (verify directories)
2. Complete Phase 2: Foundational (EnvironmentalReading model with tests)
3. Complete Phase 3: User Story 1 (environmental sensor reading and display)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Connect BME688 sensor to Raspberry Pi
   - Run monitoring system
   - Verify environmental data displays alongside plant moisture
   - Verify 2 decimal place formatting
5. Deploy/demo if ready - users can now see environmental conditions

### Incremental Delivery

1. **Foundation** (Phase 1 + 2) → EnvironmentalReading model ready
2. **+ User Story 1** (Phase 3) → Test independently → Deploy/Demo (**MVP!**)
   - Environmental data displays in real-time
3. **+ User Story 2** (Phase 4) → Test independently → Deploy/Demo
   - System resilient to environmental sensor failures
4. **Polish** (Phase 5) → Final validation → Full release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Foundation together** (Phase 1 + 2)
2. **Once Foundational is done**:
   - Developer A: User Story 1 (Phase 3) - Environmental sensor reading and display
3. **After US1 completes**:
   - Developer A or B: User Story 2 (Phase 4) - Failure handling
4. **Polish together** (Phase 5)

Stories complete and integrate independently.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Test-First is mandatory**: Verify tests fail (RED) before implementing (GREEN)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Environmental sensor failures must not block plant monitoring (FR-007)
- Sequential sensor reading prevents I2C bus conflicts (FR-012)
- Timeout handling prevents delayed monitoring cycles (FR-013)
