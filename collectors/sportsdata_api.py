"""
SportsData.IO API wrapper - for betting percentages and trends
Free tier: 1,000 requests/month
"""

import requests
from typing import Dict, List, Optional


class SportsDataAPI:
    """Wrapper for SportsData.IO NFL betting data"""

    BASE_URL = "https://api.sportsdata.io/v3/nfl"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_betting_trends(self, season: int, week: int) -> List[Dict]:
        """
        Fetch NFL betting trends for a specific week

        Args:
            season: NFL season year (e.g., 2025)
            week: Week number (1-18)

        Returns:
            List of games with betting trends data including:
            - Public betting percentages
            - Money percentages
            - Line movements
        """
        url = f"{self.BASE_URL}/scores/json/BettingTrendsByWeek/{season}/{week}"

        params = {
            'key': self.api_key
        }

        try:
            print(f"Fetching betting trends for {season} Week {week}...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            trends = response.json()
            print(f"✓ Retrieved betting trends for {len(trends)} games")

            return trends

        except requests.exceptions.RequestException as e:
            print(f"Error fetching betting trends: {e}")
            return []

    def get_betting_splits(self, season: int, week: int) -> List[Dict]:
        """
        Fetch betting splits (public vs sharp money) for a week

        Args:
            season: NFL season year
            week: Week number

        Returns:
            List of games with betting split data
        """
        url = f"{self.BASE_URL}/scores/json/BettingSplitsByWeek/{season}/{week}"

        params = {
            'key': self.api_key
        }

        try:
            print(f"Fetching betting splits for {season} Week {week}...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            splits = response.json()
            print(f"✓ Retrieved betting splits for {len(splits)} games")

            return splits

        except requests.exceptions.RequestException as e:
            print(f"Error fetching betting splits: {e}")
            return []

    def get_game_odds(self, season: int, week: int) -> List[Dict]:
        """
        Fetch current and historical odds for games

        Args:
            season: NFL season year
            week: Week number

        Returns:
            List of games with odds data from multiple sportsbooks
        """
        url = f"{self.BASE_URL}/odds/json/GameOddsByWeek/{season}/{week}"

        params = {
            'key': self.api_key
        }

        try:
            print(f"Fetching game odds for {season} Week {week}...")
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            odds = response.json()
            print(f"✓ Retrieved odds for {len(odds)} games")

            return odds

        except requests.exceptions.RequestException as e:
            print(f"Error fetching game odds: {e}")
            return []

    def detect_reverse_line_movement(self, betting_data: Dict) -> bool:
        """
        Detect if there's reverse line movement (sharp money indicator)

        Args:
            betting_data: Dictionary with bet%, money%, and line movement

        Returns:
            True if reverse line movement detected
        """
        # Reverse line movement occurs when:
        # 1. Majority of bets (60%+) are on one side
        # 2. But the line moves TOWARD the other side
        # This indicates sharp money is on the less popular side

        bet_pct = betting_data.get('public_betting_percentage', 50)
        line_movement = betting_data.get('line_movement', 0)

        # If 60%+ on favorite but line moved toward underdog = reverse movement
        if bet_pct >= 60 and line_movement < 0:
            return True
        # If 60%+ on underdog but line moved toward favorite = reverse movement
        if bet_pct <= 40 and line_movement > 0:
            return True

        return False


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    API_KEY = os.getenv('SPORTSDATA_API_KEY')

    if not API_KEY:
        print("Error: SPORTSDATA_API_KEY not set in environment")
        exit(1)

    api = SportsDataAPI(API_KEY)

    # Test: Get betting trends for current week
    from config.settings import get_current_week
    current_week = get_current_week()

    trends = api.get_betting_trends(2025, current_week)

    if trends:
        print(f"\n✅ Successfully retrieved {len(trends)} games with betting trends")
        print("\nSample game data:")
        if len(trends) > 0:
            import json
            print(json.dumps(trends[0], indent=2))
