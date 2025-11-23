import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    
    # Database settings
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300,
    }
    
    # League configuration
    LEAGUE_NAME = os.environ.get('LEAGUE_NAME', 'Gentlemen\'s Club Fantasy Football League')
    SEASON_YEAR = int(os.environ.get('SEASON_YEAR', '2025'))
    
    # Manager configuration (in draft order)
    MANAGERS = [
        {'name': 'Cliff', 'position': 1},
        {'name': 'Petty', 'position': 2},
        {'name': 'Andrew', 'position': 3},  # Commissioner
        {'name': 'Kyle', 'position': 4},
        {'name': 'Chad', 'position': 5},
        {'name': 'Shelby', 'position': 6},
        {'name': 'Levi', 'position': 7},
        {'name': 'TB', 'position': 8},
    ]
    
    # Draft configuration
    TOTAL_ROUNDS = 10
    TEAMS_PER_MANAGER = 10
    COLLEGE_TEAMS_PER_MANAGER = 6
    NFL_TEAMS_PER_MANAGER = 4
    
    # Scoring configuration
    SCORING_RULES = {
        'regular_season_win': 1,
        'conference_championship_win': 1,
        'bowl_game_win': 1,
        'playoff_participation': 1,
        'playoff_win': 1,
        'championship_win': 1,
        'vegas_over_bonus': 1,
    }
    
    # API settings
    ESPN_BASE_URL = 'https://site.api.espn.com/apis/site/v2/sports'
    UPDATE_INTERVAL = int(os.environ.get('UPDATE_INTERVAL', '900'))  # 5 minutes default
    REQUEST_TIMEOUT = 10
    
    # Conference definitions for college teams
    POWER_FOUR_CONFERENCES = [
        'ACC',
        'Big Ten',
        'Big 12', 
        'SEC'
    ]
    
    # Projection configuration
    PROJECTION_CONFIG = {
        'min_games_for_actual': int(os.environ.get('PROJ_MIN_GAMES', '3')),  # Min games before using actual performance
        'max_actual_weight': float(os.environ.get('PROJ_MAX_WEIGHT', '0.7')),  # Max weight for actual vs Vegas (70%)
        'weight_ramp_games': int(os.environ.get('PROJ_RAMP_GAMES', '6')),  # Games to reach max weight
        'update_after_week_complete': os.environ.get('PROJ_WEEK_COMPLETE', 'True').lower() == 'true',
        'use_live_vegas_lines': os.environ.get('PROJ_USE_LIVE_LINES', 'True').lower() == 'true',
        'conservative_postseason': float(os.environ.get('PROJ_CONSERVATIVE', '0.8')),  # Scale postseason bonuses
        'early_season_damping': float(os.environ.get('PROJ_EARLY_DAMPING', '0.5')),  # Reduce volatility early
    }
    
    # Vegas line updater configuration
    VEGAS_CONFIG = {
        'sources': ['espn', 'manual'],  # Available sources
        'update_frequency_hours': int(os.environ.get('VEGAS_UPDATE_FREQ', '24')),
        'request_delay': float(os.environ.get('VEGAS_REQUEST_DELAY', '1.0')),
        'max_retries': int(os.environ.get('VEGAS_MAX_RETRIES', '3')),
        'auto_update_enabled': os.environ.get('VEGAS_AUTO_UPDATE', 'False').lower() == 'true',
    }
    
    # File paths
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'seed_data')
    DRAFT_DATA_FILE = os.path.join(DATA_DIR, 'draft_results.csv')
    TEAMS_DATA_FILE = os.path.join(DATA_DIR, 'teams.json')
    
    # Logging configuration
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'fantasy_tracker.log')
    
    @staticmethod
    def init_app(app):
        """Initialize app with configuration"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(__file__), 'database_dev.db')

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.dirname(__file__), 'database.db')
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get configuration based on environment"""
    env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])