from datetime import datetime
from database import db

class Manager(db.Model):
    """Fantasy football managers/users"""
    __tablename__ = 'managers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    draft_position = db.Column(db.Integer, nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    picks = db.relationship('DraftPick', backref='manager', lazy=True)
    
    def __repr__(self):
        return f'<Manager {self.name}>'

class Team(db.Model):
    """College and NFL teams"""
    __tablename__ = 'teams'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    league = db.Column(db.String(10), nullable=False)  # 'NFL' or 'COLLEGE'
    conference = db.Column(db.String(50))  # ACC, Big Ten, etc.
    division = db.Column(db.String(50))  # For NFL divisions
    vegas_total = db.Column(db.Float)  # Preseason over/under win total
    espn_id = db.Column(db.String(20))  # ESPN team ID for API calls
    abbreviation = db.Column(db.String(10))  # Team abbreviation (e.g., 'UGA', 'KC')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    picks = db.relationship('DraftPick', backref='team', lazy=True)
    games = db.relationship('Game', backref='team', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Team {self.name} ({self.league})>'
    
    @property
    def regular_season_wins(self):
        """Count regular season wins"""
        return Game.query.filter_by(
            team_id=self.id,
            game_type='regular',
            won=True
        ).count()
    
    @property
    def total_wins(self):
        """Count all wins"""
        return Game.query.filter_by(team_id=self.id, won=True).count()

class DraftPick(db.Model):
    """Draft picks linking managers to teams"""
    __tablename__ = 'draft_picks'
    
    id = db.Column(db.Integer, primary_key=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('managers.id'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    round = db.Column(db.Integer, nullable=False)
    pick = db.Column(db.Integer, nullable=False)  # Overall pick number
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ensure each pick is unique
    __table_args__ = (
        db.UniqueConstraint('pick', name='unique_pick_number'),
        db.UniqueConstraint('team_id', name='unique_team_drafted'),
    )
    
    def __repr__(self):
        return f'<DraftPick Round {self.round}, Pick {self.pick}>'

class Game(db.Model):
    """Individual game results"""
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    week = db.Column(db.Integer)  # Week number (nullable for playoffs)
    opponent = db.Column(db.String(100), nullable=False)
    won = db.Column(db.Boolean, nullable=False, default=False)
    game_type = db.Column(db.String(50), nullable=False, default='regular')
    # Game types: 'regular', 'conference_championship', 'bowl', 'playoff', 'championship'
    game_date = db.Column(db.DateTime)
    score_us = db.Column(db.Integer)  # Our team's score
    score_them = db.Column(db.Integer)  # Opponent's score
    espn_game_id = db.Column(db.String(20))  # ESPN game ID for tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        result = "W" if self.won else "L"
        return f'<Game {self.team.name} vs {self.opponent} ({result})>'
    
    @property
    def score_string(self):
        """Format score as string"""
        if self.score_us is not None and self.score_them is not None:
            return f"{self.score_us}-{self.score_them}"
        return "TBD"

class WeeklyLine(db.Model):
    """Tracks updated Vegas O/U lines for projections"""
    __tablename__ = 'weekly_lines'
    
    id = db.Column(db.Integer, primary_key=True)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.id'), nullable=False)
    week = db.Column(db.Integer, nullable=False)  # Week when this line was set
    updated_line = db.Column(db.Float, nullable=False)  # Current O/U for remaining games
    original_line = db.Column(db.Float)  # Reference to original preseason line
    source = db.Column(db.String(50), default='manual')  # 'espn', 'manual', 'api', etc.
    notes = db.Column(db.String(255))  # Optional notes about the update
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    team = db.relationship('Team', backref=db.backref('weekly_lines', lazy=True))
    
    def __repr__(self):
        return f'<WeeklyLine {self.team.name} Week {self.week}: {self.updated_line}>'
    
    @staticmethod
    def get_current_line(team_id, current_week):
        """Get the most recent Vegas line for a team"""
        return WeeklyLine.query.filter_by(team_id=team_id)\
                             .filter(WeeklyLine.week <= current_week)\
                             .order_by(WeeklyLine.week.desc())\
                             .first()

# Helper functions for seeding data
def create_managers_data():
    """Create the 8 managers in draft order"""
    manager_names = [
        'Cliff', 'Petty', 'Andrew', 'Kyle', 
        'Chad', 'Shelby', 'Levi', 'TB'
    ]
    
    managers = []
    for i, name in enumerate(manager_names, 1):
        manager_data = {'name': name, 'draft_position': i}
        managers.append(manager_data)
    
    return managers

def seed_database():
    """Initialize database with managers"""
    try:
        # Create managers if they don't exist
        if Manager.query.count() == 0:
            manager_data = create_managers_data()
            for data in manager_data:
                manager = Manager(name=data['name'], draft_position=data['draft_position'])
                db.session.add(manager)
            db.session.commit()
            print(f"Created {len(manager_data)} managers")
        else:
            print("Managers already exist in database")
            
    except Exception as e:
        db.session.rollback()
        print(f"Error seeding database: {e}")
        raise