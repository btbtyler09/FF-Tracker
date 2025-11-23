#!/usr/bin/env python3
"""
Import draft data and initialize the fantasy football database
"""

import csv
import json
import os
from app import app
from database import db
from models import Manager, Team, DraftPick, Game, seed_database
from config import Config

def import_teams_data():
    """Import teams from JSON file"""
    teams_file = Config.TEAMS_DATA_FILE
    
    if not os.path.exists(teams_file):
        print(f"Teams data file not found: {teams_file}")
        return False
    
    try:
        with open(teams_file, 'r') as f:
            data = json.load(f)
        
        # Import college teams
        for team_name, team_info in data.get('college_teams', {}).items():
            team = Team.query.filter_by(name=team_name).first()
            if not team:
                team = Team(
                    name=team_name,
                    league='COLLEGE',
                    conference=team_info.get('conference'),
                    vegas_total=team_info.get('vegas_total'),
                    espn_id=team_info.get('espn_id'),
                    abbreviation=team_info.get('abbreviation')
                )
                db.session.add(team)
                print(f"Added college team: {team_name}")
            else:
                # Update existing team
                team.conference = team_info.get('conference')
                team.vegas_total = team_info.get('vegas_total')
                team.espn_id = team_info.get('espn_id')
                team.abbreviation = team_info.get('abbreviation')
                print(f"Updated college team: {team_name}")
        
        # Import NFL teams
        for team_name, team_info in data.get('nfl_teams', {}).items():
            team = Team.query.filter_by(name=team_name).first()
            if not team:
                team = Team(
                    name=team_name,
                    league='NFL',
                    conference=team_info.get('conference'),
                    division=team_info.get('division'),
                    vegas_total=team_info.get('vegas_total'),
                    espn_id=team_info.get('espn_id'),
                    abbreviation=team_info.get('abbreviation')
                )
                db.session.add(team)
                print(f"Added NFL team: {team_name}")
            else:
                # Update existing team
                team.conference = team_info.get('conference')
                team.division = team_info.get('division')
                team.vegas_total = team_info.get('vegas_total')
                team.espn_id = team_info.get('espn_id')
                team.abbreviation = team_info.get('abbreviation')
                print(f"Updated NFL team: {team_name}")
        
        db.session.commit()
        print(f"Successfully imported teams from {teams_file}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error importing teams data: {e}")
        return False

def import_draft_data():
    """Import draft results from CSV file"""
    draft_file = Config.DRAFT_DATA_FILE
    
    if not os.path.exists(draft_file):
        print(f"Draft data file not found: {draft_file}")
        return False
    
    try:
        with open(draft_file, 'r') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                manager_name = row['manager'].strip()
                team_name = row['team'].strip()
                round_num = int(row['round'])
                pick_num = int(row['pick'])
                
                # Find manager
                manager = Manager.query.filter_by(name=manager_name).first()
                if not manager:
                    print(f"Manager not found: {manager_name}")
                    continue
                
                # Find team
                team = Team.query.filter_by(name=team_name).first()
                if not team:
                    print(f"Team not found: {team_name}")
                    continue
                
                # Check if pick already exists
                existing_pick = DraftPick.query.filter_by(pick=pick_num).first()
                if existing_pick:
                    print(f"Pick {pick_num} already exists, skipping {team_name}")
                    continue
                
                # Create draft pick
                draft_pick = DraftPick(
                    manager_id=manager.id,
                    team_id=team.id,
                    round=round_num,
                    pick=pick_num
                )
                
                db.session.add(draft_pick)
                print(f"Added draft pick: {manager_name} -> {team_name} (Round {round_num}, Pick {pick_num})")
        
        db.session.commit()
        print(f"Successfully imported draft data from {draft_file}")
        return True
        
    except Exception as e:
        db.session.rollback()
        print(f"Error importing draft data: {e}")
        return False

def verify_data():
    """Verify the imported data"""
    print("\n=== Data Verification ===")
    
    # Check managers
    managers = Manager.query.all()
    print(f"Managers: {len(managers)}")
    for manager in managers:
        picks_count = DraftPick.query.filter_by(manager_id=manager.id).count()
        print(f"  {manager.name} (Position {manager.draft_position}): {picks_count} picks")
    
    # Check teams
    college_teams = Team.query.filter_by(league='COLLEGE').count()
    nfl_teams = Team.query.filter_by(league='NFL').count()
    print(f"\nTeams: {college_teams} college, {nfl_teams} NFL")
    
    # Check draft picks
    total_picks = DraftPick.query.count()
    print(f"Draft picks: {total_picks}")
    
    # Check for any issues
    issues = []
    
    # Verify each manager has correct number of picks
    for manager in managers:
        picks = DraftPick.query.filter_by(manager_id=manager.id).all()
        if len(picks) != Config.TEAMS_PER_MANAGER:
            issues.append(f"{manager.name} has {len(picks)} picks instead of {Config.TEAMS_PER_MANAGER}")
    
    # Check for duplicate picks
    all_picks = DraftPick.query.all()
    pick_numbers = [p.pick for p in all_picks]
    if len(pick_numbers) != len(set(pick_numbers)):
        issues.append("Duplicate pick numbers found")
    
    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"  - {issue}")
    else:
        print("\n✅ All data looks good!")

def add_sample_games():
    """Add some sample game data for testing"""
    from data_updater import manual_update_game
    
    print("\n=== Adding Sample Games ===")
    
    sample_games = [
        ('Georgia', 'Clemson', True, 1),
        ('Georgia', 'Kentucky', True, 2),
        ('Ohio State', 'Indiana', True, 1),
        ('Ohio State', 'Western Michigan', True, 2),
        ('Texas', 'Colorado State', True, 1),
        ('Kansas City Chiefs', 'Baltimore Ravens', True, 1),
        ('Kansas City Chiefs', 'Cincinnati Bengals', False, 2),
        ('Buffalo Bills', 'Arizona Cardinals', True, 1),
        ('Buffalo Bills', 'Miami Dolphins', True, 2),
        ('San Francisco 49ers', 'New York Jets', True, 1),
    ]
    
    for team_name, opponent, won, week in sample_games:
        success = manual_update_game(team_name, opponent, won, week)
        if success:
            print(f"  ✅ {team_name} vs {opponent}: {'W' if won else 'L'}")
        else:
            print(f"  ❌ Failed to add {team_name} vs {opponent}")

def main():
    """Main import function"""
    print("Fantasy Football Tracker - Data Import")
    print("=" * 40)
    
    with app.app_context():
        # Create tables if they don't exist
        db.create_all()
        print("Database tables created")
        
        # Seed managers
        seed_database()
        
        # Import teams data
        print("\n1. Importing teams data...")
        if not import_teams_data():
            print("Failed to import teams data. Exiting.")
            return
        
        # Import draft data
        print("\n2. Importing draft data...")
        if not import_draft_data():
            print("Failed to import draft data. Exiting.")
            return
        
        # Verify data
        verify_data()
        
        # Add sample games for testing
        choice = input("\nAdd sample game data for testing? (y/n): ").lower().strip()
        if choice == 'y':
            add_sample_games()
        
        print("\n🎉 Data import completed successfully!")
        print("\nYou can now run the app with: python app.py")

if __name__ == '__main__':
    main()