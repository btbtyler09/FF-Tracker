#!/usr/bin/env python3
"""
Standalone script for updating game scores via cron jobs

This script can be run independently of the Flask app to update game scores
from ESPN API. It's designed to be scheduled via cron for automatic updates.

Usage:
    python update_scores.py [--verbose] [--force] [--week WEEK]

Cron Examples:
    # Update Sunday nights after NFL games (11 PM EST)
    0 23 * * 0 cd /path/to/FF-Tracker && python update_scores.py >> logs/cron_updates.log 2>&1
    
    # Update Saturday nights after college games (11 PM EST)  
    0 23 * * 6 cd /path/to/FF-Tracker && python update_scores.py >> logs/cron_updates.log 2>&1
    
    # Update Tuesday mornings after Monday Night Football (2 AM EST)
    0 2 * * 2 cd /path/to/FF-Tracker && python update_scores.py >> logs/cron_updates.log 2>&1
    
    # Weekly catch-all update Wednesday mornings (8 AM EST)
    0 8 * * 3 cd /path/to/FF-Tracker && python update_scores.py --verbose >> logs/cron_updates.log 2>&1
"""

import sys
import os
import argparse
import logging
from datetime import datetime
from dotenv import load_dotenv

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables
load_dotenv()

# Flask app setup for database access
from flask import Flask
from database import db, init_db
from data_updater import update_game_results
from config import get_config

def setup_logging(verbose=False):
    """Set up logging for the update script"""
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir, 'update_scores.log'))
        ]
    )
    
    return logging.getLogger(__name__)

def create_app():
    """Create and configure the Flask app for database access"""
    app = Flask(__name__)
    
    # Use same configuration as main app
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize database
    init_db(app)
    
    return app

def update_scores(app, logger, verbose=False, force=False, week=None):
    """
    Update game scores using the existing data_updater module
    
    Args:
        app: Flask application instance
        logger: Logger instance
        verbose: Enable verbose logging
        force: Force update even if recent update exists
        week: Specific week to update (optional)
    
    Returns:
        bool: True if update successful, False otherwise
    """
    try:
        with app.app_context():
            logger.info("Starting game scores update...")
            
            if week:
                logger.info(f"Updating specific week: {week}")
                # Note: Current update_game_results doesn't support specific week
                # This could be enhanced in the future
            
            # Perform the update
            start_time = datetime.now()
            update_game_results()
            end_time = datetime.now()
            
            duration = (end_time - start_time).total_seconds()
            logger.info(f"Game scores update completed successfully in {duration:.2f} seconds")
            
            return True
            
    except Exception as e:
        logger.error(f"Error updating game scores: {e}")
        if verbose:
            logger.exception("Full error details:")
        return False

def main():
    """Main function for the update script"""
    parser = argparse.ArgumentParser(
        description='Update fantasy football game scores from ESPN API',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__.split('Usage:')[1].split('"""')[0]
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging output'
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force update even if recent update exists (currently not implemented)'
    )
    
    parser.add_argument(
        '--week', '-w',
        type=int,
        help='Update specific week only (currently not implemented)'
    )
    
    parser.add_argument(
        '--dry-run', '-d',
        action='store_true',
        help='Show what would be updated without making changes'
    )
    
    args = parser.parse_args()
    
    # Set up logging
    logger = setup_logging(args.verbose)
    
    try:
        # Create Flask app for database access
        app = create_app()
        
        logger.info("=" * 60)
        logger.info("Fantasy Football Score Update - Starting")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")
        logger.info(f"Verbose mode: {args.verbose}")
        logger.info(f"Force mode: {args.force}")
        if args.week:
            logger.info(f"Target week: {args.week}")
        logger.info("=" * 60)
        
        if args.dry_run:
            logger.info("DRY RUN MODE - No changes will be made")
            logger.info("Would update game scores from ESPN API")
            logger.info("Dry run completed successfully")
            return 0
        
        # Perform the update
        success = update_scores(
            app=app,
            logger=logger,
            verbose=args.verbose,
            force=args.force,
            week=args.week
        )
        
        if success:
            logger.info("Update completed successfully")
            return 0
        else:
            logger.error("Update failed")
            return 1
            
    except KeyboardInterrupt:
        logger.info("Update interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if args.verbose:
            logger.exception("Full error details:")
        return 1
    finally:
        logger.info("=" * 60)

if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)