# Tasks: Plant Profile Database

**Input**: Design documents from `/specs/002-plant-profile-database/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Test-First is NON-NEGOTIABLE per project constitution. All tests MUST be written and FAIL before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths assume single project structure per plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and directory structure

- [x] T001 Create data/ directory for SQLite database storage
- [x] T002 [P] Add data/*.db to .gitignore to exclude database files from version control
- [x] T003 [P] Create src/models/ directory if it doesn't exist
- [x] T004 [P] Create tests/contract/ directory for database contract tests
- [x] T005 [P] Create tests/integration/ directory for integration tests
- [x] T006 [P] Create tests/unit/ directory for unit tests

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Components

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T007 [P] Contract test for database schema creation in tests/contract/test_database_schema.py
- [x] T008 [P] Contract test for database initialization (table creation, pragmas) in tests/contract/test_database_schema.py
- [x] T009 [P] Unit test for PlantProfile model validation (sensor_channel, moisture levels, plant_name) in tests/unit/test_plant_profile_model.py
- [x] T010 [P] Unit test for PlantProfile.from_db_row() method in tests/unit/test_plant_profile_model.py

### Implementation for Foundational Components

- [x] T011 [P] Create PlantProfile data class with validation in src/models/plant_profile.py
- [x] T012 Create database library with connection management in src/lib/database.py
- [x] T013 Implement initialize_database() function (schema creation, pragmas) in src/lib/database.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Store Individual Plant Profiles (Priority: P1) 🎯 MVP

**Goal**: Enable users to create and persist plant profiles with custom names and moisture thresholds using an interactive CLI setup script

**Independent Test**: Can be fully tested by creating plant profiles with different names and thresholds, then verifying the data persists across system restarts

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T014 [P] [US1] Contract test for create_plant_profile operation (valid data) in tests/contract/test_database_operations.py
- [x] T015 [P] [US1] Contract test for duplicate plant name error handling in tests/contract/test_database_operations.py
- [x] T016 [P] [US1] Contract test for duplicate sensor channel error handling in tests/contract/test_database_operations.py
- [x] T017 [P] [US1] Contract test for load_all_profiles operation in tests/contract/test_database_operations.py
- [x] T018 [US1] Integration test for CLI setup script (profile creation flow) in tests/integration/test_setup_cli.py
- [x] T019 [US1] Integration test for CLI input validation (empty name, long name, invalid threshold) in tests/integration/test_setup_cli.py
- [x] T020 [US1] Integration test for profile persistence across database reconnections in tests/integration/test_setup_cli.py

### Implementation for User Story 1

- [x] T021 [US1] Implement create_plant_profile() function in src/lib/database.py
- [x] T022 [US1] Implement load_all_profiles() function returning List[PlantProfile] in src/lib/database.py
- [x] T023 [US1] Implement prompt_plant_name() with validation (non-empty, ≤50 chars) in src/cli/setup_plants.py
- [x] T024 [US1] Implement prompt_sensor_channel() with validation (0, 1, 2, not already assigned) in src/cli/setup_plants.py
- [x] T025 [US1] Implement prompt_moisture_threshold() with validation (0-100%) in src/cli/setup_plants.py
- [x] T026 [US1] Implement main() setup wizard loop (create profile, confirm, repeat) in src/cli/setup_plants.py
- [x] T027 [US1] Add error handling for database constraints (duplicate name, duplicate channel) in src/cli/setup_plants.py
- [x] T028 [US1] Add logging for profile creation success/failure in src/cli/setup_plants.py

**Checkpoint**: At this point, User Story 1 should be fully functional - users can create and persist plant profiles independently

---

## Phase 4: User Story 4 - Map Sensors to Named Plants (Priority: P2)

**Goal**: Associate each moisture sensor channel with a specific plant profile by name so notifications and logs display actual plant names instead of generic labels

**Independent Test**: Can be tested by configuring sensor channel 0 to monitor "Tomato" and channel 1 to monitor "Basil", then verifying load operations return correct plant names

**Note**: This phase adds sensor-to-plant lookup functionality needed by monitoring (US2)

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T029 [P] [US4] Contract test for load_profile_by_channel operation (existing profile) in tests/contract/test_database_operations.py
- [x] T030 [P] [US4] Contract test for load_profile_by_channel operation (unmapped channel returns None) in tests/contract/test_database_operations.py
- [x] T031 [US4] Integration test for sensor-to-plant mapping (create profiles, load by channel) in tests/integration/test_database_sensor_mapping.py

### Implementation for User Story 4

- [x] T032 [US4] Implement load_profile_by_channel() function returning Optional[PlantProfile] in src/lib/database.py
- [x] T033 [US4] Add logging for unmapped sensor channels (warn at startup) in src/lib/database.py

**Checkpoint**: At this point, sensor channels can be mapped to plant names for monitoring integration

---

## Phase 5: User Story 2 - Monitor Plants Using Custom Thresholds (Priority: P2)

**Goal**: Integrate database profiles with monitoring system so each plant is evaluated against its own threshold instead of a global default

**Independent Test**: Can be tested by setting up plants with different thresholds (cactus at 20%, fern at 60%), letting moisture levels drop, and verifying alerts are sent at the correct thresholds

**Note**: Depends on US4 (sensor mapping) to load profiles by sensor channel

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T034 [P] [US2] Contract test for update_current_moisture operation in tests/contract/test_database_operations.py
- [x] T035 [P] [US2] Contract test for set_needs_watering_flag operation in tests/contract/test_database_operations.py
- [x] T036 [US2] Integration test for monitoring cycle with database profiles (load profiles, check thresholds) in tests/integration/test_monitoring_with_database.py
- [x] T037 [US2] Integration test for fallback to environment defaults when database unavailable in tests/integration/test_monitoring_with_database.py
- [x] T038 [US2] Integration test for database write failure during monitoring (continue without updates) in tests/integration/test_monitoring_with_database.py

### Implementation for User Story 2

- [x] T039 [US2] Implement update_current_moisture() function in src/lib/database.py
- [x] T040 [US2] Implement set_needs_watering_flag() function in src/lib/database.py
- [x] T041 [US2] Modify MoistureMonitor.__init__() to load plant profiles from database in src/lib/moisture_monitor.py
- [x] T042 [US2] Update MoistureMonitor.read_sensors() to update current_moisture in database in src/lib/moisture_monitor.py
- [x] T043 [US2] Update MoistureMonitor.check_thresholds() to use plant-specific thresholds and update needs_watering flag in src/lib/moisture_monitor.py
- [x] T044 [US2] Add database unavailable fallback logic (use environment defaults) in src/lib/moisture_monitor.py
- [x] T045 [US2] Add database write failure handling (log error, continue monitoring) in src/lib/moisture_monitor.py
- [x] T046 [US2] Update notification messages to use plant names from profiles in src/lib/moisture_monitor.py
- [x] T047 [US2] Update logging to show plant names instead of generic labels in src/lib/moisture_monitor.py

**Checkpoint**: At this point, monitoring system uses plant-specific thresholds and displays custom plant names

---

## Phase 6: User Story 3 - Track Watering History (Priority: P3)

**Goal**: Automatically detect and record watering events (moisture rising above threshold) by updating date_last_watered field

**Independent Test**: Can be tested by watering a dry plant and verifying the date-last-watered field updates to today's date when moisture rises above the threshold

**Note**: Builds on US2 (monitoring with custom thresholds) to detect threshold crossings

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T048 [P] [US3] Contract test for record_watering_event operation in tests/contract/test_database_operations.py
- [x] T049 [US3] Integration test for watering event detection (moisture below → above threshold) in tests/integration/test_watering_history.py
- [x] T050 [US3] Integration test for date_last_watered not updating when moisture stays below threshold in tests/integration/test_watering_history.py

### Implementation for User Story 3

- [x] T051 [US3] Implement record_watering_event() function in src/lib/database.py
- [x] T052 [US3] Update MoistureMonitor.check_thresholds() to detect threshold crossings (dry → watered transition) in src/lib/moisture_monitor.py
- [x] T053 [US3] Call record_watering_event() when moisture rises above threshold in src/lib/moisture_monitor.py
- [x] T054 [US3] Add logging for watering event detection (plant name, date) in src/lib/moisture_monitor.py

**Checkpoint**: All user stories should now be independently functional - full feature complete

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories and final validation

- [x] T055 [P] Update quickstart.md examples to reflect actual CLI prompts and database operations
- [x] T056 [P] Add data/ directory creation to project setup documentation
- [x] T057 Verify all logging uses consistent levels (DEBUG for reads, INFO for writes, ERROR for failures)
- [x] T058 Add database file location logging at monitoring startup
- [ ] T059 Run full integration test suite to verify all user stories work together (REQUIRES RASPBERRY PI)
- [ ] T060 Validate quickstart.md setup workflow on clean Raspberry Pi environment (MANUAL VALIDATION)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational phase - Can start after Phase 2
- **User Story 4 (Phase 4)**: Depends on Foundational phase - Can start after Phase 2 (parallel with US1)
- **User Story 2 (Phase 5)**: Depends on Foundational + US4 (needs sensor mapping) - Can start after Phase 4
- **User Story 3 (Phase 6)**: Depends on Foundational + US2 (needs monitoring integration) - Can start after Phase 5
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundation (Phase 2) - BLOCKS ALL STORIES
    ↓
    ├─→ US1 (Phase 3) - Independent, no story dependencies
    │
    ├─→ US4 (Phase 4) - Independent, no story dependencies
    │       ↓
    │       └─→ US2 (Phase 5) - Depends on US4 (sensor mapping)
    │               ↓
    │               └─→ US3 (Phase 6) - Depends on US2 (monitoring integration)
```

**Critical Path**: Foundation → US4 → US2 → US3
**Parallel Path**: US1 can be developed independently alongside US4

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Test-First principle)
- Contract tests before implementation
- Integration tests before implementation
- Database functions before monitoring integration
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks T001-T006 can run in parallel

**Phase 2 (Foundational Tests)**: All tests T007-T010 can run in parallel

**Phase 2 (Foundational Implementation)**: T011 can run parallel with T012-T013

**Phase 3 (US1 Tests)**: T014-T017 can run in parallel, T018-T020 can run after

**Phase 3 (US1 Implementation)**: T023-T025 can run in parallel after T021-T022

**Phase 4 (US4 Tests)**: T029-T030 can run in parallel

**Phase 5 (US2 Tests)**: T034-T035 can run in parallel

**Phase 6 (US3 Tests)**: T048-T050 can run in parallel

**Phase 7 (Polish)**: T055-T056 can run in parallel, T057-T058 can run in parallel

**Cross-Story Parallelization**:
- After Phase 2 completes: US1 (Phase 3) and US4 (Phase 4) can start in parallel
- Different developers can work on US1 and US4 simultaneously

---

## Parallel Example: User Story 1

```bash
# Launch all contract tests for User Story 1 together:
Task: "Contract test for create_plant_profile operation (valid data)"
Task: "Contract test for duplicate plant name error handling"
Task: "Contract test for duplicate sensor channel error handling"
Task: "Contract test for load_all_profiles operation"

# After database functions implemented, launch CLI prompts in parallel:
Task: "Implement prompt_plant_name() with validation"
Task: "Implement prompt_sensor_channel() with validation"
Task: "Implement prompt_moisture_threshold() with validation"
```

## Parallel Example: Cross-Story Development

```bash
# After Phase 2 (Foundation) completes, two developers can work in parallel:

Developer A: Phase 3 (User Story 1)
- Create plant profiles with CLI setup script
- Independent of monitoring system

Developer B: Phase 4 (User Story 4)
- Sensor-to-plant mapping functions
- Independent of CLI setup

# Once both complete, Developer B continues to Phase 5 (User Story 2)
# while Developer A can start Phase 6 (User Story 3) or help with US2
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Create profiles via CLI
   - Verify persistence across restarts
   - Validate error handling (duplicate names, channels)
5. Deploy/demo if ready - users can now create custom plant profiles

### Incremental Delivery

1. **Foundation** (Phase 1 + 2) → Database infrastructure ready
2. **+ User Story 1** (Phase 3) → Test independently → Deploy/Demo (**MVP!**)
   - Users can create and persist plant profiles
3. **+ User Story 4** (Phase 4) → Test independently → Deploy/Demo
   - Sensor-to-plant mapping ready for monitoring
4. **+ User Story 2** (Phase 5) → Test independently → Deploy/Demo
   - Monitoring uses custom thresholds and plant names
5. **+ User Story 3** (Phase 6) → Test independently → Deploy/Demo
   - Watering history tracking enabled
6. **Polish** (Phase 7) → Final validation → Full release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Foundation together** (Phase 1 + 2)
2. **Once Foundational is done**:
   - Developer A: User Story 1 (Phase 3) - CLI setup script
   - Developer B: User Story 4 (Phase 4) - Sensor mapping
3. **After US4 completes**:
   - Developer B: User Story 2 (Phase 5) - Monitoring integration
   - Developer A: Can assist with US2 or start documentation
4. **After US2 completes**:
   - Developer A or B: User Story 3 (Phase 6) - Watering history
5. **Polish together** (Phase 7)

Stories complete and integrate independently.

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- **Test-First is mandatory**: Verify tests fail (RED) before implementing (GREEN)
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Database write failures must not block monitoring (FR-017)
- All plant names must replace hardcoded "Plant-A", "Plant-B", "Plant-C" labels
