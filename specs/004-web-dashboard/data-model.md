# Data Model: Local Web Dashboard for Plant Monitoring

**Feature**: 004-web-dashboard
**Date**: 2026-02-13
**Database**: SQLite (`data/plants.db`)

## Entity Relationship Overview

```
plant_profiles (existing)
    |
    | 1:0..1
    |
    v
plant_images (filepath reference via image_path column)

environmental_readings (new table, independent)
```

## Entities

### 1. PlantProfile (Existing - Extended)

**Purpose**: Represents a single plant being monitored with its configuration and current state.

**Table**: `plant_profiles` (already exists from feature 002-plant-profile-database)

**New Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `image_path` | TEXT | NULL | Relative path to plant image in data/images/ (e.g., "plant_1.jpg") |

**Existing Fields** (for reference):
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-incrementing plant ID |
| `plant_name` | TEXT | NOT NULL, UNIQUE | User-assigned plant name |
| `sensor_channel` | INTEGER | NOT NULL, UNIQUE, CHECK(0-3) | ADC channel (0-3) |
| `acceptable_moisture_level` | INTEGER | NOT NULL, CHECK(0-100) | Moisture threshold percentage |
| `current_moisture_level` | REAL | NULL | Last measured moisture percentage |
| `needs_watering` | INTEGER | DEFAULT 0 | Boolean flag (0/1) |
| `last_watered_date` | DATE | NULL | Date of last detected watering |

**Validation Rules**:
- **plant_name**: 1-100 characters, unique across all plants
- **sensor_channel**: Must be 0-3, unique (one plant per ADC channel)
- **acceptable_moisture_level**: Must be 0-100 (percentage)
- **image_path**: If present, must reference existing file in data/images/, max 10 MB file size
- **current_moisture_level**: 0-100 or NULL if no readings yet

**Business Rules**:
- Deleting a plant deletes its associated image file (cascade)
- Changing sensor_channel validates no other plant uses that channel
- At least one plant profile must exist (prevent deletion of last plant)

**State Transitions**:
- `needs_watering`: 0 → 1 when current_moisture < threshold
- `needs_watering`: 1 → 0 when current_moisture > threshold + 5% (hysteresis)
- `last_watered_date`: Updated when needs_watering transitions from 1 → 0

---

### 2. EnvironmentalReading (New)

**Purpose**: Stores time-series environmental sensor readings for historical graphing.

**Table**: `environmental_readings` (new table created by this feature)

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

**Fields**:
| Field | Type | Constraints | Description |
|-------|------|-------------|-------------|
| `id` | INTEGER | PRIMARY KEY | Auto-incrementing reading ID |
| `timestamp` | DATETIME | NOT NULL, UNIQUE | ISO 8601 format (YYYY-MM-DD HH:MM:SS) |
| `temperature` | REAL | NULL | Temperature in °C (NULL if sensor unavailable) |
| `humidity` | REAL | NULL | Relative humidity % (NULL if sensor unavailable) |
| `pressure` | REAL | NULL | Atmospheric pressure in hPa (NULL if sensor unavailable) |
| `gas_resistance` | REAL | NULL | Gas resistance in Ω (NULL if sensor unavailable) |

**Validation Rules**:
- **timestamp**: Must be unique (one reading per timestamp)
- **temperature**: -50 to 100 °C if not NULL (sensor range)
- **humidity**: 0 to 100% if not NULL
- **pressure**: 300 to 1100 hPa if not NULL (sensor range)
- **gas_resistance**: 0 to 1,000,000 Ω if not NULL

**Business Rules**:
- Automatically delete readings older than 1 hour after each insert
- All metric fields can be NULL if sensor read fails
- Readings inserted by monitoring system, not dashboard
- Timestamp uses UTC timezone for consistency

**Data Retention**:
- **Retention period**: 60 minutes (1 hour)
- **Cleanup**: After each insert, delete rows where `timestamp < datetime('now', '-1 hour')`
- **Steady-state size**: ~60-120 rows (monitoring cycle runs every 1-2 minutes)

**Query Patterns**:
- **Latest reading**: `SELECT * FROM environmental_readings ORDER BY timestamp DESC LIMIT 1`
- **Last hour**: `SELECT * FROM environmental_readings WHERE timestamp > datetime('now', '-1 hour') ORDER BY timestamp ASC`
- **Cleanup**: `DELETE FROM environmental_readings WHERE timestamp < datetime('now', '-1 hour')`

---

### 3. PlantImage (File-based, not a database table)

**Purpose**: Association between plant profiles and uploaded image files.

**Storage**: `data/images/` directory (file system)

**Naming Convention**: `plant_{id}.{ext}` where:
- `{id}` = plant_profiles.id
- `{ext}` = original file extension (jpg, jpeg, png, gif, webp)

**Examples**:
- `plant_1.jpg`
- `plant_2.png`
- `plant_15.webp`

**Database Link**: `plant_profiles.image_path` stores the filename (e.g., "plant_1.jpg")

**Validation Rules**:
- **File formats**: JPEG (.jpg, .jpeg), PNG (.png), GIF (.gif), WebP (.webp) only
- **File size**: Maximum 10 MB (FR-026)
- **File dimensions**: No minimum/maximum (client display will resize)
- **Filename sanitization**: Use plant ID, not user-provided filename

**Business Rules**:
- One image per plant (uploading new image replaces old one)
- Deleting plant deletes associated image file
- Removing image sets `image_path` to NULL but keeps plant profile
- Images served via Flask static file route `/images/{filename}`

**File Operations**:
- **Upload**: Save to temp, validate, move to `data/images/plant_{id}.{ext}`, update DB
- **Replace**: Delete old file, save new file with same ID
- **Delete**: Delete file, set `image_path = NULL` in database
- **Serve**: Flask route returns file from `data/images/` directory

---

## Database Migration

### Schema Changes Required

**Existing table modification**:
```sql
-- Add image_path column to plant_profiles
ALTER TABLE plant_profiles ADD COLUMN image_path TEXT;
```

**New table creation**:
```sql
-- Create environmental_readings table
CREATE TABLE IF NOT EXISTS environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    gas_resistance REAL,
    UNIQUE(timestamp)
);

-- Create index for efficient time-based queries
CREATE INDEX idx_timestamp ON environmental_readings(timestamp);
```

**Directory creation**:
```bash
mkdir -p data/images
```

### Migration Strategy

1. **Check if migration needed**: Query for `image_path` column existence
2. **Apply schema changes**: Add column to existing table, create new table
3. **Create image directory**: Ensure `data/images/` exists with correct permissions
4. **No data migration needed**: Existing plant_profiles data unaffected
5. **Backward compatible**: Old monitoring system continues working, new features gracefully degrade if accessed before migration

---

## Sample Data

### PlantProfile with Image

```sql
INSERT INTO plant_profiles (
    plant_name,
    sensor_channel,
    acceptable_moisture_level,
    current_moisture_level,
    needs_watering,
    image_path
) VALUES (
    'Snake Plant',
    0,
    40,
    42.5,
    0,
    'plant_1.jpg'
);
```

### EnvironmentalReading

```sql
INSERT INTO environmental_readings (
    timestamp,
    temperature,
    humidity,
    pressure,
    gas_resistance
) VALUES (
    '2026-02-13 15:30:00',
    22.45,
    55.67,
    1013.25,
    12345.67
);
```

---

## Relationships

**PlantProfile → PlantImage**: 1:0..1 (one plant has zero or one image)
- Linked via `image_path` column
- Cascade delete: Deleting plant deletes image file

**EnvironmentalReading**: Independent (no foreign keys)
- Time-series data not linked to specific plants
- Shared environmental context for all plants

---

## Constraints Summary

| Constraint | Type | Enforcement |
|------------|------|-------------|
| Unique plant names | Database | UNIQUE constraint on plant_profiles.plant_name |
| Unique sensor channels | Database | UNIQUE constraint on plant_profiles.sensor_channel |
| Channel range 0-3 | Database | CHECK constraint on sensor_channel |
| Moisture 0-100% | Application | Validation before INSERT/UPDATE |
| Unique timestamps | Database | UNIQUE constraint on environmental_readings.timestamp |
| Image file size <10 MB | Application | Validation before file save |
| Image file types | Application | Extension check before file save |
| At least one plant | Application | Prevent DELETE if COUNT(*) = 1 |
| 1-hour data retention | Application | DELETE old rows after INSERT |
