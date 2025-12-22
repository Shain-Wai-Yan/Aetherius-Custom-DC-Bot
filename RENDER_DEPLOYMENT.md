# 🚀 Deploying Aetherius to Render (Free Tier)

This guide will help you deploy your Guardian of Arcadia bot to Render's free tier hosting.

## Prerequisites

1. **GitHub Account** - You'll need to push your bot code to GitHub
2. **Render Account** - Sign up at [render.com](https://render.com) (free)
3. **Discord Bot Token** - From Discord Developer Portal

---

## Step 1: Prepare Your Code for GitHub

1. **Create a `.gitignore` file** in your project root:
```
arcadia.db
.env
__pycache__/
*.pyc
.DS_Store
```

2. **Initialize Git and push to GitHub**:
```bash
git init
git add .
git commit -m "Initial commit: Guardian of Arcadia bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/arcadia-bot.git
git push -u origin main
```

---

## Step 2: Set Up Render

1. **Go to [Render Dashboard](https://dashboard.render.com/)**

2. **Click "New +" and select "Web Service"**

3. **Connect your GitHub repository**
   - Click "Connect account" if you haven't linked GitHub yet
   - Select your `arcadia-bot` repository

4. **Configure the Web Service**:
   - **Name**: `arcadia-guardian-bot` (or any name you prefer)
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: `Free`

---

## Step 3: Add Environment Variables

In the Render dashboard for your service:

1. Scroll down to **"Environment Variables"**

2. Click **"Add Environment Variable"**

3. Add your Discord bot token:
   - **Key**: `DISCORD_BOT_TOKEN`
   - **Value**: `YOUR_DISCORD_BOT_TOKEN_HERE`

4. Click **"Save Changes"**

---

## Step 4: Deploy

1. Click **"Create Web Service"** at the bottom

2. Render will automatically:
   - Clone your repository
   - Install dependencies from `requirements.txt`
   - Start your bot with `python bot.py`

3. **Monitor the deployment** in the Logs tab

4. Look for this message in the logs:
```
✨ Aetherius | The Eternal Sentry has awakened in Arcadia!
```

---

## Important Notes for Render Free Tier

### ⚠️ Free Tier Limitations

1. **Automatic Sleep**: Your bot will sleep after 15 minutes of inactivity
   - **Solution**: Your bot will wake up when someone sends a message (with a small delay)
   - **Alternative**: Use a service like UptimeRobot to ping your bot every 14 minutes

2. **750 Hours/Month Free**: Enough for 24/7 operation on one service

3. **Database Persistence**: 
   - The `arcadia.db` file will persist between deploys
   - **But**: If Render rebuilds from scratch, you may lose data
   - **Recommendation**: For production, upgrade to a persistent disk or use external database

### 🔄 Keeping Your Bot Awake (Optional)

To prevent your bot from sleeping:

1. **Add a health check endpoint** to your bot (optional, requires code modification)

2. **Use UptimeRobot** (free service):
   - Sign up at [uptimerobot.com](https://uptimerobot.com)
   - Create a new monitor
   - Set it to ping your Render URL every 14 minutes

---

## Step 5: First-Time Setup in Discord

After deploying, in your Discord server:

1. **Sync the slash commands** (one-time setup):
   - Type `/sync` (only server owner can do this)
   - This registers all slash commands with Discord

2. **Check database health**:
   - Type `/dbcheck` to verify everything is working

3. **Test the bot**:
   - Send some messages to earn XP
   - Try `/profile` to see your stats
   - Try `/prophecy` for a mystical message

---

## Troubleshooting

### Bot Not Responding

1. Check Render logs for errors
2. Verify `DISCORD_BOT_TOKEN` is set correctly
3. Ensure bot has proper permissions in your Discord server:
   - `Send Messages`
   - `Embed Links`
   - `Manage Roles` (for role rewards)
   - `Read Message History`

### Database Errors

If you see column errors like "no such column: crystal_shards":

1. The migration code should handle this automatically
2. If not, check logs for migration messages
3. As a last resort, delete `arcadia.db` and restart (loses all data)

### Commands Not Showing

1. Use `/sync` command (owner only)
2. Wait a few minutes for Discord to update
3. Try kicking and re-inviting the bot

---

## Monitoring Your Bot

### View Logs
- Go to your Render dashboard
- Click on your service
- Click "Logs" tab to see real-time output

### Check Status
- The dashboard shows if your service is running
- Green = Running, Yellow = Deploying, Red = Error

---

## Updating Your Bot

When you make changes:

1. Commit and push to GitHub:
```bash
git add .
git commit -m "Update bot features"
git push
```

2. Render will **automatically redeploy** your bot

3. Monitor the deployment in the Logs tab

---

## Cost Optimization Tips

1. **Don't sync commands on every startup** ✅ (already implemented)
2. **Use efficient database queries** ✅ (already optimized)
3. **Minimize external API calls**
4. **Consider upgrading to paid tier** ($7/month) for:
   - No sleep
   - Persistent disk
   - Better performance

---

## Getting Help

If you run into issues:

1. Check Render logs first
2. Verify environment variables are set
3. Test locally before deploying
4. Check Discord bot permissions

---

## Quick Reference

| Action | Command |
|--------|---------|
| Deploy updates | `git push` to main branch |
| View logs | Render Dashboard → Your Service → Logs |
| Restart bot | Render Dashboard → Manual Deploy → "Clear build cache & deploy" |
| Sync commands | `/sync` in Discord (owner only) |
| Check database | `/dbcheck` in Discord (owner only) |

---

**You're all set! Your Guardian of Arcadia bot is now live and protecting the realm! ⚔️**
