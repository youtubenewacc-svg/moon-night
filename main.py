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
OWNER_ID = int(os.getenv("OWNER_ID", "1241496820455313533" ,"1248748048457269302",))          # 👑 Bot owner ID
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1544405575314440342"))  # 📝 Role-request log channel
JAIL_ROLE_ID = int(os.getenv("JAIL_ROLE_ID", "0"))                  # ⛓️ Jail role
PROTECTED_ROLE_ID = int(os.getenv("PROTECTED_ROLE_ID", "0"))        # 🛡️ Protected role (optional)
WELCOME_CHANNEL_ID = int(os.getenv("WELCOME_CHANNEL_ID", "0"))      # 👋 Welcome channel; 0 = off
LEAVE_CHANNEL_ID = int(os.getenv("LEAVE_CHANNEL_ID", "0"))          # 💔 Leave channel; 0 = off
TEMP_VC_CHANNEL_ID = int(os.getenv("TEMP_VC_CHANNEL_ID", "1544406112097411072")) # 🔊 Temp VC creator

# 📌 CHANNEL IDs — change the numbers only
CHANNEL_IDS = {
    "news": 1482902413554745638,        # 📰 News
    "rules": 1482902414997852381,       # 📜 Rules
    "self_roles": 1482902461168615465,  # 🎭 Self roles
    "apply": 1482902427064864833,       # 🧑‍💼 Apply/team
    "general": 1482902490549850184,     # 💬 General
    "commands": 1482902491711541328,    # 🤖 Bot commands
    "temp_voice": 1482902422065123338,  # 🔊 Temporary VC
    "ticket": 1482902524376780932,      # 🎫 Ticket/help
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
    "ticket": "🎫",
}

# 🖼️ IMAGES / LOGOS / BANNERS
# Socials keeps its small thumbnail. Other main panels use panel_banner as a BIG image.
IMAGES = {
    "moon_logo": "https://i.imgur.com/vHqB5o2.png",
    "panel_banner": "https://cdn.discordapp.com/attachments/1544405356258656347/1544728175827755178/octopus_png_banner.png?ex=6a998fb8&is=6a983e38&hm=f2ae9b2b880882e0aca775e5321f1f5b0048aa287a85585a7699e4156e46a5ed&",
    "role_request": "https://i.imgur.com/moon_night_banner.png",
}

# 🔗 LINKS — change these when your socials/ticket links change
LINKS = {
    "instagram": "https://instagram.com",
    "tiktok": "https://tiktok.com",
    "ig_group": "https://instagram.com",
    "store": "https://store.moonnight.com",
    "need_help": "https://discord.com",
    "ticket": f"https://discord.com/channels/{CHANNEL_IDS['ticket']}",
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

def get_xp(guild_id, user_id):
    key = user_key(guild_id, user_id)
    DATA["xp"].setdefault(key, {"xp": 0, "level": 0})
    return DATA["xp"][key]

def level_for_xp(xp):
    return int((xp / 100) ** 0.5)

def xp_for_next_level(level):
    return (level + 1) ** 2 * 100

class MoonNightBot(commands.Bot):
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
        
        await self.tree.sync()
        print("Slash Commands Synced & Persistent Views Registered Successfully!")

bot = MoonNightBot()

def is_owner_or_admin():
    async def predicate(interaction: Interaction):
        if interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Had l-command khas b Owners/Admins ghir!", ephemeral=True)
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
            f"### * {EMOJIS['store']} **Store :** *** Shop exclusive Moon Night items. ***\n\n"
            f"-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑩𝒆𝒎𝒐𝒓𝒊𝒆𝒔 {EMOJIS['moon']}"
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=IMAGES["moon_logo"])
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
        title="Moon Night Statistics",
        description=(
            f"- {EMOJIS['members']} **Total Members:** `{total_members}` ⁘\n"
            f"- {EMOJIS['voice']} **Active in Voice:** `{voice_count}` ⁘\n"
            f"- {EMOJIS['premium']} **Boosters:** `{boosters_count}` ⁘\n\n"
            "Stay active, and enjoy your time in Moon Night"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["panel_banner"])
    embed.set_footer(text="Stay Active, And Enjoy Your Time in @Moon Night")
    return embed


# ==========================================
# 3. RULES PANEL
# ==========================================
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Join Need Help!", style=ButtonStyle.link, url=LINKS["need_help"]))
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url=LINKS["ticket"]))

def get_rules_embed():
    embed = discord.Embed(
        description=(
            "> 𝗧𝗼 𝗺𝗮𝗸𝗲 𝗦𝘂𝗿𝗲 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝗲𝗻𝗷𝗼𝘆, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗼𝘀𝗲 𝗴𝘂𝗶𝗱𝗲𝗹𝗶𝗻𝗲𝘀 :\n\n"
            f"{EMOJIS['rules_star']} **⇝ Follow the [Discord TOS](https://discord.com/terms) and The [Discord Community Guidlines](https://discord.com/guidelines)**\n"
            f"{EMOJIS['rules_star']} **⇝ __Aya NSFW content f server = jail__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Respect aya member f server, kifma kan!__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Abusing any power treportat biha b preuve = warn ⇝ remove role__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Need help daret bach it7alo lmachakil, machi bach trolli, troll f nh = blacklist n.h.__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Sbek chi wahd 3ndo role (staff, high role, admin...) matseboch, tla3 need help reporti bih, ghadi itremova lih role__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Staff provoque 3liha punishment. pd: 3essas 9damet, jib chi haja jdida__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Bghiti trolli, tseb, tla9 sb's, dir one tap dialek, ou lockiha (.v lock) ou hara mat3ich, room opened = respect the rules!__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Abusa 3lik chi wahed 3ndo role (staff, high role, admin...) tla3 n.h. wla 7el ticket hna : {channel_mention('ticket')} ou ghadi itremova lih role__**\n"
            f"{EMOJIS['rules_star']} **⇝ __Pub ou pub vc 3liha jail, chi wahd spammak, wla dar pub vc, tla3 need help ou report it (don't forget screen / record)__**\n\n"
            "**⇾ __Have questions or issues? Our team is ready to help you!__**\n"
            "**⇾ __Questions, problems, or requests? Open a ticket now!__**\n\n"
            "-# `© 2026 Moon Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    embed.set_author(name="⠀" * 15 + "・Moon Night : Rules・" + "⠀" * 15)
    embed.set_image(url=IMAGES["panel_banner"])
    return embed


# ==========================================
# 4. GUIDMAP / SERVER MAP PANEL
# ==========================================
def get_map_embed():
    embed = discord.Embed(
        title=f"{EMOJIS['welcome']} ◜__Welcome To Moon Night!__◞",
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
            "-# `© 2026 Moon Night. All rights reserved.`"
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
        title="## __Staff Apply For Moon    Night    ©__",
        description=(
            "-# Moon    Night    ©'s now is accepting staff applications! Be a part of our family! We would love to bring new people to our team that would help grow this family together!\n\n"
            "### - __Staff__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "### - __Game Mods__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "-# Copyright © 2026 Lisa X Moon    Night    ©"
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
            ("Moon night 's", ROLE_IDS["booster_moon"]),
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
            "-# © 2026 Moon Night    #ɓαɕƘ's Lisa. All rights reserved."
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
        await interaction.user.remove_roles(role)
        await interaction.response.send_message(f"➖ Removed **{role.name}**!", ephemeral=True)
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message(f"➕ Added **{role.name}**!", ephemeral=True)

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
            "-# © 2026 Moon Night. All rights reserved."
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
            "-# © 2026 Moon Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )

    e3 = discord.Embed(
        title="🎮 ⋮ __Games Roles__ ⊹",
        description=(
            "> ## __Do you play any games?__\n\n"
            "-# © 2026 Moon Night™. All rights reserved."
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

        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
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
            log_embed.set_footer(text="Moon Night Logging System", icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await log_channel.send(embed=log_embed)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleRequestSelect())

def get_role_request_embed():
    embed = discord.Embed(
        title="◜__Moon Night's Role Request Panel__◞",
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
            "-# **`© 2026 Moon Night™. All rights reserved.`**"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url=IMAGES["role_request"])
    return embed



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

    embed.set_footer(text="Moon Night • Server Information")
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="invite", description="Get the bot's invite link")
async def invite(interaction: Interaction):
    invite_url = discord.utils.oauth_url(
        bot.user.id,
        permissions=discord.Permissions(administrator=True),
        scopes=("bot", "applications.commands")
    )

    embed = discord.Embed(
        title="🤖 Invite Moon Night Bot",
        description="Use the button below to invite Moon Night Bot to another server.",
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
        title="🎵 Added to Moon Night Music",
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
        title="🎵 Moon Night • Music Queue",
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
        ("/coinflip", "Flip a virtual coin."),
        ("/dice", "Roll a virtual die."),
        ("/rps", "Play Rock Paper Scissors."),
        ("/8ball", "Ask the Magic 8-Ball."),
        ("/roulette", "Virtual roulette using Moon Coins."),
        ("/slots", "Virtual slot machine."),
        ("/blackjack", "Virtual blackjack."),
        ("/mafia", "Create, join, leave, start or view Mafia.")
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
    "🎫 Community": [
        ("/ticket", "Create a private support ticket."),
        ("/poll", "Create a reaction poll."),
        ("/suggest", "Submit a server suggestion."),
        ("/announce", "Post a formatted announcement."),
        ("/userinfo", "Show member information."),
        ("/avatar", "Show a member avatar."),
        ("/roleinfo", "Show role information."),
        ("/serverinfo", "Show server information.")
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
    "🌙 Server": [
        ("/about", "Show server statistics."),
        ("/invite", "Get the bot invite link."),
        ("/send_panel", "Send Moon Night panels.")
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
            title=f"🌙 Moon Night • {category}",
            description=(
                "```ansi\nMoon Night Community Command Center\n```\n"
                + lines
                + "\n\n-# Select another category below to explore more."
            ),
            color=EMBED_COLOR
        )
        embed.set_footer(text="Moon Night • Help Center")
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=300)
        self.add_item(HelpCategorySelect())

@bot.tree.command(name="help", description="Open the Moon Night command center")
async def help_command(interaction: Interaction):
    embed = discord.Embed(
        title="🌙 Moon Night • Command Center",
        description=(
            "Welcome to the **Moon Night Help Center**.\n\n"
            "Choose a category below and you'll get every command with a clean description.\n\n"
            "✨ Moderation commands are Staff/Admin restricted."
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url=IMAGES["moon_logo"])
    embed.set_footer(text="Moon Night • Help Center")
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
    embed = discord.Embed(title=f"📢 {title}", description=message, color=EMBED_COLOR)
    embed.set_footer(text=f"Moon Night • {interaction.user}")
    await interaction.response.send_message(embed=embed)

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
# 13. TICKETS
# ==========================================
class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Close Ticket", style=ButtonStyle.danger, custom_id="moon_ticket_close")
    async def close_ticket(self, interaction: Interaction, button: Button):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ Staff only.", ephemeral=True)
        await interaction.response.send_message("🔒 Closing ticket...", ephemeral=True)
        await asyncio.sleep(2)
        await interaction.channel.delete(reason=f"Ticket closed by {interaction.user}")

@bot.tree.command(name="ticket", description="Create a private support ticket")
async def ticket(interaction: Interaction):
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name=f"{EMOJIS['ticket']} TICKETS")
    if category is None:
        category = await guild.create_category(f"{EMOJIS['ticket']} TICKETS")

    name = f"ticket-{interaction.user.id}"
    if discord.utils.get(guild.text_channels, name=name):
        return await interaction.response.send_message("❌ You already have a ticket.", ephemeral=True)

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True)
    }
    channel = await guild.create_text_channel(name, category=category, overwrites=overwrites)
    embed = discord.Embed(
        title="🎫 Moon Night Support",
        description=f"Welcome {interaction.user.mention}!\nExplain your issue here and staff will help you.",
        color=EMBED_COLOR
    )
    await channel.send(content=interaction.user.mention, embed=embed, view=TicketCloseView())
    await interaction.response.send_message(f"🎫 Ticket created: {channel.mention}", ephemeral=True)


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
            title="💰 Moon Night • Economy Leaderboard",
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
        embed=discord.Embed(title="🏆 Moon Night • XP Leaderboard", description="\n".join(lines) if lines else "No XP yet.", color=EMBED_COLOR)
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
    await interaction.response.send_message(f"✊ You: **{choice}**\n🤖 Moon Night: **{bot_choice}**\n\n{result}")

@bot.tree.command(name="8ball", description="Ask the Magic 8-Ball")
async def eightball(interaction: Interaction, question: str):
    await interaction.response.send_message(
        f"🔮 **{question}**\n\n**Answer:** {random.choice(['Yes. 🌙','No. 💀','Absolutely. ✨','Ask later. 🔮','Very likely. ⭐','Unlikely. 🌑'])}"
    )

@bot.tree.command(name="roulette", description="Virtual roulette using Moon Coins")
async def roulette(interaction: Interaction, amount: app_commands.Range[int, 1, 100000], color: str):
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
async def slots(interaction: Interaction, amount: app_commands.Range[int, 1, 100000]):
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
async def blackjack(interaction: Interaction, amount: app_commands.Range[int, 1, 100000]):
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
            await user.send(f"🔪 **Moon Night Mafia**\nYour secret role: **{role}**")
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
        title="🎁 MOON NIGHT GIVEAWAY",
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
            title="🌙 Welcome To Moon Night!",
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
                await channel.send(f"💔 **{member}** left Moon Night. We hope to see you again!")
            except discord.HTTPException:
                pass

@bot.listen("on_voice_state_update")
async def temporary_voice_listener(member, before, after):
    if TEMP_VC_CHANNEL_ID and after.channel and after.channel.id == TEMP_VC_CHANNEL_ID:
        try:
            channel = await member.guild.create_voice_channel(
                name=f"🔊 {member.display_name}'s Room",
                category=after.channel.category,
                reason="Moon Night temporary VC"
            )
            TEMP_VCS[channel.id] = member.id
            await member.move_to(channel)
        except discord.HTTPException:
            pass
    if before.channel and before.channel.id in TEMP_VCS and len(before.channel.members) == 0:
        TEMP_VCS.pop(before.channel.id, None)
        try:
            await before.channel.delete(reason="Empty temporary VC")
        except discord.HTTPException:
            pass


# ==========================================
# MASTER SLASH COMMAND TO SEND PANELS
# ==========================================
@bot.tree.command(name="send_panel", description="Send Moon Night embeds (Owner Only)")
@app_commands.choices(panel=[
    app_commands.Choice(name="Socials", value="socials"),
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Rules", value="rules"),
    app_commands.Choice(name="Guidmap / Server Map", value="map"),
    app_commands.Choice(name="Apply Staff Team", value="apply"),
    app_commands.Choice(name="Booster Perks Roles", value="boosters"),
    app_commands.Choice(name="Self Roles", value="selfroles"),
    app_commands.Choice(name="Role Request Panel", value="rolerequest")
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

    await interaction.followup.send(f"✅ Embed **{panel}** sent successfully!", ephemeral=True)


@bot.event
async def on_ready():
    for guild in bot.guilds:
        update_peak_members(guild)
    print(f"Logged in as {bot.user.name} ({bot.user.id})")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")

print(f"[VOICE DEPENDENCIES] PyNaCl={PYNACL_OK} | davey={DAVEY_OK} | NativeOpus={OPUS_OK}")
if not OPUS_OK:
    print("[VOICE] Native libopus is unavailable. Music playback will be disabled until libopus is installed.")
else:
    print("[VOICE] Native Opus is available; FFmpeg PCM playback is enabled.")

bot.run(BOT_TOKEN)
