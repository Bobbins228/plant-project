# Feature Specification: BME688 Environmental Monitoring

**Feature Branch**: `003-bme688-environmental`
**Created**: 2026-02-13
**Status**: Draft
**Input**: User description: "I want to read live environmental data to 2 decimal points from a BME688 during monitoring. The BME688 is using the SDA and SCL GPIO pins as well as the ADS1115. Use the bme680 Python package for gathering data from the sensor. I want temperature, humidity, gas and pressure data to be monitored live similar to soil moisture. This data is not required to be included in the plant profile it is purely live"

## Clarifications

### Session 2026-02-13

- Q: How should the system coordinate I2C bus access between the moisture sensor ADC (ADS1115) and environmental sensor (BME688) to prevent communication conflicts? → A: Read sensors sequentially within each monitoring cycle (moisture sensors first, then environmental sensor)
- Q: How should the system handle situations where the environmental sensor reading takes too long or hangs? → A: Skip environmental reading if it exceeds a timeout threshold and continue with plant monitoring
- Q: How should the system handle environmental sensor readings that fall outside the expected ranges? → A: Display the out-of-range values with a warning indicator but do not reject them
- Q: How should the system handle situations where only some environmental readings succeed while others fail? → A: Display successful readings and show error indicators for failed readings
- Q: How should the system handle environmental sensor readings that fluctuate rapidly between monitoring cycles? → A: Display raw sensor readings without smoothing or filtering

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View Real-Time Environmental Conditions (Priority: P1)

Users want to monitor environmental conditions (temperature, humidity, air quality, atmospheric pressure) in real-time alongside plant moisture levels to understand the complete growing environment and identify correlations between environmental factors and plant health.

**Why this priority**: Environmental conditions directly affect plant health and water needs. Displaying this data during monitoring provides critical context for plant care decisions without requiring additional tools or manual measurements.

**Independent Test**: Can be fully tested by running the monitoring system with an environmental sensor connected and verifying that temperature, humidity, gas resistance, and pressure readings appear in the monitoring output at each cycle, formatted to 2 decimal places.

**Acceptance Scenarios**:

1. **Given** the monitoring system is running with a connected environmental sensor, **When** a monitoring cycle executes, **Then** current temperature (°C), humidity (%), gas resistance (Ω), and atmospheric pressure (hPa) are displayed to 2 decimal places
2. **Given** environmental readings are being captured, **When** displaying monitoring output, **Then** environmental data appears alongside plant moisture levels in a clear, readable format
3. **Given** the monitoring system is running, **When** environmental conditions change (temperature rises/falls, humidity changes), **Then** the displayed values reflect the current conditions within one monitoring cycle

---

### User Story 2 - Continue Plant Monitoring on Environmental Sensor Failure (Priority: P2)

Users want the plant monitoring system to continue operating and monitoring plant moisture even if the environmental sensor fails, becomes disconnected, or encounters errors, ensuring core plant watering notifications are never disrupted by environmental sensor issues.

**Why this priority**: Plant moisture monitoring is the critical function - environmental data is supplementary. System reliability requires isolating environmental sensor failures from core plant monitoring operations.

**Independent Test**: Can be tested by disconnecting the environmental sensor or simulating sensor errors while the monitoring system runs, and verifying that plant moisture readings and watering notifications continue to function normally with appropriate warnings about environmental sensor status.

**Acceptance Scenarios**:

1. **Given** the monitoring system is running, **When** the environmental sensor is disconnected or fails, **Then** plant moisture monitoring continues and a warning indicates environmental data is unavailable
2. **Given** an environmental sensor error occurs, **When** reading environmental data fails, **Then** the system logs the error and continues with the next monitoring cycle without crashing
3. **Given** the environmental sensor is unavailable, **When** displaying monitoring output, **Then** plant moisture data is shown normally with a message indicating environmental readings are unavailable

---

### Edge Cases

- What happens if the environmental sensor is not detected at system startup?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST read environmental sensor data during each monitoring cycle
- **FR-002**: System MUST display temperature in degrees Celsius to 2 decimal places
- **FR-003**: System MUST display relative humidity as a percentage to 2 decimal places
- **FR-004**: System MUST display gas resistance in ohms to 2 decimal places
- **FR-005**: System MUST display atmospheric pressure in hectopascals (hPa) to 2 decimal places
- **FR-006**: System MUST display environmental data in the same monitoring output as plant moisture levels
- **FR-007**: System MUST continue plant moisture monitoring if environmental sensor reads fail
- **FR-008**: System MUST log warnings when environmental sensor is unavailable or returns errors
- **FR-009**: System MUST NOT store environmental data in the plant profile database (live display only)
- **FR-010**: System MUST detect environmental sensor presence at startup and log initialization status
- **FR-011**: Environmental readings MUST be timestamped to match the monitoring cycle timestamp
- **FR-012**: System MUST read sensors sequentially to avoid I2C bus conflicts (moisture sensors first, then environmental sensor)
- **FR-013**: System MUST skip environmental sensor reading if it exceeds timeout threshold, log a warning, and continue plant monitoring without delay
- **FR-014**: System MUST display out-of-range environmental readings (outside -10°C to 50°C for temperature, 0-100% for humidity, 900-1100 hPa for pressure) with a warning indicator rather than rejecting them
- **FR-015**: System MUST display successful environmental readings and show error indicators for failed readings when partial sensor failures occur (e.g., temperature succeeds but humidity fails)
- **FR-016**: System MUST display raw environmental sensor readings without smoothing, averaging, or filtering to provide transparent view of actual conditions

### Key Entities

- **EnvironmentalReading**: Represents a snapshot of environmental conditions at a point in time
  - Temperature (°C)
  - Humidity (%)
  - Gas resistance (Ω) - indicates air quality
  - Atmospheric pressure (hPa)
  - Timestamp
  - Validity flag (indicates if reading is valid or sensor error occurred)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Environmental readings (temperature, humidity, gas, pressure) display in real-time during each monitoring cycle
- **SC-002**: All environmental values are accurate to 2 decimal places
- **SC-003**: Users can observe environmental conditions alongside plant moisture levels without switching tools or interfaces
- **SC-004**: Plant moisture monitoring continues with 100% uptime even when environmental sensor fails
- **SC-005**: Environmental sensor initialization status is clearly indicated in startup logs
- **SC-006**: Users can correlate environmental changes with plant moisture trends by observing both datasets in the same monitoring output

## Assumptions

- Environmental sensor uses the same I2C bus (SDA/SCL pins) as the existing moisture sensor ADC
- Monitoring cycle interval remains unchanged - environmental readings occur at the same frequency as plant moisture readings
- Users do not need historical environmental data stored for analysis (current/live values only)
- Standard indoor environmental ranges expected (temperature: -10°C to 50°C, humidity: 0-100%, pressure: 900-1100 hPa)
- Environmental data is informational only - does not trigger automated actions or notifications
- Users interpret gas resistance values directly (no air quality index calculation required)

## Constraints

- Environmental sensor and moisture sensor ADC must coexist on the same I2C bus
- Environmental sensor failures must not impact core plant monitoring functionality
- No database schema changes required (environmental data is ephemeral/live only)
- Environmental readings must use minimal processing time to avoid delaying plant monitoring cycles
