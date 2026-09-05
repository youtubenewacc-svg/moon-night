import os
import time
import re
import random
import json
import asyncio
import shutil
import ctypes.util
from datetime import timedelta, datetime, timezone
import discord
import yt_dlp

# Optional at runtime, but required by requirements.txt for the tweet artwork.
try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    PIL_OK = True
except Exception as exc:
    PIL_OK = False
    Image = ImageDraw = ImageFont = ImageOps = None
    print(f"[TWEET IMAGE] Pillow unavailable: {exc!r}")

import io
import urllib.request

try:
    import imageio_ffmpeg
    IMAGEIO_FFMPEG_OK = True
except Exception as exc:
    imageio_ffmpeg = None
    IMAGEIO_FFMPEG_OK = False
    print(f"[FFMPEG DEPENDENCY] imageio-ffmpeg unavailable: {exc!r}")

from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput


# Voice dependency diagnostics
try:
    import nacl
    PYNACL_OK = True
except Exception as exc:
    PYNACL_OK = False
    print(f"[VOICE DEPENDENCY] PyNaCl unavailable: {exc!r}")

try:
    import davey
    DAVEY_OK = True
except Exception as exc:
    DAVEY_OK = False
    print(f"[VOICE DEPENDENCY] davey unavailable: {exc!r}")

# discord.py needs the native Opus library for voice encoding.
# Railway/Nixpacks may place libopus inside /nix/store instead of /usr/lib.
OPUS_OK = False

try:
    if discord.opus.is_loaded():
        OPUS_OK = True
        print("[OPUS] Opus is already loaded.")
    else:
        import glob

        opus_candidates = [
            ctypes.util.find_library("opus"),
            "libopus.so.0",
            "libopus.so",
            "/lib/x86_64-linux-gnu/libopus.so.0",
            "/usr/lib/x86_64-linux-gnu/libopus.so.0",
            "/lib/aarch64-linux-gnu/libopus.so.0",
            "/usr/lib/aarch64-linux-gnu/libopus.so.0",
            "/lib/libopus.so.0",
            "/usr/lib/libopus.so.0",
            "/usr/local/lib/libopus.so.0",
        ]

        # Nixpacks/Nix installs packages under /nix/store.
        # Find libopus there automatically so the bot does not depend
        # on one hard-coded Nix store hash/version.
        opus_candidates.extend(glob.glob(
            "/nix/store/*-libopus-*/lib/libopus.so.0"
        ))
        opus_candidates.extend(glob.glob(
            "/nix/store/*-libopus-*/lib/libopus.so"
        ))
        opus_candidates.extend(glob.glob(
            "/nix/store/*opus*/lib/libopus.so.0"
        ))
        opus_candidates.extend(glob.glob(
            "/nix/store/*opus*/lib/libopus.so"
        ))

        # Remove duplicates while preserving order.
        seen = set()
        opus_candidates = [
            x for x in opus_candidates
            if x and not (x in seen or seen.add(x))
        ]

        for opus_path in opus_candidates:
            try:
                print(f"[OPUS] Trying to load: {opus_path}")
                discord.opus.load_opus(opus_path)

                if discord.opus.is_loaded():
                    OPUS_OK = True
                    print(
                        f"[OPUS] Successfully loaded: {opus_path}"
                    )
                    break

            except Exception as opus_exc:
                print(
                    f"[OPUS] Failed to load {opus_path}: "
                    f"{type(opus_exc).__name__}: {opus_exc!r}"
                )

except Exception as exc:
    print(
        f"[OPUS] Loader error: "
        f"{type(exc).__name__}: {exc!r}"
    )

print(
    f"[VOICE DEPENDENCIES] "
    f"PyNaCl={PYNACL_OK} | "
    f"davey={DAVEY_OK} | "
    f"Opus={OPUS_OK}"
)

# ==========================================
# EASY CUSTOMIZATION — CHANGE YOUR SETTINGS HERE
# ==========================================
# This is the only section you normally need to edit.
# IDs = Discord IDs. Emojis = custom emoji code. Images = image/banner URLs.
# Put 0 for WELCOME/LEAVE if you want those features disabled.
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN")

# 👑 OWNER / LOGGING / IMPORTANT CHANNELS
OWNER_ID = int(os.getenv("OWNER_ID", "1544404824076853258"))          # 👑 Bot owner ID
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1543761123046727691"))  # 🧑‍💼 Legacy / Apply log channel
GENERAL_LOG_CHANNEL_ID = int(os.getenv("GENERAL_LOG_CHANNEL_ID", "1545594641271758848"))    # 🧾 General server audit log
APPLY_LOG_CHANNEL_ID = int(os.getenv("APPLY_LOG_CHANNEL_ID", str(LOG_CHANNEL_ID)))  # 🧑‍💼 Apply/application log
JAIL_ROLE_ID = int(os.getenv("JAIL_ROLE_ID", "1543760861137473536"))                  # ⛓️ Jail role
PROTECTED_ROLE_ID = int(os.getenv("PROTECTED_ROLE_ID", "1543760632988307597"))        # 🛡️ Protected role (optional)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))      # 👋 Welcome channel; 0 = off
LEAVE_CHANNEL_ID = int(os.getenv("LEAVE_CHANNEL_ID", "1543761299769393232"))          # 💔 Leave channel; 0 = off
TEMP_VC_CHANNEL_ID = int(os.getenv("TEMP_VC_CHANNEL_ID", "1543761017342005413")) # 🔊 Temp VC creator
TEMP_VC_DEFAULT_LIMIT = int(os.getenv("TEMP_VC_DEFAULT_LIMIT", "0"))  # 👥 0 = unlimited
TEMP_VC_NAME_PREFIX = os.getenv("TEMP_VC_NAME_PREFIX", "🔊")  # 🔊 Temp room prefix

# 📌 CHANNEL IDs — change the numbers only
CHANNEL_IDS = {
    "news": 1543761099923656705,        # 📰 News
    "rules": 1543761105036386415,       # 📜 Rules
    "self_roles": 1543761138486091867,  # 🎭 Self roles
    "apply": 1543761116281446420,       # 🧑‍💼 Apply/team
    "general": 1482902490549850184,     # 💬 General
    "commands": 1482902491711541328,    # 🤖 Bot commands
    "temp_voice": 1543761017342005413,  # 🔊 Temporary VC

    # 🧵 THREAD / TWEET ROOMS — put 0 if you want to use the current channel
    "tweets": int(os.getenv("TWEETS_CHANNEL_ID", "1543761188557426788")),          # 🐦 Published tweet messages (NOT threads)
    "general_threads": int(os.getenv("GENERAL_THREADS_CHANNEL_ID", "0")),  # 💬 General discussion threads
    "apply_threads": int(os.getenv("APPLY_THREADS_CHANNEL_ID", "0")),      # 🧑‍💼 Application threads (optional)
}

# 🎭 ROLE IDs — change the numbers only
ROLE_IDS = {
    # 🚀 Booster roles
    "booster_nickname": 1543760781441499267,
    "booster_moon": 1543760736659054653,
    "booster_soundboard": 1543760782393745438,
    "booster_pic": 1543760780506431658,
    "booster_link": 1543760779583561848,
    "booster_bughunter": 1543760735325261866,
    "booster_vip": 1543760734662565992,
    "booster_special": 1543760728391950428,

    # 💘 Situation roles
    "heartless": 1543760809820168232,
    "taken": 1543760811737088101,
    "single": 1543760812869419098,

    # 🧑 Gender roles
    "female": 1543760795349946458,
    "male": 1543760793726750790,
    "trans": 1545555471564415017,

    # 🎮 Games roles
    "valorant": 1543760829667745842,
    "freefire": 1543760828598190100,
    "pubg": 1543760842342801569,
    "chess": 1543760830762590209,
    "bloodstrike": 1543760843412344882,
}

# 😀 CUSTOM DISCORD EMOJIS — replace the value in quotes
EMOJIS = {
    "hi": "<:theCall_pink_hi:1509305726655402185>",
    "instagram": "<:INSTA:1532413334261993602>",
    "tiktok": "<:TIKTOK:1532413262669283451>",
    "ig_group": "<:popcornpandita:1529830303483429025>",
    "store": "<:5143storeg:1532413144876585056>",
    "moon": "<:bunny_moon:1532388030411833344>",
    "members": "<:Fams:1451145463511384094>",
    "voice": "<:voice:1451145649801269420>",
    "premium": "<:premium:1451145621246312529>",
    "rules_star": "<a:estrellasbrillando:1442626060134121472>",
    "welcome": "<a:welcome:1442626577690132663>",
    "channel": "<a:channelutility:1444868927262822582>",
    "arrow": "<:arrowblancasincentro:1444869479250002021>",
    "situation": "<a:11pm_redflower:1508777764994416791>",
    "gender": "<:gendersheaven:1421638974287384747>",
    "butterfly": "<a:butterfly:1432369241474076692>",
    "powers": "<a:powersheaven:1400669588596719679>",
    "special": "<a:specialheaven1:1400670272352161815>",
    "special2": "<a:special2heaven:1400670604121739385>",
    "girls": "<a:girlsheaven:1400671165885710386>",
    "remove": "<a:removeheaven:1400671588935798815>",
    "click": "<a:clickheaven:1400671930834747432>",
}

# 🖼️ COMMUNITY IMAGES
# Replace these URLs with your own Discord CDN image links whenever you want.
# No external image host is required.
COMMUNITY_IMAGE_URL = os.getenv(
    "COMMUNITY_IMAGE_URL",
    "https://cdn.discordapp.com/attachments/1544405356258656347/1544728175827755178/octopus_png_banner.png"
)
TWEET_PANEL_IMAGE_URL = os.getenv("TWEET_PANEL_IMAGE_URL", COMMUNITY_IMAGE_URL)

IMAGES = {
    "moon_logo": COMMUNITY_IMAGE_URL,
    "panel_banner": COMMUNITY_IMAGE_URL,
    "role_request": "",  # Leave empty to disable the role-request banner.
}

# 🔗 LINKS — change these when your socials/community links change
LINKS = {
    "instagram": "https://instagram.com",
    "tiktok": "https://tiktok.com",
    "ig_group": "https://instagram.com",
    "store": "https://store.moonnight.com",
    "need_help": "https://discord.com",
    "discord_terms": "https://discord.com/terms",
    "discord_guidelines": "https://discord.com/guidelines",
}

XP_COOLDOWN = 45
DATA_FILE = "moon_night_data.json"

# Music / Voice settings
YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "no_warnings": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0",
}
FFMPEG_BEFORE_OPTIONS = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

# 🎨 Embed color — change this HEX if you want another theme color.
EMBED_COLOR = 0x2b2d31

# 🧾 AUDIT / SERVER LOG ROOMS
# Put one or more channel IDs here, separated by commas.
# Example: "123456789012345678,987654321098765432"
# General audit logs are kept separate from Apply logs.
# You can still use AUDIT_LOG_CHANNEL_IDS for multiple general log rooms.
_general_log_env = os.getenv("AUDIT_LOG_CHANNEL_IDS", "")
if _general_log_env.strip():
    AUDIT_LOG_CHANNEL_IDS = [
        int(x.strip())
        for x in _general_log_env.split(",")
        if x.strip().isdigit() and int(x.strip()) > 0
    ]
else:
    AUDIT_LOG_CHANNEL_IDS = [GENERAL_LOG_CHANNEL_ID] if GENERAL_LOG_CHANNEL_ID > 0 else []

# How far back we search Discord Audit Logs to match the action with its actor.
AUDIT_MATCH_SECONDS = 20

# 🧾 Log appearance / emoji — easy to customize from this section.
LOG_EMOJIS = {
    "member_join": "📥",
    "member_leave": "📤",
    "kick": "👢",
    "ban": "🔨",
    "unban": "🔓",
    "timeout": "⏱️",
    "role_add": "➕",
    "role_remove": "➖",
    "role_create": "🎭",
    "role_delete": "🗑️",
    "role_update": "✏️",
    "channel_create": "📁",
    "channel_delete": "🗑️",
    "channel_update": "📝",
    "thread_create": "🧵",
    "thread_delete": "🗑️",
    "thread_update": "📝",
    "message_delete": "🗑️",
    "message_bulk_delete": "🧹",
    "message_edit": "✏️",
    "invite_create": "🔗",
    "invite_delete": "🔗",
    "emoji_update": "😀",
    "sticker_update": "🏷️",
    "server_update": "⚙️",
    "voice": "🔊",
    "other": "📌",
}

def channel_mention(name: str) -> str:
    channel_id = CHANNEL_IDS.get(name, 0)
    return f"<#{channel_id}>" if channel_id else "#not-configured"

def role_mention(name: str) -> str:
    role_id = ROLE_IDS.get(name, 0)
    return f"<@&{role_id}>" if role_id else "@role-not-configured"

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True


# ==========================================
# MODERATION / SERVER INFO HELPERS
# ==========================================
PROTECTED_USERS = set()
SERVER_PEAK_MEMBERS = {}

def parse_duration(value: str):
    """Accept: 60s, 1m, 6h, 1d. Discord timeout max = 28 days."""
    match = re.fullmatch(
        r"\s*(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\s*",
        value,
        re.IGNORECASE
    )
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if unit in {"s", "sec", "secs", "second", "seconds"}:
        seconds = amount
    elif unit in {"m", "min", "mins", "minute", "minutes"}:
        seconds = amount * 60
    elif unit in {"h", "hr", "hrs", "hour", "hours"}:
        seconds = amount * 3600
    else:
        seconds = amount * 86400

    if seconds <= 0 or seconds > 28 * 86400:
        return None
    return seconds

def format_duration(seconds: int):
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"

def update_peak_members(guild: discord.Guild):
    if guild:
        current = guild.member_count or len(guild.members)
        SERVER_PEAK_MEMBERS[guild.id] = max(
            SERVER_PEAK_MEMBERS.get(guild.id, 0),
            current
        )

def is_protected_member(member: discord.Member):
    return member.id == OWNER_ID or member.id in PROTECTED_USERS

def get_jail_role(guild: discord.Guild):
    if not guild or not JAIL_ROLE_ID:
        return None
    return guild.get_role(JAIL_ROLE_ID)

def get_protected_role(guild: discord.Guild):
    if not guild:
        return None
    if PROTECTED_ROLE_ID:
        role = guild.get_role(PROTECTED_ROLE_ID)
        if role:
            return role
    return discord.utils.get(guild.roles, name="Protected")


# ==========================================
# COMMUNITY / GAMES DATA
# ==========================================
DEFAULT_DATA = {
    "economy": {},
    "xp": {},
    "warnings": {},
    "birthdays": {},
    "suggestions": 0,
    "giveaways": {}
}

def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, default in DEFAULT_DATA.items():
            data.setdefault(key, default.copy() if isinstance(default, dict) else default)
        return data
    except (FileNotFoundError, json.JSONDecodeError):
        return {k: (v.copy() if isinstance(v, dict) else v) for k, v in DEFAULT_DATA.items()}

DATA = load_data()
XP_LAST_MESSAGE = {}
TEMP_VCS = {}
TEMP_VC_META = {}  # channel_id -> {owner, locked, limit, created_at}
MAFIA_GAMES = {}

def save_data():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(DATA, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Data save error: {e}")

def user_key(guild_id, user_id):
    return f"{guild_id}:{user_id}"

def get_wallet(guild_id, user_id):
    key = user_key(guild_id, user_id)
    DATA["economy"].setdefault(key, {"coins": 0, "last_daily": 0})
    return DATA["economy"][key]

def parse_coin_amount(value):
    """Accept coin amounts like 1000, 1k, 1.5k, 1m, 2b."""
    if isinstance(value, int):
        return value if value > 0 else None
    text = str(value).strip().lower().replace(" ", "")
    match = re.fullmatch(r"(\d+(?:\.\d+)?)([kmbt]?)", text)
    if not match:
        return None
    number = float(match.group(1))
    suffix = match.group(2)
    mult = {"": 1, "k": 1_000, "m": 1_000_000, "b": 1_000_000_000, "t": 1_000_000_000_000}[suffix]
    amount = int(number * mult)
    return amount if amount > 0 else None

def format_coins(amount):
    amount = int(amount)
    if amount >= 1_000_000_000_000:
        return f"{amount/1_000_000_000_000:.2f}t".rstrip("0").rstrip(".")
    if amount >= 1_000_000_000:
        return f"{amount/1_000_000_000:.2f}b".rstrip("0").rstrip(".")
    if amount >= 1_000_000:
        return f"{amount/1_000_000:.2f}m".rstrip("0").rstrip(".")
    if amount >= 1_000:
        return f"{amount/1_000:.2f}k".rstrip("0").rstrip(".")
    return f"{amount:,}"

def get_xp(guild_id, user_id):
    key = user_key(guild_id, user_id)
    DATA["xp"].setdefault(key, {"xp": 0, "level": 0})
    return DATA["xp"][key]

def level_for_xp(xp):
    return int((xp / 100) ** 0.5)

def xp_for_next_level(level):
    return (level + 1) ** 2 * 100

class DarkNightBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Register persistent views so buttons stay active after restart
        self.add_view(SocialsView())
        self.add_view(RulesView())
        self.add_view(ApplyView())
        self.add_view(BoosterRolesView())
        self.add_view(SituationRolesView())
        self.add_view(GenderRolesView())
        self.add_view(GamesRolesView())
        self.add_view(RoleRequestView())
        self.add_view(TweetPanelView())
        self.add_view(GamesCenterView())
        self.add_view(TempVCControlView())
        
        await self.tree.sync()
        print("Slash Commands Synced & Persistent Views Registered Successfully!")
        print("[ABOUT] Presence Intent enabled: online/idle/dnd/offline stats are available.")
        for g in self.guilds:
            print(
                f"[ABOUT] {g.name}: member_count={g.member_count}, "
                f"cached_members={len(g.members)}"
            )

bot = DarkNightBot()

def is_owner_or_admin():
    async def predicate(interaction: Interaction):
        if interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ This command is restricted to the server Owner/Admins.", ephemeral=True)
        return False
    return app_commands.check(predicate)


# ==========================================
# 1. SOCIALS PANEL
# ==========================================
class SocialsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Instagram", style=ButtonStyle.link, url=LINKS["instagram"]))
        self.add_item(Button(label="Tiktok", style=ButtonStyle.link, url=LINKS["tiktok"]))
        self.add_item(Button(label="IG Group", style=ButtonStyle.link, url=LINKS["instagram"]))
        self.add_item(Button(label="Store", style=ButtonStyle.link, url=LINKS["store"]))

def get_socials_embed():
    embed = discord.Embed(
        title=f"Hey @everyone {EMOJIS['hi']}",
        description=(
            "-# > 𝗦𝘁𝗮𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝘄𝗶𝘁𝗵 **𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁** 𝗼𝗻 𝗮𝗹𝗹 𝗼𝘂𝗿 𝗽𝗹𝗮𝘁𝗳𝗼𝗿𝗺𝘀.\n\n"
            f"### * {EMOJIS['instagram']} **Instagram :** *** Follow us for news & highlights. ***\n"
            f"### * {EMOJIS['tiktok']} **TikTok :** ***Follow us for videos & updates***\n"
            f"### * {EMOJIS['ig_group']} **IG Group :** *** Stay close to the community. ***\n"
            f"### * {EMOJIS['store']} **Store :** *** Shop exclusive Dark Night items. ***\n\n"
            f"-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑩𝒆𝒎𝒐𝒓𝒊𝒆𝒔 {EMOJIS['moon']}"
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=COMMUNITY_IMAGE_URL)
    return embed


# ==========================================
# 2. STATS PANEL
# ==========================================
class StatsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        total_members = guild.member_count if guild else 0
        voice_count = sum(len(channel.members) for channel in guild.voice_channels) if guild else 0

        self.add_item(Button(label=f"Members : {total_members}", style=ButtonStyle.secondary, disabled=True, custom_id="btn_members"))
        self.add_item(Button(label=f"in Voice : {voice_count}", style=ButtonStyle.secondary, disabled=True, custom_id="btn_voice"))

def get_stats_embed(guild: discord.Guild):
    total_members = guild.member_count if guild else 8628
    voice_count = sum(len(channel.members) for channel in guild.voice_channels) if guild else 107
    boosters_count = guild.premium_subscription_count if guild else 48

    embed = discord.Embed(
        title="Dark Night Statistics",
        description=(
            f"- {EMOJIS['members']} **Total Members:** `{total_members}` ⁘\n"
            f"- {EMOJIS['voice']} **Active in Voice:** `{voice_count}` ⁘\n"
            f"- {EMOJIS['premium']} **Boosters:** `{boosters_count}` ⁘\n\n"
            "Stay active, and enjoy your time in Dark Night"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["panel_banner"])
    embed.set_footer(text="Stay Active, And Enjoy Your Time in @Dark Night")
    return embed


# ==========================================
# 3. RULES PANEL
# ==========================================
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Need Help", style=ButtonStyle.link, url=LINKS["need_help"]))

def get_rules_embed():
    embed = discord.Embed(
        description=(
            "> 𝗧𝗼 𝗺𝗮𝗸𝗲 𝗦𝘂𝗿𝗲 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝗲𝗻𝗷𝗼𝘆 𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗲𝘀𝗲 𝗴𝘂𝗶𝗱𝗲𝗹𝗶𝗻𝗲𝘀:\n\n"
            f"{EMOJIS['rules_star']} **⇝ Follow the [Discord Terms of Service](https://discord.com/terms) and [Community Guidelines](https://discord.com/guidelines).**\n"
            f"{EMOJIS['rules_star']} **⇝ No NSFW content. Violations may result in a Jail action.**\n"
            f"{EMOJIS['rules_star']} **⇝ Respect every member, regardless of their role or status.**\n"
            f"{EMOJIS['rules_star']} **⇝ Abuse of staff powers with valid proof may result in a warning or role removal.**\n"
            f"{EMOJIS['rules_star']} **⇝ Use Need Help for real issues, reports, or assistance. Do not use it for trolling.**\n"
            f"{EMOJIS['rules_star']} **⇝ Do not insult staff, moderators, or high-role members. Report problems instead.**\n"
            f"{EMOJIS['rules_star']} **⇝ Staff members who provoke or abuse their authority may also be punished.**\n"
            f"{EMOJIS['rules_star']} **⇝ Trolling, harassment, spam, and disruptive behavior are not allowed. Keep every room respectful.**\n"
            f"{EMOJIS['rules_star']} **⇝ If a staff member abuses you, report the situation with proof through Need Help.**\n"
            f"{EMOJIS['rules_star']} **⇝ Advertising and unwanted promotion are not allowed. Report spam with a screenshot or recording when possible.**\n\n"
            "**⇾ __Need help? Our team is here to support you.__**\n"
            "**⇾ __Have a problem or report? Use the Need Help button below.__**\n\n"
            "-# `© 2026 Dark Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    embed.set_author(name="⠀" * 15 + "・Dark Night : Rules・" + "⠀" * 15)
    embed.set_image(url=IMAGES["panel_banner"])
    return embed


# ==========================================
# 4. GUIDMAP / SERVER MAP PANEL
# ==========================================
def get_map_embed():
    embed = discord.Embed(
        title=f"{EMOJIS['welcome']} ◜__Welcome To Dark Night!__◞",
        description=(
            f"{EMOJIS['channel']} **⇝ {channel_mention('news')}**\n"
            f"{EMOJIS['arrow']} `Official channel to post the latest news!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('rules')}**\n"
            f"{EMOJIS['arrow']} `Official channel where are the rules are posted, you must check it!!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('self_roles')}**\n"
            f"{EMOJIS['arrow']} `Official channel to get your server profile roles!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('apply')}**\n"
            f"{EMOJIS['arrow']} `Official channel to make your way through community work team!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('general')}**\n"
            f"{EMOJIS['arrow']} `Official channel to chat and having fun with server members!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('commands')}**\n"
            f"{EMOJIS['arrow']} `Official channel to use server bots commands!`\n\n"
            f"{EMOJIS['channel']} **⇝ {channel_mention('temp_voice')}**\n"
            f"{EMOJIS['arrow']} `Official channel to create your temporary voice channel!`\n\n"
            "-# `© 2026 Dark Night. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["panel_banner"])
    return embed


# ==========================================
# 5. APPLY TEAM PANEL
# ==========================================
class ApplyModal(Modal, title="Staff Application Form"):
    age = TextInput(label="How old are you?", placeholder="e.g. 18", min_length=1, max_length=2)
    experience = TextInput(label="Experience & Active Time", style=discord.TextStyle.paragraph, placeholder="Describe your experience...")

    async def on_submit(self, interaction: Interaction):
        log_channel = interaction.guild.get_channel(APPLY_LOG_CHANNEL_ID) if interaction.guild else None
        if log_channel:
            embed = discord.Embed(
                title="🧑‍💼 New Staff Application",
                description=(
                    f"👤 **Applicant:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"📍 **Submitted in:** {interaction.channel.mention if interaction.channel else '`Unknown`'}\n"
                    f"🎂 **Age:** `{str(self.age.value)[:100]}`\n"
                    f"🕒 **Experience / Active Time:**\n{str(self.experience.value)[:1500]}"
                ),
                color=EMBED_COLOR,
                timestamp=datetime.now(timezone.utc),
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text="Dark Night • Apply Logs")
            try:
                await log_channel.send(embed=embed)
            except (discord.Forbidden, discord.HTTPException):
                pass
        await interaction.response.send_message("✅ Dynamic application sent! Staff team will review it.", ephemeral=True)

class ApplyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", style=ButtonStyle.success, custom_id="btn_apply_staff")
    async def apply_staff(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ApplyModal())

    @discord.ui.button(label="Apply for Game Mods", style=ButtonStyle.success, custom_id="btn_apply_gamemods")
    async def apply_gamemods(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(ApplyModal())

def get_apply_embed():
    embed = discord.Embed(
        title="## __Staff Apply For Dark    Night    ©__",
        description=(
            "-# Dark    Night    ©'s now is accepting staff applications! Be a part of our family! We would love to bring new people to our team that would help grow this family together!\n\n"
            "### - __Staff__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "### - __Game Mods__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "-# Copyright © 2026 Lisa X Dark    Night    ©"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["panel_banner"])
    return embed


# ==========================================
# 6. BOOSTERS PERKS / ROLE PANEL
# ==========================================
class BoosterRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

        booster_roles = [
            ("Nickname Perm", ROLE_IDS["booster_nickname"]),
            ("Dark night 's", ROLE_IDS["booster_moon"]),
            ("Soundboard perm", ROLE_IDS["booster_soundboard"]),
            ("Pic Perm", ROLE_IDS["booster_pic"]),
            ("Link Perm", ROLE_IDS["booster_link"]),
            ("Bug hunter", ROLE_IDS["booster_bughunter"]),
            ("Very Important people", ROLE_IDS["booster_vip"]),
            ("Special Member ★", ROLE_IDS["booster_special"])
        ]

        for label, role_id in booster_roles:
            self.add_item(self.create_booster_button(label, role_id))

    def create_booster_button(self, label: str, role_id: int):
        button = Button(label=f"• {label}", style=ButtonStyle.secondary, custom_id=f"booster_{role_id}")
        
        async def button_callback(interaction: Interaction):
            role = interaction.guild.get_role(role_id)
            if not role:
                return await interaction.response.send_message("❌ Role not found on server!", ephemeral=True)
            
            # Only current server boosters can use booster perks.
            if not interaction.user.premium_since:
                return await interaction.response.send_message(
                    "🚀 **Booster Only!** You need to be boosting this server to use these perks.",
                    ephemeral=True
                )

            # Only one booster perk role at a time.
            booster_role_ids = {
                ROLE_IDS["booster_nickname"],
                ROLE_IDS["booster_moon"],
                ROLE_IDS["booster_soundboard"],
                ROLE_IDS["booster_pic"],
                ROLE_IDS["booster_link"],
                ROLE_IDS["booster_bughunter"],
                ROLE_IDS["booster_vip"],
                ROLE_IDS["booster_special"]
            }

            if role in interaction.user.roles:
                await interaction.user.remove_roles(role, reason="Booster perk removed")
                await interaction.response.send_message(
                    f"➖ Removed **{role.name}**!", ephemeral=True
                )
                return

            roles_to_remove = [
                r for r in interaction.user.roles
                if r.id in booster_role_ids and r.id != role_id
            ]

            if roles_to_remove:
                await interaction.user.remove_roles(
                    *roles_to_remove,
                    reason="Switching booster perk role"
                )

            await interaction.user.add_roles(role, reason="Booster perk selected")
            await interaction.response.send_message(
                f"➕ Added **{role.name}**! Your previous booster perk was removed.",
                ephemeral=True
            )

        button.callback = button_callback
        return button

def get_booster_embed():
    embed = discord.Embed(
        title="৳ Choose your booster role",
        description=(
            "-# Pick one of the roles down as a thanks for boosting!\n\n"
            f"> {role_mention('booster_nickname')}\n"
            f"> {role_mention('booster_moon')}\n"
            f"> {role_mention('booster_soundboard')}\n"
            f"> {role_mention('booster_pic')}\n"
            f"> {role_mention('booster_link')}\n"
            f"> {role_mention('booster_bughunter')}\n"
            f"> {role_mention('booster_vip')}\n"
            f"> {role_mention('booster_special')}\n\n"
            "-# © 2026 Dark Night    #ɓαɕƘ's Lisa. All rights reserved."
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["panel_banner"])
    return embed


# ==========================================
# 7. SELF ROLES PANEL (SITUATIONS, GENDER, GAMES)
# ==========================================
# ROLE_IDS is configured in the EASY CUSTOMIZATION section at the top.


async def toggle_role(interaction: Interaction, role_key: str):
    # Buttons/select options use component keys such as role_heartless,
    # while ROLE_IDS stores the real config keys (heartless, taken,
    # single, valorant, freefire, pubg, chess, bloodstrike).
    role_aliases = {
        "role_heartless": "heartless",
        "role_taken": "taken",
        "role_single": "single",
        "role_female": "female",
        "role_male": "male",
        "role_trans": "trans",
        "role_val": "valorant",
        "role_ff": "freefire",
        "role_pubg": "pubg",
        "role_chess": "chess",
        "role_bs": "bloodstrike",
    }
    config_key = role_aliases.get(role_key, role_key)
    role_id = ROLE_IDS.get(config_key)
    role = interaction.guild.get_role(role_id) if role_id else None

    if not role:
        return await interaction.response.send_message(
            f"❌ Role `{config_key}` was not found in this server.\n"
            f"🔑 Configured role ID: `{role_id or 'NOT SET'}`",
            ephemeral=True,
        )
        
    if role in interaction.user.roles:
        await interaction.user.remove_roles(role, reason=f"Self-role removal by {interaction.user} ({interaction.user.id})")
        await interaction.response.send_message(f"➖ Removed **{role.name}**!", ephemeral=True)
        action = "Role Removed"
        emoji = "➖"
    else:
        await interaction.user.add_roles(role, reason=f"Self-role selection by {interaction.user} ({interaction.user.id})")
        await interaction.response.send_message(f"➕ Added **{role.name}**!", ephemeral=True)
        action = "Role Added"
        emoji = "➕"

    # These role buttons know the exact channel where the action happened.
    await send_audit_log(
        interaction.guild,
        title=action,
        emoji=emoji,
        actor=interaction.user,
        target=role,
        channel=interaction.channel,
        extra_fields=[("🧩 Source", "Self-role panel", True), ("🔑 Role ID", f"`{role.id}`", True)],
    )

class SituationRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="• Heartless", style=ButtonStyle.secondary, custom_id="role_heartless")
    async def heartless(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_heartless")

    @discord.ui.button(label="• Taken", style=ButtonStyle.secondary, custom_id="role_taken")
    async def taken(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_taken")

    @discord.ui.button(label="• Single", style=ButtonStyle.secondary, custom_id="role_single")
    async def single(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_single")

class GenderRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="• Female", style=ButtonStyle.secondary, custom_id="role_female")
    async def female(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_female")

    @discord.ui.button(label="• Male", style=ButtonStyle.secondary, custom_id="role_male")
    async def male(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_male")

    @discord.ui.button(label="• Trans", style=ButtonStyle.secondary, custom_id="role_trans")
    async def trans(self, interaction: Interaction, button: Button):
        await toggle_role(interaction, "role_trans")

class GamesRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(
        placeholder="Select A Games Role!",
        options=[
            discord.SelectOption(label="Valorant", description="Select for Valorant Role", value="role_val", emoji="🎮"),
            discord.SelectOption(label="Free Fire", description="Select for Free Fire Role", value="role_ff", emoji="🔥"),
            discord.SelectOption(label="Pubg Mobile", description="Select for PUBG Role", value="role_pubg", emoji="🔫"),
            discord.SelectOption(label="Chess", description="Select for Chess Role", value="role_chess", emoji="♟️"),
            discord.SelectOption(label="Blood Strike", description="Select for Blood Strike Role", value="role_bs", emoji="⚔️"),
        ],
        custom_id="select_games_roles"
    )
    async def select_game_role(self, interaction: Interaction, select: Select):
        await toggle_role(interaction, select.values[0])

def get_self_roles_data():
    e1 = discord.Embed(
        title=f"{EMOJIS['situation']} ⋮ __Situation Roles__ ⊹",
        description=(
            "> ## __What's your actual situation?__\n"
            f"> {role_mention('heartless')}\n"
            f"> {role_mention('taken')}\n"
            f"> {role_mention('single')}\n\n"
            "-# © 2026 Dark Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )

    e2 = discord.Embed(
        title=f"{EMOJIS['gender']} ⋮ __Gender Roles__ ⊹",
        description=(
            "> ## __What's your gender?__\n"
            f"> {role_mention('female')}\n"
            f"> {role_mention('male')}\n"
            f"> {role_mention('trans')}\n\n"
            "-# © 2026 Dark Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )

    e3 = discord.Embed(
        title="🎮 ⋮ __Games Roles__ ⊹",
        description=(
            "> ## __Do you play any games?__\n\n"
            "-# © 2026 Dark Night™. All rights reserved."
        ),
        color=EMBED_COLOR
    )

    return [
        (e1, SituationRolesView()),
        (e2, GenderRolesView()),
        (e3, GamesRolesView())
    ]


# ==========================================
# 8. ROLE REQUEST PANEL (WITH LOGGING)
# ==========================================
class RoleRequestSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Powers", description="Special Functionalities & Privileges", emoji="⚡", value="Powers"),
            discord.SelectOption(label="Special Roles", description="Showcase Your Identity", emoji="💎", value="Special Roles"),
            discord.SelectOption(label="Special Roles 2", description="Given By Owners", emoji="🎩", value="Special Roles 2"),
            discord.SelectOption(label="Girls Roles", description="Designed Especially For Girls", emoji="🌸", value="Girls Roles"),
            discord.SelectOption(label="Remove 1 Of Your Roles", description="Get Rid Of Cringe Roles", emoji="⭐", value="Remove 1 Of Your Roles"),
        ]
        super().__init__(placeholder="Select A Role Category", options=options, custom_id="role_request_dropdown")

    async def callback(self, interaction: Interaction):
        category = self.values[0]
        timestamp = int(time.time())

        await interaction.response.send_message(f"📩 Role request opened for **{category}** category!", ephemeral=True)

        log_channel = interaction.guild.get_channel(APPLY_LOG_CHANNEL_ID)
        if log_channel:
            log_embed = discord.Embed(
                title="📥 New Role Request",
                description=(
                    f"👤 **User:** {interaction.user.mention} (`{interaction.user.id}`)\n"
                    f"🎭 **Category Requested:** `{category}`\n"
                    f"⏰ **Time:** <t:{timestamp}:F> (<t:{timestamp}:R>)"
                ),
                color=0x5865F2
            )
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            log_embed.set_footer(text="Dark Night Logging System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await log_channel.send(embed=log_embed)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleRequestSelect())

def get_role_request_embed():
    embed = discord.Embed(
        title="◜__Dark Night's Role Request Panel__◞",
        description=(
            f"## {EMOJIS['butterfly']} You’ve Officially Unlocked The Right To Beg For Some Fancy Roles :\n\n"
            f"{EMOJIS['powers']} **| Powers**\n"
            "⇝ Unlock Special Functionalities And Privileges Within The Server\n\n"
            f"{EMOJIS['special']} **| Special Roles**\n"
            "⇝ Showcase Your Identity With Distinctive And Stylish Roles\n\n"
            f"{EMOJIS['special2']} **| Special Roles 2 (Only Given By Owners)**\n"
            "⇝ Exclusive Titles Personally Assigned By The Server Owners\n\n"
            f"{EMOJIS['girls']} **| Girls Roles**\n"
            "⇝ Express Your Personality With Roles Designed Especially For Girls\n\n"
            f"{EMOJIS['remove']} **| Remove 1 Of Your Roles**\n"
            "⇝ Get Rid Of That Cringe Role You Picked At 3AM\n\n"
            f"{EMOJIS['click']} | Click The Select Menu Below And Choose Category\n\n"
            "-# **`© 2026 Dark Night™. All rights reserved.`**"
        ),
        color=EMBED_COLOR
    )
    if IMAGES.get("role_request"):
        embed.set_image(url=IMAGES["role_request"])
    return embed



# ==========================================
# 9. 🐦 DARK NIGHT TWEETS
# ==========================================
# Tweets are native Discord embeds:
# - No external image host is required.
# - The member avatar is a small thumbnail.
# - The tweet text is large and clean inside the embed.
# - Dark/Light changes the embed theme.
# - The real Discord member is mentioned in the message.

TWEET_WIDTH = 1200
TWEET_HEIGHT = 675


def _tweet_font(size, bold=False):
    if not PIL_OK:
        return None
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _tweet_wrap(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [""]
    lines, current = [], ""
    for word in words:
        test = word if not current else current + " " + word
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines[:8]


def _download_avatar(url, size=112):
    if not PIL_OK:
        return None
    try:
        req = urllib.request.Request(str(url), headers={"User-Agent": "DarkNightBot/1.0"})
        with urllib.request.urlopen(req, timeout=6) as response:
            raw = response.read()
        avatar = Image.open(io.BytesIO(raw)).convert("RGBA")
        avatar = ImageOps.fit(avatar, (size, size), method=Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        out.paste(avatar, (0, 0), mask)
        return out
    except Exception as exc:
        print(f"[TWEET IMAGE] Avatar load failed: {exc!r}")
        return None


def _draw_avatar_fallback(draw, member, x, y, size, primary, accent):
    draw.ellipse((x, y, x + size, y + size), fill=accent)
    initials = "".join(part[:1] for part in member.display_name.split()[:2]).upper() or "?"
    font = _tweet_font(34, True)
    bbox = draw.textbbox((0, 0), initials, font=font)
    draw.text((x + (size - (bbox[2]-bbox[0]))/2, y + (size - (bbox[3]-bbox[1]))/2 - 4), initials, font=font, fill=primary)


async def create_tweet_image(member: discord.Member, text: str, theme: str):
    """Create the compact tweet card shown inside the Discord embed."""
    if not PIL_OK:
        return None

    dark = theme == "dark"
    bg = (14, 14, 17, 255) if dark else (244, 246, 250, 255)
    card = (22, 23, 27, 255) if dark else (255, 255, 255, 255)
    primary = (247, 248, 250, 255) if dark else (24, 26, 31, 255)
    secondary = (155, 161, 171, 255) if dark else (95, 101, 112, 255)
    divider = (52, 54, 61, 255) if dark else (221, 224, 230, 255)
    accent = (111, 78, 255, 255)
    heart = (235, 68, 92, 255)

    image = Image.new("RGBA", (TWEET_WIDTH, TWEET_HEIGHT), bg)
    draw = ImageDraw.Draw(image)

    # Soft decorative background, without any external image or Imgur dependency.
    draw.ellipse((-220, -260, 520, 460), fill=(45, 38, 90, 150) if dark else (219, 229, 255, 255))
    draw.ellipse((850, -240, 1370, 280), fill=(54, 43, 110, 130) if dark else (220, 232, 255, 255))

    # Compact card — intentionally not full-canvas content.
    cx1, cy1, cx2, cy2 = 78, 105, 1122, 570
    draw.rounded_rectangle((cx1, cy1, cx2, cy2), radius=30, fill=card, outline=(74, 70, 90, 255) if dark else (213, 216, 223, 255), width=2)

    # Header branding.
    title_font = _tweet_font(34, True)
    small_font = _tweet_font(20, False)
    name_font = _tweet_font(31, True)
    handle_font = _tweet_font(21, False)
    body_font = _tweet_font(38, False)
    stat_font = _tweet_font(19, True)

    draw.text((cx1 + 36, 34), "Dark Night Community", font=title_font, fill=primary)
    draw.text((cx1 + 36, 72), "COMMUNITY TWEET", font=small_font, fill=secondary)

    # Small moon mark, no remote logo required.
    draw.ellipse((1030, 38, 1070, 78), fill=accent)
    draw.ellipse((1044, 30, 1075, 66), fill=bg)

    avatar_size = 86
    ax, ay = cx1 + 38, cy1 + 36
    avatar = await asyncio.to_thread(_download_avatar, member.display_avatar.url, avatar_size)
    if avatar:
        image.paste(avatar, (ax, ay), avatar)
        draw.ellipse((ax - 3, ay - 3, ax + avatar_size + 3, ay + avatar_size + 3), outline=accent, width=4)
    else:
        _draw_avatar_fallback(draw, member, ax, ay, avatar_size, primary, accent)

    name_x = ax + avatar_size + 24
    draw.text((name_x, ay + 3), member.display_name[:28], font=name_font, fill=primary)
    verified_x = name_x + draw.textbbox((0, 0), member.display_name[:28], font=name_font)[2] + 10
    draw.ellipse((verified_x, ay + 10, verified_x + 24, ay + 34), fill=accent)
    check_font = _tweet_font(17, True)
    draw.text((verified_x + 6, ay + 9), "✓", font=check_font, fill=(255,255,255,255))
    draw.text((name_x, ay + 42), f"@{member.name}", font=handle_font, fill=secondary)

    # Theme pill.
    pill_text = "DARK TWEET" if dark else "WHITE TWEET"
    pill_font = _tweet_font(18, True)
    pb = draw.textbbox((0, 0), pill_text, font=pill_font)
    pw = pb[2] - pb[0] + 34
    draw.rounded_rectangle((cx2 - pw - 28, cy1 + 34, cx2 - 28, cy1 + 72), radius=19, fill=accent if dark else (231, 235, 242, 255))
    draw.text((cx2 - pw - 11, cy1 + 43), pill_text, font=pill_font, fill=(255,255,255,255) if dark else primary)

    # Tweet body.
    lines = _tweet_wrap(draw, " ".join(text.strip().split()), body_font, cx2 - cx1 - 90)
    body_y = cy1 + 145
    for line in lines:
        draw.text((cx1 + 38, body_y), line, font=body_font, fill=primary)
        body_y += 48

    # Footer stats in ONE ROW, as requested.
    divider_y = cy2 - 92
    draw.line((cx1 + 38, divider_y, cx2 - 38, divider_y), fill=divider, width=2)
    stats_y = divider_y + 28
    stats = [("◉", "0 Replies", secondary), ("♥", "0 Likes", heart), ("◌", "0 Views", secondary)]
    sx = cx1 + 38
    for icon, label, color in stats:
        draw.text((sx, stats_y), icon, font=stat_font, fill=color)
        ib = draw.textbbox((0, 0), icon, font=stat_font)
        draw.text((sx + (ib[2]-ib[0]) + 9, stats_y), label, font=stat_font, fill=primary)
        sx += 205

    # Bottom-right time/date and community branding.
    now = datetime.now(timezone.utc)
    time_font = _tweet_font(18, False)
    date_text = now.strftime("%H:%M • %d %B %Y")
    draw.text((cx1 + 38, cy2 + 10), date_text, font=time_font, fill=secondary)
    brand = "Dark Night Community"
    bb = draw.textbbox((0, 0), brand, font=time_font)
    draw.text((cx2 - 38 - (bb[2]-bb[0]), cy2 + 10), brand, font=time_font, fill=secondary)

    output = io.BytesIO()
    image.convert("RGB").save(output, format="PNG", optimize=True)
    output.seek(0)
    return output


class TweetModal(Modal):
    def __init__(self, theme: str):
        self.theme = theme
        super().__init__(title="Dark Tweet" if theme == "dark" else "White Tweet")
        self.thought = TextInput(
            label="Your thought",
            placeholder="Write your tweet...",
            style=discord.TextStyle.paragraph,
            min_length=1,
            max_length=700,
            required=True,
        )
        self.add_item(self.thought)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        post_channel_id = CHANNEL_IDS.get("tweets", 0)
        post_channel = (
            interaction.guild.get_channel(post_channel_id)
            if interaction.guild and post_channel_id
            else None
        )

        if not isinstance(post_channel, discord.TextChannel):
            return await interaction.followup.send(
                "❌ Tweet channel is not configured for this server.\n"
                f"🔑 Current `CHANNEL_IDS['tweets']`: `{post_channel_id or 'NOT SET'}`\n"
                "➡️ Put the ID of the text channel where tweets must be posted in `CHANNEL_IDS['tweets']`.",
                ephemeral=True,
            )

        permissions = post_channel.permissions_for(interaction.guild.me)
        if not permissions.view_channel or not permissions.send_messages or not permissions.embed_links or not permissions.attach_files:
            return await interaction.followup.send(
                "❌ I found the tweet channel, but I don't have the required permissions there.\n"
                "I need: **View Channel + Send Messages + Embed Links + Attach Files**.",
                ephemeral=True,
            )

        tweet_text = " ".join(self.thought.value.strip().split())
        now = datetime.now(timezone.u... (130 Ko restants)
