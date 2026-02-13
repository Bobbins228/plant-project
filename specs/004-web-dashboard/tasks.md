# Tasks: Local Web Dashboard for Plant Monitoring

**Input**: Design documents from `/specs/004-web-dashboard/`
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

**Purpose**: Install dependencies, create directory structure, run database migration

- [X] T001 Install Flask, Gunicorn, and Pillow dependencies in requirements.txt
- [X] T002 [P] Create src/static/ directory for frontend static files
- [X] T003 [P] Create data/images/ directory for uploaded plant images
- [X] T004 Run database migration to add environmental_readings table and image_path column per contracts/database.sql

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests for Foundational Components

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T005 [P] Integration test for monitoring system persisting environmental data in tests/integration/test_monitoring_env_persistence.py
- [X] T006 [P] Unit test for image validation (format, size) in tests/unit/test_image_validation.py

### Implementation for Foundational Components

- [X] T007 Modify MoistureMonitor in src/lib/moisture_monitor.py to persist environmental readings to database after each cycle
- [X] T008 [P] Create image handler module with validation and storage logic in src/lib/image_handler.py
- [X] T009 [P] Add database query functions for environmental data (latest, history, cleanup) in src/lib/database.py

**Checkpoint**: Foundation ready - user story implementation can now begin

---

## Phase 3: User Story 1 - View Live Monitoring Dashboard (Priority: P1) 🎯 MVP

**Goal**: Display real-time plant moisture and environmental data on web dashboard with automatic 5-second polling updates

**Independent Test**: Start monitoring system and web server, open dashboard in browser, verify plant moisture levels and environmental readings display and update automatically

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T010 [P] [US1] Contract test for GET /api/plants endpoint (list all plants with current moisture) in tests/contract/test_api_plants.py
- [X] T011 [P] [US1] Contract test for GET /api/plants/{id} endpoint (single plant details) in tests/contract/test_api_plants.py
- [X] T012 [P] [US1] Contract test for GET /api/environmental/latest endpoint (latest environmental reading) in tests/contract/test_api_environmental.py
- [X] T013 [US1] Integration test for dashboard loading and displaying plant data in tests/integration/test_dashboard_db.py

### Implementation for User Story 1

- [X] T014 [US1] Create Flask app with CORS configuration in src/lib/web_server.py
- [X] T015 [US1] Implement GET /api/plants endpoint (return all plant profiles with current moisture) in src/lib/web_server.py
- [X] T016 [US1] Implement GET /api/plants/{id} endpoint (return single plant details) in src/lib/web_server.py
- [X] T017 [US1] Implement GET /api/environmental/latest endpoint (return latest environmental reading or 204 if none) in src/lib/web_server.py
- [X] T018 [US1] Add static file serving route for frontend in src/lib/web_server.py
- [X] T019 [P] [US1] Create dashboard HTML structure with plant cards and environmental panel in src/static/index.html
- [X] T020 [P] [US1] Create dashboard CSS with responsive layout and status indicators in src/static/style.css
- [X] T021 [US1] Implement JavaScript polling (every 5 seconds) to fetch plant and environmental data in src/static/app.js
- [X] T022 [US1] Implement plant card rendering with moisture percentage and status indicators in src/static/app.js
- [X] T023 [US1] Implement environmental panel rendering with temperature, humidity, pressure, gas in src/static/app.js
- [X] T024 [US1] Add error handling for API failures (show stale data warning) in src/static/app.js
- [X] T025 [US1] Create dashboard CLI entry point to start Flask server in src/cli/dashboard.py
- [X] T026 [US1] Add request logging middleware (method, path, status code, duration) in src/lib/web_server.py

**Checkpoint**: At this point, User Story 1 should be fully functional - dashboard displays live plant and environmental data

---

## Phase 4: User Story 2 - View Environmental History Graph (Priority: P2)

**Goal**: Display time-series graph of last 60 minutes of environmental data with Chart.js

**Independent Test**: Run monitoring system for at least 5 minutes, open dashboard, verify environmental history graph displays with temperature, humidity, pressure, gas resistance over time

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T027 [P] [US2] Contract test for GET /api/environmental/history endpoint (last 60 minutes) in tests/contract/test_api_environmental.py

### Implementation for User Story 2

- [X] T028 [US2] Implement GET /api/environmental/history endpoint (return readings from last 60 minutes) in src/lib/web_server.py
- [X] T029 [US2] Add Chart.js CDN script tag to HTML in src/static/index.html
- [X] T030 [US2] Create environmental history graph section in HTML in src/static/index.html
- [X] T031 [US2] Implement Chart.js time-series graph initialization with 4 datasets in src/static/app.js
- [X] T032 [US2] Implement graph data fetching and updating (polls with plant data) in src/static/app.js
- [X] T033 [US2] Add tooltip configuration to show exact values and timestamp on hover in src/static/app.js
- [X] T034 [US2] Handle empty data case (show "No data available" message) in src/static/app.js

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - dashboard displays live data and historical graph

---

## Phase 5: User Story 3 - Manage Plant Profiles (CRUD) (Priority: P3)

**Goal**: Allow users to create, edit, and delete plant profiles through web interface with validation

**Independent Test**: Create new plant via dashboard, verify it appears in monitoring output, edit plant threshold, verify changes persist, delete plant, verify removal

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T035 [P] [US3] Contract test for POST /api/plants endpoint (create plant with validation) in tests/contract/test_api_plants.py
- [X] T036 [P] [US3] Contract test for PUT /api/plants/{id} endpoint (update plant with validation) in tests/contract/test_api_plants.py
- [X] T037 [P] [US3] Contract test for DELETE /api/plants/{id} endpoint (delete plant, prevent last plant deletion) in tests/contract/test_api_plants.py

### Implementation for User Story 3

- [X] T038 [US3] Implement POST /api/plants endpoint (create plant, validate channel/threshold, return 400 on errors) in src/lib/web_server.py
- [X] T039 [US3] Implement PUT /api/plants/{id} endpoint (update plant, validate changes, return 404 if not found) in src/lib/web_server.py
- [X] T040 [US3] Implement DELETE /api/plants/{id} endpoint (delete plant, prevent last plant deletion, return 404 if not found) in src/lib/web_server.py
- [X] T041 [P] [US3] Create "Add Plant" modal form in HTML in src/static/index.html
- [X] T042 [P] [US3] Create "Edit Plant" modal form in HTML in src/static/index.html
- [X] T043 [US3] Implement add plant form submission and API call in src/static/app.js
- [X] T044 [US3] Implement edit plant form pre-fill and submission in src/static/app.js
- [X] T045 [US3] Implement delete plant confirmation and API call in src/static/app.js
- [X] T046 [US3] Add client-side validation (channel 0-3, threshold 0-100, unique name) in src/static/app.js
- [X] T047 [US3] Add error message display for validation failures in src/static/app.js

**Checkpoint**: At this point, User Stories 1, 2, AND 3 should all work - full plant management via dashboard

---

## Phase 6: User Story 4 - Add Plant Profile Images (Priority: P4)

**Goal**: Allow users to upload, change, and remove plant profile images with validation

**Independent Test**: Upload image for plant via dashboard, verify it displays on card, change image, verify old image replaced, remove image, verify placeholder appears

### Tests for User Story 4

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T048 [P] [US4] Contract test for POST /api/plants/{id}/image endpoint (upload image with format/size validation) in tests/contract/test_image_upload.py
- [X] T049 [P] [US4] Contract test for DELETE /api/plants/{id}/image endpoint (remove image) in tests/contract/test_image_upload.py

### Implementation for User Story 4

- [X] T050 [US4] Implement POST /api/plants/{id}/image endpoint (validate format/size, save to data/images/, update DB) in src/lib/web_server.py
- [X] T051 [US4] Implement DELETE /api/plants/{id}/image endpoint (delete file, set image_path to NULL) in src/lib/web_server.py
- [X] T052 [US4] Add static route to serve images from data/images/ directory in src/lib/web_server.py
- [X] T053 [P] [US4] Add image upload/remove controls to edit plant modal in src/static/index.html
- [X] T054 [P] [US4] Add image display to plant cards (show image or placeholder) in src/static/index.html
- [X] T055 [US4] Implement image upload with preview before saving in src/static/app.js
- [X] T056 [US4] Implement image removal and placeholder restoration in src/static/app.js
- [X] T057 [US4] Add client-side file type and size validation (10 MB limit) in src/static/app.js

**Checkpoint**: At this point, all User Stories (1-4) should be fully functional - complete dashboard with image support

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Production readiness, error handling, deployment configuration

- [X] T058 [P] Add comprehensive error handling and descriptive error messages to all API endpoints in src/lib/web_server.py
- [X] T059 [P] Add structured logging for all API requests and image operations in src/lib/web_server.py
- [X] T060 Verify all environmental values formatted to exactly 2 decimal places in frontend display
- [X] T061 Verify mobile responsiveness (no horizontal scrolling) on dashboard
- [X] T062 Add "Last Updated" timestamp display on dashboard
- [X] T063 Add "Monitoring System Stopped" warning when data is stale (>5 minutes old)
- [X] T064 Create systemd service file for dashboard background deployment per quickstart.md
- [X] T065 Verify environmental data cleanup (delete rows >1 hour old) runs after each insert
- [X] T066 Test concurrent users viewing/editing same plant (database locking behavior)
- [X] T067 Validate all user input sanitized before database operations (prevent SQL injection)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - Can start after Phase 2 (MVP!)
- **User Story 2 (Phase 4)**: Depends on Foundational + US1 frontend - Can start after Phase 3
- **User Story 3 (Phase 5)**: Depends on Foundational + US1 (uses same API structure) - Can start after Phase 3
- **User Story 4 (Phase 6)**: Depends on Foundational + US3 (extends edit forms) - Can start after Phase 5
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

```
Foundation (Phase 2) - BLOCKS ALL STORIES
    ↓
    └─→ US1 (Phase 3) - View Live Dashboard (MVP)
            ↓
            ├─→ US2 (Phase 4) - View Environmental Graph (extends US1 frontend)
            └─→ US3 (Phase 5) - Manage Plant Profiles (uses US1 API structure)
                    ↓
                    └─→ US4 (Phase 6) - Add Plant Images (extends US3 forms)
```

**Critical Path**: Foundation → US1 (MVP) → US2 + US3 (parallel) → US4

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Test-First principle)
- Contract tests before implementation
- Integration tests before implementation
- Models/routes before frontend
- Frontend structure (HTML) before logic (JS)
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: All tasks T001-T004 can run in parallel if desired

**Phase 2 (Foundational Tests)**: T005-T006 can run in parallel

**Phase 2 (Foundational Implementation)**: T008-T009 can run in parallel (T007 depends on existing code)

**Phase 3 (US1 Tests)**: T010-T012 can run in parallel

**Phase 3 (US1 Implementation)**: T014-T017 sequential (routes in same file), T019-T020 parallel (HTML/CSS), T021-T024 sequential (JS)

**Phase 4 (US2)**: Single contract test T027, then implementation tasks sequential

**Phase 5 (US3 Tests)**: T035-T037 can run in parallel

**Phase 5 (US3 Implementation)**: T038-T040 sequential (routes in same file), T041-T042 parallel (modals), T043-T047 sequential (JS)

**Phase 6 (US4 Tests)**: T048-T049 can run in parallel

**Phase 6 (US4 Implementation)**: T050-T052 sequential (routes), T053-T054 parallel (HTML), T055-T057 sequential (JS)

**Phase 7 (Polish)**: T058-T059 parallel, T060-T063 parallel, others sequential

**After US1 completes**: US2 and US3 can be developed in parallel by different developers

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (install dependencies, create directories, migrate DB)
2. Complete Phase 2: Foundational (environmental persistence, image handler, DB queries)
3. Complete Phase 3: User Story 1 (live dashboard with polling)
4. **STOP and VALIDATE**: Test User Story 1 independently
   - Start monitoring system
   - Start dashboard server
   - Open in browser, verify plant moisture and environmental data display
   - Verify auto-updates every 5 seconds
5. Deploy/demo if ready - users can now monitor plants via browser

### Incremental Delivery

1. **Foundation** (Phase 1 + 2) → Environmental data persistence + image handling ready
2. **+ User Story 1** (Phase 3) → Test independently → Deploy/Demo (**MVP!**)
   - Dashboard displays live plant and environmental data
3. **+ User Story 2** (Phase 4) → Test independently → Deploy/Demo
   - Historical environmental graphing added
4. **+ User Story 3** (Phase 5) → Test independently → Deploy/Demo
   - Full plant CRUD via web interface
5. **+ User Story 4** (Phase 6) → Test independently → Deploy/Demo
   - Plant profile images
6. **Polish** (Phase 7) → Final validation → Full release

Each story adds value without breaking previous stories.

### Parallel Team Strategy

With multiple developers:

1. **Team completes Foundation together** (Phase 1 + 2)
2. **Once Foundational is done**:
   - Developer A: User Story 1 (Phase 3) - Live dashboard (MVP)
3. **After US1 completes**:
   - Developer A: User Story 2 (Phase 4) - Environmental graph
   - Developer B: User Story 3 (Phase 5) - Plant CRUD (parallel to US2)
4. **After US2 and US3 complete**:
   - Developer A or B: User Story 4 (Phase 6) - Plant images
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
- Dashboard runs as separate service from monitoring system (shared DB only)
- Frontend uses vanilla JS with Chart.js CDN (no build step)
- 5-second polling provides near-real-time updates for household use
- Image uploads limited to 10 MB (JPEG, PNG, GIF, WebP only)
