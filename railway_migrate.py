#!/usr/bin/env python3
"""
Railway migration script to ensure Discord support is added.
This will run automatically when the bot starts.
"""

import sqlite3
import logging
import os
import asyncio

logger = logging.getLogger(__name__)

async def ensure_discord_support():
    """Ensure Discord support is added to the database."""
    
    db_path = os.path.join(os.path.dirname(__file__), 'goated_bot.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if discord_id column exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'discord_id' not in columns:
            logger.info("Adding Discord support to database...")
            
            # Create new table with Discord support
            cursor.execute('''
                CREATE TABLE users_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_id INTEGER UNIQUE,
                    discord_id INTEGER UNIQUE,
                    telegram_username TEXT,
                    discord_username TEXT,
                    goated_username TEXT UNIQUE NOT NULL,
                    platform TEXT DEFAULT 'telegram',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    last_wager_check TIMESTAMP,
                    last_leaderboard_check TIMESTAMP
                )
            ''')
            
            # Copy existing data if users table exists
            try:
                cursor.execute('''
                    INSERT INTO users_new (
                        telegram_id, telegram_username, goated_username, 
                        platform, created_at, updated_at, is_active, 
                        last_wager_check, last_leaderboard_check
                    )
                    SELECT 
                        telegram_id, telegram_username, goated_username,
                        'telegram', created_at, updated_at, is_active,
                        last_wager_check, last_leaderboard_check
                    FROM users
                ''')
                
                # Drop old table and rename new one
                cursor.execute('DROP TABLE users')
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                logger.info("✅ Successfully migrated existing users to new table")
                
            except sqlite3.OperationalError:
                # users table doesn't exist, just rename the new table
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                logger.info("✅ Created new users table with Discord support")
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_discord_id ON users(discord_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_platform ON users(platform)')
            
            conn.commit()
            logger.info("✅ Discord support added successfully")
        else:
            logger.info("✅ Discord support already exists")
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to ensure Discord support: {e}")
        return False

if __name__ == "__main__":
    # For testing
    logging.basicConfig(level=logging.INFO)
    asyncio.run(ensure_discord_support())
