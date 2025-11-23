# 🏈 Fantasy Football League Tracker

A simple Flask web application to track your unique fantasy football league where managers draft both college and NFL teams.

## Quick Install (LXC/Debian/Ubuntu)

```bash
# One-liner install
curl -sSL https://raw.githubusercontent.com/btbtyler09/FF-Tracker/main/install.sh | sudo bash

# Or clone and run
git clone https://github.com/btbtyler09/FF-Tracker.git
cd FF-Tracker
sudo ./install.sh
```

The installer will:
- Install all dependencies (Python 3, SQLite, etc.)
- Create a dedicated `ff-tracker` system user
- Set up the application in `/opt/ff-tracker`
- Create and enable a systemd service
- Optionally configure Cloudflare Tunnel for remote access

**Supported:** Debian 11+, Ubuntu 22.04+, Proxmox LXC containers

See [LXC Installation Guide](#lxc-installation-proxmox) for detailed instructions.

---

## League Format

- **8 Managers** (draft order: Cliff, Petty, Andrew, Kyle, Chad, Shelby, Levi, TB)
- **10 Teams per Manager**: 6 College + 4 NFL
- **College Teams**: Must be from Power Four conferences (ACC, Big Ten, Big 12, SEC)
- **Snake Draft**: Alternating draft order each round

## Scoring Rules

- **+1 point** per regular season win
- **+1 point** for winning conference championship (college only)
- **+1 point** for winning bowl game (college only)
- **+1 point** for making playoffs (both college & NFL)
- **+1 point** per playoff win (both college & NFL)
- **+1 point** for championship win (both college & NFL)
- **+1 point** for exceeding preseason Vegas win total

## Quick Start

### Method 1: Using Docker (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd FF-Tracker

# Build and run with Docker Compose
docker-compose up --build

# The app will be available at http://localhost:8742
```

### Method 2: Local Python Environment

```bash
# Clone and setup
git clone <your-repo-url>
cd FF-Tracker

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database and import draft data
python import_data.py

# Run the application
python app.py
```

The application will be available at `http://localhost:8742`

## Features

### ✅ Current Features
- **Draft Results Import** - Load team assignments from CSV
- **Live Standings** - Current rankings with total points and projected totals
- **Collapsible Team Display** - Space-efficient expandable team grids
- **Smart Projections** - Enhanced projection system with weighted algorithms
- **Vegas Line Tracking** - Preseason vs current O/U lines for projections
- **Automated Score Updates** - Background updates via cron jobs, startup updates
- **ESPN API Integration** - Fetches game results from public ESPN APIs
- **Scoring Calculation** - Automatic points based on wins and bonuses
- **Manager Details** - Individual team performance pages
- **Responsive Design** - Works on desktop and mobile
- **Docker Support** - Easy deployment with containers
- **Database Auto-Initialization** - Automatically imports seed data on first run
- **Multi-Worker Safety** - File locking prevents race conditions in production

### 🚧 Coming Soon
- **Advanced Vegas API** - Automated weekly line updates from betting sites
- **Playoff Brackets** - Visual tournament displays
- **Historical Data** - Season-over-season comparisons
- **Mobile PWA** - App-like mobile experience

## File Structure

```
FF-Tracker/
├── app.py                 # Main Flask application with API endpoints
├── models.py              # Database models (SQLAlchemy) including WeeklyLine
├── scoring.py             # Scoring logic and calculations  
├── projections.py         # NEW: Enhanced projection engine with smart algorithms
├── vegas_updater.py       # NEW: Vegas line fetching and management
├── data_updater.py        # ESPN API integration for game results
├── database.py            # Database initialization and connection
├── config.py              # Configuration settings with projection tuning
├── import_data.py         # Data initialization script
├── update_scores.py       # NEW: Standalone script for cron-based score updates
├── cron_schedule.txt      # NEW: Sample cron configuration for automated updates
├── requirements.txt       # Python dependencies
├── Dockerfile             # Container configuration
├── docker-compose.yml     # Multi-container orchestration
├── static/
│   ├── style.css          # Application styles with collapsible UI
│   └── script.js          # Enhanced client-side functionality
├── templates/
│   ├── base.html          # Base template
│   ├── index.html         # Standings page with expandable teams
│   └── manager.html       # Manager detail page
├── seed_data/
│   ├── draft_results.csv  # Draft picks data (80 actual picks)
│   └── teams.json         # Team info & Vegas lines (48 college, 32 NFL)
├── logs/                  # NEW: Log files for automated updates
│   ├── cron_updates.log   # Cron job execution logs
│   └── update_scores.log  # Detailed update process logs
└── dev/                   # Development files (git ignored)
    ├── LeagueRules.md     # League constitution
    └── ProjectPlan.md     # Project status and history
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Flask Configuration
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DATABASE_URL=sqlite:////app/data/database.db

# League Settings
LEAGUE_NAME=Gentlemen's Club Fantasy Football League
SEASON_YEAR=2025
UPDATE_INTERVAL=900

# Projection Configuration
PROJ_MIN_GAMES=3              # Min games before using actual performance
PROJ_MAX_WEIGHT=0.7           # Max weight for actual vs Vegas (70%)
PROJ_RAMP_GAMES=6             # Games to reach max weight  
PROJ_WEEK_COMPLETE=True       # Only update after week complete
PROJ_USE_LIVE_LINES=True      # Use updated Vegas lines
PROJ_CONSERVATIVE=0.8         # Scale postseason bonuses (80%)
PROJ_EARLY_DAMPING=0.5        # Reduce volatility early season

# Vegas Line Updater
VEGAS_UPDATE_FREQ=24          # Hours between updates
VEGAS_REQUEST_DELAY=1.0       # Seconds between API requests
VEGAS_MAX_RETRIES=3           # Max retries for failed requests
VEGAS_AUTO_UPDATE=False       # Enable automatic line updates
```

### Draft Data Format

Edit `seed_data/draft_results.csv` with your draft results:

```csv
manager,team,league,conference,round,pick,vegas_total
Cliff,Georgia,COLLEGE,SEC,1,1,10.5
Petty,Ohio State,COLLEGE,Big Ten,1,2,11.5
...
```

## API Endpoints

### Web Pages
- `GET /` - Standings page with collapsible team grids
- `GET /manager/<id>` - Manager detail page

### Game Data API  
- `GET /api/standings` - JSON standings data with projections
- `GET /api/update` - Manual game score update (deprecated - use cron jobs instead)
- `GET /health` - Health check endpoint

### Vegas Line Management API
- `GET /api/vegas-lines/update?force=true&week=1` - Trigger Vegas line updates
- `POST /api/vegas-lines/manual` - Manually update a team's Vegas line
- `GET /api/vegas-lines/history/<team_id>?weeks=5` - Get Vegas line history

#### Manual Vegas Line Update Example:
```bash
curl -X POST http://localhost:8742/api/vegas-lines/manual \
  -H "Content-Type: application/json" \
  -d '{
    "team_id": 1,
    "week": 1, 
    "new_line": 8.5,
    "notes": "Line moved after injury news"
  }'
```

## Enhanced Features Guide

### Smart Projections System

The app now includes an intelligent projection system that:

- **Blends actual performance with Vegas expectations** using weighted averages
- **Adapts projection confidence** as more games are played
- **Uses updated Vegas lines** when available for more accurate projections
- **Applies conservative postseason bonuses** based on projected wins
- **Reduces early-season volatility** to prevent wild swings from small samples

#### How Projections Work:

1. **Early Season** (< 3 games): Mostly based on Vegas preseason lines
2. **Mid Season** (3-6 games): Gradual blend of actual performance + Vegas  
3. **Late Season** (6+ games): Heavily weighted toward actual performance

#### Projection Display:

- **Projected Total**: Expected final points for each manager
- **Projected Wins**: Expected regular season wins for each team (→ arrow)
- **Preseason O/U**: Original Vegas line used for scoring bonuses
- **Current O/U**: Updated line used for projections (if different)

### Vegas Line Management

Track and update Vegas over/under lines throughout the season:

#### Viewing Lines:
- Expand any manager's teams to see both preseason and current O/U lines
- Lines marked with 📊 indicate they've been updated from preseason
- Green/red indicators show line movement direction and amount

#### Manual Line Updates:
```python
# In Python console or script
from vegas_updater import manual_line_update

# Update a team's line for current week
manual_line_update(team_id=1, week=1, new_line=9.5, notes="Injury update")
```

#### Automatic Updates:
Currently supports ESPN API integration (limited). Future versions will include:
- DraftKings API integration  
- FanDuel API integration
- Scheduled weekly updates

### Collapsible Interface

The standings table now features space-efficient design:
- **Collapsed view**: Shows team counts (6C/4N format)
- **Expanded view**: Shows full team grid with all details
- **Persistent state**: Remembers which managers are expanded

## Automated Score Updates

The application uses a combination of startup updates and scheduled cron jobs to keep game scores current without requiring manual intervention.

### Update Strategy

#### 1. **Startup Updates**
- App automatically updates scores when started in production mode (`DEBUG=False`)
- Skipped in development mode to avoid delays during testing
- Ensures fresh data when app is deployed or restarted

#### 2. **Scheduled Updates via Cron**
- Use the included `update_scores.py` script for automated updates
- Recommended schedule matches typical game completion times:
  - **Saturday 11 PM**: After college football games
  - **Sunday 11 PM**: After NFL games  
  - **Tuesday 2 AM**: After Monday Night Football
  - **Wednesday 8 AM**: Weekly catch-all with verbose logging

### Setting Up Cron Jobs

1. **Make update script executable:**
   ```bash
   chmod +x update_scores.py
   ```

2. **Install cron schedule:**
   ```bash
   # Edit your crontab
   crontab -e
   
   # Add these lines (adjust paths to your installation):
   0 23 * * 6 cd /path/to/FF-Tracker && python3 update_scores.py >> logs/cron_updates.log 2>&1
   0 23 * * 0 cd /path/to/FF-Tracker && python3 update_scores.py >> logs/cron_updates.log 2>&1  
   0 2 * * 2 cd /path/to/FF-Tracker && python3 update_scores.py >> logs/cron_updates.log 2>&1
   0 8 * * 3 cd /path/to/FF-Tracker && python3 update_scores.py --verbose >> logs/cron_updates.log 2>&1
   ```

3. **Verify cron installation:**
   ```bash
   crontab -l  # List installed cron jobs
   tail -f logs/cron_updates.log  # Monitor update logs
   ```

### Manual Updates

While automated updates are recommended, you can still run manual updates:

```bash
# Basic update
python3 update_scores.py

# Verbose update with detailed logging
python3 update_scores.py --verbose

# Dry run to see what would happen
python3 update_scores.py --dry-run
```

### Update Logging

- All updates are logged to `logs/cron_updates.log`
- Separate detailed logs in `logs/update_scores.log`
- Log files include timestamps, success/failure status, and error details
- Consider log rotation to prevent files from growing too large

## Development

### Running in Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Set development environment
export FLASK_ENV=development
export DEBUG=True

# Run with auto-reload
python app.py
```

### Adding Sample Data

```bash
# Import draft data and add sample games
python import_data.py
# Choose 'y' when prompted to add sample games
```

### Manual Score Updates

```python
from data_updater import manual_update_game

# Add a game result
manual_update_game('Georgia', 'Alabama', True, week=5)  # Georgia beat Alabama in week 5
```

### Testing Projections

```python  
from projections import calculate_projections
from config import get_config

# Calculate projections with current settings
config_obj = get_config()
projections = calculate_projections(config=config_obj.PROJECTION_CONFIG)

# Display projections for debugging
for p in projections[:3]:
    print(f"{p['manager_name']}: {p['projected_total']} points")
```

### Managing Vegas Lines

```python
from vegas_updater import manual_line_update, get_team_line_history

# Update a line manually  
manual_line_update(team_id=1, week=2, new_line=8.0, notes="Updated after injuries")

# View line history
history = get_team_line_history(team_id=1, weeks=5)
print(history)
```

## Deployment

### LXC Installation (Proxmox)

The recommended deployment method for Proxmox VE is using an LXC container with the automated install script.

#### Prerequisites

1. **Create a Debian/Ubuntu LXC container** in Proxmox:
   - Template: Debian 12 or Ubuntu 22.04/24.04
   - Resources: 1 CPU core, 512MB RAM minimum (1GB recommended)
   - Storage: 4GB minimum
   - Network: DHCP or static IP

2. **Ensure code is pushed to GitHub:**
   ```bash
   # Repository: https://github.com/btbtyler09/FF-Tracker
   ```

#### Installation Steps

1. **Start the LXC container** and access the console

2. **Run the installer:**
   ```bash
   # Option A: One-liner
   apt update && apt install -y curl
   curl -sSL https://raw.githubusercontent.com/btbtyler09/FF-Tracker/main/install.sh | bash

   # Option B: Clone and run
   apt update && apt install -y git
   git clone https://github.com/btbtyler09/FF-Tracker.git
   cd FF-Tracker
   ./install.sh
   ```

3. **Follow the prompts** to optionally configure Cloudflare Tunnel

4. **Access your app** at `http://LXC_IP:8742`

#### Post-Installation

**Service Management:**
```bash
sudo systemctl status ff-tracker    # Check status
sudo systemctl restart ff-tracker   # Restart app
sudo journalctl -u ff-tracker -f    # View logs
```

**Configuration:**
```bash
sudo nano /opt/ff-tracker/.env      # Edit settings
sudo systemctl restart ff-tracker   # Apply changes
```

**Cloudflare Tunnel (if skipped during install):**
```bash
sudo /opt/ff-tracker/setup-cloudflare.sh
```

**Uninstall:**
```bash
sudo /opt/ff-tracker/uninstall.sh
```

#### Directory Structure (After Install)

```
/opt/ff-tracker/
├── venv/              # Python virtual environment
├── data/
│   └── database.db    # SQLite database
├── logs/              # Application logs
├── .env               # Configuration file
├── app.py             # Main application
└── ...                # Other app files
```

---

### Docker Hub Deployment

```bash
# Build image
docker build -t yourusername/fantasy-tracker .

# Push to Docker Hub
docker push yourusername/fantasy-tracker

# Run from Docker Hub
docker run -p 8742:8742 -v ff_tracker_data:/app/data -v ff_tracker_logs:/app/logs yourusername/ff-tracker
```

### Unraid Deployment

#### **Step 1: Build and Push to Docker Hub**

```bash
# In your FF-Tracker directory
docker build -t yourusername/ff-tracker:latest .

# Login to Docker Hub
docker login

# Push to Docker Hub
docker push yourusername/ff-tracker:latest
```

#### **Step 2: Deploy on Unraid (GUI Method)**

1. **Open Unraid Docker Tab**
   - Navigate to Docker tab in Unraid WebGUI
   - Click "Add Container"
   - Toggle to "Advanced View" at top right

2. **Basic Configuration:**
   ```
   Name: ff-tracker
   Repository: yourusername/ff-tracker:latest
   Icon URL: https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/svg/football.svg
   
   WebUI: http://[IP]:[PORT:8742]
   Network Type: bridge
   Console shell command: bash
   ```

3. **Port Configuration:**
   ```
   Container Port: 8742
   Host Port: 8742 (or any available port you prefer)
   Connection Type: TCP
   ```

4. **Path Mappings (Volume Configuration):**
   
   Click **"Add another Path, Port, Variable, Label or Device"** and select **"Path"** from dropdown.
   
   **Option A: Named Volumes (Recommended - Docker manages permissions):**
   ```
   Config Type: Path
   Name: Data  
   Container Path: /app/data
   Host Path: (leave empty for named volume)
   Access Mode: Read/Write
   
   Config Type: Path
   Name: Logs
   Container Path: /app/logs  
   Host Path: (leave empty for named volume)
   Access Mode: Read/Write
   ```
   
   **Option B: Bind Mounts (Traditional approach):**
   ```
   Config Type: Path
   Name: Data
   Container Path: /app/data
   Host Path: /mnt/user/appdata/ff-tracker/data
   Access Mode: Read/Write
   
   Config Type: Path  
   Name: Logs
   Container Path: /app/logs
   Host Path: /mnt/user/appdata/ff-tracker/logs
   Access Mode: Read/Write
   ```

5. **Environment Variables:**
   
   Click **"Add another Path, Port, Variable, Label or Device"** and select **"Variable"** from dropdown.
   
   ```
   Key: SECRET_KEY
   Value: your-production-secret-key-change-this
   
   Key: DEBUG
   Value: False
   
   Key: DATABASE_URL
   Value: sqlite:////app/data/database.db
   
   Key: LEAGUE_NAME
   Value: Gentlemen's Club Fantasy Football League
   
   Key: SEASON_YEAR
   Value: 2025
   ```
   
   **⚠️ IMPORTANT: Generate a secure SECRET_KEY before production deployment:**
   ```bash
   python3 -c "import secrets; print(secrets.token_hex(32))"
   ```

6. **Apply and Start Container**

#### **Step 3: Alternative - Docker Run Command**

If you prefer command line on Unraid:

```bash
docker run -d \
  --name=ff-tracker \
  --restart=unless-stopped \
  -p 8742:8742 \
  -v ff_tracker_data:/app/data \
  -v ff_tracker_logs:/app/logs \
  -e SECRET_KEY="your-production-secret-key-change-this" \
  -e DEBUG="False" \
  -e DATABASE_URL="sqlite:////app/data/database.db" \
  -e LEAGUE_NAME="Gentlemen's Club Fantasy Football League" \
  -e SEASON_YEAR="2025" \
  yourusername/ff-tracker:latest
```

#### **Step 4: Set Up Automated Score Updates**

**Option A: Using Unraid User Scripts Plugin (Recommended)**

1. Install "User Scripts" plugin from Community Applications
2. Add new script called "FF-Tracker Score Update"
3. Script content:
   ```bash
   #!/bin/bash
   docker exec ff-tracker python3 update_scores.py >> /mnt/user/appdata/ff-tracker/logs/cron_updates.log 2>&1
   ```
4. Set schedule:
   - Saturday at 23:00 (After college games)
   - Sunday at 23:00 (After NFL games)  
   - Tuesday at 02:00 (After Monday Night Football)
   - Wednesday at 08:00 (Weekly catch-all)

**Option B: Manual Updates**

You can manually trigger updates anytime:
```bash
docker exec ff-tracker python3 update_scores.py --verbose
```

#### **Step 5: Access Your App**

- **Local Access:** `http://your-unraid-ip:8742`
- **WebUI Button:** Click the WebUI button in Docker tab
- **Mobile Access:** Works great on phones/tablets

#### **What Happens on First Start:**

1. **Database initialization** - Creates tables automatically
2. **Initial score update** - Fetches current game results from ESPN
3. **Data persistence** - All data saved to `/mnt/user/appdata/ff-tracker/`
4. **Logging** - Update logs saved for troubleshooting

#### **Troubleshooting:**

- **View logs:** `/mnt/user/appdata/ff-tracker/logs/`
- **Container logs:** Docker tab → ff-tracker → Logs
- **Database location:** `/mnt/user/appdata/ff-tracker/data/database.db`
- **Restart container:** Docker tab → ff-tracker → Stop/Start

### Cloudflare Tunnel

```bash
# Install cloudflared
# Create tunnel
cloudflared tunnel create fantasy-football

# Route traffic
cloudflared tunnel route dns fantasy-football yourdomain.com

# Run tunnel
cloudflared tunnel run fantasy-football
```

## Architecture Decisions

This app follows the **"Keep It Simple"** philosophy with smart enhancements:

### Core Philosophy
- **Monolithic Flask App** - No microservices, single container deployment
- **SQLite Database** - File-based, no external DB server required
- **Server-Side Rendering** - Jinja2 templates with progressive enhancement
- **Minimal Dependencies** - Flask, SQLAlchemy, Requests core stack
- **No Authentication** - Trusted users only

### Smart Enhancements  
- **Modular Projection System** - Separated `projections.py` for maintainability
- **Vegas Line Tracking** - New `WeeklyLine` model for historical data
- **Progressive UI** - Collapsible interface with persistent state
- **API-First Design** - RESTful endpoints for all major operations
- **Configuration-Driven** - Tunable projection parameters via environment

## Contributing

This is a private league tracker, but if you want to adapt it:

1. Fork the repository
2. Update `seed_data/draft_results.csv` with your draft
3. Modify `config.py` with your league settings
4. Customize `templates/` for your league branding
5. Deploy using Docker

## Troubleshooting

### Database Issues

**"unable to open database file" Error:**

This typically means SQLite is trying to use a relative path instead of absolute. Fix by ensuring DATABASE_URL uses 4 slashes:
```bash
# Wrong (relative path)
DATABASE_URL=sqlite:///data/database.db

# Correct (absolute path)  
DATABASE_URL=sqlite:////app/data/database.db
```

**Database Reset:**
```bash
# For local development
rm database.db
python import_data.py

# For Docker containers  
docker exec container_name rm /app/data/database.db
docker restart container_name
```

**Note:** If you see incorrect scores from NFL preseason games after updating the application, you may need to delete and recreate the database to remove old preseason game data.

**Race Condition on Startup:**

If you see "UNIQUE constraint failed" errors with multiple workers, the file locking system should prevent this. If it persists, try reducing workers:
```dockerfile
# In Dockerfile, change from:
CMD ["gunicorn", "--workers", "2", ...]
# To:
CMD ["gunicorn", "--workers", "1", ...]
```

### Port Conflicts
```bash
# Use different port
docker run -p 8000:8742 fantasy-tracker
```

### Permission Errors
```bash
# Fix data directory permissions (bind mounts only)
sudo chown -R $(whoami) data/
chmod 755 data/

# For Unraid, prefer named volumes to avoid permission issues
```

### Container Won't Start
```bash
# Check logs
docker logs container_name

# Common issues:
# 1. Wrong DATABASE_URL format (use absolute path with 4 slashes)
# 2. Missing environment variables
# 3. Port already in use
# 4. Volume permission issues (use named volumes)
```

### Scoring Issues

**NFL Teams Showing Incorrect Preseason Wins:**

If NFL teams show wins from preseason games (August), the database contains old data from before the preseason filtering was implemented:

```bash
# Solution: Delete database and let it rebuild
docker exec ff-tracker rm /app/data/database.db
docker restart ff-tracker
```

**Missing College Games:**

If college games aren't appearing (especially Week 0 games), the new team schedule API should capture them automatically. Check logs for API errors:

```bash
# Check update logs
docker exec ff-tracker tail -f /app/logs/cron_updates.log
```

## Commissioner Tools

As commissioner, you can:

- Manually update game results using the web interface
- Import new draft data by updating the CSV
- Monitor league stats and standings
- Export data for backup/analysis

## License

This project is for personal use by the 2025 Fantasy Football League participants.

---

**Commissioner:** Andrew Lloyd  
**Developer:** TB  
**Season:** 2025  

🏈 Good luck to all managers!