# Discord Bot Deployment Guide

## 🎯 Deploy Discord Bot Separately

Since running both bots together was causing issues, here's how to deploy the Discord bot on its own Railway service.

## 🚀 Step 1: Create New Railway Service

1. **Go to Railway dashboard**
2. **Click "New Project"**
3. **Connect this same GitHub repository**
4. **Name it**: `goated-discord-bot`

## ⚙️ Step 2: Configure Discord Service

### **Environment Variables**:
```
DISCORD_BOT_TOKEN=your_discord_bot_token_here
DATABASE_URL=sqlite:///goated_bot.db
LOG_LEVEL=INFO
```

### **Procfile** (create new one for Discord service):
```
worker: python main_discord_only.py
```

### **Files to Include**:
- ✅ `main_discord_only.py` (Discord bot entry point)
- ✅ `bot/discord_handlers.py` (Discord commands)
- ✅ `database/` (shared database code)
- ✅ `api/` (shared API code)
- ✅ `utils/` (shared utilities)
- ✅ `requirements.txt` (dependencies)

## 🔧 Step 3: Alternative Deployment Options

### **Option A: Railway (Recommended)**
- **Pros**: Same platform as Telegram bot, easy setup
- **Cons**: Uses another Railway service

### **Option B: Heroku**
- **Pros**: Free tier available
- **Cons**: Different platform

### **Option C: DigitalOcean App Platform**
- **Pros**: Good performance
- **Cons**: Paid service

## 📊 Step 4: Shared Database

Both bots will use their own SQLite databases, but you can sync data by:

### **Option 1: Separate Databases (Simplest)**
- Each bot has its own user database
- Users register separately on each platform

### **Option 2: Shared Database via API**
- Create a simple API service to share user data
- Both bots call the same API

### **Option 3: Cloud Database**
- Use PostgreSQL on Railway/Heroku
- Both bots connect to same database

## 🧪 Step 5: Testing

### **Discord Bot Commands**:
- `!help` - Show commands
- `!register USERNAME` - Register goated.com account
- `!wager` - Check wager statistics
- `!milestones` - View milestone progress

### **Telegram Bot Commands** (unchanged):
- `/help` - Show commands
- `/register USERNAME` - Register goated.com account
- `/wager` - Check wager statistics
- `/milestones` - View milestone progress

## 🎯 Benefits of Separate Deployment

✅ **No threading issues**
✅ **Independent scaling**
✅ **Easier debugging**
✅ **Platform-specific optimizations**
✅ **Separate error handling**
✅ **Independent updates**

## 🔄 Quick Setup Commands

```bash
# For Discord Railway service, set these files:
# 1. Create new Procfile with:
worker: python main_discord_only.py

# 2. Set environment variables:
DISCORD_BOT_TOKEN=your_token
DATABASE_URL=sqlite:///goated_bot.db
LOG_LEVEL=INFO

# 3. Deploy and test!
```

## 📞 Support

If you need help setting up the Discord service:
1. Create the new Railway service
2. Set the environment variables
3. Deploy with `main_discord_only.py`
4. Test the Discord commands

Both bots will work independently and reliably! 🚀
