#!/usr/bin/env python3
"""
Main automation script - Run this daily to collect data and generate alerts
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from collectors.nfl_data_collector import NFLDataCollector
from analyzers.alert_engine import NFLAlertEngine
from config.settings import (
    ODDS_API_KEY,
    DATA_DIR,
    SAVE_HISTORICAL,
    get_current_week
)


def main():
    """Main execution function"""
    
    print("=" * 80)
    print("🏈 NFL BETTING INTELLIGENCE - DAILY RUN")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check API key
    if not ODDS_API_KEY:
        print("❌ ERROR: ODDS_API_KEY not set in environment")
        print("   Please set it in .env file or as environment variable")
        sys.exit(1)
    
    # Detect current week
    current_week = get_current_week()
    print(f"📅 NFL Week: {current_week}")
    print()
    
    # Initialize collector
    print("STEP 1: Initializing data collector...")
    collector = NFLDataCollector(
        odds_api_key=ODDS_API_KEY,
        nfl_week=current_week
    )
    
    # Collect all data
    print("\nSTEP 2: Collecting data...")
    success = collector.collect_all_data(include_matchups=True)
    
    if not success:
        print("❌ Data collection failed")
        sys.exit(1)
    
    # Save data
    print("\nSTEP 3: Saving data...")
    data_file = collector.save_to_json(
        filename=f'{DATA_DIR}/weekly/week_{current_week}_data.json'
    )
    
    # Generate alerts
    print("\nSTEP 4: Generating betting alerts...")
    alert_engine = NFLAlertEngine(data_file)
    alerts = alert_engine.analyze_all_games()
    
    # Save alerts
    alerts_file = f'{DATA_DIR}/alerts/week_{current_week}_alerts.json'
    alert_engine.export_alerts(alerts_file)
    
    # Print summary
    print("\n" + "=" * 80)
    print("✅ DAILY RUN COMPLETE")
    print("=" * 80)
    print(f"📊 Data saved to: {data_file}")
    print(f"🚨 Alerts saved to: {alerts_file}")
    print(f"🎯 Total alerts: {len(alerts)}")
    
    # Print alert breakdown
    if alerts:
        print("\n📈 Alert Breakdown:")
        alert_types = {}
        for alert in alerts:
            alert_type = alert['type']
            alert_types[alert_type] = alert_types.get(alert_type, 0) + 1
        
        for alert_type, count in sorted(alert_types.items(), key=lambda x: x[1], reverse=True):
            print(f"   {alert_type}: {count}")
    
    print("\n" + "=" * 80)
    print(f"Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Cleanup old data if configured
    if SAVE_HISTORICAL:
        print("\n♻️  Historical data preserved")
    else:
        cleanup_old_data()
    
    # Close collector
    collector.close()


def cleanup_old_data():
    """Remove data older than 30 days"""
    print("\n🧹 Cleaning up old data...")
    
    from datetime import timedelta
    
    cutoff_date = datetime.now() - timedelta(days=30)
    
    for data_type in ['weekly', 'alerts']:
        data_path = Path(f'{DATA_DIR}/{data_type}')
        if not data_path.exists():
            continue
        
        for file in data_path.glob('*.json'):
            if file.stat().st_mtime < cutoff_date.timestamp():
                file.unlink()
                print(f"   Deleted: {file.name}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)