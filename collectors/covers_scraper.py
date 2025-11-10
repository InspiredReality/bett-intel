#!/usr/bin/env python3
"""
Covers.com scraper - Free public betting percentages
No API key required - scrapes publicly available data
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from typing import Dict, List, Optional
import time


class CoversScraper:
    """Scraper for Covers.com NFL betting percentages"""

    BASE_URL = "https://www.covers.com/sport/football/nfl/matchups"

    def __init__(self, headless: bool = True):
        """
        Initialize Covers scraper

        Args:
            headless: Run browser in headless mode
        """
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)

    def get_betting_percentages(self) -> List[Dict]:
        """
        Scrape current NFL betting percentages from Covers.com

        Returns:
            List of games with betting percentage data:
            - away_team: Away team name
            - home_team: Home team name
            - spread_bet_pct: Percentage of bets on favorite (spread)
            - total_bet_pct: Percentage of bets on Over
            - spread_money_pct: Percentage of money on favorite (if available)
            - total_money_pct: Percentage of money on Over (if available)
        """
        try:
            print(f"Loading Covers.com NFL matchups...")
            self.driver.get(self.BASE_URL)

            # Wait for page to load
            time.sleep(3)

            # Look for betting percentages section
            # Note: Covers.com structure may change - this is a starting point
            games = []

            # Find all matchup cards
            try:
                matchup_cards = self.wait.until(
                    EC.presence_of_all_elements_located((By.CLASS_NAME, "covers-CoversConsensus"))
                )

                print(f"Found {len(matchup_cards)} games with betting data")

                for card in matchup_cards:
                    try:
                        game_data = self._parse_matchup_card(card)
                        if game_data:
                            games.append(game_data)
                    except Exception as e:
                        print(f"Error parsing matchup card: {e}")
                        continue

            except Exception as e:
                print(f"Could not find matchup cards: {e}")

                # Try alternative selector
                try:
                    # Covers sometimes uses different class names
                    matchup_rows = self.driver.find_elements(By.CSS_SELECTOR, "[data-test-id='matchup-row']")
                    print(f"Found {len(matchup_rows)} matchup rows")

                    for row in matchup_rows:
                        try:
                            game_data = self._parse_matchup_row(row)
                            if game_data:
                                games.append(game_data)
                        except Exception as e:
                            print(f"Error parsing row: {e}")
                            continue
                except Exception as e2:
                    print(f"Alternative selector also failed: {e2}")

            return games

        except Exception as e:
            print(f"Error scraping Covers.com: {e}")
            return []

    def _parse_matchup_card(self, card) -> Optional[Dict]:
        """
        Parse a matchup card element to extract betting percentages

        Args:
            card: Selenium WebElement for matchup card

        Returns:
            Dictionary with team names and betting percentages
        """
        game_data = {}

        try:
            # Extract team names
            teams = card.find_elements(By.CLASS_NAME, "covers-CoversConsensus-team")
            if len(teams) >= 2:
                game_data['away_team'] = teams[0].text.strip()
                game_data['home_team'] = teams[1].text.strip()

            # Extract spread betting percentages
            spread_pct = card.find_elements(By.CLASS_NAME, "covers-CoversConsensus-percentage")
            if len(spread_pct) >= 1:
                pct_text = spread_pct[0].text.strip().replace('%', '')
                try:
                    game_data['spread_bet_pct'] = float(pct_text)
                except ValueError:
                    pass

            # Extract total (over/under) percentages
            total_pct = card.find_elements(By.CLASS_NAME, "covers-CoversConsensus-total")
            if len(total_pct) >= 1:
                pct_text = total_pct[0].text.strip().replace('%', '')
                try:
                    game_data['total_bet_pct'] = float(pct_text)
                except ValueError:
                    pass

            return game_data if len(game_data) > 2 else None

        except Exception as e:
            print(f"Error parsing card details: {e}")
            return None

    def _parse_matchup_row(self, row) -> Optional[Dict]:
        """
        Alternative parser for different page structure

        Args:
            row: Selenium WebElement for matchup row

        Returns:
            Dictionary with team names and betting percentages
        """
        game_data = {}

        try:
            # This is a placeholder - actual implementation depends on page structure
            # Use browser DevTools to inspect the actual HTML structure

            # Extract basic info
            cells = row.find_elements(By.TAG_NAME, "td")

            # The exact parsing logic will depend on Covers.com's current structure
            # You may need to adjust selectors based on the actual HTML

            return game_data if len(game_data) > 2 else None

        except Exception as e:
            print(f"Error parsing row details: {e}")
            return None

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()


if __name__ == "__main__":
    """Test the Covers scraper"""

    print("Testing Covers.com scraper...")
    print("=" * 60)

    scraper = CoversScraper(headless=False)  # Set to False to see browser

    try:
        betting_data = scraper.get_betting_percentages()

        if betting_data:
            print(f"\n✅ Successfully scraped {len(betting_data)} games")
            print("\nSample data:")
            import json
            for game in betting_data[:3]:  # Show first 3 games
                print(json.dumps(game, indent=2))
        else:
            print("\n⚠️  No betting data found")
            print("\nPossible reasons:")
            print("1. Covers.com changed their HTML structure")
            print("2. No games currently available")
            print("3. Anti-bot protection blocking scraper")
            print("\nSuggestion: Run with headless=False to see what's happening")

    finally:
        scraper.close()