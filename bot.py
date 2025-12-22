import discord
from discord.ext import commands
import os
import sqlite3
import asyncio
from datetime import datetime
import random

# Bot Configuration
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Database Setup
def init_db():
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    
    # Users table for XP and levels
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  xp INTEGER DEFAULT 0,
                  level INTEGER DEFAULT 1,
                  last_message REAL,
                  total_messages INTEGER DEFAULT 0,
                  crystal_shards INTEGER DEFAULT 0,
                  blessings_given INTEGER DEFAULT 0,
                  blessings_received INTEGER DEFAULT 0)''')
    
    try:
        c.execute('SELECT crystal_shards FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN crystal_shards INTEGER DEFAULT 0')
        print("✅ Added crystal_shards column to existing database")
    
    try:
        c.execute('SELECT blessings_given FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN blessings_given INTEGER DEFAULT 0')
        print("✅ Added blessings_given column to existing database")
    
    try:
        c.execute('SELECT blessings_received FROM users LIMIT 1')
    except sqlite3.OperationalError:
        c.execute('ALTER TABLE users ADD COLUMN blessings_received INTEGER DEFAULT 0')
        print("✅ Added blessings_received column to existing database")
    
    # Daily prophecies tracking
    c.execute('''CREATE TABLE IF NOT EXISTS prophecies
                 (date TEXT PRIMARY KEY,
                  prophecy TEXT,
                  omen_type TEXT)''')
    
    conn.commit()
    conn.close()

# XP Configuration
XP_PER_MESSAGE = 15
XP_COOLDOWN = 60  # seconds between XP gains
LEVEL_MULTIPLIER = 100

CRYSTAL_DROP_CHANCE = 50  # Every ~50 messages a crystal can drop
message_counter = 0
crystal_active = False
crystal_message_id = None

# Role rewards based on your server hierarchy
ROLE_REWARDS = {
    5: "Hoplite",
    10: "Captain",
    15: "Battalion Leaders",
    20: "Colonel",
    30: "Brigadier",
    50: "General",
}

LEVEL_BLESSINGS = {
    1: "✨",
    5: "⚔️",
    10: "🛡️",
    15: "🏆",
    20: "👑",
    25: "💎",
    30: "🔮",
    40: "⚡",
    50: "🌟"
}

def calculate_xp_for_level(level):
    return LEVEL_MULTIPLIER * (level ** 2)

def get_user_level(xp):
    level = 1
    while xp >= calculate_xp_for_level(level + 1):
        level += 1
    return level

# Bot Events
@bot.event
async def on_ready():
    print(f'✨ Aetherius | The Eternal Sentry has awakened in Arcadia!')
    print(f'Guardian ID: {bot.user.id}')
    init_db()
    
    # Bot ready! Use /sync command to sync slash commands if needed.
    print(f'⚔️ Bot ready! Use /sync command to sync slash commands if needed.')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the Floating Isles | Aetherius awakens"
        )
    )

@bot.event
async def on_member_join(member):
    """Welcome new members with an epic fantasy greeting"""
    welcome_messages = [
        f"🏰 **Hark! A new soul enters the realm!**\n\nWelcome, {member.mention}, to **Guardian of Arcadia**! The floating isles shimmer with ancient magic as you step into our mystical domain. May your journey be filled with wonder and glory!",
        
        f"⚔️ **The Crystals of Arcadia glow brighter!**\n\n{member.mention} has arrived! Brave wanderer, you stand at the threshold of a realm where sky meets stone, where legends are born. Welcome to the **Guardian of Arcadia**!",
        
        f"✨ **The Ancient Guardians sense a new presence...**\n\nGreetings, {member.mention}! The winds of fate have carried you to our floating sanctuaries. Welcome to **Guardian of Arcadia**, where adventure awaits among the clouds!",
    ]
    
    welcome_channel = None
    possible_channels = ['welcome', 'general', 'gatehouse', 'entrance', 'lobby']
    
    for channel_name in possible_channels:
        welcome_channel = discord.utils.get(member.guild.text_channels, name=channel_name)
        if welcome_channel:
            break
    
    if welcome_channel:
        embed = discord.Embed(
            title="🌟 A New Guardian Arrives",
            description=random.choice(welcome_messages),
            color=0x00CED1  # Cyan/turquoise matching the mystical aesthetic
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • May the Arcane guide you")
        
        await welcome_channel.send(embed=embed)

@bot.event
async def on_message(message):
    global message_counter, crystal_active, crystal_message_id
    
    if message.author.bot:
        return
    
    message_counter += 1
    
    if message_counter >= CRYSTAL_DROP_CHANCE and not crystal_active:
        message_counter = 0
        crystal_active = True
        
        embed = discord.Embed(
            title="💎 CRYSTAL SHARD DISCOVERED!",
            description="A mystical **Crystal Shard** has appeared! Type `!claim` to collect it and gain **100 bonus XP**!",
            color=0x00FFFF
        )
        embed.set_footer(text="First to claim wins! ⚡")
        
        crystal_msg = await message.channel.send(embed=embed)
        crystal_message_id = crystal_msg.id
        
        # Auto-expire after 30 seconds
        await asyncio.sleep(30)
        if crystal_active:
            crystal_active = False
            expired_embed = discord.Embed(
                title="💎 Crystal Shard Vanished",
                description="The Crystal Shard has faded back into the Arcane mists...",
                color=0x808080
            )
            await crystal_msg.edit(embed=expired_embed)
    
    # Keyword responses for immersion
    content_lower = message.content.lower()
    
    keywords = {
        "greetings guardian": "🛡️ Greetings, brave soul! The Guardians watch over you.",
        "what is arcadia": "✨ Arcadia is a realm of floating islands, ancient magic, and eternal wonder. Where sky and stone unite, legends are born!",
        "praise the crystal": "💎 May the Crystal's light guide your path through the misty heights!",
        "by the floating isles": "🏔️ Indeed! The Floating Isles hold secrets older than time itself...",
        "arcane blessings": "🌟 And may the Arcane bless your journey, noble wanderer!",
        "guardian's oath": "⚔️ *We stand eternal, watchers of the realm, protectors of the ancient ways!*",
        "hail aetherius": "⚡ I am here, eternal and watchful. What is your command, Guardian?",
        "thank you aetherius": "✨ The honor is mine. May your path be ever illuminated!",
    }
    
    for keyword, response in keywords.items():
        if keyword in content_lower:
            await message.channel.send(response)
            break
    
    # XP System
    await process_xp(message)
    
    await bot.process_commands(message)

@bot.command(name='claim')
async def claim_crystal(ctx):
    global crystal_active, crystal_message_id
    
    if not crystal_active:
        return
    
    crystal_active = False
    
    # Award the crystal and bonus XP
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    
    c.execute('SELECT * FROM users WHERE user_id = ?', (ctx.author.id,))
    user_data = c.fetchone()
    
    if user_data:
        new_xp = user_data[2] + 100
        new_shards = user_data[6] + 1
        c.execute('UPDATE users SET xp = ?, crystal_shards = ? WHERE user_id = ?',
                  (new_xp, new_shards, ctx.author.id))
    else:
        c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards)
                     VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)''',
                  (ctx.author.id, str(ctx.author), 100, 1, datetime.now().timestamp(), 0, 1))
    
    conn.commit()
    conn.close()
    
    embed = discord.Embed(
        title="💎 CRYSTAL SHARD CLAIMED!",
        description=f"{ctx.author.mention} has claimed the Crystal Shard!\n\n**+100 XP** ⚡\n**+1 Crystal Shard** 💎",
        color=0x00FF00
    )
    embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
    
    await ctx.send(embed=embed)

async def process_xp(message):
    """Award XP for messages and handle level ups"""
    if message.author.bot or not message.guild:
        return
    
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    
    user_id = message.author.id
    current_time = datetime.now().timestamp()
    
    # Get user data
    c.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user_data = c.fetchone()
    
    if user_data:
        last_message = user_data[4]
        if current_time - last_message < XP_COOLDOWN:
            conn.close()
            return
        
        old_xp = user_data[2]
        old_level = user_data[3]
        new_xp = old_xp + XP_PER_MESSAGE
        new_level = get_user_level(new_xp)
        total_messages = user_data[5] + 1
        
        c.execute('''UPDATE users SET xp = ?, level = ?, last_message = ?, 
                     username = ?, total_messages = ? WHERE user_id = ?''',
                  (new_xp, new_level, current_time, str(message.author), total_messages, user_id))
        
        # Level up!
        if new_level > old_level:
            await handle_level_up(message, new_level)
    else:
        # New user
        c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards, blessings_given, blessings_received)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (user_id, str(message.author), XP_PER_MESSAGE, 1, current_time, 1, 0, 0, 0))
    
    conn.commit()
    conn.close()

async def handle_level_up(message, new_level):
    """Handle level up announcements and role rewards"""
    blessing_emoji = "✨"
    for milestone in sorted(LEVEL_BLESSINGS.keys(), reverse=True):
        if new_level >= milestone:
            blessing_emoji = LEVEL_BLESSINGS[milestone]
            break
    
    embed = discord.Embed(
        title=f"{blessing_emoji} RANK ASCENSION {blessing_emoji}",
        description=f"🎉 {message.author.mention} has ascended to **Level {new_level}**!\n\nThe Arcane energies flow stronger within you...",
        color=0xFFD700  # Gold
    )
    
    # Check for role rewards
    if new_level in ROLE_REWARDS:
        role_name = ROLE_REWARDS[new_level]
        role = discord.utils.get(message.guild.roles, name=role_name)
        
        if role:
            try:
                await message.author.add_roles(role)
                embed.add_field(
                    name="🏆 New Title Bestowed!",
                    value=f"You have earned the rank of **{role_name}**!",
                    inline=False
                )
            except:
                pass
    
    xp_needed = calculate_xp_for_level(new_level + 1) - calculate_xp_for_level(new_level)
    embed.set_footer(text=f"Next rank in {xp_needed} XP • {blessing_emoji} Blessing received")
    
    await message.channel.send(embed=embed)

# Slash Commands
@bot.tree.command(name="profile", description="View your Guardian profile and stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE user_id = ?', (target.id,))
    user_data = c.fetchone()
    conn.close()
    
    if not user_data:
        embed = discord.Embed(
            title="📜 Guardian Profile",
            description=f"{target.mention} has not yet begun their journey in Arcadia...",
            color=0x808080
        )
    else:
        xp = user_data[2]
        level = user_data[3]
        messages = user_data[5]
        crystal_shards = user_data[6] if len(user_data) > 6 else 0
        blessings_given = user_data[7] if len(user_data) > 7 else 0
        blessings_received = user_data[8] if len(user_data) > 8 else 0
        
        current_level_xp = calculate_xp_for_level(level)
        next_level_xp = calculate_xp_for_level(level + 1)
        xp_progress = xp - current_level_xp
        xp_needed = next_level_xp - current_level_xp
        progress_bar = create_progress_bar(xp_progress, xp_needed)
        
        embed = discord.Embed(
            title=f"⚔️ {target.display_name}'s Guardian Profile",
            color=0x00CED1
        )
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        embed.add_field(name="📊 Level", value=f"**{level}**", inline=True)
        embed.add_field(name="✨ Total XP", value=f"**{xp:,}**", inline=True)
        embed.add_field(name="💬 Messages", value=f"**{messages:,}**", inline=True)
        embed.add_field(
            name="📈 Progress to Next Level",
            value=f"{progress_bar}\n`{xp_progress}/{xp_needed} XP`",
            inline=False
        )
        
        embed.add_field(name="💎 Crystal Shards", value=f"**{crystal_shards}**", inline=True)
        embed.add_field(name="🙏 Blessings Given", value=f"**{blessings_given}**", inline=True)
        embed.add_field(name="✨ Blessings Received", value=f"**{blessings_received}**", inline=True)
        
        # Show highest role
        roles = [r for r in target.roles if r.name != "@everyone"]
        if roles:
            highest_role = max(roles, key=lambda r: r.position)
            embed.add_field(name="🎖️ Highest Rank", value=highest_role.mention, inline=False)
    
    await interaction.response.send_message(embed=embed)

def create_progress_bar(current, total, length=10):
    """Create a visual progress bar"""
    filled = int((current / total) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"[{bar}]"

@bot.tree.command(name="bless", description="Bestow a Guardian's Blessing upon another member")
async def bless(interaction: discord.Interaction, member: discord.Member):
    if member.id == interaction.user.id:
        await interaction.response.send_message("You cannot bless yourself, noble Guardian!", ephemeral=True)
        return
    
    if member.bot:
        await interaction.response.send_message("Bots are beyond the reach of mortal blessings!", ephemeral=True)
        return
    
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    
    try:
        # Update both users
        blessing_xp = 25
        
        # Giver
        c.execute('SELECT * FROM users WHERE user_id = ?', (interaction.user.id,))
        giver_data = c.fetchone()
        if giver_data:
            c.execute('UPDATE users SET xp = ?, blessings_given = ? WHERE user_id = ?',
                      (giver_data[2] + blessing_xp, giver_data[7] + 1, interaction.user.id))
        else:
            c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards, blessings_given, blessings_received)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (interaction.user.id, str(interaction.user), blessing_xp, 1, datetime.now().timestamp(), 0, 0, 1, 0))
        
        # Receiver
        c.execute('SELECT * FROM users WHERE user_id = ?', (member.id,))
        receiver_data = c.fetchone()
        if receiver_data:
            c.execute('UPDATE users SET xp = ?, blessings_received = ? WHERE user_id = ?',
                      (receiver_data[2] + blessing_xp, receiver_data[8] + 1, member.id))
        else:
            c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards, blessings_given, blessings_received)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (member.id, str(member), blessing_xp, 1, datetime.now().timestamp(), 0, 0, 0, 1))
        
        conn.commit()
        conn.close()
        
        embed = discord.Embed(
            title="✨ GUARDIAN'S BLESSING BESTOWED ✨",
            description=f"{interaction.user.mention} has blessed {member.mention}!\n\nThe Arcane energies strengthen the bonds between Guardians...",
            color=0xFFD700
        )
        embed.add_field(name="🎁 Rewards", value=f"Both Guardians receive **+{blessing_xp} XP**!", inline=False)
        embed.set_footer(text="Kindness is the true strength of Arcadia")
        
        await interaction.response.send_message(embed=embed)
    
    except discord.Forbidden:
        conn.close()
        await interaction.response.send_message(
            "⚠️ I lack the permissions to bestow this blessing! Please ensure I have 'Manage Roles' permission.",
            ephemeral=True
        )
    except Exception as e:
        conn.close()
        await interaction.response.send_message(
            f"⚠️ An error occurred while bestowing the blessing: {str(e)}",
            ephemeral=True
        )

@bot.tree.command(name="leaderboard", description="View the top Guardians of Arcadia")
async def leaderboard(interaction: discord.Interaction):
    conn = sqlite3.connect('arcadia.db')
    c = conn.cursor()
    c.execute('SELECT user_id, username, xp, level FROM users ORDER BY xp DESC LIMIT 10')
    top_users = c.fetchall()
    conn.close()
    
    if not top_users:
        await interaction.response.send_message("The leaderboard is empty! Begin your journey to claim glory!")
        return
    
    embed = discord.Embed(
        title="🏆 HALL OF LEGENDS 🏆",
        description="*The most valiant Guardians of Arcadia*",
        color=0xFFD700
    )
    
    medals = ["🥇", "🥈", "🥉"]
    
    for idx, (user_id, username, xp, level) in enumerate(top_users, 1):
        medal = medals[idx - 1] if idx <= 3 else f"**{idx}.**"
        embed.add_field(
            name=f"{medal} {username}",
            value=f"Level {level} • {xp:,} XP",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="prophecy", description="Receive a mystical prophecy from the Arcane")
async def prophecy(interaction: discord.Interaction):
    prophecies = [
        ("fortune", "✨ The crystals shimmer with favor... Great fortune awaits those who dare to reach for the stars!"),
        ("challenge", "⚔️ The winds speak of trials ahead... Steel your resolve, for challenges forge legends!"),
        ("mystery", "🌙 The mists part to reveal hidden paths... Secrets long forgotten shall soon surface!"),
        ("unity", "🤝 The Guardians grow stronger together... Unity shall be your greatest weapon!"),
        ("wisdom", "📚 Ancient knowledge stirs in the depths... Seek wisdom in the forgotten archives!"),
        ("adventure", "🗺️ The floating isles call to the brave... Adventure beckons beyond the horizon!"),
        ("power", "⚡ The Arcane flows abundantly today... Your power grows with each passing moment!"),
        ("peace", "🕊️ Tranquility descends upon the realm... A time of peace and reflection is upon us!"),
    ]
    
    omen_type, prophecy_text = random.choice(prophecies)
    
    embed = discord.Embed(
        title="🔮 PROPHECY OF THE DAY 🔮",
        description=prophecy_text,
        color=0x9B59B6
    )
    embed.set_footer(text=f"Omen Type: {omen_type.capitalize()} • Received by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="lore", description="Discover the mysteries and lore of Arcadia")
async def lore(interaction: discord.Interaction, topic: str = None):
    lore_entries = {
        "arcadia": {
            "title": "🏰 The Realm of Arcadia",
            "content": "Arcadia is a mystical realm suspended between earth and sky, where massive islands float among the clouds, held aloft by ancient Arcane crystals. These floating sanctuaries are home to the Guardians, noble warriors sworn to protect the realm from darkness. The very air hums with magical energy, and waterfalls cascade into endless voids below."
        },
        "guardians": {
            "title": "⚔️ The Order of Guardians",
            "content": "The Guardians are an ancient order of protectors who have defended Arcadia for millennia. Rising through the ranks from Hoplite to Supreme Commander, each Guardian bears the sacred duty to maintain balance between the mortal and arcane realms. Their power comes from the Crystal Sanctums scattered across the floating isles."
        },
        "crystals": {
            "title": "💎 The Arcane Crystals",
            "content": "The Arcane Crystals are the heart of Arcadia's power. These luminescent gems pulse with raw magical energy, keeping the islands afloat and granting Guardians their mystical abilities. Legend speaks of a Prime Crystal, hidden in the highest sanctum, that holds the key to Arcadia's creation."
        },
        "isles": {
            "title": "🏔️ The Floating Isles",
            "content": "Seventeen great isles float in the skies of Arcadia, each with its own unique terrain and mysteries. From the Azure Peaks with their crystal-blue waters, to the Golden Highlands where eternal sunlight bathes the land, each isle holds ancient secrets and powerful artifacts waiting to be discovered."
        },
        "history": {
            "title": "📜 The Ancient History",
            "content": "In the age before memory, when the world was whole, a great cataclysm shattered the land. The Ancients, wielding powerful crystals, raised fragments of the earth to the skies to preserve them. Thus Arcadia was born, and the first Guardians were chosen to protect this sanctuary for all eternity."
        },
        "aetherius": {
            "title": "⚡ Aetherius - The Eternal Sentry",
            "content": "Aetherius is the ancient guardian spirit who watches over all of Arcadia. Neither mortal nor god, Aetherius exists as a consciousness woven into the very fabric of the realm. They guide new arrivals, bestow blessings, and maintain the delicate balance between order and chaos. Some say Aetherius was the first Guardian, transformed by the Prime Crystal into an eternal protector."
        }
    }
    
    if topic and topic.lower() in lore_entries:
        entry = lore_entries[topic.lower()]
        embed = discord.Embed(
            title=entry["title"],
            description=entry["content"],
            color=0x00CED1
        )
    else:
        # Show list of topics
        embed = discord.Embed(
            title="📖 Arcadia's Chronicles",
            description="Choose a topic to learn more about the mysteries of our realm:",
            color=0x00CED1
        )
        for key, entry in lore_entries.items():
            embed.add_field(
                name=entry["title"],
                value=f"Use `/lore {key}` to read more",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="rank", description="View all ranks and their XP requirements")
async def rank(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎖️ GUARDIAN RANKS & HIERARCHY",
        description="Rise through the ranks and earn your place among legends!",
        color=0xFFD700
    )
    
    for level, role_name in sorted(ROLE_REWARDS.items()):
        xp_needed = calculate_xp_for_level(level)
        embed.add_field(
            name=f"Level {level} - {role_name}",
            value=f"Requires: {xp_needed:,} XP",
            inline=True
        )
    
    embed.set_footer(text="Earn XP by being active in the server!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quest", description="Get a daily quest to earn bonus XP")
async def quest(interaction: discord.Interaction):
    quests = [
        ("Social Butterfly", "Send 20 messages in different channels", 300),
        ("Guardian's Wisdom", "Share lore or help a new member", 250),
        ("Arcane Explorer", "Use 5 different bot commands", 200),
        ("Voice of Arcadia", "Spend 30 minutes in voice chat", 350),
        ("Reaction Master", "React to 15 messages with emojis", 150),
        ("Night Watch", "Be active during late hours (after 10 PM)", 400),
    ]
    
    quest_name, quest_desc, quest_reward = random.choice(quests)
    
    embed = discord.Embed(
        title="🗺️ DAILY QUEST",
        description=f"**{quest_name}**\n\n{quest_desc}",
        color=0x00FF00
    )
    embed.add_field(name="💰 Reward", value=f"+{quest_reward} XP", inline=False)
    embed.set_footer(text="Complete this quest before the day ends!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="arcadia", description="Get information about the Guardian of Arcadia server")
async def arcadia(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🏰 Welcome to Guardian of Arcadia",
        description="A mystical realm where legends are born among the floating isles!",
        color=0x00CED1
    )
    embed.add_field(
        name="🌟 About Us",
        value="Guardian of Arcadia is a fantasy-themed community where adventure, friendship, and magic unite!",
        inline=False
    )
    embed.add_field(
        name="⚔️ Join the Journey",
        value="Participate, level up, earn ranks, and become a legend!",
        inline=False
    )
    embed.add_field(
        name="📜 Available Commands",
        value="`/profile` `/leaderboard` `/prophecy` `/lore` `/rank` `/quest` `/bless`",
        inline=False
    )
    embed.add_field(
        name="💎 Special Features",
        value="• Crystal Shard drops (type `!claim` when they appear)\n• Guardian's Blessing system (`/bless @user`)\n• Keyword responses in chat",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ranks", description="View all available ranks and their requirements")
async def ranks(interaction: discord.Interaction):
    embed = discord.Embed(
        title="⚔️ GUARDIAN RANK HIERARCHY ⚔️",
        description="*Ascend through the ranks to unlock greater power*",
        color=0x00CED1
    )
    
    for level, role_name in sorted(ROLE_REWARDS.items()):
        xp_needed = calculate_xp_for_level(level)
        embed.add_field(
            name=f"Level {level} - {role_name}",
            value=f"Requires {xp_needed:,} total XP",
            inline=False
        )
    
    embed.set_footer(text="Keep engaging to climb the ranks! ⚡")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sync", description="[Admin] Manually sync slash commands")
async def sync_commands(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Only the server owner can sync commands!", ephemeral=True)
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        synced = await bot.tree.sync()
        await interaction.followup.send(f"✅ Successfully synced {len(synced)} commands!", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to sync: {str(e)}", ephemeral=True)

@bot.tree.command(name="dbcheck", description="[Admin] Check database health")
async def db_check(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Only the server owner can check the database!", ephemeral=True)
        return
    
    try:
        conn = sqlite3.connect('arcadia.db')
        c = conn.cursor()
        
        # Check users table structure
        c.execute("PRAGMA table_info(users)")
        columns = c.fetchall()
        column_names = [col[1] for col in columns]
        
        c.execute("SELECT COUNT(*) FROM users")
        user_count = c.fetchone()[0]
        
        conn.close()
        
        embed = discord.Embed(
            title="🔍 Database Health Check",
            color=0x00FF00
        )
        embed.add_field(name="Total Users", value=str(user_count), inline=True)
        embed.add_field(name="Columns", value=", ".join(column_names), inline=False)
        embed.set_footer(text="Database is operational ✅")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Database error: {str(e)}", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set your bot token in the environment or .env file")
    else:
        bot.run(TOKEN)
