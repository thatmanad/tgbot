"""
Utility functions for the Goated Wager Tracker Bot.
"""

import re
from typing import Union, Optional
from datetime import datetime

def format_wager_amount(amount: Union[int, float, str]) -> str:
    """Format wager amount for display."""
    try:
        if isinstance(amount, str):
            # Remove any currency symbols and convert to float
            amount = float(re.sub(r'[^\d.]', '', amount))
        
        if amount >= 1000000:
            return f"${amount/1000000:.2f}M"
        elif amount >= 1000:
            return f"${amount/1000:.2f}K"
        else:
            return f"${amount:.2f}"
    except (ValueError, TypeError):
        return "N/A"

def format_leaderboard_position(position: Union[int, str]) -> str:
    """Format leaderboard position for display."""
    try:
        if isinstance(position, str) and position.lower() in ['n/a', 'none', '']:
            return "Not Ranked"
        
        pos = int(position)
        
        # Add ordinal suffix
        if 10 <= pos % 100 <= 20:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(pos % 10, "th")
        
        # Add emoji for top positions
        if pos == 1:
            return f"🥇 {pos}{suffix}"
        elif pos == 2:
            return f"🥈 {pos}{suffix}"
        elif pos == 3:
            return f"🥉 {pos}{suffix}"
        elif pos <= 10:
            return f"🔥 {pos}{suffix}"
        elif pos <= 50:
            return f"⭐ {pos}{suffix}"
        else:
            return f"#{pos}{suffix}"
            
    except (ValueError, TypeError):
        return "Not Ranked"

def validate_affiliate_id(affiliate_id: str) -> bool:
    """Validate affiliate ID format."""
    if not affiliate_id or not isinstance(affiliate_id, str):
        return False
    
    # Basic validation - adjust based on actual goated.com affiliate ID format
    # This is a placeholder implementation
    if len(affiliate_id) < 3 or len(affiliate_id) > 50:
        return False
    
    # Check for valid characters (alphanumeric and some special chars)
    if not re.match(r'^[a-zA-Z0-9_-]+$', affiliate_id):
        return False
    
    return True

def format_datetime(dt: Optional[datetime]) -> str:
    """Format datetime for display."""
    if not dt:
        return "Unknown"
    
    try:
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except:
        return "Unknown"

def sanitize_input(text: str, max_length: int = 100) -> str:
    """Sanitize user input."""
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()

def format_progress_bar(current: float, target: float, width: int = 10) -> str:
    """Create a simple progress bar."""
    try:
        if target <= 0:
            return "N/A"
        
        percentage = min(current / target, 1.0)
        filled = int(percentage * width)
        empty = width - filled
        
        bar = "█" * filled + "░" * empty
        return f"{bar} {percentage*100:.1f}%"
    except:
        return "N/A"

def get_rank_emoji(position: int) -> str:
    """Get emoji for rank position."""
    if position == 1:
        return "🥇"
    elif position == 2:
        return "🥈"
    elif position == 3:
        return "🥉"
    elif position <= 10:
        return "🔥"
    elif position <= 50:
        return "⭐"
    else:
        return "📊"
