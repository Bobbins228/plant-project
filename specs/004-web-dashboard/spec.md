# Feature Specification: Local Web Dashboard for Plant Monitoring

**Feature Branch**: `004-web-dashboard`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "A web app that can interact with the monitoring system. The web app is only meant to run locally within a house and not exposed. The web app should display the live environmental data as well as graphing as an option. The plant profiles should be configurable from the web app with full CRUD capabilities. Each plant profile card should have the option to add an image and change it as if it is the plant's profile picture. For the environment graph it should showcase the last hour of environmental data and this data could be persisted using the SQLite database"

## Clarifications

### Session 2026-02-13

- Q: How should the dashboard access monitoring data and communicate changes to the monitoring system? → A: Shared SQLite database - Dashboard and monitoring system both access same database file directly
- Q: Where should uploaded plant images be stored on the filesystem? → A: data/images/ directory - Store images alongside database in data/ directory structure
- Q: How should the dashboard detect new data and update automatically? → A: Periodic polling every 5 seconds - Browser requests latest data every 5 seconds
- Q: Which component should be responsible for writing environmental readings to the database? → A: Monitoring system writes environmental data to database in a separate table from plant profiles
- Q: What is the maximum file size allowed for uploaded plant images? → A: 10 MB maximum file size

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Live Monitoring Dashboard (Priority: P1) 🎯 MVP

A homeowner wants to check on their plants without physically inspecting them or reviewing log files. They open the web dashboard in their browser to see current moisture levels for all plants and current environmental conditions (temperature, humidity, pressure, gas resistance) at a glance.

**Why this priority**: This is the core value proposition - providing an accessible, visual way to monitor plant and environmental status without technical knowledge. This alone delivers immediate value and makes the system usable by non-technical household members.

**Independent Test**: Can be fully tested by starting the monitoring system and web server, opening the dashboard in a browser, and verifying that current plant moisture levels and environmental readings display and update in real-time. Delivers immediate value by making monitoring data accessible to anyone in the household.

**Acceptance Scenarios**:

1. **Given** the monitoring system is running, **When** I open the dashboard URL in my browser, **Then** I see all plant profiles with their current moisture percentage
2. **Given** I am viewing the dashboard, **When** the monitoring cycle runs, **Then** I see updated moisture and environmental readings without refreshing the page
3. **Given** I am viewing the dashboard, **When** a plant's moisture drops below threshold, **Then** I see a visual indicator (color, icon, alert) showing it needs watering
4. **Given** environmental sensor is available, **When** I view the dashboard, **Then** I see current temperature, humidity, pressure, and gas resistance readings
5. **Given** environmental sensor is unavailable, **When** I view the dashboard, **Then** I see plant moisture data and a message that environmental data is unavailable

---

### User Story 2 - View Environmental History Graph (Priority: P2)

A homeowner wants to understand how temperature and humidity have changed over the past hour to identify patterns (e.g., humidity drop when heater turns on, temperature spike in afternoon sun). They view a time-series graph showing the last hour of environmental data.

**Why this priority**: Adds historical context to environmental data, enabling users to identify trends and correlations between environmental conditions and plant water consumption. Requires environmental data persistence.

**Independent Test**: Can be fully tested by running the monitoring system for at least one hour with environmental sensor connected, opening the dashboard, and verifying that a graph displays temperature, humidity, pressure, and gas resistance over the past hour with timestamps.

**Acceptance Scenarios**:

1. **Given** environmental data has been collected for at least 5 minutes, **When** I open the environmental graph view, **Then** I see a time-series chart showing temperature, humidity, pressure, and gas resistance over time
2. **Given** I am viewing the environmental graph, **When** new readings are collected, **Then** the graph updates to show the latest data point
3. **Given** the graph displays one hour of data, **When** data older than one hour exists, **Then** the graph shows only the most recent 60 minutes
4. **Given** I am viewing the graph, **When** I hover over a data point, **Then** I see the exact timestamp and values for all metrics at that moment
5. **Given** no environmental data is available, **When** I open the environmental graph view, **Then** I see a message explaining environmental sensor is not connected or no data has been collected yet

---

### User Story 3 - Manage Plant Profiles (Priority: P3)

A homeowner wants to add a new plant to the monitoring system, update an existing plant's name or moisture threshold, or remove a plant that is no longer being monitored. They use the web dashboard to create, edit, and delete plant profiles without editing configuration files or databases directly.

**Why this priority**: Eliminates technical barriers to system configuration. Users should not need command-line access or database knowledge to manage their plants.

**Independent Test**: Can be fully tested by creating a new plant profile through the web interface, verifying it appears in monitoring output, editing the profile's name and threshold, verifying changes persist across monitoring cycles, and deleting the profile to verify it no longer appears.

**Acceptance Scenarios**:

1. **Given** I am on the dashboard, **When** I click "Add Plant", **Then** I see a form to enter plant name, sensor channel (0-3), and moisture threshold percentage
2. **Given** I have filled the add plant form with valid data, **When** I submit the form, **Then** the new plant appears on the dashboard with "no data" status until next monitoring cycle
3. **Given** I am viewing a plant card, **When** I click "Edit", **Then** I see a form pre-filled with the plant's current name, threshold, and sensor channel
4. **Given** I have edited a plant's threshold, **When** I save changes, **Then** the updated threshold is used in the next monitoring cycle
5. **Given** I am viewing a plant card, **When** I click "Delete" and confirm, **Then** the plant is removed from the dashboard and no longer monitored
6. **Given** I try to create a plant with a sensor channel already in use, **When** I submit the form, **Then** I see an error message indicating the channel is already assigned
7. **Given** I try to create a plant with an invalid threshold (e.g., negative number, over 100%), **When** I submit the form, **Then** I see validation errors

---

### User Story 4 - Add Plant Profile Images (Priority: P4)

A homeowner wants to personalize each plant card with a photo of the actual plant to make the dashboard more visual and easier to navigate at a glance. They upload or change a plant's profile picture through the web interface.

**Why this priority**: Enhances user experience and makes the dashboard more intuitive, especially for households with many plants. This is a nice-to-have feature that doesn't affect core monitoring functionality.

**Independent Test**: Can be fully tested by uploading an image for a plant profile through the web interface, verifying it displays on the plant card, changing the image to a different photo, and verifying the old image is replaced.

**Acceptance Scenarios**:

1. **Given** I am editing a plant profile, **When** I click "Upload Image" and select a photo from my device, **Then** I see a preview of the image before saving
2. **Given** I have uploaded a plant image, **When** I save the plant profile, **Then** the image appears on the plant's card on the dashboard
3. **Given** a plant has an existing image, **When** I upload a new image, **Then** the new image replaces the old one
4. **Given** a plant has an image, **When** I click "Remove Image", **Then** the image is removed and a default placeholder appears
5. **Given** I try to upload a very large file, **When** the file exceeds the size limit, **Then** I see an error message indicating maximum file size
6. **Given** I try to upload a non-image file, **When** I select a non-image file type, **Then** I see an error message indicating only image files are allowed

---

### Edge Cases

- What happens when a user tries to access the dashboard while the monitoring system is not running?
- How does the system handle concurrent users viewing/editing the same plant profile?
- What happens when environmental data collection is interrupted (sensor disconnected mid-graph)?
- How does the graph display when less than one hour of data is available (e.g., system just started)?
- What happens when a user uploads a malformed or corrupted image file?
- How does the system handle rapid refresh attempts (preventing dashboard from overwhelming the system)?
- What happens when a plant's moisture reading fails but other plants succeed?
- How does the dashboard indicate staleness of data (e.g., monitoring system hasn't run in hours)?

## Requirements *(mandatory)*

### Functional Requirements

**Dashboard Access**
- **FR-001**: System MUST provide a web interface accessible via local network (localhost or local IP address)
- **FR-002**: System MUST NOT require authentication for local network access
- **FR-003**: Dashboard MUST be accessible from any device on the local network (desktop, tablet, mobile phone)
- **FR-003a**: Dashboard MUST access monitoring data through shared SQLite database (same database used by monitoring system)

**Live Data Display**
- **FR-004**: Dashboard MUST display current moisture percentage for each plant profile
- **FR-005**: Dashboard MUST display current environmental readings (temperature, humidity, pressure, gas resistance) when sensor is available
- **FR-006**: Dashboard MUST update displayed data automatically when new monitoring cycle completes (no manual refresh required)
- **FR-006a**: Dashboard MUST poll database for new data every 5 seconds to detect updates
- **FR-007**: Dashboard MUST display timestamp of last successful monitoring cycle
- **FR-008**: Dashboard MUST visually indicate which plants need watering (moisture below threshold)
- **FR-009**: Dashboard MUST display "unavailable" or "no data" state when environmental sensor is not connected
- **FR-010**: Dashboard MUST display "no data" state for plants with no successful readings yet

**Environmental Data Graphing**
- **FR-011**: Monitoring system MUST persist environmental readings to database with timestamps in a separate table from plant profiles
- **FR-011a**: Environmental readings table MUST store timestamp, temperature, humidity, pressure, and gas_resistance for each monitoring cycle
- **FR-012**: Dashboard MUST provide a time-series graph showing the last 60 minutes of environmental data
- **FR-013**: Graph MUST display all four environmental metrics (temperature, humidity, pressure, gas resistance) on same time axis
- **FR-014**: Graph MUST update automatically when new environmental data is collected
- **FR-015**: Graph MUST display exact values and timestamp when user hovers over or taps a data point
- **FR-016**: Graph MUST handle scenarios with less than 60 minutes of data (e.g., system just started)

**Plant Profile Management (CRUD)**
- **FR-017**: Dashboard MUST allow creating new plant profiles with name, sensor channel, and moisture threshold
- **FR-018**: Dashboard MUST validate sensor channel is between 0-3 and not already assigned to another plant
- **FR-019**: Dashboard MUST validate moisture threshold is between 0-100%
- **FR-020**: Dashboard MUST allow editing existing plant profile name, sensor channel, and threshold
- **FR-021**: Dashboard MUST allow deleting plant profiles with confirmation prompt
- **FR-022**: Dashboard MUST immediately reflect plant profile changes in monitoring output (next cycle uses new configuration)
- **FR-023**: System MUST prevent deletion of last plant profile (at least one plant required for monitoring)

**Plant Image Management**
- **FR-024**: Dashboard MUST allow uploading an image file for each plant profile
- **FR-025**: System MUST accept common image formats (JPEG, PNG, GIF, WebP)
- **FR-026**: System MUST enforce maximum file size limit of 10 MB for uploaded images
- **FR-027**: Dashboard MUST display uploaded plant image on the plant's card
- **FR-028**: Dashboard MUST allow changing/replacing an existing plant image
- **FR-029**: Dashboard MUST allow removing a plant image (revert to default placeholder)
- **FR-030**: System MUST persist plant image associations across system restarts
- **FR-030a**: System MUST store uploaded images in data/images/ directory alongside database

**Error Handling**
- **FR-031**: Dashboard MUST display user-friendly error messages for failed operations (create, update, delete, upload)
- **FR-032**: Dashboard MUST indicate when displayed data is stale (e.g., monitoring system stopped)
- **FR-033**: Dashboard MUST gracefully handle loss of connection to backend monitoring system
- **FR-034**: System MUST validate all user input before persisting to database

### Key Entities *(include if feature involves data)*

- **Environmental Reading (new table)**: Timestamp, temperature, humidity, pressure, gas resistance - stored in separate database table from plant profiles, persisted by monitoring system during each cycle, used for historical graphing
- **Plant Profile (existing table)**: Name, sensor channel, moisture threshold, current moisture level, needs watering flag - now editable via web interface
- **Plant Image (new association)**: Association between plant profile and uploaded image file stored in data/images/ directory, file path relative to data/images/, upload timestamp, file size/type metadata

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Household members can check plant status in under 10 seconds without technical knowledge
- **SC-002**: Users can identify environmental trends by viewing one hour of historical data
- **SC-003**: Users can add a new plant to monitoring in under 2 minutes without editing files
- **SC-004**: Dashboard remains responsive with 10+ plants and 60 minutes of environmental data
- **SC-005**: 95% of plant profile changes (create, update, delete) succeed on first attempt
- **SC-006**: Dashboard displays updated readings within 10 seconds of monitoring cycle completion (5-second polling interval plus processing time)
- **SC-007**: Users can successfully upload and view plant images in under 30 seconds
- **SC-008**: Dashboard is accessible from mobile devices without horizontal scrolling or zoom
- **SC-009**: Environmental data graph displays without lag when rendering 60 data points (one per minute)
- **SC-010**: System continues monitoring plants even when web dashboard is not being accessed

## Assumptions

- Web dashboard runs on the same machine as the monitoring system (Raspberry Pi)
- Dashboard and monitoring system share direct access to the same SQLite database file
- Only household members on local network will access the dashboard (no internet exposure)
- Browser supports modern web standards (JavaScript for UI interactions)
- Users have permission to create/delete files in the plant monitoring directory for image uploads
- Environmental sensor readings occur at regular intervals (consistent with current monitoring cycle timing)
- Plant profile changes take effect on next monitoring cycle (not mid-cycle)
- Maximum number of plants is reasonable for local dashboard (e.g., <50 plants)
- Image file size limit of 10 MB is sufficient for typical plant photos from modern devices
- One hour of environmental data at 1-minute intervals = ~60 data points (manageable for client-side graphing)

## Dependencies

- Existing plant monitoring system (001-moisture-monitoring)
- Existing plant profile database (002-plant-profile-database)
- Existing environmental monitoring (003-bme688-environmental) - requires modification to persist readings to database
- SQLite database with new environmental_readings table for historical data persistence
- Local network connectivity between user devices and Raspberry Pi

## Out of Scope

- User authentication or authorization (local network only, trusted environment)
- Remote access from outside local network (VPN, port forwarding, cloud hosting)
- Mobile native apps (dashboard is browser-based)
- Real-time notifications (users must check dashboard; existing ntfy.sh notifications continue separately)
- Automated watering controls or actuators
- Historical moisture data graphing (only environmental data graphing in this feature)
- Multi-language support or internationalization
- Data export features (CSV, PDF reports)
- Comparison graphs (e.g., comparing today vs yesterday)
- Custom dashboard layouts or themes
- Image editing or cropping within the dashboard
- User preferences or settings persistence per device
