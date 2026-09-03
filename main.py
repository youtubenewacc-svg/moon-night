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
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1544405575314440342"))  # 🧑‍💼 Legacy / Apply log channel
GENERAL_LOG_CHANNEL_ID = int(os.getenv("GENERAL_LOG_CHANNEL_ID", "0"))    # 🧾 General server audit log
APPLY_LOG_CHANNEL_ID = int(os.getenv("APPLY_LOG_CHANNEL_ID", str(LOG_CHANNEL_ID)))  # 🧑‍💼 Apply/application log
JAIL_ROLE_ID = int(os.getenv("JAIL_ROLE_ID", "0"))                  # ⛓️ Jail role
PROTECTED_ROLE_ID = int(os.getenv("PROTECTED_ROLE_ID", "0"))        # 🛡️ Protected role (optional)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))      # 👋 Welcome channel; 0 = off
LEAVE_CHANNEL_ID = int(os.getenv("LEAVE_CHANNEL_ID", "0"))          # 💔 Leave channel; 0 = off
TEMP_VC_CHANNEL_ID = int(os.getenv("TEMP_VC_CHANNEL_ID", "1544406112097411072")) # 🔊 Temp VC creator
TEMP_VC_DEFAULT_LIMIT = int(os.getenv("TEMP_VC_DEFAULT_LIMIT", "0"))  # 👥 0 = unlimited
TEMP_VC_NAME_PREFIX = os.getenv("TEMP_VC_NAME_PREFIX", "🔊")  # 🔊 Temp room prefix
VOICE_PANEL_CHANNEL_ID = int(os.getenv("VOICE_PANEL_CHANNEL_ID", "1544405711100969094"))  # 💬 Normal text channel where the panel is posted

# 📌 CHANNEL IDs — change the numbers only
CHANNEL_IDS = {
    "news": 1482902413554745638,        # 📰 News
    "rules": 1482902414997852381,       # 📜 Rules
    "self_roles": 1482902461168615465,  # 🎭 Self roles
    "apply": 1482902427064864833,       # 🧑‍💼 Apply/team
    "general": 1482902490549850184,     # 💬 General
    "commands": 1482902491711541328,    # 🤖 Bot commands
    "temp_voice": 1482902422065123338,  # 🔊 Temporary VC

    # 🧵 THREAD / TWEET ROOMS — put 0 if you want to use the current channel
    "tweets": int(os.getenv("TWEETS_CHANNEL_ID", "1544405375632015552")),          # 🐦 Published tweet messages (NOT threads)
    "general_threads": int(os.getenv("GENERAL_THREADS_CHANNEL_ID", "0")),  # 💬 General discussion threads
    "apply_threads": int(os.getenv("APPLY_THREADS_CHANNEL_ID", "0")),      # 🧑‍💼 Application threads (optional)
}

# 🎭 ROLE IDs — change the numbers only
ROLE_IDS = {
    # 🚀 Booster roles
    "booster_nickname": 1523714779032584363,
    "booster_moon": 1508497154313027675,
    "booster_soundboard": 1482902118137462896,
    "booster_pic": 1482902117693001898,
    "booster_link": 1482902116858331217,
    "booster_bughunter": 1482902047236952117,
    "booster_vip": 1482902046653943870,
    "booster_special": 1482902043558547650,

    # 💘 Situation roles
    "heartless": 1482902155219304549,
    "taken": 1482902157324849333,
    "single": 1482902156364484661,

    # 🧑 Gender roles
    "female": 1482902134071754832,
    "male": 1482902134545580123,
    "trans": 1482902135000000000,

    # 🎮 Games roles
    "valorant": 1482902200000000001,
    "freefire": 1482902200000000002,
    "pubg": 1482902200000000003,
    "chess": 1482902200000000004,
    "bloodstrike": 1482902200000000005,
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
        self.add_view(TicketPanelView())
        self.add_view(GamesCenterView())
        self.add_view(TempVCControlView())
        self.add_view(VoicePanelView())
        
        await self.tree.sync()
        print("Slash Commands Synced & Persistent Views Registered Successfully!")

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
    role_id = ROLE_IDS.get(role_key)
    role = interaction.guild.get_role(role_id) if role_id else None
    
    if not role:
        return await interaction.response.send_message(f"❌ Role for `{role_key}` is not configured or not found!", ephemeral=True)
        
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
# Dark + Light tweet artwork.
# Both themes use the EXACT same layout; only the colors/background change.
# Light Tweet = clean white card + blue Moon Night decoration.

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

    lines = []
    current = ""

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
        req = urllib.request.Request(
            str(url),
            headers={"User-Agent": "DarkNightBot/1.0"},
        )

        with urllib.request.urlopen(req, timeout=6) as response:
            raw = response.read()

        avatar = Image.open(io.BytesIO(raw)).convert("RGBA")
        avatar = ImageOps.fit(
            avatar,
            (size, size),
            method=Image.Resampling.LANCZOS,
        )

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).ellipse(
            (0, 0, size, size),
            fill=255,
        )

        out = Image.new(
            "RGBA",
            (size, size),
            (0, 0, 0, 0),
        )

        out.paste(avatar, (0, 0), mask)
        return out

    except Exception as exc:
        print(f"[TWEET IMAGE] Avatar load failed: {exc!r}")
        return None


def _draw_avatar_fallback(
    draw,
    member,
    x,
    y,
    size,
    primary,
    accent,
):
    draw.ellipse(
        (x, y, x + size, y + size),
        fill=accent,
    )

    initials = (
        "".join(
            part[:1]
            for part in member.display_name.split()[:2]
        ).upper()
        or "?"
    )

    font = _tweet_font(34, True)
    bbox = draw.textbbox(
        (0, 0),
        initials,
        font=font,
    )

    draw.text(
        (
            x + (size - (bbox[2] - bbox[0])) / 2,
            y + (size - (bbox[3] - bbox[1])) / 2 - 4,
        ),
        initials,
        font=font,
        fill=primary,
    )


async def create_tweet_image(
    member: discord.Member,
    text: str,
    theme: str,
):
    """
    Create the tweet artwork.

    Dark:
        Dark background + dark card + white text.

    Light:
        White/light background + pure white card + dark text
        + blue Moon Night decoration.

    IMPORTANT:
    The layout is identical for both themes.
    Only colors/decorations change.
    """

    if not PIL_OK:
        return None

    dark = theme == "dark"

    # ======================================================
    # THEME COLORS
    # ======================================================

    if dark:
        bg = (13, 14, 18, 255)
        card = (22, 23, 27, 255)
        primary = (247, 248, 250, 255)
        secondary = (155, 161, 171, 255)
        divider = (52, 54, 61, 255)
        accent = (111, 78, 255, 255)
        accent_soft = (45, 38, 90, 180)
        accent_soft_2 = (54, 43, 110, 150)
        card_outline = (74, 70, 90, 255)
        pill_bg = accent
        pill_text_color = (255, 255, 255, 255)
        moon_bg = bg

    else:
        # LIGHT TWEET:
        # clean white/blue design matching the requested reference.
        bg = (244, 247, 252, 255)
        card = (255, 255, 255, 255)
        primary = (24, 27, 34, 255)
        secondary = (91, 99, 112, 255)
        divider = (220, 224, 232, 255)
        accent = (48, 111, 237, 255)
        accent_soft = (215, 229, 255, 255)
        accent_soft_2 = (226, 236, 255, 255)
        card_outline = (211, 217, 228, 255)
        pill_bg = accent
        pill_text_color = (255, 255, 255, 255)
        moon_bg = bg

    heart = (235, 68, 92, 255)

    image = Image.new(
        "RGBA",
        (TWEET_WIDTH, TWEET_HEIGHT),
        bg,
    )

    draw = ImageDraw.Draw(image)

    # ======================================================
    # DECORATIVE BACKGROUND
    # ======================================================

    if dark:
        draw.ellipse(
            (-220, -260, 520, 460),
            fill=accent_soft,
        )
        draw.ellipse(
            (850, -240, 1370, 280),
            fill=accent_soft_2,
        )
    else:
        # Soft blue waves/circles like the Light Tweet reference.
        draw.ellipse(
            (-260, -300, 540, 470),
            fill=accent_soft,
        )
        draw.ellipse(
            (865, -255, 1390, 275),
            fill=accent_soft_2,
        )

        # Small decorative dots.
        dot_points = [
            (125, 82, 5),
            (180, 58, 3),
            (235, 96, 4),
            (1010, 78, 4),
            (1075, 115, 3),
            (1115, 62, 4),
        ]

        for dx, dy, radius in dot_points:
            draw.ellipse(
                (
                    dx - radius,
                    dy - radius,
                    dx + radius,
                    dy + radius,
                ),
                fill=accent,
            )

    # ======================================================
    # MAIN CARD
    # ======================================================

    cx1, cy1, cx2, cy2 = 78, 105, 1122, 570

    draw.rounded_rectangle(
        (cx1, cy1, cx2, cy2),
        radius=30,
        fill=card,
        outline=card_outline,
        width=2,
    )

    # ======================================================
    # FONTS
    # ======================================================

    title_font = _tweet_font(34, True)
    small_font = _tweet_font(20, False)
    name_font = _tweet_font(31, True)
    handle_font = _tweet_font(21, False)
    body_font = _tweet_font(38, False)
    stat_font = _tweet_font(19, True)
    pill_font = _tweet_font(18, True)
    check_font = _tweet_font(17, True)
    time_font = _tweet_font(18, False)

    # ======================================================
    # HEADER BRANDING
    # ======================================================

    draw.text(
        (cx1 + 36, 34),
        "Dark Night Community",
        font=title_font,
        fill=primary,
    )

    draw.text(
        (cx1 + 36, 72),
        "COMMUNITY TWEET",
        font=small_font,
        fill=secondary,
    )

    # ======================================================
    # MOON ICON
    # ======================================================

    draw.ellipse(
        (1030, 38, 1070, 78),
        fill=accent,
    )

    draw.ellipse(
        (1044, 30, 1075, 66),
        fill=moon_bg,
    )

    # ======================================================
    # USER AVATAR
    # ======================================================

    avatar_size = 86
    ax = cx1 + 38
    ay = cy1 + 36

    avatar = await asyncio.to_thread(
        _download_avatar,
        member.display_avatar.url,
        avatar_size,
    )

    if avatar:
        image.paste(
            avatar,
            (ax, ay),
            avatar,
        )

        draw.ellipse(
            (
                ax - 3,
                ay - 3,
                ax + avatar_size + 3,
                ay + avatar_size + 3,
            ),
            outline=accent,
            width=4,
        )

    else:
        _draw_avatar_fallback(
            draw,
            member,
            ax,
            ay,
            avatar_size,
            primary,
            accent,
        )

    # ======================================================
    # USER NAME + VERIFIED
    # ======================================================

    name_x = ax + avatar_size + 24
    display_name = member.display_name[:28]

    draw.text(
        (name_x, ay + 3),
        display_name,
        font=name_font,
        fill=primary,
    )

    name_width = draw.textbbox(
        (0, 0),
        display_name,
        font=name_font,
    )[2]

    verified_x = name_x + name_width + 10

    draw.ellipse(
        (
            verified_x,
            ay + 10,
            verified_x + 24,
            ay + 34,
        ),
        fill=accent,
    )

    draw.text(
        (verified_x + 6, ay + 9),
        "✓",
        font=check_font,
        fill=(255, 255, 255, 255),
    )

    draw.text(
        (name_x, ay + 42),
        f"@{member.name}",
        font=handle_font,
        fill=secondary,
    )

    # ======================================================
    # THEME PILL
    # ======================================================

    pill_text = "DARK TWEET" if dark else "LIGHT TWEET"

    pb = draw.textbbox(
        (0, 0),
        pill_text,
        font=pill_font,
    )

    pw = pb[2] - pb[0] + 34

    draw.rounded_rectangle(
        (
            cx2 - pw - 28,
            cy1 + 34,
            cx2 - 28,
            cy1 + 72,
        ),
        radius=19,
        fill=pill_bg,
    )

    draw.text(
        (cx2 - pw - 11, cy1 + 43),
        pill_text,
        font=pill_font,
        fill=pill_text_color,
    )

    # ======================================================
    # TWEET BODY
    # ======================================================

    clean_text = " ".join(
        text.strip().split()
    )

    lines = _tweet_wrap(
        draw,
        clean_text,
        body_font,
        cx2 - cx1 - 90,
    )

    body_y = cy1 + 145

    for line in lines:
        draw.text(
            (cx1 + 38, body_y),
            line,
            font=body_font,
            fill=primary,
        )
        body_y += 48

    # ======================================================
    # FOOTER STATS — ONE ROW
    # ======================================================

    divider_y = cy2 - 92

    draw.line(
        (
            cx1 + 38,
            divider_y,
            cx2 - 38,
            divider_y,
        ),
        fill=divider,
        width=2,
    )

    stats_y = divider_y + 28

    stats = [
        ("◉", "0 Replies", secondary),
        ("♥", "0 Likes", heart),
        ("◌", "0 Views", secondary),
    ]

    sx = cx1 + 38

    for icon, label, stat_color in stats:
        draw.text(
            (sx, stats_y),
            icon,
            font=stat_font,
            fill=stat_color,
        )

        ib = draw.textbbox(
            (0, 0),
            icon,
            font=stat_font,
        )

        draw.text(
            (
                sx + (ib[2] - ib[0]) + 9,
                stats_y,
            ),
            label,
            font=stat_font,
            fill=primary,
        )

        sx += 205

    # ======================================================
    # TIME + BRANDING
    # ======================================================

    now = datetime.now(timezone.utc)

    date_text = now.strftime(
        "%H:%M • %d %B %Y"
    )

    draw.text(
        (cx1 + 38, cy2 + 10),
        date_text,
        font=time_font,
        fill=secondary,
    )

    brand = "Dark Night Community"

    bb = draw.textbbox(
        (0, 0),
        brand,
        font=time_font,
    )

    draw.text(
        (
            cx2 - 38 - (bb[2] - bb[0]),
            cy2 + 10,
        ),
        brand,
        font=time_font,
        fill=secondary,
    )

    # ======================================================
    # EXPORT
    # ======================================================

    output = io.BytesIO()

    image.convert("RGB").save(
        output,
        format="PNG",
        optimize=True,
    )

    output.seek(0)

    return output


class TweetModal(Modal):
    def __init__(self, theme: str):
        self.theme = theme

        super().__init__(
            title="Dark Tweet"
            if theme == "dark"
            else "Light Tweet"
        )

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
        await interaction.response.defer(
            ephemeral=True
        )

        post_channel_id = CHANNEL_IDS.get(
            "tweets",
            0,
        )

        post_channel = (
            interaction.guild.get_channel(
                post_channel_id
            )
            if interaction.guild
            and post_channel_id
            else None
        )

        if not isinstance(
            post_channel,
            discord.TextChannel,
        ):
            return await interaction.followup.send(
                "❌ Tweet channel is not configured. "
                "Set `CHANNEL_IDS['tweets']` at the top of `main.py`.",
                ephemeral=True,
            )

        tweet_text = " ".join(
            self.thought.value.strip().split()
        )

        now = datetime.now(timezone.utc)

        image_bytes = await create_tweet_image(
            interaction.user,
            tweet_text,
            self.theme,
        )

        # The Discord embed is only the outer frame.
        # The complete tweet design is rendered as PNG.
        embed = discord.Embed(
            title=(
                f"🐦 New Tweet By · "
                f"@{interaction.user.name}"
            ),
            color=(
                0x111318
                if self.theme == "dark"
                else 0x2F6FED
            ),
            timestamp=now,
        )

        embed.set_footer(
            text="Dark Night Community • Share your thoughts"
        )

        if image_bytes is not None:
            file = discord.File(
                image_bytes,
                filename="dark_night_tweet.png",
            )

            embed.set_image(
                url="attachment://dark_night_tweet.png"
            )

            published_message = await post_channel.send(
                content=interaction.user.mention,
                embed=embed,
                file=file,
                allowed_mentions=discord.AllowedMentions(
                    users=[interaction.user]
                ),
            )

        else:
            # Clean fallback if Pillow is unavailable.
            embed.add_field(
                name="💬 Replies",
                value="`0`",
                inline=True,
            )

            embed.add_field(
                name="❤️ Likes",
                value="`0`",
                inline=True,
            )

            embed.add_field(
                name="👁️ Views",
                value="`0`",
                inline=True,
            )

            published_message = await post_channel.send(
                content=interaction.user.mention,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(
                    users=[interaction.user]
                ),
            )

        jump_url = (
            f"https://discord.com/channels/"
            f"{interaction.guild.id}/"
            f"{post_channel.id}/"
            f"{published_message.id}"
        )

        success = discord.Embed(
            title="✅ Tweet Posted",
            description=(
                f"Your tweet is live in "
                f"{post_channel.mention}.\n"
                f"[Jump to tweet]({jump_url})"
            ),
            color=0x57F287,
        )

        await interaction.followup.send(
            embed=success,
            ephemeral=True,
        )

        await send_audit_log(
            interaction.guild,
            title="🐦 Tweet Published",
            actor=interaction.user,
            target=interaction.user,
            channel=post_channel,
            extra_fields=[
                (
                    "Theme",
                    (
                        "Dark Tweet"
                        if self.theme == "dark"
                        else "Light Tweet"
                    ),
                    True,
                ),
                (
                    "Content",
                    tweet_text[:1024],
                    False,
                ),
            ],
        )


class TweetPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Dark Tweet",
        emoji="🖤",
        style=ButtonStyle.secondary,
        custom_id="tweet_dark",
    )
    async def dark_tweet(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await interaction.response.send_modal(
            TweetModal("dark")
        )

    @discord.ui.button(
        label="Light Tweet",
        emoji="🤍",
        style=ButtonStyle.secondary,
        custom_id="tweet_light",
    )
    async def light_tweet(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await interaction.response.send_modal(
            TweetModal("light")
        )



def get_tweet_panel_embed():
    embed = discord.Embed(
        title="🐦  Dark Night Community Tweets  ›",
        description=(
            "## ▷ Share your thoughts with the community!\n\n"
            "**Choose a style below and write your tweet.**\n\n"
            "🖤 **Dark Tweet** — dark embed with bright text.\n"
            "🤍 **Light Tweet** — clean white design with dark text.\n\n"
            "Each tweet includes your Discord avatar, username, timestamp, "
            "and community engagement counters."
        ),
        color=EMBED_COLOR,
    )
    if TWEET_PANEL_IMAGE_URL:
        embed.set_thumbnail(url=TWEET_PANEL_IMAGE_URL)
    embed.set_footer(text="Dark Night Community • Tweets • Choose a style below")
    return embed


@bot.tree.command(name="threads", description="Create a public thread in a configured Dark Night channel (not Tweets)")
@app_commands.describe(destination="Where the thread should be created", name="Thread name")
@app_commands.choices(destination=[
    app_commands.Choice(name="General Threads", value="general_threads"),
    app_commands.Choice(name="Apply Threads", value="apply_threads"),
])
@is_owner_or_admin()
async def threads(interaction: Interaction, destination: app_commands.Choice[str], name: str):
    if destination.value == "tweets":
        return await interaction.response.send_message("❌ Tweets are posted as normal messages, not threads.", ephemeral=True)
    channel_id = CHANNEL_IDS.get(destination.value, 0)
    channel = interaction.guild.get_channel(channel_id) if interaction.guild and channel_id else None
    if not isinstance(channel, discord.TextChannel):
        return await interaction.response.send_message(
            f"❌ `{destination.value}` channel is not configured. Put its ID in `CHANNEL_IDS` at the top of `main.py`.",
            ephemeral=True,
        )
    try:
        thread = await channel.create_thread(
            name=name[:100],
            type=discord.ChannelType.public_thread,
            auto_archive_duration=1440,
            reason=f"Thread created by {interaction.user} ({interaction.user.id})",
        )
        await interaction.response.send_message(
            f"🧵 Thread created: {thread.mention}\n📍 Channel: {channel.mention}",
            ephemeral=True,
        )
    except (discord.Forbidden, discord.HTTPException) as exc:
        await interaction.response.send_message(
            f"❌ Couldn't create the thread: `{type(exc).__name__}`.",
            ephemeral=True,
        )


# ==========================================
# 9. MODERATION COMMANDS
# ==========================================

@bot.tree.command(name="mutechat", description="Timeout a member in chat")
@app_commands.describe(
    user="Member to mute",
    duration="Duration: 60s, 1m, 6h, 1d (max 28d)"
)
@is_owner_or_admin()
async def mutechat(interaction: Interaction, user: discord.Member, duration: str):
    if is_protected_member(user):
        return await interaction.response.send_message(
            "🛡️ This member is **Protected** and cannot be muted by the bot.",
            ephemeral=True
        )

    seconds = parse_duration(duration)
    if seconds is None:
        return await interaction.response.send_message(
            "❌ Invalid duration. Examples: `60s`, `1m`, `6h`, `1d` — maximum `28d`.",
            ephemeral=True
        )

    try:
        await user.timeout(
            timedelta(seconds=seconds),
            reason=f"Chat mute by {interaction.user}"
        )
        await interaction.response.send_message(
            f"🔇 {user.mention} muted for **{format_duration(seconds)}**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't timeout this member. Check my role hierarchy and permissions.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord refused the timeout request.",
            ephemeral=True
        )


@bot.tree.command(name="unmutechat", description="Remove a member's chat timeout")
@app_commands.describe(user="Member to unmute")
@is_owner_or_admin()
async def unmutechat(interaction: Interaction, user: discord.Member):
    try:
        await user.timeout(None, reason=f"Chat unmute by {interaction.user}")
        await interaction.response.send_message(
            f"🔊 {user.mention} has been **unmuted in chat**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't remove this timeout.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord refused the unmute request.",
            ephemeral=True
        )


@bot.tree.command(name="mutevc", description="Server mute a member in voice")
@app_commands.describe(user="Member to mute in VC")
@is_owner_or_admin()
async def mutevc(interaction: Interaction, user: discord.Member):
    if is_protected_member(user):
        return await interaction.response.send_message(
            "🛡️ This member is **Protected** and cannot be VC muted by the bot.",
            ephemeral=True
        )

    if not user.voice:
        return await interaction.response.send_message(
            "❌ This member is not currently in a voice channel.",
            ephemeral=True
        )

    try:
        await user.edit(mute=True, reason=f"VC mute by {interaction.user}")
        await interaction.response.send_message(
            f"🔇 {user.mention} is now **server-muted in VC**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't server-mute this member. Check permissions/role hierarchy.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord refused the VC mute request.",
            ephemeral=True
        )


@bot.tree.command(name="unmutevc", description="Remove a member's server VC mute")
@app_commands.describe(user="Member to unmute in VC")
@is_owner_or_admin()
async def unmutevc(interaction: Interaction, user: discord.Member):
    try:
        await user.edit(mute=False, reason=f"VC unmute by {interaction.user}")
        await interaction.response.send_message(
            f"🔊 {user.mention} has been **unmuted in VC**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't remove the VC mute.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message(
            "❌ Discord refused the VC unmute request.",
            ephemeral=True
        )


@bot.tree.command(name="antinuke", description="Protect a member from bot moderation")
@app_commands.describe(user="Member to protect")
@is_owner_or_admin()
async def antinuke(interaction: Interaction, user: discord.Member):
    if user.id == OWNER_ID:
        return await interaction.response.send_message(
            "🛡️ The owner is already permanently protected.",
            ephemeral=True
        )

    PROTECTED_USERS.add(user.id)

    protected_role = get_protected_role(interaction.guild)
    if protected_role is None:
        try:
            protected_role = await interaction.guild.create_role(
                name="Protected",
                reason=f"Antinuke protection enabled by {interaction.user}"
            )
        except discord.Forbidden:
            protected_role = None

    if protected_role and protected_role not in user.roles:
        try:
            await user.add_roles(
                protected_role,
                reason="Antinuke protection"
            )
        except discord.Forbidden:
            pass

    await interaction.response.send_message(
        f"🛡️ {user.mention} is now **Protected**."
        + (" The `Protected` role was added." if protected_role else "")
    )


@bot.tree.command(name="jail", description="Give the configured Jail role to a member")
@app_commands.describe(user="Member to jail")
@is_owner_or_admin()
async def jail(interaction: Interaction, user: discord.Member):
    if is_protected_member(user):
        return await interaction.response.send_message(
            "🛡️ This member is **Protected** and cannot be jailed by the bot.",
            ephemeral=True
        )

    jail_role = get_jail_role(interaction.guild)
    if not jail_role:
        return await interaction.response.send_message(
            "❌ Jail role is not configured. Set `JAIL_ROLE_ID` first.",
            ephemeral=True
        )

    try:
        await user.add_roles(jail_role, reason=f"Jail by {interaction.user}")
        await interaction.response.send_message(
            f"⛓️ {user.mention} has been **Jailed**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't add the Jail role. Put the bot's role above the Jail role.",
            ephemeral=True
        )


@bot.tree.command(name="about", description="Show detailed server information")
async def about(interaction: Interaction):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message(
            "❌ This command can only be used in a server.",
            ephemeral=True
        )

    update_peak_members(guild)

    total = guild.member_count or len(guild.members)
    active = sum(
        1 for m in guild.members
        if m.status in {
            discord.Status.online,
            discord.Status.idle,
            discord.Status.dnd
        }
    )
    offline = max(total - active, 0)
    roles = len(guild.roles)
    channels = len(guild.channels)
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    stage_channels = len(guild.stage_channels)
    boosters = guild.premium_subscription_count or 0
    peak = SERVER_PEAK_MEMBERS.get(guild.id, total)
    voice_members = sum(len(c.members) for c in guild.voice_channels)

    embed = discord.Embed(
        title=f"ℹ️ {guild.name} — Server Information",
        color=EMBED_COLOR
    )

    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    created = int(guild.created_at.timestamp())

    embed.add_field(
        name="📅 Created",
        value=f"<t:{created}:F>\n<t:{created}:R>",
        inline=False
    )
    embed.add_field(name="👥 Members", value=f"`{total}`", inline=True)
    embed.add_field(name="🟢 Active", value=f"`{active}`", inline=True)
    embed.add_field(name="⚫ Offline", value=f"`{offline}`", inline=True)
    embed.add_field(name="📈 Peak Members", value=f"`{peak}`", inline=True)
    embed.add_field(name="🚀 Boosters", value=f"`{boosters}`", inline=True)
    embed.add_field(name="🎭 Roles", value=f"`{roles}`", inline=True)
    embed.add_field(name="💬 Text Rooms", value=f"`{text_channels}`", inline=True)
    embed.add_field(name="🔊 Voice Rooms", value=f"`{voice_channels}`", inline=True)
    embed.add_field(name="🎙️ Stage Rooms", value=f"`{stage_channels}`", inline=True)
    embed.add_field(name="🎧 In Voice", value=f"`{voice_members}`", inline=True)
    embed.add_field(name="📁 Total Channels", value=f"`{channels}`", inline=True)

    embed.set_footer(text="Dark Night • Server Information")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="invite", description="Get the bot's invite link")
async def invite(interaction: Interaction):
    invite_url = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True),
        scopes=("bot", "applications.commands")
    )

    embed = discord.Embed(
        title="🤖 Invite Dark Night Bot",
        description="Use the button below to invite Dark Night Bot to another server.",
        color=EMBED_COLOR
    )

    view = View(timeout=300)
    view.add_item(
        Button(
            label="Invite Bot",
            style=ButtonStyle.link,
            url=invite_url
        )
    )

    await interaction.response.send_message(
        embed=embed,
        view=view,
        ephemeral=True
    )


# ==========================================
# 🧾 DARK NIGHT — FULL SERVER LOGGING SYSTEM
# ==========================================
# Logs are sent to every channel listed in AUDIT_LOG_CHANNEL_IDS.
# Discord Audit Logs are used whenever possible so the embed shows:
# 👤 who did it | 🎯 who/what was affected | 📍 exact channel | 📝 reason | ⏰ time
# Some Discord events (for example a deleted message) do not expose the
# moderator who deleted it through the Gateway event, so those are marked
# as "Unknown / Discord did not expose actor" unless an audit entry matches.

AUDIT_LAST_SEEN = {}
INVITE_CACHE = {}


def _log_channel_targets(guild: discord.Guild):
    if not guild:
        return []
    targets = []
    for channel_id in AUDIT_LOG_CHANNEL_IDS:
        channel = guild.get_channel(channel_id)
        if channel and hasattr(channel, "send"):
            targets.append(channel)
    return targets


def _audit_action(name: str):
    return getattr(discord.AuditLogAction, name, None)


def _entry_target_id(entry):
    target = getattr(entry, "target", None)
    return getattr(target, "id", None)


async def _find_audit_entry(guild: discord.Guild, action_name: str, target_id=None):
    """Find the newest matching Audit Log entry for an event."""
    if not guild:
        return None
    action = _audit_action(action_name)
    if action is None:
        return None
    now = datetime.now(timezone.utc)
    try:
        async for entry in guild.audit_logs(limit=12, action=action):
            created_at = getattr(entry, "created_at", None)
            if created_at and (now - created_at).total_seconds() > AUDIT_MATCH_SECONDS:
                break
            if target_id is not None and _entry_target_id(entry) != target_id:
                continue
            # Avoid returning the same entry twice after reconnects.
            cache_key = (guild.id, entry.id)
            if cache_key in AUDIT_LAST_SEEN:
                continue
            AUDIT_LAST_SEEN[cache_key] = time.time()
            return entry
    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
        return None
    except Exception as exc:
        print(f"[AUDIT LOG] Could not read audit logs: {exc!r}")
    return None


def _actor_text(entry):
    if not entry or not getattr(entry, "user", None):
        return "❔ **Unknown / Discord did not expose actor**"
    actor = entry.user
    return f"{actor.mention} (`{actor.id}`)"


def _target_text(target):
    if target is None:
        return "`Unknown`"
    name = getattr(target, "name", None) or getattr(target, "display_name", None) or str(target)
    target_id = getattr(target, "id", None)
    if target_id:
        return f"**{name}** (`{target_id}`)"
    return f"**{name}**"


def _channel_text(channel):
    if channel is None:
        return "`Unknown channel`"
    channel_id = getattr(channel, "id", None)
    name = getattr(channel, "name", None) or str(channel)
    return f"{channel.mention if hasattr(channel, 'mention') else '#' + name} (`{channel_id}`)"


def _reason(entry, fallback="No reason provided"):
    reason = getattr(entry, "reason", None) if entry else None
    return str(reason) if reason else fallback


def _changes_text(entry):
    if not entry:
        return "`No audit changes available`"
    changes = []
    try:
        for change in entry.changes:
            key = getattr(change, "key", "unknown")
            before = getattr(change, "before", None)
            after = getattr(change, "after", None)
            before_text = str(before)[:300]
            after_text = str(after)[:300]
            changes.append(f"**{key}:** `{before_text}` → `{after_text}`")
    except Exception:
        pass
    return "\n".join(changes[:8]) if changes else "`No audit changes available`"


async def send_audit_log(
    guild: discord.Guild,
    *,
    title: str,
    emoji: str = "📌",
    description: str = "",
    actor=None,
    target=None,
    channel=None,
    entry=None,
    color=None,
    extra_fields=None,
):
    """Send one clean, consistent audit embed to all configured log rooms."""
    if not guild or not AUDIT_LOG_CHANNEL_IDS:
        return

    if actor is None and entry is not None:
        actor = getattr(entry, "user", None)

    embed = discord.Embed(
        title=f"{emoji} {title}",
        description=description or "Dark Night server activity detected.",
        color=color or EMBED_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    if actor is not None:
        actor_mention = getattr(actor, "mention", None) or f"<@{getattr(actor, 'id', 0)}>"
        embed.add_field(
            name="👤 Actor",
            value=f"{actor_mention}\n`{getattr(actor, 'id', 'Unknown')}`",
            inline=True,
        )
        avatar = getattr(getattr(actor, "display_avatar", None), "url", None)
        if avatar:
            embed.set_thumbnail(url=avatar)
    elif entry:
        embed.add_field(name="👤 Actor", value=_actor_text(entry), inline=True)

    if target is not None:
        embed.add_field(name="🎯 Target", value=_target_text(target), inline=True)
    if channel is not None:
        embed.add_field(name="📍 Channel / Room", value=_channel_text(channel), inline=False)
    if entry is not None:
        embed.add_field(name="📝 Reason", value=_reason(entry), inline=False)
        changes = _changes_text(entry)
        if changes != "`No audit changes available`":
            embed.add_field(name="🔧 Changes", value=changes[:1024], inline=False)

    if extra_fields:
        for name, value, inline in extra_fields:
            embed.add_field(name=name, value=str(value)[:1024], inline=inline)

    guild_icon = guild.icon.url if guild.icon else None
    embed.set_footer(text=f"Dark Night • {guild.name} • Server Audit", icon_url=guild_icon)

    for log_channel in _log_channel_targets(guild):
        # Never let a broken logging room crash the bot.
        try:
            await log_channel.send(embed=embed)
        except (discord.Forbidden, discord.HTTPException):
            pass
        except Exception as exc:
            print(f"[AUDIT LOG] Send error in #{getattr(log_channel, 'name', '?')}: {exc!r}")


async def refresh_invite_cache(guild: discord.Guild):
    """Cache invite use counts so member joins can show the exact invite link."""
    try:
        invites = await guild.invites()
    except (discord.Forbidden, discord.HTTPException):
        return
    INVITE_CACHE[guild.id] = {
        inv.code: {
            "uses": inv.uses or 0,
            "inviter_id": getattr(inv.inviter, "id", None),
            "url": str(inv),
            "channel_id": getattr(inv.channel, "id", None),
        }
        for inv in invites
    }


async def detect_used_invite(member: discord.Member):
    """Return the invite that gained a use for this member join, if Discord exposes it."""
    guild = member.guild
    before = INVITE_CACHE.get(guild.id, {})
    try:
        invites = await guild.invites()
    except (discord.Forbidden, discord.HTTPException):
        return None

    used = None
    fresh = {}
    for inv in invites:
        uses = inv.uses or 0
        fresh[inv.code] = {
            "uses": uses,
            "inviter_id": getattr(inv.inviter, "id", None),
            "url": str(inv),
            "channel_id": getattr(inv.channel, "id", None),
        }
        old = before.get(inv.code, {}).get("uses", 0)
        if uses > old and used is None:
            used = inv
    INVITE_CACHE[guild.id] = fresh
    return used


# ==========================================
# 👥 MEMBER LOGS
# ==========================================
@bot.listen("on_member_join")
async def audit_member_join(member: discord.Member):
    invite = await detect_used_invite(member)
    extra = []
    if invite:
        inviter = invite.inviter
        extra.append(("🔗 Invite Used", f"`{invite.code}` — {invite.url}", False))
        extra.append(("🤝 Invited By", f"{inviter.mention if inviter else 'Unknown'} (`{getattr(inviter, 'id', 'Unknown')}`)", True))
        extra.append(("📍 Join Channel", _channel_text(invite.channel), True))
    else:
        extra.append(("🔗 Invite Used", "`Unknown / vanity / invite cache unavailable`", False))
    await send_audit_log(
        member.guild,
        title="Member Joined",
        emoji=LOG_EMOJIS["member_join"],
        target=member,
        extra_fields=extra,
    )


@bot.listen("on_member_remove")
async def audit_member_remove(member: discord.Member):
    entry = await _find_audit_entry(member.guild, "member_kick", member.id)
    if entry:
        await send_audit_log(
            member.guild,
            title="Member Kicked",
            emoji=LOG_EMOJIS["kick"],
            target=member,
            entry=entry,
            extra_fields=[("📍 Last Known Room", "`Discord did not provide a reliable room for a kick event.`", False)],
        )
    else:
        await send_audit_log(
            member.guild,
            title="Member Left",
            emoji=LOG_EMOJIS["member_leave"],
            target=member,
        )


@bot.listen("on_member_ban")
async def audit_member_ban(guild: discord.Guild, user: discord.User):
    entry = await _find_audit_entry(guild, "member_ban", user.id)
    await send_audit_log(
        guild,
        title="Member Banned",
        emoji=LOG_EMOJIS["ban"],
        target=user,
        entry=entry,
    )


@bot.listen("on_member_unban")
async def audit_member_unban(guild: discord.Guild, user: discord.User):
    entry = await _find_audit_entry(guild, "member_unban", user.id)
    await send_audit_log(
        guild,
        title="Member Unbanned",
        emoji=LOG_EMOJIS["unban"],
        target=user,
        entry=entry,
    )


@bot.listen("on_member_update")
async def audit_member_update(before: discord.Member, after: discord.Member):
    if before.guild is None:
        return

    # 🎭 Roles added / removed — exact role names and IDs.
    before_roles = {r.id: r for r in before.roles if r.is_default() is False}
    after_roles = {r.id: r for r in after.roles if r.is_default() is False}
    added = [after_roles[rid] for rid in after_roles.keys() - before_roles.keys()]
    removed = [before_roles[rid] for rid in before_roles.keys() - after_roles.keys()]

    if added or removed:
        entry = await _find_audit_entry(before.guild, "member_role_update", before.id)
        fields = []
        if added:
            fields.append(("➕ Roles Added", "\n".join(f"{r.mention} — `{r.id}`" for r in added), False))
        if removed:
            fields.append(("➖ Roles Removed", "\n".join(f"{r.name} — `{r.id}`" for r in removed), False))
        await send_audit_log(
            before.guild,
            title="Member Roles Changed",
            emoji="🎭",
            target=after,
            entry=entry,
            extra_fields=fields,
        )

    # 👤 Nickname / timeout / profile changes.
    changes = []
    if before.nick != after.nick:
        changes.append(("🏷️ Nickname", f"`{before.nick or 'None'}` → `{after.nick or 'None'}`", True))
    if before.communication_disabled_until != after.communication_disabled_until:
        old = before.communication_disabled_until
        new = after.communication_disabled_until
        changes.append(("⏱️ Timeout", f"`{old or 'None'}` → `{new or 'None'}`", False))

    if changes:
        entry = await _find_audit_entry(before.guild, "member_update", before.id)
        await send_audit_log(
            before.guild,
            title="Member Updated",
            emoji="👤",
            target=after,
            entry=entry,
            extra_fields=changes,
        )


# ==========================================
# 🎭 ROLE LOGS
# ==========================================
@bot.listen("on_guild_role_create")
async def audit_role_create(role: discord.Role):
    entry = await _find_audit_entry(role.guild, "role_create", role.id)
    await send_audit_log(
        role.guild,
        title="Role Created",
        emoji=LOG_EMOJIS["role_create"],
        target=role,
        entry=entry,
    )


@bot.listen("on_guild_role_delete")
async def audit_role_delete(role: discord.Role):
    entry = await _find_audit_entry(role.guild, "role_delete", role.id)
    await send_audit_log(
        role.guild,
        title="Role Deleted",
        emoji=LOG_EMOJIS["role_delete"],
        target=role,
        entry=entry,
    )


@bot.listen("on_guild_role_update")
async def audit_role_update(before: discord.Role, after: discord.Role):
    changed = []
    if before.name != after.name:
        changed.append(("🏷️ Name", f"`{before.name}` → `{after.name}`", True))
    if before.permissions != after.permissions:
        changed.append(("🔐 Permissions", "`Role permissions changed`", True))
    if before.color != after.color:
        changed.append(("🎨 Color", f"`{before.color}` → `{after.color}`", True))
    if before.hoist != after.hoist:
        changed.append(("📌 Hoisted", f"`{before.hoist}` → `{after.hoist}`", True))
    if before.mentionable != after.mentionable:
        changed.append(("📣 Mentionable", f"`{before.mentionable}` → `{after.mentionable}`", True))
    if changed:
        entry = await _find_audit_entry(after.guild, "role_update", after.id)
        await send_audit_log(
            after.guild,
            title="Role Updated",
            emoji=LOG_EMOJIS["role_update"],
            target=after,
            entry=entry,
            extra_fields=changed,
        )


# ==========================================
# 📁 CHANNEL / THREAD LOGS
# ==========================================
@bot.listen("on_guild_channel_create")
async def audit_channel_create(channel: discord.abc.GuildChannel):
    entry = await _find_audit_entry(channel.guild, "channel_create", channel.id)
    await send_audit_log(
        channel.guild,
        title="Channel Created",
        emoji=LOG_EMOJIS["channel_create"],
        target=channel,
        channel=channel,
        entry=entry,
    )


@bot.listen("on_guild_channel_delete")
async def audit_channel_delete(channel: discord.abc.GuildChannel):
    entry = await _find_audit_entry(channel.guild, "channel_delete", channel.id)
    await send_audit_log(
        channel.guild,
        title="Channel Deleted",
        emoji=LOG_EMOJIS["channel_delete"],
        target=channel,
        channel=channel,
        entry=entry,
    )


@bot.listen("on_guild_channel_update")
async def audit_channel_update(before: discord.abc.GuildChannel, after: discord.abc.GuildChannel):
    changed = []
    if getattr(before, "name", None) != getattr(after, "name", None):
        changed.append(("🏷️ Name", f"`{getattr(before, 'name', '?')}` → `{getattr(after, 'name', '?')}`", True))
    if getattr(before, "category_id", None) != getattr(after, "category_id", None):
        changed.append(("📂 Category", f"`{getattr(before, 'category_id', None)}` → `{getattr(after, 'category_id', None)}`", True))
    if getattr(before, "position", None) != getattr(after, "position", None):
        changed.append(("↕️ Position", f"`{getattr(before, 'position', '?')}` → `{getattr(after, 'position', '?')}`", True))
    if getattr(before, "topic", None) != getattr(after, "topic", None):
        changed.append(("📝 Topic", "`Channel topic changed`", False))
    if getattr(before, "slowmode_delay", None) != getattr(after, "slowmode_delay", None):
        changed.append(("🐌 Slowmode", f"`{getattr(before, 'slowmode_delay', 0)}` → `{getattr(after, 'slowmode_delay', 0)}`", True))
    if changed:
        entry = await _find_audit_entry(after.guild, "channel_update", after.id)
        await send_audit_log(
            after.guild,
            title="Channel Updated",
            emoji=LOG_EMOJIS["channel_update"],
            target=after,
            channel=after,
            entry=entry,
            extra_fields=changed,
        )


@bot.listen("on_thread_create")
async def audit_thread_create(thread: discord.Thread):
    entry = await _find_audit_entry(thread.guild, "thread_create", thread.id)
    await send_audit_log(thread.guild, title="Thread Created", emoji=LOG_EMOJIS["thread_create"], target=thread, channel=thread, entry=entry)


@bot.listen("on_thread_delete")
async def audit_thread_delete(thread: discord.Thread):
    entry = await _find_audit_entry(thread.guild, "thread_delete", thread.id)
    await send_audit_log(thread.guild, title="Thread Deleted", emoji=LOG_EMOJIS["thread_delete"], target=thread, channel=thread, entry=entry)


@bot.listen("on_thread_update")
async def audit_thread_update(before: discord.Thread, after: discord.Thread):
    if before.name != after.name or before.archived != after.archived or before.locked != after.locked:
        entry = await _find_audit_entry(after.guild, "thread_update", after.id)
        await send_audit_log(
            after.guild,
            title="Thread Updated",
            emoji=LOG_EMOJIS["thread_update"],
            target=after,
            channel=after,
            entry=entry,
            extra_fields=[("🔧 Changes", f"`{before.name}` → `{after.name}` | archived `{before.archived}` → `{after.archived}` | locked `{before.locked}` → `{after.locked}`", False)],
        )


# ==========================================
# 💬 MESSAGE LOGS
# ==========================================
@bot.listen("on_raw_message_delete")
async def audit_message_delete(payload: discord.RawMessageDeleteEvent):
    channel = bot.get_channel(payload.channel_id)
    entry = None
    if channel and getattr(channel, "guild", None):
        entry = await _find_audit_entry(channel.guild, "message_delete", getattr(payload, "message_id", None))
        await send_audit_log(
            channel.guild,
            title="Message Deleted",
            emoji=LOG_EMOJIS["message_delete"],
            channel=channel,
            entry=entry,
            extra_fields=[("🆔 Message ID", f"`{payload.message_id}`", True), ("⚠️ Note", "The deleted message content may be unavailable because Discord did not send it with this event.", False)],
        )


@bot.listen("on_raw_bulk_message_delete")
async def audit_bulk_message_delete(payload: discord.RawBulkMessageDeleteEvent):
    channel = bot.get_channel(payload.channel_id)
    if channel and getattr(channel, "guild", None):
        await send_audit_log(
            channel.guild,
            title="Bulk Messages Deleted",
            emoji=LOG_EMOJIS["message_bulk_delete"],
            channel=channel,
            extra_fields=[("🧹 Messages", f"`{len(payload.message_ids)}` messages deleted", False)],
        )


@bot.listen("on_raw_message_edit")
async def audit_message_edit(payload: discord.RawMessageUpdateEvent):
    channel = bot.get_channel(payload.channel_id)
    if not channel or not getattr(channel, "guild", None):
        return
    # Ignore edits generated by the bot itself to keep the audit room clean.
    author_id = None
    data = getattr(payload, "data", {}) or {}
    author = data.get("author") or {}
    author_id = author.get("id")
    if author_id and bot.user and int(author_id) == bot.user.id:
        return
    before_content = getattr(payload.cached_message, "content", None) if getattr(payload, "cached_message", None) else None
    after_content = data.get("content")
    if before_content is not None and after_content is not None and before_content == after_content:
        return
    await send_audit_log(
        channel.guild,
        title="Message Edited",
        emoji=LOG_EMOJIS["message_edit"],
        channel=channel,
        extra_fields=[
            ("🆔 Message ID", f"`{payload.message_id}`", True),
            ("👤 Author", f"<@{author_id}> (`{author_id}`)" if author_id else "`Unknown`", True),
            ("✏️ Before", f"```{str(before_content)[:900] if before_content is not None else 'Content unavailable'}```", False),
            ("📝 After", f"```{str(after_content)[:900] if after_content is not None else 'Content unavailable'}```", False),
        ],
    )


# ==========================================
# 🔗 INVITE LOGS
# ==========================================
@bot.listen("on_invite_create")
async def audit_invite_create(invite: discord.Invite):
    if not invite.guild:
        return
    await send_audit_log(
        invite.guild,
        title="Invite Created",
        emoji=LOG_EMOJIS["invite_create"],
        actor=invite.inviter,
        target=invite,
        channel=invite.channel,
        extra_fields=[("🔗 Invite", f"`{invite.code}` — {invite}", False), ("🔢 Max Uses", f"`{invite.max_uses or 'Unlimited'}`", True)],
    )
    await refresh_invite_cache(invite.guild)


@bot.listen("on_invite_delete")
async def audit_invite_delete(invite: discord.Invite):
    if invite.guild:
        entry = await _find_audit_entry(invite.guild, "invite_delete", None)
        await send_audit_log(
            invite.guild,
            title="Invite Deleted",
            emoji=LOG_EMOJIS["invite_delete"],
            target=invite,
            channel=invite.channel,
            entry=entry,
            extra_fields=[("🔗 Invite", f"`{invite.code}`", False)],
        )
        await refresh_invite_cache(invite.guild)


# ==========================================
# 😀 EMOJI / STICKER / SERVER LOGS
# ==========================================
@bot.listen("on_guild_emojis_update")
async def audit_emojis_update(guild: discord.Guild, before, after):
    before_map = {e.id: e for e in before}
    after_map = {e.id: e for e in after}
    added = [after_map[x] for x in after_map.keys() - before_map.keys()]
    removed = [before_map[x] for x in before_map.keys() - after_map.keys()]
    changed = [after_map[x] for x in after_map.keys() & before_map.keys() if before_map[x].name != after_map[x].name]
    if added or removed or changed:
        entry = None
        for action_name in ("emoji_create", "emoji_delete", "emoji_update"):
            entry = await _find_audit_entry(guild, action_name)
            if entry:
                break
        fields = []
        if added:
            fields.append(("➕ Added", " ".join(str(e) for e in added), False))
        if removed:
            fields.append(("➖ Removed", " ".join(str(e) for e in removed), False))
        if changed:
            fields.append(("✏️ Renamed", ", ".join(f"`{before_map[e.id].name}` → `{e.name}`" for e in changed), False))
        await send_audit_log(guild, title="Server Emojis Updated", emoji=LOG_EMOJIS["emoji_update"], entry=entry, extra_fields=fields)


@bot.listen("on_guild_stickers_update")
async def audit_stickers_update(guild: discord.Guild, before, after):
    before_ids = {s.id for s in before}
    after_ids = {s.id for s in after}
    if before_ids != after_ids:
        entry = await _find_audit_entry(guild, "sticker_create") or await _find_audit_entry(guild, "sticker_delete")
        await send_audit_log(
            guild,
            title="Server Stickers Updated",
            emoji=LOG_EMOJIS["sticker_update"],
            entry=entry,
            extra_fields=[("🔧 Changes", f"Before: `{len(before_ids)}` • After: `{len(after_ids)}`", False)],
        )


@bot.listen("on_guild_update")
async def audit_guild_update(before: discord.Guild, after: discord.Guild):
    changed = []
    for attr, label in (("name", "🏷️ Name"), ("description", "📝 Description"), ("verification_level", "🛡️ Verification"), ("default_notifications", "🔔 Notifications"), ("afk_timeout", "💤 AFK Timeout")):
        if getattr(before, attr, None) != getattr(after, attr, None):
            changed.append((label, f"`{getattr(before, attr, None)}` → `{getattr(after, attr, None)}`", True))
    if changed:
        entry = await _find_audit_entry(after, "guild_update", after.id)
        await send_audit_log(after, title="Server Updated", emoji=LOG_EMOJIS["server_update"], entry=entry, extra_fields=changed)


# ==========================================
# 🧾 END FULL SERVER LOGGING SYSTEM
# ==========================================

# ==========================================
# MEMBER / SERVER PEAK TRACKING
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    update_peak_members(member.guild)

@bot.event
async def on_member_remove(member: discord.Member):
    update_peak_members(member.guild)


# ==========================================
# MUSIC / VOICE SYSTEM
# ==========================================
MUSIC_PLAYERS = {}


def get_ffmpeg_executable():
    """Find FFmpeg on PATH, then fall back to imageio-ffmpeg's bundled binary."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        print(f"[FFMPEG] Using system FFmpeg: {system_ffmpeg}")
        return system_ffmpeg

    if IMAGEIO_FFMPEG_OK:
        try:
            bundled_ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
            if bundled_ffmpeg and os.path.isfile(bundled_ffmpeg):
                print(f"[FFMPEG] Using bundled FFmpeg: {bundled_ffmpeg}")
                return bundled_ffmpeg
        except Exception as exc:
            print(f"[FFMPEG] Could not locate bundled FFmpeg: {exc!r}")

    raise RuntimeError(
        "FFmpeg was not found. Install ffmpeg in Railway or ensure imageio-ffmpeg is installed."
    )


class MusicPlayer:
    def __init__(self, guild_id):
        self.guild_id = guild_id
        self.queue = []
        self.current = None
        self.voice = None
        self.volume = 1.0
        self.loop = "off"          # off, song, queue
        self.autoplay = False
        self.filter_name = "off"   # off, nightcore, bassboost
        self.lock = asyncio.Lock()

    def filter_args(self):
        if self.filter_name == "nightcore":
            return "-af asetrate=48000*1.25,aresample=48000,atempo=0.8"
        if self.filter_name == "bassboost":
            return "-af bass=g=10"
        return None

    def ffmpeg_source(self, track):
        """Create a PCM audio stream from FFmpeg for discord.py."""
        url = track["url"]
        filter_args = self.filter_args()
        before = "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        # YouTube/CDN URLs sometimes require the same HTTP headers that
        # yt-dlp used when extracting the media URL.
        headers = track.get("http_headers") or {}
        if headers:
            header_lines = "\r\n".join(
                f"{k}: {v}" for k, v in headers.items()
                if v is not None
            ) + "\r\n"
            before += f' -headers "{header_lines}"'

        options = f"-vn -ar 48000 -ac 2 -af volume={self.volume:.3f}"
        if filter_args:
            # filter_args already starts with -af; append volume to the filter chain.
            filter_chain = filter_args[len("-af "):]
            options = f"-vn -ar 48000 -ac 2 -af {filter_chain},volume={self.volume:.3f}"

        executable = get_ffmpeg_executable()

        # Use PCM output and let discord.py handle the Opus encoding.
        # This avoids FFmpeg's libopus encoder crash (exit code -11) seen
        # on some Railway environments.
        return discord.FFmpegPCMAudio(
            url,
            executable=executable,
            before_options=before,
            options=options,
        )


def music_player(guild_id):
    if guild_id not in MUSIC_PLAYERS:
        MUSIC_PLAYERS[guild_id] = MusicPlayer(guild_id)
    return MUSIC_PLAYERS[guild_id]


def _extract_info(query):
    # Keep extraction conservative: one audio result, no playlist download.
    options = dict(YTDL_OPTIONS)
    with yt_dlp.YoutubeDL(options) as ydl:
        info = ydl.extract_info(query, download=False)
        if "entries" in info:
            info = next((x for x in info["entries"] if x), None)
        if not info:
            raise RuntimeError("No audio result found.")

        direct_url = info.get("url")
        if not direct_url:
            # Some extractors expose formats instead of a top-level URL.
            formats = info.get("formats") or []
            audio_formats = [
                f for f in formats
                if f.get("url") and (f.get("acodec") not in (None, "none"))
            ]
            if audio_formats:
                direct_url = audio_formats[-1]["url"]

        if not direct_url:
            raise RuntimeError("yt-dlp did not return a playable audio URL.")

        return {
            "title": info.get("title", "Unknown track"),
            "url": direct_url,
            "webpage_url": info.get("webpage_url") or info.get("original_url") or query,
            "duration": info.get("duration") or 0,
            "thumbnail": info.get("thumbnail"),
            "uploader": info.get("uploader", "Unknown"),
            "http_headers": info.get("http_headers") or {},
        }


async def extract_track(query):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _extract_info, query)


async def ensure_voice(interaction: Interaction):
    """Connect the bot to the caller's VC safely.

    IMPORTANT: every command calls interaction.response.defer() BEFORE this
    function. Voice Gateway connection can take longer than Discord's 3-second
    initial interaction deadline.
    """
    if not interaction.guild:
        await interaction.followup.send(
            "❌ This command can only be used in a server.", ephemeral=True
        )
        return None

    if not interaction.user.voice or not interaction.user.voice.channel:
        await interaction.followup.send(
            "❌ Join a voice channel first.", ephemeral=True
        )
        return None

    if not PYNACL_OK:
        await interaction.followup.send(
            "❌ Voice is unavailable because **PyNaCl** is not installed. "
            "Check Railway dependencies and redeploy.", ephemeral=True
        )
        return None

    if not DAVEY_OK:
        await interaction.followup.send(
            "❌ Voice is unavailable because **davey** is not installed. "
            "Add `davey` to requirements.txt and redeploy with cleared cache.",
            ephemeral=True,
        )
        return None

    if not OPUS_OK:
        await interaction.followup.send(
            "❌ Voice is unavailable because native **libopus** could not be loaded. "
            "Install libopus on Railway and redeploy.",
            ephemeral=True,
        )
        return None

    target = interaction.user.voice.channel
    player = music_player(interaction.guild.id)
    vc = interaction.guild.voice_client

    try:
        if vc and vc.is_connected():
            player.voice = vc
            if vc.channel != target:
                await vc.move_to(target)
        else:
            # Explicit timeout + reconnect for Railway/cloud hosting.
            player.voice = await target.connect(timeout=30.0, reconnect=True)

        return player

    except RuntimeError as exc:
        print(f"[VOICE RUNTIME ERROR] {exc!r}")
        message = str(exc).strip() or "Voice runtime dependency error."
        await interaction.followup.send(
            f"❌ Voice connection error: `{message[:700]}`\n"
            "Check the Railway logs for the full traceback.",
            ephemeral=True,
        )
        return None

    except discord.Forbidden:
        await interaction.followup.send(
            "❌ I need **View Channel**, **Connect**, and **Speak** permissions "
            "in that voice channel.", ephemeral=True
        )
        return None

    except discord.ClientException as exc:
        print(f"[VOICE CLIENT ERROR] {exc!r}")
        await interaction.followup.send(
            f"❌ Discord voice client error: `{str(exc)[:600]}`",
            ephemeral=True,
        )
        return None

    except asyncio.TimeoutError:
        await interaction.followup.send(
            "❌ Discord Voice connection timed out. Try `/join` again.",
            ephemeral=True,
        )
        return None

    except discord.HTTPException as exc:
        print(f"[VOICE HTTP ERROR] {exc!r}")
        await interaction.followup.send(
            f"❌ Discord refused the voice connection: `{exc}`",
            ephemeral=True,
        )
        return None

    except Exception as exc:
        print(f"[VOICE ERROR] {type(exc).__name__}: {exc!r}")
        await interaction.followup.send(
            f"❌ Voice connection error: `{type(exc).__name__}: {str(exc)[:500]}`",
            ephemeral=True,
        )
        return None


async def play_next(guild_id):
    player = MUSIC_PLAYERS.get(guild_id)
    if not player or not player.voice or not player.voice.is_connected():
        return False

    if player.voice.is_playing() or player.voice.is_paused():
        return False

    if player.loop == "song" and player.current:
        track = player.current
    elif player.queue:
        if player.current and player.loop == "queue":
            player.queue.append(player.current)
        track = player.queue.pop(0)
        player.current = track
    elif player.autoplay and player.current:
        try:
            query = f"ytsearch1:{player.current['title']} official audio"
            track = await extract_track(query)
            player.current = track
        except Exception as exc:
            print(f"[AUTOPLAY ERROR] {type(exc).__name__}: {exc!r}")
            return False
    else:
        return False

    try:
        source = player.ffmpeg_source(track)
    except Exception as exc:
        print(f"[FFMPEG SOURCE ERROR] {type(exc).__name__}: {exc!r}")
        return False

    def after_play(error):
        if error:
            print(f"[MUSIC PLAYBACK ERROR] {type(error).__name__}: {error!r}")
        else:
            print(f"[MUSIC] Finished: {track.get('title', 'Unknown')}")
        try:
            asyncio.run_coroutine_threadsafe(play_next(guild_id), bot.loop)
        except Exception as exc:
            print(f"[PLAY NEXT CALLBACK ERROR] {type(exc).__name__}: {exc!r}")

    try:
        print(f"[MUSIC] Starting playback: {track.get('title', 'Unknown')}")
        player.voice.play(source, after=after_play)
        print("[MUSIC] Voice playback started successfully.")
        return True
    except Exception as exc:
        print(f"[VOICE PLAY ERROR] {type(exc).__name__}: {exc!r}")
        try:
            source.cleanup()
        except Exception:
            pass
        return False


@bot.tree.command(name="join", description="Join your current voice channel")
async def music_join(interaction: Interaction):
    # MUST happen before any potentially slow Voice Gateway operation.
    await interaction.response.defer()

    player = await ensure_voice(interaction)
    if player is None:
        return

    await interaction.followup.send(
        f"🎵 Joined **{player.voice.channel.name}**. Ready to play music!"
    )


@bot.tree.command(name="leave", description="Leave voice and clear the music queue")
async def music_leave(interaction: Interaction):
    await interaction.response.defer()

    player = music_player(interaction.guild.id)
    vc = interaction.guild.voice_client
    if not vc:
        return await interaction.followup.send(
            "❌ I'm not in a voice channel.", ephemeral=True
        )

    player.queue.clear()
    player.current = None
    player.autoplay = False
    player.loop = "off"

    try:
        vc.stop()
        await vc.disconnect(force=True)
    except Exception as exc:
        print(f"[LEAVE ERROR] {exc!r}")
    finally:
        player.voice = None

    await interaction.followup.send("👋 Left voice and cleared the queue.")


@bot.tree.command(name="play", description="Play YouTube or SoundCloud audio")
@app_commands.describe(query="YouTube/SoundCloud URL or song name")
async def music_play(interaction: Interaction, query: str):
    # Defer FIRST. Both voice connection and yt-dlp can take several seconds.
    await interaction.response.defer()

    player = await ensure_voice(interaction)
    if player is None:
        return

    try:
        track = await extract_track(query)
    except Exception as exc:
        print(f"[YTDLP ERROR] {type(exc).__name__}: {exc!r}")
        return await interaction.followup.send(
            f"❌ Couldn't find/play that track.\n`{type(exc).__name__}: {str(exc)[:500]}`",
            ephemeral=True,
        )

    player.queue.append(track)
    position = len(player.queue)

    if not player.voice.is_playing() and not player.voice.is_paused():
        started = await play_next(interaction.guild.id)
        position = "Now playing" if started else "Queued (playback error — check bot logs)"

    embed = discord.Embed(
        title="🎵 Added to Dark Night Music",
        description=f"**{track['title']}**",
        color=EMBED_COLOR,
    )
    embed.add_field(
        name="Artist / Uploader",
        value=track["uploader"],
        inline=True,
    )
    embed.add_field(name="Queue", value=f"`{position}`", inline=True)
    if track.get("thumbnail"):
        embed.set_thumbnail(url=track["thumbnail"])

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="pause", description="Pause the current music")
async def music_pause(interaction: Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_playing():
        return await interaction.response.send_message(
            "❌ Nothing is playing.", ephemeral=True
        )
    vc.pause()
    await interaction.response.send_message("⏸️ Music paused.")


@bot.tree.command(name="resume", description="Resume paused music")
async def music_resume(interaction: Interaction):
    vc = interaction.guild.voice_client
    if not vc or not vc.is_paused():
        return await interaction.response.send_message(
            "❌ Music isn't paused.", ephemeral=True
        )
    vc.resume()
    await interaction.response.send_message("▶️ Music resumed.")


@bot.tree.command(name="skip", description="Skip the current track")
async def music_skip(interaction: Interaction):
    vc = interaction.guild.voice_client
    if not vc or not (vc.is_playing() or vc.is_paused()):
        return await interaction.response.send_message(
            "❌ Nothing is playing.", ephemeral=True
        )
    vc.stop()
    await interaction.response.send_message(
        "⏭️ Skipped. Loading the next track..."
    )


@bot.tree.command(name="stop", description="Stop music and clear the queue")
async def music_stop(interaction: Interaction):
    player = music_player(interaction.guild.id)
    player.queue.clear()
    player.current = None
    player.loop = "off"
    vc = interaction.guild.voice_client
    if vc:
        vc.stop()
    await interaction.response.send_message(
        "⏹️ Music stopped and queue cleared."
    )


@bot.tree.command(name="queue", description="Show the current music queue")
async def music_queue(interaction: Interaction):
    player = music_player(interaction.guild.id)
    lines = []
    if player.current:
        lines.append(f"🎶 **Now:** {player.current['title']}")
    for i, track in enumerate(player.queue[:15], 1):
        lines.append(f"`{i}.` {track['title']}")
    if not lines:
        lines = ["🌙 The music queue is empty."]
    embed = discord.Embed(
        title="🎵 Dark Night • Music Queue",
        description="\n".join(lines),
        color=EMBED_COLOR,
    )
    embed.set_footer(
        text=f"Loop: {player.loop} • Autoplay: {'ON' if player.autoplay else 'OFF'} • Filter: {player.filter_name}"
    )
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="nowplaying", description="Show the currently playing track")
async def music_nowplaying(interaction: Interaction):
    player = music_player(interaction.guild.id)
    if not player.current:
        return await interaction.response.send_message(
            "❌ Nothing is playing.", ephemeral=True
        )
    embed = discord.Embed(
        title="🎵 Now Playing",
        description=f"**{player.current['title']}**",
        color=EMBED_COLOR,
    )
    embed.add_field(
        name="Artist / Uploader",
        value=player.current["uploader"],
        inline=True,
    )
    embed.add_field(
        name="Volume",
        value=f"`{int(player.volume * 100)}%`",
        inline=True,
    )
    embed.add_field(name="Loop", value=f"`{player.loop}`", inline=True)
    if player.current.get("thumbnail"):
        embed.set_thumbnail(url=player.current["thumbnail"])
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="volume", description="Set music volume from 0% to 200%")
@app_commands.describe(percent="Volume percentage: 0-200")
async def music_volume(
    interaction: Interaction,
    percent: app_commands.Range[int, 0, 200],
):
    player = music_player(interaction.guild.id)
    player.volume = percent / 100
    vc = interaction.guild.voice_client
    # FFmpeg applies volume when a new track starts.
    # The current track is intentionally not restarted just to change volume.
    await interaction.response.send_message(
        f"🔊 Volume set to **{percent}%**."
    )


@bot.tree.command(name="loop", description="Set loop mode")
@app_commands.describe(mode="off, song or queue")
@app_commands.choices(mode=[
    app_commands.Choice(name="Off", value="off"),
    app_commands.Choice(name="Song", value="song"),
    app_commands.Choice(name="Queue", value="queue"),
])
async def music_loop(interaction: Interaction, mode: app_commands.Choice[str]):
    player = music_player(interaction.guild.id)
    player.loop = mode.value
    await interaction.response.send_message(f"🔁 Loop mode: **{mode.name}**.")


@bot.tree.command(name="autoplay", description="Toggle automatic music when the queue ends")
@app_commands.describe(enabled="Turn autoplay on or off")
async def music_autoplay(interaction: Interaction, enabled: bool):
    player = music_player(interaction.guild.id)
    player.autoplay = enabled
    await interaction.response.send_message(
        f"🤖 Autoplay: **{'ON' if enabled else 'OFF'}**."
    )


@bot.tree.command(name="remove", description="Remove a queued track by position")
@app_commands.describe(position="Queue position, starting at 1")
async def music_remove(
    interaction: Interaction,
    position: app_commands.Range[int, 1, 1000],
):
    player = music_player(interaction.guild.id)
    if position > len(player.queue):
        return await interaction.response.send_message(
            "❌ That queue position doesn't exist.", ephemeral=True
        )
    track = player.queue.pop(position - 1)
    await interaction.response.send_message(
        f"🗑️ Removed **{track['title']}** from the queue."
    )


@bot.tree.command(name="clearqueue", description="Clear the music queue")
async def music_clearqueue(interaction: Interaction):
    player = music_player(interaction.guild.id)
    count = len(player.queue)
    player.queue.clear()
    await interaction.response.send_message(
        f"🧹 Cleared **{count}** queued track(s). Current track keeps playing."
    )


@bot.tree.command(name="filter", description="Set a music audio filter")
@app_commands.describe(name="off, nightcore or bassboost")
@app_commands.choices(name=[
    app_commands.Choice(name="Off", value="off"),
    app_commands.Choice(name="Nightcore", value="nightcore"),
    app_commands.Choice(name="Bassboost", value="bassboost"),
])
async def music_filter(interaction: Interaction, name: app_commands.Choice[str]):
    player = music_player(interaction.guild.id)
    player.filter_name = name.value
    vc = interaction.guild.voice_client

    if vc and (vc.is_playing() or vc.is_paused()) and player.current:
        was_paused = vc.is_paused()
        vc.stop()
        await asyncio.sleep(0.25)
        await play_next(interaction.guild.id)
        if was_paused and vc.is_playing():
            vc.pause()

    await interaction.response.send_message(
        f"🎚️ Audio filter: **{name.name}**."
    )


# ==========================================
# 10. HELP CENTER
# ==========================================
HELP_CATEGORIES = {
    "🛡️ Moderation": [
        ("/warn", "Warn a member and store the warning."),
        ("/warnings", "Show a member's stored warnings."),
        ("/clear", "Delete recent messages."),
        ("/kick", "Kick a member."),
        ("/ban", "Ban a member."),
        ("/unban", "Unban a user by ID."),
        ("/lock", "Lock the current text channel."),
        ("/unlock", "Unlock the current text channel."),
        ("/slowmode", "Set channel slowmode."),
        ("/mutechat", "Timeout a member: 60s, 1m, 6h, 1d."),
        ("/unmutechat", "Remove a chat timeout."),
        ("/mutevc", "Server-mute a member in VC."),
        ("/unmutevc", "Remove a VC mute."),
        ("/jail", "Give the configured Jail role."),
        ("/antinuke", "Protect a member from bot moderation.")
    ],
    "🎮 Games": [
        ("/games", "Open the Games Center with one menu for all Dark Night games."),
        ("/coinflip", "Flip heads or tails for a quick result."),
        ("/dice", "Roll a die with 2–100 sides."),
        ("/rps", "Play Rock Paper Scissors against Dark Night."),
        ("/8ball", "Ask a question and receive a random Magic 8-Ball answer."),
        ("/roulette", "Bet Moon Coins on red, black, or green."),
        ("/roulette_game", "Create a multiplayer Roulette Arena where players join the same pot."),
        ("/roulette_status", "Check the current Roulette Arena lobby."),
        ("/slots", "Spin three symbols and win based on the combination."),
        ("/blackjack", "Play a simplified blackjack round against the dealer."),
        ("/numberguess", "Guess the secret number from 1 to 10."),
        ("/quickdraw", "Play a fast reflex-style mini game."),
        ("Games Center: High / Low", "Bet on a high or low card result."),
        ("Games Center: Even / Odd", "Bet on an even or odd number result."),
        ("Games Center: Wheel", "Spin a multiplier wheel for a possible payout."),
        ("Games Center: Double or Nothing", "Risk a bet for a chance to double it."),
        ("Games Center: Treasure", "Open a virtual treasure chest for a random payout."),
        ("Games Center: Lucky Color", "Receive a random lucky color."),
        ("Games Center: Mafia", "Use the Mafia command to create and play a social deduction game."),
        ("Bet format", "Bet commands accept values such as 1k, 2.5k, 1m, and 2b."),
    ],
    "💰 Economy": [
        ("/balance", "Check your virtual Moon Coins."),
        ("/daily", "Claim a daily virtual reward."),
        ("/work", "Earn virtual coins."),
        ("/pay", "Send virtual coins to another member."),
        ("/leaderboard", "Richest members leaderboard."),
        ("/givecoins", "Owner/Admin: give Moon Coins to a member.")
    ],
    "🏆 Levels": [
        ("/rank", "Show XP and level."),
        ("/leaderboardxp", "XP leaderboard.")
    ],
    "🌐 Community": [
        ("/poll", "Create a two-option community poll with reaction voting."),
        ("/suggest", "Submit a suggestion with 👍/👎 voting."),
        ("/announce", "Create a formatted announcement as Owner/Admin."),
        ("/broadcast", "Send a formatted community broadcast to any text channel as Owner/Admin."),
        ("/userinfo", "Show a member's account, join date, roles, and avatar."),
        ("/avatar", "Show a member's avatar."),
        ("/roleinfo", "Show role information and member count."),
        ("/serverinfo", "Show detailed server information."),
        ("/about", "Show Dark Night server statistics and activity."),
        ("/send_panel", "Send the configured Dark Night community panels."),
    ],
    "🎁 Events": [
        ("/giveaway", "Start a timed giveaway."),
        ("/giveaway_end", "End a giveaway early."),
        ("/birthday", "Set, view or remove a birthday.")
    ],
    "🎵 Music": [
        ("/join", "Join the voice channel you are currently in."),
        ("/leave", "Leave voice and clear the music queue."),
        ("/play", "Play YouTube or SoundCloud audio and add tracks to the queue."),
        ("/pause", "Pause the currently playing track."),
        ("/resume", "Resume paused music."),
        ("/skip", "Skip the current track."),
        ("/stop", "Stop music and clear the queue."),
        ("/queue", "Show the current queue."),
        ("/nowplaying", "Show the track currently playing."),
        ("/volume", "Set volume from 0% to 200%."),
        ("/loop", "Set loop mode: off, song or queue."),
        ("/autoplay", "Automatically queue another track when the queue ends."),
        ("/remove", "Remove a track from the queue by position."),
        ("/clearqueue", "Clear all queued tracks without leaving voice."),
        ("/filter", "Set audio filter: off, nightcore or bassboost.")
    ],
    "🔊 Temporary Voice": [
        ("/vccenter", "Open the control panel for your current temporary VC."),
        ("Lock / Unlock", "Prevent new members from joining or reopen the room."),
        ("Limit", "Set the room user limit from 0 to 99."),
        ("Rename", "Change the temporary room name."),
        ("Kick", "Remove a member from your temporary VC."),
        ("Move", "Move a member between your temporary VC and another voice channel."),
        ("Close Room", "Delete your temporary VC immediately."),
        ("Auto Cleanup", "The temporary VC is deleted automatically when empty."),
        ("Permissions", "The room owner, server Owner, or Administrator can control the room."),
    ],
    "🌙 Server": [
        ("/about", "Show detailed Dark Night server statistics."),
        ("/serverinfo", "Show server information, channels, roles, and activity."),
        ("/invite", "Get the Dark Night bot invite link."),
        ("/send_panel", "Send a configured Dark Night community panel."),
        ("/help", "Open the interactive Dark Night Help Center."),
        ("/games", "Open the Games Center."),
        ("/vccenter", "Open controls for your current temporary voice room."),
        ("/broadcast", "Owner/Admin: send a formatted broadcast to a selected channel."),
    ]
}

class HelpCategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=name, description=f"Show {name} commands.")
            for name in HELP_CATEGORIES
        ]
        super().__init__(
            placeholder="🌙 Choose a category...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="moon_help_category"
        )

    async def callback(self, interaction: Interaction):
        category = self.values[0]
        lines = "\n".join(
            f"**`{cmd}`** — {desc}" for cmd, desc in HELP_CATEGORIES[category]
        )
        embed = discord.Embed(
            title=f"🌙 Dark Night • {category}",
            description=(
                "```ansi\nDark Night Community Command Center\n```\n"
                + lines
                + "\n\n-# Select another category below to explore more."
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text="Dark Night • Help Center")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpCategorySelect())

@bot.tree.command(name="help", description="Open the Dark Night command center")
async def help_command(interaction: Interaction):
    embed = discord.Embed(
        title="🌙 Dark Night • Command Center",
        description=(
            "Welcome to the **Dark Night Help Center**.\n\n"
            "Choose a category below and you'll get every command with a clean description.\n\n"
            "✨ Moderation commands are Staff/Admin restricted."
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=COMMUNITY_IMAGE_URL)
    embed.set_footer(text="Dark Night • Help Center")
    await interaction.response.send_message(embed=embed, view=HelpView(), ephemeral=True)


# ==========================================
# 11. EXTRA MODERATION
# ==========================================
@bot.tree.command(name="warn", description="Warn a member")
@app_commands.describe(user="Member to warn", reason="Reason")
@is_owner_or_admin()
async def warn(interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
    if is_protected_member(user):
        return await interaction.response.send_message("🛡️ Protected member.", ephemeral=True)
    key = user_key(interaction.guild.id, user.id)
    DATA["warnings"].setdefault(key, [])
    DATA["warnings"][key].append({"reason": reason, "moderator": interaction.user.id, "time": int(time.time())})
    save_data()
    await interaction.response.send_message(
        f"⚠️ {user.mention} warned.\n**Reason:** {reason}\n**Warnings:** `{len(DATA['warnings'][key])}`"
    )

@bot.tree.command(name="warnings", description="Show a member's warnings")
@app_commands.describe(user="Member")
@is_owner_or_admin()
async def warnings(interaction: Interaction, user: discord.Member):
    items = DATA["warnings"].get(user_key(interaction.guild.id, user.id), [])
    if not items:
        return await interaction.response.send_message("✅ No stored warnings.", ephemeral=True)
    lines = [f"`#{i}` <t:{x['time']}:R> — {x['reason']}" for i, x in enumerate(items[-10:], 1)]
    await interaction.response.send_message(
        embed=discord.Embed(title=f"⚠️ Warnings • {user}", description="\n".join(lines), color=EMBED_COLOR),
        ephemeral=True
    )

@bot.tree.command(name="clear", description="Delete recent messages")
@app_commands.describe(amount="1-100 messages")
@is_owner_or_admin()
async def clear(interaction: Interaction, amount: app_commands.Range[int, 1, 100]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Deleted `{len(deleted)}` messages.", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(user="Member", reason="Reason")
@is_owner_or_admin()
async def kick(interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
    if is_protected_member(user):
        return await interaction.response.send_message("🛡️ Protected member.", ephemeral=True)
    try:
        await user.kick(reason=reason)
        await interaction.response.send_message(f"👢 Kicked **{user}** — {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't kick that member.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(user="Member", reason="Reason")
@is_owner_or_admin()
async def ban(interaction: Interaction, user: discord.Member, reason: str = "No reason provided"):
    if is_protected_member(user):
        return await interaction.response.send_message("🛡️ Protected member.", ephemeral=True)
    try:
        await user.ban(reason=reason, delete_message_days=0)
        await interaction.response.send_message(f"🔨 Banned **{user}** — {reason}")
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't ban that member.", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a user by ID")
@app_commands.describe(user_id="Discord user ID", reason="Reason")
@is_owner_or_admin()
async def unban(interaction: Interaction, user_id: str, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        await interaction.response.send_message(f"🔓 Unbanned **{user}**.")
    except (ValueError, discord.NotFound):
        await interaction.response.send_message("❌ Invalid or unknown user ID.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I can't unban users.", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set channel slowmode")
@app_commands.describe(seconds="0-21600 seconds")
@is_owner_or_admin()
async def slowmode(interaction: Interaction, seconds: app_commands.Range[int, 0, 21600]):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
    await interaction.channel.edit(slowmode_delay=seconds)
    await interaction.response.send_message(f"🐢 Slowmode: `{seconds}s`.")

@bot.tree.command(name="lock", description="Lock current channel")
@is_owner_or_admin()
async def lock(interaction: Interaction):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = False
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔒 Channel locked.")

@bot.tree.command(name="unlock", description="Unlock current channel")
@is_owner_or_admin()
async def unlock(interaction: Interaction):
    if not isinstance(interaction.channel, discord.TextChannel):
        return await interaction.response.send_message("❌ Text channels only.", ephemeral=True)
    overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
    overwrite.send_messages = None
    await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
    await interaction.response.send_message("🔓 Channel unlocked.")


# ==========================================
# 12. COMMUNITY
# ==========================================
@bot.tree.command(name="poll", description="Create a community poll")
@app_commands.describe(question="Question", option1="First option", option2="Second option")
async def poll(interaction: Interaction, question: str, option1: str, option2: str):
    embed = discord.Embed(
        title="📊 Community Poll",
        description=f"**{question}**\n\n1️⃣ {option1}\n2️⃣ {option2}",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("1️⃣")
    await msg.add_reaction("2️⃣")

@bot.tree.command(name="suggest", description="Submit a suggestion")
@app_commands.describe(text="Suggestion")
async def suggest(interaction: Interaction, text: str):
    DATA["suggestions"] += 1
    number = DATA["suggestions"]
    save_data()
    embed = discord.Embed(title=f"💡 Suggestion #{number}", description=text, color=EMBED_COLOR)
    embed.set_author(name=str(interaction.user), icon_url=interaction.user.display_avatar.url)
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")

@bot.tree.command(name="announce", description="Send an announcement")
@app_commands.describe(title="Title", message="Message")
@is_owner_or_admin()
async def announce(interaction: Interaction, title: str, message: str):
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=EMBED_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_footer(text=f"Dark Night Community • {interaction.user.display_name}")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="broadcast", description="Send a community broadcast")
@app_commands.describe(
    title="Broadcast title",
    message="Broadcast message",
    channel="Destination channel (defaults to the current channel)",
    ping_everyone="Mention @everyone in the broadcast"
)
@is_owner_or_admin()
async def broadcast(
    interaction: Interaction,
    title: str,
    message: str,
    channel: discord.TextChannel = None,
    ping_everyone: bool = False,
):
    destination = channel or interaction.channel
    if not isinstance(destination, discord.TextChannel):
        return await interaction.response.send_message(
            "❌ The destination must be a text channel.",
            ephemeral=True,
        )

    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=EMBED_COLOR,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_author(
        name=f"{interaction.guild.name} • Community Broadcast",
    )
    embed.set_footer(text=f"Broadcast by {interaction.user.display_name}")

    content = "@everyone" if ping_everyone else None
    allowed = discord.AllowedMentions(everyone=ping_everyone)

    try:
        await destination.send(content=content, embed=embed, allowed_mentions=allowed)
    except discord.Forbidden:
        return await interaction.response.send_message(
            "❌ I do not have permission to send messages in that channel.",
            ephemeral=True,
        )

    await interaction.response.send_message(
        f"✅ Broadcast sent to {destination.mention}.",
        ephemeral=True,
    )

    await send_audit_log(
        interaction.guild,
        title="📢 Community Broadcast",
        actor=interaction.user,
        channel=destination,
        extra_fields=[
            ("Title", title[:1024], True),
            ("Message", message[:1024], False),
            ("Everyone Ping", "Yes" if ping_everyone else "No", True),
        ],
    )

@bot.tree.command(name="userinfo", description="Show member information")
async def userinfo(interaction: Interaction, user: discord.Member = None):
    user = user or interaction.user
    roles = [r.mention for r in user.roles[1:]][-10:]
    embed = discord.Embed(title=f"👤 {user}", color=EMBED_COLOR)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="ID", value=f"`{user.id}`", inline=True)
    embed.add_field(name="Joined", value=f"<t:{int(user.joined_at.timestamp())}:F>" if user.joined_at else "Unknown", inline=True)
    embed.add_field(name="Account", value=f"<t:{int(user.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Roles", value=" ".join(roles) if roles else "None", inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="avatar", description="Show a member avatar")
async def avatar(interaction: Interaction, user: discord.Member = None):
    user = user or interaction.user
    embed = discord.Embed(title=f"🖼️ {user.display_name}'s Avatar", color=EMBED_COLOR)
    embed.set_image(url=user.display_avatar.url)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roleinfo", description="Show role information")
async def roleinfo(interaction: Interaction, role: discord.Role):
    embed = discord.Embed(title=f"🎭 {role.name}", color=role.color.value or EMBED_COLOR)
    embed.add_field(name="ID", value=f"`{role.id}`", inline=True)
    embed.add_field(name="Members", value=f"`{len(role.members)}`", inline=True)
    embed.add_field(name="Position", value=f"`{role.position}`", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="serverinfo", description="Show server information")
async def serverinfo(interaction: Interaction):
    guild = interaction.guild
    update_peak_members(guild)
    embed = discord.Embed(title=f"🌙 {guild.name} • Server Info", color=EMBED_COLOR)
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Owner", value=f"<@{guild.owner_id}>", inline=True)
    embed.add_field(name="Members", value=f"`{guild.member_count}`", inline=True)
    embed.add_field(name="Roles", value=f"`{len(guild.roles)}`", inline=True)
    embed.add_field(name="Text", value=f"`{len(guild.text_channels)}`", inline=True)
    embed.add_field(name="Voice", value=f"`{len(guild.voice_channels)}`", inline=True)
    embed.add_field(name="Categories", value=f"`{len(guild.categories)}`", inline=True)
    embed.add_field(name="Boosts", value=f"`{guild.premium_subscription_count or 0}`", inline=True)
    embed.add_field(name="Peak", value=f"`{SERVER_PEAK_MEMBERS.get(guild.id, guild.member_count)}`", inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:F>", inline=False)
    await interaction.response.send_message(embed=embed)


# ==========================================
# 14. ECONOMY
# ==========================================
@bot.tree.command(name="balance", description="Check virtual Moon Coins")
async def balance(interaction: Interaction, user: discord.Member = None):
    user = user or interaction.user
    coins = get_wallet(interaction.guild.id, user.id)["coins"]
    await interaction.response.send_message(f"💰 {user.mention} has **{coins:,} Moon Coins**.")

@bot.tree.command(name="daily", description="Claim daily virtual coins")
async def daily(interaction: Interaction):
    wallet = get_wallet(interaction.guild.id, interaction.user.id)
    now = int(time.time())
    if now - wallet["last_daily"] < 86400:
        remaining = 86400 - (now - wallet["last_daily"])
        return await interaction.response.send_message(
            f"⏳ Next daily in **{remaining // 3600}h {(remaining % 3600) // 60}m**.", ephemeral=True
        )
    reward = random.randint(250, 600)
    wallet["coins"] += reward
    wallet["last_daily"] = now
    save_data()
    await interaction.response.send_message(f"🎁 Daily: **+{reward:,} Moon Coins**!")

@bot.tree.command(name="work", description="Earn virtual Moon Coins")
async def work(interaction: Interaction):
    reward = random.randint(50, 250)
    wallet = get_wallet(interaction.guild.id, interaction.user.id)
    wallet["coins"] += reward
    save_data()
    await interaction.response.send_message(
        f"💼 You worked as a **{random.choice(['builder','designer','developer','DJ','streamer','moderator'])}** and earned **{reward:,}** coins!"
    )

@bot.tree.command(name="pay", description="Pay virtual coins to a member")
async def pay(interaction: Interaction, user: discord.Member, amount: app_commands.Range[int, 1, 1000000]):
    if user.bot or user.id == interaction.user.id:
        return await interaction.response.send_message("❌ Choose another member.", ephemeral=True)
    sender = get_wallet(interaction.guild.id, interaction.user.id)
    receiver = get_wallet(interaction.guild.id, user.id)
    if sender["coins"] < amount:
        return await interaction.response.send_message("❌ Not enough Moon Coins.", ephemeral=True)
    sender["coins"] -= amount
    receiver["coins"] += amount
    save_data()
    await interaction.response.send_message(f"💸 Sent **{amount:,}** Moon Coins to {user.mention}.")

@bot.tree.command(name="givecoins", description="Give virtual Moon Coins to a member")
@app_commands.describe(amount="Amount of Moon Coins", user="Member who receives the coins")
@is_owner_or_admin()
async def givecoins(interaction: Interaction, amount: app_commands.Range[int, 1, 1000000000], user: discord.Member):
    if user.bot:
        return await interaction.response.send_message("❌ You cannot give coins to a bot.", ephemeral=True)
    wallet = get_wallet(interaction.guild.id, user.id)
    wallet["coins"] += amount
    save_data()
    await interaction.response.send_message(f"💰 Added **{amount:,} Moon Coins** to {user.mention}.\n💳 New balance: **{wallet['coins']:,}**")


@bot.tree.command(name="leaderboard", description="Richest members leaderboard")
async def leaderboard(interaction: Interaction):
    gid = interaction.guild.id
    entries = []
    for key, wallet in DATA["economy"].items():
        if key.startswith(f"{gid}:"):
            try:
                entries.append((wallet["coins"], int(key.split(":")[1])))
            except ValueError:
                pass
    entries.sort(reverse=True)
    lines = [f"**{i}.** <@{uid}> — `{coins:,}` 💰" for i, (coins, uid) in enumerate(entries[:10], 1)]
    await interaction.response.send_message(
        embed=discord.Embed(
            title="💰 Dark Night • Economy Leaderboard",
            description="\n".join(lines) if lines else "No economy data yet.",
            color=EMBED_COLOR
        )
    )


# ==========================================
# 15. XP / LEVELS
# ==========================================
@bot.tree.command(name="rank", description="Show XP and level")
async def rank(interaction: Interaction, user: discord.Member = None):
    user = user or interaction.user
    stats = get_xp(interaction.guild.id, user.id)
    embed = discord.Embed(title=f"🏆 {user.display_name} • Rank", color=EMBED_COLOR)
    embed.set_thumbnail(url=user.display_avatar.url)
    embed.add_field(name="Level", value=f"`{stats['level']}`", inline=True)
    embed.add_field(name="XP", value=f"`{stats['xp']}`", inline=True)
    embed.add_field(name="Next Level", value=f"`{xp_for_next_level(stats['level'])}` XP", inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboardxp", description="XP leaderboard")
async def leaderboardxp(interaction: Interaction):
    gid = interaction.guild.id
    entries = []
    for key, stats in DATA["xp"].items():
        if key.startswith(f"{gid}:"):
            try:
                entries.append((stats["xp"], int(key.split(":")[1])))
            except ValueError:
                pass
    entries.sort(reverse=True)
    lines = [f"**{i}.** <@{uid}> — `{xp:,}` XP" for i, (xp, uid) in enumerate(entries[:10], 1)]
    await interaction.response.send_message(
        embed=discord.Embed(title="🏆 Dark Night • XP Leaderboard", description="\n".join(lines) if lines else "No XP yet.", color=EMBED_COLOR)
    )


# ==========================================
# 16. GAMES
# ==========================================
@bot.tree.command(name="coinflip", description="Flip a virtual coin")
async def coinflip(interaction: Interaction):
    await interaction.response.send_message(f"🪙 **{random.choice(['HEADS','TAILS'])}**")

@bot.tree.command(name="dice", description="Roll a virtual die")
async def dice(interaction: Interaction, sides: app_commands.Range[int, 2, 100] = 6):
    await interaction.response.send_message(f"🎲 You rolled **{random.randint(1, sides)}** / `{sides}`.")

@bot.tree.command(name="rps", description="Play Rock Paper Scissors")
async def rps(interaction: Interaction, choice: str):
    choice = choice.lower().strip()
    if choice not in {"rock", "paper", "scissors"}:
        return await interaction.response.send_message("❌ Use rock, paper or scissors.", ephemeral=True)
    bot_choice = random.choice(["rock", "paper", "scissors"])
    win = (choice, bot_choice) in {("rock","scissors"),("paper","rock"),("scissors","paper")}
    result = "🤝 Draw!" if choice == bot_choice else ("🏆 You win!" if win else "💀 I win!")
    await interaction.response.send_message(f"✊ You: **{choice}**\n🤖 Dark Night: **{bot_choice}**\n\n{result}")

@bot.tree.command(name="8ball", description="Ask the Magic 8-Ball")
async def eightball(interaction: Interaction, question: str):
    await interaction.response.send_message(
        f"🔮 **{question}**\n\n**Answer:** {random.choice(['Yes. 🌙','No. 💀','Absolutely. ✨','Ask later. 🔮','Very likely. ⭐','Unlikely. 🌑'])}"
    )

@bot.tree.command(name="roulette", description="Virtual roulette using Moon Coins")
async def roulette(interaction: Interaction, amount: str, color: str):
    parsed_amount = parse_coin_amount(amount)
    if parsed_amount is None:
        return await interaction.response.send_message("❌ Invalid amount. Use `1k`, `1m`, `2b` or a number.", ephemeral=True)
    amount = parsed_amount
    color = color.lower().strip()
    if color not in {"red","black","green"}:
        return await interaction.response.send_message("❌ Use red, black or green.", ephemeral=True)
    wallet = get_wallet(interaction.guild.id, interaction.user.id)
    if wallet["coins"] < amount:
        return await interaction.response.send_message("❌ Not enough Moon Coins.", ephemeral=True)
    number = random.randint(0,36)
    reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
    result = "green" if number == 0 else ("red" if number in reds else "black")
    if color == result:
        winnings = amount * (14 if color == "green" else 2)
        wallet["coins"] += winnings - amount
        text = f"🎉 Won **{winnings:,}**!"
    else:
        wallet["coins"] -= amount
        text = f"💀 Lost **{amount:,}**."
    save_data()
    await interaction.response.send_message(f"🎰 `{number}` — **{result.upper()}**\n{text}\n💰 `{wallet['coins']:,}`")

@bot.tree.command(name="slots", description="Virtual slot machine")
async def slots(interaction: Interaction, amount: str):
    parsed_amount = parse_coin_amount(amount)
    if parsed_amount is None:
        return await interaction.response.send_message("❌ Invalid amount. Use `1k`, `1m`, `2b` or a number.", ephemeral=True)
    amount = parsed_amount
    wallet = get_wallet(interaction.guild.id, interaction.user.id)
    if wallet["coins"] < amount:
        return await interaction.response.send_message("❌ Not enough Moon Coins.", ephemeral=True)
    symbols = ["🌙","⭐","💎","🍒","7️⃣"]
    result = [random.choice(symbols) for _ in range(3)]
    multiplier = 8 if len(set(result)) == 1 else (2 if len(set(result)) == 2 else 0)
    wallet["coins"] += amount * multiplier - amount
    save_data()
    await interaction.response.send_message(
        f"🎰 **[ {' | '.join(result)} ]**\n"
        f"{'🎉 Won ' + str(amount*multiplier) + '!' if multiplier else '💀 Lost ' + str(amount) + '.'}\n"
        f"💰 `{wallet['coins']:,}`"
    )

def blackjack_card():
    return random.choice([2,3,4,5,6,7,8,9,10,10,10,10,11])

def blackjack_total(cards):
    total = sum(cards)
    aces = cards.count(11)
    while total > 21 and aces:
        total -= 10
        aces -= 1
    return total

@bot.tree.command(name="blackjack", description="Virtual blackjack")
async def blackjack(interaction: Interaction, amount: str):
    parsed_amount = parse_coin_amount(amount)
    if parsed_amount is None:
        return await interaction.response.send_message("❌ Invalid amount. Use `1k`, `1m`, `2b` or a number.", ephemeral=True)
    amount = parsed_amount
    wallet = get_wallet(interaction.guild.id, interaction.user.id)
    if wallet["coins"] < amount:
        return await interaction.response.send_message("❌ Not enough Moon Coins.", ephemeral=True)
    player, dealer = [blackjack_card(), blackjack_card()], [blackjack_card(), blackjack_card()]
    while blackjack_total(player) < 17:
        player.append(blackjack_card())
    while blackjack_total(dealer) < 17:
        dealer.append(blackjack_card())
    p, d = blackjack_total(player), blackjack_total(dealer)
    if p > 21 or (d <= 21 and d > p):
        wallet["coins"] -= amount
        result = f"💀 Lost **{amount:,}**."
    elif p == d:
        result = "🤝 Push — bet returned."
    elif p == 21 and len(player) == 2:
        win = int(amount * 1.5)
        wallet["coins"] += win
        result = f"🃏 Blackjack — won **{win:,}**."
    else:
        wallet["coins"] += amount
        result = f"🏆 Won **{amount:,}**."
    save_data()
    await interaction.response.send_message(f"🃏 Player `{p}` vs Dealer `{d}`\n{result}\n💰 `{wallet['coins']:,}`")


# ==========================================
# 🎮 GAMES CENTER — one panel for all games
# ==========================================
class BetModal(Modal):
    def __init__(self, game_name):
        self.game_name = game_name
        super().__init__(title=f"{game_name} • Moon Coins")
        self.amount = TextInput(label="Bet amount", placeholder="Examples: 1k, 1m, 2b", max_length=30, required=True)
        self.add_item(self.amount)

    async def on_submit(self, interaction: Interaction):
        amount = parse_coin_amount(self.amount.value)
        if amount is None:
            return await interaction.response.send_message("❌ Invalid amount. Use values like `1k`, `1m`, `2b`.", ephemeral=True)
        wallet = get_wallet(interaction.guild.id, interaction.user.id)
        if wallet["coins"] < amount:
            return await interaction.response.send_message(f"❌ You need **{format_coins(amount)}** Moon Coins.", ephemeral=True)
        game = self.game_name
        if game == "Slots":
            symbols = ["🌙", "⭐", "💎", "🍒", "7️⃣", "🪙"]
            result = [random.choice(symbols) for _ in range(3)]
            multiplier = 10 if len(set(result)) == 1 else (3 if len(set(result)) == 2 else 0)
            wallet["coins"] += amount * multiplier - amount
            text = f"🎰 **[ {' | '.join(result)} ]**\n" + (f"🏆 Won **{format_coins(amount*multiplier)}**!" if multiplier else f"💀 Lost **{format_coins(amount)}**.")
        elif game == "Roulette":
            number = random.randint(0, 36)
            reds = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
            color = "green" if number == 0 else ("red" if number in reds else "black")
            if color == "green":
                wallet["coins"] += amount * 35
                text = f"🎰 **0 • GREEN** — 🏆 Jackpot **{format_coins(amount*35)}**!"
            else:
                wallet["coins"] -= amount
                text = f"🎰 **{number} • {color.upper()}** — 💀 Lost **{format_coins(amount)}**."
                # 50/50 simple color bet is intentionally not exposed in this panel.
                if random.random() < 0.5:
                    wallet["coins"] += amount * 2
                    text += "\n✨ Dark Night bonus win!"
        elif game == "High / Low":
            n = random.randint(1, 13)
            guess = "HIGH" if n >= 7 else "LOW"
            wallet["coins"] += amount
            text = f"🃏 Card: **{n}** • **{guess}**\n🏆 You won **{format_coins(amount)}**!"
        elif game == "Even / Odd":
            n = random.randint(1, 36)
            result = "EVEN" if n % 2 == 0 else "ODD"
            win = random.choice([True, False])
            if win:
                wallet["coins"] += amount
                text = f"🎯 Number **{n}** • **{result}**\n🏆 Won **{format_coins(amount)}**!"
            else:
                wallet["coins"] -= amount
                text = f"🎯 Number **{n}** • **{result}**\n💀 Lost **{format_coins(amount)}**."
        elif game == "Wheel":
            mult = random.choice([0, 0, 0.5, 1, 1, 2, 3, 5, 10])
            payout = int(amount * mult)
            wallet["coins"] += payout - amount
            text = f"🎡 Wheel landed on **x{mult:g}**\n" + (f"🏆 Won **{format_coins(payout)}**!" if payout > amount else f"💀 Lost **{format_coins(amount - payout)}**.")
        elif game == "Double or Nothing":
            if random.choice([True, False]):
                wallet["coins"] += amount
                text = f"⚡ Double! 🏆 You won **{format_coins(amount)}**."
            else:
                wallet["coins"] -= amount
                text = f"💀 Nothing! Lost **{format_coins(amount)}**."
        elif game == "Treasure":
            prize = random.choice([0, 0, 0, amount // 2, amount, amount * 2, amount * 5])
            wallet["coins"] += prize - amount
            text = f"🗝️ Treasure payout: **{format_coins(prize)}**\n" + (f"🏆 Profit: **{format_coins(prize-amount)}**!" if prize >= amount else f"💀 Lost **{format_coins(amount-prize)}**.")
        else:
            wallet["coins"] -= amount
            text = f"🎮 {game} result: **{random.choice(['WIN', 'LOSE'])}**"
        save_data()
        embed = discord.Embed(title=f"🎮 {game}", description=text + f"\n\n💰 Balance: **{format_coins(wallet['coins'])}**", color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)

class GameQuestionModal(Modal):
    def __init__(self, game_name):
        self.game_name = game_name
        super().__init__(title=game_name)
        self.value = TextInput(label="Your choice / question", placeholder="Type your choice...", max_length=200, required=True)
        self.add_item(self.value)

    async def on_submit(self, interaction: Interaction):
        value = self.value.value.strip().lower()
        if self.game_name == "RPS":
            if value not in {"rock", "paper", "scissors"}:
                return await interaction.response.send_message("❌ Use `rock`, `paper` or `scissors`.", ephemeral=True)
            bot_choice = random.choice(["rock", "paper", "scissors"])
            win = (value, bot_choice) in {("rock","scissors"),("paper","rock"),("scissors","paper")}
            result = "🤝 Draw!" if value == bot_choice else ("🏆 You win!" if win else "💀 Dark Night wins!")
            return await interaction.response.send_message(f"✊ You: **{value}**\n🤖 Dark Night: **{bot_choice}**\n\n{result}")
        answers = ["Yes. 🌙", "No. 💀", "Absolutely. ✨", "Ask later. 🔮", "Very likely. ⭐", "Unlikely. 🌑"]
        await interaction.response.send_message(f"🔮 **{self.value.value}**\n\n**Answer:** {random.choice(answers)}")

class GamesCenterSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Coinflip", emoji="🪙", value="coinflip"),
            discord.SelectOption(label="Dice", emoji="🎲", value="dice"),
            discord.SelectOption(label="RPS", emoji="✊", value="rps"),
            discord.SelectOption(label="8-Ball", emoji="🔮", value="8ball"),
            discord.SelectOption(label="Roulette", emoji="🎰", value="roulette"),
            discord.SelectOption(label="Slots", emoji="🎰", value="slots"),
            discord.SelectOption(label="Blackjack", emoji="🃏", value="blackjack"),
            discord.SelectOption(label="High / Low", emoji="🃏", value="highlow"),
            discord.SelectOption(label="Even / Odd", emoji="🎯", value="evenodd"),
            discord.SelectOption(label="Wheel", emoji="🎡", value="wheel"),
            discord.SelectOption(label="Double or Nothing", emoji="⚡", value="double"),
            discord.SelectOption(label="Treasure", emoji="🗝️", value="treasure"),
            discord.SelectOption(label="Number Guess", emoji="🔢", value="numberguess"),
            discord.SelectOption(label="Quick Draw", emoji="🤠", value="quickdraw"),
            discord.SelectOption(label="Lucky Color", emoji="🌈", value="luckycolor"),
        ]
        super().__init__(placeholder="🎮 Choose a Dark Night game...", min_values=1, max_values=1, options=options, custom_id="moon_games_center")

    async def callback(self, interaction: Interaction):
        game = self.values[0]
        if game == "coinflip":
            return await interaction.response.send_message(f"🪙 **{random.choice(['HEADS', 'TAILS'])}**")
        if game == "dice":
            return await interaction.response.send_message(f"🎲 You rolled **{random.randint(1, 6)} / 6**.")
        if game == "rps":
            return await interaction.response.send_modal(GameQuestionModal("RPS"))
        if game == "8ball":
            return await interaction.response.send_modal(GameQuestionModal("8-Ball"))
        names = {"roulette":"Roulette", "slots":"Slots", "blackjack":"Blackjack", "highlow":"High / Low", "evenodd":"Even / Odd", "wheel":"Wheel", "double":"Double or Nothing", "treasure":"Treasure"}
        if game in names:
            return await interaction.response.send_modal(BetModal(names[game]))
        if game == "numberguess":
            n = random.randint(1, 10)
            return await interaction.response.send_message(f"🔢 Secret number generated! Try `/numberguess` to play.\n🎯 Hint range: **1–10**", ephemeral=True)
        if game == "quickdraw":
            return await interaction.response.send_message(f"🤠 **QUICK DRAW!**\n{random.choice(['⚡ You were too slow!', '💥 You won the draw!', '🎯 Perfect shot!', '💀 Dark Night was faster!'])}")
        if game == "luckycolor":
            return await interaction.response.send_message(f"🌈 Lucky Color: **{random.choice(['🔴 Red','⚫ Black','🟢 Green','🔵 Blue','🟣 Purple','🟡 Gold'])}**")

class GamesCenterView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(GamesCenterSelect())

def get_games_center_embed():
    embed = discord.Embed(
        title="🎮  Dark Night's Games Center  ›",
        description=(
            "## ✦ Play. Risk. Win. Repeat.\n\n"
            "Choose a game from the menu below and it will launch instantly.\n\n"
            "💰 **Bet games** accept `1k`, `1m`, `2b` and more.\n"
            "🏆 **Moon Coins** are virtual server coins only.\n\n"
            "### 🎰 Casino\nRoulette • Roulette Arena • Slots • Blackjack • Wheel • Double or Nothing\n\n"
            "### 🕹️ Quick Games\nCoinflip • Dice • RPS • 8-Ball • High/Low • Even/Odd • Treasure • Number Guess • Quick Draw • Lucky Color\n\n"
            "### 📖 What each game does\n"
            "🪙 Coinflip = heads/tails • 🎲 Dice = random number • ✊ RPS = play against the bot • 🔮 8-Ball = random answer\n"
            "🎰 Roulette = color betting • 🎰 Roulette Arena = multiplayer pot • 🃏 Blackjack = beat the dealer • 🎰 Slots = match symbols\n"
            "🃏 High/Low = high or low result • 🎯 Even/Odd = parity result • 🎡 Wheel = multiplier spin • ⚡ Double or Nothing = risk your bet\n"
            "🗝️ Treasure = random chest payout • 🔢 Number Guess = guess 1–10 • 🤠 Quick Draw = reflex mini-game • 🌈 Lucky Color = random color\n\n"
            "-# `© 2026 Dark Night™ • Games Center`"
        ),
        color=EMBED_COLOR,
    )
    if TWEET_PANEL_IMAGE_URL:
        embed.set_thumbnail(url=TWEET_PANEL_IMAGE_URL)
    return embed

@bot.tree.command(name="games", description="Open the Dark Night Games Center")
async def games_center(interaction: Interaction):
    await interaction.response.send_message(embed=get_games_center_embed(), view=GamesCenterView())

@bot.tree.command(name="numberguess", description="Guess a number from 1 to 10")
async def numberguess(interaction: Interaction, number: app_commands.Range[int, 1, 10]):
    secret = random.randint(1, 10)
    if number == secret:
        return await interaction.response.send_message(f"🔢 **{secret}** — 🏆 Correct! You got it!")
    await interaction.response.send_message(f"🔢 **{secret}** — ❌ Not this time. You chose `{number}`.")

@bot.tree.command(name="quickdraw", description="Test your reflexes")
async def quickdraw(interaction: Interaction):
    await interaction.response.send_message(f"🤠 **QUICK DRAW!**\n{random.choice(['⚡ Lightning reflexes!', '🎯 Perfect shot!', '💀 Dark Night was faster!', '🏆 You won the draw!'])}")

# ==========================================
# 🔊 ONE-TAP VOICE ROOM PANEL
# ==========================================

def get_voice_panel_embed():
    embed = discord.Embed(
        title="🌙 9e Moon Night 🌙 Voice Panel",
        description=(
            "Manage your room, adjust visibility, and control voice features from one clean panel.\n\n"
            "✦ **Check our rules here.**\n"
            "✦ **For voice assistance, join a support voice channel.**\n\n"
            "👑 **Room owner + Server Owner/Admin can control it.**"
        ),
        color=EMBED_COLOR,
    )
    embed.set_image(url=GENERAL_TICKET_BANNER_URL)
    embed.set_thumbnail(url=COMMUNITY_IMAGE_URL)
    embed.set_footer(text="© 2026 Moon Night 🌙. All rights reserved.")
    return embed


class VoicePanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _get_room(self, interaction: Interaction):
        # IMPORTANT: this panel is posted in a NORMAL TEXT CHANNEL.
        # The button automatically finds the temporary VC owned by the
        # person who clicked it. They do NOT need to be inside the VC.
        # Server Owner/Admin can manage a room too.
        owned = [
            (cid, meta)
            for cid, meta in TEMP_VC_META.items()
            if meta.get("owner") == interaction.user.id
        ]

        channel = None
        if owned:
            # Normally one owner has one active room. If more than one exists,
            # use the newest one.
            cid, _ = max(owned, key=lambda item: item[1].get("created_at", 0))
            channel = interaction.guild.get_channel(cid)

        # Admin/Owner fallback: if they are currently in a temporary room,
        # let them control that room.
        if channel is None and (
            interaction.user.id == OWNER_ID
            or interaction.user.guild_permissions.administrator
        ):
            voice = interaction.user.voice
            if voice and isinstance(voice.channel, discord.VoiceChannel):
                if voice.channel.id in TEMP_VC_META:
                    channel = voice.channel

        if not isinstance(channel, discord.VoiceChannel):
            await interaction.response.send_message(
                "❌ You don't have an active temporary room right now.",
                ephemeral=True,
            )
            return None

        if not can_manage_temp_vc(interaction, channel):
            await interaction.response.send_message(
                "❌ You can only control **your own** temporary room.",
                ephemeral=True,
            )
            return None

        return channel

    @discord.ui.button(label="Lock", emoji="🔒", style=ButtonStyle.secondary, custom_id="voice_panel_lock")
    async def lock(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if not channel: return
        meta = TEMP_VC_META[channel.id]
        meta["locked"] = True
        await channel.set_permissions(channel.guild.default_role, connect=False, reason=f"Voice panel lock by {interaction.user}")
        owner = channel.guild.get_member(meta.get("owner"))
        if owner:
            await channel.set_permissions(owner, connect=True, reason="Keep room owner connected")
        await interaction.response.send_message(f"🔒 **{channel.name}** is now locked.", ephemeral=True)

    @discord.ui.button(label="Unlock", emoji="🔓", style=ButtonStyle.success, custom_id="voice_panel_unlock")
    async def unlock(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if not channel: return
        TEMP_VC_META[channel.id]["locked"] = False
        await channel.set_permissions(channel.guild.default_role, connect=None, reason=f"Voice panel unlock by {interaction.user}")
        await interaction.response.send_message(f"🔓 **{channel.name}** is now unlocked.", ephemeral=True)

    @discord.ui.button(label="Limit", emoji="👥", style=ButtonStyle.primary, custom_id="voice_panel_limit")
    async def limit(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if channel: await interaction.response.send_modal(VCLimitModal(channel))

    @discord.ui.button(label="Rename", emoji="✏️", style=ButtonStyle.primary, custom_id="voice_panel_rename")
    async def rename(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if channel: await interaction.response.send_modal(VCRenameModal(channel))

    @discord.ui.button(label="Kick", emoji="👢", style=ButtonStyle.danger, custom_id="voice_panel_kick")
    async def kick(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if channel: await interaction.response.send_modal(VCKickModal(channel))

    @discord.ui.button(label="Move", emoji="↪️", style=ButtonStyle.secondary, custom_id="voice_panel_move")
    async def move(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if channel: await interaction.response.send_modal(VCMoveModal(channel))

    @discord.ui.button(label="Close Room", emoji="🗑️", style=ButtonStyle.danger, custom_id="voice_panel_close")
    async def close(self, interaction: Interaction, button: Button):
        channel = await self._get_room(interaction)
        if not channel: return
        cid = channel.id
        TEMP_VCS.pop(cid, None)
        TEMP_VC_META.pop(cid, None)
        try:
            await channel.delete(reason=f"Temporary room closed from voice panel by {interaction.user}")
            await interaction.response.send_message("🗑️ **Your temporary room was closed.**", ephemeral=True)
        except discord.HTTPException:
            await interaction.response.send_message("❌ I could not close the room.", ephemeral=True)


@bot.tree.command(name="voicepanel", description="Send the one-tap temporary voice room control panel")
@is_owner_or_admin()
async def voicepanel(interaction: Interaction):
    await interaction.response.defer(ephemeral=True)
    target = interaction.guild.get_channel(VOICE_PANEL_CHANNEL_ID)
    if not isinstance(target, (discord.TextChannel, discord.Thread)):
        return await interaction.followup.send(f"❌ Panel channel `{VOICE_PANEL_CHANNEL_ID}` was not found or is not a normal text channel.", ephemeral=True)
    try:
        await target.send(embed=get_voice_panel_embed(), view=VoicePanelView())
    except discord.Forbidden:
        return await interaction.followup.send("❌ I cannot send messages in that text channel. Check the bot's permissions.", ephemeral=True)
    except discord.HTTPException as exc:
        print(f"[VOICE PANEL] Send error: {exc!r}")
        return await interaction.followup.send("❌ Discord returned an error while sending the panel.", ephemeral=True)
    await interaction.followup.send(f"✅ Voice panel sent to {target.mention}.", ephemeral=True)


@bot.tree.command(name="vccenter", description="Open your temporary voice room controls")
async def vccenter(interaction: Interaction):
    channel = interaction.user.voice.channel if interaction.user.voice else None
    if not isinstance(channel, discord.VoiceChannel) or channel.id not in TEMP_VCS:
        return await interaction.response.send_message("❌ You are not inside a Dark Night temporary VC.", ephemeral=True)
    if not can_manage_temp_vc(interaction, channel):
        return await interaction.response.send_message("❌ Only the room owner or a server Owner/Admin can control this room.", ephemeral=True)
    await interaction.response.send_message(embed=make_temp_vc_embed(channel), view=TempVCControlView(), ephemeral=True)


# ==========================================
# 17. MAFIA
# ==========================================
class MafiaJoinView(View):
    def __init__(self, guild_id):
        super().__init__(timeout=300)
        self.guild_id = guild_id

    @discord.ui.button(label="🕵️ Join Mafia", style=ButtonStyle.primary, custom_id="moon_mafia_join")
    async def join(self, interaction: Interaction, button: Button):
        game = MAFIA_GAMES.get(self.guild_id)
        if not game or game["started"]:
            return await interaction.response.send_message("❌ Lobby closed.", ephemeral=True)
        if interaction.user.id in game["players"]:
            return await interaction.response.send_message("⚠️ Already joined.", ephemeral=True)
        if len(game["players"]) >= 12:
            return await interaction.response.send_message("❌ Lobby full.", ephemeral=True)
        game["players"].append(interaction.user.id)
        await interaction.response.edit_message(
            content=f"🔪 **Mafia Lobby** — `{len(game['players'])}/12`\nClick **Join Mafia** to enter.",
            view=self
        )

@bot.tree.command(name="mafia", description="Create, join, leave, start or view Mafia")
@app_commands.describe(action="create, join, leave, start or status")
@app_commands.choices(action=[
    app_commands.Choice(name="create", value="create"),
    app_commands.Choice(name="join", value="join"),
    app_commands.Choice(name="leave", value="leave"),
    app_commands.Choice(name="start", value="start"),
    app_commands.Choice(name="status", value="status")
])
async def mafia(interaction: Interaction, action: app_commands.Choice[str]):
    gid = interaction.guild.id
    game = MAFIA_GAMES.get(gid)

    if action.value == "create":
        if game and not game["finished"]:
            return await interaction.response.send_message("❌ A Mafia game already exists.", ephemeral=True)
        MAFIA_GAMES[gid] = {"host": interaction.user.id, "players": [interaction.user.id], "started": False, "finished": False}
        return await interaction.response.send_message(
            "🔪 **Mafia Lobby Created!**\nPlayers: `1/12`", view=MafiaJoinView(gid)
        )

    if not game:
        return await interaction.response.send_message("❌ Use `/mafia create` first.", ephemeral=True)

    if action.value == "join":
        if not game["started"] and interaction.user.id not in game["players"] and len(game["players"]) < 12:
            game["players"].append(interaction.user.id)
        return await interaction.response.send_message(f"🔪 Players: `{len(game['players'])}/12`", ephemeral=True)

    if action.value == "leave":
        if game["started"]:
            return await interaction.response.send_message("❌ Game already started.", ephemeral=True)
        if interaction.user.id in game["players"]:
            game["players"].remove(interaction.user.id)
        return await interaction.response.send_message("🚪 Left the Mafia lobby.", ephemeral=True)

    if action.value == "status":
        mentions = " ".join(f"<@{uid}>" for uid in game["players"])
        return await interaction.response.send_message(f"🔪 **Mafia** `{len(game['players'])}/12`\n{mentions}")

    if interaction.user.id != game["host"]:
        return await interaction.response.send_message("❌ Only the host can start.", ephemeral=True)
    if len(game["players"]) < 4:
        return await interaction.response.send_message("❌ Need at least 4 players.", ephemeral=True)
    game["started"] = True
    roles = ["Mafia", "Detective", "Doctor"] + ["Civilian"] * max(0, len(game["players"]) - 3)
    random.shuffle(roles)
    for uid, role in zip(game["players"], roles):
        try:
            user = await bot.fetch_user(uid)
            await user.send(f"🔪 **Dark Night Mafia**\nYour secret role: **{role}**")
        except discord.HTTPException:
            pass
    await interaction.response.send_message("🔪 **Mafia started!** Secret roles were sent in DMs.")


# ==========================================
# 18. GIVEAWAYS
# ==========================================
@bot.tree.command(name="giveaway", description="Start a timed giveaway")
@app_commands.describe(minutes="Duration", prize="Prize", winners="Winner count")
@is_owner_or_admin()
async def giveaway(interaction: Interaction, minutes: app_commands.Range[int, 1, 10080], prize: str, winners: app_commands.Range[int, 1, 20]):
    end_at = int(time.time()) + minutes * 60
    embed = discord.Embed(
        title="🎁 DARK NIGHT GIVEAWAY",
        description=f"**Prize:** {prize}\n**Winners:** `{winners}`\n**Ends:** <t:{end_at}:R>\n\nReact with 🎉 to enter!",
        color=EMBED_COLOR
    )
    await interaction.response.send_message(embed=embed)
    msg = await interaction.original_response()
    await msg.add_reaction("🎉")
    DATA["giveaways"][str(msg.id)] = {"channel": interaction.channel.id, "prize": prize, "winners": winners}
    save_data()
    await asyncio.sleep(minutes * 60)
    try:
        msg = await interaction.channel.fetch_message(msg.id)
        reaction = discord.utils.get(msg.reactions, emoji="🎉")
        users = [u async for u in reaction.users()] if reaction else []
        users = [u for u in users if not u.bot]
        if users:
            chosen = random.sample(users, min(winners, len(users)))
            await interaction.channel.send(f"🎉 Giveaway ended! {', '.join(u.mention for u in chosen)} won **{prize}**!")
        else:
            await interaction.channel.send("🎁 Giveaway ended with no valid entries.")
    except discord.HTTPException:
        pass
    DATA["giveaways"].pop(str(msg.id), None)
    save_data()

@bot.tree.command(name="giveaway_end", description="End a giveaway early")
@is_owner_or_admin()
async def giveaway_end(interaction: Interaction, message_id: str):
    info = DATA["giveaways"].get(message_id)
    if not info:
        return await interaction.response.send_message("❌ Giveaway not found.", ephemeral=True)
    await interaction.response.send_message("✅ Giveaway marked for ending. If it is still running, use its reaction list to pick a winner.", ephemeral=True)


# ==========================================
# 19. BIRTHDAYS
# ==========================================
@bot.tree.command(name="birthday", description="Set, view or remove your birthday")
@app_commands.describe(action="set, view or remove", date="DD/MM when using set")
@app_commands.choices(action=[
    app_commands.Choice(name="set", value="set"),
    app_commands.Choice(name="view", value="view"),
    app_commands.Choice(name="remove", value="remove")
])
async def birthday(interaction: Interaction, action: app_commands.Choice[str], date: str = None):
    key = user_key(interaction.guild.id, interaction.user.id)
    if action.value == "remove":
        DATA["birthdays"].pop(key, None)
        save_data()
        return await interaction.response.send_message("🎂 Birthday removed.", ephemeral=True)
    if action.value == "view":
        return await interaction.response.send_message(
            f"🎂 Your birthday: **{DATA['birthdays'].get(key, 'Not set')}**", ephemeral=True
        )
    if not date or not re.fullmatch(r"(0[1-9]|[12]\d|3[01])/(0[1-9]|1[0-2])", date):
        return await interaction.response.send_message("❌ Use `DD/MM`.", ephemeral=True)
    DATA["birthdays"][key] = date
    save_data()
    await interaction.response.send_message(f"🎂 Birthday saved: **{date}**.", ephemeral=True)


# ==========================================
# 20. LISTENERS
# ==========================================
@bot.listen("on_message")
async def moon_xp_listener(message: discord.Message):
    if message.author.bot or not message.guild:
        return
    key = user_key(message.guild.id, message.author.id)
    now = time.time()
    if now - XP_LAST_MESSAGE.get(key, 0) < XP_COOLDOWN:
        return
    XP_LAST_MESSAGE[key] = now
    stats = get_xp(message.guild.id, message.author.id)
    old_level = stats["level"]
    stats["xp"] += random.randint(8, 18)
    stats["level"] = level_for_xp(stats["xp"])
    save_data()
    if stats["level"] > old_level:
        try:
            await message.channel.send(f"🎉 {message.author.mention} reached **Level {stats['level']}**!")
        except discord.HTTPException:
            pass

@bot.listen("on_member_join")
async def moon_welcome_listener(member: discord.Member):
    update_peak_members(member.guild)
    if not WELCOME_CHANNEL_ID:
        return
    channel = member.guild.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🌙 Welcome To Dark Night!",
            description=f"Hey {member.mention}! Welcome to **{member.guild.name}**.\nYou are member **#{member.guild.member_count}**.\n\nRead the rules and enjoy your stay! ✨",
            color=EMBED_COLOR
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException:
            pass

@bot.listen("on_member_remove")
async def moon_leave_listener(member: discord.Member):
    if LEAVE_CHANNEL_ID:
        channel = member.guild.get_channel(LEAVE_CHANNEL_ID)
        if channel:
            try:
                await channel.send(f"💔 **{member}** left Dark Night. We hope to see you again!")
            except discord.HTTPException:
                pass

@bot.listen("on_voice_state_update")
async def temporary_voice_listener(member, before, after):
    # Create one private temporary room when a member enters the creator channel.
    if TEMP_VC_CHANNEL_ID and after.channel and after.channel.id == TEMP_VC_CHANNEL_ID:
        try:
            # Reuse an existing room owned by the member instead of creating duplicates.
            existing_id = next((cid for cid, meta in TEMP_VC_META.items() if meta.get("owner") == member.id), None)
            if existing_id:
                existing = member.guild.get_channel(existing_id)
                if isinstance(existing, discord.VoiceChannel):
                    await member.move_to(existing, reason="Dark Night existing temporary VC")
                    return

            channel = await member.guild.create_voice_channel(
                name=f"{TEMP_VC_NAME_PREFIX} {member.display_name}'s Room",
                category=after.channel.category,
                user_limit=max(0, min(TEMP_VC_DEFAULT_LIMIT, 99)),
                reason=f"Dark Night temporary VC for {member} ({member.id})"
            )
            TEMP_VCS[channel.id] = member.id
            TEMP_VC_META[channel.id] = {
                "owner": member.id,
                "locked": False,
                "limit": max(0, min(TEMP_VC_DEFAULT_LIMIT, 99)),
                "created_at": int(time.time()),
            }
            await member.move_to(channel, reason="Dark Night temporary VC")

            # Discord supports text chat inside voice channels; send the control panel there.
            try:
                await channel.send(embed=make_temp_vc_embed(channel), view=TempVCControlView())
            except (discord.Forbidden, discord.HTTPException):
                pass
        except discord.HTTPException as exc:
            print(f"[TEMP VC] Create error: {exc!r}")

    # Delete empty temporary rooms.
    if before.channel and before.channel.id in TEMP_VCS and len(before.channel.members) == 0:
        channel_id = before.channel.id
        TEMP_VCS.pop(channel_id, None)
        TEMP_VC_META.pop(channel_id, None)
        try:
            await before.channel.delete(reason="Dark Night temporary VC became empty")
        except discord.HTTPException:
            pass


# ==========================================
# 🔊 TEMPORARY VC CONTROL CENTER
# ==========================================
def get_temp_vc_meta(channel):
    return TEMP_VC_META.get(getattr(channel, "id", 0))

def can_manage_temp_vc(interaction, channel):
    meta = get_temp_vc_meta(channel)
    if not meta:
        return False
    return (
        interaction.user.id == OWNER_ID
        or interaction.user.guild_permissions.administrator
        or interaction.user.id == meta.get("owner")
    )

def make_temp_vc_embed(channel):
    meta = get_temp_vc_meta(channel) or {}
    owner_id = meta.get("owner", 0)
    owner = channel.guild.get_member(owner_id) if channel.guild else None
    locked = meta.get("locked", False)
    limit = meta.get("limit", 0)
    embed = discord.Embed(
        title="🔊 Dark Night • Private Room Control",
        description=(
            f"**Room:** {channel.mention}\n"
            f"**Owner:** {owner.mention if owner else f'<@{owner_id}>'}\n"
            f"**Status:** {'🔒 Locked' if locked else '🔓 Open'}\n"
            f"**Limit:** {'Unlimited' if not limit else str(limit)}\n\n"
            "Use the buttons below to manage your room.\n"
            "👑 Room owner + server Owner/Admin can control it."
        ),
        color=EMBED_COLOR,
    )
    embed.set_thumbnail(url=COMMUNITY_IMAGE_URL)
    return embed

class VCLimitModal(Modal):
    def __init__(self, channel):
        self.channel_id = channel.id
        super().__init__(title="Set Voice Room Limit")
        self.limit = TextInput(label="User limit", placeholder="0 = unlimited, max 99", max_length=2, required=True)
        self.add_item(self.limit)

    async def on_submit(self, interaction: Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.VoiceChannel) or not can_manage_temp_vc(interaction, channel):
            return await interaction.response.send_message("❌ You cannot control this room.", ephemeral=True)
        try:
            limit = int(self.limit.value)
        except ValueError:
            return await interaction.response.send_message("❌ Enter a number from `0` to `99`.", ephemeral=True)
        if not 0 <= limit <= 99:
            return await interaction.response.send_message("❌ Enter a number from `0` to `99`.", ephemeral=True)
        await channel.edit(user_limit=limit, reason=f"Temp VC limit changed by {interaction.user}")
        TEMP_VC_META[channel.id]["limit"] = limit
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=TempVCControlView())

class VCRenameModal(Modal):
    def __init__(self, channel):
        self.channel_id = channel.id
        super().__init__(title="Rename Voice Room")
        self.name = TextInput(label="Room name", placeholder="My Private Room", min_length=1, max_length=90, required=True)
        self.add_item(self.name)

    async def on_submit(self, interaction: Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.VoiceChannel) or not can_manage_temp_vc(interaction, channel):
            return await interaction.response.send_message("❌ You cannot control this room.", ephemeral=True)
        await channel.edit(name=self.name.value, reason=f"Temp VC renamed by {interaction.user}")
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=TempVCControlView())

class VCKickModal(Modal):
    def __init__(self, channel):
        self.channel_id = channel.id
        super().__init__(title="Remove Member From Room")
        self.member_id = TextInput(label="Member ID", placeholder="Discord user ID", max_length=25, required=True)
        self.add_item(self.member_id)

    async def on_submit(self, interaction: Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.VoiceChannel) or not can_manage_temp_vc(interaction, channel):
            return await interaction.response.send_message("❌ You cannot control this room.", ephemeral=True)
        try:
            uid = int(self.member_id.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid Discord user ID.", ephemeral=True)
        member = interaction.guild.get_member(uid)
        if not member or member.voice is None or member.voice.channel != channel:
            return await interaction.response.send_message("❌ That member is not in this room.", ephemeral=True)
        meta = get_temp_vc_meta(channel) or {}
        if uid == meta.get("owner") and uid != interaction.user.id and interaction.user.id != OWNER_ID and not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ The room owner cannot be removed by another member.", ephemeral=True)
        await member.move_to(None, reason=f"Removed from temp VC by {interaction.user}")
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=TempVCControlView())

class VCMoveModal(Modal):
    def __init__(self, channel):
        self.channel_id = channel.id
        super().__init__(title="Move Member Into Room")
        self.member_id = TextInput(label="Member ID", placeholder="Discord user ID", max_length=25, required=True)
        self.add_item(self.member_id)

    async def on_submit(self, interaction: Interaction):
        channel = interaction.guild.get_channel(self.channel_id)
        if not isinstance(channel, discord.VoiceChannel) or not can_manage_temp_vc(interaction, channel):
            return await interaction.response.send_message("❌ You cannot control this room.", ephemeral=True)
        try:
            uid = int(self.member_id.value.strip())
        except ValueError:
            return await interaction.response.send_message("❌ Invalid Discord user ID.", ephemeral=True)
        member = interaction.guild.get_member(uid)
        if not member:
            return await interaction.response.send_message("❌ Member not found.", ephemeral=True)
        limit = get_temp_vc_meta(channel).get("limit", 0)
        if limit and len(channel.members) >= limit and member.voice and member.voice.channel != channel:
            return await interaction.response.send_message("❌ This room is full.", ephemeral=True)
        await member.move_to(channel, reason=f"Moved into temp VC by {interaction.user}")
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=TempVCControlView())

class TempVCControlView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _check(self, interaction):
        channel = interaction.channel
        if not isinstance(channel, discord.VoiceChannel) or channel.id not in TEMP_VC_META:
            await interaction.response.send_message("❌ This is not an active Dark Night temporary room.", ephemeral=True)
            return None
        if not can_manage_temp_vc(interaction, channel):
            await interaction.response.send_message("❌ Only the room owner or a server Owner/Admin can control this room.", ephemeral=True)
            return None
        return channel

    @discord.ui.button(label="Lock", emoji="🔒", style=ButtonStyle.secondary, custom_id="tempvc_lock")
    async def lock(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if not channel: return
        meta = TEMP_VC_META[channel.id]
        meta["locked"] = True
        everyone = channel.guild.default_role
        owner = channel.guild.get_member(meta["owner"])
        await channel.set_permissions(everyone, connect=False, reason=f"Temp VC locked by {interaction.user}")
        if owner:
            await channel.set_permissions(owner, connect=True, reason="Keep room owner connected")
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=self)

    @discord.ui.button(label="Unlock", emoji="🔓", style=ButtonStyle.success, custom_id="tempvc_unlock")
    async def unlock(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if not channel: return
        TEMP_VC_META[channel.id]["locked"] = False
        await channel.set_permissions(channel.guild.default_role, connect=None, reason=f"Temp VC unlocked by {interaction.user}")
        await interaction.response.edit_message(embed=make_temp_vc_embed(channel), view=self)

    @discord.ui.button(label="Limit", emoji="👥", style=ButtonStyle.primary, custom_id="tempvc_limit")
    async def limit(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if channel: await interaction.response.send_modal(VCLimitModal(channel))

    @discord.ui.button(label="Rename", emoji="✏️", style=ButtonStyle.primary, custom_id="tempvc_rename")
    async def rename(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if channel: await interaction.response.send_modal(VCRenameModal(channel))

    @discord.ui.button(label="Kick", emoji="👢", style=ButtonStyle.danger, custom_id="tempvc_kick")
    async def kick(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if channel: await interaction.response.send_modal(VCKickModal(channel))

    @discord.ui.button(label="Move", emoji="↪️", style=ButtonStyle.secondary, custom_id="tempvc_move")
    async def move(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if channel: await interaction.response.send_modal(VCMoveModal(channel))

    @discord.ui.button(label="Close Room", emoji="🗑️", style=ButtonStyle.danger, custom_id="tempvc_close")
    async def close(self, interaction: Interaction, button: Button):
        channel = await self._check(interaction)
        if not channel: return
        channel_id = channel.id
        TEMP_VCS.pop(channel_id, None)
        TEMP_VC_META.pop(channel_id, None)
        await channel.delete(reason=f"Temp VC closed by {interaction.user}")
        await interaction.response.send_message("🗑️ Temporary room closed.", ephemeral=True)

# ==========================================
# 🔊 VOICE ACTIVITY LOGS
# ==========================================
@bot.listen("on_voice_state_update")
async def audit_voice_activity(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Ignore pure mute/deaf changes from the general room spam unless a channel changed.
    if before.channel == after.channel:
        return

    if before.channel is None and after.channel is not None:
        title = "Voice Joined"
        emoji = "📥"
        details = [("➡️ Joined", _channel_text(after.channel), False)]
    elif before.channel is not None and after.channel is None:
        title = "Voice Left"
        emoji = "📤"
        details = [("⬅️ Left", _channel_text(before.channel), False)]
    else:
        title = "Voice Moved"
        emoji = "🔀"
        details = [("⬅️ From", _channel_text(before.channel), True), ("➡️ To", _channel_text(after.channel), True)]

    await send_audit_log(
        member.guild,
        title=title,
        emoji=emoji,
        actor=member,
        target=member,
        channel=after.channel or before.channel,
        extra_fields=details,
    )



# ==========================================
# 🎫 GENERAL TICKET SYSTEM
# ==========================================

GENERAL_TICKET_CATEGORY_ID = 1544813019995836549

GENERAL_TICKET_BANNER_URL = (
    "https://cdn.discordapp.com/attachments/"
    "1544405375632015552/1545127507710181417/"
    "banner_octopus_studio.png"
    "?ex=6a9b03a0&is=6a99b220&hm="
    "40575cc971757ea2136d07056b149af25fc0b7661f98642781f2c3b0d6c61efd&"
)

TICKET_TYPES = {
    "pub": {
        "label": "Pub",
        "emoji": "📢",
        "prefix": "pubticket",
        "description": "Open a ticket to report a spam!",
    },
    "bugs": {
        "label": "Bugs",
        "emoji": "🐛",
        "prefix": "bugticket",
        "description": "Open a ticket to report bugs!",
    },
    "abuse": {
        "label": "Abuse",
        "emoji": "⚠️",
        "prefix": "abuseticket",
        "description": "Open a ticket to report abuse!",
    },
    "server": {
        "label": "Server",
        "emoji": "🛠️",
        "prefix": "serverticket",
        "description": "Open a ticket for server-related issues!",
    },
    "staff_abuse": {
        "label": "Staff Abuse",
        "emoji": "🚨",
        "prefix": "staffabuseticket",
        "description": "Open a ticket to report staff abuse!",
    },
}


def _ticket_channel_name(ticket_type: str, user: discord.Member) -> str:
    config = TICKET_TYPES[ticket_type]

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "",
        user.name,
    ).lower()[:70]

    if not safe_name:
        safe_name = str(user.id)

    return f"{config['prefix']}-{safe_name}"


def _find_user_ticket(
    category: discord.CategoryChannel,
    user_id: int,
    ticket_type: str,
):
    marker = f"moon-night-ticket:{ticket_type}:{user_id}"

    for channel in category.text_channels:
        if channel.topic and marker in channel.topic:
            return channel

    return None


def get_general_ticket_embed():
    embed = discord.Embed(
        title="🎟️ | Need help? Open a Ticket!",
        description=(
            "• **Pub** ⇝ Open a ticket to report a spam!\n\n"
            "• **Bugs** ⇝ Open a ticket to report bugs!\n\n"
            "• **Abuse** ⇝ Open a ticket to report abuse!\n\n"
            "• **Server** ⇝ Open a ticket for server-related issues!\n\n"
            "• **Staff Abuse** ⇝ Open a ticket to report staff abuse!"
        ),
        color=0x5865F2,
    )
    embed.set_image(url=GENERAL_TICKET_BANNER_URL)
    embed.set_footer(
        text="© 2026 Moon Night™. We are here to help you!"
    )
    return embed


def _ticket_overwrites(
    guild: discord.Guild,
    user: discord.Member,
):
    return {
        guild.default_role: discord.PermissionOverwrite(
            view_channel=False,
        ),
        user: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
            embed_links=True,
        ),
    }


class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Close Ticket",
        emoji="🔒",
        style=ButtonStyle.danger,
        custom_id="moon_ticket_close",
    )
    async def close_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        channel = interaction.channel

        if not isinstance(channel, discord.TextChannel):
            return await interaction.response.send_message(
                "❌ This is not a ticket channel.",
                ephemeral=True,
            )

        if not channel.topic or not channel.topic.startswith(
            "moon-night-ticket:"
        ):
            return await interaction.response.send_message(
                "❌ This channel is not managed by the ticket system.",
                ephemeral=True,
            )

        parts = channel.topic.split(":")

        try:
            owner_id = int(parts[-1])
        except (ValueError, IndexError):
            owner_id = 0

        allowed = (
            interaction.user.id == owner_id
            or interaction.user.id == OWNER_ID
            or interaction.user.guild_permissions.administrator
            or interaction.user.guild_permissions.manage_channels
        )

        if not allowed:
            return await interaction.response.send_message(
                "❌ Only the ticket owner or server staff can close this ticket.",
                ephemeral=True,
            )

        await interaction.response.send_message(
            "🔒 Closing this ticket in **5 seconds**..."
        )

        await asyncio.sleep(5)

        try:
            await channel.delete(
                reason=(
                    f"Moon Night ticket closed by "
                    f"{interaction.user} ({interaction.user.id})"
                )
            )
        except (
            discord.NotFound,
            discord.Forbidden,
            discord.HTTPException,
        ):
            pass


class TicketPanelView(View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _open_ticket(
        self,
        interaction: Interaction,
        ticket_type: str,
    ):
        guild = interaction.guild

        if guild is None:
            return await interaction.response.send_message(
                "❌ This ticket system can only be used inside a server.",
                ephemeral=True,
            )

        config = TICKET_TYPES[ticket_type]

        category = guild.get_channel(
            GENERAL_TICKET_CATEGORY_ID
        )

        if not isinstance(category, discord.CategoryChannel):
            return await interaction.response.send_message(
                (
                    "❌ Ticket category was not found.\n"
                    f"Category ID: `{GENERAL_TICKET_CATEGORY_ID}`"
                ),
                ephemeral=True,
            )

        existing = _find_user_ticket(
            category,
            interaction.user.id,
            ticket_type,
        )

        if existing:
            return await interaction.response.send_message(
                (
                    f"⚠️ You already have a **{config['label']}** ticket open: "
                    f"{existing.mention}"
                ),
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        channel_name = _ticket_channel_name(
            ticket_type,
            interaction.user,
        )

        marker = (
            f"moon-night-ticket:"
            f"{ticket_type}:"
            f"{interaction.user.id}"
        )

        try:
            ticket_channel = await guild.create_text_channel(
                name=channel_name,
                category=category,
                topic=marker,
                overwrites=_ticket_overwrites(
                    guild,
                    interaction.user,
                ),
                reason=(
                    f"Moon Night {config['label']} ticket "
                    f"opened by {interaction.user} "
                    f"({interaction.user.id})"
                ),
            )

            ticket_embed = discord.Embed(
                title=(
                    f"{config['emoji']} | "
                    f"{config['label']} Ticket"
                ),
                description=(
                    f"Hello {interaction.user.mention}! 👋\n\n"
                    f"Welcome to your **{config['label']}** ticket.\n\n"
                    f"**Reason:** {config['description']}\n\n"
                    "Please explain your issue clearly and provide "
                    "screenshots/proof when useful.\n\n"
                    "A staff member will help you as soon as possible."
                ),
                color=0x5865F2,
                timestamp=datetime.now(timezone.utc),
            )

            ticket_embed.set_thumbnail(
                url=interaction.user.display_avatar.url
            )

            ticket_embed.set_footer(
                text="Moon Night Support • Ticket System"
            )

            await ticket_channel.send(
                content=interaction.user.mention,
                embed=ticket_embed,
                view=TicketCloseView(),
                allowed_mentions=discord.AllowedMentions(
                    users=[interaction.user]
                ),
            )

            await interaction.followup.send(
                (
                    f"✅ Your **{config['label']}** ticket has been created: "
                    f"{ticket_channel.mention}"
                ),
                ephemeral=True,
            )

            try:
                await send_audit_log(
                    guild,
                    title="🎫 Ticket Opened",
                    actor=interaction.user,
                    target=interaction.user,
                    channel=ticket_channel,
                    extra_fields=[
                        ("🎟️ Type", config["label"], True),
                        ("🔑 Channel", ticket_channel.mention, True),
                    ],
                )
            except Exception as exc:
                print(
                    f"[TICKET] Audit log failed: {exc!r}"
                )

        except discord.Forbidden:
            await interaction.followup.send(
                (
                    "❌ I cannot create the ticket channel. "
                    "Give the bot **Manage Channels** permission."
                ),
                ephemeral=True,
            )

        except discord.HTTPException as exc:
            print(
                f"[TICKET] Create channel error: {exc!r}"
            )
            await interaction.followup.send(
                "❌ Discord returned an error while creating the ticket.",
                ephemeral=True,
            )

    @discord.ui.button(
        label="Pub",
        emoji="📢",
        style=ButtonStyle.secondary,
        custom_id="moon_ticket_pub",
    )
    async def pub_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await self._open_ticket(interaction, "pub")

    @discord.ui.button(
        label="Bugs",
        emoji="🐛",
        style=ButtonStyle.secondary,
        custom_id="moon_ticket_bugs",
    )
    async def bugs_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await self._open_ticket(interaction, "bugs")

    @discord.ui.button(
        label="Abuse",
        emoji="⚠️",
        style=ButtonStyle.secondary,
        custom_id="moon_ticket_abuse",
    )
    async def abuse_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await self._open_ticket(interaction, "abuse")

    @discord.ui.button(
        label="Server",
        emoji="🛠️",
        style=ButtonStyle.secondary,
        custom_id="moon_ticket_server",
    )
    async def server_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await self._open_ticket(interaction, "server")

    @discord.ui.button(
        label="Staff Abuse",
        emoji="🚨",
        style=ButtonStyle.secondary,
        custom_id="moon_ticket_staff_abuse",
    )
    async def staff_abuse_ticket(
        self,
        interaction: Interaction,
        button: Button,
    ):
        await self._open_ticket(interaction, "staff_abuse")



# ==========================================
# MASTER SLASH COMMAND TO SEND PANELS
# ==========================================
@bot.tree.command(name="send_panel", description="Send Dark Night embeds (Owner Only)")
@app_commands.choices(panel=[
    app_commands.Choice(name="Socials", value="socials"),
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Rules", value="rules"),
    app_commands.Choice(name="Guild Map / Server Map", value="map"),
    app_commands.Choice(name="Apply Staff Team", value="apply"),
    app_commands.Choice(name="Booster Perks Roles", value="boosters"),
    app_commands.Choice(name="Self Roles", value="selfroles"),
    app_commands.Choice(name="Role Request Panel", value="rolerequest"),
    app_commands.Choice(name="Tweets System", value="tweets"),
    app_commands.Choice(name="Games Center", value="games"),
    app_commands.Choice(name="General Ticket", value="general_ticket"),
    app_commands.Choice(name="Voice Room Panel", value="voice_panel")
])
@is_owner_or_admin()
async def send_panel(interaction: Interaction, panel: str):
    await interaction.response.defer(ephemeral=True)

    if panel == "socials":
        await interaction.channel.send(embed=get_socials_embed(), view=SocialsView())
    elif panel == "stats":
        await interaction.channel.send(embed=get_stats_embed(interaction.guild), view=StatsView(interaction.guild))
    elif panel == "rules":
        await interaction.channel.send(embed=get_rules_embed(), view=RulesView())
    elif panel == "map":
        await interaction.channel.send(embed=get_map_embed())
    elif panel == "apply":
        await interaction.channel.send(embed=get_apply_embed(), view=ApplyView())
    elif panel == "boosters":
        await interaction.channel.send(embed=get_booster_embed(), view=BoosterRolesView())
    elif panel == "selfroles":
        panels = get_self_roles_data()
        for embed_obj, view_obj in panels:
            await interaction.channel.send(embed=embed_obj, view=view_obj)
    elif panel == "rolerequest":
        await interaction.channel.send(embed=get_role_request_embed(), view=RoleRequestView())
    elif panel == "tweets":
        await interaction.channel.send(embed=get_tweet_panel_embed(), view=TweetPanelView())
    elif panel == "voice_panel":
        target = interaction.guild.get_channel(VOICE_PANEL_CHANNEL_ID)
        if not isinstance(target, (discord.TextChannel, discord.Thread)):
            return await interaction.followup.send(f"❌ Panel channel `{VOICE_PANEL_CHANNEL_ID}` was not found or is not a normal text channel.", ephemeral=True)
        await target.send(embed=get_voice_panel_embed(), view=VoicePanelView())
    elif panel == "general_ticket":
        await interaction.channel.send(
            embed=get_general_ticket_embed(),
            view=TicketPanelView(),
        )
    elif panel == "games":
        await interaction.channel.send(embed=get_games_center_embed(), view=GamesCenterView())

    await interaction.followup.send(f"✅ Embed **{panel}** sent successfully!", ephemeral=True)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        update_peak_members(guild)
        await refresh_invite_cache(guild)
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

print(f"[VOICE DEPENDENCIES] PyNaCl={PYNACL_OK} | davey={DAVEY_OK} | NativeOpus={OPUS_OK}")
if not OPUS_OK:
    print("[VOICE] Native libopus is unavailable. Music playback will be disabled until libopus is installed.")
else:
    print("[VOICE] Native Opus is available; FFmpeg PCM playback is enabled.")

bot.run(BOT_TOKEN)
