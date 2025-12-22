# Guardian of Arcadia Discord Bot

**Aetherius | The Eternal Sentry** - A mystical Discord bot for the Guardian of Arcadia server, featuring XP systems, lore commands, prophecies, crystal drops, blessing system, and immersive fantasy interactions.

## Features

✨ **Immersive Welcome Messages** - Greet new members with epic fantasy announcements
⚔️ **XP & Leveling System** - Members gain XP and level up through activity
🎖️ **Role Rewards** - Automatic rank promotions tied to your server hierarchy
💎 **Crystal Shard Drops** - Random loot drops in chat for bonus XP (type `!claim` to collect!)
🙏 **Guardian's Blessing** - Members can bless each other for mutual XP rewards
🔮 **Daily Prophecies** - Mystical omens and predictions
📖 **Lore Commands** - Explore the rich history of Arcadia and Aetherius
💬 **Keyword Responses** - Bot responds to fantasy phrases for immersion
🏆 **Leaderboards** - See top Guardians with detailed stats
🗺️ **Daily Quests** - Special challenges for bonus XP
🌟 **Dynamic Level Blessings** - Unique emojis based on milestone levels

## Setup Instructions

### 1. Create a Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and name it "Aetherius" (or any name you prefer)
3. Go to "Bot" tab and click "Add Bot"
4. **IMPORTANT**: Under "Privileged Gateway Intents", enable:
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT
   - ✅ PRESENCE INTENT
5. Copy your bot token (keep it secret!)

### 2. Invite Bot to Your Server

1. Go to "OAuth2" → "URL Generator"
2. Select scopes: `bot` and `applications.commands`
3. Select permissions:
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Manage Roles
   - Add Reactions
4. Copy and visit the generated URL to invite bot

### 3. Configure Environment Variables

Create a `.env` file or set environment variables:
```
DISCORD_BOT_TOKEN=your_token_here
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Bot

```bash
python bot.py
```

## Hosting on Render (Free) - Recommended

1. Create account at [Render.com](https://render.com)
2. Push your code to GitHub
3. Click "New +" → "Web Service"
4. Connect your GitHub repo
5. Configure:
   - **Name**: guardian-arcadia-bot
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
6. Add environment variable:
   - Key: `DISCORD_BOT_TOKEN`
   - Value: Your bot token from Discord Developer Portal
7. Click "Create Web Service"

**Important**: Render free tier sleeps after 15 minutes of inactivity. Use [UptimeRobot](https://uptimerobot.com) to ping your bot URL every 5 minutes to keep it awake!

See `HOSTING_GUIDE.md` for more hosting options (Railway, Fly.io, Replit).

## Customization

### Adjust XP Rates
In `bot.py`, modify:
```python
XP_PER_MESSAGE = 15  # XP awarded per message
XP_COOLDOWN = 60     # Seconds between XP gains
LEVEL_MULTIPLIER = 100  # Affects XP needed for levels
CRYSTAL_DROP_CHANCE = 50  # Messages before crystal drop
```

### Edit Role Rewards
Match your server's exact role names:
```python
ROLE_REWARDS = {
    5: "Hoplite",
    10: "Captain",
    15: "Battalion Leaders",
    20: "Colonel",
    30: "Brigadier",
    50: "General",
}
```

### Welcome Channel
The bot automatically searches for common welcome channel names: `welcome`, `general`, `gatehouse`, `entrance`, `lobby`. If yours is different, edit:
```python
possible_channels = ['welcome', 'general', 'your-channel-name']
```

### Color Scheme
The bot uses cyan/turquoise (`0x00CED1`) and gold (`0xFFD700`) to match your mystical aesthetic. Change in embeds:
```python
color=0x00CED1  # Main cyan color
color=0xFFD700  # Gold for special events
```

### Add More Keywords
Add to the `keywords` dictionary in `on_message`:
```python
keywords = {
    "your phrase": "Bot's response",
    "hail aetherius": "⚡ I am here, eternal and watchful!",
}
```

## Commands

### Slash Commands
- `/profile [member]` - View Guardian stats, XP, crystal shards, and blessings
- `/leaderboard` - Top 10 Guardians by XP
- `/prophecy` - Receive a mystical prophecy from the Arcane
- `/lore [topic]` - Learn about Arcadia's lore (topics: arcadia, guardians, crystals, isles, history, aetherius)
- `/rank` - View all ranks and XP requirements
- `/quest` - Get daily quest for bonus XP
- `/bless @user` - Bestow a blessing on another Guardian (both get +25 XP!)
- `/arcadia` - Server information and features

### Text Commands
- `!claim` - Claim crystal shard drops when they appear (first come, first served!)

## Keyword Responses

The bot responds to these phrases in chat:
- "greetings guardian" → Acknowledgment
- "what is arcadia" → Realm explanation
- "praise the crystal" → Crystal blessing
- "by the floating isles" → Mystical response
- "arcane blessings" → Return blessing
- "guardian's oath" → Recites the oath
- "hail aetherius" → Direct response from Aetherius
- "thank you aetherius" → Gracious reply

## Special Features

### Crystal Shard Drops
Every ~50 messages, a Crystal Shard randomly appears in chat. The first person to type `!claim` receives:
- +100 XP bonus
- +1 Crystal Shard (tracked in profile)

### Guardian's Blessing System
Use `/bless @user` to bless another member. Both the giver and receiver get +25 XP, encouraging kindness and community building!

### Dynamic Level Blessings
Different emojis appear on level-up based on milestones:
- Level 1-4: ✨
- Level 5-9: ⚔️
- Level 10-14: 🛡️
- Level 15-19: 🏆
- Level 20-24: 👑
- Level 25-29: 💎
- Level 30-39: 🔮
- Level 40-49: ⚡
- Level 50+: 🌟

## Database

The bot uses SQLite (`arcadia.db`) to persist:
- User XP, levels, and message counts
- Crystal shards collected
- Blessings given and received
- Daily prophecies

The database file is automatically created on first run.

## Troubleshooting

### Bot doesn't respond to messages
- Check that MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
- Verify bot has permissions in your server

### Welcome messages not sending
- Check channel name matches one of: `welcome`, `general`, `gatehouse`, `entrance`, `lobby`
- Or edit the code to match your channel name

### Slash commands not appearing
- Wait 5-10 minutes for Discord to sync commands
- Try kicking and re-inviting the bot
- Check bot has `applications.commands` scope

### Roles not being assigned
- Ensure role names in code exactly match your server roles
- Bot's role must be higher than roles it assigns
- Bot needs "Manage Roles" permission

## Support

For issues or questions, contact your server administrators or check the bot logs for error messages.

---

*Aetherius watches over you. May the Arcane guide your path through the Floating Isles!* ⚔️✨
