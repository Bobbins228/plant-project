-- Database Schema for Web Dashboard Feature
-- Feature: 004-web-dashboard
-- Date: 2026-02-13
-- Database: SQLite (data/plants.db)

-- ============================================================================
-- TABLE MODIFICATIONS
-- ============================================================================

-- Add image_path column to existing plant_profiles table
-- This column stores the relative filename of the uploaded plant image
ALTER TABLE plant_profiles ADD COLUMN image_path TEXT;

-- ============================================================================
-- NEW TABLES
-- ============================================================================

-- Environmental readings table for historical time-series data
-- Stores sensor readings collected by monitoring system every 1-2 minutes
-- Automatically cleaned up to retain only last 60 minutes of data
CREATE TABLE IF NOT EXISTS environmental_readings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME NOT NULL,           -- ISO 8601 format: YYYY-MM-DD HH:MM:SS
    temperature REAL,                      -- Temperature in °C (NULL if unavailable)
    humidity REAL,                         -- Relative humidity % (NULL if unavailable)
    pressure REAL,                         -- Atmospheric pressure hPa (NULL if unavailable)
    gas_resistance REAL,                   -- Gas resistance Ω (NULL if unavailable)
    UNIQUE(timestamp)                      -- One reading per timestamp
);

-- Index for efficient time-range queries (e.g., last 60 minutes)
CREATE INDEX IF NOT EXISTS idx_timestamp ON environmental_readings(timestamp);

-- ============================================================================
-- REFERENCE: EXISTING SCHEMA (from feature 002-plant-profile-database)
-- ============================================================================

-- plant_profiles table (already exists - shown for reference)
-- CREATE TABLE IF NOT EXISTS plant_profiles (
--     id INTEGER PRIMARY KEY AUTOINCREMENT,
--     plant_name TEXT NOT NULL UNIQUE,
--     sensor_channel INTEGER NOT NULL UNIQUE CHECK(sensor_channel >= 0 AND sensor_channel <= 3),
--     acceptable_moisture_level INTEGER NOT NULL CHECK(acceptable_moisture_level >= 0 AND acceptable_moisture_level <= 100),
--     current_moisture_level REAL,
--     needs_watering INTEGER DEFAULT 0,
--     last_watered_date DATE,
--     image_path TEXT                    -- NEW COLUMN (added by this feature)
-- );

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Example environmental reading
-- INSERT INTO environmental_readings (timestamp, temperature, humidity, pressure, gas_resistance)
-- VALUES ('2026-02-13 15:30:00', 22.45, 55.67, 1013.25, 12345.67);

-- Example plant profile with image
-- UPDATE plant_profiles SET image_path = 'plant_1.jpg' WHERE id = 1;

-- ============================================================================
-- QUERIES (common operations)
-- ============================================================================

-- Get latest environmental reading
-- SELECT * FROM environmental_readings ORDER BY timestamp DESC LIMIT 1;

-- Get last 60 minutes of environmental readings
-- SELECT * FROM environmental_readings
-- WHERE timestamp > datetime('now', '-1 hour')
-- ORDER BY timestamp ASC;

-- Cleanup old environmental readings (run after each insert)
-- DELETE FROM environmental_readings WHERE timestamp < datetime('now', '-1 hour');

-- Get all plant profiles with images
-- SELECT id, plant_name, sensor_channel, acceptable_moisture_level,
--        current_moisture_level, needs_watering, last_watered_date, image_path
-- FROM plant_profiles
-- ORDER BY plant_name;

-- Get plant profile by ID
-- SELECT * FROM plant_profiles WHERE id = ?;

-- Create new plant profile
-- INSERT INTO plant_profiles (plant_name, sensor_channel, acceptable_moisture_level)
-- VALUES (?, ?, ?);

-- Update plant profile
-- UPDATE plant_profiles
-- SET plant_name = ?,
--     sensor_channel = ?,
--     acceptable_moisture_level = ?
-- WHERE id = ?;

-- Delete plant profile (with safeguard to prevent deleting last plant)
-- DELETE FROM plant_profiles WHERE id = ? AND (SELECT COUNT(*) FROM plant_profiles) > 1;

-- ============================================================================
-- VALIDATION CONSTRAINTS
-- ============================================================================

-- Enforced by SQLite:
-- - plant_name: UNIQUE constraint prevents duplicate names
-- - sensor_channel: UNIQUE constraint prevents duplicate channels, CHECK ensures 0-3
-- - acceptable_moisture_level: CHECK ensures 0-100
-- - timestamp: UNIQUE constraint prevents duplicate timestamps

-- Enforced by application code:
-- - image_path: Must reference existing file in data/images/ directory
-- - Image file size: Must be <= 10 MB (checked before insert)
-- - Image file format: Must be JPEG/PNG/GIF/WebP (checked before insert)
-- - At least one plant: Prevent DELETE if COUNT(*) = 1
-- - Environmental data retention: Delete rows older than 1 hour after INSERT

-- ============================================================================
-- DATA TYPES
-- ============================================================================

-- INTEGER: id fields, sensor_channel, acceptable_moisture_level, needs_watering
-- TEXT: plant_name, image_path
-- REAL: temperature, humidity, pressure, gas_resistance, current_moisture_level
-- DATE: last_watered_date (stored as TEXT in ISO 8601 format)
-- DATETIME: timestamp (stored as TEXT in ISO 8601 format)

-- ============================================================================
-- MIGRATION STRATEGY
-- ============================================================================

-- This schema modification can be applied incrementally:
-- 1. Check if image_path column exists (query pragma_table_info)
-- 2. If not exists, run ALTER TABLE to add image_path
-- 3. Check if environmental_readings table exists
-- 4. If not exists, run CREATE TABLE and CREATE INDEX
-- 5. Existing plant_profiles data is unaffected
-- 6. Old monitoring system continues working
-- 7. New dashboard features gracefully degrade if schema not yet migrated
