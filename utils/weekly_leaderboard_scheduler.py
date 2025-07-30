#!/usr/bin/env python3
"""
Weekly leaderboard scheduler for capturing top 10 users every Sunday at 7pm CST.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from api.goated_api import GoatedAPI
from database.connection import store_weekly_leaderboard_snapshot

logger = logging.getLogger(__name__)

class WeeklyLeaderboardScheduler:
    """Scheduler for capturing weekly leaderboard snapshots."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.cst_timezone = pytz.timezone('America/Chicago')
        
    async def capture_weekly_leaderboard(self):
        """Capture the top 10 leaderboard players and store them."""
        try:
            logger.info("Starting weekly leaderboard capture...")
            
            # Get current date in CST for snapshot naming
            now_cst = datetime.now(self.cst_timezone)
            snapshot_date = now_cst.strftime('%Y-%m-%d')
            
            # Fetch top 10 players from API
            api = GoatedAPI()
            try:
                top_players = await api.get_top_leaderboard_players(limit=10)
                
                if not top_players:
                    logger.warning("No players found for weekly leaderboard capture")
                    return False
                
                # Store the snapshot in database
                success = await store_weekly_leaderboard_snapshot(snapshot_date, top_players)
                
                if success:
                    logger.info(f"Successfully captured weekly leaderboard snapshot for {snapshot_date} with {len(top_players)} players")
                    
                    # Log the top 3 for verification
                    for i, player in enumerate(top_players[:3], 1):
                        logger.info(f"  #{i}: {player.get('username', 'Unknown')} - {player.get('last_7_days_wager', 0):,.2f}")
                    
                    return True
                else:
                    logger.error(f"Failed to store weekly leaderboard snapshot for {snapshot_date}")
                    return False
                    
            finally:
                await api.close()
                
        except Exception as e:
            logger.error(f"Error during weekly leaderboard capture: {e}")
            return False
    
    async def manual_capture(self, snapshot_date: Optional[str] = None) -> bool:
        """Manually trigger a leaderboard capture (for testing or missed captures)."""
        try:
            if not snapshot_date:
                now_cst = datetime.now(self.cst_timezone)
                snapshot_date = now_cst.strftime('%Y-%m-%d')
            
            logger.info(f"Manual leaderboard capture for {snapshot_date}")
            
            api = GoatedAPI()
            try:
                top_players = await api.get_top_leaderboard_players(limit=10)
                
                if not top_players:
                    logger.warning("No players found for manual leaderboard capture")
                    return False
                
                success = await store_weekly_leaderboard_snapshot(snapshot_date, top_players)
                
                if success:
                    logger.info(f"Successfully captured manual leaderboard snapshot for {snapshot_date}")
                    return True
                else:
                    logger.error(f"Failed to store manual leaderboard snapshot for {snapshot_date}")
                    return False
                    
            finally:
                await api.close()
                
        except Exception as e:
            logger.error(f"Error during manual leaderboard capture: {e}")
            return False
    
    def start_scheduler(self):
        """Start the weekly leaderboard capture scheduler."""
        try:
            # Schedule for every Sunday at 7:00 PM CST
            trigger = CronTrigger(
                day_of_week='sun',  # Sunday
                hour=19,           # 7 PM
                minute=0,          # :00
                timezone=self.cst_timezone
            )
            
            self.scheduler.add_job(
                self.capture_weekly_leaderboard,
                trigger=trigger,
                id='weekly_leaderboard_capture',
                name='Weekly Leaderboard Capture',
                replace_existing=True
            )
            
            self.scheduler.start()
            
            # Calculate next run time for logging
            next_run = self.scheduler.get_job('weekly_leaderboard_capture').next_run_time
            logger.info(f"Weekly leaderboard scheduler started. Next capture: {next_run}")
            
        except Exception as e:
            logger.error(f"Error starting weekly leaderboard scheduler: {e}")
    
    def stop_scheduler(self):
        """Stop the scheduler."""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
                logger.info("Weekly leaderboard scheduler stopped")
        except Exception as e:
            logger.error(f"Error stopping weekly leaderboard scheduler: {e}")
    
    def get_next_capture_time(self) -> Optional[datetime]:
        """Get the next scheduled capture time."""
        try:
            job = self.scheduler.get_job('weekly_leaderboard_capture')
            if job:
                return job.next_run_time
            return None
        except Exception as e:
            logger.error(f"Error getting next capture time: {e}")
            return None

# Global scheduler instance
weekly_scheduler = WeeklyLeaderboardScheduler()

async def test_capture():
    """Test function for manual leaderboard capture."""
    scheduler = WeeklyLeaderboardScheduler()
    success = await scheduler.manual_capture()
    print(f"Manual capture {'successful' if success else 'failed'}")

if __name__ == "__main__":
    # Test the manual capture
    asyncio.run(test_capture())
