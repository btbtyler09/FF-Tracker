import requests
from datetime import datetime, timedelta
import json
import time
from models import Team, Game
from database import db

# Team name mapping for known mismatches between ESPN and our database
TEAM_NAME_MAPPINGS = {
    # College teams
    'NC State Wolfpack': 'NC State',
    'North Carolina State Wolfpack': 'NC State',
    'N.C. State Wolfpack': 'NC State',
    'Miami Hurricanes': 'Miami',
    'Georgia Bulldogs': 'Georgia',
    'Texas Longhorns': 'Texas',
    'Ohio State Buckeyes': 'Ohio State',
    'Alabama Crimson Tide': 'Alabama',
    'Michigan Wolverines': 'Michigan',
    'Notre Dame Fighting Irish': 'Notre Dame',
    'USC Trojans': 'USC',
    'Southern California Trojans': 'USC',
    'Clemson Tigers': 'Clemson',
    'Florida State Seminoles': 'Florida State',
    'Penn State Nittany Lions': 'Penn State',
    'Tennessee Volunteers': 'Tennessee',
    'LSU Tigers': 'LSU',
    'Auburn Tigers': 'Auburn',
    'Florida Gators': 'Florida',
    'Oklahoma Sooners': 'Oklahoma',
    'Oregon Ducks': 'Oregon',  
    'Washington Huskies': 'Washington',
    
    # Add common teams that appear in ESPN data but aren't in our league (suppress warnings)
    'Boise State Broncos': None,  # Not in our league, suppress warning
    'South Florida Bulls': None,   # Not in our league, suppress warning (USF)
    
    # NFL teams - only add if ESPN returns different names than what's in our database
    # Current NFL teams have exact name matches, so no mappings needed
}

def find_team_by_espn_data(teams, espn_team_name, espn_abbr, espn_id):
    """
    Enhanced team matching that handles ESPN API variations
    Returns the matching Team object or None
    """
    # Create lookup dictionaries
    name_lookup = {team.name: team for team in teams}
    abbr_lookup = {team.abbreviation: team for team in teams if team.abbreviation}
    id_lookup = {team.espn_id: team for team in teams if team.espn_id}
    
    # Convert ESPN ID to string for comparison (ESPN returns int, we store string)
    espn_id_str = str(espn_id) if espn_id else ''
    
    # Strategy 1: Try exact ESPN ID match (most reliable)
    if espn_id_str and espn_id_str in id_lookup:
        matched_team = id_lookup[espn_id_str]
        print(f"✓ Matched '{espn_team_name}' to '{matched_team.name}' via ESPN ID {espn_id_str}")
        return matched_team
    
    # Strategy 2: Try mapped team name
    if espn_team_name in TEAM_NAME_MAPPINGS:
        mapped_name = TEAM_NAME_MAPPINGS[espn_team_name]
        if mapped_name is None:
            # Explicitly marked as not in our league, return None silently
            return None
        elif mapped_name in name_lookup:
            matched_team = name_lookup[mapped_name]
            print(f"✓ Matched '{espn_team_name}' to '{matched_team.name}' via name mapping")
            return matched_team
    
    # Strategy 3: Try direct name match
    if espn_team_name in name_lookup:
        matched_team = name_lookup[espn_team_name]
        print(f"✓ Matched '{espn_team_name}' to '{matched_team.name}' via exact name")
        return matched_team
    
    # Strategy 4: Try abbreviation match
    if espn_abbr and espn_abbr in abbr_lookup:
        matched_team = abbr_lookup[espn_abbr]
        print(f"✓ Matched '{espn_team_name}' to '{matched_team.name}' via abbreviation {espn_abbr}")
        return matched_team
    
    # Strategy 5 (partial name matching) removed - too aggressive and causes false matches
    # like "South Florida Bulls" matching "Florida"
    
    # Log unmatched teams for debugging
    print(f"⚠️  Could not match ESPN team: '{espn_team_name}' (abbr: '{espn_abbr}', id: '{espn_id}')")
    return None

# ESPN Team Schedule API base URLs
NFL_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams"
COLLEGE_TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams"

# API request settings
API_TIMEOUT = 15  # seconds
API_RETRY_COUNT = 3
API_RETRY_DELAY = 2  # seconds between retries
API_REQUEST_DELAY = 0.5  # seconds between teams


def fetch_with_retry(url, params, team_name=""):
    """
    Fetch URL with retry logic and proper error handling.
    Returns the JSON data or None on failure.
    """
    for attempt in range(1, API_RETRY_COUNT + 1):
        try:
            response = requests.get(url, params=params, timeout=API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.Timeout:
            print(f"    ⚠️  TIMEOUT (attempt {attempt}/{API_RETRY_COUNT}) fetching {team_name}: request exceeded {API_TIMEOUT}s")
            if attempt < API_RETRY_COUNT:
                time.sleep(API_RETRY_DELAY * attempt)  # Exponential backoff
        except requests.RequestException as e:
            print(f"    ⚠️  REQUEST ERROR (attempt {attempt}/{API_RETRY_COUNT}) fetching {team_name}: {e}")
            if attempt < API_RETRY_COUNT:
                time.sleep(API_RETRY_DELAY * attempt)

    print(f"    ❌ FAILED to fetch {team_name} after {API_RETRY_COUNT} attempts")
    return None


def update_game_results():
    """
    Main function to update all game results using team schedule API
    """
    
    print("Starting game results update...")
    
    try:
        # Get current year
        current_year = datetime.now().year
        print(f"Updating games for {current_year} season")
        
        # Get all teams and update each one
        all_teams = Team.query.all()
        print(f"Updating {len(all_teams)} teams...")
        
        for team in all_teams:
            print(f"  Updating {team.name} ({team.league})...")
            update_team_schedule(team, current_year)

            # Be nice to ESPN's API - longer delay to avoid rate limiting
            time.sleep(API_REQUEST_DELAY)
        
        db.session.commit()
        print("Game results update completed successfully")
        
    except Exception as e:
        db.session.rollback()
        print(f"Error updating game results: {e}")
        raise

def update_team_schedule(team, season_year):
    """
    Update a single team's game results from their schedule API
    """
    try:
        if not team.espn_id:
            print(f"    Warning: {team.name} has no ESPN ID, skipping")
            return
        
        # Determine the correct API URL based on league
        if team.league == 'NFL':
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team.espn_id}/schedule"
        elif team.league == 'COLLEGE':
            url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/teams/{team.espn_id}/schedule"
        else:
            print(f"    Warning: Unknown league '{team.league}' for {team.name}")
            return
        
        # Get the team's full schedule for the season
        # ESPN only returns the current phase by default, so we need to explicitly
        # request both regular season (seasontype=2) and postseason (seasontype=3)
        all_events = []

        # Fetch regular season (seasontype=2) and postseason (seasontype=3) separately
        for season_type in [2, 3]:
            params = {'season': season_year, 'seasontype': season_type}
            data = fetch_with_retry(url, params, f"{team.name} seasontype={season_type}")
            if data:
                all_events.extend(data.get('events', []))
            # Small delay between seasontype requests
            time.sleep(0.2)

        events = all_events
        if not events:
            print(f"    No games found for {team.name} in {season_year}")
            return
        
        # Process each game in the schedule
        games_processed = 0
        wins_found = 0
        
        for event in events:
            # Skip preseason games (seasonType.id = 1)
            season_type_id = event.get('seasonType', {}).get('id')
            if season_type_id == '1' or season_type_id == 1:
                continue  # Skip preseason games
            
            for competition in event.get('competitions', []):
                # Only process completed games
                completed = competition.get('status', {}).get('type', {}).get('completed', False)
                if not completed:
                    continue
                
                games_processed += 1
                
                # Find our team and opponent
                our_competitor = None
                opponent_competitor = None
                
                for competitor in competition.get('competitors', []):
                    competitor_team_id = str(competitor.get('team', {}).get('id', ''))
                    if competitor_team_id == str(team.espn_id):
                        our_competitor = competitor
                    else:
                        opponent_competitor = competitor
                
                if not our_competitor or not opponent_competitor:
                    print(f"    Warning: Could not find team matchup for game {event.get('id')}")
                    continue
                
                # Get game details
                game_date = datetime.fromisoformat(event.get('date', '').replace('Z', '+00:00'))
                opponent_name = opponent_competitor.get('team', {}).get('displayName', 'Unknown')
                our_score = float(our_competitor.get('score', {}).get('value', 0))
                their_score = float(opponent_competitor.get('score', {}).get('value', 0))
                won = our_score > their_score
                
                if won:
                    wins_found += 1
                
                # Determine week number (try to extract from event, fallback to calculated)
                week = 1
                week_info = event.get('week', {})
                if isinstance(week_info, dict) and 'number' in week_info:
                    week = week_info['number']
                elif isinstance(week_info, int):
                    week = week_info
                else:
                    # Calculate week based on date (rough estimate)
                    if team.league == 'NFL':
                        # NFL season starts around early September
                        season_start = datetime(season_year, 9, 7)
                    else:
                        # College season starts around late August  
                        season_start = datetime(season_year, 8, 26)
                    
                    days_since_start = (game_date - season_start).days
                    week = max(1, (days_since_start // 7) + 1)
                
                # Check if this game already exists in our database
                existing_game = Game.query.filter_by(
                    team_id=team.id,
                    espn_game_id=event.get('id')
                ).first()
                
                if existing_game:
                    # Update existing game if result changed
                    if (existing_game.won != won or 
                        existing_game.score_us != our_score or 
                        existing_game.score_them != their_score):
                        print(f"    Updated: {team.name} vs {opponent_name}: {int(our_score)}-{int(their_score)} ({'W' if won else 'L'})")
                        existing_game.won = won
                        existing_game.score_us = our_score
                        existing_game.score_them = their_score
                        existing_game.updated_at = datetime.utcnow()
                else:
                    # Create new game record
                    print(f"    Added: {team.name} vs {opponent_name}: {int(our_score)}-{int(their_score)} ({'W' if won else 'L'})")
                    game = Game(
                        team_id=team.id,
                        week=week,
                        opponent=opponent_name,
                        won=won,
                        game_type='regular',
                        game_date=game_date,
                        score_us=our_score,
                        score_them=their_score,
                        espn_game_id=event.get('id')
                    )
                    db.session.add(game)
        
        if games_processed > 0:
            print(f"    Processed {games_processed} completed games, {wins_found} wins")
        else:
            print(f"    No completed games found for {team.name}")

    except Exception as e:
        print(f"    ❌ Error processing schedule for {team.name}: {e}")






def manual_update_game(team_name, opponent, won, week=None, game_type='regular'):
    """
    Manually update a game result (useful for testing or when API fails)
    """
    
    try:
        team = Team.query.filter_by(name=team_name).first()
        if not team:
            print(f"Team '{team_name}' not found")
            return False
        
        if week is None:
            # Find the next week for this team
            last_game = Game.query.filter_by(team_id=team.id).order_by(Game.week.desc()).first()
            week = (last_game.week + 1) if last_game else 1
        
        # Check if game already exists
        existing_game = Game.query.filter_by(
            team_id=team.id,
            week=week,
            opponent=opponent,
            game_type=game_type
        ).first()
        
        if existing_game:
            existing_game.won = won
            existing_game.updated_at = datetime.utcnow()
        else:
            game = Game(
                team_id=team.id,
                week=week,
                opponent=opponent,
                won=won,
                game_type=game_type,
                game_date=datetime.utcnow()
            )
            db.session.add(game)
        
        db.session.commit()
        print(f"Updated {team_name} vs {opponent}: {'W' if won else 'L'}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error manually updating game: {e}")
        return False

# For testing purposes - add some sample data
def add_sample_games():
    """Add some sample game data for testing"""
    sample_results = [
        ('Georgia', 'Clemson', True, 1),
        ('Georgia', 'South Carolina', True, 2),
        ('Ohio State', 'Indiana', True, 1),
        ('Texas', 'Rice', True, 1),
        ('Kansas City Chiefs', 'Cincinnati Bengals', False, 1),
        ('Buffalo Bills', 'New York Jets', True, 1),
    ]
    
    for team_name, opponent, won, week in sample_results:
        manual_update_game(team_name, opponent, won, week)