"""
Statistics calculation functions for betting analysis
"""

from typing import Dict, Optional


def calculate_expected_total(
    home_offense_ppg: float,
    away_offense_ppg: float,
    home_defense_ppg: float,
    away_defense_ppg: float
) -> float:
    """
    Calculate expected total score using weighted formula
    
    Formula: (home_off + away_off) × 0.6 + (home_def + away_def) × 0.4
    
    Args:
        home_offense_ppg: Home team's offensive points per game
        away_offense_ppg: Away team's offensive points per game
        home_defense_ppg: Home team's defensive points allowed per game
        away_defense_ppg: Away team's defensive points allowed per game
    
    Returns:
        Expected total score
    """
    offensive_component = (home_offense_ppg + away_offense_ppg) * 0.6
    defensive_component = (home_defense_ppg + away_defense_ppg) * 0.4
    
    return offensive_component + defensive_component


def calculate_sharp_differential(bet_percentage: float, money_percentage: float) -> float:
    """
    Calculate the differential between bet % and money %
    
    Args:
        bet_percentage: Percentage of bets on one side
        money_percentage: Percentage of money on one side
    
    Returns:
        Differential (positive means sharp money on this side)
    """
    return money_percentage - bet_percentage


def is_value_over(line: float, expected_total: float, threshold: float = 0.20) -> bool:
    """
    Check if there's value on the OVER
    
    Args:
        line: Current total line
        expected_total: Calculated expected total
        threshold: Percentage threshold (default 20%)
    
    Returns:
        True if line is 20%+ below expected
    """
    difference = line - expected_total
    percent_diff = (difference / expected_total)
    
    return percent_diff <= -threshold


def is_value_under(line: float, expected_total: float, threshold: float = 0.20) -> bool:
    """
    Check if there's value on the UNDER
    
    Args:
        line: Current total line
        expected_total: Calculated expected total
        threshold: Percentage threshold (default 20%)
    
    Returns:
        True if line is 20%+ above expected
    """
    difference = line - expected_total
    percent_diff = (difference / expected_total)
    
    return percent_diff >= threshold


def calculate_offensive_advantage(offense_ppg: float, opponent_defense_ppg: float) -> float:
    """
    Calculate offensive mismatch advantage
    
    Args:
        offense_ppg: Offensive points per game
        opponent_defense_ppg: Opponent's defensive points allowed per game
    
    Returns:
        Point advantage (positive means offensive advantage)
    """
    return offense_ppg - opponent_defense_ppg


def extract_percentage(text: str) -> float:
    """
    Extract percentage from text string
    
    Args:
        text: String containing percentage (e.g., "75%", "75.5", "75")
    
    Returns:
        Percentage as float
    """
    import re
    
    if not text:
        return 0.0
    
    # Remove % symbol and any other non-numeric characters except decimal point
    cleaned = re.sub(r'[^\d.]', '', str(text))
    
    try:
        return float(cleaned)
    except ValueError:
        return 0.0