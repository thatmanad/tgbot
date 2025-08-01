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

def run_both_bots():
    """Run both Telegram and Discord bots concurrently."""
    logger = setup_logging()

    logger.info("🚀 STARTING DUAL PLATFORM BOT (main_dual.py)")
    logger.info("🤖 This will run both Telegram and Discord bots")

    # Initialize database synchronously first
    try:
        import asyncio
        from database.connection import db_manager

        # Run database initialization
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(db_manager.init_database())
        loop.close()

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

    # Check which bots to run
    telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
    discord_token = os.getenv('DISCORD_BOT_TOKEN')

    if not telegram_token and not discord_token:
        logger.error("No bot tokens found! Please set TELEGRAM_BOT_TOKEN and/or DISCORD_BOT_TOKEN")
        sys.exit(1)

    # Run bots based on available tokens
    if telegram_token and discord_token:
        logger.info("Running both Telegram and Discord bots...")
        run_dual_bots(telegram_token, discord_token)
    elif telegram_token:
        logger.info("Running Telegram bot only...")
        run_telegram_only(telegram_token)
    elif discord_token:
        logger.info("Running Discord bot only...")
        run_discord_only(discord_token)

def run_telegram_only(token):
    """Run only the Telegram bot."""
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    from bot.handlers import (
        start_handler, register_handler, unregister_handler, confirm_unregister_handler,
        wager_handler, leaderboard_handler, help_handler, milestones_handler,
        milestone_info_handler, milestone_callback_handler, pending_requests_handler,
        approve_request_handler, deny_request_handler, list_users, stats,
        weekly_leaderboard, capture_leaderboard, error_handler
    )

    application = Application.builder().token(token).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("register", register_handler))
    application.add_handler(CommandHandler("unregister", unregister_handler))
    application.add_handler(CommandHandler("confirm_unregister", confirm_unregister_handler))
    application.add_handler(CommandHandler("wager", wager_handler))
    application.add_handler(CommandHandler("leaderboard", leaderboard_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("milestones", milestones_handler))
    application.add_handler(CommandHandler("milestone_info", milestone_info_handler))
    application.add_handler(CallbackQueryHandler(milestone_callback_handler))
    application.add_handler(CommandHandler("users", list_users))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("weekly_leaderboard", weekly_leaderboard))
    application.add_handler(CommandHandler("capture_leaderboard", capture_leaderboard))
    application.add_handler(CommandHandler("pending", pending_requests_handler))
    application.add_handler(CommandHandler("approve", approve_request_handler))
    application.add_handler(CommandHandler("deny", deny_request_handler))
    application.add_error_handler(error_handler)

    # Run the bot
    application.run_polling(allowed_updates=["message", "callback_query"])

def run_discord_only(token):
    """Run only the Discord bot."""
    from bot.discord_handlers import discord_bot
    discord_bot.run(token)

def run_dual_bots(telegram_token, discord_token):
    """Run both bots using threading."""
    import threading

    def run_telegram():
        run_telegram_only(telegram_token)

    def run_discord():
        run_discord_only(discord_token)

    # Start Telegram bot in a separate thread
    telegram_thread = threading.Thread(target=run_telegram, daemon=True)
    telegram_thread.start()

    # Run Discord bot in main thread
    run_discord_only(discord_token)

def main():
    """Main function to start both bots."""
    try:
        run_both_bots()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    except Exception as e:
        print(f"Bot crashed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
