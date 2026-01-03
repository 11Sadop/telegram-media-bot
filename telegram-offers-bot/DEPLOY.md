# Deploy to Railway Guide

## Steps to Deploy

### 1. Create GitHub Account (if you don't have one)
Go to: https://github.com/signup

### 2. Upload Code to GitHub
1. Go to: https://github.com/new
2. Repository name: `telegram-offers-bot`
3. Click "Create repository"
4. Open terminal in the bot folder and run:
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/telegram-offers-bot.git
git push -u origin main
```

### 3. Deploy to Railway
1. Go to: https://railway.app
2. Click "Start a New Project"
3. Select "Deploy from GitHub repo"
4. Connect your GitHub account
5. Select `telegram-offers-bot` repository
6. Click "Deploy Now"

### 4. Add Environment Variables
In Railway dashboard:
1. Click on your project
2. Go to "Variables" tab
3. Add these variables:
   - `BOT_TOKEN` = `8576745210:AAFbIHw4OGVRHfzpRlxw0qXpVsf5_uu4eGA`
   - `CHANNEL_ID` = `@QQXQQ8`

### 5. Done!
The bot will start automatically and run 24/7 for free!
