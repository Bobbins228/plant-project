# Quickstart: BME688 Environmental Monitoring

**Feature**: 003-bme688-environmental
**Date**: 2026-02-13
**Audience**: Users setting up environmental monitoring alongside plant moisture monitoring

## Overview

This guide shows you how to add real-time environmental monitoring (temperature, humidity, air quality, atmospheric pressure) to your plant monitoring system using a BME688 sensor.

## Prerequisites

- Raspberry Pi with plant monitoring system installed and working
- BME688 environmental sensor connected to I2C bus (SDA/SCL pins)
- BME688 shares I2C bus with existing ADS1115 moisture sensor ADC
- Python 3.9+ with `bme680` package installed

## Hardware Setup

### I2C Connection

The BME688 sensor shares the same I2C bus as the ADS1115:

```
Raspberry Pi GPIO Pins:
├── Pin 3 (SDA) ──┬── ADS1115 SDA
│                 └── BME688 SDA
├── Pin 5 (SCL) ──┬── ADS1115 SCL
│                 └── BME688 SCL
├── 3.3V ─────────┬── ADS1115 VDD
│                 └── BME688 VIN
└── GND ──────────┬── ADS1115 GND
                  └── BME688 GND
```

**Important**: Both sensors share the same I2C bus. The system reads sensors sequentially (moisture first, then environmental) to prevent conflicts.

### Verify I2C Connection

Check that both sensors are detected:

```bash
i2cdetect -y 1
```

Expected output:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- --
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
40: -- -- -- -- -- -- -- -- 48 -- -- -- -- -- -- --  <- ADS1115 (0x48)
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
60: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- --
70: -- -- -- -- -- -- 76 --                          <- BME688 (0x76 or 0x77)
```

**If BME688 not detected**: Check wiring, ensure sensor has 3.3V power

## Installation

### Install Dependencies

```bash
# Install BME680 library
uv pip install bme680

# Or using pip
pip install bme680
```

### Verify Installation

```bash
python3 -c "import bme680; print('BME680 library installed successfully')"
```

## Quick Start

### Step 1: Start Monitoring with Environmental Data

Simply run the existing monitoring script - environmental data will automatically display if sensor is detected:

```bash
uv run python3 src/cli/monitor.py
```

### Step 2: View Environmental Data

You'll see environmental data alongside plant moisture levels:

```
2026-02-13 15:30:00 - INFO - ============================================================
2026-02-13 15:30:00 - INFO - Environmental sensor initialized successfully
2026-02-13 15:30:00 - INFO - ============================================================
2026-02-13 15:30:00 - INFO - Read 3 sensors: Snake Plant: 42.0% (OK), Boston Fern: 38.0% (DRY), Money Plant: 50.0% (OK)
2026-02-13 15:30:00 - INFO - Environment: Temp: 22.45°C, Humidity: 55.67%, Pressure: 1013.25 hPa, Gas: 12345.67 Ω
2026-02-13 15:30:00 - INFO - Notification sent: Boston Fern needs watering (moisture: 38.0%)
```

### Step 3: Interpret Environmental Data

**Temperature (°C)**:
- Typical indoor range: 18-25°C
- Values outside -10°C to 50°C show ⚠️ warning

**Humidity (%)**:
- Typical indoor range: 30-60%
- Ideal for most plants: 40-60%

**Pressure (hPa)**:
- Sea level: ~1013 hPa
- Values outside 900-1100 hPa show ⚠️ warning

**Gas Resistance (Ω)**:
- Higher values = better air quality
- Typical indoor: 10,000-100,000 Ω
- Very low values (<10,000 Ω) may indicate poor air quality

## Common Scenarios

### Scenario 1: Environmental Sensor Not Detected

If BME688 is not connected or not detected:

```
2026-02-13 15:30:00 - WARNING - Environmental sensor not detected at I2C address 0x76
2026-02-13 15:30:00 - INFO - Read 3 sensors: Snake Plant: 42.0% (OK), Boston Fern: 38.0% (DRY), Money Plant: 50.0% (OK)
2026-02-13 15:30:00 - INFO - Environment: UNAVAILABLE
```

**Plant monitoring continues normally** - environmental data is supplementary.

### Scenario 2: Out-of-Range Temperature

High temperature warning:

```
2026-02-13 15:30:00 - INFO - Read 3 sensors: Snake Plant: 42.0% (OK), Boston Fern: 38.0% (DRY), Money Plant: 50.0% (OK)
2026-02-13 15:30:00 - INFO - Environment: Temp: 55.23°C ⚠️ OUT OF RANGE, Humidity: 45.67%, Pressure: 1013.25 hPa, Gas: 12345.67 Ω
```

**Action**: Value is displayed with warning indicator. Check sensor placement or environmental conditions.

### Scenario 3: Partial Sensor Failure

Some readings succeed, others fail:

```
2026-02-13 15:30:00 - INFO - Read 3 sensors: Snake Plant: 42.0% (OK), Boston Fern: 38.0% (DRY), Money Plant: 50.0% (OK)
2026-02-13 15:30:00 - INFO - Environment: Temp: 22.45°C, Humidity: ERROR, Pressure: 1013.25 hPa, Gas: ERROR
2026-02-13 15:30:00 - WARNING - Partial environmental sensor read: humidity, gas_resistance failed
```

**Action**: Successful readings displayed, failed readings show ERROR. Plant monitoring unaffected.

### Scenario 4: Sensor Read Timeout

Environmental sensor takes too long:

```
2026-02-13 15:30:00 - WARNING - Environmental sensor read timeout after 2.0 seconds - skipping this cycle
2026-02-13 15:30:00 - INFO - Read 3 sensors: Snake Plant: 42.0% (OK), Boston Fern: 38.0% (DRY), Money Plant: 50.0% (OK)
2026-02-13 15:30:00 - INFO - Environment: TIMEOUT
```

**Action**: Environmental reading skipped, plant monitoring continues. Next cycle will attempt environmental read again.

## Correlating Environmental and Plant Data

Use environmental data to understand plant behavior:

### High Temperature + Low Humidity → Faster Water Consumption

```
2026-02-13 12:00:00 - Environment: Temp: 28.50°C, Humidity: 25.30%
2026-02-13 12:00:00 - Snake Plant: 45.0% (OK)

2026-02-13 18:00:00 - Environment: Temp: 28.45°C, Humidity: 24.80%
2026-02-13 18:00:00 - Snake Plant: 30.0% (DRY)
```

**Observation**: Hot, dry conditions caused rapid moisture loss (45% → 30% in 6 hours)

### Low Temperature → Slower Water Consumption

```
2026-02-13 08:00:00 - Environment: Temp: 16.50°C, Humidity: 65.30%
2026-02-13 08:00:00 - Boston Fern: 50.0% (OK)

2026-02-14 08:00:00 - Environment: Temp: 16.20°C, Humidity: 66.10%
2026-02-14 08:00:00 - Boston Fern: 48.0% (OK)
```

**Observation**: Cool, humid conditions slowed moisture loss (50% → 48% in 24 hours)

## Troubleshooting

### Environmental Sensor Not Initializing

**Symptom**: `WARNING - Environmental sensor not detected`

**Solutions**:
1. Check I2C wiring (SDA, SCL, VIN, GND)
2. Verify I2C address with `i2cdetect -y 1`
3. Try alternate I2C address (0x77 instead of 0x76)
4. Check 3.3V power supply to sensor

### Environmental Data Shows All ERROR

**Symptom**: `Environment: Temp: ERROR, Humidity: ERROR, Pressure: ERROR, Gas: ERROR`

**Solutions**:
1. Sensor may need warm-up (wait 2-3 monitoring cycles)
2. Check I2C bus not overloaded
3. Verify sensor not damaged
4. Check system logs for I2C communication errors

### Plant Monitoring Delayed

**Symptom**: Monitoring cycles take longer than expected

**Possible Cause**: Environmental sensor reads timing out repeatedly

**Solution**: Check sensor health, verify I2C connections stable

### Gas Resistance Always Very Low

**Symptom**: Gas resistance <1000 Ω consistently

**Possible Causes**:
1. Poor air quality (VOCs present)
2. Sensor heater not functioning
3. First few readings after startup (sensor warming up)

**Solution**: Wait 5-10 minutes for sensor to stabilize, check air quality

## Advanced Usage

### Check Sensor Status Programmatically

```python
from src.lib.environmental_sensor import EnvironmentalSensorReader

sensor = EnvironmentalSensorReader()
if sensor.is_available():
    reading = sensor.read()
    print(f"Temperature: {reading.temperature:.2f}°C")
else:
    print("Sensor not available")
```

### Understand Gas Resistance Values

Gas resistance indicates air quality (higher = better):

- **>100,000 Ω**: Excellent air quality
- **50,000-100,000 Ω**: Good air quality
- **10,000-50,000 Ω**: Moderate air quality
- **<10,000 Ω**: Poor air quality (VOCs/pollutants present)

**Note**: First readings after startup may be inaccurate while sensor heater stabilizes.

## Next Steps

1. **Monitor trends**: Observe how environmental conditions affect plant moisture levels over several days
2. **Adjust watering**: Use environmental data to inform watering decisions (hot/dry days need more frequent watering)
3. **Improve growing conditions**: Use gas resistance to identify air quality issues

## Reference

- **Environmental Sensor Library**: `src/lib/environmental_sensor.py`
- **Data Model**: `src/models/environmental_reading.py`
- **Monitoring Integration**: `src/lib/moisture_monitor.py`
- **Full Specification**: [spec.md](./spec.md)
- **Implementation Plan**: [plan.md](./plan.md)
