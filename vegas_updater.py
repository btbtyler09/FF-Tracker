"""
Vegas Line Updater for Fantasy Football Tracker

Fetches updated Vegas O/U lines from various sources to improve projections.
Supports ESPN API, manual updates, and future integration with other sources.
"""

import requests
import json
import time
from datetime import datetime, timedelta
from models import Team, WeeklyLine, Game
from database import db
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

class VegasLineUpdater:
    """Handles fetching and updating Vegas lines from various sources"""
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
        self.session = requests.Session()
        self.session.timeout = 10
    
    def _default_config(self):
        """Default configuration for Vegas line updates"""
        return {
            'sources': [
                # 'espn',  # Disabled - ESPN API doesn't provide season win totals (always returns None)
                'projected'
            ],  # Available: 'espn', 'manual', 'projected'
            'update_frequency_hours': 24,  # How often to fetch updates
            'request_delay': 1.0,  # Seconds between API requests
            'max_retries': 3,
            'espn_base_url': 'https://site.api.espn.com/apis/site/v2/sports',
            'use_projected_fallback': True,  # Use projected lines if other sources fail
        }
    
    def update_all_lines(self, week=None, force=False):
        """
        Update Vegas lines for all teams
        
        Args:
            week: Week number to update for (current week if None)
            force: Force update even if recently updated
            
        Returns:
            dict: Summary of updates
        """
        if week is None:
            week = self._get_current_week()
        
        logger.info(f"Starting Vegas line update for week {week}")
        
        summary = {
            'week': week,
            'attempted': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0,
            'sources_used': [],
            'timestamp': datetime.utcnow()
        }
        
        try:
            teams = Team.query.all()
            summary['attempted'] = len(teams)
            
            for team in teams:
                try:
                    result = self._update_team_line(team, week, force)
                    if result['updated']:
                        summary['updated'] += 1
                    elif result['skipped']:
                        summary['skipped'] += 1
                    
                    if result['source'] and result['source'] not in summary['sources_used']:
                        summary['sources_used'].append(result['source'])
                    
                    # Rate limiting
                    time.sleep(self.config['request_delay'])
                    
                except Exception as e:
                    logger.error(f"Error updating line for {team.name}: {e}")
                    summary['errors'] += 1
            
            # Commit all changes
            db.session.commit()
            
            logger.info(f"Vegas line update complete: {summary['updated']} updated, "
                       f"{summary['errors']} errors, {summary['skipped']} skipped")
            
            return summary
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during Vegas line update: {e}")
            summary['errors'] = summary['attempted']
            return summary
    
    def _update_team_line(self, team, week, force=False):
        """Update Vegas line for a single team"""
        result = {
            'team_id': team.id,
            'team_name': team.name,
            'updated': False,
            'skipped': False,
            'source': None,
            'new_line': None,
            'error': None
        }
        
        try:
            # Check if we need to update
            if not force and self._should_skip_update(team, week):
                result['skipped'] = True
                return result
            
            # Try each source in order
            for source in self.config['sources']:
                try:
                    new_line = self._fetch_line_from_source(team, source)
                    if new_line is not None:
                        # Save the updated line (with special handling for projected)
                        if source == 'projected':
                            self._save_projected_line(team, week, new_line)
                        else:
                            self._save_weekly_line(team, week, new_line, source)
                        result['updated'] = True
                        result['source'] = source
                        result['new_line'] = new_line
                        logger.debug(f"Updated {team.name} line to {new_line} from {source}")
                        break
                        
                except Exception as e:
                    logger.warning(f"Failed to fetch line for {team.name} from {source}: {e}")
                    continue
            
            if not result['updated'] and not result['skipped']:
                logger.debug(f"No line update available for {team.name}")
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"Error updating team line for {team.name}: {e}")
        
        return result
    
    def _fetch_line_from_source(self, team, source):
        """Fetch Vegas line from a specific source"""
        if source == 'espn':
            return self._fetch_espn_line(team)
        elif source == 'projected':
            return self._fetch_projected_line(team)
        elif source == 'manual':
            # Manual updates are handled separately
            return None
        else:
            logger.warning(f"Unknown source: {source}")
            return None
    
    def _fetch_espn_line(self, team):
        """
        Fetch Vegas line from ESPN API
        
        ESPN's API sometimes includes betting odds in their scoreboard endpoints.
        This is best-effort since ESPN doesn't guarantee betting data availability.
        """
        try:
            if team.league == 'NFL':
                url = f"{self.config['espn_base_url']}/football/nfl/teams/{team.espn_id or team.abbreviation}"
            else:
                url = f"{self.config['espn_base_url']}/football/college-football/teams/{team.espn_id or team.abbreviation}"
            
            # Add season context
            current_year = datetime.now().year
            url += f"?season={current_year}"
            
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Try to extract betting information
            # ESPN's betting data structure can vary, so this is best-effort
            line = self._parse_espn_betting_data(data, team)
            return line
            
        except requests.RequestException as e:
            logger.warning(f"ESPN API request failed for {team.name}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing ESPN data for {team.name}: {e}")
            return None
    
    def _parse_espn_betting_data(self, data, team):
        """
        Parse betting data from ESPN API response
        
        Note: ESPN's betting data structure is not documented and may change.
        This is a best-effort implementation.
        """
        try:
            # Look for season win totals in various places
            # This structure is speculative based on ESPN's typical API patterns
            
            if 'team' in data:
                team_data = data['team']
                
                # Check for season records/projections
                if 'record' in team_data:
                    record = team_data['record']
                    # Look for projected wins or season totals
                    # This is hypothetical - actual ESPN structure may differ
                    pass
                
                # Check for odds/betting section
                if 'odds' in team_data:
                    odds = team_data['odds']
                    # Parse season win total if available
                    pass
            
            # For now, return None since ESPN's betting API structure
            # is not publicly documented and may not be consistently available
            return None
            
        except Exception as e:
            logger.debug(f"Could not parse ESPN betting data for {team.name}: {e}")
            return None
    
    def _fetch_projected_line(self, team):
        """
        Use projected wins from projections.py as the updated Vegas line
        
        This leverages the existing projection logic instead of duplicating it.
        """
        try:
            from projections import get_team_projection
            
            current_week = self._get_current_week()
            
            # Get team projection (includes projected_wins)
            projection = get_team_projection(team.id, current_week)
            if not projection:
                logger.debug(f"No projection available for {team.name}")
                return None
            
            # Use projected_wins as the new O/U line
            projected_wins = projection.get('projected_wins')
            if projected_wins is None:
                logger.debug(f"No projected wins for {team.name}")
                return None
            
            # Need some games played for meaningful projection
            games_played = projection.get('games_played', 0)
            if games_played < 2:
                logger.debug(f"Not enough games ({games_played}) for {team.name} projection")
                return None
            
            logger.debug(f"Using projected line for {team.name}: "
                        f"{projected_wins} (based on projection system)")
            
            return projected_wins
            
        except ImportError:
            logger.error("projections module not available")
            return None
        except Exception as e:
            logger.warning(f"Error getting projected line for {team.name}: {e}")
            return None
    
    def _should_skip_update(self, team, week):
        """Check if we should skip updating this team's line"""
        # Check if we already have a recent update for this team and week
        recent_line = WeeklyLine.query.filter_by(
            team_id=team.id,
            week=week
        ).filter(
            WeeklyLine.updated_at > datetime.utcnow() - timedelta(hours=self.config['update_frequency_hours'])
        ).first()
        
        return recent_line is not None
    
    def _save_weekly_line(self, team, week, new_line, source, notes=None):
        """Save or update weekly line in database"""
        try:
            # Check if line already exists for this team/week
            existing_line = WeeklyLine.query.filter_by(
                team_id=team.id,
                week=week
            ).first()
            
            if existing_line:
                # Update existing line
                existing_line.updated_line = new_line
                existing_line.source = source
                existing_line.notes = notes or f"Updated from {source}"
                existing_line.updated_at = datetime.utcnow()
            else:
                # Create new line entry
                new_weekly_line = WeeklyLine(
                    team_id=team.id,
                    week=week,
                    updated_line=new_line,
                    original_line=team.vegas_total,
                    source=source,
                    notes=notes or f"Initial entry from {source}"
                )
                db.session.add(new_weekly_line)
            
            logger.debug(f"Saved line {new_line} for {team.name} week {week}")
            
        except Exception as e:
            logger.error(f"Error saving weekly line for {team.name}: {e}")
            raise
    
    def _save_projected_line(self, team, week, new_line):
        """Save projected line with appropriate metadata"""
        try:
            # Get team performance for notes
            games_played = Game.query.filter_by(
                team_id=team.id, 
                game_type='regular'
            ).count()
            current_wins = Game.query.filter_by(
                team_id=team.id, 
                game_type='regular', 
                won=True
            ).count()
            
            original_line = team.vegas_total or (8.0 if team.league == 'NFL' else 6.0)
            notes = (f"Projection-based update: {current_wins}/{games_played} record "
                    f"adjusted from original {original_line}")
            
            # Check if projected line already exists
            existing_line = WeeklyLine.query.filter_by(
                team_id=team.id,
                week=week,
                source='projected'
            ).first()
            
            if existing_line:
                # Update existing projected line
                existing_line.updated_line = new_line
                existing_line.notes = notes
                existing_line.updated_at = datetime.utcnow()
            else:
                # Create new projected line entry
                new_weekly_line = WeeklyLine(
                    team_id=team.id,
                    week=week,
                    updated_line=new_line,
                    original_line=original_line,
                    source='projected',
                    notes=notes
                )
                db.session.add(new_weekly_line)
            
            logger.debug(f"Saved projected line {new_line} for {team.name} week {week}")
            
        except Exception as e:
            logger.error(f"Error saving projected line for {team.name}: {e}")
            raise
    
    def manual_update_line(self, team_id, week, new_line, notes=None):
        """
        Manually update a team's Vegas line
        
        Args:
            team_id: Team ID to update
            week: Week number
            new_line: New O/U line
            notes: Optional notes about the update
            
        Returns:
            bool: True if successful
        """
        try:
            team = Team.query.get(team_id)
            if not team:
                logger.error(f"Team not found: {team_id}")
                return False
            
            self._save_weekly_line(team, week, new_line, 'manual', notes)
            db.session.commit()
            
            logger.info(f"Manually updated {team.name} line to {new_line} for week {week}")
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error manually updating line: {e}")
            return False
    
    def get_line_history(self, team_id, weeks=5):
        """Get recent line history for a team"""
        try:
            team = Team.query.get(team_id)
            if not team:
                return None
            
            current_week = self._get_current_week()
            start_week = max(1, current_week - weeks)
            
            lines = WeeklyLine.query.filter_by(team_id=team_id)\
                                  .filter(WeeklyLine.week >= start_week)\
                                  .order_by(WeeklyLine.week.desc())\
                                  .all()
            
            history = []
            for line in lines:
                history.append({
                    'week': line.week,
                    'line': line.updated_line,
                    'original': line.original_line,
                    'source': line.source,
                    'notes': line.notes,
                    'updated_at': line.updated_at.isoformat()
                })
            
            return {
                'team_name': team.name,
                'current_original_line': team.vegas_total,
                'history': history
            }
            
        except Exception as e:
            logger.error(f"Error getting line history for team {team_id}: {e}")
            return None
    
    def _get_current_week(self):
        """Get current week of season"""
        
        max_week = db.session.query(func.max(Game.week)).filter(
            Game.game_type == 'regular'
        ).scalar()
        return max_week or 1

# Convenience functions
def update_vegas_lines(week=None, force=False):
    """Update Vegas lines using default configuration"""
    updater = VegasLineUpdater()
    return updater.update_all_lines(week, force)

def manual_line_update(team_id, week, new_line, notes=None):
    """Manually update a team's Vegas line"""
    updater = VegasLineUpdater()
    return updater.manual_update_line(team_id, week, new_line, notes)

def get_team_line_history(team_id, weeks=5):
    """Get line history for a team"""
    updater = VegasLineUpdater()
    return updater.get_line_history(team_id, weeks)