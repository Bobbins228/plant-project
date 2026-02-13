#!/usr/bin/env python3
"""Dashboard server CLI entry point.

Starts the Flask development server for the plant monitoring dashboard.
For production deployment, use Gunicorn instead:
    gunicorn -w 2 -b 0.0.0.0:5000 src.lib.web_server:app
"""

import sys
import logging
import argparse
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.lib.web_server import create_app
from src.lib.database import DEFAULT_DB_PATH


def main():
    """Start dashboard development server."""
    parser = argparse.ArgumentParser(
        description='Plant Monitoring Dashboard Server',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Development mode (auto-reload enabled)
  python3 src/cli/dashboard.py

  # Custom port
  python3 src/cli/dashboard.py --port 8080

  # Production deployment with Gunicorn
  gunicorn -w 2 -b 0.0.0.0:5000 src.lib.web_server:app
        """
    )

    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0 for all interfaces)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )

    parser.add_argument(
        '--db-path',
        default=DEFAULT_DB_PATH,
        help=f'Path to SQLite database (default: {DEFAULT_DB_PATH})'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable Flask debug mode (auto-reload, detailed errors)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Verify database exists
    db_file = Path(args.db_path)
    if not db_file.exists():
        logger.error(f"Database not found: {db_file}")
        logger.error("Run the monitoring system first or run the migration script:")
        logger.error("  python3 src/cli/migrate_dashboard.py")
        sys.exit(1)

    # Create Flask app
    logger.info(f"Creating dashboard app with database: {args.db_path}")
    app = create_app(db_path=args.db_path)

    # Start server
    logger.info("=" * 60)
    logger.info("Plant Monitoring Dashboard Server")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Database: {args.db_path}")
    logger.info(f"Debug Mode: {args.debug}")
    logger.info("")
    logger.info(f"Dashboard URL: http://{args.host}:{args.port}")
    if args.host == '0.0.0.0':
        logger.info("Access from other devices: http://<raspberry-pi-ip>:5000")
    logger.info("")
    logger.info("Press CTRL+C to stop the server")
    logger.info("=" * 60)

    try:
        app.run(
            host=args.host,
            port=args.port,
            debug=args.debug
        )
    except KeyboardInterrupt:
        logger.info("\nShutting down dashboard server...")
        sys.exit(0)


if __name__ == '__main__':
    main()
