import os
import time
import re
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput

# ==========================================
# CONFIGURATION & SETTINGS (Using Environment Variables)
# ==========================================
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1241496820455313533"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1544405575314440342"))
JAIL_ROLE_ID = int(os.getenv("JAIL_ROLE_ID", "0"))  # Put your Jail role ID here / in env

# Color Palette (Dark Theme / Night Blue Aesthetic)
EMBED_COLOR = 0x2b2d31

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


# ==========================================
# MODERATION / SERVER INFO HELPERS
# ==========================================
PROTECTED_USERS = set()
SERVER_PEAK_MEMBERS = {}

DURATION_RE = re.compile(r"^\s*(\d+)\s*(s|sec|secs|second|seconds|m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days)\s*$", re.IGNORECASE)

def parse_duration(duration: str):
    """Accepts values such as 60s, 1m, 6h, 1d."""
    match = DURATION_RE.match(duration)
    if not match:
        return None

    amount = int(match.group(1))
    unit = match.group(2).lower()

    if amount <= 0:
        return None

    if unit in {"s", "sec", "secs", "second", "seconds"}:
        seconds = amount
    elif unit in {"m", "min", "mins", "minute", "minutes"}:
        seconds = amount * 60
    elif unit in {"h", "hr", "hrs", "hour", "hours"}:
        seconds = amount * 60 * 60
    else:
        seconds = amount * 24 * 60 * 60

    # Discord timeout maximum is 28 days.
    if seconds > 28 * 24 * 60 * 60:
        return None

    return seconds

def format_duration(seconds: int) -> str:
    if seconds % 86400 == 0:
        return f"{seconds // 86400}d"
    if seconds % 3600 == 0:
        return f"{seconds // 3600}h"
    if seconds % 60 == 0:
        return f"{seconds // 60}m"
    return f"{seconds}s"

def get_jail_role(guild: discord.Guild):
    if not guild or not JAIL_ROLE_ID:
        return None
    return guild.get_role(JAIL_ROLE_ID)

def update_peak_members(guild: discord.Guild):
    if not guild:
        return
    current = guild.member_count or len(guild.members)
    SERVER_PEAK_MEMBERS[guild.id] = max(SERVER_PEAK_MEMBERS.get(guild.id, 0), current)

def is_protected(member: discord.Member) -> bool:
    return member.id == OWNER_ID or member.id in PROTECTED_USERS

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
        self.add_item(Button(label="Instagram", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Tiktok", style=ButtonStyle.link, url="https://tiktok.com"))
        self.add_item(Button(label="IG Group", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Store", style=ButtonStyle.link, url="https://store.moonnight.com"))

def get_socials_embed():
    embed = discord.Embed(
        title="Hey @everyone <:theCall_pink_hi:1509305726655402185>",
        description=(
            "-# > 𝗦𝘁𝗮𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝘄𝗶𝘁𝗵 **𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁** 𝗼𝗻 𝗮𝗹𝗹 𝗼𝘂𝗿 𝗽𝗹𝗮𝘁𝗳𝗼𝗿𝗺𝘀.\n\n"
            "### * <:INSTA:1532413334261993602> **Instagram :** *** Follow us for news & highlights. ***\n"
            "### * <:TIKTOK:1532413262669283451> **TikTok :** ***Follow us for videos & updates***\n"
            "### * <:popcornpandita:1529830303483429025> **IG Group :** *** Stay close to the community. ***\n"
            "### * <:5143storeg:1532413144876585056> **Store :** *** Shop exclusive Moon Night items. ***\n\n"
            "-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑩𝒆𝒎𝒐𝒓𝒊𝒆𝒔 <:bunny_moon:1532388030411833344>"
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url="https://i.imgur.com/vHqB5o2.png")
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
            f"- <:Fams:1451145463511384094> **Total Members:** `{total_members}` ⁘\n"
            f"- <:voice:1451145649801269420> **Active in Voice:** `{voice_count}` ⁘\n"
            f"- <:premium:1451145621246312529> **Boosters:** `{boosters_count}` ⁘\n\n"
            "Stay active, and enjoy your time in Moon Night"
        ),
        color=EMBED_COLOR
    )
    embed.set_thumbnail(url="https://i.imgur.com/vHqB5o2.png")
    embed.set_footer(text="Stay Active, And Enjoy Your Time in @Moon Night")
    return embed


# ==========================================
# 3. RULES PANEL
# ==========================================
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Join Need Help!", style=ButtonStyle.link, url="https://discord.com"))
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))

def get_rules_embed():
    embed = discord.Embed(
        description=(
            "> 𝗧𝗼 𝗺𝗮𝗸𝗲 𝗦𝘂𝗿𝗲 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝗲𝗻𝗷𝗼𝘆, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗼𝘀𝗲 𝗴𝘂𝗶𝗱𝗲𝗹𝗶𝗻𝗲𝘀 :\n\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ Follow the [Discord TOS](https://discord.com/terms) and The [Discord Community Guidlines](https://discord.com/guidelines)**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Aya NSFW content f server = jail__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Respect aya member f server, kifma kan!__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Abusing any power treportat biha b preuve = warn ⇝ remove role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Need help daret bach it7alo lmachakil, machi bach trolli, troll f nh = blacklist n.h.__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Sbek chi wahd 3ndo role (staff, high role, admin...) matseboch, tla3 need help reporti bih, ghadi itremova lih role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Staff provoque 3liha punishment. pd: 3essas 9damet, jib chi haja jdida__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Bghiti trolli, tseb, tla9 sb's, dir one tap dialek, ou lockiha (.v lock) ou hara mat3ich, room opened = respect the rules!__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Abusa 3lik chi wahed 3ndo role (staff, high role, admin...) tla3 n.h. wla 7el ticket hna : <#1482902524376780932> ou ghadi itremova lih role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Pub ou pub vc 3liha jail, chi wahd spammak, wla dar pub vc, tla3 need help ou report it (don't forget screen / record)__**\n\n"
            "**⇾ __Have questions or issues? Our team is ready to help you!__**\n"
            "**⇾ __Questions, problems, or requests? Open a ticket now!__**\n\n"
            "-# `© 2026 Moon Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    embed.set_author(name="⠀" * 15 + "・Moon Night : Rules・" + "⠀" * 15)
    embed.set_image(url="https://i.imgur.com/9O3X3M7.png")
    return embed


# ==========================================
# 4. GUIDMAP / SERVER MAP PANEL
# ==========================================
def get_map_embed():
    embed = discord.Embed(
        title="<a:welcome:1442626577690132663> ◜__Welcome To Moon Night!__◞",
        description=(
            "<a:channelutility:1444868927262822582> **⇝ <#1482902413554745638>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to post the latest news!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902414997852381>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel where are the rules are posted, you must check it!!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902461168615465>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to get your server profile roles!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902427064864833>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to make your way through community work team!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902490549850184>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to chat and having fun with server members!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902491711541328>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to use server bots commands!`\n\n"
            "<a:channelutility:1444868927262822582> **⇝ <#1482902422065123338>**\n"
            "<:arrowblancasincentro:1444869479250002021> `Official channel to create your temporary voice channel!`\n\n"
            "-# `© 2026 Moon Night. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url="https://i.imgur.com/x07X44a.png")
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
    embed.set_image(url="https://i.imgur.com/a4E40k2.png")
    return embed


# ==========================================
# 6. BOOSTERS PERKS / ROLE PANEL
# ==========================================
class BoosterRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

        booster_roles = [
            ("Nickname Perm", 1523714779032584363),
            ("Moon night 's", 1508497154313027675),
            ("Soundboard perm", 1482902118137462896),
            ("Pic Perm", 1482902117693001898),
            ("Link Perm", 1482902116858331217),
            ("Bug hunter", 1482902047236952117),
            ("Very Important people", 1482902046653943870),
            ("Special Member ★", 1482902043558547650)
        ]

        for label, role_id in booster_roles:
            self.add_item(self.create_booster_button(label, role_id))

    def create_booster_button(self, label: str, role_id: int):
        button = Button(label=f"• {label}", style=ButtonStyle.secondary, custom_id=f"booster_{role_id}")
        
        async def button_callback(interaction: Interaction):
            role = interaction.guild.get_role(role_id)
            if not role:
                return await interaction.response.send_message("❌ Role not found on server!", ephemeral=True)
            
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"➖ Removed **{role.name}**!", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"➕ Added **{role.name}**!", ephemeral=True)

        button.callback = button_callback
        return button

def get_booster_embed():
    embed = discord.Embed(
        title="৳ Choose your booster role",
        description=(
            "-# Pick one of the roles down as a thanks for boosting!\n\n"
            "> <@&1523714779032584363>\n"
            "> <@&1508497154313027675>\n"
            "> <@&1482902118137462896>\n"
            "> <@&1482902117693001898>\n"
            "> <@&1482902116858331217>\n"
            "> <@&1482902047236952117>\n"
            "> <@&1482902046653943870>\n"
            "> <@&1482902043558547650>\n\n"
            "-# © 2026 Moon Night    #ɓαɕƘ's Lisa. All rights reserved."
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url="https://i.imgur.com/booster_money.png")
    return embed


# ==========================================
# 7. SELF ROLES PANEL (SITUATIONS, GENDER, GAMES)
# ==========================================
ROLE_IDS = {
    # Situations
    "role_heartless": 1482902155219304549,
    "role_taken": 1482902157324849333,
    "role_single": 1482902156364484661,
    
    # Genders
    "role_female": 1482902134071754832,
    "role_male": 1482902134545580123,
    "role_trans": 1482902135000000000,
    
    # Games
    "role_val": 1482902200000000001,
    "role_ff": 1482902200000000002,
    "role_pubg": 1482902200000000003,
    "role_chess": 1482902200000000004,
    "role_bs": 1482902200000000005,
}

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
        title="<a:11pm_redflower:1508777764994416791> ⋮ __Situation Roles__ ⊹",
        description=(
            "> ## __What's your actual situation?__\n"
            "> <@&1482902155219304549>\n"
            "> <@&1482902157324849333>\n"
            "> <@&1482902156364484661>\n\n"
            "-# © 2026 Moon Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )

    e2 = discord.Embed(
        title="<:gendersheaven:1421638974287384747> ⋮ __Gender Roles__ ⊹",
        description=(
            "> ## __What's your gender?__\n"
            "> <@&1482902134071754832>\n"
            "> <@&1482902134545580123>\n"
            "> <@&1482902135000000000>\n\n"
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
            "## <a:butterfly:1432369241474076692> You’ve Officially Unlocked The Right To Beg For Some Fancy Roles :\n\n"
            "<a:powersheaven:1400669588596719679> **| Powers**\n"
            "⇝ Unlock Special Functionalities And Privileges Within The Server\n\n"
            "<a:specialheaven1:1400670272352161815> **| Special Roles**\n"
            "⇝ Showcase Your Identity With Distinctive And Stylish Roles\n\n"
            "<a:special2heaven:1400670604121739385> **| Special Roles 2 (Only Given By Owners)**\n"
            "⇝ Exclusive Titles Personally Assigned By The Server Owners\n\n"
            "<a:girlsheaven:1400671165885710386> **| Girls Roles**\n"
            "⇝ Express Your Personality With Roles Designed Especially For Girls\n\n"
            "<a:removeheaven:1400671588935798815> **| Remove 1 Of Your Roles**\n"
            "⇝ Get Rid Of That Cringe Role You Picked At 3AM\n\n"
            "<a:clickheaven:1400671930834747432> | Click The Select Menu Below And Choose Category\n\n"
            "-# **`© 2026 Moon Night™. All rights reserved.`**"
        ),
        color=EMBED_COLOR
    )
    embed.set_image(url="https://i.imgur.com/moon_night_banner.png")
    return embed



# ==========================================
# 9. MODERATION COMMANDS
# ==========================================

@bot.tree.command(name="mutechat", description="Timeout a member in text chat (e.g. 60s, 1m, 6h)")
@app_commands.describe(user="Member to mute", duration="Duration: 60s, 1m, 6h, 1d")
@is_owner_or_admin()
async def mutechat(interaction: Interaction, user: discord.Member, duration: str):
    if is_protected(user):
        return await interaction.response.send_message("🛡️ This member is protected and cannot be muted.", ephemeral=True)

    seconds = parse_duration(duration)
    if seconds is None:
        return await interaction.response.send_message(
            "❌ Invalid duration. Use for example `60s`, `1m`, `6h` or `1d` (maximum 28d).",
            ephemeral=True
        )

    try:
        await user.timeout(discord.utils.utcnow() + __import__("datetime").timedelta(seconds=seconds),
                            reason=f"Chat mute by {interaction.user}")
        await interaction.response.send_message(
            f"🔇 {user.mention} has been muted in chat for **{format_duration(seconds)}**."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to timeout this member, or their role is higher than mine.",
            ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message("❌ Discord refused the timeout request.", ephemeral=True)


@bot.tree.command(name="unmutechat", description="Remove a member's chat mute")
@app_commands.describe(user="Member to unmute")
@is_owner_or_admin()
async def unmutechat(interaction: Interaction, user: discord.Member):
    try:
        await user.timeout(None, reason=f"Chat unmute by {interaction.user}")
        await interaction.response.send_message(f"🔊 {user.mention} has been unmuted in chat.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove this timeout.", ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message("❌ Discord refused the unmute request.", ephemeral=True)


@bot.tree.command(name="mutevc", description="Server-mute a member in voice chat")
@app_commands.describe(user="Member to mute in VC")
@is_owner_or_admin()
async def mutevc(interaction: Interaction, user: discord.Member):
    if is_protected(user):
        return await interaction.response.send_message("🛡️ This member is protected and cannot be VC muted.", ephemeral=True)

    if not user.voice:
        return await interaction.response.send_message(
            "❌ This member is not currently in a voice channel.", ephemeral=True
        )

    try:
        await user.edit(mute=True, reason=f"VC mute by {interaction.user}")
        await interaction.response.send_message(f"🔇 {user.mention} is now server-muted in VC.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to server-mute this member.", ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message("❌ Discord refused the VC mute request.", ephemeral=True)


@bot.tree.command(name="unmutevc", description="Remove a member's server VC mute")
@app_commands.describe(user="Member to unmute in VC")
@is_owner_or_admin()
async def unmutevc(interaction: Interaction, user: discord.Member):
    try:
        await user.edit(mute=False, reason=f"VC unmute by {interaction.user}")
        await interaction.response.send_message(f"🔊 {user.mention} has been unmuted in VC.")
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to remove the VC mute.", ephemeral=True
        )
    except discord.HTTPException:
        await interaction.response.send_message("❌ Discord refused the VC unmute request.", ephemeral=True)


@bot.tree.command(name="antinuke", description="Protect a member from moderation actions")
@app_commands.describe(user="Member to protect")
@is_owner_or_admin()
async def antinuke(interaction: Interaction, user: discord.Member):
    if user.id == OWNER_ID:
        return await interaction.response.send_message(
            "🛡️ The bot owner is already permanently protected.", ephemeral=True
        )

    PROTECTED_USERS.add(user.id)

    protected_role = discord.utils.get(interaction.guild.roles, name="Protected")
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
            await user.add_roles(protected_role, reason="Antinuke protection")
        except discord.Forbidden:
            pass

    await interaction.response.send_message(
        f"🛡️ {user.mention} is now **Protected**. The bot will refuse moderation actions against them."
        + (" The `Protected` role was added." if protected_role else ""),
        ephemeral=False
    )


@bot.tree.command(name="jail", description="Give the configured Jail role to a member")
@app_commands.describe(user="Member to jail")
@is_owner_or_admin()
async def jail(interaction: Interaction, user: discord.Member):
    if is_protected(user):
        return await interaction.response.send_message(
            "🛡️ This member is protected and cannot be jailed.", ephemeral=True
        )

    jail_role = get_jail_role(interaction.guild)
    if not jail_role:
        return await interaction.response.send_message(
            "❌ Jail role is not configured. Set `JAIL_ROLE_ID` to the role you want to use.",
            ephemeral=True
        )

    try:
        await user.add_roles(jail_role, reason=f"Jail by {interaction.user}")
        await interaction.response.send_message(
            f"⛓️ {user.mention} has been jailed with {jail_role.mention}."
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I can't add the Jail role. Make sure my bot role is above the Jail role.",
            ephemeral=True
        )


@bot.tree.command(name="about", description="Show server information and statistics")
async def about(interaction: Interaction):
    guild = interaction.guild
    if not guild:
        return await interaction.response.send_message("❌ This command can only be used in a server.", ephemeral=True)

    update_peak_members(guild)

    total_members = guild.member_count or len(guild.members)
    roles_count = len(guild.roles)
    rooms_count = len(guild.channels)
    active_members = sum(
        1 for member in guild.members
        if member.status in {discord.Status.online, discord.Status.idle, discord.Status.dnd}
    )
    offline_members = max(total_members - active_members, 0)
    voice_members = sum(len(channel.members) for channel in guild.voice_channels)
    peak_members = SERVER_PEAK_MEMBERS.get(guild.id, total_members)

    embed = discord.Embed(
        title=f"ℹ️ {guild.name} — Server Information",
        color=EMBED_COLOR
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)

    created_ts = int(guild.created_at.timestamp())
    embed.add_field(name="📅 Server Created", value=f"<t:{created_ts}:F>\n<t:{created_ts}:R>", inline=False)
    embed.add_field(name="👥 Members", value=f"`{total_members}`", inline=True)
    embed.add_field(name="🟢 Active", value=f"`{active_members}`", inline=True)
    embed.add_field(name="⚫ Offline", value=f"`{offline_members}`", inline=True)
    embed.add_field(name="📈 Peak Members", value=f"`{peak_members}`", inline=True)
    embed.add_field(name="🎭 Roles", value=f"`{roles_count}`", inline=True)
    embed.add_field(name="🏠 Rooms / Channels", value=f"`{rooms_count}`", inline=True)
    embed.add_field(name="🔊 In Voice", value=f"`{voice_members}`", inline=True)
    embed.add_field(name="🆔 Server ID", value=f"`{guild.id}`", inline=True)
    embed.set_footer(text="Moon Night Server Information")

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="invite", description="Get the bot's invite link")
async def invite(interaction: Interaction):
    permissions = discord.Permissions(administrator=True)
    invite_url = discord.utils.oauth_url(
        bot.user.id,
        permissions=permissions,
        scopes=("bot", "applications.commands")
    )

    embed = discord.Embed(
        title="🤖 Invite Moon Night Bot",
        description=f"Click the button below to invite me to another server.",
        color=EMBED_COLOR
    )
    view = View(timeout=300)
    view.add_item(Button(label="Invite Bot", style=ButtonStyle.link, url=invite_url))

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


# ==========================================
# PROTECTION GUARD
# ==========================================
@bot.event
async def on_member_join(member: discord.Member):
    update_peak_members(member.guild)


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

bot.run(BOT_TOKEN)
