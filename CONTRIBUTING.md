# Contributing to Plant Monitoring System

Thank you for your interest in contributing! This project follows strict Test-First Development (TDD) and specific architectural patterns.

## Project Constitution

This project is governed by three core principles defined in [`.specify/memory/constitution.md`](.specify/memory/constitution.md):

### I. Test-First (NON-NEGOTIABLE)

- **Tests written FIRST**: Before any implementation code, tests must be drafted, reviewed, and approved
- **Red-Green-Refactor cycle strictly enforced**:
  1. Write failing test (RED)
  2. Write minimal code to pass (GREEN)
  3. Refactor for quality (REFACTOR)
- **No test = No merge**: All PRs require tests

### II. Library-First

- Core functionality in `src/lib/` (reusable, framework-agnostic)
- CLI/UI in `src/cli/` (thin wrapper, no business logic)
- Single project structure (no microservices for MVP)

### III. Observability

- Structured logging at appropriate levels (DEBUG/INFO/ERROR)
- All user-facing errors must be actionable
- Metrics and monitoring built-in from day one

## Development Workflow

### 1. Feature Development Process

We use the Specify framework for feature development:

```bash
# 1. Create feature specification
/speckit.specify <feature description>

# 2. Clarify requirements (if needed)
/speckit.clarify

# 3. Generate implementation plan
/speckit.plan

# 4. Generate task list
/speckit.tasks

# 5. Implement following Test-First workflow
# See tasks.md for detailed task breakdown
```

### 2. Test-First Workflow (MANDATORY)

Every feature follows this strict workflow:

#### Step 1: Write Tests (BEFORE Implementation)

```bash
# Example: Adding new sensor type support
# File: tests/integration/test_analog_sensor.py

def test_analog_sensor_reads_voltage():
    """Test analog sensor voltage reading."""
    sensor = AnalogSensor(channel=0)
    voltage = sensor.read_voltage()

    assert voltage is not None
    assert 0.0 <= voltage <= 5.0

def test_analog_sensor_converts_to_percentage():
    """Test voltage conversion to percentage."""
    sensor = AnalogSensor(channel=0, min_voltage=1.0, max_voltage=3.0)

    # Test boundary values
    assert sensor.voltage_to_percentage(1.0) == 0.0
    assert sensor.voltage_to_percentage(3.0) == 100.0
    assert sensor.voltage_to_percentage(2.0) == 50.0
```

#### Step 2: Run Tests (Should FAIL)

```bash
pytest tests/integration/test_analog_sensor.py -v

# Expected output:
# FAILED tests/integration/test_analog_sensor.py::test_analog_sensor_reads_voltage
# ModuleNotFoundError: No module named 'analog_sensor'
```

#### Step 3: Implement Minimal Code

```python
# File: src/lib/analog_sensor.py

class AnalogSensor:
    """Analog sensor interface for voltage reading."""

    def __init__(self, channel: int, min_voltage: float = 0.0, max_voltage: float = 5.0):
        self.channel = channel
        self.min_voltage = min_voltage
        self.max_voltage = max_voltage

    def read_voltage(self) -> float:
        # Minimal implementation to pass test
        # TODO: Add actual hardware interface
        return 2.5  # Placeholder

    def voltage_to_percentage(self, voltage: float) -> float:
        voltage_range = self.max_voltage - self.min_voltage
        return ((voltage - self.min_voltage) / voltage_range) * 100.0
```

#### Step 4: Run Tests (Should PASS)

```bash
pytest tests/integration/test_analog_sensor.py -v

# Expected output:
# PASSED tests/integration/test_analog_sensor.py::test_analog_sensor_reads_voltage
# PASSED tests/integration/test_analog_sensor.py::test_analog_sensor_converts_to_percentage
```

#### Step 5: Refactor

```python
# Refactor for production quality
# Add error handling, validation, documentation

class AnalogSensor:
    """Analog sensor interface for voltage reading.

    Supports configurable voltage ranges and automatic percentage conversion.
    """

    def __init__(self, channel: int, min_voltage: float = 0.0, max_voltage: float = 5.0):
        """Initialize analog sensor.

        Args:
            channel: ADC channel number (0-3)
            min_voltage: Voltage representing 0% (default: 0.0V)
            max_voltage: Voltage representing 100% (default: 5.0V)

        Raises:
            ValueError: If channel out of range or voltage range invalid
        """
        if not 0 <= channel <= 3:
            raise ValueError(f"Channel must be 0-3, got {channel}")
        if min_voltage >= max_voltage:
            raise ValueError(f"min_voltage must be < max_voltage")

        self.channel = channel
        self.min_voltage = min_voltage
        self.max_voltage = max_voltage
        self.logger = logging.getLogger(__name__)

    def read_voltage(self) -> Optional[float]:
        """Read voltage from sensor.

        Returns:
            Voltage value (V), or None if read failed
        """
        try:
            # Actual hardware interface
            from src.lib.hardware import read_adc_channel
            voltage = read_adc_channel(self.channel)
            self.logger.debug(f"Channel {self.channel}: {voltage:.3f}V")
            return voltage
        except Exception as e:
            self.logger.error(f"Failed to read channel {self.channel}: {e}")
            return None

    def voltage_to_percentage(self, voltage: float) -> float:
        """Convert voltage to percentage using linear calibration.

        Args:
            voltage: Voltage reading (V)

        Returns:
            Percentage value (0-100)
        """
        voltage_range = self.max_voltage - self.min_voltage
        percentage = ((voltage - self.min_voltage) / voltage_range) * 100.0
        return max(0.0, min(100.0, percentage))  # Clamp to 0-100
```

#### Step 6: Verify Tests Still Pass

```bash
pytest tests/integration/test_analog_sensor.py -v

# All tests should still pass after refactoring
```

## Code Structure

### Project Layout

```
plant-project/
├── src/
│   ├── lib/              # Core reusable library (Library-First)
│   │   ├── config.py     # Configuration management
│   │   ├── sensor.py     # Sensor hardware interface
│   │   ├── notifier.py   # Notification client
│   │   └── moisture_monitor.py  # Core monitoring logic
│   ├── cli/              # CLI entry point (thin wrapper)
│   │   └── monitor.py    # Daemon entry point
│   └── models/           # Data models
│       ├── plant.py      # Plant entity
│       ├── sensor_reading.py  # Sensor reading event
│       └── notification_event.py  # Notification event
├── tests/
│   ├── unit/             # Component unit tests
│   ├── integration/      # Cross-component tests
│   └── contract/         # External API tests
├── config/               # Configuration files
│   ├── monitor.env.example  # Example configuration
│   └── plant-monitor.service  # systemd service
└── specs/                # Design documentation
    └── 001-moisture-monitoring/
        ├── spec.md       # Feature specification
        ├── plan.md       # Implementation plan
        ├── tasks.md      # Task breakdown
        └── quickstart.md # Quick start guide
```

### Code Conventions

#### Python Style

- Follow PEP 8
- Use type hints for all function signatures
- Maximum line length: 100 characters
- Docstrings: Google style

```python
def read_sensor(channel: int, retries: int = 3) -> Optional[float]:
    """Read voltage from sensor channel with retry logic.

    Args:
        channel: ADC channel number (0-3)
        retries: Number of retry attempts on failure

    Returns:
        Voltage reading (V), or None if all retries failed

    Raises:
        ValueError: If channel number invalid
    """
    pass
```

#### Logging Conventions

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG: Detailed diagnostic information
logger.debug(f"Channel {channel}: voltage={voltage:.3f}V, raw={raw_value}")

# INFO: General informational messages
logger.info(f"Sensor calibration complete: dry={dry_v:.2f}V, wet={wet_v:.2f}V")

# WARNING: Recoverable issues
logger.warning(f"Sensor read timeout on channel {channel}, retrying...")

# ERROR: Serious issues that prevent operation
logger.error(f"Failed to initialize I2C bus: {e}", exc_info=True)

# CRITICAL: System-level failures
logger.critical(f"Configuration validation failed: {e}")
```

#### Error Handling

```python
# Good: Specific exception handling
try:
    voltage = sensor.read_channel(0)
except ValueError as e:
    logger.error(f"Invalid channel: {e}")
    return None
except IOError as e:
    logger.error(f"I2C communication error: {e}")
    return None

# Bad: Broad exception catching
try:
    voltage = sensor.read_channel(0)
except Exception as e:  # Too broad!
    logger.error(f"Error: {e}")
    return None
```

## Pull Request Process

### 1. Before Starting

- Check existing issues and PRs to avoid duplicates
- Review project constitution (.specify/memory/constitution.md)
- Read relevant design docs (specs/*/spec.md, plan.md)

### 2. Branch Naming

```bash
# Feature branches
git checkout -b 002-new-sensor-support

# Bug fix branches
git checkout -b fix-sensor-calibration-bug

# Documentation branches
git checkout -b docs-deployment-guide
```

### 3. Development

```bash
# 1. Write tests FIRST
# Create test file in tests/

# 2. Run tests (should FAIL)
pytest tests/integration/test_new_feature.py -v

# 3. Implement minimal code

# 4. Run tests (should PASS)
pytest tests/integration/test_new_feature.py -v

# 5. Refactor for quality

# 6. Run ALL tests
pytest -v

# 7. Commit with descriptive message
git add tests/integration/test_new_feature.py src/lib/new_feature.py
git commit -m "feat: add new sensor support

- Add analog sensor voltage reading
- Add voltage-to-percentage conversion
- Include calibration support

Closes #42"
```

### 4. Commit Message Format

Follow Conventional Commits specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `test`: Adding or updating tests
- `refactor`: Code refactoring (no functional change)
- `perf`: Performance improvement
- `chore`: Maintenance tasks

**Examples**:

```bash
feat(sensor): add analog sensor support

Implement AnalogSensor class with voltage reading and percentage
conversion. Includes configurable voltage ranges and error handling.

Closes #42

---

fix(monitor): prevent notification spam during startup

Add throttle check before sending notifications. Fixes issue where
all dry plants would send multiple notifications during daemon startup.

Fixes #58

---

test(integration): add multi-plant monitoring tests

Add comprehensive tests for independent plant monitoring:
- Test 3 plants with independent state
- Test simultaneous notifications
- Test throttle isolation

Related to #45
```

### 5. Pull Request Template

```markdown
## Description

Brief description of changes.

## Type of Change

- [ ] Bug fix (non-breaking change fixing an issue)
- [ ] New feature (non-breaking change adding functionality)
- [ ] Breaking change (fix or feature causing existing functionality to change)
- [ ] Documentation update

## Test-First Checklist

- [ ] Tests written BEFORE implementation
- [ ] Tests initially failed (RED)
- [ ] Implementation makes tests pass (GREEN)
- [ ] Code refactored for quality (REFACTOR)
- [ ] All tests pass (`pytest -v`)

## Testing

Describe how this was tested:
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed (if applicable)

## Documentation

- [ ] Code includes docstrings (Google style)
- [ ] README updated (if needed)
- [ ] CHANGELOG updated (if needed)

## Constitution Compliance

- [ ] Follows Test-First principle (tests written before code)
- [ ] Follows Library-First architecture (logic in src/lib/)
- [ ] Includes observability (structured logging)

## Related Issues

Closes #XX
```

### 6. Review Process

All PRs require:
1. **Tests**: Complete test coverage following Test-First
2. **Documentation**: Docstrings and updated docs
3. **Constitution compliance**: Meets all 3 principles
4. **CI passing**: All automated checks pass
5. **Code review**: Approval from maintainer

## Testing Guidelines

### Test Categories

#### Unit Tests (`tests/unit/`)
- Test individual components in isolation
- Mock external dependencies
- Fast execution (<1s per test)

```python
# tests/unit/test_config.py
def test_config_validation():
    """Test configuration validation logic."""
    with pytest.raises(ValueError):
        MonitorConfig(moisture_threshold=150.0)  # Invalid > 100%
```

#### Integration Tests (`tests/integration/`)
- Test cross-component workflows
- May use mocked hardware
- Test realistic scenarios

```python
# tests/integration/test_single_plant_alert.py
def test_dry_plant_sends_notification():
    """Test complete workflow from sensor read to notification."""
    # Setup, execute, verify
```

#### Contract Tests (`tests/contract/`)
- Test external API integrations
- Verify API contract compliance
- May use actual API (with rate limiting consideration)

```python
# tests/contract/test_ntfy_api.py
def test_ntfy_api_returns_200_on_success():
    """Verify ntfy.sh API returns 200 on successful notification."""
    # Test actual API behavior
```

### Running Tests

```bash
# Run all tests
pytest -v

# Run specific category
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/contract/ -v

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/integration/test_single_plant_alert.py -v

# Run specific test
pytest tests/integration/test_single_plant_alert.py::test_dry_plant_sends_notification -v

# Run with markers
pytest -m unit  # Run only unit tests
pytest -m integration  # Run only integration tests
```

## Development Environment

### Local Setup (Mac/Linux - No Hardware)

```bash
# Clone repository
git clone https://github.com/yourusername/plant-project.git
cd plant-project

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests (mocked hardware)
pytest -v

# The codebase gracefully handles missing I2C hardware
# Tests use mocked sensor interfaces
```

### Raspberry Pi Setup (With Hardware)

See [DEPLOYMENT.md](DEPLOYMENT.md) for complete Raspberry Pi setup.

## Code Review Checklist

When reviewing PRs, verify:

- [ ] **Test-First**: Tests exist and were written before implementation
- [ ] **Tests pass**: `pytest -v` shows all green
- [ ] **Code quality**: Clean, readable, well-documented
- [ ] **Type hints**: All functions have type annotations
- [ ] **Docstrings**: Google-style docstrings on all public functions/classes
- [ ] **Error handling**: Appropriate exceptions and logging
- [ ] **Constitution compliance**: Follows all 3 principles
- [ ] **No hardcoded values**: Configuration via config file or environment
- [ ] **Logging**: Structured logs at appropriate levels
- [ ] **Security**: No credentials in code, validated inputs
- [ ] **Performance**: No obvious performance issues

## Questions?

- Review project documentation in `specs/` directory
- Check [README.md](README.md) for overview
- See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment guide
- Read [.specify/memory/constitution.md](.specify/memory/constitution.md) for governance

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
