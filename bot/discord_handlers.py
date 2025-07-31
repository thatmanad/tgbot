"""
Discord bot handlers for Goated Wager Bot.
Shares the same backend as the Telegram bot.
"""

import discord
from discord.ext import commands
import logging
import os
from typing import Optional

# Import shared backend functions
from database.connection import (
    get_user, create_user, 
    get_cached_wager_data, cache_wager_data,
    log_command_usage
)
from api.goated_api import GoatedAPI
from utils.milestone_tracker import MilestoneTracker
from bot.utils import format_wager_amount

logger = logging.getLogger(__name__)

class GoatedWagerDiscordBot(commands.Bot):
    """Discord bot for Goated Wager tracking."""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Goated Wager Tracker Bot'
        )
        
        self.milestone_tracker = MilestoneTracker()
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f'{self.user} has connected to Discord!')
        logger.info(f'Bot is in {len(self.guilds)} guilds')

        # List the guilds for debugging
        for guild in self.guilds:
            logger.info(f'Connected to guild: {guild.name} (id: {guild.id})')

    async def setup_hook(self):
        """Called when the bot is starting up."""
        logger.info("Discord bot is starting up...")

    async def on_connect(self):
        """Called when the bot connects to Discord."""
        logger.info("Discord bot connected to Discord gateway")
    
    async def on_command_error(self, ctx, error):
        """Handle command errors."""
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore unknown commands
        
        logger.error(f"Discord command error: {error}")
        await ctx.send("❌ An error occurred while processing your command.")

# Create bot instance
discord_bot = GoatedWagerDiscordBot()

@discord_bot.command(name='register')
async def register_command(ctx, username: str = None):
    """Register your goated.com username."""
    user_id = ctx.author.id
    discord_username = str(ctx.author)
    
    logger.info(f"Discord user {user_id} attempting to register")
    
    if not username:
        await ctx.send("❌ **Usage:** `!register YOUR_USERNAME`")
        await log_command_usage(user_id, "discord_register", False, "Missing username")
        return
    
    try:
        # Check if user already exists
        existing_user = await get_user(discord_id=user_id)
        if existing_user:
            await ctx.send(f"✅ You're already registered as **{existing_user['goated_username']}**")
            await log_command_usage(user_id, "discord_register", True, "Already registered")
            return
        
        # Validate username with API
        api = GoatedAPI()
        try:
            player_data = await api.find_player_by_username(username)
            if not player_data:
                await ctx.send(f"❌ **Username not found:** `{username}`\n\nMake sure you're using your exact goated.com username.")
                await log_command_usage(user_id, "discord_register", False, "Username not found")
                return
        finally:
            await api.close()
        
        # Create user account
        success = await create_user(user_id, discord_username, username, platform='discord')
        
        if success:
            embed = discord.Embed(
                title="✅ Registration Successful!",
                description=f"Welcome **{username}**! You can now use all bot commands.",
                color=discord.Color.green()
            )
            embed.add_field(name="Next Steps", value="• Use `!wager` to check your stats\n• Use `!milestones` to track progress\n• Use `!help` for all commands", inline=False)
            await ctx.send(embed=embed)
            await log_command_usage(user_id, "discord_register", True)
        else:
            await ctx.send("❌ **Registration failed.** Please try again later.")
            await log_command_usage(user_id, "discord_register", False, "Database error")
            
    except Exception as e:
        logger.error(f"Error in Discord register command for user {user_id}: {e}")
        await ctx.send("❌ **Error during registration.** Please try again later.")
        await log_command_usage(user_id, "discord_register", False, str(e))

@discord_bot.command(name='wager')
async def wager_command(ctx):
    """Check your wager statistics."""
    user_id = ctx.author.id
    logger.info(f"Discord user {user_id} requested wager information")
    
    try:
        # Check if user is registered
        user_data = await get_user(discord_id=user_id)
        if not user_data:
            await ctx.send("❌ **Not registered!** Use `!register YOUR_USERNAME` first.")
            await log_command_usage(user_id, "discord_wager", False, "User not registered")
            return
        
        username = user_data['goated_username']
        
        # Get wager data
        wager_data = await get_cached_wager_data(username)
        if not wager_data:
            # Fetch fresh data
            api = GoatedAPI()
            try:
                player_data = await api.find_player_by_username(username)
                if player_data:
                    wager_data = player_data.get('wagered', {})
                    await cache_wager_data(username, wager_data)
            finally:
                await api.close()
        
        if not wager_data:
            await ctx.send(f"❌ **No wager data found** for {username}")
            await log_command_usage(user_id, "discord_wager", False, "No wager data")
            return
        
        # Check for new milestones
        monthly_wager = wager_data.get('monthly', 0)
        milestone_tracker = MilestoneTracker()
        new_milestones = await milestone_tracker.check_milestones(username, monthly_wager)
        
        # Create embed
        embed = discord.Embed(
            title=f"💰 Wager Stats for {username}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📊 Current Stats",
            value=f"**Daily:** {format_wager_amount(wager_data.get('daily', 0))}\n"
                  f"**Weekly:** {format_wager_amount(wager_data.get('weekly', 0))}\n"
                  f"**Monthly:** {format_wager_amount(wager_data.get('monthly', 0))}\n"
                  f"**All Time:** {format_wager_amount(wager_data.get('all_time', 0))}",
            inline=True
        )
        
        if new_milestones:
            milestone_text = "\n".join([f"🎉 ${m['bonus_amount']:.0f} for {format_wager_amount(m['milestone_amount'])}" for m in new_milestones])
            embed.add_field(name="🏆 New Milestones!", value=milestone_text, inline=False)
        
        embed.set_footer(text="Use !milestones to see all milestone progress")
        
        await ctx.send(embed=embed)
        await log_command_usage(user_id, "discord_wager", True)
        
    except Exception as e:
        logger.error(f"Error in Discord wager command for user {user_id}: {e}")
        await ctx.send("❌ **Error fetching wager data.** Please try again later.")
        await log_command_usage(user_id, "discord_wager", False, str(e))

@discord_bot.command(name='milestones')
async def milestones_command(ctx):
    """View your milestone progress."""
    user_id = ctx.author.id
    logger.info(f"Discord user {user_id} requested milestone information")
    
    try:
        # Check if user is registered
        user_data = await get_user(discord_id=user_id)
        if not user_data:
            await ctx.send("❌ **Not registered!** Use `!register YOUR_USERNAME` first.")
            await log_command_usage(user_id, "discord_milestones", False, "User not registered")
            return
        
        username = user_data['goated_username']
        
        # Get current monthly wager
        wager_data = await get_cached_wager_data(username)
        monthly_wager = wager_data.get('monthly', 0) if wager_data else 0
        
        # Get milestone progress
        milestone_tracker = MilestoneTracker()
        message, _ = await milestone_tracker.get_milestone_progress_message(username, monthly_wager)
        
        # Create embed
        embed = discord.Embed(
            title="🏆 Monthly Milestone Progress",
            description=message,
            color=discord.Color.gold()
        )
        
        await ctx.send(embed=embed)
        await log_command_usage(user_id, "discord_milestones", True)
        
    except Exception as e:
        logger.error(f"Error in Discord milestones command for user {user_id}: {e}")
        await ctx.send("❌ **Error fetching milestone data.** Please try again later.")
        await log_command_usage(user_id, "discord_milestones", False, str(e))

@discord_bot.command(name='help')
async def help_command(ctx):
    """Show available commands."""
    embed = discord.Embed(
        title="🤖 Goated Wager Bot Commands",
        description="Track your goated.com wager statistics and milestones",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📋 User Commands",
        value="`!register USERNAME` - Register your goated.com account\n"
              "`!wager` - Check your wager statistics\n"
              "`!milestones` - View milestone progress\n"
              "`!leaderboard` - Check your leaderboard position\n"
              "`!help` - Show this help message",
        inline=False
    )
    
    embed.set_footer(text="Bot also available on Telegram!")
    await ctx.send(embed=embed)

# Export the bot instance
__all__ = ['discord_bot']
