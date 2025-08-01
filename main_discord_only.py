#!/usr/bin/env python3
"""
Discord-only bot for separate deployment.
"""

import asyncio
import logging
import os
import sys

def setup_logging():
    """Set up logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level),
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

async def main():
    """Main function to run Discord bot only."""
    logger = setup_logging()
    
    logger.info("🤖 STARTING DISCORD-ONLY BOT")
    
    # Check for Discord token
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        logger.error("❌ No DISCORD_BOT_TOKEN found!")
        sys.exit(1)
    
    # Initialize database
    try:
        from database.connection import db_manager
        from railway_migrate import ensure_discord_support
        
        await db_manager.init_database()
        await ensure_discord_support()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        sys.exit(1)

    # Initialize milestone tracker
    try:
        from utils.milestone_tracker import MilestoneTracker
        milestone_tracker = MilestoneTracker()
        logger.info("✅ Milestone tracker initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize milestone tracker: {e}")

    # Initialize weekly scheduler
    try:
        from utils.weekly_leaderboard_scheduler import WeeklyLeaderboardScheduler
        scheduler = WeeklyLeaderboardScheduler()
        scheduler.start_scheduler()
        logger.info("✅ Weekly leaderboard scheduler initialized")
    except Exception as e:
        logger.error(f"❌ Failed to initialize weekly scheduler: {e}")

    # Import and run Discord bot
    logger.info("🚀 Starting Discord bot...")
    try:
        from bot.discord_handlers import discord_bot
        await discord_bot.start(discord_token)
    except Exception as e:
        logger.error(f"❌ Discord bot error: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Discord bot stopped by user")
    except Exception as e:
        print(f"Discord bot crashed: {e}")
        sys.exit(1)
