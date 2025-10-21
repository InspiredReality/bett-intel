"""
The Odds API wrapper - handles all API interactions
"""

import requests
from typing import Dict, List, Optional


class OddsAPI:
    """Wrapper for The Odds API"""
    
    BASE_URL = "https://api.the-odds-api.com/v4"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.remaining_requests = None
    
    def get_nfl_odds(self, regions: str = 'us', markets: str = 'h2h,spreads,totals') -> List[Dict]:
        """
        Fetch NFL odds from The Odds API
        
        Args:
            regions: Comma-separated regions (default: 'us')
            markets: Comma-separated markets (default: 'h2h,spreads,totals')
        
        Returns:
            List of games with odds data
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
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching odds: {e}")
            return []
    
    def get_requests_remaining(self) -> Optional[int]:
        """Get remaining API requests for this billing period"""
        return self.remaining_requests