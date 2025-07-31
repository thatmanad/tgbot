"""
Database connection and operations for the Goated Wager Tracker Bot.
"""

import sqlite3
import asyncio
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self):
        database_url = os.getenv('DATABASE_URL', 'sqlite:///goated_bot.db')
        self.db_path = database_url.replace('sqlite:///', '')
        self._lock = asyncio.Lock()
    
    async def init_database(self):
        """Initialize the database with required tables."""
        async with self._lock:
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                
                # Create users table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS users (
                        telegram_id INTEGER PRIMARY KEY,
                        telegram_username TEXT,
                        goated_username TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        last_wager_check TIMESTAMP,
                        last_leaderboard_check TIMESTAMP
                    )
                ''')
                
                # Create wager_cache table for caching API responses
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS wager_cache (
                        username TEXT PRIMARY KEY,
                        daily_wager REAL,
                        weekly_wager REAL,
                        last_7_days_wager REAL,
                        monthly_wager REAL,
                        total_wager REAL,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')
                
                # Create daily_wager_history table for tracking daily wagers
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_wager_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        date TEXT NOT NULL,
                        daily_wager REAL NOT NULL,
                        total_wager REAL,
                        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(username, date)
                    )
                ''')

                # Create index for faster queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_daily_wager_username_date
                    ON daily_wager_history(username, date)
                ''')

                # Create leaderboard_cache table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS leaderboard_cache (
                        username TEXT PRIMARY KEY,
                        daily_rank INTEGER,
                        weekly_rank INTEGER,
                        last_7_days_rank INTEGER,
                        monthly_rank INTEGER,
                        all_time_rank INTEGER,
                        total_players INTEGER,
                        player_daily REAL,
                        player_weekly REAL,
                        player_last_7_days REAL,
                        player_monthly REAL,
                        player_all_time REAL,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP
                    )
                ''')

                # Create weekly_leaderboard_snapshots table for storing top 10 weekly
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS weekly_leaderboard_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        snapshot_date TEXT NOT NULL,
                        rank_position INTEGER NOT NULL,
                        username TEXT NOT NULL,
                        affiliate_id TEXT,
                        daily_wager REAL,
                        weekly_wager REAL,
                        last_7_days_wager REAL,
                        monthly_wager REAL,
                        all_time_wager REAL,
                        total_players INTEGER,
                        captured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(snapshot_date, rank_position)
                    )
                ''')

                # Create index for faster queries on weekly snapshots
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_weekly_snapshots_date
                    ON weekly_leaderboard_snapshots(snapshot_date)
                ''')

                # Create milestone_achievements table for tracking monthly wager milestones
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS milestone_achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        milestone_amount INTEGER NOT NULL,
                        bonus_amount REAL NOT NULL,
                        achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        month_year TEXT NOT NULL,
                        monthly_wager_at_achievement REAL,
                        notified BOOLEAN DEFAULT 0,
                        UNIQUE(username, milestone_amount, month_year)
                    )
                ''')

                # Create index for faster milestone queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_milestone_username
                    ON milestone_achievements(username)
                ''')

                # Create milestone_definitions table for configurable milestones
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS milestone_definitions (
                        milestone_amount INTEGER PRIMARY KEY,
                        bonus_amount REAL NOT NULL,
                        description TEXT,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')

                # Insert default milestone definitions
                cursor.execute('''
                    INSERT OR IGNORE INTO milestone_definitions
                    (milestone_amount, bonus_amount, description) VALUES
                    (10000, 10.0, '$10 for 10k wagered'),
                    (25000, 15.0, '$15 for 25k wagered'),
                    (50000, 25.0, '$25 for 50k wagered'),
                    (100000, 50.0, '$50 at 100k wagered')
                ''')

                # Create milestone_requests table for tracking reward requests
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS milestone_requests (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        telegram_id INTEGER NOT NULL,
                        milestone_amount INTEGER NOT NULL,
                        bonus_amount REAL NOT NULL,
                        month_year TEXT NOT NULL,
                        requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        status TEXT DEFAULT 'pending',
                        admin_notes TEXT,
                        processed_by INTEGER,
                        processed_at TIMESTAMP,
                        UNIQUE(username, milestone_amount, month_year)
                    )
                ''')

                # Create indexes for faster request queries
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_milestone_requests_status
                    ON milestone_requests(status)
                ''')

                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_milestone_requests_user
                    ON milestone_requests(username, month_year)
                ''')

                # Create bot_stats table for tracking usage
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS bot_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER,
                        command TEXT,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        success BOOLEAN DEFAULT 1,
                        error_message TEXT
                    )
                ''')
                
                conn.commit()
                conn.close()
                logger.info("Database initialized successfully")
                
            except Exception as e:
                logger.error(f"Error initializing database: {e}")
                raise

# Global database manager instance
db_manager = DatabaseManager()

async def get_user(telegram_id: int = None, discord_id: int = None) -> Optional[Dict[str, Any]]:
    """Get user by Telegram ID or Discord ID."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if discord_id:
                cursor.execute(
                    "SELECT * FROM users WHERE discord_id = ? AND is_active = 1",
                    (discord_id,)
                )
            elif telegram_id:
                cursor.execute(
                    "SELECT * FROM users WHERE telegram_id = ? AND is_active = 1",
                    (telegram_id,)
                )
            else:
                conn.close()
                return None

            row = cursor.fetchone()
            conn.close()

            if row:
                return dict(row)
            return None

        except Exception as e:
            logger.error(f"Error getting user (telegram: {telegram_id}, discord: {discord_id}): {e}")
            return None

async def create_user(telegram_id: int = None, telegram_username: Optional[str] = None, goated_username: str = None,
                     discord_id: int = None, discord_username: str = None, platform: str = 'telegram') -> bool:
    """Create a new user for either Telegram or Discord."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            if platform == 'discord':
                cursor.execute('''
                    INSERT INTO users (discord_id, discord_username, goated_username, platform)
                    VALUES (?, ?, ?, ?)
                ''', (discord_id, discord_username, goated_username, platform))
                logger.info(f"Created Discord user {discord_id} with goated username {goated_username}")
            else:
                cursor.execute('''
                    INSERT INTO users (telegram_id, telegram_username, goated_username, platform)
                    VALUES (?, ?, ?, ?)
                ''', (telegram_id, telegram_username, goated_username, platform))
                logger.info(f"Created Telegram user {telegram_id} with goated username {goated_username}")

            conn.commit()
            conn.close()
            return True

        except sqlite3.IntegrityError as e:
            logger.error(f"User creation failed - duplicate goated username: {e}")
            return False
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return False

async def update_user(telegram_id: int, **kwargs) -> bool:
    """Update user information."""
    async with db_manager._lock:
        try:
            if not kwargs:
                return True
            
            # Build dynamic update query
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['telegram_username', 'goated_username', 'is_active', 'last_wager_check', 'last_leaderboard_check']:
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return True
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(telegram_id)
            
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()
            
            query = f"UPDATE users SET {', '.join(set_clauses)} WHERE telegram_id = ?"
            cursor.execute(query, values)
            
            conn.commit()
            conn.close()
            
            logger.info(f"Updated user {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating user {telegram_id}: {e}")
            return False

async def cache_wager_data(username: str, wager_data: Dict[str, Any], cache_duration_minutes: int = 5) -> bool:
    """Cache wager data to reduce API calls."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            expires_at = datetime.now().timestamp() + (cache_duration_minutes * 60)

            cursor.execute('''
                INSERT OR REPLACE INTO wager_cache
                (username, daily_wager, weekly_wager, last_7_days_wager, monthly_wager, total_wager, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                wager_data.get('daily_wager', 0),
                wager_data.get('weekly_wager', 0),
                wager_data.get('last_7_days_wager', wager_data.get('weekly_wager', 0)),  # Use weekly as fallback for last 7 days
                wager_data.get('monthly_wager', 0),
                wager_data.get('total_wager', 0),
                expires_at
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error caching wager data for {username}: {e}")
            return False

async def get_cached_wager_data(username: str) -> Optional[Dict[str, Any]]:
    """Get cached wager data if still valid."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM wager_cache
                WHERE username = ? AND expires_at > ?
            ''', (username, datetime.now().timestamp()))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'daily_wager': row['daily_wager'],
                    'weekly_wager': row['weekly_wager'],
                    'last_7_days_wager': row['last_7_days_wager'],
                    'monthly_wager': row['monthly_wager'],
                    'total_wager': row['total_wager'],
                    'username': username,
                    'last_updated': row['cached_at']
                }

            return None

        except Exception as e:
            logger.error(f"Error getting cached wager data for {username}: {e}")
            return None

async def cache_leaderboard_data(username: str, leaderboard_data: Dict[str, Any], cache_duration_minutes: int = 5) -> bool:
    """Cache leaderboard data to reduce API calls."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            expires_at = datetime.now().timestamp() + (cache_duration_minutes * 60)

            cursor.execute('''
                INSERT OR REPLACE INTO leaderboard_cache
                (username, daily_rank, weekly_rank, last_7_days_rank, monthly_rank, all_time_rank,
                 total_players, player_daily, player_weekly, player_last_7_days, player_monthly, player_all_time, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                username,
                leaderboard_data.get('daily_rank'),
                leaderboard_data.get('weekly_rank'),
                leaderboard_data.get('last_7_days_rank', leaderboard_data.get('weekly_rank')),  # Use weekly rank as fallback
                leaderboard_data.get('monthly_rank'),
                leaderboard_data.get('all_time_rank'),
                leaderboard_data.get('total_players'),
                leaderboard_data.get('player_daily'),
                leaderboard_data.get('player_weekly'),
                leaderboard_data.get('player_last_7_days', leaderboard_data.get('player_weekly')),  # Use weekly as fallback
                leaderboard_data.get('player_monthly'),
                leaderboard_data.get('player_all_time'),
                expires_at
            ))

            conn.commit()
            conn.close()

            return True

        except Exception as e:
            logger.error(f"Error caching leaderboard data for {username}: {e}")
            return False

async def get_cached_leaderboard_data(username: str) -> Optional[Dict[str, Any]]:
    """Get cached leaderboard data if still valid."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM leaderboard_cache
                WHERE username = ? AND expires_at > ?
            ''', (username, datetime.now().timestamp()))

            row = cursor.fetchone()
            conn.close()

            if row:
                return {
                    'username': username,
                    'daily_rank': row['daily_rank'],
                    'weekly_rank': row['weekly_rank'],
                    'last_7_days_rank': row['last_7_days_rank'],
                    'monthly_rank': row['monthly_rank'],
                    'all_time_rank': row['all_time_rank'],
                    'total_players': row['total_players'],
                    'player_daily': row['player_daily'],
                    'player_weekly': row['player_weekly'],
                    'player_last_7_days': row['player_last_7_days'],
                    'player_monthly': row['player_monthly'],
                    'player_all_time': row['player_all_time'],
                    'last_updated': row['cached_at']
                }

            return None

        except Exception as e:
            logger.error(f"Error getting cached leaderboard data for {username}: {e}")
            return None

async def store_weekly_leaderboard_snapshot(snapshot_date: str, leaderboard_data: List[Dict[str, Any]]) -> bool:
    """Store a weekly leaderboard snapshot with top 10 users."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            # Clear any existing data for this snapshot date
            cursor.execute('DELETE FROM weekly_leaderboard_snapshots WHERE snapshot_date = ?', (snapshot_date,))

            # Insert the top 10 users
            for i, player_data in enumerate(leaderboard_data[:10], 1):
                cursor.execute('''
                    INSERT INTO weekly_leaderboard_snapshots
                    (snapshot_date, rank_position, username, affiliate_id, daily_wager, weekly_wager,
                     last_7_days_wager, monthly_wager, all_time_wager, total_players)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    snapshot_date,
                    i,  # rank position (1-10)
                    player_data.get('username', ''),
                    player_data.get('affiliate_id', ''),
                    player_data.get('daily_wager', 0),
                    player_data.get('weekly_wager', 0),
                    player_data.get('last_7_days_wager', 0),
                    player_data.get('monthly_wager', 0),
                    player_data.get('all_time_wager', 0),
                    player_data.get('total_players', 0)
                ))

            conn.commit()
            conn.close()

            logger.info(f"Stored weekly leaderboard snapshot for {snapshot_date} with {len(leaderboard_data[:10])} players")
            return True

        except Exception as e:
            logger.error(f"Error storing weekly leaderboard snapshot for {snapshot_date}: {e}")
            return False

async def get_weekly_leaderboard_snapshots(limit: int = 10) -> List[Dict[str, Any]]:
    """Get the most recent weekly leaderboard snapshots."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT DISTINCT snapshot_date, captured_at
                FROM weekly_leaderboard_snapshots
                ORDER BY snapshot_date DESC
                LIMIT ?
            ''', (limit,))

            snapshots = []
            for row in cursor.fetchall():
                snapshot_date = row['snapshot_date']

                # Get the top 10 for this snapshot
                cursor.execute('''
                    SELECT * FROM weekly_leaderboard_snapshots
                    WHERE snapshot_date = ?
                    ORDER BY rank_position
                ''', (snapshot_date,))

                players = []
                for player_row in cursor.fetchall():
                    players.append({
                        'rank': player_row['rank_position'],
                        'username': player_row['username'],
                        'affiliate_id': player_row['affiliate_id'],
                        'daily_wager': player_row['daily_wager'],
                        'weekly_wager': player_row['weekly_wager'],
                        'last_7_days_wager': player_row['last_7_days_wager'],
                        'monthly_wager': player_row['monthly_wager'],
                        'all_time_wager': player_row['all_time_wager'],
                        'total_players': player_row['total_players']
                    })

                snapshots.append({
                    'snapshot_date': snapshot_date,
                    'captured_at': row['captured_at'],
                    'players': players
                })

            conn.close()
            return snapshots

        except Exception as e:
            logger.error(f"Error getting weekly leaderboard snapshots: {e}")
            return []

async def get_weekly_leaderboard_snapshot(snapshot_date: str) -> Optional[Dict[str, Any]]:
    """Get a specific weekly leaderboard snapshot by date."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM weekly_leaderboard_snapshots
                WHERE snapshot_date = ?
                ORDER BY rank_position
            ''', (snapshot_date,))

            rows = cursor.fetchall()
            conn.close()

            if not rows:
                return None

            players = []
            for row in rows:
                players.append({
                    'rank': row['rank_position'],
                    'username': row['username'],
                    'affiliate_id': row['affiliate_id'],
                    'daily_wager': row['daily_wager'],
                    'weekly_wager': row['weekly_wager'],
                    'last_7_days_wager': row['last_7_days_wager'],
                    'monthly_wager': row['monthly_wager'],
                    'all_time_wager': row['all_time_wager'],
                    'total_players': row['total_players']
                })

            return {
                'snapshot_date': snapshot_date,
                'captured_at': rows[0]['captured_at'],
                'players': players
            }

        except Exception as e:
            logger.error(f"Error getting weekly leaderboard snapshot for {snapshot_date}: {e}")
            return None

async def check_milestone_achievements(username: str, current_monthly_wager: float) -> List[Dict[str, Any]]:
    """Check if user has achieved any new monthly milestones and record them."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get current month/year
            from datetime import datetime
            current_month_year = datetime.now().strftime('%Y-%m')

            # Get all milestone definitions
            cursor.execute('SELECT * FROM milestone_definitions WHERE is_active = 1 ORDER BY milestone_amount')
            milestones = cursor.fetchall()

            # Get already achieved milestones for this user in current month
            cursor.execute(
                'SELECT milestone_amount FROM milestone_achievements WHERE username = ? AND month_year = ?',
                (username, current_month_year)
            )
            achieved_milestones = {row['milestone_amount'] for row in cursor.fetchall()}

            new_achievements = []

            for milestone in milestones:
                milestone_amount = milestone['milestone_amount']
                bonus_amount = milestone['bonus_amount']
                description = milestone['description']

                # Check if milestone is achieved and not already recorded for this month
                if current_monthly_wager >= milestone_amount and milestone_amount not in achieved_milestones:
                    # Record the achievement
                    cursor.execute('''
                        INSERT INTO milestone_achievements
                        (username, milestone_amount, bonus_amount, month_year, monthly_wager_at_achievement)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (username, milestone_amount, bonus_amount, current_month_year, current_monthly_wager))

                    new_achievements.append({
                        'milestone_amount': milestone_amount,
                        'bonus_amount': bonus_amount,
                        'description': description,
                        'monthly_wager': current_monthly_wager,
                        'month_year': current_month_year
                    })

            # Check for 50k milestones after 100k (every 50k = $50 bonus)
            if current_monthly_wager >= 100000:
                # Calculate how many 50k milestones after 100k should be achieved
                milestones_after_100k = int((current_monthly_wager - 100000) // 50000)

                for i in range(1, milestones_after_100k + 1):
                    milestone_amount = 100000 + (i * 50000)  # 150k, 200k, 250k, etc.

                    if milestone_amount not in achieved_milestones:
                        cursor.execute('''
                            INSERT INTO milestone_achievements
                            (username, milestone_amount, bonus_amount, month_year, monthly_wager_at_achievement)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (username, milestone_amount, 50.0, current_month_year, current_monthly_wager))

                        new_achievements.append({
                            'milestone_amount': milestone_amount,
                            'bonus_amount': 50.0,
                            'description': f'$50 bonus for {milestone_amount:,} wagered this month',
                            'monthly_wager': current_monthly_wager,
                            'month_year': current_month_year
                        })

            conn.commit()
            conn.close()

            if new_achievements:
                logger.info(f"User {username} achieved {len(new_achievements)} new monthly milestones for {current_month_year}")

            return new_achievements

        except Exception as e:
            logger.error(f"Error checking milestone achievements for {username}: {e}")
            return []

async def get_user_achievements(username: str, month_year: str = None) -> List[Dict[str, Any]]:
    """Get achievements for a user, optionally filtered by month."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if month_year:
                # Get achievements for specific month
                cursor.execute('''
                    SELECT ma.*, md.description
                    FROM milestone_achievements ma
                    LEFT JOIN milestone_definitions md ON ma.milestone_amount = md.milestone_amount
                    WHERE ma.username = ? AND ma.month_year = ?
                    ORDER BY ma.milestone_amount
                ''', (username, month_year))
            else:
                # Get all achievements, ordered by month and milestone
                cursor.execute('''
                    SELECT ma.*, md.description
                    FROM milestone_achievements ma
                    LEFT JOIN milestone_definitions md ON ma.milestone_amount = md.milestone_amount
                    WHERE ma.username = ?
                    ORDER BY ma.month_year DESC, ma.milestone_amount
                ''', (username,))

            achievements = []
            for row in cursor.fetchall():
                achievements.append({
                    'milestone_amount': row['milestone_amount'],
                    'bonus_amount': row['bonus_amount'],
                    'achieved_at': row['achieved_at'],
                    'month_year': row['month_year'],
                    'monthly_wager_at_achievement': row['monthly_wager_at_achievement'],
                    'description': row['description'] or f'${row["bonus_amount"]} bonus for {row["milestone_amount"]:,} wagered',
                    'notified': bool(row['notified'])
                })

            conn.close()
            return achievements

        except Exception as e:
            logger.error(f"Error getting achievements for {username}: {e}")
            return []

async def get_next_milestone(username: str, current_monthly_wager: float) -> Optional[Dict[str, Any]]:
    """Get the next milestone for a user in the current month."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get current month/year
            from datetime import datetime
            current_month_year = datetime.now().strftime('%Y-%m')

            # Get achieved milestones for current month
            cursor.execute(
                'SELECT milestone_amount FROM milestone_achievements WHERE username = ? AND month_year = ?',
                (username, current_month_year)
            )
            achieved_milestones = {row['milestone_amount'] for row in cursor.fetchall()}

            # Get next standard milestone that hasn't been achieved
            cursor.execute('''
                SELECT * FROM milestone_definitions
                WHERE is_active = 1 AND milestone_amount > ?
                AND milestone_amount NOT IN (
                    SELECT milestone_amount FROM milestone_achievements
                    WHERE username = ? AND month_year = ?
                )
                ORDER BY milestone_amount LIMIT 1
            ''', (current_monthly_wager, username, current_month_year))

            next_milestone = cursor.fetchone()

            # Check for 50k milestones after 100k
            if current_monthly_wager >= 100000:
                next_50k_milestone = ((int(current_monthly_wager) // 50000) + 1) * 50000
                if next_50k_milestone not in achieved_milestones:
                    if not next_milestone or next_50k_milestone < next_milestone['milestone_amount']:
                        conn.close()
                        return {
                            'milestone_amount': next_50k_milestone,
                            'bonus_amount': 50.0,
                            'description': f'$50 bonus for {next_50k_milestone:,} wagered this month',
                            'progress': current_monthly_wager / next_50k_milestone,
                            'remaining': next_50k_milestone - current_monthly_wager
                        }

            if next_milestone:
                conn.close()
                return {
                    'milestone_amount': next_milestone['milestone_amount'],
                    'bonus_amount': next_milestone['bonus_amount'],
                    'description': next_milestone['description'],
                    'progress': current_monthly_wager / next_milestone['milestone_amount'],
                    'remaining': next_milestone['milestone_amount'] - current_monthly_wager
                }

            conn.close()
            return None

        except Exception as e:
            logger.error(f"Error getting next milestone for {username}: {e}")
            return None

async def mark_achievements_notified(username: str, milestone_amounts: List[int]) -> bool:
    """Mark achievements as notified."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            placeholders = ','.join('?' * len(milestone_amounts))
            cursor.execute(f'''
                UPDATE milestone_achievements
                SET notified = 1
                WHERE username = ? AND milestone_amount IN ({placeholders})
            ''', [username] + milestone_amounts)

            conn.commit()
            conn.close()
            return True

        except Exception as e:
            logger.error(f"Error marking achievements as notified for {username}: {e}")
            return False

async def create_milestone_request(username: str, telegram_id: int, milestone_amount: int, bonus_amount: float, month_year: str) -> bool:
    """Create a milestone reward request."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            # Check if request already exists
            cursor.execute('''
                SELECT id FROM milestone_requests
                WHERE username = ? AND milestone_amount = ? AND month_year = ?
            ''', (username, milestone_amount, month_year))

            if cursor.fetchone():
                conn.close()
                return False  # Request already exists

            # Create the request
            cursor.execute('''
                INSERT INTO milestone_requests
                (username, telegram_id, milestone_amount, bonus_amount, month_year)
                VALUES (?, ?, ?, ?, ?)
            ''', (username, telegram_id, milestone_amount, bonus_amount, month_year))

            conn.commit()
            conn.close()

            logger.info(f"Created milestone request for {username}: ${bonus_amount} for {milestone_amount} ({month_year})")
            return True

        except Exception as e:
            logger.error(f"Error creating milestone request for {username}: {e}")
            return False

async def get_pending_milestone_requests() -> List[Dict[str, Any]]:
    """Get all pending milestone requests."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute('''
                SELECT * FROM milestone_requests
                WHERE status = 'pending'
                ORDER BY requested_at ASC
            ''')

            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'id': row['id'],
                    'username': row['username'],
                    'telegram_id': row['telegram_id'],
                    'milestone_amount': row['milestone_amount'],
                    'bonus_amount': row['bonus_amount'],
                    'month_year': row['month_year'],
                    'requested_at': row['requested_at'],
                    'status': row['status']
                })

            conn.close()
            return requests

        except Exception as e:
            logger.error(f"Error getting pending milestone requests: {e}")
            return []

async def get_user_milestone_requests(username: str, month_year: str = None) -> List[Dict[str, Any]]:
    """Get milestone requests for a specific user."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if month_year:
                cursor.execute('''
                    SELECT * FROM milestone_requests
                    WHERE username = ? AND month_year = ?
                    ORDER BY requested_at DESC
                ''', (username, month_year))
            else:
                cursor.execute('''
                    SELECT * FROM milestone_requests
                    WHERE username = ?
                    ORDER BY requested_at DESC
                ''', (username,))

            requests = []
            for row in cursor.fetchall():
                requests.append({
                    'id': row['id'],
                    'milestone_amount': row['milestone_amount'],
                    'bonus_amount': row['bonus_amount'],
                    'month_year': row['month_year'],
                    'requested_at': row['requested_at'],
                    'status': row['status'],
                    'admin_notes': row['admin_notes'],
                    'processed_at': row['processed_at']
                })

            conn.close()
            return requests

        except Exception as e:
            logger.error(f"Error getting milestone requests for {username}: {e}")
            return []

async def update_milestone_request_status(request_id: int, status: str, admin_id: int, admin_notes: str = None) -> bool:
    """Update the status of a milestone request."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE milestone_requests
                SET status = ?, processed_by = ?, processed_at = CURRENT_TIMESTAMP, admin_notes = ?
                WHERE id = ?
            ''', (status, admin_id, admin_notes, request_id))

            success = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if success:
                logger.info(f"Updated milestone request {request_id} to status: {status}")

            return success

        except Exception as e:
            logger.error(f"Error updating milestone request {request_id}: {e}")
            return False

async def unregister_user(telegram_id: int) -> bool:
    """Unregister a user and clean up their data."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            # Get user info before deletion
            cursor.execute('SELECT goated_username FROM users WHERE telegram_id = ?', (telegram_id,))
            user_row = cursor.fetchone()

            if not user_row:
                conn.close()
                return False  # User not found

            username = user_row[0]

            # Delete user record
            cursor.execute('DELETE FROM users WHERE telegram_id = ?', (telegram_id,))

            # Clean up related data
            # Delete milestone achievements
            cursor.execute('DELETE FROM milestone_achievements WHERE username = ?', (username,))

            # Delete milestone requests
            cursor.execute('DELETE FROM milestone_requests WHERE username = ? OR telegram_id = ?', (username, telegram_id))

            # Delete cached wager data
            cursor.execute('DELETE FROM wager_cache WHERE username = ?', (username,))

            # Delete cached leaderboard data
            cursor.execute('DELETE FROM leaderboard_cache WHERE username = ?', (username,))

            # Update command usage logs to anonymize (if table exists)
            try:
                cursor.execute('UPDATE command_usage SET telegram_id = 0 WHERE telegram_id = ?', (telegram_id,))
            except sqlite3.OperationalError:
                # command_usage table doesn't exist, skip
                pass

            conn.commit()
            conn.close()

            logger.info(f"Successfully unregistered user {telegram_id} (username: {username})")
            return True

        except Exception as e:
            logger.error(f"Error unregistering user {telegram_id}: {e}")
            return False

async def get_user_data_summary(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get a summary of user's data before unregistering."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Get user info
            cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
            user_row = cursor.fetchone()

            if not user_row:
                conn.close()
                return None

            username = user_row['goated_username']

            # Count milestone achievements
            cursor.execute('SELECT COUNT(*) FROM milestone_achievements WHERE username = ?', (username,))
            achievement_count = cursor.fetchone()[0]

            # Count milestone requests
            cursor.execute('SELECT COUNT(*) FROM milestone_requests WHERE username = ?', (username,))
            request_count = cursor.fetchone()[0]

            # Get total bonus earned
            cursor.execute('SELECT SUM(bonus_amount) FROM milestone_achievements WHERE username = ?', (username,))
            total_bonus = cursor.fetchone()[0] or 0

            # Count command usage (if table exists)
            try:
                cursor.execute('SELECT COUNT(*) FROM command_usage WHERE telegram_id = ?', (telegram_id,))
                command_count = cursor.fetchone()[0]
            except sqlite3.OperationalError:
                # command_usage table doesn't exist
                command_count = 0

            conn.close()

            return {
                'username': username,
                'registered_at': user_row['created_at'],
                'last_wager_check': user_row['last_wager_check'],
                'achievement_count': achievement_count,
                'request_count': request_count,
                'total_bonus_earned': total_bonus,
                'command_usage_count': command_count
            }

        except Exception as e:
            logger.error(f"Error getting user data summary for {telegram_id}: {e}")
            return None

async def log_command_usage(telegram_id: int, command: str, success: bool = True, error_message: Optional[str] = None) -> bool:
    """Log command usage for analytics."""
    try:
        # Use a shorter timeout and skip if database is busy
        conn = sqlite3.connect(db_manager.db_path, timeout=2.0)
        conn.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode for better concurrency
        cursor = conn.cursor()

        # Check if bot_stats table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='bot_stats'
        """)

        if not cursor.fetchone():
            # Table doesn't exist, skip logging
            conn.close()
            return True

        cursor.execute('''
            INSERT INTO bot_stats (telegram_id, command, success, error_message)
            VALUES (?, ?, ?, ?)
        ''', (telegram_id, command, success, error_message))

        conn.commit()
        conn.close()

        return True

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e) or "database is busy" in str(e):
            # Skip logging if database is locked to avoid blocking operations
            logger.debug(f"Skipping command usage logging due to database lock")
            return True  # Return True to not affect command execution
        else:
            logger.error(f"Error logging command usage: {e}")
            return False
    except Exception as e:
        logger.error(f"Error logging command usage: {e}")
        return False

async def record_daily_wager(username: str, daily_wager: float, total_wager: float, date: str = None) -> bool:
    """Record daily wager amount for a user."""
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')

    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO daily_wager_history
                (username, date, daily_wager, total_wager)
                VALUES (?, ?, ?, ?)
            ''', (username, date, daily_wager, total_wager))

            conn.commit()
            conn.close()

            logger.info(f"Recorded daily wager for {username} on {date}: ${daily_wager}")
            return True

        except Exception as e:
            logger.error(f"Error recording daily wager for {username}: {e}")
            return False

async def calculate_rolling_7_day_wager(username: str) -> float:
    """Calculate rolling 7-day wager total for a user."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            # Get the last 7 days of data
            seven_days_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            today = datetime.now().strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT SUM(daily_wager) as total_7_days
                FROM daily_wager_history
                WHERE username = ? AND date > ? AND date <= ?
            ''', (username, seven_days_ago, today))

            result = cursor.fetchone()
            conn.close()

            if result and result[0] is not None:
                return float(result[0])
            else:
                # If no historical data, fall back to today's wager
                return 0.0

        except Exception as e:
            logger.error(f"Error calculating rolling 7-day wager for {username}: {e}")
            return 0.0

async def get_daily_wager_history(username: str, days: int = 7) -> List[Dict[str, Any]]:
    """Get daily wager history for a user."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

            cursor.execute('''
                SELECT * FROM daily_wager_history
                WHERE username = ? AND date > ?
                ORDER BY date DESC
            ''', (username, start_date))

            rows = cursor.fetchall()
            conn.close()

            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting daily wager history for {username}: {e}")
            return []

async def cleanup_old_daily_wager_data(days_to_keep: int = 30) -> bool:
    """Clean up old daily wager data to prevent database bloat."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days_to_keep)).strftime('%Y-%m-%d')

            cursor.execute('''
                DELETE FROM daily_wager_history
                WHERE date < ?
            ''', (cutoff_date,))

            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old daily wager records")

            return True

        except Exception as e:
            logger.error(f"Error cleaning up old daily wager data: {e}")
            return False

async def get_all_active_users() -> List[Dict[str, Any]]:
    """Get all active users."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE is_active = 1")
            rows = cursor.fetchall()

            conn.close()
            return [dict(row) for row in rows]

        except Exception as e:
            logger.error(f"Error getting all active users: {e}")
            return []

async def get_user_count() -> int:
    """Get total number of active users."""
    async with db_manager._lock:
        try:
            conn = sqlite3.connect(db_manager.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
            count = cursor.fetchone()[0]

            conn.close()
            return count

        except Exception as e:
            logger.error(f"Error getting user count: {e}")
            return 0

# Initialize database on import
async def init_db():
    """Initialize database tables."""
    await db_manager.init_database()

# Run initialization
if __name__ == "__main__":
    asyncio.run(init_db())
