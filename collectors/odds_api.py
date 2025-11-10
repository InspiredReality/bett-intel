"""
The Odds API wrapper - handles all API interactions
"""

import requests
from typing import Dict, List, Optional, Tuple


class OddsAPI:
    """Wrapper for The Odds API"""

    BASE_URL = "https://api.the-odds-api.com/v4"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.remaining_requests = None

    @staticmethod
    def american_to_implied_prob(odds: int) -> float:
        """
        Convert American odds to implied probability

        Args:
            odds: American odds (e.g., -110, +150)

        Returns:
            Implied probability as percentage (0-100)
        """
        if odds < 0:
            # Favorite: |odds| / (|odds| + 100)
            return abs(odds) / (abs(odds) + 100) * 100
        else:
            # Underdog: 100 / (odds + 100)
            return 100 / (odds + 100) * 100

    @staticmethod
    def calculate_market_probabilities(outcomes: List[Dict]) -> Dict[str, float]:
        """
        Calculate implied probabilities for all outcomes in a market

        Args:
            outcomes: List of outcomes with odds

        Returns:
            Dict mapping outcome names to implied probabilities
        """
        probs = {}
        for outcome in outcomes:
            odds = outcome.get('price', 0)
            if odds:
                probs[outcome['name']] = OddsAPI.american_to_implied_prob(odds)
        return probs
    
    def get_nfl_odds(self, regions: str = 'us', markets: str = 'h2h,spreads,totals',
                     include_probabilities: bool = True) -> List[Dict]:
        """
        Fetch NFL odds from The Odds API with implied probabilities

        Args:
            regions: Comma-separated regions (default: 'us')
            markets: Comma-separated markets (default: 'h2h,spreads,totals')
            include_probabilities: Calculate implied probabilities from odds

        Returns:
            List of games with odds data and implied probabilities
        """
        url = f"{self.BASE_URL}/sports/americanfootball_nfl/odds"

        params = {
            'apiKey': self.api_key,
            'regions': regions,
            'markets': markets,
            'oddsFormat': 'american'
        }

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()

            # Track remaining requests
            self.remaining_requests = response.headers.get('x-requests-remaining')
            if self.remaining_requests:
                print(f"API requests remaining: {self.remaining_requests}")

            games = response.json()

            # Add implied probabilities if requested
            if include_probabilities:
                games = self._add_implied_probabilities(games)

            return games

        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds: {e}")
            return []

    def _add_implied_probabilities(self, games: List[Dict]) -> List[Dict]:
        """
        Add implied probability calculations to each game's markets

        Args:
            games: List of games from API

        Returns:
            Games with added 'implied_probabilities' for each market
        """
        for game in games:
            for bookmaker in game.get('bookmakers', []):
                for market in bookmaker.get('markets', []):
                    outcomes = market.get('outcomes', [])
                    probs = self.calculate_market_probabilities(outcomes)

                    # Add implied_prob field to each outcome
                    for outcome in outcomes:
                        outcome_name = outcome['name']
                        if outcome_name in probs:
                            outcome['implied_prob'] = round(probs[outcome_name], 1)

        return games
    
    def get_requests_remaining(self) -> Optional[int]:
        """Get remaining API requests for this billing period"""
        return self.remaining_requests