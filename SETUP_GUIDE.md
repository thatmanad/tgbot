# Goated Wager Tracker Bot - Setup Guide

This guide will walk you through setting up your Telegram bot for tracking goated.com affiliate wagers and leaderboard positions.

## Prerequisites

- Python 3.8 or higher
- A Telegram account
- Access to goated.com affiliate API (you'll need to research the actual API endpoints)

## Step 1: Create Your Telegram Bot

1. **Start a chat with BotFather**
   - Open Telegram and search for `@BotFather`
   - Start a conversation with the official BotFather bot

2. **Create a new bot**
   ```
   /newbot
   ```

3. **Choose a name for your bot**
   - Example: "Goated Wager Tracker"

4. **Choose a username for your bot**
   - Must end with "bot"
   - Example: "goated_wager_tracker_bot"

5. **Save your bot token**
   - BotFather will give you a token like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`
   - Keep this token secure and private!

## Step 2: Install Dependencies

1. **Navigate to the project directory**
   ```bash
   cd Documents/augment-projects/goatedwager
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Step 3: Configure Environment

1. **Copy the environment template**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file**
   Open `.env` in a text editor and update:
   ```
   TELEGRAM_BOT_TOKEN=your_actual_bot_token_here
   GOATED_API_URL=https://apis.goated.com
   GOATED_API_KEY=your_api_key_if_required
   ```

## Step 4: API Configuration (Already Done!)

**GOOD NEWS**: The bot is already configured to work with the real goated.com API!

The bot uses the endpoint: `https://apis.goated.com/user/affiliate/referral-leaderboard/{AFFILIATE_ID}`

This endpoint provides:
- Affiliate validation (if the ID exists, it returns data)
- Wager statistics for all referrals under the affiliate
- Leaderboard-style data showing top performers

**No additional API research needed** - the bot is ready to use!

## Step 5: Initialize the Database

Run the setup script to create the database:
```bash
python setup.py
```

## Step 6: Test Your Setup

Run the test script to verify everything is working:
```bash
python test_bot.py
```

## Step 7: Start Your Bot

Once everything is configured:
```bash
python main.py
```

Your bot should now be running and ready to accept commands!

## Bot Commands

Users can interact with your bot using these commands:

- `/start` - Welcome message and introduction
- `/register YOUR_AFFILIATE_ID` - Register affiliate account
- `/wager` - Check wager statistics
- `/leaderboard` - Check leaderboard position
- `/help` - Get help information

## Customization

### Modifying Commands

Edit `bot/handlers.py` to customize:
- Welcome messages
- Command responses
- Error messages
- Data formatting

### Adding Features

You can extend the bot by:
- Adding more commands in `bot/handlers.py`
- Creating scheduled updates
- Adding notification features
- Implementing admin commands

### Database Schema

The bot uses SQLite with these tables:
- `users` - Registered users and their affiliate IDs
- `wager_cache` - Cached wager data to reduce API calls
- `leaderboard_cache` - Cached leaderboard data
- `bot_stats` - Usage statistics and logging

## Deployment

### Local Development
- Run `python main.py` to start the bot locally
- Use Ctrl+C to stop the bot

### Production Deployment
Consider using:
- **VPS/Cloud Server**: Deploy on DigitalOcean, AWS, etc.
- **Process Manager**: Use PM2 or systemd to keep the bot running
- **Monitoring**: Set up logging and error monitoring
- **Backup**: Regular database backups

### Example PM2 Configuration
```bash
pm2 start main.py --name goated-bot --interpreter python3
pm2 save
pm2 startup
```

## Troubleshooting

### Common Issues

1. **Bot Token Error**
   - Verify your token in the .env file
   - Make sure there are no extra spaces

2. **API Connection Issues**
   - Check if goated.com API is accessible
   - Verify API endpoints and authentication

3. **Database Errors**
   - Run `python setup.py` to reinitialize
   - Check file permissions

4. **Import Errors**
   - Ensure all dependencies are installed
   - Check Python version compatibility

### Getting Help

1. Check the logs in `bot.log`
2. Run `python test_bot.py` to diagnose issues
3. Review the error messages in the console

## Security Notes

- Never share your bot token publicly
- Keep your API keys secure
- Consider rate limiting for production use
- Regularly update dependencies
- Monitor for unusual activity

## Next Steps

After your bot is running:
1. Test all commands thoroughly
2. Invite your affiliates to use the bot
3. Monitor usage and performance
4. Consider adding more features based on user feedback

Good luck with your Goated Wager Tracker Bot! 🎰🤖
