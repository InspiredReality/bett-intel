#!/usr/bin/env python3
"""
Convert NFL week data JSON to CSV format
Extracts key matchup stats and odds data into a flat CSV structure
"""

import json
import sys
import re
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Tuple


def parse_stat_value(value: str) -> Tuple[str, str]:
    """
    Parse a stat value like "17.1 (#28)" into value and rank

    Args:
        value: String like "17.1 (#28)"

    Returns:
        Tuple of (numeric_value, rank) e.g., ("17.1", "28")
    """
    if not value:
        return ('', '')

    # Extract number before parenthesis
    match = re.match(r'([\d.]+)\s*\(#(\d+)\)', value)
    if match:
        return (match.group(1), match.group(2))

    # If no match, return the value as-is and empty rank
    return (value.strip(), '')


def extract_table_data(table: List[Dict], stat_name: str, team: str = 'away') -> str:
    """
    Extract a specific stat value from a table for a specific team

    Args:
        table: List of stat dictionaries
        stat_name: Name of the stat to extract (e.g., "Points/Game")
        team: Which team's data to extract ('away' or 'home')

    Returns:
        The value (rank) string, or empty string if not found
    """
    for row in table:
        if row.get('stat') == stat_name:
            return row.get(team, '')
    return ''


def json_to_dataframe(json_file_path: str) -> pd.DataFrame:
    """
    Convert NFL week JSON data to pandas DataFrame

    Args:
        json_file_path: Path to the JSON file

    Returns:
        DataFrame with columns:
        - home_team
        - away_team
        - total_line (odds.totals.Over.line)
        - table1_* (matchup_stats.offense_vs_defense.Table 1 stats)
        - table2_* (matchup_stats.offense_vs_defense.Table 2 stats)
    """
    # Read JSON file
    with open(json_file_path, 'r') as f:
        data = json.load(f)

    # Extract data for each game
    rows = []

    for game in data.get('games', []):
        # Extract total line from odds
        odds = game.get('odds', {})
        totals = odds.get('totals', {})
        over = totals.get('Over', {})

        # Extract matchup stats
        matchup_stats = game.get('matchup_stats', {})
        offense_vs_defense = matchup_stats.get('offense_vs_defense', {})

        # Extract Table 1 and Table 2 stats
        table1 = offense_vs_defense.get('Table 1', [])
        table2 = offense_vs_defense.get('Table 2', [])

        # Build row with new column names
        row = {
            'away_team': game.get('away_team', ''),
            'home_team': game.get('home_team', ''),
            'total_line': over.get('line', ''),
            'away_off_ppg': extract_table_data(table1, 'Points/Game', 'away'),
            'home_def_ppg': extract_table_data(table1, 'Points/Game', 'home'),
            'away_off_ypg': extract_table_data(table1, 'Yards/Game', 'away'),
            'home_def_ypg': extract_table_data(table1, 'Yards/Game', 'home'),
            'home_off_ppg': extract_table_data(table2, 'Points/Game', 'away'),
            'away_def_ppg': extract_table_data(table2, 'Points/Game', 'home'),
            'home_off_ypg': extract_table_data(table2, 'Yards/Game', 'away'),
            'away_def_ypg': extract_table_data(table2, 'Yards/Game', 'home'),
            'away_tds_per_game': extract_table_data(table2, 'TDs/Game', 'away'),
            'home_tds_per_game': extract_table_data(table2, 'TDs/Game', 'home'),
        }

        rows.append(row)

    # Create DataFrame
    df = pd.DataFrame(rows)

    # Parse Points/Game columns into value and rank
    points_columns = [
        'away_off_ppg',
        'home_def_ppg',
        'home_off_ppg',
        'away_def_ppg'
    ]

    for col in points_columns:
        if col in df.columns:
            # Parse each value into (value, rank)
            parsed = df[col].apply(parse_stat_value)
            # Create new columns
            df[col] = parsed.apply(lambda x: x[0])  # Numeric value
            df[f'{col}_rank'] = parsed.apply(lambda x: x[1])  # Rank

    # Convert PPG columns to numeric for calculations
    for col in points_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Calculate estimated points
    df['away_pts_est'] = (df['away_off_ppg'] * 0.55) + (df['home_def_ppg'] * 0.45)
    df['home_pts_est'] = (df['home_off_ppg'] * 0.55) + (df['away_def_ppg'] * 0.45)

    # Round to 1 decimal place
    df['away_pts_est'] = df['away_pts_est'].round(1)
    df['home_pts_est'] = df['home_pts_est'].round(1)

    # Calculate total line estimate and away spread estimate
    df['total_line_est'] = (df['away_pts_est'] + df['home_pts_est']).round(1)
    df['away_spread_est'] = (df['home_pts_est'] - df['away_pts_est']).round(1)

    # Convert total_line to numeric for calculation
    df['total_line'] = pd.to_numeric(df['total_line'], errors='coerce')

    # Calculate difference between estimated and actual total line
    df['total_diff'] = (df['total_line_est'] - df['total_line']).round(1)

    # Sort by absolute value of total_diff (largest discrepancies first)
    df['abs_total_diff'] = df['total_diff'].abs()
    df = df.sort_values('abs_total_diff', ascending=False)
    df = df.drop('abs_total_diff', axis=1)  # Remove temporary sorting column

    # Define exact column order
    new_order = [
        'away_team',
        'home_team',
        'total_line',
        'total_line_est',
        'total_diff',
        'away_spread_est',
        'away_pts_est',
        'home_pts_est',
        'away_off_ppg',
        'away_off_ppg_rank',
        'home_def_ppg',
        'home_def_ppg_rank',
        'home_off_ppg',
        'home_off_ppg_rank',
        'away_def_ppg',
        'away_def_ppg_rank',
        'away_off_ypg',
        'home_def_ypg',
        'home_off_ypg',
        'away_def_ypg',
        'away_tds_per_game',
        'home_tds_per_game',
    ]

    # Filter to only include columns that exist in the dataframe
    new_order = [col for col in new_order if col in df.columns]

    # Reorder DataFrame
    df = df[new_order]

    return df


def main():
    """Main execution function"""
    if len(sys.argv) < 2:
        print("Usage: python json_to_csv.py <json_file_path>")
        print("Example: python json_to_csv.py data/weekly/week_9_data.json")
        sys.exit(1)

    json_file_path = sys.argv[1]

    # Verify file exists
    if not Path(json_file_path).exists():
        print(f"Error: File not found: {json_file_path}")
        sys.exit(1)

    print(f"Reading JSON file: {json_file_path}")

    # Convert to DataFrame
    df = json_to_dataframe(json_file_path)

    # Generate output filename
    input_file = Path(json_file_path)

    # Use absolute path - same directory as input file
    output_file = input_file.parent.parent / 'data' / f"{input_file.stem}.csv"

    # Create data directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"📁 Output path: {output_file.absolute()}")

    # Save to CSV
    try:
        df.to_csv(output_file, index=False)
        print(f"✅ Converted {len(df)} games to CSV")
        print(f"📊 Output saved to: {output_file}")
    except Exception as e:
        print(f"❌ Error saving CSV: {e}")
        raise

    print(f"\nDataFrame shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")


if __name__ == "__main__":
    main()