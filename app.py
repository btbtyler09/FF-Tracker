from flask import Flask, render_template, jsonify, request
from datetime import datetime
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:////app/data/database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
from database import db, init_db
init_db(app)

# Import models after db initialization
from models import Manager, Team, DraftPick, Game
from scoring import calculate_scores
from projections import calculate_projections
from data_updater import update_game_results
from config import get_config

# Scheduler imports
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, time as time_obj
import atexit

@app.route('/')
def index():
    """Home page showing current standings"""
    try:
        standings = calculate_scores()
        
        # Get projections using new system
        config_obj = get_config()
        projections = calculate_projections(config=config_obj.PROJECTION_CONFIG)
        
        # Merge projections into standings
        projection_map = {p['manager_id']: p for p in projections}  # Store full projection data
        for standing in standings:
            projection_data = projection_map.get(standing['manager_id'])
            if projection_data:
                standing['projected_total'] = projection_data['projected_total']
                
                # Merge projection team data with standing team data
                projection_teams = {t['team_name']: t for t in projection_data.get('teams', [])}
                for team in standing['teams']:
                    proj_team = projection_teams.get(team['team_name'])
                    if proj_team:
                        # Add projection-specific data to team
                        team['vegas_line_used'] = proj_team.get('vegas_line_used')
                        team['original_vegas_line'] = proj_team.get('original_vegas_line', team.get('vegas_total'))
                        team['projected_wins'] = proj_team.get('projected_wins')
                        team['confidence'] = proj_team.get('confidence', 0)
            else:
                standing['projected_total'] = 0.0
        
        return render_template('index.html', standings=standings)
    except Exception as e:
        app.logger.error(f"Error calculating scores: {e}")
        return render_template('index.html', standings=[], error="Unable to load standings")

# Manager detail page removed - functionality moved to clickable expand in standings table
# @app.route('/manager/<int:manager_id>')
# def manager_detail(manager_id):
#     """Individual manager details page - DEPRECATED: Use clickable manager names in standings"""
#     return redirect('/')

@app.route('/rules')
def rules():
    """Scoring rules page"""
    return render_template('rules.html')

@app.route('/api/update')
def update_data():
    """Manually trigger data update"""
    try:
        update_game_results()
        return jsonify({'status': 'success', 'message': 'Data updated successfully'})
    except Exception as e:
        app.logger.error(f"Error updating data: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vegas-lines/update')
def update_vegas_lines_api():
    """Manually trigger Vegas line updates"""
    try:
        from vegas_updater import update_vegas_lines
        result = update_vegas_lines(force=True)
        return jsonify({
            'status': 'success', 
            'message': f"Vegas lines updated: {result['updated']} teams updated, {result['errors']} errors",
            'details': result
        })
    except Exception as e:
        app.logger.error(f"Error updating Vegas lines: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/standings')
def api_standings():
    """API endpoint for standings data"""
    try:
        standings = calculate_scores()
        
        # Get projections using new system
        config_obj = get_config()
        projections = calculate_projections(config=config_obj.PROJECTION_CONFIG)
        
        # Merge projections into standings
        projection_map = {p['manager_id']: p for p in projections}  # Store full projection data
        for standing in standings:
            projection_data = projection_map.get(standing['manager_id'])
            if projection_data:
                standing['projected_total'] = projection_data['projected_total']
                
                # Merge projection team data with standing team data
                projection_teams = {t['team_name']: t for t in projection_data.get('teams', [])}
                for team in standing['teams']:
                    proj_team = projection_teams.get(team['team_name'])
                    if proj_team:
                        # Add projection-specific data to team
                        team['vegas_line_used'] = proj_team.get('vegas_line_used')
                        team['original_vegas_line'] = proj_team.get('original_vegas_line', team.get('vegas_total'))
                        team['projected_wins'] = proj_team.get('projected_wins')
                        team['confidence'] = proj_team.get('confidence', 0)
            else:
                standing['projected_total'] = 0.0
            
        return jsonify({'status': 'success', 'data': standings, 'projections': projections})
    except Exception as e:
        app.logger.error(f"Error getting standings: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vegas-lines/update')
def update_vegas_lines():
    """Manually trigger Vegas line updates"""
    try:
        from vegas_updater import update_vegas_lines
        config_obj = get_config()
        
        # Force update if requested
        force = request.args.get('force', 'false').lower() == 'true'
        week = request.args.get('week', type=int)
        
        summary = update_vegas_lines(week=week, force=force)
        return jsonify({'status': 'success', 'summary': summary})
    except Exception as e:
        app.logger.error(f"Error updating Vegas lines: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vegas-lines/manual', methods=['POST'])
def manual_vegas_line_update():
    """Manually update a specific team's Vegas line"""
    try:
        from vegas_updater import manual_line_update
        
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data provided'}), 400
        
        team_id = data.get('team_id')
        week = data.get('week')
        new_line = data.get('new_line')
        notes = data.get('notes')
        
        if not all([team_id, week, new_line is not None]):
            return jsonify({'status': 'error', 'message': 'Missing required fields'}), 400
        
        success = manual_line_update(team_id, week, new_line, notes)
        if success:
            return jsonify({'status': 'success', 'message': 'Line updated successfully'})
        else:
            return jsonify({'status': 'error', 'message': 'Failed to update line'}), 500
            
    except Exception as e:
        app.logger.error(f"Error manually updating Vegas line: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/vegas-lines/history/<int:team_id>')
def get_vegas_line_history(team_id):
    """Get Vegas line history for a team"""
    try:
        from vegas_updater import get_team_line_history
        
        weeks = request.args.get('weeks', 5, type=int)
        history = get_team_line_history(team_id, weeks)
        
        if history:
            return jsonify({'status': 'success', 'data': history})
        else:
            return jsonify({'status': 'error', 'message': 'Team not found or no history'}), 404
            
    except Exception as e:
        app.logger.error(f"Error getting Vegas line history: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint for Docker"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

@app.route('/api/scheduler/status')
def scheduler_status():
    """Get background scheduler status for debugging"""
    global scheduler
    
    try:
        auto_update_enabled = os.environ.get('ENABLE_AUTO_UPDATE', 'true').lower() == 'true'
        debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
        
        status = {
            'auto_update_enabled': auto_update_enabled,
            'debug_mode': debug_mode,
            'scheduler_running': scheduler is not None and scheduler.running,
            'is_game_day': is_game_day(),
            'update_interval_minutes': get_update_interval(),
            'timestamp': datetime.now().isoformat()
        }
        
        if scheduler and scheduler.running:
            # Get job info
            jobs = []
            for job in scheduler.get_jobs():
                jobs.append({
                    'id': job.id,
                    'name': job.name,
                    'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                    'trigger': str(job.trigger)
                })
            status['jobs'] = jobs
        else:
            status['jobs'] = []
        
        return jsonify({'status': 'success', 'data': status})
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Global scheduler variable
scheduler = None

def scheduled_update():
    """
    Background task to update game scores
    Runs within Flask app context for database access
    """
    with app.app_context():
        try:
            app.logger.info("Starting scheduled game data update...")
            start_time = datetime.now()
            
            # Update game results first
            update_game_results()
            
            # Vegas line updates disabled - using projections directly
            # try:
            #     from vegas_updater import update_vegas_lines
            #     app.logger.info("Starting Vegas line updates...")
            #     line_update_result = update_vegas_lines()
            #     app.logger.info(f"Vegas line update: {line_update_result['updated']} teams updated, "
            #                   f"{line_update_result['errors']} errors")
            # except Exception as e:
            #     app.logger.error(f"Vegas line update failed: {e}")
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            app.logger.info(f"Scheduled update completed successfully in {duration:.2f} seconds")
            
        except Exception as e:
            app.logger.error(f"Scheduled update failed: {e}")

def is_game_day():
    """
    Determine if today is likely a game day
    Returns True for Saturday (college), Sunday (NFL), Monday (MNF)
    """
    today = datetime.now().weekday()  # 0=Monday, 6=Sunday
    return today in [5, 6, 0]  # Saturday, Sunday, Monday

def get_update_interval():
    """
    Get update interval based on configuration and current day
    More frequent updates on game days
    """
    # Check environment variable first
    env_interval = os.environ.get('UPDATE_INTERVAL_MINUTES')
    if env_interval:
        try:
            return int(env_interval)
        except ValueError:
            app.logger.warning(f"Invalid UPDATE_INTERVAL_MINUTES: {env_interval}, using defaults")
    
    # Use smart defaults based on day
    if is_game_day():
        return 30  # Every 30 minutes on game days
    else:
        return 120  # Every 2 hours on non-game days

def initialize_scheduler():
    """Initialize and start the background scheduler for automatic updates"""
    global scheduler
    
    # Check if auto updates are enabled
    auto_update_enabled = os.environ.get('ENABLE_AUTO_UPDATE', 'true').lower() == 'true'
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    if not auto_update_enabled:
        app.logger.info("Automatic updates disabled via ENABLE_AUTO_UPDATE=false")
        return
        
    if debug_mode:
        app.logger.info("Skipping scheduler initialization in debug mode")
        return
    
    try:
        scheduler = BackgroundScheduler()
        
        # Calculate update interval
        update_interval = get_update_interval()
        
        # Add the scheduled job
        scheduler.add_job(
            func=scheduled_update,
            trigger="interval",
            minutes=update_interval,
            id='game_data_update',
            name='Automatic Game Data Update',
            max_instances=1,  # Prevent overlapping updates
            misfire_grace_time=300,  # Allow 5 minutes grace for missed updates
            replace_existing=True
        )
        
        # Start the scheduler
        scheduler.start()
        
        app.logger.info(f"Background scheduler started - updating every {update_interval} minutes")
        app.logger.info(f"Game day mode: {'ON' if is_game_day() else 'OFF'}")
        
        # Register shutdown handler
        atexit.register(lambda: scheduler.shutdown() if scheduler else None)
        
    except Exception as e:
        app.logger.error(f"Failed to initialize scheduler: {e}")
        # Don't crash the app if scheduler fails

def initialize_app():
    """Initialize the application with database setup and startup updates"""
    import fcntl
    import time
    
    print("")
    print("=" * 60)
    print("FANTASY FOOTBALL TRACKER - DATABASE INITIALIZATION")
    print("=" * 60)
    
    # Debug information
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print(f"Database URL: {app.config['SQLALCHEMY_DATABASE_URI']}")
    
    # Check directory permissions
    data_dir = '/app/data'
    print(f"Data directory exists: {os.path.exists(data_dir)}")
    if os.path.exists(data_dir):
        print(f"Data directory writable: {os.access(data_dir, os.W_OK)}")
        try:
            print(f"Data directory permissions: {oct(os.stat(data_dir).st_mode)[-3:]}")
            print(f"Data directory owner: {os.stat(data_dir).st_uid}:{os.stat(data_dir).st_gid}")
        except Exception as e:
            print(f"Could not check data directory stats: {e}")
    
    # Check seed data
    seed_dir = '/app/seed_data'
    print(f"Seed data directory exists: {os.path.exists(seed_dir)}")
    if os.path.exists(seed_dir):
        try:
            files = os.listdir(seed_dir)
            print(f"Seed data files: {files}")
        except Exception as e:
            print(f"Could not list seed data files: {e}")
    
    print("-" * 60)
    
    # Use file locking to prevent race conditions with multiple workers
    # Try /app/data first, fall back to /tmp if permission issues
    lock_file_path = '/app/data/init.lock'
    lock_file = None
    
    try:
        # Try to ensure data directory exists for lock file (may fail on local dev)
        try:
            os.makedirs('/app/data', exist_ok=True)
        except (PermissionError, OSError):
            pass  # Directory creation failed, will use fallback
        
        # Try to open lock file in /app/data
        try:
            lock_file = open(lock_file_path, 'w')
        except PermissionError:
            # Fall back to /tmp which is always writable
            print(f"Permission denied for {lock_file_path}, using /tmp/init.lock instead")
            lock_file_path = '/tmp/init.lock'
            lock_file = open(lock_file_path, 'w')
        
        # Try to acquire exclusive lock (will block if another process has it)
        print("Acquiring initialization lock...")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        print("Lock acquired, proceeding with initialization")
        
        # Small delay to ensure any other process commits
        time.sleep(0.1)
        
        with app.app_context():
            try:
                # Create tables
                print("Step 1: Creating database tables...")
                db.create_all()
                print("✅ Database tables created successfully")
                
                # Check if database needs initialization  
                # Re-check after acquiring lock in case another worker already initialized
                from models import Manager, Team, seed_database
                manager_count = Manager.query.count()
                print(f"Found {manager_count} existing managers in database")
                
                if manager_count == 0:
                    print("")
                    print("🔄 Empty database detected - initializing with data...")
                    
                    # Import managers
                    print("  → Creating managers...")
                    seed_database()
                    print("  ✅ Managers created successfully")
                    
                    # Import teams and draft data
                    try:
                        from import_data import import_teams_data, import_draft_data
                        
                        print("  → Importing teams data...")
                        if import_teams_data():
                            print("  ✅ Teams data imported successfully")
                        else:
                            print("  ❌ Warning: Teams data import failed")
                        
                        print("  → Importing draft data...")
                        if import_draft_data():
                            print("  ✅ Draft data imported successfully") 
                        else:
                            print("  ❌ Warning: Draft data import failed")
                            
                    except Exception as e:
                        print(f"  ❌ Warning: Data import failed: {e}")
                else:
                    print("✅ Database already initialized with data")
                
                # Show final database status
                manager_count = Manager.query.count()
                team_count = Team.query.count()
                print(f"Database status: {manager_count} managers, {team_count} teams")
                
                print("-" * 60)
                
                # Perform automatic update on startup (skip in debug mode)
                debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
                if not debug_mode:
                    print("🔄 Running startup game data update...")
                    try:
                        update_game_results()
                        print("✅ Game data update completed")
                        
                        # Vegas line updates disabled - using projections directly
                        # print("🎲 Running Vegas line updates...")
                        # from vegas_updater import update_vegas_lines
                        # vegas_result = update_vegas_lines()
                        # print(f"✅ Vegas lines updated: {vegas_result['updated']} teams")
                        
                        print("✅ Startup data update completed successfully")
                    except Exception as e:
                        print(f"❌ Warning: Startup data update failed: {e}")
                        # Don't crash the app if update fails
                else:
                    print("⏭️  Skipping startup update (debug mode)")
                
                # Initialize background scheduler for automatic updates
                print("🔄 Initializing background scheduler...")
                try:
                    initialize_scheduler()
                    print("✅ Background scheduler initialized successfully")
                except Exception as e:
                    print(f"⚠️  Warning: Scheduler initialization failed: {e}")
                    # Don't crash the app if scheduler fails
                
                print("=" * 60)
                print("🚀 APPLICATION READY - Database initialization complete!")
                print("=" * 60)
                print("")
                    
            except Exception as e:
                print("=" * 60)
                print(f"💥 CRITICAL ERROR during app initialization: {e}")
                print("=" * 60)
                import traceback
                traceback.print_exc()
                
    finally:
        # Always release the lock
        if lock_file:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()
            print("Initialization lock released")

# Initialize the application when module is imported (works with both direct run and gunicorn)
initialize_app()

if __name__ == '__main__':
    # Run the application directly (development mode)
    debug_mode = os.environ.get('DEBUG', 'False').lower() == 'true'
    app.run(host='0.0.0.0', port=8742, debug=debug_mode)