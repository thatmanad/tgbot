#!/usr/bin/env python3
"""
Goated Wager Tracker Bot
A Telegram bot for tracking goated.com affiliate wagers and leaderboard positions.
"""

import logging
import os
import sys
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# Load environment variables
load_dotenv()

# Import bot modules
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
from config.settings import get_settings

def setup_logging():
    """Set up logging configuration."""
    settings = get_settings()
    
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=getattr(logging, settings.LOG_LEVEL),
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set up logger for this module
    logger = logging.getLogger(__name__)
    return logger

def main():
    """Main function to start the bot."""
    logger = setup_logging()
    settings = get_settings()

    if not settings.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not found in environment variables")
        sys.exit(1)

    logger.info("Starting Goated Wager Tracker Bot...")

    # Create the Application
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

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
    from telegram.ext import CallbackQueryHandler
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

    # Initialize milestone tracker with bot instance
    try:
        from utils.milestone_tracker import set_milestone_bot
        set_milestone_bot(application.bot)
        logger.info("Milestone tracker initialized")
    except Exception as e:
        logger.error(f"Failed to initialize milestone tracker: {e}")

    # Initialize weekly leaderboard scheduler
    try:
        from utils.weekly_leaderboard_scheduler import weekly_scheduler
        weekly_scheduler.start_scheduler()
        logger.info("Weekly leaderboard scheduler initialized")
    except Exception as e:
        logger.error(f"Failed to initialize weekly leaderboard scheduler: {e}")

    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
