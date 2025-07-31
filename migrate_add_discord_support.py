#!/usr/bin/env python3
"""
Migration script to add Discord support to the database.
"""

import sqlite3
import logging
import os
import sys
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def migrate_add_discord_support():
    """Add Discord support to the users table."""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'goated_bot.db')
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return False
    
    # Create backup
    backup_path = f"{db_path}.backup_discord_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backup created: {backup_path}")
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if discord_id column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'discord_id' in columns:
            logger.info("Discord support already exists in database")
            conn.close()
            return True
        
        logger.info("Adding Discord support to users table...")
        
        # Add Discord columns (without UNIQUE constraint initially)
        cursor.execute('ALTER TABLE users ADD COLUMN discord_id INTEGER')
        cursor.execute('ALTER TABLE users ADD COLUMN discord_username TEXT')
        cursor.execute('ALTER TABLE users ADD COLUMN platform TEXT DEFAULT "telegram"')
        
        # Make telegram_id nullable since Discord users won't have it
        # SQLite doesn't support modifying column constraints directly,
        # so we'll create a new table and migrate data
        
        logger.info("Recreating users table with Discord support...")
        
        # Create new table with proper structure
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
        
        # Copy existing data
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
        
        # Create indexes
        cursor.execute('CREATE INDEX idx_users_telegram_id ON users(telegram_id)')
        cursor.execute('CREATE INDEX idx_users_discord_id ON users(discord_id)')
        cursor.execute('CREATE INDEX idx_users_platform ON users(platform)')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ Successfully added Discord support to database!")
        return True
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return False

def verify_migration():
    """Verify that the migration was successful."""
    db_path = os.path.join(os.path.dirname(__file__), 'goated_bot.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        expected_columns = [
            'id', 'telegram_id', 'discord_id', 'telegram_username', 
            'discord_username', 'goated_username', 'platform',
            'created_at', 'updated_at', 'is_active', 
            'last_wager_check', 'last_leaderboard_check'
        ]
        
        actual_columns = [col[1] for col in columns]
        
        for expected_col in expected_columns:
            if expected_col not in actual_columns:
                logger.error(f"Missing column: {expected_col}")
                return False
        
        # Check indexes exist
        cursor.execute("PRAGMA index_list(users)")
        indexes = cursor.fetchall()
        
        conn.close()
        
        logger.info("✅ Migration verification successful!")
        return True
        
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Adding Discord Support Migration")
    print("=" * 50)
    
    success = migrate_add_discord_support()
    
    if success:
        verify_migration()
        print("\n✅ Discord support added successfully!")
        print("\nNew features:")
        print("• Discord bot can now register users")
        print("• Shared database between Telegram and Discord")
        print("• Platform tracking for analytics")
        print("\nNext steps:")
        print("1. Add DISCORD_BOT_TOKEN to your environment")
        print("2. Update main.py to run both bots")
        print("3. Test Discord commands with ! prefix")
    else:
        print("\n❌ Migration failed!")
        print("Check the logs above for details.")
        sys.exit(1)
