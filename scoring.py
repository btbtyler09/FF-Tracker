from sqlalchemy import func
from models import Manager, Team, Game

def calculate_scores():
    """
    Calculate current standings based on league scoring rules:
    - +1 point per regular season win
    - +1 for winning conference championship (college)
    - +1 for winning bowl game (college)  
    - +1 for making playoffs (both)
    - +1 per playoff win (both)
    - +1 for championship win (both)
    - +1 for exceeding preseason Vegas win total
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
                team_postseason = 0
                
                # Regular season wins (+1 each)
                regular_wins = Game.query.filter_by(
                    team_id=team.id, 
                    game_type='regular',
                    won=True
                ).count()
                
                # Calculate full record (wins, losses, ties)
                total_regular_games = Game.query.filter_by(
                    team_id=team.id,
                    game_type='regular'
                ).count()
                regular_losses = Game.query.filter_by(
                    team_id=team.id,
                    game_type='regular',
                    won=False
                ).count()
                regular_ties = total_regular_games - regular_wins - regular_losses
                
                points += regular_wins
                
                # Conference championship games (college only)
                if team.league == 'COLLEGE':
                    conf_champ_games = Game.query.filter_by(
                        team_id=team.id,
                        game_type='conference_championship'
                    ).all()
                    
                    for game in conf_champ_games:
                        if game.won:
                            points += 1  # Win conference championship
                            team_postseason += 1
                
                # Bowl games (college only) - separate from playoffs
                if team.league == 'COLLEGE':
                    bowl_games = Game.query.filter_by(
                        team_id=team.id,
                        game_type='bowl',
                        won=True
                    ).all()
                    
                    for game in bowl_games:
                        points += 1  # Win bowl game
                        team_postseason += 1
                
                # Playoff participation and wins (both college and NFL)
                playoff_games = Game.query.filter_by(
                    team_id=team.id,
                    game_type='playoff'
                ).all()
                
                if playoff_games:
                    # +1 for making playoffs
                    points += 1
                    team_postseason += 1
                    
                    # +1 per playoff win
                    playoff_wins = len([g for g in playoff_games if g.won])
                    points += playoff_wins
                    team_postseason += playoff_wins
                
                # Championship games
                championship_games = Game.query.filter_by(
                    team_id=team.id,
                    game_type='championship',
                    won=True
                ).all()
                
                for game in championship_games:
                    points += 1  # Championship win
                    team_postseason += 1
                
                # Vegas over/under bonus
                vegas_bonus = 0
                if team.vegas_total and regular_wins > team.vegas_total:
                    vegas_bonus = 1
                    points += vegas_bonus
                
                team_scores.append({
                    'team_id': team.id,
                    'team_name': team.name,
                    'league': team.league,
                    'conference': team.conference or '',
                    'regular_wins': regular_wins,
                    'regular_losses': regular_losses,
                    'regular_ties': regular_ties,
                    'record': f"{regular_wins}-{regular_losses}-{regular_ties}",
                    'postseason_points': team_postseason,
                    'vegas_bonus': vegas_bonus,
                    'vegas_total': team.vegas_total,
                    'total_points': points,
                    'pick_info': {
                        'round': pick.round,
                        'pick': pick.pick
                    }
                })
                
                total_points += points
                postseason_points += team_postseason
            
            # Sort teams by points (descending), then by pick order for tiebreaker
            team_scores.sort(key=lambda x: (-x['total_points'], x['pick_info']['pick']))
            
            # Calculate mobile-friendly breakdowns
            total_wins = sum(team['regular_wins'] for team in team_scores)
            total_bonus = sum(team['postseason_points'] + team['vegas_bonus'] for team in team_scores)
            preseason_projection = sum(team['vegas_total'] or 0 for team in team_scores)
            
            # Calculate manager's total record (W-L-T) across all teams
            total_losses = 0
            total_ties = 0
            total_games = 0
            for team_data in team_scores:
                team = Team.query.get(team_data['team_id'])
                if team:
                    games_count = Game.query.filter_by(team_id=team.id, game_type='regular').count()
                    losses_count = Game.query.filter_by(team_id=team.id, game_type='regular', won=False).count()
                    ties_count = games_count - team_data['regular_wins'] - losses_count
                    total_games += games_count
                    total_losses += losses_count
                    total_ties += ties_count
            
            manager_record = f"{total_wins}-{total_losses}-{total_ties}"
            
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