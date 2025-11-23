"""
Enhanced Projection System for Fantasy Football Tracker

This module provides intelligent projections that:
1. Use weighted averages between actual performance and Vegas expectations
2. Integrate weekly updated Vegas lines
3. Only update after complete weeks
4. Provide stable, realistic projections
"""

from sqlalchemy import func
from datetime import datetime
from models import Manager, Team, Game, WeeklyLine
from database import db
import logging

logger = logging.getLogger(__name__)

class ProjectionEngine:
    """Handles all projection calculations with improved logic"""
    
    def __init__(self, config=None):
        self.config = config or self._default_config()
    
    def _default_config(self):
        """Default projection configuration"""
        return {
            'min_games_for_actual': 3,      # Minimum games before using actual performance
            'max_actual_weight': 0.7,       # Maximum weight for actual vs Vegas (70%)
            'weight_ramp_games': 6,         # Games to reach max weight
            'update_after_week_complete': True,  # Only update after all games done
            'use_live_vegas_lines': True,   # Use updated Vegas lines if available
            'conservative_postseason': 0.8, # Scale postseason bonuses (80% of full value)
            'early_season_damping': 0.5,    # Reduce projection volatility early in season
        }
    
    def calculate_projections(self, current_week=None):
        """
        Calculate projected total points for each manager
        
        Args:
            current_week: Current week of season (auto-detected if None)
            
        Returns:
            List of manager projections sorted by projected total
        """
        try:
            if current_week is None:
                current_week = self._get_current_week()
            
            logger.info(f"Calculating projections for week {current_week}")
            
            projections = []
            
            for manager in Manager.query.order_by(Manager.draft_position).all():
                manager_projection = self._calculate_manager_projection(manager, current_week)
                projections.append(manager_projection)
            
            # Sort by projected total (descending)
            projections.sort(key=lambda x: x['projected_total'], reverse=True)
            
            # Add rank
            for i, projection in enumerate(projections, 1):
                projection['projected_rank'] = i
            
            logger.info(f"Calculated projections for {len(projections)} managers")
            return projections
            
        except Exception as e:
            logger.error(f"Error calculating projections: {e}")
            return []
    
    def _calculate_manager_projection(self, manager, current_week):
        """Calculate projection for a single manager"""
        total_projected = 0.0
        team_projections = []
        
        for pick in manager.picks:
            team = pick.team
            team_projection = self._calculate_team_projection(team, current_week)
            team_projections.append(team_projection)
            total_projected += team_projection['projected_total']
        
        return {
            'manager_name': manager.name,
            'manager_id': manager.id,
            'draft_position': manager.draft_position,
            'projected_total': round(total_projected, 1),
            'teams': team_projections,
            'calculation_week': current_week,
            'updated_at': datetime.utcnow().isoformat()
        }
    
    def _calculate_team_projection(self, team, current_week):
        """Calculate projection for a single team"""
        try:
            # Get current stats
            current_wins = self._get_team_wins(team.id)
            games_played = self._get_team_games_played(team.id)
            
            # Determine total regular season games
            total_reg_games = 17 if team.league == 'NFL' else 12
            remaining_games = max(0, total_reg_games - games_played)
            
            # Get current Vegas line (updated if available, original otherwise)
            current_line = self._get_current_vegas_line(team, current_week)
            
            # Calculate projected wins
            projected_wins = self._project_regular_season_wins(
                team, current_wins, games_played, remaining_games, 
                current_line, total_reg_games, current_week
            )
            
            # Calculate projected points
            base_points = projected_wins
            vegas_bonus = 1.0 if current_line and projected_wins > current_line else 0.0
            postseason_bonus = self._calculate_postseason_projection(
                team, projected_wins, current_week, total_reg_games
            )
            
            total_projected = base_points + vegas_bonus + postseason_bonus
            
            return {
                'team_name': team.name,
                'league': team.league,
                'current_wins': current_wins,
                'games_played': games_played,
                'remaining_games': remaining_games,
                'projected_wins': round(projected_wins, 1),
                'vegas_line_used': round(projected_wins, 1),  # Use projected wins as "updated" line
                'original_vegas_line': team.vegas_total,
                'vegas_bonus': vegas_bonus,
                'postseason_bonus': round(postseason_bonus, 1),
                'projected_total': round(total_projected, 1),
                'confidence': self._calculate_confidence(games_played, total_reg_games)
            }
            
        except Exception as e:
            logger.error(f"Error calculating projection for {team.name}: {e}")
            # Return safe defaults
            return {
                'team_name': team.name,
                'league': team.league,
                'projected_total': team.vegas_total or 8.0,
                'error': str(e)
            }
    
    def _project_regular_season_wins(self, team, current_wins, games_played, 
                                   remaining_games, vegas_line, total_games, current_week):
        """Project regular season wins using weighted average of actual vs Vegas"""
        
        # If no games played yet, use Vegas line
        if games_played == 0:
            return vegas_line if vegas_line else 8.0  # Default to 8 wins if no line
        
        # Calculate actual win rate
        actual_win_rate = current_wins / games_played if games_played > 0 else 0
        
        # Calculate Vegas expected win rate
        vegas_expected_rate = (vegas_line / total_games) if vegas_line else 0.5
        
        # Determine weight for actual performance
        if games_played < self.config['min_games_for_actual']:
            # Use mostly Vegas for small sample sizes
            actual_weight = min(games_played / self.config['min_games_for_actual'] * 0.3, 0.3)
        else:
            # Gradually increase weight of actual performance
            actual_weight = min(
                (games_played / self.config['weight_ramp_games']) * self.config['max_actual_weight'],
                self.config['max_actual_weight']
            )
        
        # Apply early season damping to reduce volatility
        season_progress = games_played / total_games
        if season_progress < 0.3:  # First 30% of season
            actual_weight *= self.config['early_season_damping']
        
        # Calculate blended win rate
        blended_rate = (actual_win_rate * actual_weight) + (vegas_expected_rate * (1 - actual_weight))
        
        # Project remaining wins and add to current wins
        projected_additional = remaining_games * blended_rate
        total_projected_wins = current_wins + projected_additional
        
        # Apply reasonable bounds (no team goes 0-17 or 17-0)
        total_projected_wins = max(1.0, min(total_projected_wins, total_games - 1.0))
        
        return total_projected_wins
    
    def _calculate_postseason_projection(self, team, projected_wins, current_week, total_games):
        """Calculate conservative postseason bonus projections"""
        
        # Scale postseason bonuses based on season progress
        season_progress = min(current_week / 15.0, 1.0)  # Assume ~15 week season
        conservative_factor = self.config['conservative_postseason']
        progress_factor = 1.0 - (season_progress * 0.3)  # Reduce projections as season progresses
        
        bonus = 0.0
        
        if team.league == 'NFL':
            # NFL postseason (14/32 teams make playoffs)
            if projected_wins >= 12:
                bonus = 2.5  # Strong playoff team: playoff spot + ~1.5 avg wins
            elif projected_wins >= 10:
                bonus = 1.2  # Borderline: ~60% chance * 2 avg points
            elif projected_wins >= 9:
                bonus = 0.4  # Wildcard hope: ~20% chance * 2 avg points
        else:
            # College postseason (more opportunities: bowls, CFP)
            if projected_wins >= 11:
                bonus = 3.0  # Elite: Conf championship + bowl/CFP wins
            elif projected_wins >= 9:
                bonus = 1.5  # Good: Bowl eligible + possible conf championship
            elif projected_wins >= 7:
                bonus = 0.6  # Borderline bowl eligible
        
        # Apply conservative and progress factors
        return bonus * conservative_factor * progress_factor
    
    def _get_current_vegas_line(self, team, current_week):
        """Get most recent Vegas line for team (updated or original)"""
        # Always use original line for calculations
        # We'll use projected_wins as the "updated" line for display
        return team.vegas_total
    
    def _get_team_wins(self, team_id):
        """Get current win count for team"""
        return Game.query.filter_by(
            team_id=team_id,
            game_type='regular',
            won=True
        ).count()
    
    def _get_team_games_played(self, team_id):
        """Get total games played for team"""
        return Game.query.filter_by(
            team_id=team_id,
            game_type='regular'
        ).count()
    
    def _get_current_week(self):
        """Determine current week of season"""
        max_week = db.session.query(func.max(Game.week)).filter(
            Game.game_type == 'regular'
        ).scalar()
        return max_week or 1
    
    def _calculate_confidence(self, games_played, total_games):
        """Calculate confidence level of projection (0-100%)"""
        if games_played == 0:
            return 0
        
        # Confidence increases with games played, maxing at ~85%
        base_confidence = min((games_played / total_games) * 85, 85)
        
        # Higher confidence later in season
        season_bonus = min((games_played / total_games) * 15, 15)
        
        return round(base_confidence + season_bonus)
    
    def should_update_projections(self):
        """
        Determine if projections should be updated based on configuration
        
        Returns:
            bool: True if projections should be updated
        """
        if not self.config['update_after_week_complete']:
            return True
        
        # Check if current week is complete
        current_week = self._get_current_week()
        return self._is_week_complete(current_week)
    
    def _is_week_complete(self, week):
        """
        Check if a given week's games are complete
        
        This is a simplified implementation - could be enhanced to check
        actual game schedules from ESPN API
        """
        # For now, assume week is complete if we have data for the next week
        next_week_games = Game.query.filter_by(week=week + 1).count()
        return next_week_games > 0

# Convenience functions for backward compatibility
def calculate_projections(config=None):
    """Calculate projections using default engine"""
    engine = ProjectionEngine(config)
    return engine.calculate_projections()

def get_team_projection(team_id, current_week=None, config=None):
    """Get projection for a specific team"""
    engine = ProjectionEngine(config)
    team = Team.query.get(team_id)
    if not team:
        return None
    
    if current_week is None:
        current_week = engine._get_current_week()
    
    return engine._calculate_team_projection(team, current_week)