# Research: Local Web Dashboard for Plant Monitoring

**Feature**: 004-web-dashboard
**Date**: 2026-02-13
**Status**: Complete

## Research Questions

### 1. Web Framework Choice: Flask vs FastAPI

**Decision**: Flask

**Rationale**:
- **Memory footprint**: Flask uses 50-60 MB RSS vs FastAPI's 140 MB with Uvicorn - well under the <100MB constraint
- **Static file serving**: Flask has built-in static file support with no additional dependencies; FastAPI requires `aiofiles` and `StaticFiles` configuration
- **File upload handling**: Flask includes file uploads via Werkzeug's `secure_filename()` without extra packages; FastAPI requires `python-multipart`
- **Deployment simplicity**: Flask + Gunicorn is straightforward on Raspberry Pi with abundant community tutorials; FastAPI requires Uvicorn + additional ASGI setup
- **Raspberry Pi community**: Extensive Flask tutorials specific to Raspberry Pi (Random Nerd Tutorials, Pi My Life Up, official Raspberry Pi Foundation guides)
- **Testing**: Both have excellent pytest support; Flask is slightly simpler without async considerations
- **Performance**: At 1-3 concurrent household users, both frameworks will be imperceptibly fast (Flask: 2,000-5,000 RPS vs FastAPI: 15,000-20,000 RPS - the difference is irrelevant for this use case)

**Alternatives Considered**:
- **FastAPI**: Excellent for high-concurrency APIs with automatic documentation, but overkill for local dashboard with 1-3 users. Higher memory footprint (140 MB) and more dependencies (uvicorn, python-multipart, aiofiles) add unnecessary complexity.
- **Django**: Full-featured framework with admin panel, but massive overkill for ~10 API routes. Memory footprint and complexity far exceed requirements.

**Implementation Notes**:
- Use Flask development server for local testing
- Use Gunicorn with 2 workers for production deployment as systemd service
- Serve static files from `src/static/` directory
- Use `werkzeug.utils.secure_filename()` for file upload validation

---

### 2. Frontend Charting Library

**Decision**: Chart.js

**Rationale**:
- **Lightweight**: ~60 KB minified, no dependencies beyond vanilla JavaScript
- **Responsive**: Works on mobile devices (dashboard requirement SC-008)
- **Time-series support**: Built-in time scale for environmental data graphing
- **Tooltip support**: Hover/tap to see exact values (FR-015 requirement)
- **Simple integration**: CDN available, no build step required
- **Well-documented**: Extensive examples for line charts with multiple datasets

**Alternatives Considered**:
- **D3.js**: Extremely powerful but overkill for simple time-series graphs. Steeper learning curve and larger bundle size.
- **Plotly.js**: Feature-rich but 3+ MB bundle size. Too heavy for Raspberry Pi serving over local network.
- **ApexCharts**: Good alternative but Chart.js has better lightweight performance and simpler API for our use case.

**Implementation Notes**:
- Use CDN link in HTML: `https://cdn.jsdelivr.net/npm/chart.js`
- Configure time scale for X-axis with timestamps
- Display 4 datasets on same chart (temperature, humidity, pressure, gas resistance)
- Update chart data every 5 seconds via polling

---

### 3. Database Schema for Environmental Readings

**Decision**: Simple table with timestamp-indexed rows, 1-hour retention with periodic cleanup

**Rationale**:
- **Query efficiency**: Index on timestamp enables fast "last 60 minutes" queries
- **Storage efficiency**: Delete data older than 1 hour to prevent unbounded growth (~60-120 rows at steady state)
- **Write pattern**: Monitoring system inserts one row per cycle (every 1-2 minutes)
- **Read pattern**: Dashboard queries last 60 minutes for graphing (simple `WHERE timestamp > NOW() - 1 hour`)

**Schema**:
```sql
CREATE TABLE IF NOT EXISTS environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    gas_resistance REAL,
    UNIQUE(timestamp)
);

CREATE INDEX idx_timestamp ON environmental_readings(timestamp);
```

**Cleanup Strategy**:
- Monitoring system deletes rows older than 1 hour after each insert
- Simple DELETE query: `DELETE FROM environmental_readings WHERE timestamp < datetime('now', '-1 hour')`

**Alternatives Considered**:
- **Circular buffer**: More complex to implement in SQLite, minimal benefit for ~60 rows
- **No retention limit**: Would grow unbounded; unnecessary for dashboard only showing last hour
- **Separate daily tables**: Overkill for small dataset; adds partitioning complexity

---

### 4. Image Upload Storage Strategy

**Decision**: Store images in `data/images/` with filename = `plant_{id}.{ext}`, reference in database via image_path column

**Rationale**:
- **Simplicity**: One image per plant, easy to manage with plant ID in filename
- **Data locality**: Images stored alongside SQLite database for simple backups
- **File serving**: Flask can serve images from `data/images/` directory via static route
- **Database footprint**: Store only relative path (e.g., `plant_1.jpg`) not binary data
- **Size limit**: 10 MB enforced at upload time per FR-026

**Storage Pattern**:
- Upload to temporary location
- Validate file type (JPEG, PNG, GIF, WebP) and size (<10 MB)
- If plant already has image, delete old file
- Save as `data/images/plant_{plant_id}.{extension}`
- Update database: `UPDATE plant_profiles SET image_path = 'plant_1.jpg' WHERE id = 1`

**Alternatives Considered**:
- **BLOB in database**: Simplifies serving but bloats database size; files are easier to backup/restore separately
- **UUID filenames**: More complex than plant ID; ID-based naming makes debugging easier
- **Preserve original filenames**: Potential security risk (path traversal); sanitized ID-based names are safer

---

### 5. Real-Time Update Mechanism

**Decision**: Client-side polling every 5 seconds (already clarified in spec)

**Rationale**:
- **Simplicity**: No persistent connections to manage
- **Adequate latency**: 5-second delay acceptable given monitoring cycles run every 1-2 minutes
- **Low overhead**: At 1-3 concurrent users, polling is negligible load
- **Easy testing**: Standard HTTP requests, no WebSocket complexity
- **Browser compatibility**: Works everywhere without special server configuration

**Polling Endpoints**:
- `GET /api/plants` - Get all plant profiles with current moisture levels
- `GET /api/environmental/latest` - Get latest environmental reading
- `GET /api/environmental/history` - Get last 60 minutes for graphing

**Alternatives Considered**:
- **WebSockets**: Real-time push updates but adds complexity (persistent connections, fallback handling, testing). Minimal benefit for 5-second acceptable latency.
- **Server-Sent Events (SSE)**: Simpler than WebSockets but still requires persistent connections; overkill for local dashboard.

---

## Technology Stack Summary

| Component | Technology | Justification |
|-----------|-----------|---------------|
| Backend Framework | Flask | Lightweight (50-60 MB), built-in static files & uploads, extensive Pi community |
| Production Server | Gunicorn | Standard Flask production deployment, simple systemd service |
| Frontend | Vanilla HTML/CSS/JS | No build step, minimal complexity, adequate for dashboard UI |
| Charting | Chart.js (CDN) | Lightweight (60 KB), responsive, time-series support |
| Database | SQLite (existing) | Already in use, adequate for local single-user writes |
| Testing | pytest + Flask test client | Existing project standard |
| Deployment | systemd service | Standard Linux service management on Raspberry Pi |

---

## Dependencies (New)

**Python packages**:
- `flask` - Web framework
- `gunicorn` - Production WSGI server
- `pillow` - Image validation (format, size)

**Frontend (CDN)**:
- `chart.js` - Environmental data graphing

---

## Open Questions (None)

All technical decisions resolved. Proceed to Phase 1: Design & Contracts.
