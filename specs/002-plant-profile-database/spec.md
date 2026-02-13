# Feature Specification: Plant Profile Database

**Feature Branch**: `002-plant-profile-database`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "I want to create a sqlite database that can be run on the Raspberry Pi and it will include a plant-profile for each plant with the following keys plant-name (primary key str), acceptable-moisture-level(float), current-moisture-level(float), date-last-watered (DATE format), needs-watering(bool). The monitoring script will read from this database before every sampling to check if each plant is within its acceptable-moisture-level. If that is not possible the monitor will use the default threshold from the env file. Every time the the moisture levels go above the threshold after a watering the date-last-watered will be populated with the current day's date. When the plant's moisture level is below its threshold needs-watering is set to True and False when it is appropriately watered. current-moisture-level is updated with the moisture level of the given plant at the time of sampling. It is important to note that it is 1 moisture sensor per plant profile so for example I have moisture sensor 1 reading data for plant profile 1 and so on. Plant names are now read from the respective plant-profiles and not hard coded as Plant-A, Plant-B and Plant-C"

## Clarifications

### Session 2026-02-13

- Q: Where should the SQLite database file be stored on the Raspberry Pi filesystem? → A: Project data directory (e.g., `data/plants.db` or `db/plants.db`)
- Q: How should the system handle database write failures during monitoring cycles? → A: Log error and continue monitoring without database updates (sensors still read, notifications still sent, profile updates skipped until database recovers)
- Q: What mechanism should be provided for users to initially create plant profiles? → A: Provide a setup CLI script to create profiles interactively with guided prompts for name, threshold, sensor channel, and input validation
- Q: When checking if a plant needs water, should moisture exactly at the threshold (e.g., 40.0% with 40% threshold) be considered okay or needing water? → A: Use >= for "at or above threshold" (inclusive comparison) - moisture at or above threshold means plant is okay

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Store Individual Plant Profiles (Priority: P1)

As a plant owner, I want to create and store profiles for each of my plants with custom names and moisture preferences, so that each plant can be monitored according to its specific watering needs rather than using a one-size-fits-all threshold.

**Why this priority**: This is the foundation of the feature. Without the ability to store plant-specific profiles, none of the other functionality is possible. This delivers immediate value by allowing personalized plant care.

**Independent Test**: Can be fully tested by creating plant profiles with different names and thresholds, then verifying the data persists across system restarts and can be retrieved accurately.

**Acceptance Scenarios**:

1. **Given** the system has no existing plant profiles, **When** I create a profile for "Basil" with a 45% moisture threshold, **Then** the profile is stored with my custom name and threshold
2. **Given** I have created a plant profile, **When** I restart the Raspberry Pi, **Then** my plant profile and settings are still available
3. **Given** I have three different plants, **When** I create profiles for each with different moisture thresholds (e.g., 30%, 45%, 60%), **Then** each plant retains its individual threshold setting

---

### User Story 2 - Monitor Plants Using Custom Thresholds (Priority: P2)

As a plant owner, I want the monitoring system to check each plant against its own acceptable moisture level (not a global default), so that I receive accurate watering alerts based on each plant's specific needs.

**Why this priority**: This is the primary value proposition - using the stored profiles to improve monitoring accuracy. It builds directly on P1 and delivers the core benefit of personalized monitoring.

**Independent Test**: Can be tested by setting up plants with different thresholds (e.g., cactus at 20%, fern at 60%), letting moisture levels drop, and verifying alerts are sent at the correct thresholds for each plant.

**Acceptance Scenarios**:

1. **Given** I have a cactus profile with 20% threshold and a fern profile with 60% threshold, **When** the monitoring cycle runs, **Then** the cactus is only flagged as needing water when below 20% and the fern when below 60%
2. **Given** my plant's moisture is at 50% and its threshold is 40%, **When** the monitoring cycle runs, **Then** the plant is marked as not needing water
3. **Given** my plant's moisture is at 35% and its threshold is 40%, **When** the monitoring cycle runs, **Then** the plant is marked as needing water
4. **Given** the database is unavailable or corrupted, **When** the monitoring cycle runs, **Then** the system falls back to the default threshold from the environment configuration

---

### User Story 3 - Track Watering History (Priority: P3)

As a plant owner, I want the system to automatically record when each plant was last watered (based on moisture level rising above threshold), so I can track my watering patterns and ensure I'm caring for my plants consistently.

**Why this priority**: This provides historical insight and helps users understand their plant care patterns. While valuable, it's not essential for basic monitoring functionality.

**Independent Test**: Can be tested by watering a dry plant and verifying the date-last-watered field updates to today's date when moisture rises above the threshold.

**Acceptance Scenarios**:

1. **Given** my plant's moisture is below its threshold and marked as needing water, **When** I water the plant and moisture rises above the threshold, **Then** the date-last-watered is set to today's date
2. **Given** my plant was last watered 5 days ago, **When** I view the plant profile, **Then** I can see the date it was last watered
3. **Given** my plant's moisture fluctuates but stays below the threshold, **When** monitoring cycles run, **Then** the date-last-watered is not updated (only updates when crossing from below to above threshold)

---

### User Story 4 - Map Sensors to Named Plants (Priority: P2)

As a plant owner, I want to associate each moisture sensor channel with a specific plant profile by name (e.g., sensor channel 0 monitors "Basil"), so I can identify plants by their actual names in notifications and logs instead of generic labels like "Plant-A".

**Why this priority**: This significantly improves usability by making notifications and logs meaningful. It's essential for multi-plant setups where generic names are confusing.

**Independent Test**: Can be tested by configuring sensor channel 0 to monitor "Tomato" and channel 1 to monitor "Basil", then verifying notifications and logs use these custom names.

**Acceptance Scenarios**:

1. **Given** I have sensor channel 0 configured to monitor my "Basil" plant, **When** the sensor reads low moisture, **Then** the notification says "Basil needs watering" (not "Plant-A needs watering")
2. **Given** I have three sensors monitoring "Tomato", "Basil", and "Oregano", **When** the monitoring cycle runs, **Then** log entries show the actual plant names
3. **Given** I have configured sensor channel 1 to monitor "Fern", **When** I view system status, **Then** the moisture reading is associated with "Fern"

---

### Edge Cases

- What happens when the database file is missing or corrupted?
  - System should fall back to environment file defaults and log a warning
  - Monitoring should continue without plant-specific profiles until database is restored

- What happens when a plant profile exists but no sensor is mapped to it?
  - Plant profile exists in database but is not monitored (no readings, no updates)
  - System logs should indicate which profiles are active (have sensors) vs inactive

- What happens when a sensor channel is configured but no matching plant profile exists in the database?
  - System ignores unmapped sensors (no readings taken, no logs, no notifications)
  - User must create plant profiles before sensors will be monitored
  - System logs a warning at startup listing any unmapped sensor channels

- What happens when acceptable-moisture-level is set to an invalid value (e.g., negative or > 100%)?
  - System should validate profiles on load and reject invalid thresholds
  - Fall back to environment default for that plant and log a warning

- What happens when multiple plant profiles try to use the same sensor channel?
  - Database enforces uniqueness constraint on sensor channel assignments
  - Each sensor channel (0, 1, 2) can be assigned to exactly one plant profile
  - Attempting to assign the same channel to multiple plants results in a validation error

- What happens when the date-last-watered is in the future (clock issue or manual error)?
  - System should accept the value but may want to log an anomaly warning

- What happens when database write operations fail during a monitoring cycle?
  - System logs the error and continues monitoring without database updates
  - Sensor readings and notifications continue to function normally
  - Profile updates (current moisture, needs-watering flag, date-last-watered) are skipped until database recovers
  - System retries database operations on next monitoring cycle

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST store plant profiles in a persistent database that survives system restarts
- **FR-002**: System MUST support plant profiles with the following attributes: plant name, acceptable moisture threshold, current moisture level, date last watered, and watering status flag
- **FR-003**: System MUST use plant name as the unique identifier for each profile (no duplicate plant names)
- **FR-004**: System MUST read plant profiles from the database before each monitoring cycle to determine plant-specific thresholds
- **FR-005**: System MUST fall back to the environment file default threshold if the database cannot be read or if a specific plant profile cannot be loaded
- **FR-006**: System MUST update the current moisture level in the database for each plant after every sensor reading
- **FR-007**: System MUST set the watering status flag to true when a plant's current moisture is below its acceptable threshold (using < comparison)
- **FR-008**: System MUST set the watering status flag to false when a plant's current moisture is at or above its acceptable threshold (using >= comparison)
- **FR-009**: System MUST record the current date as the date-last-watered when a plant's moisture level rises above its threshold after being below it (indicating the plant was watered)
- **FR-010**: System MUST associate each moisture sensor channel (0, 1, 2) with exactly one plant profile
- **FR-011**: System MUST use the plant name from the database profile in all notifications, logs, and status displays (replacing hardcoded names like "Plant-A", "Plant-B", "Plant-C")
- **FR-012**: System MUST validate plant profiles on load to ensure acceptable-moisture-level is between 0% and 100%
- **FR-013**: System MUST handle database unavailability gracefully by logging warnings and continuing operation with fallback defaults
- **FR-014**: System MUST enforce uniqueness constraint on sensor channel assignments (each channel can be assigned to only one plant profile)
- **FR-015**: System MUST ignore sensor channels that have no matching plant profile in the database and log a warning at startup listing unmapped channels
- **FR-016**: System MUST provide an interactive CLI setup script that prompts users for plant name, acceptable moisture threshold, and sensor channel assignment with input validation
- **FR-017**: System MUST continue sensor readings and notifications when database write operations fail, logging errors and skipping profile updates until the database recovers

### Key Entities

- **Plant Profile**: Represents a monitored plant with its configuration and current state
  - Plant name (unique identifier, user-friendly string)
  - Acceptable moisture threshold (percentage value specific to plant type)
  - Current moisture level (most recent sensor reading)
  - Date last watered (timestamp of most recent watering event)
  - Needs watering status (boolean flag for current state)
  - Sensor channel mapping (which hardware sensor monitors this plant)

- **Sensor-to-Plant Mapping**: Associates a physical sensor channel with a plant profile
  - One sensor channel per plant profile (1:1 relationship)
  - Enables correlation between hardware readings and plant identities

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can create plant profiles with custom names and individual moisture thresholds
- **SC-002**: The monitoring system correctly evaluates each plant against its own threshold (not a global default) during every monitoring cycle
- **SC-003**: Plant profile data (name, threshold, last watered date) persists across system restarts and power cycles
- **SC-004**: Watering events are automatically detected and recorded when moisture rises from below to above the threshold
- **SC-005**: Notifications and logs display actual plant names (e.g., "Basil") instead of generic labels (e.g., "Plant-A")
- **SC-006**: The monitoring system continues to operate when the database is unavailable, falling back to environment defaults
- **SC-007**: All database updates (moisture levels, watering status, last watered date) complete within each monitoring cycle without blocking sensor readings
- **SC-008**: Users can maintain accurate watering history for each plant, showing the most recent watering date

## Assumptions

- **A-001**: The database file will be stored in a project data directory (e.g., `data/plants.db`) that is user-writable and does not require elevated permissions
- **A-002**: Database schema migrations or versioning are out of scope for this feature (initial schema only)
- **A-003**: Manual database editing tools (CLI or GUI) for managing plant profiles may be added in future but are not required for this feature
- **A-004**: The existing three sensor channels (0, 1, 2) are sufficient; no additional sensors will be added
- **A-005**: Plant profiles will be initially created through an interactive CLI setup script that prompts for plant name, moisture threshold, and sensor channel assignment
- **A-006**: Sensor channel assignment to plants is configured in the database and does not need to be changed during monitoring
- **A-007**: Concurrent access to the database (multiple processes) is not required; only the monitoring script accesses the database

## Dependencies

- **D-001**: SQLite database engine availability on Raspberry Pi OS
- **D-002**: Existing moisture monitoring system (sensors, ADS1115, current monitoring script) must continue to function
- **D-003**: Environment configuration file must retain the default threshold setting for fallback purposes

## Out of Scope

- **OS-001**: Ongoing management interfaces for plant profiles (web UI, mobile app, full CRUD CLI) - initial setup via CLI script is in scope per FR-016
- **OS-002**: Database backup and recovery mechanisms
- **OS-003**: Multi-user access or authentication for database modifications
- **OS-004**: Historical trend data beyond the most recent watering date
- **OS-005**: Support for more than three plants (limited by hardware sensor channels)
- **OS-006**: Database schema migrations or versioning
- **OS-007**: Export/import of plant profiles
- **OS-008**: Notifications based on watering history (e.g., "Plant not watered in X days")
