"""Flask web server for plant monitoring dashboard.

Provides REST API for plant management and environmental data,
plus static file serving for frontend dashboard.
"""

import logging
from typing import Optional
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from pathlib import Path

from src.lib.database import (
    load_all_profiles,
    load_profile_by_channel,
    create_plant_profile,
    get_latest_environmental_reading,
    get_environmental_history,
    DEFAULT_DB_PATH
)
import sqlite3

logger = logging.getLogger(__name__)


def create_app(db_path: str = DEFAULT_DB_PATH) -> Flask:
    """Create and configure Flask application.

    Args:
        db_path: Path to SQLite database file

    Returns:
        Configured Flask app instance
    """
    app = Flask(__name__, static_folder=None)  # We'll handle static files manually

    # Enable CORS for local network access from browsers
    CORS(app)

    # Store database path in app config
    app.config['DB_PATH'] = db_path

    # Request logging middleware
    @app.before_request
    def log_request_info():
        """Log incoming requests."""
        logger.debug(f"{request.method} {request.path}")

    @app.after_request
    def log_response_info(response):
        """Log response status."""
        logger.debug(f"{request.method} {request.path} -> {response.status_code}")
        return response

    # ============================================================================
    # Plant API Endpoints
    # ============================================================================

    @app.route('/api/plants', methods=['GET'])
    def get_plants():
        """List all plant profiles.

        Returns:
            200 OK: {plants: [PlantProfile]}

        Contract: GET /api/plants from contracts/api.yaml
        """
        try:
            profiles = load_all_profiles(app.config['DB_PATH'])

            # Convert PlantProfile objects to dicts
            plants = []
            for profile in profiles:
                plant_dict = {
                    'id': profile.plant_name,  # Use plant_name as ID
                    'plant_name': profile.plant_name,
                    'sensor_channel': profile.sensor_channel,
                    'acceptable_moisture_level': profile.acceptable_moisture_level,
                    'current_moisture_level': profile.current_moisture_level,
                    'needs_watering': bool(profile.needs_watering),
                    'last_watered_date': profile.date_last_watered.isoformat() if profile.date_last_watered else None,
                    'image_path': profile.image_path
                }
                plants.append(plant_dict)

            logger.info(f"Retrieved {len(plants)} plant profiles")
            return jsonify({'plants': plants}), 200

        except Exception as e:
            logger.error(f"Failed to retrieve plants: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/plants/<plant_id>', methods=['GET'])
    def get_plant(plant_id: str):
        """Get single plant profile by ID.

        Args:
            plant_id: Plant name

        Returns:
            200 OK: PlantProfile object
            404 Not Found: {error: "Plant not found"}

        Contract: GET /api/plants/{id} from contracts/api.yaml
        """
        try:
            profiles = load_all_profiles(app.config['DB_PATH'])

            # Find plant by name
            for profile in profiles:
                if profile.plant_name == plant_id:
                    plant_dict = {
                        'id': profile.plant_name,
                        'plant_name': profile.plant_name,
                        'sensor_channel': profile.sensor_channel,
                        'acceptable_moisture_level': profile.acceptable_moisture_level,
                        'current_moisture_level': profile.current_moisture_level,
                        'needs_watering': bool(profile.needs_watering),
                        'last_watered_date': profile.date_last_watered.isoformat() if profile.date_last_watered else None,
                        'image_path': profile.image_path
                    }
                    logger.info(f"Retrieved plant: {plant_id}")
                    return jsonify(plant_dict), 200

            # Plant not found
            logger.warning(f"Plant not found: {plant_id}")
            return jsonify({'error': f'Plant with ID {plant_id} not found'}), 404

        except Exception as e:
            logger.error(f"Failed to retrieve plant {plant_id}: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/plants', methods=['POST'])
    def create_plant():
        """Create new plant profile.

        Request Body:
            {
                plant_name: string (required),
                sensor_channel: int 0-3 (required),
                acceptable_moisture_level: int 0-100 (required)
            }

        Returns:
            201 Created: PlantProfile object
            400 Bad Request: Validation error

        Contract: POST /api/plants from contracts/api.yaml
        """
        try:
            data = request.get_json()

            # Validate required fields
            if not data:
                return jsonify({'error': 'Request body is required'}), 400

            plant_name = data.get('plant_name')
            sensor_channel = data.get('sensor_channel')
            acceptable_moisture_level = data.get('acceptable_moisture_level')

            if not plant_name:
                return jsonify({'error': 'plant_name is required'}), 400
            if sensor_channel is None:
                return jsonify({'error': 'sensor_channel is required'}), 400
            if acceptable_moisture_level is None:
                return jsonify({'error': 'acceptable_moisture_level is required'}), 400

            # Validate ranges
            if not isinstance(sensor_channel, int) or sensor_channel < 0 or sensor_channel > 3:
                return jsonify({'error': 'sensor_channel must be between 0 and 3'}), 400

            if not isinstance(acceptable_moisture_level, (int, float)) or \
               acceptable_moisture_level < 0 or acceptable_moisture_level > 100:
                return jsonify({'error': 'acceptable_moisture_level must be between 0 and 100'}), 400

            # Create plant profile
            create_plant_profile(
                plant_name=plant_name,
                sensor_channel=sensor_channel,
                acceptable_moisture_level=float(acceptable_moisture_level),
                db_path=app.config['DB_PATH']
            )

            # Return created plant
            profiles = load_all_profiles(app.config['DB_PATH'])
            for profile in profiles:
                if profile.plant_name == plant_name:
                    plant_dict = {
                        'id': profile.plant_name,
                        'plant_name': profile.plant_name,
                        'sensor_channel': profile.sensor_channel,
                        'acceptable_moisture_level': profile.acceptable_moisture_level,
                        'current_moisture_level': profile.current_moisture_level,
                        'needs_watering': bool(profile.needs_watering),
                        'last_watered_date': profile.date_last_watered.isoformat() if profile.date_last_watered else None,
                        'image_path': profile.image_path
                    }
                    logger.info(f"Created plant: {plant_name}")
                    return jsonify(plant_dict), 201

            return jsonify({'error': 'Failed to retrieve created plant'}), 500

        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'unique' in error_msg and 'sensor_channel' in error_msg:
                return jsonify({'error': f'Sensor channel {sensor_channel} is already assigned to another plant'}), 400
            elif 'unique' in error_msg and 'plant_name' in error_msg:
                return jsonify({'error': f'Plant name \'{plant_name}\' already exists'}), 400
            else:
                logger.error(f"Integrity error creating plant: {e}")
                return jsonify({'error': f'Database constraint violation: {str(e)}'}), 400

        except Exception as e:
            logger.error(f"Failed to create plant: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    @app.route('/api/plants/<plant_id>', methods=['PUT'])
    def update_plant(plant_id: str):
        """Update plant profile.

        Args:
            plant_id: Plant name

        Request Body (all optional):
            {
                plant_name?: string,
                sensor_channel?: int 0-3,
                acceptable_moisture_level?: int 0-100
            }

        Returns:
            200 OK: Updated PlantProfile object
            400 Bad Request: Validation error
            404 Not Found: Plant not found

        Contract: PUT /api/plants/{id} from contracts/api.yaml
        """
        try:
            data = request.get_json()

            if not data:
                return jsonify({'error': 'Request body is required'}), 400

            # Check if plant exists
            profiles = load_all_profiles(app.config['DB_PATH'])
            plant_exists = any(p.plant_name == plant_id for p in profiles)

            if not plant_exists:
                return jsonify({'error': f'Plant with ID {plant_id} not found'}), 404

            # Validate fields if provided
            if 'sensor_channel' in data:
                channel = data['sensor_channel']
                if not isinstance(channel, int) or channel < 0 or channel > 3:
                    return jsonify({'error': 'sensor_channel must be between 0 and 3'}), 400

            if 'acceptable_moisture_level' in data:
                level = data['acceptable_moisture_level']
                if not isinstance(level, (int, float)) or level < 0 or level > 100:
                    return jsonify({'error': 'acceptable_moisture_level must be between 0 and 100'}), 400

            # Build UPDATE query
            update_fields = []
            update_values = []

            if 'plant_name' in data:
                update_fields.append('plant_name = ?')
                update_values.append(data['plant_name'])
            if 'sensor_channel' in data:
                update_fields.append('sensor_channel = ?')
                update_values.append(data['sensor_channel'])
            if 'acceptable_moisture_level' in data:
                update_fields.append('acceptable_moisture_level = ?')
                update_values.append(float(data['acceptable_moisture_level']))

            if not update_fields:
                return jsonify({'error': 'No fields to update'}), 400

            # Execute update
            update_values.append(plant_id)  # For WHERE clause
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE plant_profiles SET {', '.join(update_fields)} WHERE plant_name = ?",
                update_values
            )
            conn.commit()
            conn.close()

            # Return updated plant
            new_name = data.get('plant_name', plant_id)
            profiles = load_all_profiles(app.config['DB_PATH'])
            for profile in profiles:
                if profile.plant_name == new_name:
                    plant_dict = {
                        'id': profile.plant_name,
                        'plant_name': profile.plant_name,
                        'sensor_channel': profile.sensor_channel,
                        'acceptable_moisture_level': profile.acceptable_moisture_level,
                        'current_moisture_level': profile.current_moisture_level,
                        'needs_watering': bool(profile.needs_watering),
                        'last_watered_date': profile.date_last_watered.isoformat() if profile.date_last_watered else None,
                        'image_path': profile.image_path
                    }
                    logger.info(f"Updated plant: {plant_id}")
                    return jsonify(plant_dict), 200

            return jsonify({'error': 'Failed to retrieve updated plant'}), 500

        except sqlite3.IntegrityError as e:
            error_msg = str(e).lower()
            if 'unique' in error_msg and 'sensor_channel' in error_msg:
                return jsonify({'error': f'Sensor channel is already assigned to another plant'}), 400
            elif 'unique' in error_msg and 'plant_name' in error_msg:
                return jsonify({'error': f'Plant name already exists'}), 400
            else:
                return jsonify({'error': f'Database constraint violation: {str(e)}'}), 400

        except Exception as e:
            logger.error(f"Failed to update plant {plant_id}: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    @app.route('/api/plants/<plant_id>', methods=['DELETE'])
    def delete_plant(plant_id: str):
        """Delete plant profile.

        Args:
            plant_id: Plant name

        Returns:
            204 No Content: Plant deleted successfully
            400 Bad Request: Cannot delete last plant
            404 Not Found: Plant not found

        Contract: DELETE /api/plants/{id} from contracts/api.yaml
        """
        try:
            # Check if plant exists
            profiles = load_all_profiles(app.config['DB_PATH'])
            plant_exists = any(p.plant_name == plant_id for p in profiles)

            if not plant_exists:
                return jsonify({'error': f'Plant with ID {plant_id} not found'}), 404

            # Prevent deleting last plant
            if len(profiles) == 1:
                return jsonify({'error': 'Cannot delete the last plant profile. At least one plant is required.'}), 400

            # Delete plant
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            cursor.execute('DELETE FROM plant_profiles WHERE plant_name = ?', (plant_id,))
            conn.commit()
            conn.close()

            # Delete associated image if exists
            from src.lib.image_handler import delete_plant_image
            # Find plant ID by name (use channel as identifier for image deletion)
            for profile in profiles:
                if profile.plant_name == plant_id:
                    # Use plant_name hash or channel as fallback identifier
                    # For now, we'll skip image deletion here since we need proper ID mapping
                    pass

            logger.info(f"Deleted plant: {plant_id}")
            return '', 204

        except Exception as e:
            logger.error(f"Failed to delete plant {plant_id}: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    # ============================================================================
    # Plant Image API Endpoints
    # ============================================================================

    @app.route('/api/plants/<plant_id>/image', methods=['POST'])
    def upload_plant_image(plant_id: str):
        """Upload plant image.

        Args:
            plant_id: Plant name

        Request: multipart/form-data with 'image' file

        Returns:
            200 OK: {image_path, message}
            400 Bad Request: Validation error
            404 Not Found: Plant not found

        Contract: POST /api/plants/{id}/image from contracts/api.yaml
        """
        try:
            from src.lib.image_handler import save_plant_image, ValidationError

            # Check if plant exists
            profiles = load_all_profiles(app.config['DB_PATH'])
            plant = None
            for profile in profiles:
                if profile.plant_name == plant_id:
                    plant = profile
                    break

            if plant is None:
                return jsonify({'error': f'Plant with ID {plant_id} not found'}), 404

            # Check if image file provided
            if 'image' not in request.files:
                return jsonify({'error': 'No image file provided'}), 400

            file = request.files['image']
            if file.filename == '':
                return jsonify({'error': 'No image file selected'}), 400

            # Read image data
            image_data = file.read()

            # Save image (includes validation)
            # Use plant name as identifier for now (we'll need to map to a proper ID later)
            # For simplicity, use hash of plant name as plant_id
            plant_hash_id = abs(hash(plant_id)) % 10000

            image_filename = save_plant_image(
                image_data=image_data,
                plant_id=plant_hash_id,
                filename=file.filename
            )

            # Update database with image path
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE plant_profiles SET image_path = ? WHERE plant_name = ?',
                (image_filename, plant_id)
            )
            conn.commit()
            conn.close()

            logger.info(f"Uploaded image for plant: {plant_id}")
            return jsonify({
                'image_path': image_filename,
                'message': 'Image uploaded successfully'
            }), 200

        except ValidationError as e:
            logger.warning(f"Image validation failed for {plant_id}: {e}")
            return jsonify({'error': str(e)}), 400

        except Exception as e:
            logger.error(f"Failed to upload image for {plant_id}: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    @app.route('/api/plants/<plant_id>/image', methods=['DELETE'])
    def delete_plant_image_endpoint(plant_id: str):
        """Remove plant image.

        Args:
            plant_id: Plant name

        Returns:
            204 No Content: Image removed successfully
            404 Not Found: Plant not found

        Contract: DELETE /api/plants/{id}/image from contracts/api.yaml
        """
        try:
            from src.lib.image_handler import delete_plant_image

            # Check if plant exists
            profiles = load_all_profiles(app.config['DB_PATH'])
            plant_exists = any(p.plant_name == plant_id for p in profiles)

            if not plant_exists:
                return jsonify({'error': f'Plant with ID {plant_id} not found'}), 404

            # Delete image file
            plant_hash_id = abs(hash(plant_id)) % 10000
            delete_plant_image(plant_id=plant_hash_id)

            # Update database (set image_path to NULL)
            conn = sqlite3.connect(app.config['DB_PATH'])
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE plant_profiles SET image_path = NULL WHERE plant_name = ?',
                (plant_id,)
            )
            conn.commit()
            conn.close()

            logger.info(f"Deleted image for plant: {plant_id}")
            return '', 204

        except Exception as e:
            logger.error(f"Failed to delete image for {plant_id}: {e}")
            return jsonify({'error': f'Internal server error: {str(e)}'}), 500

    # ============================================================================
    # Environmental API Endpoints
    # ============================================================================

    @app.route('/api/environmental/latest', methods=['GET'])
    def get_environmental_latest():
        """Get latest environmental reading.

        Returns:
            200 OK: EnvironmentalReading object
            204 No Content: No environmental data available

        Contract: GET /api/environmental/latest from contracts/api.yaml
        """
        try:
            reading = get_latest_environmental_reading(app.config['DB_PATH'])

            if reading is None:
                # No environmental data available (sensor not connected or no readings yet)
                logger.debug("No environmental data available")
                return '', 204

            logger.info(f"Retrieved latest environmental reading: {reading['timestamp']}")
            return jsonify(reading), 200

        except Exception as e:
            logger.error(f"Failed to retrieve latest environmental reading: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    @app.route('/api/environmental/history', methods=['GET'])
    def get_environmental_history_endpoint():
        """Get environmental reading history (last 60 minutes).

        Returns:
            200 OK: {readings: [EnvironmentalReading]}

        Contract: GET /api/environmental/history from contracts/api.yaml
        """
        try:
            readings = get_environmental_history(hours=1, db_path=app.config['DB_PATH'])

            logger.info(f"Retrieved {len(readings)} environmental readings")
            return jsonify({'readings': readings}), 200

        except Exception as e:
            logger.error(f"Failed to retrieve environmental history: {e}")
            return jsonify({'error': 'Internal server error'}), 500

    # ============================================================================
    # Static File Serving
    # ============================================================================

    @app.route('/', methods=['GET'])
    def serve_index():
        """Serve main dashboard page."""
        static_dir = Path(__file__).parent.parent / 'static'
        return send_from_directory(static_dir, 'index.html')

    @app.route('/<path:filename>', methods=['GET'])
    def serve_static(filename: str):
        """Serve static files (CSS, JS, images)."""
        static_dir = Path(__file__).parent.parent / 'static'
        return send_from_directory(static_dir, filename)

    @app.route('/images/<path:filename>', methods=['GET'])
    def serve_image(filename: str):
        """Serve plant images from data/images/ directory."""
        images_dir = Path('data/images')
        return send_from_directory(images_dir, filename)

    logger.info("Flask app created successfully")
    return app


# For running with Gunicorn: gunicorn src.lib.web_server:app
app = create_app()


if __name__ == '__main__':
    # Development server (use Gunicorn for production)
    logging.basicConfig(level=logging.DEBUG)
    app.run(host='0.0.0.0', port=5000, debug=True)
