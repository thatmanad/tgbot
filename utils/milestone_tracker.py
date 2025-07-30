#!/usr/bin/env python3
"""
Milestone achievement tracking and notification system.
"""

import logging
from typing import List, Dict, Any, Optional
from telegram import Bot
from telegram.constants import ParseMode

from database.connection import (
    check_milestone_achievements,
    get_user_achievements,
    get_next_milestone,
    mark_achievements_notified,
    get_user,
    create_milestone_request,
    get_user_milestone_requests,
    get_pending_milestone_requests,
    update_milestone_request_status
)
from bot.utils import format_wager_amount

logger = logging.getLogger(__name__)

class MilestoneTracker:
    """Handles milestone achievement tracking and notifications."""
    
    def __init__(self, bot: Optional[Bot] = None):
        self.bot = bot
    
    async def check_and_notify_milestones(self, username: str, current_monthly_wager: float) -> List[Dict[str, Any]]:
        """Check for new monthly milestones and send notifications if bot is available."""
        try:
            # Check for new achievements
            new_achievements = await check_milestone_achievements(username, current_monthly_wager)
            
            if new_achievements and self.bot:
                # Get user's telegram info for notification
                user_data = await get_user(goated_username=username)
                if user_data:
                    telegram_id = user_data.get('telegram_id')
                    if telegram_id:
                        await self._send_achievement_notification(telegram_id, username, new_achievements)
                        
                        # Mark as notified
                        milestone_amounts = [achievement['milestone_amount'] for achievement in new_achievements]
                        await mark_achievements_notified(username, milestone_amounts)
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking milestones for {username}: {e}")
            return []
    
    async def _send_achievement_notification(self, telegram_id: int, username: str, achievements: List[Dict[str, Any]]):
        """Send achievement notification to user."""
        try:
            if not self.bot:
                return
            
            # Create achievement message
            message = "🎉 **MILESTONE ACHIEVED!** 🎉\n\n"
            message += f"Congratulations {username}! You've reached new wager milestones:\n\n"
            
            total_bonus = 0
            for achievement in achievements:
                milestone_amount = achievement['milestone_amount']
                bonus_amount = achievement['bonus_amount']
                total_bonus += bonus_amount
                
                message += f"🔥 **{format_wager_amount(milestone_amount)}** wagered\n"
                message += f"💰 **${bonus_amount:.0f} bonus earned!**\n\n"
            
            if len(achievements) > 1:
                message += f"🎊 **Total bonus earned: ${total_bonus:.0f}**\n\n"
            
            message += "Keep up the great work! 🚀\n"
            message += "_Use /milestones to see all your achievements_"
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"Sent milestone notification to user {telegram_id} for {len(achievements)} achievements")
            
        except Exception as e:
            logger.error(f"Error sending achievement notification to {telegram_id}: {e}")

    async def send_admin_request_notification(self, username: str, milestone_amount: int, bonus_amount: float, month_year: str):
        """Send notification to admins about a new milestone request."""
        try:
            if not self.bot:
                return

            # Admin user IDs (should match the ones in handlers.py)
            ADMIN_USER_IDS = [5612012431, 5966207178]

            from bot.utils import format_wager_amount
            from datetime import datetime

            month_name = datetime.strptime(month_year, '%Y-%m').strftime('%B %Y')

            message = "🔔 **NEW MILESTONE REWARD REQUEST** 🔔\n\n"
            message += f"👤 **User:** {username}\n"
            message += f"🎯 **Milestone:** {format_wager_amount(milestone_amount)}\n"
            message += f"💰 **Bonus Amount:** ${bonus_amount:.0f}\n"
            message += f"📅 **Month:** {month_name}\n\n"
            message += "Use `/pending_requests` to view and manage all requests."

            for admin_id in ADMIN_USER_IDS:
                try:
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                except Exception as e:
                    logger.warning(f"Failed to send admin notification to {admin_id}: {e}")

            logger.info(f"Sent milestone request notification to admins for {username}")

        except Exception as e:
            logger.error(f"Error sending admin request notification: {e}")

    async def request_milestone_reward(self, username: str, telegram_id: int, milestone_amount: int, bonus_amount: float, month_year: str) -> bool:
        """Create a milestone reward request and notify admins."""
        try:
            # Create the request
            success = await create_milestone_request(username, telegram_id, milestone_amount, bonus_amount, month_year)

            if success:
                # Send notification to admins
                await self.send_admin_request_notification(username, milestone_amount, bonus_amount, month_year)
                logger.info(f"Created milestone request for {username}: ${bonus_amount} for {milestone_amount}")
                return True
            else:
                logger.warning(f"Failed to create milestone request for {username} - may already exist")
                return False

        except Exception as e:
            logger.error(f"Error requesting milestone reward for {username}: {e}")
            return False
    
    async def get_milestone_progress_message(self, username: str, current_monthly_wager: float) -> tuple[str, list]:
        """Get a formatted message showing monthly milestone progress with request buttons."""
        try:
            # Get current month/year
            from datetime import datetime
            current_month_year = datetime.now().strftime('%Y-%m')
            current_month_name = datetime.now().strftime('%B %Y')

            # Get user's achievements for current month
            achievements = await get_user_achievements(username, current_month_year)
            next_milestone = await get_next_milestone(username, current_monthly_wager)

            # Get existing requests for this month
            existing_requests = await get_user_milestone_requests(username, current_month_year)
            requested_milestones = {req['milestone_amount']: req['status'] for req in existing_requests}

            message = f"🏆 **Your Monthly Milestone Progress** 🏆\n"
            message += f"📅 **{current_month_name}**\n\n"
            
            # Show achieved milestones for current month
            if achievements:
                total_bonus_earned = sum(a['bonus_amount'] for a in achievements)
                message += f"✅ **This Month's Achievements:** {len(achievements)}\n"
                message += f"💰 **Monthly Bonus Earned:** ${total_bonus_earned:.0f}\n\n"

                message += "**Achievements This Month:**\n"
                for achievement in achievements:
                    milestone_amount = achievement['milestone_amount']
                    bonus_amount = achievement['bonus_amount']
                    message += f"🔥 {format_wager_amount(milestone_amount)} - ${bonus_amount:.0f}\n"
                message += "\n"
            else:
                message += "📋 No milestones achieved this month\n\n"
            
            # Show next milestone
            if next_milestone:
                milestone_amount = next_milestone['milestone_amount']
                bonus_amount = next_milestone['bonus_amount']
                remaining = next_milestone['remaining']
                progress = next_milestone['progress']
                
                message += "🎯 **Next Milestone:**\n"
                message += f"Target: {format_wager_amount(milestone_amount)}\n"
                message += f"Bonus: ${bonus_amount:.0f}\n"
                message += f"Remaining: {format_wager_amount(remaining)}\n"
                
                # Progress bar
                progress_percent = min(progress * 100, 100)
                progress_bar = self._create_progress_bar(progress_percent)
                message += f"Progress: {progress_bar} {progress_percent:.1f}%\n"
            else:
                message += "🎊 **All monthly milestones achieved!**\n"
                message += "Keep wagering for $50 bonuses every 50k this month!\n"
            
            # Create inline keyboard for requesting rewards
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            keyboard = []

            # Add request buttons for achieved milestones that haven't been requested
            for achievement in achievements:
                milestone_amount = achievement['milestone_amount']
                bonus_amount = achievement['bonus_amount']

                if milestone_amount not in requested_milestones:
                    # Not requested yet - show request button
                    button_text = f"Request ${bonus_amount:.0f} ({format_wager_amount(milestone_amount)})"
                    callback_data = f"request_milestone_{milestone_amount}_{bonus_amount}_{current_month_year}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
                elif requested_milestones[milestone_amount] == 'pending':
                    # Already requested - show pending status
                    button_text = f"⏳ Pending: ${bonus_amount:.0f} ({format_wager_amount(milestone_amount)})"
                    callback_data = f"pending_milestone_{milestone_amount}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
                elif requested_milestones[milestone_amount] == 'approved':
                    # Approved - show status
                    button_text = f"✅ Approved: ${bonus_amount:.0f} ({format_wager_amount(milestone_amount)})"
                    callback_data = f"approved_milestone_{milestone_amount}"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

            # Add refresh button
            keyboard.append([InlineKeyboardButton("🔄 Refresh Progress", callback_data="refresh_milestones")])

            reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None

            return message, reply_markup

        except Exception as e:
            logger.error(f"Error getting milestone progress for {username}: {e}")
            return "❌ Error retrieving milestone progress", None
    
    def _create_progress_bar(self, percentage: float, length: int = 10) -> str:
        """Create a visual progress bar."""
        filled = int(length * percentage / 100)
        bar = "█" * filled + "░" * (length - filled)
        return f"[{bar}]"
    
    async def get_milestone_definitions(self) -> str:
        """Get formatted milestone definitions."""
        from datetime import datetime
        current_month = datetime.now().strftime('%B %Y')

        message = "🎯 **Monthly Wager Milestone Rewards** 🎯\n\n"
        message += f"Earn bonuses for reaching monthly wager milestones in **{current_month}**:\n\n"
        message += "🔥 **$10** for **10k** wagered this month\n"
        message += "🔥 **$15** for **25k** wagered this month\n"
        message += "🔥 **$25** for **50k** wagered this month\n"
        message += "🔥 **$50** for **100k** wagered this month\n"
        message += "🔥 **$50** for every **50k** after 100k this month!\n\n"
        message += "📅 **Milestones reset each month**\n"
        message += "_Milestones are based on your monthly wager amount_\n"
        message += "_Use /wager to check your current progress_"

        return message

# Global milestone tracker instance
milestone_tracker = MilestoneTracker()

def set_milestone_bot(bot: Bot):
    """Set the bot instance for milestone notifications."""
    global milestone_tracker
    milestone_tracker.bot = bot
