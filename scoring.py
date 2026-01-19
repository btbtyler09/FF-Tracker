from sqlalchemy import func
from models import Manager, Team, Game

def calculate_scores():
    """
    Calculate current standings based on league scoring rules:
    - +1 point per win (any game type: regular, bowl, playoff, championship)
    - +1 bonus for making playoffs (both college and NFL)
    - +1 bonus for winning conference championship (college)
    - +1 bonus for winning national championship (both)
    - +1 bonus for exceeding preseason Vegas win total (regular season only)
    """

    standings = []

    try:
        for manager in Manager.query.order_by(Manager.draft_position).all():
            total_points = 0
            team_scores = []
            postseason_points = 0

            for pick in manager.picks:
                team = pick.team
                points = 0
                bonus_points = 0

                # Count ALL wins (+1 each, regardless of game type)
                all_wins = Game.query.filter_by(
                    team_id=team.id,
                    won=True
                ).count()

                all_losses = Game.query.filter_by(
                    team_id=team.id,
                    won=False
                ).count()

                # Regular season wins (for O/U calculation only)
                regular_wins = Game.query.filter_by(
                    team_id=team.id,
                    game_type='regular',
                    won=True
                ).count()

                # All wins count as points
                points += all_wins

                # BONUS: Conference championship win (college only)
                if team.league == 'COLLEGE':
                    conf_champ_wins = Game.query.filter_by(
                        team_id=team.id,
                        game_type='conference_championship',
                        won=True
                    ).count()
                    if conf_champ_wins > 0:
                        bonus_points += 1  # Bonus for winning conf championship

                # BONUS: Making playoffs (both college and NFL)
                playoff_games = Game.query.filter_by(
                    team_id=team.id,
                    game_type='playoff'
                ).count()

                if playoff_games > 0:
                    bonus_points += 1  # Bonus for making playoffs

                # BONUS: Championship win (both college and NFL)
                championship_wins = Game.query.filter_by(
                    team_id=team.id,
                    game_type='championship',
                    won=True
                ).count()

                if championship_wins > 0:
                    bonus_points += 1  # Bonus for winning championship

                # BONUS: Vegas over/under (based on regular season wins only)
                vegas_bonus = 0
                if team.vegas_total and regular_wins > team.vegas_total:
                    vegas_bonus = 1
                    bonus_points += vegas_bonus

                points += bonus_points

                team_scores.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'league': team.league,
                    'conference': team.conference or '',
                    'total_wins': all_wins,
                    'total_losses': all_losses,
                    'regular_wins': regular_wins,  # Keep for O/U display
                    'record': f"{all_wins}-{all_losses}",
                    'postseason_points': bonus_points,  # Now represents all bonus points
                    'vegas_bonus': vegas_bonus,
                    'vegas_total': team.vegas_total,
                    'total_points': points,
                    'pick_info': {
                        'round': pick.round,
                        'pick': pick.pick
                    }
                })
                
                total_points += points
                postseason_points += bonus_points
            
            # Sort teams by points (descending), then by pick order for tiebreaker
            team_scores.sort(key=lambda x: (-x['total_points'], x['pick_info']['pick']))
            
            # Calculate mobile-friendly breakdowns
            total_wins = sum(team['total_wins'] for team in team_scores)
            total_losses = sum(team['total_losses'] for team in team_scores)
            total_bonus = sum(team['postseason_points'] for team in team_scores)  # Already includes vegas_bonus
            preseason_projection = sum(team['vegas_total'] or 0 for team in team_scores)

            manager_record = f"{total_wins}-{total_losses}"
            
            standings.append({
                'manager_name': manager.name,
                'manager_id': manager.id,
                'draft_position': manager.draft_position,
                'total_points': total_points,
                'postseason_points': postseason_points,  # For tiebreakers
                'teams': team_scores,
                'team_count': len(team_scores),
                # Mobile-friendly breakdowns
                'total_wins': total_wins,
                'total_bonus': total_bonus,
                'preseason_projection': preseason_projection,
                'manager_record': manager_record
            })
        
        # Sort standings by total points (descending), then by postseason points
        standings.sort(key=lambda x: (-x['total_points'], -x['postseason_points']))
        
        # Add rank to each manager
        for i, standing in enumerate(standings, 1):
            standing['rank'] = i
        
        return standings
        
    except Exception as e:
        print(f"Error calculating scores: {e}")
        return []

def get_manager_summary(manager_id):
    """Get detailed scoring summary for a specific manager"""
    
    try:
        manager = Manager.query.get(manager_id)
        if not manager:
            return None
        
        standings = calculate_scores()
        manager_standing = next((s for s in standings if s['manager_id'] == manager_id), None)
        
        if not manager_standing:
            return None
        
        # Add some additional stats
        total_regular_wins = sum(team['regular_wins'] for team in manager_standing['teams'])
        total_postseason = sum(team['postseason_points'] for team in manager_standing['teams'])
        college_teams = [team for team in manager_standing['teams'] if team['league'] == 'COLLEGE']
        nfl_teams = [team for team in manager_standing['teams'] if team['league'] == 'NFL']
        
        return {
            **manager_standing,
            'total_regular_wins': total_regular_wins,
            'total_postseason_points': total_postseason,
            'college_teams': college_teams,
            'nfl_teams': nfl_teams,
            'college_count': len(college_teams),
            'nfl_count': len(nfl_teams)
        }
        
    except Exception as e:
        print(f"Error getting manager summary for {manager_id}: {e}")
        return None

# Note: Projection functionality has been moved to projections.py
# This old implementation is kept for reference but should not be used
def calculate_projections_deprecated():
    """
    DEPRECATED: Old projection calculation method
    Use projections.py calculate_projections() instead for improved logic
    """
    print("Warning: Using deprecated projection method. Use projections.py instead.")
    return []

def get_league_stats():
    """Get overall league statistics"""
    from database import db
    
    try:
        total_games = Game.query.count()
        total_wins = Game.query.filter_by(won=True).count()
        total_teams = Team.query.count()
        total_managers = Manager.query.count()
        
        college_teams = Team.query.filter_by(league='COLLEGE').count()
        nfl_teams = Team.query.filter_by(league='NFL').count()
        
        # Current week
        current_week = db.session.query(func.max(Game.week)).filter(
            Game.game_type == 'regular'
        ).scalar() or 0
        
        return {
            'total_games': total_games,
            'total_wins': total_wins,
            'total_teams': total_teams,
            'total_managers': total_managers,
            'college_teams': college_teams,
            'nfl_teams': nfl_teams,
            'current_week': current_week,
            'games_per_team': round(total_games / total_teams, 1) if total_teams > 0 else 0
        }
        
    except Exception as e:
        print(f"Error getting league stats: {e}")
        return {}