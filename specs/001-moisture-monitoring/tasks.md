---
description: "Task list for moisture monitoring and notifications implementation"
---

# Tasks: Moisture Monitoring and Notifications

**Input**: Design documents from `/specs/001-moisture-monitoring/`
**Prerequisites**: plan.md (required), spec.md (required), research.md, data-model.md, contracts/ntfy-api.md

**Tests**: Per constitution (Test-First NON-NEGOTIABLE), contract tests and integration tests MUST be written and approved BEFORE implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root (as defined in plan.md)
- Paths shown below follow single project structure from implementation plan

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure (src/lib/, src/cli/, src/models/, tests/contract/, tests/integration/, tests/unit/, config/)
- [ ] T002 Create requirements.txt with dependencies: adafruit-circuitpython-ads1x15==2.2.23, requests==2.31.0, python-dotenv==1.0.0, pytest==7.4.0
- [ ] T003 [P] Create config/monitor.env.example with all configuration parameters from data-model.md
- [ ] T004 [P] Create .gitignore with Python patterns (\_\_pycache\_\_/, \*.pyc, .env, .pytest_cache/)
- [ ] T005 [P] Create README.md with project overview and setup instructions

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T006 Create src/models/plant.py with Plant dataclass (id, ads_channel, min_moisture_threshold, current_moisture, last_notification_time, needs_water property, throttle_reset_threshold property)
- [ ] T007 [P] Create src/models/sensor_reading.py with SensorReading dataclass (plant_id, timestamp, raw_adc_value, voltage, moisture_percent, is_valid property)
- [ ] T008 [P] Create src/models/notification_event.py with NotificationEvent dataclass (plant_id, timestamp, moisture_percent, message, success, error_message, create_message classmethod)
- [ ] T009 Create src/lib/config.py to load configuration from .env file using python-dotenv (load MOISTURE_THRESHOLD, MOISTURE_VOLTAGE_DRY, MOISTURE_VOLTAGE_WET, SAMPLING_INTERVAL, THROTTLE_DURATION, NTFY_TOPIC, NTFY_URL, LOG_LEVEL, ADS1115_ADDRESS, ADS1115_GAIN)
- [ ] T010 Create src/\_\_init\_\_.py as empty file to make src a package
- [ ] T011 [P] Create src/lib/\_\_init\_\_.py as empty file
- [ ] T012 [P] Create src/models/\_\_init\_\_.py as empty file

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Automatic Watering Alerts (Priority: P1) 🎯 MVP

**Goal**: Send notification to ntfy.sh when a plant's moisture drops below threshold

**Independent Test**: Simulate low moisture on any sensor (e.g., Plant-A at 35%), verify notification received via ntfy.sh within 5 seconds with correct message format "Plant-A needs watering (moisture: 35%)"

### Tests for User Story 1 (Test-First: MUST write and approve BEFORE implementation) ⚠️

> **CONSTITUTION REQUIREMENT**: These tests MUST be written FIRST, verified to FAIL, then approved before writing any implementation code

- [ ] T013 [P] [US1] Contract test for ntfy.sh API in tests/contract/test_ntfy_api.py (mock POST request, verify 200 OK response, test error codes 400/429/500, test retry logic with exponential backoff)
- [ ] T014 [P] [US1] Integration test for single plant notification in tests/integration/test_single_plant_alert.py (create Plant with moisture 35%, verify needs_water=True, mock ntfy.sh POST, verify notification sent with correct message format)

**USER APPROVAL GATE**: Tests T013-T014 must be reviewed and approved before proceeding to T015

### Implementation for User Story 1

- [ ] T015 [US1] Implement ntfy.sh notification client in src/lib/notifier.py (NtfyClient class with send_notification method, HTTP POST to ntfy.sh/{topic}, include Title/Priority/Tags headers, implement retry logic for 429/500 errors with exponential backoff per contracts/ntfy-api.md, timeout=10s, return success dict)
- [ ] T016 [P] [US1] Implement ADS1115 sensor reader in src/lib/sensor.py (SensorReader class, initialize I2C bus with board.SCL/SDA, create ADS1115 object at address 0x48 gain=1, read_channel method returns voltage from channel 0/1/2, handle I2C errors gracefully)
- [ ] T017 [US1] Implement moisture conversion logic in src/lib/sensor.py (voltage_to_moisture method using linear formula from research.md: ((voltage_dry - voltage) / (voltage_dry - voltage_wet)) \* 100.0, validate result in range [-5, 105], clamp to [0, 100] for reporting, return None if outside margin)
- [ ] T018 [US1] Implement basic monitoring loop in src/lib/moisture_monitor.py (MoistureMonitor class, initialize with config, plants list with 3 Plant objects for Plant-A/B/C channels 0/1/2, read_sensors method iterates plants, check_thresholds method compares moisture vs threshold, send_notification method calls NtfyClient if needs_water=True)
- [ ] T019 [US1] Add logging configuration in src/lib/moisture_monitor.py (configure Python logging with level from LOG_LEVEL config, log to both syslog and rotating file /var/log/plant-monitor.log, log format: [TIMESTAMP] [LEVEL] [PLANT_ID] message, INFO: log notifications sent and errors, DEBUG: log all sensor readings and threshold checks)
- [ ] T020 [US1] Create CLI entry point in src/cli/monitor.py (main function, load config from .env, create MoistureMonitor instance, implement graceful shutdown with signal handlers for SIGTERM/SIGINT using GracefulKiller pattern from research.md, main loop with SAMPLING_INTERVAL sleep, handle exceptions without crashing)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently - single plant notifications work

---

## Phase 4: User Story 2 - Multi-Plant Independent Monitoring (Priority: P2)

**Goal**: Monitor all 3 plants independently and send distinct notifications for each plant that needs water

**Independent Test**: Set Plant-A at 35%, Plant-B at 55%, Plant-C at 38%, run monitor for 1 minute, verify exactly 2 notifications sent (Plant-A and Plant-C) with correct plant identifiers in messages

### Tests for User Story 2 (Test-First: MUST write and approve BEFORE implementation) ⚠️

- [ ] T021 [P] [US2] Integration test for multi-plant independent monitoring in tests/integration/test_multi_plant_monitoring.py (create 3 Plants with different moisture levels: A=35%, B=55%, C=38%, mock sensor readings for all channels, verify notifications sent only for A and C with correct plant IDs in message, verify Plant-B notification not sent)
- [ ] T022 [P] [US2] Integration test for all plants dry scenario in tests/integration/test_all_plants_dry.py (set all 3 plants below 40%, verify 3 separate notifications sent within 1 monitoring cycle, verify each notification has correct plant ID and moisture value)

**USER APPROVAL GATE**: Tests T021-T022 must be reviewed and approved before proceeding to T023

### Implementation for User Story 2

- [ ] T023 [US2] Update read_sensors method in src/lib/moisture_monitor.py to iterate all 3 plants (loop through plants list, read each plant's ADS channel, create SensorReading for each, validate each reading independently, update each Plant.current_moisture if valid, log errors per-plant without affecting other plants)
- [ ] T024 [US2] Update check_thresholds method in src/lib/moisture_monitor.py for independent plant checking (iterate all plants, check each plant's needs_water property independently, return list of plants needing water, ensure one plant's state doesn't affect another)
- [ ] T025 [US2] Update send_notification method in src/lib/moisture_monitor.py for per-plant notifications (accept plant parameter, generate message with specific plant ID using NotificationEvent.create_message, send to ntfy.sh with plant ID in message, log success/failure with plant ID, handle each plant's notification independently)

**Checkpoint**: At this point, User Stories 1 AND 2 both work independently - all 3 plants monitored with distinct notifications

---

## Phase 5: User Story 3 - Notification Throttling (Priority: P3)

**Goal**: Prevent notification spam by throttling to maximum once per 6 hours per plant, with throttle reset when plant is watered

**Independent Test**: Keep Plant-A below 40% for 12 hours, verify exactly 2 notifications sent (at 0h and 6h), then water plant (moisture rises to 50%), verify throttle resets and next dry event triggers immediate notification

### Tests for User Story 3 (Test-First: MUST write and approve BEFORE implementation) ⚠️

- [ ] T026 [P] [US3] Integration test for throttle logic in tests/integration/test_throttle_logic.py (send notification for Plant-A at 10:00 AM, keep moisture at 35%, advance time to 3:00 PM, verify no second notification sent, advance to 4:00 PM, verify second notification sent)
- [ ] T027 [P] [US3] Integration test for throttle reset on watering in tests/integration/test_throttle_reset.py (send notification for Plant-A at 10:00 AM, increase moisture to 50% at 11:00 AM, verify throttle reset, drop moisture to 35% again, verify immediate notification sent without waiting 6 hours)
- [ ] T028 [P] [US3] Integration test for independent throttle timers in tests/integration/test_independent_throttles.py (notify Plant-A at 10:00 AM, notify Plant-B at 10:05 AM, keep both dry, verify Plant-A notified again at 4:00 PM, verify Plant-B notified again at 4:05 PM)
- [ ] T029 [P] [US3] Integration test for hysteresis buffer in tests/integration/test_hysteresis_buffer.py (set threshold=40%, test moisture fluctuating 39%-41%, verify notification triggers at <40%, verify throttle only resets when moisture rises above 45% not 40%)

**USER APPROVAL GATE**: Tests T026-T029 must be reviewed and approved before proceeding to T030

### Implementation for User Story 3

- [ ] T030 [US3] Implement throttle checking in send_notification method in src/lib/moisture_monitor.py (before sending notification, check if plant.last_notification_time is None OR time since last notification > THROTTLE_DURATION, if throttled log "Plant-X DRY - throttled, last notified Xmin ago", skip notification, return early)
- [ ] T031 [US3] Implement throttle timer update in send_notification method in src/lib/moisture_monitor.py (after successful notification, update plant.last_notification_time to datetime.utcnow(), log notification sent with plant ID and moisture)
- [ ] T032 [US3] Implement throttle reset logic in check_thresholds method in src/lib/moisture_monitor.py (for each plant, if current_moisture > plant.throttle_reset_threshold (threshold + 5%), reset plant.last_notification_time = None, log "Plant-X OK - throttle reset", this allows immediate notification if plant dries out again)
- [ ] T033 [US3] Add DEBUG logging for throttle decisions in src/lib/moisture_monitor.py (log when throttle prevents notification, log when throttle resets, log time until next notification eligible, include plant ID and moisture level in all throttle logs)

**Checkpoint**: All user stories should now be independently functional - full MVP feature complete

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and production readiness

- [ ] T034 [P] Create pytest configuration in pytest.ini (set testpaths = tests, configure markers for contract/integration/unit tests)
- [ ] T035 [P] Create systemd service file template in config/plant-monitor.service per research.md (Type=simple, User=pi, WorkingDirectory=/home/pi/plant-project, ExecStart=/usr/bin/python3 -u src/cli/monitor.py, Restart=on-failure, RestartSec=5s, KillSignal=SIGTERM, TimeoutStopSec=30, StandardOutput=journal, NoNewPrivileges=true)
- [ ] T036 [P] Add edge case handling for sensor failures in src/lib/moisture_monitor.py (catch I2C errors per sensor, log error with sensor ID and exception, continue monitoring other sensors, track consecutive failures, log critical error if all sensors fail)
- [ ] T037 [P] Add edge case handling for network failures in src/lib/notifier.py (catch requests.Timeout, requests.ConnectionError, log error, return failure dict, will retry on next monitoring cycle per FR-015)
- [ ] T038 [P] Add invalid reading handling in src/lib/sensor.py (if moisture_percent < -5 or > 105, log ERROR with plant ID and voltage/percentage values, set moisture_percent = None, skip updating Plant.current_moisture, continue to next sensor)
- [ ] T039 [P] Create calibration utility in src/cli/monitor.py (add --calibrate-dry flag: read all 3 sensors, average voltage, print "Update MOISTURE_VOLTAGE_DRY=X.XX", add --calibrate-wet flag: read all 3 sensors in water, average voltage, print "Update MOISTURE_VOLTAGE_WET=X.XX")
- [ ] T040 [P] Update README.md with quickstart guide summary (link to specs/001-moisture-monitoring/quickstart.md for full details, include basic hardware setup diagram, installation commands, configuration steps, systemd service setup)
- [ ] T041 Validate all tests pass with pytest (run pytest -v tests/, verify all contract tests pass, verify all integration tests pass, confirm test coverage >80% for core modules)
- [ ] T042 Manual integration test following quickstart.md (set up hardware, run calibration, configure .env, test foreground run, install systemd service, verify 30+ minute continuous run, test all 3 user story scenarios end-to-end)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Polish (Phase 6)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 but can be developed in parallel if US1 code is refactored to support multiple plants
- **User Story 3 (P3)**: Depends on US1 and US2 (needs notification sending to exist) - Adds throttling logic to existing notification flow

### Within Each User Story (Test-First Workflow)

⚠️ **CONSTITUTIONAL REQUIREMENT**: Tests MUST be written FIRST

1. **Write Tests** (RED):
   - Write contract tests and integration tests
   - Run pytest - tests MUST FAIL (no implementation yet)
   - **USER APPROVAL GATE**: Get user approval before implementing

2. **Implement** (GREEN):
   - Write minimal code to make tests pass
   - Run pytest frequently - watch tests turn green
   - Add implementation files in order listed

3. **Refactor** (REFACTOR):
   - Clean up code while keeping tests green
   - Add logging, error handling, edge cases
   - Run pytest to ensure no regressions

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational model files (T006-T008, T011-T012) can run in parallel
- Tests within a user story marked [P] can run in parallel (after previous story's tests approved)
- Polish tasks marked [P] can run in parallel

---

## Parallel Example: User Story 1

```bash
# Step 1: Write tests FIRST (in parallel)
Task T013: Contract test for ntfy.sh API
Task T014: Integration test for single plant alert

# Step 2: Get user approval (tests must FAIL at this point)
# USER REVIEWS AND APPROVES TESTS

# Step 3: Implement (some can be parallel)
Task T015: Implement ntfy.sh client (notifier.py)
Task T016: Implement sensor reader (sensor.py) - can run parallel with T015
Task T017: Add moisture conversion to sensor.py
Task T018: Implement monitoring loop (moisture_monitor.py)
Task T019: Add logging to moisture_monitor.py
Task T020: Create CLI entry point (cli/monitor.py)

# Step 4: Run tests - should all PASS now
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Write tests for User Story 1 (T013-T014) → Get approval
4. Implement User Story 1 (T015-T020)
5. **STOP and VALIDATE**: Test User Story 1 independently
6. Deploy/demo if ready (single plant notifications work!)

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (multi-plant support)
4. Add User Story 3 → Test independently → Deploy/Demo (throttling prevents spam)
5. Add Polish → Final production deployment
6. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (tests then implementation)
   - Developer B: User Story 2 (tests then implementation, may need to wait for US1 API)
   - Developer C: User Story 3 (tests then implementation, needs US1/US2 complete)
3. Stories integrate and test together
4. Team tackles Polish tasks in parallel

---

## Notes

- **[P] tasks** = different files, no dependencies, can run in parallel
- **[Story] label** maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Test-First is NON-NEGOTIABLE**: Verify tests FAIL before implementing
- **User Approval Required**: After writing tests, before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Constitution compliance: All tests written first, library-first structure, structured logging

---

## Test-First Workflow Checklist

For each User Story phase:

1. ✅ Write contract tests (external APIs)
2. ✅ Write integration tests (cross-component)
3. ✅ Run `pytest` - verify tests FAIL (RED)
4. ✅ Get user approval of tests
5. ✅ Implement minimal code (GREEN)
6. ✅ Run `pytest` - verify tests PASS
7. ✅ Refactor while keeping tests green
8. ✅ Commit and move to next story

**Never skip the approval gate** - it's a constitutional requirement.
