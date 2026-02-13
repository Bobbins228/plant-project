# Implementation Plan: Local Web Dashboard for Plant Monitoring

**Branch**: `004-web-dashboard` | **Date**: 2026-02-13 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-web-dashboard/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Create a local web dashboard accessible on the home network that displays real-time plant moisture and environmental data, provides time-series graphing of environmental conditions over the past hour, and allows full CRUD management of plant profiles with image uploads. The dashboard polls a shared SQLite database every 5 seconds for updates, with the existing monitoring system persisting environmental readings to a new database table.

## Technical Context

**Language/Version**: Python 3.9+ (existing project standard)
**Primary Dependencies**: Flask (web framework), Gunicorn (production server), Pillow (image validation), Chart.js (frontend charting via CDN)
**Storage**: SQLite database (existing data/plants.db with new environmental_readings table)
**Testing**: pytest with Flask test client (existing)
**Target Platform**: Raspberry Pi 4 (Linux/Raspbian), local network access only
**Project Type**: Web application (simple backend API + static frontend)
**Performance Goals**: Serve dashboard to 1-3 concurrent household users, 5-second polling interval, <500ms page load
**Constraints**: <100MB memory footprint (shared with monitoring system), no external dependencies beyond PyPI packages, runs continuously as background service
**Scale/Scope**: <10 routes (list plants, get plant, create/update/delete plant, upload image, get environmental data), <50 plants maximum, 60 minutes of environmental data retention

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### I. Test-First (NON-NEGOTIABLE)

**Status**: ✓ PASS

- Contract tests will verify HTTP API endpoints (GET /api/plants, POST /api/plants, etc.)
- Integration tests will verify database interactions and file uploads
- Unit tests for data validation and business logic as needed
- Tests written before implementation per TDD workflow

**Compliance**: All user stories have acceptance scenarios that map directly to testable API contracts. The shared database approach enables testing without complex mocking.

### II. Library-First

**Status**: ✓ PASS

- Web server module: self-contained HTTP server exposing plant management API
- Image upload handler: reusable file validation and storage logic
- Dashboard frontend: static HTML/CSS/JS served by web server (separate from monitoring system)
- Environmental data query service: reusable database query logic for graphing

**Compliance**: The dashboard is a separate service from the monitoring system, communicating only via shared database. Each component (API routes, image handling, frontend) is independently testable.

### III. Observability

**Status**: ✓ PASS

- Structured logging for all API requests (method, path, status code, duration)
- Error transparency: HTTP errors include descriptive messages (e.g., "Plant with channel 2 already exists")
- Database query logging (at DEBUG level)
- File upload tracking (filename, size, validation result)

**Compliance**: Text-based HTTP protocol, JSON responses, structured logs enable debugging without attaching a debugger.

**GATE RESULT (Pre-Research)**: ✓ ALL GATES PASS - Proceed to Phase 0 Research

---

## Constitution Check (Post-Design Re-evaluation)

*Required after Phase 1 design completion*

### I. Test-First (NON-NEGOTIABLE)

**Status**: ✓ PASS (Confirmed)

**Contract Tests Defined** (contracts/api.yaml):
- GET /api/plants - List all plant profiles
- POST /api/plants - Create plant profile
- GET /api/plants/{id} - Get single plant
- PUT /api/plants/{id} - Update plant profile
- DELETE /api/plants/{id} - Delete plant profile
- POST /api/plants/{id}/image - Upload image
- DELETE /api/plants/{id}/image - Remove image
- GET /api/environmental/latest - Get latest reading
- GET /api/environmental/history - Get historical data

**Integration Tests Required**:
- Database operations (plant CRUD with shared DB)
- Environmental data persistence by monitoring system
- Image upload file handling and storage

**Compliance**: All API endpoints have OpenAPI specifications defining expected behavior, enabling contract tests to be written before implementation.

### II. Library-First

**Status**: ✓ PASS (Confirmed)

**Modular Components Designed**:
- `src/lib/web_server.py` - Flask HTTP server (self-contained API routes)
- `src/lib/image_handler.py` - Image validation and storage (reusable file operations)
- `src/static/` - Frontend (independent from monitoring system)
- Database queries reuse existing `src/lib/database.py` utilities

**Compliance**: Web server can run independently from monitoring system. Each component has clear boundaries and can be tested in isolation.

### III. Observability

**Status**: ✓ PASS (Confirmed)

**Logging Strategy** (from research.md):
- Structured logging for all HTTP requests (method, path, status, duration)
- Error transparency in JSON responses with descriptive messages
- Database query logging at DEBUG level
- File upload tracking (filename, size, validation result)

**Compliance**: Text-based HTTP/JSON protocol, structured logs, traceable operations enable debugging without debugger attachment.

**GATE RESULT (Post-Design)**: ✓ ALL GATES PASS - Design compliant with constitution

## Project Structure

### Documentation (this feature)

```text
specs/004-web-dashboard/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── api.yaml         # OpenAPI specification for REST API
│   └── database.sql     # Database schema for new environmental_readings table
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
# Web application structure (frontend + backend on same Raspberry Pi)

src/
├── models/
│   ├── environmental_reading.py  # (existing from 003-bme688-environmental)
│   └── plant_profile.py          # (existing from 002-plant-profile-database)
├── lib/
│   ├── database.py               # (existing database utilities)
│   ├── moisture_monitor.py       # (existing monitoring system - modified to persist env data)
│   └── web_server.py             # NEW: HTTP server for dashboard API
├── cli/
│   ├── monitor.py                # (existing monitoring daemon)
│   └── dashboard.py              # NEW: Dashboard server CLI entry point
└── static/                       # NEW: Frontend static files
    ├── index.html                # Main dashboard page
    ├── style.css                 # Dashboard styles
    ├── app.js                    # Dashboard JavaScript (polling, updates, charts)
    └── images/                   # Frontend assets (icons, placeholders)

data/
├── plants.db                     # (existing SQLite database)
└── images/                       # NEW: Uploaded plant profile images

tests/
├── contract/
│   ├── test_api_plants.py        # NEW: API endpoint contract tests
│   ├── test_api_environmental.py # NEW: Environmental data API tests
│   └── test_image_upload.py      # NEW: Image upload contract tests
├── integration/
│   ├── test_dashboard_db.py      # NEW: Database query integration tests
│   └── test_monitoring_env_persistence.py  # NEW: Verify monitoring system writes env data
└── unit/
    └── test_image_validation.py  # NEW: Unit tests for image file validation
```

**Structure Decision**: Single project with web application additions. The dashboard backend (src/lib/web_server.py) and frontend (src/static/) are added to the existing project structure. The monitoring system (src/lib/moisture_monitor.py) will be modified to persist environmental data to the database. This maintains simplicity by avoiding a separate backend/frontend split - the web server serves both the API and static files.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitutional violations - table remains empty.
