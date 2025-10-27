"""
Configuration settings for NFL Betting Intelligence
"""

import os
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Keys
ODDS_API_KEY = os.getenv('ODDS_API_KEY', '')

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = os.getenv('DATA_DIR', str(BASE_DIR / 'data'))
LOGS_DIR = os.getenv('LOGS_DIR', str(BASE_DIR / 'logs'))

# Ensure directories exist
Path(DATA_DIR).mkdir(parents=True, exist_ok=True)
Path(DATA_DIR, 'weekly').mkdir(parents=True, exist_ok=True)
Path(DATA_DIR, 'alerts').mkdir(parents=True, exist_ok=True)
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

# Scraping settings
HEADLESS = os.getenv('HEADLESS', 'true').lower() == 'true'
TIMEOUT_SECONDS = int(os.getenv('TIMEOUT_SECONDS', '10'))
CHROMEDRIVER_PATH = os.getenv('CHROMEDRIVER_PATH', None)

# Data storage
SAVE_HISTORICAL = os.getenv('SAVE_HISTORICAL', 'true').lower() == 'true'

# NFL Season settings
NFL_SEASON_START = datetime(2025, 9, 4)  # 2025-26 season start


def get_current_week() -> int:
    """
    Calculate current NFL week based on season start date
    
    Returns:
        Current week number (1-18 for regular season)
    """
    today = datetime.now()
    
    if today < NFL_SEASON_START:
        return 1
    
    days_since_start = (today - NFL_SEASON_START).days
    week = (days_since_start // 7) + 1
    
    # Regular season is weeks 1-18
    return min(max(1, week), 18)


# Alert thresholds
SHARP_MONEY_THRESHOLD = 25.0  # Percentage differential
VALUE_TOTAL_THRESHOLD = 0.20  # 20% above/below expected
MISMATCH_THRESHOLD = 8.0  # Point differential
PUBLIC_FADE_THRESHOLD = 75.0  # Percentage of public bets

# Database settings (if using database instead of JSON files)
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '5432'))
DB_NAME = os.getenv('DB_NAME', 'nfl_betting')
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# Storage backend ('json' or 'database')
STORAGE_BACKEND = os.getenv('STORAGE_BACKEND', 'json')

# Vercel/R2 settings (if using cloud storage)
VERCEL_TOKEN = os.getenv('VERCEL_TOKEN', '')
R2_ACCESS_KEY = os.getenv('R2_ACCESS_KEY', '')
R2_SECRET_KEY = os.getenv('R2_SECRET_KEY', '')
R2_BUCKET = os.getenv('R2_BUCKET', 'nfl-betting')
R2_ENDPOINT = os.getenv('R2_ENDPOINT', '')