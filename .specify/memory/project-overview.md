# Plant Project Overview

**Project Type**: IoT Environmental Monitoring System
**Platform**: Raspberry Pi 4B
**Created**: 2026-02-13
**Status**: Planning

## What is it?

An automated soil moisture and environmental monitoring system that tracks multiple plants, alerts when watering is needed, and provides real-time environmental data through a web interface.

## Problem Statement

Plant care requires constant monitoring of soil moisture levels and environmental conditions. Manual checking is time-consuming, inconsistent, and often leads to under/over-watering. This system automates monitoring and provides timely watering notifications based on each plant's specific needs.

## Target Users

- Home gardeners managing multiple plants
- Indoor plant enthusiasts
- Small-scale greenhouse operators
- Anyone wanting data-driven plant care

## Core Capabilities

### 1. Multi-Plant Soil Moisture Monitoring
- Monitor up to 3 plants simultaneously via capacitive moisture sensors
- Each plant has a custom profile with acceptable moisture thresholds
- Continuous monitoring of soil moisture levels
- Alert when moisture drops below plant-specific thresholds

### 2. Plant Profile Management
- Store custom information per plant:
  - Plant name
  - Acceptable moisture level (threshold)
  - Date last watered
  - Additional plant-specific metadata
- Edit and view plant profiles via web interface

### 3. Environmental Monitoring
- Real-time environmental data from BME688 sensor:
  - Temperature
  - Humidity
  - Pressure
  - Gas resistance (air quality)
- Live display in web interface

### 4. Notification System
- Push notifications via ntfy.sh when watering needed
- Plant-specific notifications (e.g., "Plant A needs watering")
- Configurable notification topics

### 5. Web Interface
- Display live environmental data
- View current moisture levels for all plants
- Edit plant profiles
- View watering history

## Hardware Components

### Raspberry Pi 4B
- Main computing platform
- Runs monitoring script continuously
- Hosts web application

### Sensors (I2C Connected via SDA/SCL GPIO Pins)

**Capacitive Soil Moisture Sensors (x3)**
- Connected via ADS1115 ADC (Analog-to-Digital Converter)
- One sensor per plant
- Capacitive design prevents corrosion

**ADS1115 ADC Module**
- 16-bit precision
- I2C interface to Raspberry Pi
- Reads analog moisture sensor values
- I2C address: 0x48 (default)

**BME688 Environmental Sensor**
- I2C interface to Raspberry Pi
- Measures: temperature, humidity, pressure, gas resistance
- I2C address: 0x76 or 0x77

### I2C Bus Topology
```
Raspberry Pi 4B (GPIO Pins)
├── SDA (GPIO 2)  ─┬─ ADS1115 (0x48) ─┬─ Moisture Sensor 1
│                  │                   ├─ Moisture Sensor 2
│                  │                   └─ Moisture Sensor 3
│                  └─ BME688 (0x76/0x77)
└── SCL (GPIO 3)  ─┘
```

## Software Components

### 1. Monitoring Script (Python)
- Continuous background service
- Reads sensor data via I2C
- Compares moisture levels to plant profiles
- Sends notifications via ntfy.sh API
- Logs environmental data
- Persists plant profiles and readings

### 2. Web Application
**Option A: Flask (Python - Recommended for cohesion)**
- Lightweight Python web framework
- Matches monitoring script language
- RESTful API for plant profiles
- Template-based UI or JSON API for frontend

**Option B: React (JavaScript)**
- Modern SPA frontend
- Separate from monitoring script
- Requires backend API (Flask/FastAPI)
- Real-time data updates via WebSocket or polling

### 3. Data Storage
- Plant profiles (name, thresholds, last watered)
- Historical moisture readings
- Environmental data logs
- Options: SQLite, JSON files, or PostgreSQL

## Technology Stack

### Hardware
- Raspberry Pi 4B (Raspberry Pi OS)
- ADS1115 16-bit ADC
- 3x Capacitive Soil Moisture Sensors
- BME688 Environmental Sensor

### Software (Core)
- **Language**: Python 3.9+
- **I2C Communication**: `smbus2` or `adafruit-circuitpython-ads1x15`
- **BME688 Driver**: `bme680` or `adafruit-circuitpython-bme680`
- **Notifications**: `requests` library for ntfy.sh HTTP API

### Software (Web - To Be Decided)
- **Option A**: Flask + Jinja2 templates (or Flask + REST API)
- **Option B**: React frontend + Flask/FastAPI backend
- **Database**: SQLite (default), PostgreSQL (if needed)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Raspberry Pi 4B                       │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Monitoring Script (Python)                      │   │
│  │  - Read sensors via I2C                          │   │
│  │  - Check moisture thresholds                     │   │
│  │  - Send notifications (ntfy.sh)                  │   │
│  │  - Log environmental data                        │   │
│  └────────────┬─────────────────────────────────────┘   │
│               │                                          │
│               ▼                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Data Storage (SQLite/JSON)                      │   │
│  │  - Plant profiles                                │   │
│  │  - Moisture readings                             │   │
│  │  - Environmental logs                            │   │
│  └────────────┬─────────────────────────────────────┘   │
│               │                                          │
│               ▼                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │  Web Application (Flask or React)                │   │
│  │  - Live environmental dashboard                  │   │
│  │  - Plant profile management                      │   │
│  │  - Moisture level visualization                  │   │
│  └──────────────────────────────────────────────────┘   │
│               │                                          │
└───────────────┼──────────────────────────────────────────┘
                │
                ▼
         User Browser (HTTP)
```

### External Services
- **ntfy.sh**: Push notification delivery (HTTPS API)

## Constraints & Requirements

### Hardware Constraints
- Single I2C bus shared by all sensors
- Maximum 3 moisture sensors (ADS1115 has 4 channels, 3 used)
- I2C address conflicts must be avoided
- GPIO pin availability on Raspberry Pi

### Software Constraints
- Must run continuously as background service (systemd or supervisor)
- Low resource usage (Raspberry Pi 4B has limited RAM)
- Reliable I2C communication (handle sensor failures gracefully)
- Web app must be accessible on local network

### Performance Goals
- Sensor reading frequency: Every 10-60 seconds (configurable)
- Notification latency: <5 seconds after threshold breach
- Web UI response time: <500ms for page loads
- Data retention: 30+ days of historical readings

### Deployment
- Runs on Raspberry Pi OS (Debian-based)
- Auto-start on boot (systemd service)
- Web app accessible via Pi's IP address on local network
- No cloud dependencies (except ntfy.sh for notifications)

## Project Scope

**Phase 1 (MVP)**: Core monitoring and notifications
- Read 3 moisture sensors via ADS1115
- Read BME688 environmental data
- Send ntfy.sh notifications when moisture low
- Basic plant profile storage (JSON or SQLite)

**Phase 2**: Web interface
- Display live environmental data
- Show current moisture levels
- Basic plant profile viewing

**Phase 3**: Full profile management
- Edit plant profiles via web UI
- Set custom thresholds per plant
- Track watering history

**Phase 4**: Enhanced features (future)
- Historical data visualization (charts/graphs)
- Watering schedule predictions
- Email notifications
- Mobile app or responsive design

## Success Criteria

- System reliably detects low moisture and sends notifications within 5 seconds
- No false positives (incorrect watering alerts) in 7-day test period
- Web interface loads and displays real-time data within 500ms
- System runs continuously for 30+ days without manual intervention
- All 3 plant sensors monitored independently with correct thresholds
- Environmental data updates every 10-60 seconds
