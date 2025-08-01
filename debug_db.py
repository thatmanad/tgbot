#!/usr/bin/env python3
"""
Debug script to check database structure and test registration.
"""

import sqlite3
import asyncio
import os
import sys

async def check_database():
    """Check database structure and test basic operations."""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), 'goated_bot.db')
    
    print("🔍 Database Debug Information")
    print("=" * 50)
    
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check users table structure
        print("📋 Users Table Structure:")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        
        for col in columns:
            print(f"  - {col[1]} ({col[2]}) {'PRIMARY KEY' if col[5] else ''} {'NOT NULL' if col[3] else 'NULL'}")
        
        # Check if Discord columns exist
        column_names = [col[1] for col in columns]
        discord_support = 'discord_id' in column_names and 'platform' in column_names
        
        print(f"\n🤖 Discord Support: {'✅ Enabled' if discord_support else '❌ Missing'}")
        
        # Check existing users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Total Users: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT telegram_id, discord_id, goated_username, platform FROM users LIMIT 5")
            users = cursor.fetchall()
            print("\n📊 Sample Users:")
            for user in users:
                platform = user[3] if len(user) > 3 else 'telegram'
                print(f"  - {user[2]} ({platform})")
        
        # Test database write
        print("\n🧪 Testing Database Write...")
        try:
            if discord_support:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (discord_id, discord_username, goated_username, platform)
                    VALUES (?, ?, ?, ?)
                ''', (999999999, 'test_user', 'test_goated_user', 'discord'))
            else:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (telegram_id, telegram_username, goated_username)
                    VALUES (?, ?, ?)
                ''', (999999999, 'test_user', 'test_goated_user'))
            
            conn.commit()
            print("✅ Database write test successful")
            
            # Clean up test user
            cursor.execute("DELETE FROM users WHERE goated_username = 'test_goated_user'")
            conn.commit()
            
        except Exception as e:
            print(f"❌ Database write test failed: {e}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        return False

async def test_api():
    """Test API connectivity."""
    print("\n🌐 API Connectivity Test")
    print("=" * 30)
    
    try:
        from api.goated_api import GoatedAPI
        
        api = GoatedAPI()
        try:
            # Test API call
            response = await api._make_request()
            
            if response and response.get('success'):
                players = response.get('data', [])
                print(f"✅ API connected successfully")
                print(f"📊 Found {len(players)} players in UCW47GH affiliate")
                
                if players:
                    sample_player = players[0]
                    print(f"👤 Sample player: {sample_player.get('name', 'Unknown')}")
                
            else:
                print(f"❌ API returned no data or error")
                print(f"Response: {response}")
                
        finally:
            await api.close()
            
    except Exception as e:
        print(f"❌ API test failed: {e}")

async def main():
    """Run all debug checks."""
    print("🚀 GoatedWager Bot Debug Tool")
    print("=" * 50)
    
    # Check database
    db_ok = await check_database()
    
    # Check API
    await test_api()
    
    print("\n" + "=" * 50)
    if db_ok:
        print("✅ Database structure looks good")
        print("\n💡 If registration still fails, check:")
        print("  1. Railway logs for specific error messages")
        print("  2. API connectivity issues")
        print("  3. Username validation problems")
    else:
        print("❌ Database issues detected")
        print("\n🔧 Try running the migration script:")
        print("  python migrate_add_discord_support.py")

if __name__ == "__main__":
    asyncio.run(main())
