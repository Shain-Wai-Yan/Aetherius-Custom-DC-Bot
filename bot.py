import discord
from discord.ext import commands
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import asyncio
from datetime import datetime, date
import random
from dotenv import load_dotenv
from flask import Flask
from threading import Thread
from collections import defaultdict
from threading import Lock

load_dotenv()

app = Flask('')

@app.route('/')
def home():
    return "🛡️ Aetherius | The Eternal Sentry is awake and guarding Arcadia!"

@app.route('/health')
def health():
    return {"status": "online", "bot": "Aetherius"}

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
intents.voice_states = True  # Added for voice chat tracking

bot = commands.Bot(command_prefix="!", intents=intents)

connection_pool = None

def get_db_connection():
    """Get a connection from the pool"""
    global connection_pool
    if connection_pool is None:
        DATABASE_URL = os.getenv('DATABASE_URL')
        if not DATABASE_URL:
            raise Exception("❌ DATABASE_URL environment variable not set!")
        
        connection_pool = psycopg2.pool.ThreadedConnectionPool(
            1, 10,
            DATABASE_URL,
            cursor_factory=RealDictCursor
        )
        print("✅ PostgreSQL connection pool created successfully!")
    
    return connection_pool.getconn()

def release_db_connection(conn):
    """Release connection back to the pool"""
    global connection_pool
    if connection_pool:
        connection_pool.putconn(conn)

def init_db():
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id BIGINT PRIMARY KEY,
                      username TEXT,
                      xp INTEGER DEFAULT 0,
                      level INTEGER DEFAULT 1,
                      last_message DOUBLE PRECISION,
                      total_messages INTEGER DEFAULT 0,
                      crystal_shards INTEGER DEFAULT 0,
                      blessings_given INTEGER DEFAULT 0,
                      blessings_received INTEGER DEFAULT 0)''')
        
        c.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'users'
        """)
        existing_columns = [row['column_name'] for row in c.fetchall()]
        
        if 'crystal_shards' not in existing_columns:
            c.execute('ALTER TABLE users ADD COLUMN crystal_shards INTEGER DEFAULT 0')
            print("✅ Added crystal_shards column to existing database")
        
        if 'blessings_given' not in existing_columns:
            c.execute('ALTER TABLE users ADD COLUMN blessings_given INTEGER DEFAULT 0')
            print("✅ Added blessings_given column to existing database")
        
        if 'blessings_received' not in existing_columns:
            c.execute('ALTER TABLE users ADD COLUMN blessings_received INTEGER DEFAULT 0')
            print("✅ Added blessings_received column to existing database")
        
        c.execute('''CREATE TABLE IF NOT EXISTS user_quests
                     (quest_id SERIAL PRIMARY KEY,
                      user_id BIGINT NOT NULL,
                      quest_name TEXT NOT NULL,
                      quest_type TEXT NOT NULL,
                      quest_description TEXT,
                      quest_reward INTEGER,
                      progress INTEGER DEFAULT 0,
                      target INTEGER,
                      completed BOOLEAN DEFAULT FALSE,
                      claimed BOOLEAN DEFAULT FALSE,
                      assigned_date DATE NOT NULL,
                      completed_date TIMESTAMP,
                      UNIQUE(user_id, assigned_date))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS quest_progress
                     (id SERIAL PRIMARY KEY,
                      user_id BIGINT NOT NULL,
                      quest_date DATE NOT NULL,
                      messages_sent INTEGER DEFAULT 0,
                      unique_channels TEXT[] DEFAULT '{}',
                      commands_used TEXT[] DEFAULT '{}',
                      reactions_added INTEGER DEFAULT 0,
                      voice_time INTEGER DEFAULT 0,
                      help_given BOOLEAN DEFAULT FALSE,
                      late_night_active BOOLEAN DEFAULT FALSE,
                      UNIQUE(user_id, quest_date))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS prophecies
                     (date TEXT PRIMARY KEY,
                      prophecy TEXT,
                      omen_type TEXT)''')
        
        conn.commit()
        print("✅ Database tables initialized successfully!")
        print("✅ Quest system tables created!")
    except Exception as e:
        print(f"❌ Database initialization error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)


XP_PER_MESSAGE = 15
XP_COOLDOWN = 60
LEVEL_MULTIPLIER = 100

message_counter = defaultdict(int)
crystals = {}
crystal_lock = Lock()
xp_cooldowns = {}

CRYSTAL_DROP_CHANCE = 50

keyword_cooldowns = defaultdict(float)
KEYWORD_COOLDOWN = 30

voice_tracking = {}  # user_id -> {join_time: timestamp}

ROLE_REWARDS = {
    0: "Cloud-Walker",
    5: "Mist-Warden",
    10: "Aether-Guard",
    18: "Crystal-Sentinel",
    26: "Isle-Vanguard",
    35: "Sky-Paladin",
    45: "Grand Archon",
    60: "Arcadian Paragon"
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

QUEST_TYPES = {
    "social_butterfly": {
        "name": "Social Butterfly",
        "description": "Send 20 messages in different channels",
        "reward": 300,
        "target": 20,
        "type": "messages"
    },
    "guardians_wisdom": {
        "name": "Guardian's Wisdom",
        "description": "Share lore or help a new member (use /lore or mention @new)",
        "reward": 250,
        "target": 1,
        "type": "help"
    },
    "arcane_explorer": {
        "name": "Arcane Explorer",
        "description": "Use 5 different bot commands",
        "reward": 200,
        "target": 5,
        "type": "commands"
    },
    "voice_of_arcadia": {
        "name": "Voice of Arcadia",
        "description": "Spend 30 minutes in voice chat",
        "reward": 350,
        "target": 1800,  # 30 minutes in seconds
        "type": "voice"
    },
    "reaction_master": {
        "name": "Reaction Master",
        "description": "React to 15 messages with emojis",
        "reward": 150,
        "target": 15,
        "type": "reactions"
    },
    "night_watch": {
        "name": "Night Watch",
        "description": "Be active during late hours (after 10 PM server time)",
        "reward": 400,
        "target": 1,
        "type": "late_night"
    }
}

def calculate_xp_for_level(level):
    return LEVEL_MULTIPLIER * (level - 1) ** 2

def get_user_level(xp):
    level = 1
    while xp >= calculate_xp_for_level(level + 1):
        level += 1
    return level

async def get_or_assign_daily_quest(user_id):
    """Get today's quest for user, or assign a new one if none exists"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        today = date.today()
        
        # Check if user has a quest for today
        c.execute('''SELECT * FROM user_quests 
                     WHERE user_id = %s AND assigned_date = %s''',
                  (user_id, today))
        quest = c.fetchone()
        
        if quest:
            return dict(quest)
        
        # Assign a new random quest
        quest_key = random.choice(list(QUEST_TYPES.keys()))
        quest_data = QUEST_TYPES[quest_key]
        
        c.execute('''INSERT INTO user_quests 
                     (user_id, quest_name, quest_type, quest_description, 
                      quest_reward, target, assigned_date)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)
                     RETURNING *''',
                  (user_id, quest_data['name'], quest_data['type'],
                   quest_data['description'], quest_data['reward'],
                   quest_data['target'], today))
        
        new_quest = c.fetchone()
        conn.commit()
        
        # Initialize progress tracking
        c.execute('''INSERT INTO quest_progress (user_id, quest_date)
                     VALUES (%s, %s)
                     ON CONFLICT (user_id, quest_date) DO NOTHING''',
                  (user_id, today))
        conn.commit()
        
        return dict(new_quest)
    
    except Exception as e:
        print(f"❌ Error in get_or_assign_daily_quest: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            release_db_connection(conn)

async def update_quest_progress(user_id, progress_type, value=1, channel_id=None):
    """Update user's quest progress based on activity"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        today = date.today()
        
        # Get user's active quest
        c.execute('''SELECT * FROM user_quests 
                     WHERE user_id = %s AND assigned_date = %s 
                     AND completed = FALSE''',
                  (user_id, today))
        quest = c.fetchone()
        
        if not quest:
            return False
        
        quest_type = quest['quest_type']
        
        # Update progress based on quest type
        if quest_type == 'messages' and progress_type == 'message':
            # Track unique channels for Social Butterfly
            c.execute('''SELECT unique_channels FROM quest_progress
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            progress = c.fetchone()
            
            if progress:
                channels = progress['unique_channels'] or []
                if channel_id and str(channel_id) not in channels:
                    channels.append(str(channel_id))
                    c.execute('''UPDATE quest_progress
                                 SET unique_channels = %s, messages_sent = %s
                                 WHERE user_id = %s AND quest_date = %s''',
                              (channels, len(channels), user_id, today))
                    
                    # Update quest progress
                    new_progress = len(channels)
                    c.execute('''UPDATE user_quests
                                 SET progress = %s, 
                                     completed = CASE WHEN %s >= target THEN TRUE ELSE FALSE END
                                 WHERE user_id = %s AND assigned_date = %s''',
                              (new_progress, new_progress, user_id, today))
        
        elif quest_type == 'commands' and progress_type == 'command':
            # Track unique commands for Arcane Explorer
            c.execute('''SELECT commands_used FROM quest_progress
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            progress = c.fetchone()
            
            if progress:
                commands = progress['commands_used'] or []
                if value not in commands:
                    commands.append(value)
                    c.execute('''UPDATE quest_progress
                                 SET commands_used = %s
                                 WHERE user_id = %s AND quest_date = %s''',
                              (commands, user_id, today))
                    
                    new_progress = len(commands)
                    c.execute('''UPDATE user_quests
                                 SET progress = %s,
                                     completed = CASE WHEN %s >= target THEN TRUE ELSE FALSE END
                                 WHERE user_id = %s AND assigned_date = %s''',
                              (new_progress, new_progress, user_id, today))
        
        elif quest_type == 'reactions' and progress_type == 'reaction':
            # Track reactions for Reaction Master
            c.execute('''UPDATE quest_progress
                         SET reactions_added = reactions_added + 1
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            
            c.execute('''UPDATE user_quests
                         SET progress = progress + 1,
                             completed = CASE WHEN progress + 1 >= target THEN TRUE ELSE FALSE END
                         WHERE user_id = %s AND assigned_date = %s''',
                      (user_id, today))
        
        elif quest_type == 'voice' and progress_type == 'voice':
            # Track voice time for Voice of Arcadia
            c.execute('''UPDATE quest_progress
                         SET voice_time = voice_time + %s
                         WHERE user_id = %s AND quest_date = %s''',
                      (value, user_id, today))
            
            c.execute('''SELECT voice_time FROM quest_progress
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            progress = c.fetchone()
            
            if progress:
                total_time = progress['voice_time']
                c.execute('''UPDATE user_quests
                             SET progress = %s,
                                 completed = CASE WHEN %s >= target THEN TRUE ELSE FALSE END
                             WHERE user_id = %s AND assigned_date = %s''',
                          (total_time, total_time, user_id, today))
        
        elif quest_type == 'help' and progress_type == 'help':
            # Track help given for Guardian's Wisdom
            c.execute('''UPDATE quest_progress
                         SET help_given = TRUE
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            
            c.execute('''UPDATE user_quests
                         SET progress = 1, completed = TRUE
                         WHERE user_id = %s AND assigned_date = %s''',
                      (user_id, today))
        
        elif quest_type == 'late_night' and progress_type == 'late_night':
            # Track late night activity for Night Watch
            c.execute('''UPDATE quest_progress
                         SET late_night_active = TRUE
                         WHERE user_id = %s AND quest_date = %s''',
                      (user_id, today))
            
            c.execute('''UPDATE user_quests
                         SET progress = 1, completed = TRUE
                         WHERE user_id = %s AND assigned_date = %s''',
                      (user_id, today))
        
        conn.commit()
        
        # Check if quest just completed
        c.execute('''SELECT * FROM user_quests 
                     WHERE user_id = %s AND assigned_date = %s''',
                  (user_id, today))
        updated_quest = c.fetchone()
        
        return updated_quest['completed'] if updated_quest else False
        
    except Exception as e:
        print(f"❌ Error in update_quest_progress: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            release_db_connection(conn)

@bot.event
async def on_ready():
    print(f'✨ Aetherius | The Eternal Sentry has awakened in Arcadia!')
    print(f'Guardian ID: {bot.user.id}')
    init_db()
    
    try:
        synced = await bot.tree.sync()
        print(f"⚔️ Synced {len(synced)} slash commands successfully!")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="over the Floating Isles | Aetherius awakens"
        )
    )

@bot.event
async def on_member_join(member):
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
            color=0x00CED1
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_footer(text=f"Member #{member.guild.member_count} • May the Arcane guide you")
        
        await welcome_channel.send(embed=embed)

@bot.event
async def on_voice_state_update(member, before, after):
    """Track voice channel activity for quests"""
    if member.bot:
        return
    
    # User joined a voice channel
    if before.channel is None and after.channel is not None:
        voice_tracking[member.id] = {
            'join_time': datetime.now().timestamp()
        }
    
    # User left a voice channel
    elif before.channel is not None and after.channel is None:
        if member.id in voice_tracking:
            join_time = voice_tracking[member.id]['join_time']
            current_time = datetime.now().timestamp()
            time_spent = int(current_time - join_time)
            
            # Update quest progress
            await update_quest_progress(member.id, 'voice', time_spent)
            
            del voice_tracking[member.id]

@bot.event
async def on_reaction_add(reaction, user):
    """Track reactions for quests"""
    if user.bot:
        return
    
    await update_quest_progress(user.id, 'reaction')

@bot.event
async def on_message(message):
    global message_counter, crystals
    
    if message.author.bot:
        return
    
    if not message.guild:
        return
    
    guild_id = message.guild.id
    message_counter[guild_id] += 1
    
    # Crystal drop logic
    if message_counter[guild_id] >= CRYSTAL_DROP_CHANCE and guild_id not in crystals:
        message_counter[guild_id] = 0
        
        embed = discord.Embed(
            title="💎 CRYSTAL SHARD DISCOVERED!",
            description="A mystical **Crystal Shard** has appeared! Type `!claim` in this channel to collect it and gain **100 bonus XP**!",
            color=0x00FFFF
        )
        embed.set_footer(text="First to claim wins! ⚡ Expires in 30 seconds")
        
        crystal_msg = await message.channel.send(embed=embed)
        crystals[guild_id] = {
            'active': True,
            'message_id': crystal_msg.id,
            'channel_id': message.channel.id
        }
        
        await asyncio.sleep(30)
        if guild_id in crystals and crystals[guild_id]['active']:
            crystals[guild_id]['active'] = False
            expired_embed = discord.Embed(
                title="💎 Crystal Shard Vanished",
                description="The Crystal Shard has faded back into the Arcane mists...",
                color=0x808080
            )
            try:
                await crystal_msg.edit(embed=expired_embed)
            except:
                pass
            del crystals[guild_id]
    
    content_lower = message.content.lower()
    
    if 'lore' in content_lower or '@new' in content_lower or 'welcome' in content_lower:
        await update_quest_progress(message.author.id, 'help')
    
    current_hour = datetime.now().hour
    if current_hour >= 22 or current_hour < 6:  # 10 PM to 6 AM
        await update_quest_progress(message.author.id, 'late_night')
    
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
    
    current_time = datetime.now().timestamp()
    user_id = message.author.id
    
    for keyword, response in keywords.items():
        if keyword in content_lower:
            if current_time - keyword_cooldowns.get(user_id, 0) >= KEYWORD_COOLDOWN:
                await message.channel.send(response)
                keyword_cooldowns[user_id] = current_time
            break
    
    await update_quest_progress(message.author.id, 'message', channel_id=message.channel.id)
    
    await process_xp(message)
    
    await bot.process_commands(message)

@bot.command(name='claim')
async def claim_crystal(ctx):
    global crystals

    guild_id = ctx.guild.id
    
    with crystal_lock:
        if guild_id not in crystals or not crystals[guild_id]['active']:
            return

        if ctx.channel.id != crystals[guild_id]['channel_id']:
            await ctx.reply("⚠️ The crystal is in a different channel!", delete_after=5)
            return

        crystals[guild_id]['active'] = False

    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('SELECT xp, level, crystal_shards FROM users WHERE user_id = %s', (ctx.author.id,))
        row = c.fetchone()

        if row:
            xp, level, shards = row['xp'], row['level'], row['crystal_shards']
            new_xp = xp + 100
            new_level = get_user_level(new_xp)
            c.execute(
                'UPDATE users SET xp = %s, level = %s, crystal_shards = %s WHERE user_id = %s',
                (new_xp, new_level, shards + 1, ctx.author.id)
            )
            
            if new_level > level:
                conn.commit()
                await handle_level_up(ctx.message, new_level)
        else:
            c.execute(
                '''INSERT INTO users
                   (user_id, username, xp, level, last_message, total_messages,
                    crystal_shards, blessings_given, blessings_received)
                   VALUES (%s, %s, 100, 1, %s, 0, 1, 0, 0)''',
                (ctx.author.id, str(ctx.author), datetime.now().timestamp())
            )

        conn.commit()

        embed = discord.Embed(
            title="💎 CRYSTAL SHARD CLAIMED!",
            description=f"{ctx.author.mention} has claimed the Crystal Shard!\n\n**+100 XP** ⚡\n**+1 Crystal Shard** 💎",
            color=0x00FF00
        )
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)
        
        if guild_id in crystals:
            del crystals[guild_id]
    
    except Exception as e:
        print(f"❌ Error in claim_crystal: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

async def process_xp(message):
    if message.author.bot or not message.guild:
        return

    guild_id = message.guild.id
    user_id = message.author.id
    current_time = datetime.now().timestamp()
    cooldown_key = (guild_id, user_id)
    
    if cooldown_key in xp_cooldowns:
        if current_time - xp_cooldowns[cooldown_key] < XP_COOLDOWN:
            return

    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        c.execute('SELECT xp, level, last_message, total_messages FROM users WHERE user_id = %s', (user_id,))
        row = c.fetchone()

        if row:
            xp, level, last_message, total_messages = row['xp'], row['level'], row['last_message'], row['total_messages']

            if last_message and current_time - last_message < XP_COOLDOWN:
                xp_cooldowns[cooldown_key] = last_message
                return

            new_xp = xp + XP_PER_MESSAGE
            new_level = get_user_level(new_xp)

            c.execute(
                '''UPDATE users
                   SET xp = %s, level = %s, last_message = %s, total_messages = %s, username = %s
                   WHERE user_id = %s''',
                (new_xp, new_level, current_time, total_messages + 1, str(message.author), user_id)
            )

            conn.commit()
            
            xp_cooldowns[cooldown_key] = current_time

            if new_level > level:
                await handle_level_up(message, new_level)

        else:
            c.execute(
                '''INSERT INTO users
                   (user_id, username, xp, level, last_message, total_messages,
                    crystal_shards, blessings_given, blessings_received)
                   VALUES (%s, %s, %s, %s, %s, %s, 0, 0, 0)''',
                (user_id, str(message.author), XP_PER_MESSAGE, 1, current_time, 1)
            )

            conn.commit()
            
            xp_cooldowns[cooldown_key] = current_time
    
    except Exception as e:
        print(f"❌ Error in process_xp: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            release_db_connection(conn)

async def handle_level_up(message, new_level):
    blessing_emoji = "✨"
    for milestone in sorted(LEVEL_BLESSINGS.keys(), reverse=True):
        if new_level >= milestone:
            blessing_emoji = LEVEL_BLESSINGS[milestone]
            break
    
    embed = discord.Embed(
        title=f"{blessing_emoji} RANK ASCENSION {blessing_emoji}",
        description=f"🎉 {message.author.mention} has ascended to **Level {new_level}**!\n\nThe Arcane energies flow stronger within you...",
        color=0xFFD700
    )
    
    if new_level in ROLE_REWARDS:
        role_name = ROLE_REWARDS[new_level]
        role = discord.utils.get(message.guild.roles, name=role_name)
        
        if role:
            try:
                bot_member = message.guild.get_member(bot.user.id)
                if role < bot_member.top_role:
                    await message.author.add_roles(role)
                    embed.add_field(
                        name="🏆 New Title Bestowed!",
                        value=f"You have earned the rank of **{role_name}**!",
                        inline=False
                    )
                else:
                    print(f"⚠️ Cannot assign role {role_name} - role hierarchy issue")
            except Exception as e:
                print(f"❌ Error assigning role: {e}")
    
    xp_needed = calculate_xp_for_level(new_level + 1) - calculate_xp_for_level(new_level)
    embed.set_footer(text=f"Next rank in {xp_needed} XP • {blessing_emoji} Blessing received")
    
    await message.channel.send(embed=embed)

@bot.tree.command(name="profile", description="View your Guardian profile and stats")
async def profile(interaction: discord.Interaction, member: discord.Member = None):
    target = member or interaction.user
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM users WHERE user_id = %s', (target.id,))
        user_data = c.fetchone()
        
        if not user_data:
            embed = discord.Embed(
                title="📜 Guardian Profile",
                description=f"{target.mention} has not yet begun their journey in Arcadia...",
                color=0x808080
            )
        else:
            xp = user_data['xp']
            level = user_data['level']
            messages = user_data['total_messages']
            crystal_shards = user_data['crystal_shards'] if user_data['crystal_shards'] is not None else 0
            blessings_given = user_data['blessings_given'] if user_data['blessings_given'] is not None else 0
            blessings_received = user_data['blessings_received'] if user_data['blessings_received'] is not None else 0
            
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
            
            today = date.today()
            c.execute('''SELECT * FROM user_quests 
                         WHERE user_id = %s AND assigned_date = %s''',
                      (target.id, today))
            quest = c.fetchone()
            
            if quest:
                progress_percent = int((quest['progress'] / quest['target']) * 100) if quest['target'] > 0 else 0
                status = "✅ Completed!" if quest['completed'] else f"{quest['progress']}/{quest['target']}"
                claimed_status = " (Claimed)" if quest['claimed'] else ""
                
                embed.add_field(
                    name="🗺️ Today's Quest",
                    value=f"**{quest['quest_name']}**{claimed_status}\nProgress: {status}",
                    inline=False
                )
            
            roles = [r for r in target.roles if r.name != "@everyone"]
            if roles:
                highest_role = max(roles, key=lambda r: r.position)
                embed.add_field(name="🎖️ Highest Rank", value=highest_role.mention, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        print(f"❌ Error in profile: {e}")
        await interaction.response.send_message("⚠️ An error occurred while fetching the profile.", ephemeral=True)
    finally:
        if conn:
            release_db_connection(conn)

def create_progress_bar(current, total, length=10):
    if total <= 0:
        return "[██████████]"
    filled = int((current / total) * length)
    filled = min(filled, length)
    return "[" + "█" * filled + "░" * (length - filled) + "]"

bless_cooldowns = {}
BLESS_COOLDOWN = 300

@bot.tree.command(name="bless", description="Bestow a Guardian's Blessing upon another member")
async def bless(interaction: discord.Interaction, member: discord.Member):
    await update_quest_progress(interaction.user.id, 'command', 'bless')
    
    if member.id == interaction.user.id:
        await interaction.response.send_message("You cannot bless yourself, noble Guardian!", ephemeral=True)
        return
    
    if member.bot:
        await interaction.response.send_message("Bots are beyond the reach of mortal blessings!", ephemeral=True)
        return
    
    current_time = datetime.now().timestamp()
    if interaction.user.id in bless_cooldowns:
        time_left = BLESS_COOLDOWN - (current_time - bless_cooldowns[interaction.user.id])
        if time_left > 0:
            minutes = int(time_left // 60)
            seconds = int(time_left % 60)
            await interaction.response.send_message(
                f"⏳ Your blessing power is recharging! Please wait {minutes}m {seconds}s before blessing again.",
                ephemeral=True
            )
            return
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        blessing_xp = 25
        
        c.execute('SELECT * FROM users WHERE user_id = %s', (interaction.user.id,))
        giver_data = c.fetchone()
        if giver_data:
            new_xp = giver_data['xp'] + blessing_xp
            new_level = get_user_level(new_xp)
            c.execute('UPDATE users SET xp = %s, level = %s, blessings_given = %s WHERE user_id = %s',
                      (new_xp, new_level, giver_data['blessings_given'] + 1, interaction.user.id))
            
            if new_level > giver_data['level']:
                await interaction.channel.send(f"🎉 {interaction.user.mention} has ascended to **Level {new_level}** through their generosity!")
        else:
            c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards, blessings_given, blessings_received)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                      (interaction.user.id, str(interaction.user), blessing_xp, 1, datetime.now().timestamp(), 0, 0, 1, 0))
        
        c.execute('SELECT * FROM users WHERE user_id = %s', (member.id,))
        receiver_data = c.fetchone()
        if receiver_data:
            new_xp = receiver_data['xp'] + blessing_xp
            new_level = get_user_level(new_xp)
            c.execute('UPDATE users SET xp = %s, level = %s, blessings_received = %s WHERE user_id = %s',
                      (new_xp, new_level, receiver_data['blessings_received'] + 1, member.id))
            
            if new_level > receiver_data['level']:
                await interaction.channel.send(f"🎉 {member.mention} has ascended to **Level {new_level}** through the blessing!")
        else:
            c.execute('''INSERT INTO users (user_id, username, xp, level, last_message, total_messages, crystal_shards, blessings_given, blessings_received)
                         VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                      (member.id, str(member), blessing_xp, 1, datetime.now().timestamp(), 0, 0, 0, 1))
        
        conn.commit()
        
        bless_cooldowns[interaction.user.id] = current_time
        
        embed = discord.Embed(
            title="✨ GUARDIAN'S BLESSING BESTOWED ✨",
            description=f"{interaction.user.mention} has blessed {member.mention}!\n\nThe Arcane energies strengthen the bonds between Guardians...",
            color=0xFFD700
        )
        embed.add_field(name="🎁 Rewards", value=f"Both Guardians receive **+{blessing_xp} XP**!", inline=False)
        embed.set_footer(text="Kindness is the true strength of Arcadia")
        
        await interaction.response.send_message(embed=embed)
    
    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ I lack the permissions to bestow this blessing! Please ensure I have 'Manage Roles' permission.",
            ephemeral=True
        )
    except Exception as e:
        print(f"❌ Error in bless: {e}")
        if conn:
            conn.rollback()
        await interaction.response.send_message(
            f"⚠️ An error occurred while bestowing the blessing.",
            ephemeral=True
        )
    finally:
        if conn:
            release_db_connection(conn)

@bot.tree.command(name="leaderboard", description="View the top Guardians of Arcadia")
async def leaderboard(interaction: discord.Interaction):
    await update_quest_progress(interaction.user.id, 'command', 'leaderboard')
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''SELECT user_id, username, xp, level 
                     FROM users 
                     ORDER BY xp DESC 
                     LIMIT 10''')
        top_users = c.fetchall()
        
        if not top_users:
            await interaction.response.send_message("No Guardians have begun their journey yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 ARCADIA LEADERBOARD 🏆",
            description="The mightiest Guardians of the realm!",
            color=0xFFD700
        )
        
        medals = ["🥇", "🥈", "🥉"]
        
        for idx, user in enumerate(top_users):
            medal = medals[idx] if idx < 3 else f"**{idx + 1}.**"
            embed.add_field(
                name=f"{medal} {user['username']}",
                value=f"Level {user['level']} • {user['xp']:,} XP",
                inline=False
            )
        
        embed.set_footer(text="Keep climbing the ranks, Guardian!")
        await interaction.response.send_message(embed=embed)
    
    except Exception as e:
        print(f"❌ Error in leaderboard: {e}")
        await interaction.response.send_message("⚠️ An error occurred while fetching the leaderboard.", ephemeral=True)
    finally:
        if conn:
            release_db_connection(conn)

@bot.tree.command(name="prophecy", description="Receive a mystical prophecy from the Arcane")
async def prophecy(interaction: discord.Interaction):
    await update_quest_progress(interaction.user.id, 'command', 'prophecy')
    
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
    await update_quest_progress(interaction.user.id, 'command', 'lore')
    await update_quest_progress(interaction.user.id, 'help')
    
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
            color=0x1ABC9C
        )
    else:
        embed = discord.Embed(
            title="📜 Arcadia Lore",
            description="Available topics: " + ", ".join(lore_entries.keys()),
            color=0x1ABC9C
        )
    
    await interaction.response.send_message(embed=embed)

# Safe shutdown for the bot
async def shutdown():
    print("🛡️ Shutting down Aetherius...")
    global connection_pool
    if connection_pool:
        connection_pool.closeall()
        print("✅ Connection pool closed.")
    await bot.close()

# Handle SIGINT/SIGTERM to run shutdown
import signal
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda s, f: asyncio.create_task(shutdown()))

@bot.tree.command(name="rank", description="View all ranks and their XP requirements")
async def rank(interaction: discord.Interaction):
    await update_quest_progress(interaction.user.id, 'command', 'rank')
    
    embed = discord.Embed(
        title="🎖️ GUARDIAN RANKS & HIERARCHY",
        description="Rise through the ranks and earn your place among legends!",
        color=0xFFD700
    )
    
    for level, role_name in sorted(ROLE_REWARDS.items()):
        xp_needed = calculate_xp_for_level(level)
        embed.add_field(
            name=f"Level {level} - {role_name}",
            value=f"Total XP to reach: {xp_needed:,}",
            inline=True
        )
    
    embed.set_footer(text="Earn XP by being active in the server!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="quest", description="View your daily quest and progress")
async def quest(interaction: discord.Interaction):
    """View today's quest, progress, and claim rewards"""
    await update_quest_progress(interaction.user.id, 'command', 'quest')
    
    conn = None
    try:
        # Get or assign today's quest
        quest_data = await get_or_assign_daily_quest(interaction.user.id)
        
        if not quest_data:
            await interaction.response.send_message(
                "⚠️ Unable to retrieve your quest. Please try again!",
                ephemeral=True
            )
            return
        
        # Create embed
        progress_percent = int((quest_data['progress'] / quest_data['target']) * 100) if quest_data['target'] > 0 else 0
        progress_bar = create_progress_bar(quest_data['progress'], quest_data['target'], 15)
        
        if quest_data['completed'] and quest_data['claimed']:
            # Quest already completed and claimed
            embed = discord.Embed(
                title="✅ QUEST COMPLETED",
                description=f"**{quest_data['quest_name']}**\n\n{quest_data['quest_description']}",
                color=0x808080
            )
            embed.add_field(
                name="Status",
                value="You've already completed today's quest! Come back tomorrow for a new challenge.",
                inline=False
            )
        elif quest_data['completed'] and not quest_data['claimed']:
            # Quest completed but not claimed
            embed = discord.Embed(
                title="🎉 QUEST COMPLETED!",
                description=f"**{quest_data['quest_name']}**\n\n{quest_data['quest_description']}",
                color=0x00FF00
            )
            embed.add_field(name="💰 Reward", value=f"+{quest_data['quest_reward']} XP", inline=False)
            embed.add_field(
                name="✨ Claim Your Reward",
                value="Use `/questclaim` to collect your reward!",
                inline=False
            )
        else:
            # Quest in progress
            embed = discord.Embed(
                title="🗺️ DAILY QUEST",
                description=f"**{quest_data['quest_name']}**\n\n{quest_data['quest_description']}",
                color=0x00CED1
            )
            embed.add_field(name="💰 Reward", value=f"+{quest_data['quest_reward']} XP", inline=True)
            embed.add_field(name="📊 Progress", value=f"{quest_data['progress']}/{quest_data['target']}", inline=True)
            embed.add_field(
                name="Progress Bar",
                value=f"{progress_bar} {progress_percent}%",
                inline=False
            )
        
        embed.set_footer(text=f"Quest resets daily at midnight • {quest_data['assigned_date']}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        print(f"❌ Error in quest command: {e}")
        await interaction.response.send_message(
            "⚠️ An error occurred while retrieving your quest.",
            ephemeral=True
        )

@bot.tree.command(name="questclaim", description="Claim your completed quest reward")
async def questclaim(interaction: discord.Interaction):
    """Claim XP reward for completed quest"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        today = date.today()
        
        # Get user's quest
        c.execute('''SELECT * FROM user_quests 
                     WHERE user_id = %s AND assigned_date = %s''',
                  (interaction.user.id, today))
        quest = c.fetchone()
        
        if not quest:
            await interaction.response.send_message(
                "⚠️ You don't have an active quest today! Use `/quest` to get one.",
                ephemeral=True
            )
            return
        
        if not quest['completed']:
            await interaction.response.send_message(
                f"⚠️ You haven't completed your quest yet!\n\n**Progress:** {quest['progress']}/{quest['target']}",
                ephemeral=True
            )
            return
        
        if quest['claimed']:
            await interaction.response.send_message(
                "⚠️ You've already claimed this quest reward!",
                ephemeral=True
            )
            return
        
        # Ensure user exists in database before awarding XP
        c.execute('SELECT xp, level FROM users WHERE user_id = %s', (interaction.user.id,))
        user = c.fetchone()
        
        if not user:
            # Create user if doesn't exist
            c.execute('''INSERT INTO users (user_id, username, xp, level)
                         VALUES (%s, %s, 0, 1)''',
                      (interaction.user.id, interaction.user.name))
            conn.commit()
            user = {'xp': 0, 'level': 1}
        
        old_xp = user['xp']
        old_level = user['level']
        new_xp = old_xp + quest['quest_reward']
        new_level = get_user_level(new_xp)
        
        c.execute('''UPDATE users 
                     SET xp = %s, level = %s 
                     WHERE user_id = %s''',
                  (new_xp, new_level, interaction.user.id))
        
        c.execute('''UPDATE user_quests 
                     SET claimed = TRUE, completed_date = %s 
                     WHERE user_id = %s AND assigned_date = %s''',
                  (datetime.now(), interaction.user.id, today))
        
        conn.commit()
        
        embed = discord.Embed(
            title="✨ QUEST REWARD CLAIMED!",
            description=f"**{quest['quest_name']}** completed!\n\nYou've earned **+{quest['quest_reward']} XP**!",
            color=0xFFD700
        )
        embed.add_field(name="Previous XP", value=f"{old_xp:,}", inline=True)
        embed.add_field(name="New XP", value=f"{new_xp:,}", inline=True)
        embed.add_field(name="Current Level", value=f"Level {new_level}", inline=True)
        
        if new_level > old_level:
            level_up_text = f"\n\n🎉 **LEVEL UP!** You've reached Level {new_level}!"
            if new_level in ROLE_REWARDS:
                level_up_text += f"\n⚔️ New Rank: **{ROLE_REWARDS[new_level]}**"
            embed.add_field(name="Milestone Achieved!", value=level_up_text, inline=False)
        
        embed.set_footer(text="Return tomorrow for a new quest!")
        
        await interaction.response.send_message(embed=embed)
        
        if new_level > old_level:
            level_blessing = LEVEL_BLESSINGS.get(new_level, "⭐")
            announcement = f"{level_blessing} {interaction.user.mention} has ascended to **Level {new_level}** by completing their quest!"
            if new_level in ROLE_REWARDS:
                announcement += f"\n⚔️ New Rank Unlocked: **{ROLE_REWARDS[new_level]}**"
            await interaction.channel.send(announcement)
    
    except Exception as e:
        print(f"❌ Error in questclaim: {e}")
        if conn:
            conn.rollback()
        await interaction.response.send_message(
            "⚠️ An error occurred while claiming your reward. Please try again!",
            ephemeral=True
        )
    finally:
        if conn:
            release_db_connection(conn)

@bot.tree.command(name="arcadia", description="Get information about the Guardian of Arcadia server")
async def arcadia(interaction: discord.Interaction):
    await update_quest_progress(interaction.user.id, 'command', 'arcadia')
    
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
        value="`/profile` `/leaderboard` `/prophecy` `/lore` `/rank` `/quest` `/questclaim` `/bless`",
        inline=False
    )
    embed.add_field(
        name="💎 Special Features",
        value="• Daily Quest system with tracking\n• Crystal Shard drops (type `!claim` when they appear)\n• Guardian's Blessing system (`/bless @user`)\n• Keyword responses in chat",
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ranks", description="View all available ranks and their requirements")
async def ranks(interaction: discord.Interaction):
    await update_quest_progress(interaction.user.id, 'command', 'ranks')
    
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
async def dbcheck(interaction: discord.Interaction):
    if interaction.user.id != interaction.guild.owner_id:
        await interaction.response.send_message("Only the server owner can check database health!", ephemeral=True)
        return
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) as count FROM users')
        user_count = c.fetchone()['count']
        
        c.execute('SELECT COUNT(*) as count FROM user_quests')
        quest_count = c.fetchone()['count']
        
        c.execute('SELECT COUNT(*) as count FROM quest_progress')
        progress_count = c.fetchone()['count']
        
        embed = discord.Embed(
            title="💾 Database Health Check",
            color=0x00FF00
        )
        embed.add_field(name="Total Users", value=str(user_count), inline=True)
        embed.add_field(name="Total Quests", value=str(quest_count), inline=True)
        embed.add_field(name="Progress Records", value=str(progress_count), inline=True)
        embed.add_field(name="Status", value="✅ All systems operational", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Database error: {str(e)}", ephemeral=True)
    finally:
        if conn:
            release_db_connection(conn)

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_BOT_TOKEN')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    if not TOKEN:
        print("❌ Error: DISCORD_BOT_TOKEN not found in environment variables!")
        print("Please set your bot token in the environment or .env file")
    elif not DATABASE_URL:
        print("❌ Error: DATABASE_URL not found in environment variables!")
        print("Please set your Neon database connection string in the environment or .env file")
    else:
        print("🌐 Starting keep-alive server for Render...")
        keep_alive()
        print("🤖 Starting Discord bot with PostgreSQL database...")
        bot.run(TOKEN)
