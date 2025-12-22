# Free Hosting Options for Guardian Bot

## Option 1: Render.com (Recommended) ⭐

**Pros**: Easy setup, free tier, automatic deployments from GitHub
**Cons**: Sleeps after 15 min inactivity (solvable with UptimeRobot)

### Detailed Setup Steps:

#### 1. Prepare Your Repository
```bash
# Create .gitignore if you haven't
echo "arcadia.db
.env
__pycache__/
*.pyc
.DS_Store" > .gitignore

# Initialize git and push to GitHub
git init
git add .
git commit -m "Initial commit: Guardian of Arcadia bot"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/arcadia-bot.git
git push -u origin main
```

#### 2. Create Render Account
- Go to [render.com](https://render.com)
- Sign up with GitHub (recommended for easy integration)

#### 3. Deploy Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `arcadia-guardian-bot`
   - **Region**: Choose closest to your location
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
   - **Instance Type**: **Free**

#### 4. Add Environment Variable
1. Scroll to **Environment Variables** section
2. Click **"Add Environment Variable"**
3. Add:
   - **Key**: `DISCORD_BOT_TOKEN`
   - **Value**: Your bot token from Discord Developer Portal

4. Click **"Create Web Service"**

#### 5. Monitor Deployment
- Watch the **Logs** tab
- Wait for: `✨ Aetherius | The Eternal Sentry has awakened in Arcadia!`

#### 6. First-Time Setup in Discord
Once deployed:
1. In your Discord server, type: `/sync` (owner only)
2. Wait 1-2 minutes for commands to register
3. Test with `/profile` or `/prophecy`

#### 7. Keep Bot Awake (Optional)
Since Render free tier sleeps after 15 minutes:

**Option A: UptimeRobot (Recommended)**
1. Sign up at [uptimerobot.com](https://uptimerobot.com)
2. Click **"Add New Monitor"**
3. Configure:
   - Monitor Type: HTTP(s)
   - Friendly Name: Arcadia Bot
   - URL: Your Render service URL (e.g., `https://arcadia-guardian-bot.onrender.com`)
   - Monitoring Interval: 5 minutes
4. Save - your bot will stay awake!

**Option B: Cron-Job.org**
- Alternative to UptimeRobot with similar functionality

### Troubleshooting Render

**Bot offline after deploy?**
- Check Logs tab for errors
- Verify `DISCORD_BOT_TOKEN` is correct
- Ensure you used "Web Service" not "Background Worker"

**Commands not appearing?**
- Use `/sync` command in Discord
- Wait 2-5 minutes
- Try in a different channel

**Database errors?**
- Use `/dbcheck` to verify database health
- The bot auto-migrates columns on startup

---

## Option 2: Railway.app

**Pros**: 500 hours/month free, better uptime than Render
**Cons**: Requires credit card for verification (no charges on free tier)

### Steps:
1. Create account at [railway.app](https://railway.app)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Select your repository
4. Add environment variable:
   - Key: `DISCORD_BOT_TOKEN`
   - Value: Your bot token
5. Railway auto-detects Python and deploys
6. No need for keep-alive service!

---

## Option 3: Fly.io

**Pros**: Good free tier (3 VMs free), always-on, fast
**Cons**: Requires CLI setup, more technical

### Steps:
1. Install Fly CLI:
   ```bash
   # macOS/Linux
   curl -L https://fly.io/install.sh | sh
   
   # Windows (PowerShell)
   iwr https://fly.io/install.ps1 -useb | iex
   ```

2. Create `fly.toml` in your project:
   ```toml
   app = "arcadia-guardian-bot"
   
   [build]
   
   [env]
   PORT = "8080"
   
   [[services]]
   internal_port = 8080
   protocol = "tcp"
   
   [[services.ports]]
   handlers = ["http"]
   port = 80
   ```

3. Deploy:
   ```bash
   fly auth login
   fly launch
   fly secrets set DISCORD_BOT_TOKEN=your_token_here
   fly deploy
   ```

---

## Option 4: Replit (Quick Testing)

**Pros**: Web-based IDE, instant deployment, great for testing
**Cons**: Public code (paid for private), less reliable for 24/7

### Steps:
1. Go to [replit.com](https://replit.com)
2. Click **"Create Repl"** → **"Import from GitHub"**
3. Paste your repository URL
4. In Secrets tab (lock icon), add:
   - Key: `DISCORD_BOT_TOKEN`
   - Value: Your bot token
5. Click **"Run"**
6. To keep alive, use UptimeRobot with your Repl URL

---

## Comparison Table

| Platform | Free Hours | Sleep? | Uptime | Setup Difficulty |
|----------|-----------|---------|--------|------------------|
| **Render** | 750/mo | After 15min | Good with monitor | ⭐ Easy |
| **Railway** | 500/mo | No | Excellent | ⭐ Easy |
| **Fly.io** | Always | No | Excellent | ⭐⭐ Medium |
| **Replit** | Always | Sometimes | Fair | ⭐ Very Easy |

---

## Recommended Setup for Guardian of Arcadia

### For Beginners:
**Render.com** + **UptimeRobot**
- Easiest setup
- Completely free
- Reliable with monitoring

### For Best Performance:
**Railway.app**
- No sleep issues
- Better uptime
- Still free (requires card verification)

### For Advanced Users:
**Fly.io**
- Best performance
- Full control
- Scales better

---

## Important Notes

### Database Persistence
- All platforms keep `arcadia.db` between restarts
- **Exception**: Full rebuilds may wipe data
- For production, consider external database (PostgreSQL)

### Bot Permissions
Ensure your bot has these Discord permissions:
- Send Messages
- Embed Links
- Read Message History
- Manage Roles (for rank rewards)
- Add Reactions

### Environment Variables
Only one required: `DISCORD_BOT_TOKEN`

Get it from:
1. [Discord Developer Portal](https://discord.com/developers/applications)
2. Your Application → Bot → Token
3. Click "Reset Token" if needed

---

## After Deployment Checklist

- [ ] Bot shows online in Discord
- [ ] Used `/sync` to register commands
- [ ] Tested `/profile` command
- [ ] Verified XP gaining works
- [ ] Set up UptimeRobot (if using Render)
- [ ] Checked logs for errors

---

**Your Guardian of Arcadia bot is ready to protect the realm 24/7! ⚔️**

For detailed Render-specific instructions, see `RENDER_DEPLOYMENT.md`
