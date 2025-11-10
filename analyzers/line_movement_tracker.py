#!/usr/bin/env python3
"""
Line Movement Tracker - Infer sharp money from odds movements
Uses historical odds data to identify reverse line movement
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime


class LineMovementTracker:
    """
    Track line movements to identify sharp money action

    Sharp money indicators:
    1. Reverse line movement (line moves opposite to public betting)
    2. Steam moves (sudden sharp line movement across multiple books)
    3. Line freezes (books stop taking action on one side)
    """

    def __init__(self, data_dir: str = 'data/line_history'):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def save_snapshot(self, games: List[Dict], timestamp: Optional[str] = None) -> str:
        """
        Save current odds snapshot for later comparison

        Args:
            games: List of games with odds from The Odds API
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Path to saved snapshot file
        """
        if not timestamp:
            timestamp = datetime.now().isoformat()

        snapshot = {
            'timestamp': timestamp,
            'games': games
        }

        # Save with timestamp in filename
        filename = f"snapshot_{timestamp.replace(':', '-')}.json"
        filepath = self.data_dir / filename

        with open(filepath, 'w') as f:
            json.dump(snapshot, f, indent=2)

        print(f"📸 Saved odds snapshot: {filepath}")
        return str(filepath)

    def get_snapshots(self, game_id: str) -> List[Dict]:
        """
        Get all snapshots for a specific game

        Args:
            game_id: The game ID to retrieve snapshots for

        Returns:
            List of snapshots ordered by timestamp
        """
        snapshots = []

        for snapshot_file in sorted(self.data_dir.glob('snapshot_*.json')):
            with open(snapshot_file) as f:
                data = json.load(f)

            # Find this game in the snapshot
            for game in data.get('games', []):
                if game.get('id') == game_id:
                    snapshots.append({
                        'timestamp': data['timestamp'],
                        'game': game
                    })
                    break

        return snapshots

    def detect_reverse_line_movement(
        self,
        opening_line: float,
        current_line: float,
        implied_public_bet_pct: float,
        threshold: float = 55.0
    ) -> bool:
        """
        Detect reverse line movement (sharp money indicator)

        Args:
            opening_line: Opening spread/total
            current_line: Current spread/total
            implied_public_bet_pct: Estimated public betting % (from implied prob)
            threshold: Minimum public % to consider (default 55%)

        Returns:
            True if reverse line movement detected

        Example:
            Opening line: -3.5, Current: -2.5
            Public bet %: 65% on favorite
            Line moved TOWARD underdog despite public on favorite = REVERSE MOVEMENT
        """
        line_movement = current_line - opening_line

        # Public heavily on one side (>55%)
        if implied_public_bet_pct > threshold:
            # But line moved the opposite direction
            if line_movement < 0:  # Line moved down despite public betting up
                return True

        if implied_public_bet_pct < (100 - threshold):
            if line_movement > 0:  # Line moved up despite public betting down
                return True

        return False

    def detect_steam_move(self, snapshots: List[Dict]) -> Optional[Dict]:
        """
        Detect steam move (sudden sharp line movement)

        Args:
            snapshots: List of snapshots for a game ordered by time

        Returns:
            Dictionary with steam move details if detected, None otherwise

        A steam move is:
        - Line moves 1.5+ points in short time (<2 hours)
        - Movement across multiple sportsbooks simultaneously
        """
        if len(snapshots) < 2:
            return None

        for i in range(len(snapshots) - 1):
            prev_snapshot = snapshots[i]
            curr_snapshot = snapshots[i + 1]

            # Get spreads from multiple books
            prev_spreads = self._extract_spreads(prev_snapshot['game'])
            curr_spreads = self._extract_spreads(curr_snapshot['game'])

            # Count books that moved significantly
            significant_moves = 0
            total_movement = 0

            for book in prev_spreads:
                if book in curr_spreads:
                    movement = abs(curr_spreads[book] - prev_spreads[book])
                    if movement >= 1.5:  # 1.5+ point move
                        significant_moves += 1
                        total_movement += movement

            # Steam move if 3+ books moved 1.5+ points
            if significant_moves >= 3:
                return {
                    'timestamp': curr_snapshot['timestamp'],
                    'books_moved': significant_moves,
                    'avg_movement': total_movement / significant_moves,
                    'direction': 'up' if curr_spreads[list(curr_spreads.keys())[0]] > prev_spreads[list(prev_spreads.keys())[0]] else 'down'
                }

        return None

    def _extract_spreads(self, game: Dict) -> Dict[str, float]:
        """
        Extract spread lines from all bookmakers

        Args:
            game: Game data from API

        Returns:
            Dictionary mapping bookmaker name to spread line
        """
        spreads = {}

        for bookmaker in game.get('bookmakers', []):
            book_name = bookmaker.get('key', '')

            for market in bookmaker.get('markets', []):
                if market.get('key') == 'spreads':
                    outcomes = market.get('outcomes', [])
                    if len(outcomes) >= 2:
                        # Use home team spread as reference
                        for outcome in outcomes:
                            if outcome.get('name') == game.get('home_team'):
                                spreads[book_name] = outcome.get('point', 0)
                                break

        return spreads

    def calculate_consensus_line(self, game: Dict, market_type: str = 'spreads') -> Optional[float]:
        """
        Calculate consensus line across all bookmakers

        Args:
            game: Game data from API
            market_type: 'spreads' or 'totals'

        Returns:
            Average line across all books, or None if not available
        """
        lines = []

        for bookmaker in game.get('bookmakers', []):
            for market in bookmaker.get('markets', []):
                if market.get('key') == market_type:
                    outcomes = market.get('outcomes', [])

                    if market_type == 'spreads' and len(outcomes) >= 2:
                        # Get home team spread
                        for outcome in outcomes:
                            if outcome.get('name') == game.get('home_team'):
                                line = outcome.get('point')
                                if line is not None:
                                    lines.append(line)
                                break

                    elif market_type == 'totals' and len(outcomes) >= 1:
                        # Get Over line (total)
                        for outcome in outcomes:
                            if outcome.get('name') == 'Over':
                                line = outcome.get('point')
                                if line is not None:
                                    lines.append(line)
                                break

        if not lines:
            return None

        return sum(lines) / len(lines)

    def get_line_movement_report(self, game_id: str) -> Dict:
        """
        Generate comprehensive line movement report for a game

        Args:
            game_id: Game ID to analyze

        Returns:
            Dictionary with:
            - opening_line: First recorded line
            - current_line: Most recent line
            - total_movement: Points moved
            - steam_moves: List of detected steam moves
            - reverse_movement: Boolean if detected
        """
        snapshots = self.get_snapshots(game_id)

        if not snapshots:
            return {'error': 'No snapshots found for this game'}

        # Opening and current lines
        opening_game = snapshots[0]['game']
        current_game = snapshots[-1]['game']

        opening_spread = self.calculate_consensus_line(opening_game, 'spreads')
        current_spread = self.calculate_consensus_line(current_game, 'spreads')

        opening_total = self.calculate_consensus_line(opening_game, 'totals')
        current_total = self.calculate_consensus_line(current_game, 'totals')

        # Detect steam moves
        steam = self.detect_steam_move(snapshots)

        report = {
            'game_id': game_id,
            'opening_timestamp': snapshots[0]['timestamp'],
            'current_timestamp': snapshots[-1]['timestamp'],
            'spread': {
                'opening': opening_spread,
                'current': current_spread,
                'movement': current_spread - opening_spread if opening_spread and current_spread else None
            },
            'total': {
                'opening': opening_total,
                'current': current_total,
                'movement': current_total - opening_total if opening_total and current_total else None
            },
            'steam_moves': [steam] if steam else [],
            'snapshots_analyzed': len(snapshots)
        }

        return report


if __name__ == "__main__":
    """Test line movement tracker"""

    tracker = LineMovementTracker()

    print("Line Movement Tracker - Test")
    print("=" * 60)
    print("\nThis tool helps identify sharp money by tracking odds movements")
    print("\nUsage:")
    print("1. Save snapshots periodically (every 2-4 hours)")
    print("2. Analyze movements to detect sharp action")
    print("3. Look for reverse line movement and steam moves")
    print("\nExample workflow:")
    print("  - Monday morning: Save opening lines")
    print("  - Throughout week: Save snapshots 3-4 times per day")
    print("  - Sunday morning: Analyze movements for sharp action")