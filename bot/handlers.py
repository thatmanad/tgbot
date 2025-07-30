"""
Telegram bot command handlers for the Goated Wager Tracker Bot.
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from api.goated_api import GoatedAPI
from database.connection import (
    get_user, create_user, update_user,
    get_cached_wager_data, cache_wager_data,
    get_cached_leaderboard_data, cache_leaderboard_data,
    log_command_usage, get_all_active_users, get_user_count,
    get_weekly_leaderboard_snapshots, get_weekly_leaderboard_snapshot,
    get_pending_milestone_requests, update_milestone_request_status,
    unregister_user, get_user_data_summary
)
from utils.milestone_tracker import milestone_tracker
from bot.utils import format_wager_amount, format_leaderboard_position

logger = logging.getLogger(__name__)

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    logger.info(f"User {user.id} ({user.username}) started the bot")
    
    welcome_message = f"""
🎰 **Welcome to Goated Wager Tracker Bot!** 🎰

Hello {user.first_name}! I'm here to help you track your goated.com wager progress and performance.

**What I can do:**
• Track your daily, weekly, monthly, and all-time wagers
• Show your leaderboard position within your network
• Provide quick access to your gaming stats

**Getting Started:**
1. Use `/register YOUR_USERNAME` to link your goated.com account
2. Use `/wager` to check your current wager stats
3. Use `/leaderboard` to see your ranking

Type `/help` for a complete list of commands.

Let's get started! 🚀
    """
    
    await update.message.reply_text(
        welcome_message,
        parse_mode=ParseMode.MARKDOWN
    )

async def register_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /register command."""
    user = update.effective_user
    logger.info(f"User {user.id} attempting to register")
    

    existing_user = await get_user(user.id)
    if existing_user:
        await update.message.reply_text(
            "✅ You're already registered! Use `/wager` to check your stats or `/help` for more commands.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    registration_message = """
🔐 **Registration Process**

To register your goated.com account, please provide your username.

**Registration Format:**
`/register YOUR_USERNAME`

**Example:**
`/register Thatmanadam`

Once registered, you'll be able to track your wagers and leaderboard position!

**Note:** Your username must match exactly as it appears on goated.com
    """

    if context.args:
        username = context.args[0]

        
        api = GoatedAPI()
        is_valid = await api.validate_username(username)

        if is_valid:
            
            await create_user(user.id, user.username, username)
            await update.message.reply_text(
                f"✅ **Registration Successful!**\n\n"
                f"Your username `{username}` has been registered.\n"
                f"You can now use `/wager` and `/leaderboard` commands.",
                parse_mode=ParseMode.MARKDOWN
            )
            logger.info(f"User {user.id} registered with username {username}")
        else:
            await update.message.reply_text(
                "❌ **Username Not Found**\n\n"
                "The provided username could not be found on goated.com. Please check your spelling and try again.\n\n"
                "Make sure to use your exact username as it appears on the site.",
                parse_mode=ParseMode.MARKDOWN
            )

        await api.close()
    else:
        await update.message.reply_text(
            registration_message,
            parse_mode=ParseMode.MARKDOWN
        )

async def wager_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /wager command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested wager information")

   
    await log_command_usage(user.id, "wager")

    
    user_data = await get_user(user.id)
    if not user_data:
        await update.message.reply_text(
            "❌ **Not Registered**\n\n"
            "Please register first using `/register` to track your wagers.",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_command_usage(user.id, "wager", False, "User not registered")
        return

    try:
        username = user_data['goated_username']

        
        wager_data = await get_cached_wager_data(username)

        if not wager_data:
            
            api = GoatedAPI()
            wager_data = await api.get_player_wager_stats(username)

            if wager_data:
                
                await cache_wager_data(username, wager_data)
            await api.close()

        if wager_data:
            monthly_wager = wager_data.get('monthly_wager', 0)
            total_wager = wager_data.get('total_wager', 0)

            # Check for milestone achievements based on monthly wager
            new_achievements = await milestone_tracker.check_and_notify_milestones(username, monthly_wager)

            message = f"""
📊 **Your Wager Statistics**

**Today:** {format_wager_amount(wager_data.get('daily_wager', 0))}
**Last 7 Days:** {format_wager_amount(wager_data.get('last_7_days_wager', 0))}
**This Week:** {format_wager_amount(wager_data.get('weekly_wager', 0))}
**This Month:** {format_wager_amount(wager_data.get('monthly_wager', 0))}
**All-Time:** {format_wager_amount(total_wager)}

**Username:** {wager_data.get('username', username)}
"""

            # Add milestone achievement notification if any
            if new_achievements:
                message += "\n🎉 **NEW MILESTONE ACHIEVED!** 🎉\n"
                for achievement in new_achievements:
                    milestone_amount = achievement['milestone_amount']
                    bonus_amount = achievement['bonus_amount']
                    message += f"🔥 {format_wager_amount(milestone_amount)} - ${bonus_amount:.0f} bonus!\n"
                message += "\n"

            message += f"\n*Last updated: {wager_data.get('last_updated', 'Unknown')}*\n"
            message += "_Use /milestones to see your progress_"

            await update_user(user.id, last_wager_check=datetime.now().isoformat())
        else:
            message = "❌ **Unable to fetch wager data**\n\nPlease try again later or contact support."
            await log_command_usage(user.id, "wager", False, "API returned no data")

    except Exception as e:
        logger.error(f"Error fetching wager data for user {user.id}: {e}")
        message = "❌ **Error fetching data**\n\nThere was an issue retrieving your wager information. Please try again later."
        await log_command_usage(user.id, "wager", False, str(e))

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def leaderboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /leaderboard command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested leaderboard information")
    
    
    user_data = await get_user(user.id)
    if not user_data:
        await update.message.reply_text(
            "❌ **Not Registered**\n\n"
            "Please register first using `/register` to check your leaderboard position.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        username = user_data['goated_username']

        
        leaderboard_data = await get_cached_leaderboard_data(username)

        if not leaderboard_data:
            
            api = GoatedAPI()
            leaderboard_data = await api.get_player_leaderboard_position(username)

            if leaderboard_data:
               
                await cache_leaderboard_data(username, leaderboard_data)
            await api.close()

        if leaderboard_data:
            message = f"""
🏆 **Your Leaderboard Position**

**Username:** {leaderboard_data.get('username', username)}

**Your Rankings:**
• Daily: {format_leaderboard_position(leaderboard_data.get('daily_rank', 'N/A'))}
• Last 7 Days: {format_leaderboard_position(leaderboard_data.get('last_7_days_rank', 'N/A'))}
• Weekly: {format_leaderboard_position(leaderboard_data.get('weekly_rank', 'N/A'))}
• Monthly: {format_leaderboard_position(leaderboard_data.get('monthly_rank', 'N/A'))}
• All-Time: {format_leaderboard_position(leaderboard_data.get('all_time_rank', 'N/A'))}

**Your Wagers:**
• Today: {format_wager_amount(leaderboard_data.get('player_daily', 0))}
• Last 7 Days: {format_wager_amount(leaderboard_data.get('player_last_7_days', 0))}
• This Week: {format_wager_amount(leaderboard_data.get('player_weekly', 0))}
• This Month: {format_wager_amount(leaderboard_data.get('player_monthly', 0))}
• All-Time: {format_wager_amount(leaderboard_data.get('player_all_time', 0))}

*Last updated: {leaderboard_data.get('last_updated', 'Unknown')}*
            """

            
            await update_user(user.id, last_leaderboard_check=datetime.now().isoformat())
        else:
            message = "❌ **Unable to fetch leaderboard data**\n\nPlease try again later or contact support."
            await log_command_usage(user.id, "leaderboard", False, "API returned no data")

    except Exception as e:
        logger.error(f"Error fetching leaderboard data for user {user.id}: {e}")
        message = "❌ **Error fetching data**\n\nThere was an issue retrieving your leaderboard information. Please try again later."
        await log_command_usage(user.id, "leaderboard", False, str(e))
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    user = update.effective_user

    # Check if user is admin
    ADMIN_USER_IDS = [5612012431 , 5966207178 ]   # Add your Telegram user ID here
    is_admin = user.id in ADMIN_USER_IDS

    help_message = """
🤖 **Goated Wager Tracker Bot - Help**

**Available Commands:**

🏠 `/start` - Welcome message and bot introduction
🔐 `/register USERNAME` - Register your goated.com account
📊 `/wager` - Check your wager statistics
🏆 `/leaderboard` - Check your leaderboard position
🎯 `/milestones` - View your milestone achievements
🔥 `/milestone_info` - See available milestone rewards
🚪 `/unregister` - Remove your account from the bot
❓ `/help` - Show this help message
"""

    if is_admin:
        help_message += """
**Admin Commands:**

👥 `/users` - List all registered users
📊 `/stats` - Show bot usage statistics
🏆 `/weekly_leaderboard` - View weekly leaderboard snapshots
📸 `/capture_leaderboard` - Manually capture current leaderboard
📋 `/pending` - View pending milestone requests
✅ `/approve <ID>` - Approve milestone request
❌ `/deny <ID> [reason]` - Deny milestone request
"""

    help_message += """
**How to Use:**

1. **First Time Setup:**
   - Use `/register YOUR_USERNAME` to link your account
   - Example: `/register CURRYPUZZY`

2. **Check Your Stats:**
   - Use `/wager` for daily/weekly/monthly wager amounts
   - Use `/leaderboard` for your current ranking

3. **Need Help?**
   - Make sure your username matches exactly as on goated.com
   - Contact support if you have issues

**Tips:**
• Data is updated in real-time from goated.com
• Use commands frequently to track your progress
• Your username is case-sensitive
"""

    if is_admin:
        help_message += """
**Admin Features:**
• Weekly leaderboard snapshots captured every Sunday at 7pm CST
• View historical top 10 player data
• Manual capture for testing or missed snapshots
"""

    help_message += """
Happy gaming! 🎰
    """

    await update.message.reply_text(help_message, parse_mode=ParseMode.MARKDOWN)

async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all registered users (admin command)."""
    user = update.effective_user
    logger.info(f"User {user.id} requested user list")

    ADMIN_USER_IDS = [5612012431 , 5966207178]  

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
      
        users = await get_all_active_users()
        user_count = await get_user_count()

        if not users:
            message = "📋 **Registered Users**\n\nNo users are currently registered."
        else:
            
            max_users_per_message = 20

            if len(users) <= max_users_per_message:
             
                user_list = []
                for i, user_data in enumerate(users, 1):
                    telegram_username = user_data.get('telegram_username', 'N/A')
                    goated_username = user_data.get('goated_username', 'N/A')
                    created_at = user_data.get('created_at', 'Unknown')

                    
                    try:
                        if created_at != 'Unknown':
                            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            created_str = created_date.strftime('%Y-%m-%d')
                        else:
                            created_str = 'Unknown'
                    except:
                        created_str = 'Unknown'

                    # Escape special characters in usernames for Markdown
                    safe_goated_username = goated_username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                    safe_telegram_username = telegram_username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')

                    user_list.append(f"{i}. **{safe_goated_username}** (@{safe_telegram_username}) - {created_str}")

                message = f"""📋 **Registered Users** ({user_count} total)

{chr(10).join(user_list)}

*Use /stats for detailed statistics*"""
            else:
                
                message = f"""📋 **Registered Users Summary**

**Total Users:** {user_count}
**Active Users:** {len(users)}

**Recent Registrations:**"""

                
                recent_users = sorted(users, key=lambda x: x.get('created_at', ''), reverse=True)[:10]
                for i, user_data in enumerate(recent_users, 1):
                    goated_username = user_data.get('goated_username', 'N/A')
                    telegram_username = user_data.get('telegram_username', 'N/A')

                    # Escape special characters for Markdown
                    safe_goated_username = goated_username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')
                    safe_telegram_username = telegram_username.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)')

                    message += f"\n{i}. **{safe_goated_username}** (@{safe_telegram_username})"

                if len(users) > 10:
                    message += f"\n\n*... and {len(users) - 10} more users*"

                message += "\n\n*Use the management script for full user list*"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "list_users", True)

    except Exception as e:
        logger.error(f"Error listing users for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue retrieving the user list. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "list_users", False, str(e))

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics (admin command)."""
    user = update.effective_user
    logger.info(f"User {user.id} requested bot statistics")

   
    ADMIN_USER_IDS = [5612012431 , 5966207178]  # Add your Telegram user ID here

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        
        users = await get_all_active_users()
        user_count = len(users)

        
        from datetime import timedelta
        today = datetime.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)

        recent_week = 0
        recent_month = 0

        for user_data in users:
            created_at = user_data.get('created_at', '')
            try:
                if created_at:
                    created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00')).date()
                    if created_date >= week_ago:
                        recent_week += 1
                    if created_date >= month_ago:
                        recent_month += 1
            except:
                continue

        
        recent_wager_checks = sum(1 for u in users if u.get('last_wager_check'))
        recent_leaderboard_checks = sum(1 for u in users if u.get('last_leaderboard_check'))

        message = f"""📊 **Bot Statistics**

**👥 Users:**
• Total Registered: {user_count}
• New This Week: {recent_week}
• New This Month: {recent_month}

**📈 Activity:**
• Users with Wager Checks: {recent_wager_checks}
• Users with Leaderboard Checks: {recent_leaderboard_checks}

**🎯 Features:**
• Rolling 7-Day Tracking: ✅ Active
• Smart Caching: ✅ Active
• Daily Wager Recording: ✅ Active

*Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}*"""

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "stats", True)

    except Exception as e:
        logger.error(f"Error getting statistics for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue retrieving statistics. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "stats", False, str(e))

async def weekly_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show weekly leaderboard snapshots (admin command)."""
    user = update.effective_user
    logger.info(f"User {user.id} requested weekly leaderboard snapshots")

    # Admin check
    ADMIN_USER_IDS = [5612012431]  # Add your Telegram user ID here

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        # Check if a specific date was requested
        args = context.args if context.args else []

        if args and len(args) > 0:
            # Show specific snapshot
            snapshot_date = args[0]
            snapshot = await get_weekly_leaderboard_snapshot(snapshot_date)

            if not snapshot:
                message = f"❌ **No Data Found**\n\nNo weekly leaderboard snapshot found for {snapshot_date}."
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                return

            # Format the specific snapshot
            message = f"🏆 **Weekly Leaderboard Snapshot**\n"
            message += f"📅 **Date:** {snapshot['snapshot_date']}\n"
            message += f"⏰ **Captured:** {snapshot['captured_at']}\n\n"

            for player in snapshot['players']:
                rank = player['rank']
                username = player['username']
                weekly_wager = player.get('last_7_days_wager', player.get('weekly_wager', 0))
                affiliate = player.get('affiliate_id', 'Unknown')

                message += f"**#{rank}.** {username} ({affiliate})\n"
                message += f"   💰 7-Day: {format_wager_amount(weekly_wager)}\n\n"

        else:
            # Show list of available snapshots
            snapshots = await get_weekly_leaderboard_snapshots(limit=10)

            if not snapshots:
                message = "❌ **No Data Found**\n\nNo weekly leaderboard snapshots available yet."
                await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
                return

            message = "📊 **Weekly Leaderboard Snapshots**\n\n"
            message += "Available snapshots (use `/weekly_leaderboard YYYY-MM-DD` for details):\n\n"

            for snapshot in snapshots:
                date = snapshot['snapshot_date']
                captured = snapshot['captured_at']
                player_count = len(snapshot['players'])

                # Get top player for preview
                if snapshot['players']:
                    top_player = snapshot['players'][0]
                    top_username = top_player['username']
                    top_wager = top_player.get('last_7_days_wager', top_player.get('weekly_wager', 0))

                    message += f"📅 **{date}**\n"
                    message += f"   👑 #{1}: {top_username} - {format_wager_amount(top_wager)}\n"
                    message += f"   📊 {player_count} players captured\n"
                    message += f"   ⏰ {captured}\n\n"

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "weekly_leaderboard", True)

    except Exception as e:
        logger.error(f"Error getting weekly leaderboard for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue retrieving weekly leaderboard data. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "weekly_leaderboard", False, str(e))

async def capture_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manually trigger weekly leaderboard capture (admin command)."""
    user = update.effective_user
    logger.info(f"User {user.id} requested manual leaderboard capture")

    # Admin check
    ADMIN_USER_IDS = [5612012431]  # Add your Telegram user ID here

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        # Import here to avoid circular imports
        from utils.weekly_leaderboard_scheduler import WeeklyLeaderboardScheduler

        scheduler = WeeklyLeaderboardScheduler()

        # Check if a specific date was requested
        args = context.args if context.args else []
        snapshot_date = args[0] if args and len(args) > 0 else None

        await update.message.reply_text(
            "🔄 **Capturing Leaderboard...**\n\nThis may take a few moments...",
            parse_mode=ParseMode.MARKDOWN
        )

        success = await scheduler.manual_capture(snapshot_date)

        if success:
            date_str = snapshot_date or datetime.now().strftime('%Y-%m-%d')
            message = f"✅ **Capture Successful**\n\nWeekly leaderboard snapshot captured for {date_str}."
        else:
            message = "❌ **Capture Failed**\n\nThere was an issue capturing the leaderboard snapshot."

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "capture_leaderboard", success)

    except Exception as e:
        logger.error(f"Error capturing leaderboard for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue capturing the leaderboard. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "capture_leaderboard", False, str(e))

async def milestones_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /milestones command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested milestone information")

    # Check if user is registered
    user_data = await get_user(telegram_id=user.id)
    if not user_data:
        message = """
❌ **Not Registered**

You need to register first to view your milestones.

Use `/register YOUR_USERNAME` to get started!
        """
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "milestones", False, "User not registered")
        return

    try:
        username = user_data['goated_username']

        # Get current wager data to show progress
        wager_data = await get_cached_wager_data(username)

        if not wager_data:
            # Fetch fresh data if not cached
            api = GoatedAPI()
            wager_data = await api.get_player_wager_stats(username)
            if wager_data:
                await cache_wager_data(username, wager_data)
            await api.close()

        if wager_data:
            monthly_wager = wager_data.get('monthly_wager', 0)
            message, reply_markup = await milestone_tracker.get_milestone_progress_message(username, monthly_wager)
        else:
            message = "❌ **Unable to fetch wager data**\n\nPlease try again later or contact support."
            await log_command_usage(user.id, "milestones", False, "API returned no data")

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
        await log_command_usage(user.id, "milestones", True)

    except Exception as e:
        logger.error(f"Error fetching milestone data for user {user.id}: {e}")
        message = "❌ **Error fetching data**\n\nThere was an issue retrieving your milestone information. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "milestones", False, str(e))

async def milestone_info_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /milestone_info command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested milestone information")

    message = await milestone_tracker.get_milestone_definitions()

    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    await log_command_usage(user.id, "milestone_info", True)

async def milestone_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle milestone-related callback queries."""
    query = update.callback_query
    user = query.from_user

    await query.answer()

    try:
        callback_data = query.data

        if callback_data.startswith("request_milestone_"):
            # Parse callback data: request_milestone_{amount}_{bonus}_{month_year}
            parts = callback_data.split("_")
            milestone_amount = int(parts[2])
            bonus_amount = float(parts[3])
            month_year = parts[4]

            # Check if user is registered
            user_data = await get_user(telegram_id=user.id)
            if not user_data:
                await query.edit_message_text(
                    "❌ **Not Registered**\n\nYou need to register first to request milestone rewards.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            username = user_data['goated_username']

            # Create the milestone request
            success = await milestone_tracker.request_milestone_reward(
                username, user.id, milestone_amount, bonus_amount, month_year
            )

            if success:
                from bot.utils import format_wager_amount
                from datetime import datetime
                month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')

                message = f"✅ **Request Submitted!**\n\n"
                message += f"🎯 **Milestone:** {format_wager_amount(milestone_amount)}\n"
                message += f"💰 **Bonus:** ${bonus_amount:.0f}\n"
                message += f"📅 **Month:** {month_name}\n\n"
                message += "Your request has been sent to the admins. You'll be notified when it's processed.\n\n"
                message += "_Use /milestones to check your request status_"

                await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN)
            else:
                await query.edit_message_text(
                    "❌ **Request Failed**\n\nThis milestone may have already been requested or there was an error.",
                    parse_mode=ParseMode.MARKDOWN
                )

        elif callback_data.startswith("pending_milestone_") or callback_data.startswith("approved_milestone_"):
            await query.edit_message_text(
                "ℹ️ **Request Status**\n\nUse /milestones to view your current request status.",
                parse_mode=ParseMode.MARKDOWN
            )

        elif callback_data == "refresh_milestones":
            # Refresh milestone progress
            user_data = await get_user(telegram_id=user.id)
            if not user_data:
                await query.edit_message_text(
                    "❌ **Not Registered**\n\nYou need to register first.",
                    parse_mode=ParseMode.MARKDOWN
                )
                return

            username = user_data['goated_username']

            # Get fresh wager data
            wager_data = await get_cached_wager_data(username)
            if not wager_data:
                api = GoatedAPI()
                wager_data = await api.get_player_wager_stats(username)
                if wager_data:
                    await cache_wager_data(username, wager_data)
                await api.close()

            if wager_data:
                monthly_wager = wager_data.get('monthly_wager', 0)
                message, reply_markup = await milestone_tracker.get_milestone_progress_message(username, monthly_wager)
                await query.edit_message_text(message, parse_mode=ParseMode.MARKDOWN, reply_markup=reply_markup)
            else:
                await query.edit_message_text(
                    "❌ **Error**\n\nUnable to refresh milestone data.",
                    parse_mode=ParseMode.MARKDOWN
                )

        await log_command_usage(user.id, f"milestone_callback_{callback_data}", True)

    except Exception as e:
        logger.error(f"Error handling milestone callback for user {user.id}: {e}")
        await query.edit_message_text(
            "❌ **Error**\n\nThere was an issue processing your request.",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_command_usage(user.id, "milestone_callback", False, str(e))

async def pending_requests_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /pending_requests admin command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested pending milestone requests")

    # Admin check
    ADMIN_USER_IDS = [5612012431, 5966207178]

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        pending_requests = await get_pending_milestone_requests()

        if not pending_requests:
            message = "📋 **No Pending Requests**\n\nThere are currently no pending milestone reward requests."
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            return

        message = f"📋 **Pending Milestone Requests** ({len(pending_requests)})\n\n"

        for i, request in enumerate(pending_requests, 1):
            from bot.utils import format_wager_amount
            from datetime import datetime

            username = request['username']
            milestone_amount = request['milestone_amount']
            bonus_amount = request['bonus_amount']
            month_year = request['month_year']
            requested_at = request['requested_at']
            request_id = request['id']

            month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')

            message += f"**#{i} - Request ID: {request_id}**\n"
            message += f"👤 User: {username}\n"
            message += f"🎯 Milestone: {format_wager_amount(milestone_amount)}\n"
            message += f"💰 Bonus: ${bonus_amount:.0f}\n"
            message += f"📅 Month: {month_name}\n"
            message += f"⏰ Requested: {requested_at}\n\n"

        message += "Use `/approve_request <ID>` or `/deny_request <ID> [reason]` to process requests."

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "pending_requests", True)

    except Exception as e:
        logger.error(f"Error getting pending requests for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue retrieving pending requests."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "pending_requests", False, str(e))

async def approve_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /approve_request admin command."""
    user = update.effective_user
    logger.info(f"Admin {user.id} approving milestone request")

    # Admin check
    ADMIN_USER_IDS = [5612012431, 5966207178]

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ **Usage:** `/approve_request <request_id>`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        request_id = int(args[0])
        admin_notes = " ".join(args[1:]) if len(args) > 1 else "Approved by admin"

        success = await update_milestone_request_status(request_id, "approved", user.id, admin_notes)

        if success:
            message = f"✅ **Request Approved**\n\nMilestone request #{request_id} has been approved."
        else:
            message = f"❌ **Error**\n\nFailed to approve request #{request_id}. Check if the ID is valid."

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "approve_request", success)

    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid ID**\n\nPlease provide a valid request ID number.",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_command_usage(user.id, "approve_request", False, "Invalid ID")
    except Exception as e:
        logger.error(f"Error approving request for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue approving the request."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "approve_request", False, str(e))

async def deny_request_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /deny_request admin command."""
    user = update.effective_user
    logger.info(f"Admin {user.id} denying milestone request")

    # Admin check
    ADMIN_USER_IDS = [5612012431, 5966207178]

    if user.id not in ADMIN_USER_IDS:
        await update.message.reply_text(
            "❌ **Access Denied**\n\nThis command is only available to administrators.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "❌ **Usage:** `/deny_request <request_id> [reason]`",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        request_id = int(args[0])
        admin_notes = " ".join(args[1:]) if len(args) > 1 else "Denied by admin"

        success = await update_milestone_request_status(request_id, "denied", user.id, admin_notes)

        if success:
            message = f"❌ **Request Denied**\n\nMilestone request #{request_id} has been denied."
            if len(args) > 1:
                message += f"\n\n**Reason:** {admin_notes}"
        else:
            message = f"❌ **Error**\n\nFailed to deny request #{request_id}. Check if the ID is valid."

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "deny_request", success)

    except ValueError:
        await update.message.reply_text(
            "❌ **Invalid ID**\n\nPlease provide a valid request ID number.",
            parse_mode=ParseMode.MARKDOWN
        )
        await log_command_usage(user.id, "deny_request", False, "Invalid ID")
    except Exception as e:
        logger.error(f"Error denying request for admin {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue denying the request."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "deny_request", False, str(e))

async def unregister_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /unregister command."""
    user = update.effective_user
    logger.info(f"User {user.id} requested to unregister")

    try:
        # Check if user is registered
        user_data = await get_user(telegram_id=user.id)
        if not user_data:
            message = """
❌ **Not Registered**

You are not currently registered with the bot.

Use `/register YOUR_USERNAME` if you want to register.
            """
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "unregister", False, "User not registered")
            return

        # Get user data summary
        data_summary = await get_user_data_summary(user.id)

        if not data_summary:
            message = "❌ **Error**\n\nUnable to retrieve your account information."
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "unregister", False, "Could not get data summary")
            return

        username = data_summary['username']
        achievement_count = data_summary['achievement_count']
        total_bonus = data_summary['total_bonus_earned']
        request_count = data_summary['request_count']

        # Create confirmation message with data summary
        message = f"""
⚠️ **CONFIRM UNREGISTRATION** ⚠️

You are about to unregister from the Goated Wager Bot.

**Your Account:**
👤 **Username:** {username}
📅 **Registered:** {data_summary['registered_at'][:10]}
🏆 **Achievements:** {achievement_count} milestones
💰 **Total Bonus Earned:** ${total_bonus:.0f}
📋 **Requests Made:** {request_count}

**⚠️ WARNING: This action will:**
• Delete your account and all associated data
• Remove all milestone achievements and requests
• Clear your wager and leaderboard cache
• Cannot be undone

**To confirm unregistration, type:**
`/confirm_unregister {username}`

**To cancel, simply ignore this message.**
        """

        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "unregister", True, "Confirmation requested")

    except Exception as e:
        logger.error(f"Error processing unregister request for user {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue processing your unregister request. Please try again later."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "unregister", False, str(e))

async def confirm_unregister_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /confirm_unregister command."""
    user = update.effective_user
    logger.info(f"User {user.id} confirming unregistration")

    try:
        args = context.args
        if not args:
            message = """
❌ **Missing Username**

To confirm unregistration, you must provide your username:
`/confirm_unregister YOUR_USERNAME`

This is a safety measure to prevent accidental unregistration.
            """
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "confirm_unregister", False, "Missing username")
            return

        provided_username = args[0]

        # Check if user is registered and username matches
        user_data = await get_user(telegram_id=user.id)
        if not user_data:
            message = "❌ **Not Registered**\n\nYou are not currently registered with the bot."
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "confirm_unregister", False, "User not registered")
            return

        actual_username = user_data['goated_username']

        if provided_username != actual_username:
            message = f"""
❌ **Username Mismatch**

The username you provided doesn't match your registered username.

**Your registered username:** {actual_username}
**You provided:** {provided_username}

Please use the correct username to confirm unregistration.
            """
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "confirm_unregister", False, "Username mismatch")
            return

        # Perform the unregistration
        success = await unregister_user(user.id)

        if success:
            message = f"""
✅ **Successfully Unregistered**

Your account has been completely removed from the Goated Wager Bot.

**What was deleted:**
• Account registration for {actual_username}
• All milestone achievements and requests
• Cached wager and leaderboard data
• Personal data associations

Thank you for using the Goated Wager Bot!

You can register again anytime with `/register YOUR_USERNAME`.
            """
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "confirm_unregister", True, f"Unregistered {actual_username}")
        else:
            message = "❌ **Unregistration Failed**\n\nThere was an error removing your account. Please contact support."
            await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
            await log_command_usage(user.id, "confirm_unregister", False, "Database error")

    except Exception as e:
        logger.error(f"Error confirming unregistration for user {user.id}: {e}")
        message = "❌ **Error**\n\nThere was an issue processing your unregistration. Please contact support."
        await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
        await log_command_usage(user.id, "confirm_unregister", False, str(e))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle errors that occur during bot operation."""
    logger.error(f"Exception while handling an update: {context.error}")

    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ **Oops! Something went wrong.**\n\n"
            "Please try again later or contact support if the issue persists.",
            parse_mode=ParseMode.MARKDOWN
        )
