"""
NFL Betting Alert Engine
Analyzes collected data and generates actionable betting alerts
"""

import json
from typing import List, Dict, Any
from datetime import datetime

class NFLAlertEngine:
    def __init__(self, data_file: str):
        """
        Initialize alert engine with collected NFL data
        
        Args:
            data_file: Path to JSON file from collector
        """
        with open(data_file, 'r') as f:
            self.data = json.load(f)
        
        self.alerts = []
        
        # Alert type configurations
        self.alert_types = {
            'sharp_money': {'emoji': '💎', 'priority': 'HIGH', 'color': '#10b981'},
            'line_flip': {'emoji': '🔄', 'priority': 'HIGH', 'color': '#f59e0b'},
            'line_movement': {'emoji': '📈', 'priority': 'MEDIUM', 'color': '#3b82f6'},
            'value_over': {'emoji': '🔥', 'priority': 'HIGH', 'color': '#ef4444'},
            'value_under': {'emoji': '❄️', 'priority': 'HIGH', 'color': '#06b6d4'},
            'trap_game': {'emoji': '🪤', 'priority': 'MEDIUM', 'color': '#8b5cf6'},
            'mismatch': {'emoji': '⚔️', 'priority': 'MEDIUM', 'color': '#ec4899'},
            'public_fade': {'emoji': '🎯', 'priority': 'LOW', 'color': '#64748b'}
        }
    
    def analyze_all_games(self):
        """Run all alert checks on all games"""
        print("🔍 Analyzing games for betting opportunities...\n")
        
        for game in self.data.get('games', []):
            self._check_sharp_money(game)
            self._check_line_flip(game)
            self._check_line_movement(game)
            self._check_total_value(game)
            self._check_trap_game(game)
            self._check_mismatch(game)
            self._check_public_fade(game)
        
        # Sort alerts by priority
        priority_order = {'HIGH': 0, 'MEDIUM': 1, 'LOW': 2}
        self.alerts.sort(key=lambda x: priority_order.get(x['priority'], 3))
        
        return self.alerts
    
    def _check_sharp_money(self, game: Dict):
        """Alert 1: Smart money differential by 25%+"""
        betting = game.get('betting_percentages', {})
        
        bet_pct = self._parse_percentage(betting.get('spread_bet_pct', '0'))
        money_pct = self._parse_percentage(betting.get('spread_money_pct', '0'))
        
        if bet_pct == 0 or money_pct == 0:
            return
        
        differential = abs(money_pct - bet_pct)
        
        if differential >= 25:
            # Determine which side has sharp money
            if money_pct > bet_pct:
                sharp_side = "Higher money % side"
                reasoning = f"{money_pct}% of money on {bet_pct}% of bets = Sharp money backing this side"
            else:
                sharp_side = "Lower money % side (reverse line movement)"
                reasoning = f"{money_pct}% of money on {bet_pct}% of bets = Public trap potential"
            
            self.alerts.append({
                'type': 'sharp_money',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"💎 SHARP MONEY ALERT: {differential:.1f}% Differential",
                'description': f"{sharp_side} - Professional bettors strongly on one side",
                'reasoning': reasoning,
                'data': {
                    'bet_pct': bet_pct,
                    'money_pct': money_pct,
                    'differential': differential
                },
                'priority': 'HIGH',
                'game_id': game.get('id')
            })
    
    def _check_line_flip(self, game: Dict):
        """Alert 2: Lines that flipped team favorite"""
        # This requires historical line data
        # For now, we'll flag games close to pick'em as potential flips
        odds = game.get('odds', {})
        spreads = odds.get('spreads', {})
        
        for team, spread_data in spreads.items():
            line = spread_data.get('line', 0)
            
            # Flag if line is within 1 point of pick'em (likely to flip)
            if abs(line) <= 1.5 and line != 0:
                self.alerts.append({
                    'type': 'line_flip',
                    'game': f"{game['away_team']} @ {game['home_team']}",
                    'title': f"🔄 POTENTIAL LINE FLIP: {team}",
                    'description': f"Line at {line} - Very close to pick'em, watch for flip",
                    'reasoning': "Small spreads often flip as money comes in. Monitor for value.",
                    'data': {
                        'current_line': line,
                        'team': team
                    },
                    'priority': 'HIGH',
                    'game_id': game.get('id')
                })
                break  # Only alert once per game
    
    def _check_line_movement(self, game: Dict):
        """Alert 3: Lines that moved more than 4 points"""
        # This requires historical line tracking
        # For now, flag unusually large spreads as "moved from opener"
        odds = game.get('odds', {})
        spreads = odds.get('spreads', {})
        
        for team, spread_data in spreads.items():
            line = abs(spread_data.get('line', 0))
            
            # Large spreads (14+) suggest significant movement from opener
            if line >= 14:
                self.alerts.append({
                    'type': 'line_movement',
                    'game': f"{game['away_team']} @ {game['home_team']}",
                    'title': f"📈 LARGE SPREAD: {team} {spread_data.get('line')}",
                    'description': f"Unusually large line suggests significant early movement",
                    'reasoning': "Big spreads often indicate injury news or sharp action moved the line dramatically.",
                    'data': {
                        'current_line': spread_data.get('line')
                    },
                    'priority': 'MEDIUM',
                    'game_id': game.get('id')
                })
                break
    
    def _check_total_value(self, game: Dict):
        """Alerts 4 & 5: Over/Under value based on custom formula"""
        matchup = game.get('matchup_stats', {})
        odds = game.get('odds', {})
        totals = odds.get('totals', {})
        
        # Get the line
        over_line = totals.get('Over', {}).get('line')
        if not over_line:
            return
        
        # Extract stats from matchup data
        stats = self._extract_scoring_stats(matchup)
        if not stats:
            return
        
        # Calculate expected total using the formula
        # (home_off + away_off) * 0.6 + (home_def + away_def) * 0.4
        expected_total = (
            (stats['home_offense_ppg'] + stats['away_offense_ppg']) * 0.6 +
            (stats['home_defense_ppg'] + stats['away_defense_ppg']) * 0.4
        )
        
        difference = over_line - expected_total
        percent_diff = (difference / expected_total) * 100
        
        # Alert 4: Over is 20%+ less than expected (value on OVER)
        if percent_diff <= -20:
            self.alerts.append({
                'type': 'value_over',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"🔥 VALUE OVER: Line at {over_line}, Expected {expected_total:.1f}",
                'description': f"Over is {abs(percent_diff):.1f}% below expected total - STRONG OVER VALUE",
                'reasoning': f"Formula: ({stats['away_offense_ppg']}+{stats['home_offense_ppg']})*.6 + ({stats['away_defense_ppg']}+{stats['home_defense_ppg']})*.4 = {expected_total:.1f}",
                'data': {
                    'line': over_line,
                    'expected': expected_total,
                    'difference': difference,
                    'percent_diff': percent_diff
                },
                'priority': 'HIGH',
                'game_id': game.get('id')
            })
        
        # Alert 5: Under is 20%+ more than expected (value on UNDER)
        if percent_diff >= 20:
            self.alerts.append({
                'type': 'value_under',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"❄️ VALUE UNDER: Line at {over_line}, Expected {expected_total:.1f}",
                'description': f"Under is {percent_diff:.1f}% above expected total - STRONG UNDER VALUE",
                'reasoning': f"Formula: ({stats['away_offense_ppg']}+{stats['home_offense_ppg']})*.6 + ({stats['away_defense_ppg']}+{stats['home_defense_ppg']})*.4 = {expected_total:.1f}",
                'data': {
                    'line': over_line,
                    'expected': expected_total,
                    'difference': difference,
                    'percent_diff': percent_diff
                },
                'priority': 'HIGH',
                'game_id': game.get('id')
            })
    
    def _check_trap_game(self, game: Dict):
        """Identify potential trap games"""
        betting = game.get('betting_percentages', {})
        odds = game.get('odds', {})
        
        bet_pct = self._parse_percentage(betting.get('spread_bet_pct', '0'))
        money_pct = self._parse_percentage(betting.get('spread_money_pct', '0'))
        
        # Public heavy on one side, sharp money on other
        if bet_pct >= 70 and money_pct <= 45:
            self.alerts.append({
                'type': 'trap_game',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"🪤 TRAP GAME: Public vs Sharps",
                'description': f"{bet_pct}% of bets but only {money_pct}% of money",
                'reasoning': "Classic trap setup - public loading one side, sharps taking the other",
                'data': {
                    'bet_pct': bet_pct,
                    'money_pct': money_pct
                },
                'priority': 'MEDIUM',
                'game_id': game.get('id')
            })
    
    def _check_mismatch(self, game: Dict):
        """Identify offensive/defensive mismatches"""
        matchup = game.get('matchup_stats', {})
        stats = self._extract_scoring_stats(matchup)
        
        if not stats:
            return
        
        # Good offense vs bad defense
        away_advantage = stats['away_offense_ppg'] - stats['home_defense_ppg']
        home_advantage = stats['home_offense_ppg'] - stats['away_defense_ppg']
        
        if away_advantage >= 8:
            self.alerts.append({
                'type': 'mismatch',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"⚔️ OFFENSIVE MISMATCH: {game['away_team']}",
                'description': f"{game['away_team']} offense ({stats['away_offense_ppg']} ppg) vs {game['home_team']} defense ({stats['home_defense_ppg']} ppg allowed)",
                'reasoning': f"{away_advantage:.1f} point advantage - Strong offensive matchup",
                'data': {
                    'advantage': away_advantage,
                    'offense_ppg': stats['away_offense_ppg'],
                    'defense_ppg': stats['home_defense_ppg']
                },
                'priority': 'MEDIUM',
                'game_id': game.get('id')
            })
        
        if home_advantage >= 8:
            self.alerts.append({
                'type': 'mismatch',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"⚔️ OFFENSIVE MISMATCH: {game['home_team']}",
                'description': f"{game['home_team']} offense ({stats['home_offense_ppg']} ppg) vs {game['away_team']} defense ({stats['away_defense_ppg']} ppg allowed)",
                'reasoning': f"{home_advantage:.1f} point advantage - Strong offensive matchup",
                'data': {
                    'advantage': home_advantage,
                    'offense_ppg': stats['home_offense_ppg'],
                    'defense_ppg': stats['away_defense_ppg']
                },
                'priority': 'MEDIUM',
                'game_id': game.get('id')
            })
    
    def _check_public_fade(self, game: Dict):
        """Identify opportunities to fade the public"""
        betting = game.get('betting_percentages', {})
        
        bet_pct = self._parse_percentage(betting.get('spread_bet_pct', '0'))
        
        if bet_pct >= 75 or bet_pct <= 25:
            side = "favorite" if bet_pct >= 75 else "underdog"
            fade_side = "underdog" if bet_pct >= 75 else "favorite"
            
            self.alerts.append({
                'type': 'public_fade',
                'game': f"{game['away_team']} @ {game['home_team']}",
                'title': f"🎯 PUBLIC FADE: {bet_pct}% on {side}",
                'description': f"Extreme public betting on {side} - Consider {fade_side}",
                'reasoning': "Public tends to overvalue favorites and popular teams",
                'data': {
                    'bet_pct': bet_pct,
                    'fade_side': fade_side
                },
                'priority': 'LOW',
                'game_id': game.get('id')
            })
    
    def _extract_scoring_stats(self, matchup: Dict) -> Dict:
        """Extract PPG stats from matchup data"""
        stats = {
            'home_offense_ppg': 0,
            'away_offense_ppg': 0,
            'home_defense_ppg': 0,
            'away_defense_ppg': 0
        }
        
        offense_defense = matchup.get('offense_vs_defense', {})
        
        # Search through all tables for PPG data
        for table_name, table_data in offense_defense.items():
            for row in table_data:
                stat = row.get('stat', '').lower()
                
                if 'points per game' in stat or 'ppg' in stat:
                    # Extract numeric values
                    away_val = self._extract_number(row.get('away', '0'))
                    home_val = self._extract_number(row.get('home', '0'))
                    
                    if 'offense' in table_name.lower():
                        stats['away_offense_ppg'] = away_val
                        stats['home_offense_ppg'] = home_val
                    elif 'defense' in table_name.lower() or 'allowed' in stat:
                        stats['away_defense_ppg'] = away_val
                        stats['home_defense_ppg'] = home_val
        
        # Return None if no valid stats found
        if all(v == 0 for v in stats.values()):
            return None
        
        return stats
    
    def _parse_percentage(self, pct_str: str) -> float:
        """Convert percentage string to float"""
        try:
            return float(pct_str.replace('%', '').strip())
        except:
            return 0
    
    def _extract_number(self, text: str) -> float:
        """Extract first number from text"""
        import re
        match = re.search(r'(\d+\.?\d*)', str(text))
        return float(match.group(1)) if match else 0
    
    def print_alerts(self):
        """Print all alerts to console"""
        if not self.alerts:
            print("❌ No betting alerts found")
            return
        
        print(f"\n🚨 FOUND {len(self.alerts)} BETTING ALERTS 🚨\n")
        print("="*80)
        
        for i, alert in enumerate(self.alerts, 1):
            emoji = self.alert_types[alert['type']]['emoji']
            print(f"\n{i}. {emoji} {alert['title']}")
            print(f"   Game: {alert['game']}")
            print(f"   Priority: {alert['priority']}")
            print(f"   {alert['description']}")
            print(f"   Why: {alert['reasoning']}")
            print("-"*80)
    
    def export_alerts(self, filename: str = 'betting_alerts.json'):
        """Export alerts to JSON file"""
        output = {
            'generated_at': datetime.now().isoformat(),
            'total_alerts': len(self.alerts),
            'alerts': self.alerts
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"\n💾 Alerts exported to {filename}")
        return filename


# =============================================================================
# USAGE EXAMPLE
# =============================================================================

if __name__ == "__main__":
    # Load the data file from collector
    DATA_FILE = "nfl_week_7_data.json"
    
    try:
        # Initialize alert engine
        engine = NFLAlertEngine(DATA_FILE)
        
        # Run all alert checks
        alerts = engine.analyze_all_games()
        
        # Print results
        engine.print_alerts()
        
        # Export to file
        engine.export_alerts()
        
        print("\n" + "="*80)
        print(f"📊 Alert Summary:")
        print(f"   Total Alerts: {len(alerts)}")
        
        # Count by type
        by_type = {}
        for alert in alerts:
            alert_type = alert['type']
            by_type[alert_type] = by_type.get(alert_type, 0) + 1
        
        for alert_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            emoji = engine.alert_types[alert_type]['emoji']
            print(f"   {emoji} {alert_type}: {count}")
        
        print("="*80)
        
    except FileNotFoundError:
        print(f"❌ Error: Could not find {DATA_FILE}")
        print("   Run the data collector first!")
    except Exception as e:
        print(f"❌ Error: {e}")