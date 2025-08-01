#!/usr/bin/env python3
"""
Unified main file to run both Telegram and Discord bots.
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

# Import Discord bot
from bot.discord_handlers import discord_bot

def setup_logging():
    """Set up logging configuration."""
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'bot.log')
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, log_level),
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    return logging.getLogger(__name__)

async def setup_telegram_bot():
    """Set up and configure the Telegram bot."""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        return None
    
    # Create the Application
    application = Application.builder().token(bot_token).build()

    # Add command handlers
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

    return application

async def setup_discord_bot():
    """Set up and configure the Discord bot."""
    discord_token = os.getenv('DISCORD_BOT_TOKEN')
    if not discord_token:
        return None

    try:
        # Test if the token is valid format
        if not discord_token.startswith(('Bot ', 'MTk', 'MTA', 'MTI', 'MTE', 'MTM', 'MTQ', 'MTU', 'MTY', 'MTc', 'MTg')):
            logger.warning("Discord token format looks incorrect")

        return discord_bot, discord_token
    except Exception as e:
        logger.error(f"Error setting up Discord bot: {e}")
        return None

async def run_both_bots():
    """Run both Telegram and Discord bots concurrently."""
    logger = setup_logging()

    logger.info("🚀 STARTING DUAL PLATFORM BOT (main_dual.py)")
    logger.info("🤖 This will run both Telegram and Discord bots")
    
    # Initialize database
    try:
        from database.connection import db_manager
        await db_manager.init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        sys.exit(1)

    # Initialize milestone tracker
    try:
        from utils.milestone_tracker import MilestoneTracker
        milestone_tracker = MilestoneTracker()
        logger.info("Milestone tracker initialized")
    except Exception as e:
        logger.error(f"Failed to initialize milestone tracker: {e}")

    # Initialize weekly scheduler
    try:
        from utils.weekly_leaderboard_scheduler import WeeklyLeaderboardScheduler
        scheduler = WeeklyLeaderboardScheduler()
        scheduler.start_scheduler()
        logger.info("Weekly leaderboard scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize weekly scheduler: {e}")

    # Set up bots
    telegram_app = await setup_telegram_bot()
    discord_setup = await setup_discord_bot()
    
    tasks = []
    
    # Start Telegram bot if token is available
    if telegram_app:
        logger.info("Starting Telegram bot...")

        async def run_telegram():
            try:
                await telegram_app.run_polling(allowed_updates=["message", "callback_query"])
            except Exception as e:
                logger.error(f"Telegram bot failed to start: {e}")

        tasks.append(run_telegram())
    else:
        logger.warning("No Telegram bot token found, skipping Telegram bot")

    # Start Discord bot if token is available
    if discord_setup:
        discord_bot_instance, discord_token = discord_setup
        logger.info("Starting Discord bot...")

        async def run_discord():
            try:
                await discord_bot_instance.start(discord_token)
            except Exception as e:
                logger.error(f"Discord bot failed to start: {e}")

        tasks.append(run_discord())
    else:
        logger.warning("No Discord bot token found, skipping Discord bot")
    
    if not tasks:
        logger.error("No bot tokens found! Please set TELEGRAM_BOT_TOKEN and/or DISCORD_BOT_TOKEN")
        sys.exit(1)
    
    # Run both bots concurrently
    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        logger.info("Shutting down bots...")
    except Exception as e:
        logger.error(f"Error running bots: {e}")

def main():
    """Main function to start both bots."""
    # Run both bots using asyncio.run which handles the event loop properly
    try:
        asyncio.run(run_both_bots())
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
