"""
NFL Data Collector - Main collector class
Fetches odds, betting percentages, and matchup stats for all NFL games
"""

import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from .odds_api import OddsAPI


class NFLDataCollector:
    """Main class for collecting NFL betting data"""
    
    def __init__(self, odds_api_key: str, nfl_week: int = None):
        """
        Initialize the collector
        
        Args:
            odds_api_key: API key from The Odds API
            nfl_week: NFL week number (auto-detects if None)
        """
        self.odds_api = OddsAPI(odds_api_key)
        self.nfl_week = nfl_week or self._detect_nfl_week()
        self.driver = None
        
        self.data = {
            'week': self.nfl_week,
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
    
    def _detect_nfl_week(self) -> int:
        """Auto-detect current NFL week based on season start"""
        season_start = datetime(2024, 9, 5)  # 2024-25 season
        now = datetime.now()
        
        if now < season_start:
            return 1
        
        days_since_start = (now - season_start).days
        week = (days_since_start // 7) + 1
        
        return min(max(1, week), 18)  # Weeks 1-18
    
    def initialize_driver(self):
        """Initialize Selenium WebDriver"""
        print("Initializing browser...")

        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        try:
            self.driver = webdriver.Chrome(options=options)

            # Hide webdriver property to avoid detection
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': '''
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined
                    })
                '''
            })

            print("✓ Browser initialized")
        except Exception as e:
            print(f"Error initializing browser: {e}")
            print("Trying with webdriver-manager...")

            try:
                from selenium.webdriver.chrome.service import Service
                from webdriver_manager.chrome import ChromeDriverManager

                driver_path = ChromeDriverManager().install()
                if driver_path is None:
                    raise Exception("ChromeDriverManager returned None - driver installation failed")

                service = Service(driver_path)
                self.driver = webdriver.Chrome(service=service, options=options)
                print("✓ Browser initialized with webdriver-manager")
            except Exception as webdriver_error:
                print(f"❌ Failed to initialize Chrome driver: {webdriver_error}")
                print("\nPlease ensure Chrome/Chromium is installed:")
                print("  Ubuntu/Debian: sudo apt-get install chromium-browser chromium-chromedriver")
                print("  or download ChromeDriver from: https://chromedriver.chromium.org/")
                raise
    
    def get_team_slug(self, team_name: str) -> str:
        """Convert team name to TeamRankings URL slug"""
        # Direct mapping
        if team_name in self.team_slug_map:
            return self.team_slug_map[team_name]
        
        # Fuzzy match
        for full_name, slug in self.team_slug_map.items():
            if team_name.lower() in full_name.lower() or full_name.lower() in team_name.lower():
                return slug
        
        # Fallback: convert to slug format
        slug = team_name.lower()
        slug = re.sub(r'[^a-z0-9]+', '-', slug)
        slug = slug.strip('-')
        return slug
    
    def fetch_odds(self) -> bool:
        """Fetch NFL odds from The Odds API"""
        print("\n📊 Fetching odds from The Odds API...")
        
        games_data = self.odds_api.get_nfl_odds()
        
        if not games_data:
            print("❌ No games data received")
            return False
        
        print(f"✓ Found {len(games_data)} games")
        
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
    
    def _process_odds(self, bookmakers: List) -> Dict:
        """Extract odds from bookmakers"""
        if not bookmakers:
            return {}
        
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
        """Scrape public betting percentages"""
        print("\n💰 Scraping betting percentages...")
        
        if not self.driver:
            self.initialize_driver()
        
        try:
            self.driver.get('https://www.sportsbettingdime.com/nfl/public-betting-trends/')
            time.sleep(5)
            
            try:
                game_elements = self.driver.find_elements(By.CSS_SELECTOR, 
                    '.game-card, .betting-trends-row, [data-game], .public-betting-game')
                
                if game_elements:
                    print(f"✓ Found {len(game_elements)} games with betting data")
                    
                    for game_el in game_elements:
                        try:
                            matchup = self._extract_text(game_el, 
                                '.matchup, .teams, .game-matchup, .team-names')
                            
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
                    print("⚠️  No betting data elements found")
                    
            except TimeoutException:
                print("⚠️  Betting data not available yet")
                
        except Exception as e:
            print(f"❌ Error scraping betting percentages: {e}")
    
    def scrape_all_matchup_stats(self):
        """Auto-scrape matchup stats for ALL games"""
        print(f"\n📈 Scraping matchup stats for Week {self.nfl_week}...")
        
        if not self.driver:
            self.initialize_driver()
        
        success_count = 0
        total_games = len(self.data['games'])
        
        for idx, game in enumerate(self.data['games'], 1):
            print(f"\n[{idx}/{total_games}] {game['away_team']} @ {game['home_team']}")

            away_slug = self.get_team_slug(game['away_team'])
            home_slug = self.get_team_slug(game['home_team'])
            print(f"  Slugs: {away_slug} @ {home_slug}")

            # Try multiple URL patterns
            urls_to_try = [
                f"https://www.teamrankings.com/nfl/matchup/{away_slug}-{home_slug}-week-{self.nfl_week}-2025/stats",
                f"https://www.teamrankings.com/nfl/matchup/{away_slug}-at-{home_slug}-week-{self.nfl_week}-2025/stats",
                f"https://www.teamrankings.com/nfl/matchup/{home_slug}-{away_slug}-week-{self.nfl_week}-2025/stats",
                f"https://www.teamrankings.com/nfl/matchup/{home_slug}-at-{away_slug}-week-{self.nfl_week}-2025/stats",
            ]

            matchup_data = None

            for url in urls_to_try:
                try:
                    print(f"  Trying: {url}")
                    self.driver.get(url)
                    time.sleep(3)

                    # Debug: show page title
                    page_title = self.driver.title
                    print(f"    Page title: {page_title}")

                    # Check for 404
                    if "Page Not Found" in page_title or "404" in page_title or "Not Found" in self.driver.page_source[:500]:
                        print(f"    ⚠️  404 - Page not found")
                        continue

                    # Look for tables with multiple selectors
                    wait = WebDriverWait(self.driver, 10)
                    try:
                        tables = wait.until(EC.presence_of_all_elements_located(
                            (By.CSS_SELECTOR, 'table.tr-table, table[class*="stat"], table')))
                    except TimeoutException:
                        print(f"    ⚠️  Timeout - No tables found")
                        continue

                    if not tables:
                        print(f"    ⚠️  No tables on page")
                        continue

                    print(f"    Found {len(tables)} tables, processing...")

                    matchup_data = {
                        'url': url,
                        'offense_vs_defense': {},
                        'scraped_at': datetime.now().isoformat()
                    }

                    for table_idx, table in enumerate(tables):
                        try:
                            section_title = f"Table {table_idx + 1}"
                            try:
                                header = table.find_element(By.XPATH,
                                    './preceding-sibling::h2[1] | ./preceding-sibling::h3[1]')
                                section_title = header.text.strip()
                            except:
                                pass

                            thead = table.find_element(By.TAG_NAME, 'thead')
                            headers = [th.text.strip() for th in thead.find_elements(By.TAG_NAME, 'th')]

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
                            print(f"    ⚠️  Error processing table {table_idx}: {e}")
                            continue

                    if matchup_data['offense_vs_defense']:
                        game['matchup_stats'] = matchup_data
                        success_count += 1
                        print(f"  ✓ Success! Collected {len(matchup_data['offense_vs_defense'])} stat tables")
                        break
                    else:
                        print(f"    ⚠️  No data extracted from tables")

                except Exception as e:
                    print(f"    ❌ Error: {e}")
                    continue
            
            if not matchup_data or not matchup_data.get('offense_vs_defense'):
                print(f"  ⚠️  Could not find matchup data")
            
            time.sleep(2)  # Rate limiting
        
        print(f"\n✓ Successfully scraped {success_count}/{total_games} matchups")
    
    def _extract_text(self, element, selectors: str) -> str:
        """Extract text from element using multiple selectors"""
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
        """Add betting data to matching game"""
        for game in self.data['games']:
            game_matchup = f"{game['away_team']} @ {game['home_team']}"
            if (matchup.lower() in game_matchup.lower() or 
                game['away_team'].lower() in matchup.lower() or
                game['home_team'].lower() in matchup.lower()):
                game['betting_percentages'] = betting_data
                return
    
    def collect_all_data(self, include_matchups: bool = True) -> bool:
        """
        Main method to collect all data
        
        Args:
            include_matchups: Whether to scrape matchup stats (default: True)
        
        Returns:
            True if successful
        """
        print("🏈 Starting NFL Data Collection")
        print("="*60)
        
        # Step 1: Fetch odds
        print("\nSTEP 1: Fetching Odds Data")
        if not self.fetch_odds():
            print("⚠️  Warning: No odds data available")
            return False
        
        # Step 2: Scrape betting percentages
        print("\nSTEP 2: Scraping Betting Percentages")
        self.scrape_betting_percentages()
        
        # Step 3: Scrape matchup stats
        if include_matchups:
            print(f"\nSTEP 3: Scraping Matchup Stats for Week {self.nfl_week}")
            self.scrape_all_matchup_stats()
        
        self.data['last_updated'] = datetime.now().isoformat()
        
        print("\n" + "="*60)
        print("✅ Data collection complete!")
        print(f"   Week: {self.nfl_week}")
        print(f"   Games: {len(self.data['games'])}")
        
        with_stats = sum(1 for g in self.data['games'] 
                        if g['matchup_stats'].get('offense_vs_defense'))
        print(f"   Games with matchup stats: {with_stats}/{len(self.data['games'])}")
        print("="*60)
        
        return True
    
    def save_to_json(self, filename: str = None) -> str:
        """
        Save collected data to JSON file
        
        Args:
            filename: Output filename (auto-generates if None)
        
        Returns:
            Path to saved file
        """
        if not filename:
            filename = f'nfl_week_{self.nfl_week}_data.json'
        
        with open(filename, 'w') as f:
            json.dump(self.data, f, indent=2)
        
        print(f"\n💾 Data saved to {filename}")
        return filename
    
    def close(self):
        """Cleanup resources"""
        if self.driver:
            self.driver.quit()
            print("✓ Browser closed")


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    API_KEY = os.getenv('ODDS_API_KEY')
    
    if not API_KEY:
        print("Error: ODDS_API_KEY not set in environment")
        exit(1)
    
    collector = NFLDataCollector(odds_api_key=API_KEY)
    
    try:
        success = collector.collect_all_data(include_matchups=True)
        
        if success:
            collector.save_to_json()
            print("\n✅ Success! Check the JSON file for your data.")
    
    finally:
        collector.close()