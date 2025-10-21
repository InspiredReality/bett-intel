"""
NFL Data Collector - Auto-scrapes ALL matchup stats for the week
Fetches: Odds (API) + Betting % (Scraped) + Full Matchup Stats (TeamRankings)
"""

import json
import time
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from datetime import datetime, timedelta
from typing import Dict, List
import re

class NFLDataCollector:
    def __init__(self, odds_api_key: str, nfl_week: int = None):
        """
        Initialize the collector
        
        Args:
            odds_api_key: Your API key from https://the-odds-api.com/
            nfl_week: NFL week number (if None, will attempt to auto-detect)
        """
        self.odds_api_key = odds_api_key
        self.nfl_week = nfl_week
        self.driver = None
        self.data = {
            'week': nfl_week,
            'games': [],
            'last_updated': None,
            'data_sources': {
                'odds': 'The Odds API',
                'betting_percentages': 'SportsBettingDime',
                'matchup_stats': 'TeamRankings'
            }
        }
        
        # NFL team name to URL slug mapping
        self.team_slug_map = {
            'Arizona Cardinals': 'cardinals',
            'Atlanta Falcons': 'falcons',
            'Baltimore Ravens': 'ravens',
            'Buffalo Bills': 'bills',
            'Carolina Panthers': 'panthers',
            'Chicago Bears': 'bears',
            'Cincinnati Bengals': 'bengals',
            'Cleveland Browns': 'browns',
            'Dallas Cowboys': 'cowboys',
            'Denver Broncos': 'broncos',
            'Detroit Lions': 'lions',
            'Green Bay Packers': 'packers',
            'Houston Texans': 'texans',
            'Indianapolis Colts': 'colts',
            'Jacksonville Jaguars': 'jaguars',
            'Kansas City Chiefs': 'chiefs',
            'Las Vegas Raiders': 'raiders',
            'Los Angeles Chargers': 'chargers',
            'Los Angeles Rams': 'rams',
            'Miami Dolphins': 'dolphins',
            'Minnesota Vikings': 'vikings',
            'New England Patriots': 'patriots',
            'New Orleans Saints': 'saints',
            'New York Giants': 'giants',
            'New York Jets': 'jets',
            'Philadelphia Eagles': 'eagles',
            'Pittsburgh Steelers': 'steelers',
            'San Francisco 49ers': '49ers',
            'Seattle Seahawks': 'seahawks',
            'Tampa Bay Buccaneers': 'buccaneers',
            'Tennessee Titans': 'titans',
            'Washington Commanders': 'commanders'
        }
    
    def initialize_driver(self):
        """Initialize Selenium WebDriver"""
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.driver = webdriver.Chrome(options=options)
        print("✓ Browser initialized")
    
    def get_team_slug(self, team_name: str) -> str:
        """Convert team name to TeamRankings URL slug"""
        # Direct mapping
        if team_name in self.team_slug_map:
            return self.team_slug_map[team_name]
        
        # Fuzzy match - find best match
        for full_name, slug in self.team_slug_map.items():
            if team_name.lower() in full_name.lower() or full_name.lower() in team_name.lower():
                return slug
        
        # Fallback: convert to slug format
        slug = team_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def detect_nfl_week(self) -> int:
        """
        Auto-detect current NFL week based on season start
        NFL 2024-25 season started Sep 5, 2024
        """
        season_start = datetime(2024, 9, 5)
        now = datetime.now()
        
        if now < season_start:
            return 1
        
        days_since_start = (now - season_start).days
        week = (days_since_start // 7) + 1
        
        # Regular season is weeks 1-18
        if week > 18:
            return 18
        
        return max(1, week)
    
    def fetch_odds_from_api(self):
        """Fetch current NFL odds using The Odds API"""
        print("📊 Fetching odds from The Odds API...")
        
        url = "https://api.the-odds-api.com/v4/sports/americanfootball_nfl/odds"
        params = {
            'apiKey': self.odds_api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american'
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            games_data = response.json()
            print(f"✓ Found {len(games_data)} games")
            
            # Check remaining quota
            remaining = response.headers.get('x-requests-remaining')
            if remaining:
                print(f"📈 API requests remaining: {remaining}")
            
            # Auto-detect week if not provided
            if not self.nfl_week:
                self.nfl_week = self.detect_nfl_week()
                self.data['week'] = self.nfl_week
                print(f"📅 Auto-detected NFL Week {self.nfl_week}")
            
            # Process each game
            for game in games_data:
                game_info = {
                    'id': game['id'],
                    'home_team': game['home_team'],
                    'away_team': game['away_team'],
                    'commence_time': game['commence_time'],
                    'odds': self._process_odds(game.get('bookmakers', [])),
                    'betting_percentages': {},
                    'matchup_stats': {}
                }
                self.data['games'].append(game_info)
            
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"❌ Error fetching odds: {e}")
            return False
    
    def _process_odds(self, bookmakers: List) -> Dict:
        """Extract and average odds from multiple bookmakers"""
        if not bookmakers:
            return {}
        
        # Use first bookmaker
        first_book = bookmakers[0]
        markets = first_book.get('markets', [])
        
        odds_data = {
            'bookmaker': first_book.get('title', 'Unknown'),
            'spreads': {},
            'totals': {},
            'moneyline': {}
        }
        
        for market in markets:
            market_key = market['key']
            outcomes = market.get('outcomes', [])
            
            if market_key == 'spreads':
                for outcome in outcomes:
                    odds_data['spreads'][outcome['name']] = {
                        'line': outcome.get('point', 0),
                        'odds': outcome.get('price', 0)
                    }
            elif market_key == 'totals':
                for outcome in outcomes:
                    odds_data['totals'][outcome['name']] = {
                        'line': outcome.get('point', 0),
                        'odds': outcome.get('price', 0)
                    }
            elif market_key == 'h2h':
                for outcome in outcomes:
                    odds_data['moneyline'][outcome['name']] = outcome.get('price', 0)
        
        return odds_data
    
    def scrape_betting_percentages(self):
        """Scrape public betting percentages from SportsBettingDime"""
        print("\n💰 Scraping betting percentages...")
        
        if not self.driver:
            self.initialize_driver()
        
        try:
            self.driver.get('https://www.sportsbettingdime.com/nfl/public-betting-trends/')
            time.sleep(5)
            
            try:
                # Look for game rows
                game_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    '.game-card, .betting-trends-row, [data-game], .public-betting-game')
                
                if game_elements:
                    print(f"✓ Found {len(game_elements)} games with betting data")
                    
                    for game_el in game_elements:
                        try:
                            matchup = game_el.find_element(By.CSS_SELECTOR, 
                                '.matchup, .teams, .game-matchup, .team-names').text
                            
                            bet_pct = self._extract_text(game_el, 
                                '.spread-bet-pct, [data-spread-bet], .bet-percentage')
                            money_pct = self._extract_text(game_el, 
                                '.spread-money-pct, [data-spread-money], .money-percentage')
                            
                            self._add_betting_data(matchup, {
                                'spread_bet_pct': bet_pct,
                                'spread_money_pct': money_pct,
                                'source': 'SportsBettingDime'
                            })
                        except Exception as e:
                            continue
                else:
                    print("⚠️  No betting data elements found (may not be game week)")
                
            except TimeoutException:
                print("⚠️  Betting data not available yet")
                
        except Exception as e:
            print(f"❌ Error scraping betting percentages: {e}")
    
    def scrape_all_matchup_stats(self):
        """
        Automatically scrape offense vs defense stats for ALL games
        """
        print(f"\n📈 Scraping matchup stats for Week {self.nfl_week}...")
        
        if not self.driver:
            self.initialize_driver()
        
        success_count = 0
        total_games = len(self.data['games'])
        
        for idx, game in enumerate(self.data['games'], 1):
            print(f"\n[{idx}/{total_games}] Processing: {game['away_team']} @ {game['home_team']}")
            
            # Get team slugs
            away_slug = self.get_team_slug(game['away_team'])
            home_slug = self.get_team_slug(game['home_team'])
            
            # Try multiple URL patterns
            urls_to_try = [
                f"https://www.teamrankings.com/nfl/matchup/{away_slug}-{home_slug}-week-{self.nfl_week}-2025/stats",
                f"https://www.teamrankings.com/nfl/matchup/{away_slug}-at-{home_slug}-week-{self.nfl_week}-2025/stats",
            ]
            
            matchup_data = None
            
            for url in urls_to_try:
                try:
                    print(f"  Trying: {url}")
                    self.driver.get(url)
                    time.sleep(2)
                    
                    # Check if page loaded successfully
                    if "Page Not Found" in self.driver.title or "404" in self.driver.page_source:
                        continue
                    
                    # Wait for tables
                    wait = WebDriverWait(self.driver, 8)
                    tables = wait.until(EC.presence_of_all_elements_located(
                        (By.CSS_SELECTOR, 'table.tr-table')))
                    
                    if not tables:
                        continue
                    
                    matchup_data = {
                        'url': url,
                        'offense_vs_defense': {},
                        'scraped_at': datetime.now().isoformat()
                    }
                    
                    # Parse all tables
                    for table_idx, table in enumerate(tables):
                        try:
                            # Get section title (if available)
                            section_title = f"Table {table_idx + 1}"
                            try:
                                header = table.find_element(By.XPATH, 
                                    './preceding-sibling::h2[1] | ./preceding-sibling::h3[1]')
                                section_title = header.text.strip()
                            except:
                                pass
                            
                            # Get table headers
                            thead = table.find_element(By.TAG_NAME, 'thead')
                            headers = [th.text.strip() for th in thead.find_elements(By.TAG_NAME, 'th')]
                            
                            # Get table rows
                            tbody = table.find_element(By.TAG_NAME, 'tbody')
                            rows = tbody.find_elements(By.TAG_NAME, 'tr')
                            
                            table_data = []
                            for row in rows:
                                cells = row.find_elements(By.TAG_NAME, 'td')
                                if len(cells) >= 3:
                                    row_data = {
                                        'stat': cells[0].text.strip(),
                                        headers[1] if len(headers) > 1 else 'away': cells[1].text.strip(),
                                        headers[2] if len(headers) > 2 else 'home': cells[2].text.strip()
                                    }
                                    table_data.append(row_data)
                            
                            if table_data:
                                matchup_data['offense_vs_defense'][section_title] = table_data
                        
                        except Exception as e:
                            continue
                    
                    # If we got data, break the loop
                    if matchup_data['offense_vs_defense']:
                        game['matchup_stats'] = matchup_data
                        success_count += 1
                        print(f"  ✓ Success! Collected {len(matchup_data['offense_vs_defense'])} stat tables")
                        break
                    
                except Exception as e:
                    continue
            
            if not matchup_data or not matchup_data.get('offense_vs_defense'):
                print(f"  ⚠️  Could not find matchup data")
            
            # Rate limiting
            time.sleep(2)
        
        print(f"\n✓ Successfully scraped {success_count}/{total_games} matchups")
    
    def _extract_text(self, element, selectors: str) -> str:
        """Helper to extract text from element"""
        try:
            for selector in selectors.split(','):
                try:
                    return element.find_element(By.CSS_SELECTOR, selector.strip()).text
                except:
                    continue
            return "N/A"
        except:
            return "N/A"
    
    def _add_betting_data(self, matchup: str, betting_data: Dict):
        """Add betting percentage data to matching game"""
        for game in self.data['games']:
            game_matchup = f"{game['away_team']} @ {game['home_team']}"
            # Fuzzy matching
            if (matchup.lower() in game_matchup.lower() or 
                game['away_team'].lower() in matchup.lower() or
                game['home_team'].lower() in matchup.lower()):
                game['betting_percentages'] = betting_data
                return
    
    def collect_all_data(self, include_matchups: bool = True):
        """
        Main method to collect all data
        
        Args:
            include_matchups: Whether to scrape detailed matchup stats (default: True)
        """
        print("🏈 Starting NFL Data Collection")
        print("="*60)
        
        # Step 1: Get odds from API
        print("\nSTEP 1: Fetching Odds Data")
        if not self.fetch_odds_from_api():
            print("⚠️  Warning: No odds data available")
            return False
        
        # Step 2: Scrape betting percentages
        print("\nSTEP 2: Scraping Betting Percentages")
        self.scrape_betting_percentages()
        
        # Step 3: Scrape matchup stats for ALL games
        if include_matchups:
            print(f"\nSTEP 3: Scraping Matchup Stats for Week {self.nfl_week}")
            self.scrape_all_matchup_stats()
        
        self.data['last_updated'] = datetime.now().isoformat()
        
        print("\n" + "="*60)
        print("✅ Data collection complete!")
        print(f"   Week: {self.nfl_week}")
        print(f"   Games: {len(self.data['games'])}")
        
        # Count games with matchup stats
        with_stats = sum(1 for g in self.data['games'] 
                        if g['matchup_stats'].get('offense_vs_defense'))
        print(f"   Games with matchup stats: {with_stats}/{len(self.data['games'])}")
        print("="*60)
        
        return True
    
    def save_to_json(self, filename: str = None):
        """Save all collected data to JSON"""
        if not filename:
            filename = f'nfl_week_{self.nfl_week}_data.json'
        
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        print(f"\n💾 Data saved to {filename}")
        return filename
    
    def close(self):
        """Cleanup"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser closed")


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Get your free API key from: https://the-odds-api.com/
    API_KEY = "YOUR_API_KEY_HERE"  # Replace with your actual key
    
    # Optional: specify NFL week (if None, auto-detects current week)
    WEEK = None  # or set to specific week like: WEEK = 7
    
    # Initialize collector
    collector = NFLDataCollector(
        odds_api_key=API_KEY,
        nfl_week=WEEK
    )
    
    try:
        # Collect ALL data including matchup stats for every game
        success = collector.collect_all_data(include_matchups=True)
        
        if success:
            # Save to file
            filename = collector.save_to_json()
            
            print("\n" + "="*60)
            print("🎉 SUCCESS! Next steps:")
            print(f"1. Upload '{filename}' to your dashboard")
            print("2. View comprehensive matchup analysis")
            print("3. Make informed betting decisions!")
            print("="*60)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        collector.close()