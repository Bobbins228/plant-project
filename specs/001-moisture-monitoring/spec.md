# Feature Specification: Moisture Monitoring and Notifications

**Feature Branch**: `001-moisture-monitoring`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "MVP plant monitoring and notifications via ntfy.sh"

## Clarifications

### Session 2026-02-13

- Q: What format should notification messages use? → A: With moisture level (e.g., "Plant-A needs watering (moisture: 35%)")
- Q: Should throttle state persist across system restarts? → A: In-memory only (state lost on restart; dry plants re-notified immediately after restart)
- Q: Should sensor calibration be per-sensor or shared? → A: Shared calibration (all sensors use same voltage-to-percentage formula)
- Q: How should invalid sensor readings be detected? → A: Range with margin: reject if <0% or >100% from raw conversion
- Q: What logging detail level should the system use? → A: Configurable log levels (INFO: notifications/errors only; DEBUG: includes all sensor readings)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automatic Watering Alerts (Priority: P1)

As a plant owner, I want to receive automatic notifications when my plants need watering so I don't have to manually check soil moisture and can prevent my plants from drying out.

**Why this priority**: This is the core value proposition of the MVP. Without automatic alerts, the system provides no benefit over manual checking. This story alone delivers immediate value.

**Independent Test**: Can be fully tested by simulating low moisture conditions on any sensor and verifying a notification is received via ntfy.sh within expected time. Delivers immediate value by preventing plant dehydration.

**Acceptance Scenarios**:

1. **Given** Plant-A soil moisture is at 50%, **When** moisture drops to 38%, **Then** a notification is sent to ntfy.sh topic "mark-test-watering-monitor" stating "Plant-A needs watering (moisture: 38%)"
2. **Given** Plant-B soil moisture is at 35% (already low), **When** system starts monitoring, **Then** a notification is sent immediately stating "Plant-B needs watering (moisture: 35%)"
3. **Given** all three plants have adequate moisture (above 40%), **When** system monitors for 24 hours, **Then** no notifications are sent

---

### User Story 2 - Multi-Plant Independent Monitoring (Priority: P2)

As a plant owner with multiple plants, I want each plant to be monitored independently so I know exactly which plant needs attention without having to check all of them.

**Why this priority**: Critical for usability when managing 3 plants. Without independent monitoring, notifications would be ambiguous and require manual investigation.

**Independent Test**: Can be tested by setting Plant-A to low moisture (35%), Plant-B to adequate moisture (50%), and Plant-C to low moisture (38%). System should send exactly 2 notifications identifying Plant-A and Plant-C specifically.

**Acceptance Scenarios**:

1. **Given** Plant-A is at 35% and Plant-B is at 55%, **When** monitoring runs for 1 minute, **Then** only Plant-A notification is sent
2. **Given** all three plants are below 40%, **When** monitoring runs, **Then** three separate notifications are sent, each identifying the specific plant (Plant-A, Plant-B, Plant-C)
3. **Given** Plant-C was just watered (moisture rises to 60%), **When** Plant-A drops below 40%, **Then** only Plant-A notification is sent

---

### User Story 3 - Notification Throttling (Priority: P3)

As a plant owner, I want to receive watering reminders no more than once every 6 hours per plant so I'm not spammed with repeated alerts for the same dry plant.

**Why this priority**: Prevents notification fatigue and annoyance. Without throttling, users receive constant alerts every monitoring cycle (e.g., every 30 seconds), making the system unusable.

**Independent Test**: Can be tested by keeping Plant-A below 40% moisture for 12 hours and verifying exactly 2 notifications are sent (at 0 hours and 6 hours), not hundreds.

**Acceptance Scenarios**:

1. **Given** Plant-A is at 35% and was notified at 10:00 AM, **When** moisture remains at 35% until 3:00 PM, **Then** no additional notifications are sent between 10:00 AM and 4:00 PM
2. **Given** Plant-A was notified at 10:00 AM and moisture remains low, **When** 6 hours pass (4:00 PM), **Then** a second notification is sent for Plant-A
3. **Given** Plant-A was notified at 10:00 AM, **When** moisture rises to 50% at 11:00 AM (plant watered), **Then** the 6-hour throttle resets and next low-moisture event triggers immediate notification
4. **Given** Plant-A was notified at 10:00 AM and Plant-B at 10:05 AM, **When** both remain dry, **Then** Plant-A is notified again at 4:00 PM and Plant-B at 4:05 PM (independent throttle timers)

---

### Edge Cases

- What happens when a sensor gives invalid readings (converted value <0% or >100%)?
  - System logs error with sensor identifier and invalid value, skips that reading, continues monitoring other plants on next cycle

- What happens when ntfy.sh service is unreachable?
  - System logs notification failure, retries notification on next monitoring cycle

- What happens if moisture reading fluctuates around 40% (e.g., 39%, 41%, 39%)?
  - System uses 5% hysteresis buffer: notification triggers at <40%, but throttle only resets when moisture rises above 45%

- What happens when system restarts while a plant is dry?
  - On startup, throttle state is cleared (in-memory only); system checks all plants and sends notifications for any below threshold, even if they were recently notified before restart

- What happens if all three sensors fail simultaneously?
  - System logs critical error but continues running; when sensors recover, monitoring resumes

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST continuously read soil moisture from 3 capacitive sensors connected via ADS1115 I2C interface
- **FR-002**: System MUST identify sensors as Plant-A, Plant-B, and Plant-C based on ADS1115 channel mapping (Channel 0 = Plant-A, Channel 1 = Plant-B, Channel 2 = Plant-C)
- **FR-003**: System MUST convert raw sensor readings to moisture percentage (0-100%)
- **FR-003a**: System MUST validate converted readings are within valid range (0-100%); readings outside this range are considered invalid and must be rejected
- **FR-004**: System MUST compare each plant's moisture reading against a configurable minimum threshold (default: 40%)
- **FR-005**: System MUST send notification via ntfy.sh HTTP API when moisture drops below threshold
- **FR-006**: System MUST include plant identifier and current moisture percentage in notification message (format: "Plant-A needs watering (moisture: 35%)")
- **FR-007**: System MUST send notifications to configurable ntfy.sh topic (default: "mark-test-watering-monitor")
- **FR-008**: System MUST throttle notifications to maximum once per 6 hours per plant
- **FR-009**: System MUST reset throttle timer when plant moisture rises above threshold + 5% buffer (e.g., 45% for 40% threshold)
- **FR-010**: System MUST track last notification time independently for each plant in memory (state not persisted across restarts)
- **FR-011**: System MUST run as long-running process (continuous monitoring)
- **FR-012**: System MUST sample sensors at configurable interval (default: 30 seconds)
- **FR-013**: System MUST support configurable log levels with the following behavior:
  - INFO level: Log notifications sent, errors, and system lifecycle events (startup, shutdown)
  - DEBUG level: Log all sensor readings, threshold comparisons, throttle decisions, and all INFO-level events
- **FR-014**: System MUST handle sensor read failures gracefully (log error, continue monitoring other sensors)
- **FR-015**: System MUST handle ntfy.sh API failures gracefully (log error, retry on next cycle)

### Configuration Requirements

- **CR-001**: Minimum moisture threshold MUST be easily configurable (environment variable or configuration file)
- **CR-002**: ntfy.sh topic name MUST be easily configurable
- **CR-003**: Sensor sampling interval MUST be configurable
- **CR-004**: Notification throttle duration MUST be configurable (default: 6 hours)
- **CR-005**: Sensor calibration values (voltage range to moisture percentage mapping) MUST be configurable and shared across all three sensors
- **CR-006**: Log level MUST be configurable (values: INFO, DEBUG; default: INFO)
- **CR-007**: Configuration design MUST support future database integration for per-plant thresholds and names

### Key Entities

- **Plant**: Represents a monitored plant with attributes:
  - Identifier (Plant-A, Plant-B, Plant-C)
  - ADS1115 channel number (0, 1, 2)
  - Current moisture reading (percentage)
  - Minimum acceptable moisture threshold (default 40%)
  - Last notification timestamp
  - Watering state (needs water / adequately watered)

- **Sensor Reading**: Represents a moisture measurement with attributes:
  - Plant identifier
  - Raw sensor value
  - Converted moisture percentage
  - Timestamp

- **Notification Event**: Represents an alert sent to user with attributes:
  - Plant identifier
  - Message content
  - Timestamp sent
  - Success/failure status

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: System detects low moisture condition (below 40%) within 60 seconds of occurrence
- **SC-002**: Notification is delivered to ntfy.sh within 5 seconds of low moisture detection
- **SC-003**: No duplicate notifications for same plant within 6-hour window (0% false duplicates in 7-day test)
- **SC-004**: System runs continuously for 30+ days without manual intervention or crashes
- **SC-005**: All 3 plants are monitored independently (notifications correctly identify specific plants in 100% of cases)
- **SC-006**: Sensor read errors do not crash system (graceful degradation: continues monitoring functional sensors)
- **SC-007**: System startup to first sensor reading completes within 30 seconds
- **SC-008**: Notifications accurately reflect moisture status (0% false positives in 7-day test: no alerts when moisture ≥40%)

## Assumptions *(optional)*

### Technical Assumptions

- **A-001**: ADS1115 is correctly wired to Raspberry Pi I2C pins (SDA GPIO 2, SCL GPIO 3)
- **A-002**: ADS1115 is configured at default I2C address 0x48
- **A-003**: Capacitive sensors provide analog voltage output proportional to moisture (higher voltage = higher moisture)
- **A-004**: All three capacitive sensors are identical models with same characteristics; a single shared calibration formula (voltage range to 0-100% mapping) applies to all sensors
- **A-005**: Raspberry Pi has internet connectivity for ntfy.sh API access
- **A-006**: System clock is synchronized (accurate timestamps for throttling logic)

### Operational Assumptions

- **A-007**: User has access to ntfy.sh mobile app or web interface to receive notifications
- **A-008**: User waters plants manually when notified (no automated watering system)
- **A-009**: "Plant watered" is detected by moisture rising above threshold + 5% buffer (e.g., 45%)
- **A-010**: Initial plant configuration (names, thresholds) is hardcoded for MVP; database integration is future feature
- **A-011**: System runs on boot via systemd or similar service manager (implementation detail, not specified here)

### Calibration Assumptions

- **A-012**: 40% moisture threshold is appropriate default for common houseplants
- **A-013**: 30-second sampling interval balances responsiveness with CPU/power usage
- **A-014**: 6-hour notification throttle balances reminder frequency with avoiding spam
- **A-015**: 5% hysteresis buffer (45% to reset throttle) prevents notification flapping due to minor moisture fluctuations

## Dependencies *(optional)*

### External Dependencies

- **D-001**: ntfy.sh service availability (external HTTP API for notifications)
- **D-002**: Raspberry Pi I2C hardware interface functionality
- **D-003**: ADS1115 ADC module operational status
- **D-004**: Capacitive moisture sensors operational status

### Future Feature Dependencies

- **D-005**: This feature is designed to support future database integration for per-plant configuration (plant names, custom thresholds, watering history)
- **D-006**: Configuration structure must accommodate future web UI for editing plant profiles
