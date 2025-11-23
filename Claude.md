# Claude Development Guide

## Project Overview
This is a simple Flask web application to track a fantasy football league with a unique format: each manager drafts 6 college teams and 4 NFL teams. The app tracks wins and calculates scores based on custom rules.

## Core Principles - KEEP IT SIMPLE
1. **Monolithic Architecture** - Single Flask app, no microservices
2. **SQLite Database** - No external database servers
3. **Minimal Dependencies** - Flask, SQLAlchemy, Requests only
4. **No Authentication** - It's for 8 trusted friends
5. **MVP First** - Get it working, optimize later
6. **Plain CSS/JS** - No React, Vue, or complex frameworks
7. **Single Docker Container** - Simple deployment

## League Rules (From League Constitution)
```
- 8 Managers total
- Each manager drafts 10 teams (6 College, 4 NFL)
- College teams must be from Power Four conferences (ACC, Big Ten, Big 12, SEC)
- Snake draft format
- Scoring:
  - +1 point per regular season win
  - +1 for winning conference championship (college)
  - +1 for winning bowl game (college)
  - +1 for making playoffs (both)
  - +1 per playoff win (both)
  - +1 for championship win (both)  
  - +1 for exceeding preseason Vegas win total
```

## Managers (Draft Order)
1. Cliff
2. Petty
3. Andrew (Commissioner)
4. Kyle
5. Chad
6. Shelby
7. Levi
8. TB

## Technical Stack
- **Backend**: Flask (Python 3.11)
- **Database**: SQLite (file-based)
- **Frontend**: Jinja2 templates + vanilla CSS/JS
- **Deployment**: Docker → Docker Hub → Unraid
- **Domain**: Cloudflare Tunnel

## File Structure (Keep it flat and simple)
```
fantasy-football-tracker/
├── app.py                  # Main Flask app
├── models.py              # Database models
├── scoring.py             # Score calculation
├── data_updater.py        # Fetch game results
├── import_draft.py        # One-time draft import
├── static/
│   ├── style.css
│   └── script.js
├── templates/
│   ├── base.html
│   ├── index.html
│   └── manager.html
├── data/
│   └── draft_results.csv
├── database.db            # SQLite file (gitignored)
├── requirements.txt
├── Dockerfile
├── README.md
├── Claude.md              # This file
└── .gitignore
```

## Database Schema (SQLite)
Keep models simple with basic relationships:
- **Manager**: id, name, draft_position
- **Team**: id, name, league (NFL/COLLEGE), conference, vegas_total
- **DraftPick**: id, manager_id, team_id, round, pick
- **Game**: id, team_id, week, opponent, won, game_type, date

## Implementation Priority
### Phase 1 - Get It Running (By Friday)
1. ✅ Basic Flask app with routes
2. ✅ SQLite database with models
3. ✅ Import draft results from CSV
4. ✅ Display standings page
5. ✅ Manual score calculation

### Phase 2 - Add Data (Week 1 of Season)
1. Connect to ESPN API for scores
2. Auto-update game results
3. Add Vegas line tracking
4. Simple projections

### Phase 3 - Polish (Later)
1. Better styling
2. Mobile responsive
3. Auto-refresh during games
4. Historical tracking

## Code Guidelines

### DO:
- Write simple, readable code
- Use Flask's built-in features
- Keep functions under 30 lines
- Use SQLAlchemy ORM (no raw SQL)
- Comment complex logic
- Handle errors gracefully
- Use environment variables for secrets

### DON'T:
- Over-engineer solutions
- Add unnecessary abstractions
- Use complex JavaScript frameworks
- Implement user auth (yet)
- Create multiple databases
- Use Redis/caching (yet)
- Build an API-first architecture
- Add features not in the requirements

## ESPN Data Integration
When implementing data fetching:
1. Start with NFL (easier API)
2. Use ESPN's hidden API endpoints
3. Only fetch what we need (wins, game type)
4. Update once per hour during games
5. Cache results in database

### NFL Endpoint Example:
```python
# ESPN API endpoint for NFL scores
url = f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week={week}"
```

### College Endpoint Example:
```python
# ESPN API endpoint for college scores
url = f"https://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?week={week}&group=80"
# group=80 is FBS
```

## Error Handling
- Log errors, don't crash
- Provide fallback data when APIs fail
- Show last known good data
- Allow manual score entry as backup

## Deployment Notes
1. **Local Testing**: Use Flask development server
2. **Production**: Use Gunicorn with 2 workers
3. **Database**: Store in mounted volume for persistence
4. **Updates**: Pull from Docker Hub in Unraid

## Common Pitfalls to Avoid
1. **Overthinking the data model** - We only need 4 tables
2. **Complex frontend** - Server-side rendering is fine
3. **Perfect API integration** - Manual updates are okay as backup
4. **Real-time everything** - Updating every 5 minutes is plenty
5. **Feature creep** - Stick to the requirements

## Sample Code Patterns

### Route Pattern
```python
@app.route('/')
def index():
    # Simple and direct
    standings = calculate_scores()
    return render_template('index.html', standings=standings)
```

### Data Update Pattern
```python
def update_scores():
    # Fetch, parse, save - keep it simple
    for team in Team.query.all():
        results = fetch_team_results(team)
        save_game_results(team, results)
    db.session.commit()
```

### Error Handling Pattern
```python
try:
    data = fetch_from_espn()
except Exception as e:
    app.logger.error(f"ESPN fetch failed: {e}")
    return last_known_good_data()
```

## Testing Approach
- Manual testing is fine for MVP
- Test with 2024 season data first
- Verify scoring math with spreadsheet
- Have managers verify their team assignments

## Questions to Ask Before Adding Features
1. Do we need this for Friday's launch?
2. Will this work with SQLite?
3. Can we do this in under 20 lines?
4. Will all 8 managers actually use this?
5. Can it wait until after the season starts?

If any answer is "no", skip it for now.

## Environment Variables
```bash
# .env file
SECRET_KEY=any-random-string-for-development
DATABASE_URL=sqlite:///database.db
UPDATE_INTERVAL=300  # 5 minutes in seconds
DEBUG=True  # Set to False in production
```

## Quick Commands
```bash
# Run locally
python app.py

# Import draft data
python import_draft.py

# Build Docker image
docker build -t fantasy-tracker .

# Run Docker container
docker run -p 5000:5000 -v $(pwd)/data:/app/data fantasy-tracker

# Check logs
docker logs fantasy-tracker

# Enter container shell
docker exec -it fantasy-tracker /bin/bash
```

## Success Criteria
- [ ] Shows current standings
- [ ] Correctly calculates points from wins
- [ ] Updates scores (manual or auto)
- [ ] Displays each manager's teams
- [ ] Runs in Docker on Unraid
- [ ] Accessible via Cloudflare tunnel

That's it. Keep it simple, get it working, improve it later.