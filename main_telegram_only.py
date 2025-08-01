#!/usr/bin/env python3
"""
Telegram-only bot for testing.
"""

import asyncio
import logging
import os
import sys
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Import Telegram handlers
from bot.handlers import (
    start_handler,
    register_handler,
    unregister_handler,
    confirm_unregister_handler,
    wager_handler,
    leaderboard_handler,
    help_handler,
    milestones_handler,
    milestone_info_handler,
    milestone_callback_handler,
    pending_requests_handler,
    approve_request_handler,
    deny_request_handler,
    list_users,
    stats,
    weekly_leaderboard,
    capture_leaderboard,
    error_handler
)

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
    """Main function to run Telegram bot only."""
    logger = setup_logging()
    
    logger.info("🤖 STARTING TELEGRAM-ONLY BOT")
    
    # Check for Telegram token
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not telegram_token:
        logger.error("❌ No TELEGRAM_BOT_TOKEN found!")
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

    # Create the Application
    logger.info("🚀 Creating Telegram application...")
    application = Application.builder().token(telegram_token).build()

    # Add command handlers
    logger.info("📋 Adding command handlers...")
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("register", register_handler))
    application.add_handler(CommandHandler("unregister", unregister_handler))
    application.add_handler(CommandHandler("confirm_unregister", confirm_unregister_handler))
    application.add_handler(CommandHandler("wager", wager_handler))
    application.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    application.add_handler(CommandHandler("help", help_handler))

    # Add milestone command handlers
    application.add_handler(CommandHandler("milestones", milestones_handler))
    application.add_handler(CommandHandler("milestone_info", milestone_info_handler))
    
    # Add callback query handler for milestone buttons
    application.add_handler(CallbackQueryHandler(milestone_callback_handler))

    # Add admin command handlers
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("weekly_leaderboard", weekly_leaderboard))
    application.add_handler(CommandHandler("capture_leaderboard", capture_leaderboard))
    application.add_handler(CommandHandler("pending", pending_requests_handler))
    application.add_handler(CommandHandler("approve", approve_request_handler))
    application.add_handler(CommandHandler("deny", deny_request_handler))

    # Add error handler
    application.add_error_handler(error_handler)

    # Run the bot
    logger.info("🚀 Starting Telegram bot...")
    try:
        # Initialize and start the application
        await application.initialize()
        await application.start()

        # Start polling
        await application.updater.start_polling(allowed_updates=["message", "callback_query"])

        logger.info("✅ Telegram bot started successfully and is running...")

        # Keep running until stopped
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Telegram bot stopped by user")

    except Exception as e:
        logger.error(f"❌ Telegram bot error: {e}")
        raise
    finally:
        try:
            await application.stop()
            await application.shutdown()
        except:
            pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        sys.exit(1)
