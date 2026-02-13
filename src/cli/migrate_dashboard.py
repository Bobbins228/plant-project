#!/usr/bin/env python3
"""
Database migration for web dashboard feature (004-web-dashboard).

Adds:
- image_path column to plant_profiles table
- environmental_readings table for time-series data
- Index on timestamp for efficient queries
"""

import sqlite3
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


def migrate_database(db_path: str = "data/plants.db") -> None:
    """
    Apply database schema changes for web dashboard.

    Args:
        db_path: Path to SQLite database file
    """
    from src.lib.database import initialize_database

    db_file = project_root / db_path

    # Initialize database if it doesn't exist
    if not db_file.exists():
        print(f"Database not found. Initializing database at {db_file}...")
        initialize_database(str(db_file))
        print("✓ Database initialized")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    try:
        # Check if image_path column already exists
        cursor.execute("PRAGMA table_info(plant_profiles)")
        columns = [row[1] for row in cursor.fetchall()]

        if "image_path" not in columns:
            print("Adding image_path column to plant_profiles...")
            cursor.execute("ALTER TABLE plant_profiles ADD COLUMN image_path TEXT")
            print("✓ Added image_path column")
        else:
            print("✓ image_path column already exists")

        # Create environmental_readings table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS environmental_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL,
                temperature REAL,
                humidity REAL,
                pressure REAL,
                gas_resistance REAL,
                UNIQUE(timestamp)
            )
        """)
        print("✓ Created environmental_readings table (if not exists)")

        # Create index on timestamp for efficient time-range queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON environmental_readings(timestamp)
        """)
        print("✓ Created timestamp index")

        conn.commit()
        print("\n✅ Database migration complete!")
        print(f"✓ Added image_path column to plant_profiles")
        print(f"✓ Created environmental_readings table")

        # Verify images directory exists
        images_dir = project_root / "data" / "images"
        images_dir.mkdir(exist_ok=True)
        print(f"✓ Created images directory: {images_dir}")

    except sqlite3.Error as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    migrate_database()
