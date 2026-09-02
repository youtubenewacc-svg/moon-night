import os
import time
import asyncio
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button, Select, Modal, TextInput
import yt_dlp

# ==========================================
# CONFIGURATION FROM ENVIRONMENT VARIABLES
# ==========================================
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "1241496820455313533"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1544405575314440342"))

EMBED_COLOR = 0x2b2d31

if not BOT_TOKEN:
    print("❌ ERROR: DISCORD_TOKEN environment variable is missing!")

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

class MoonNightBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=["=", "!"], intents=intents)
        self.remove_command('help')

    async def setup_hook(self):
        await self.tree.sync()
        print("Slash Commands Synced Successfully!")

bot = MoonNightBot()

# Checks dyal Protection
def is_owner_or_admin_slash():
    async def predicate(interaction: Interaction):
        if interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Had l-command khas b Owners/Admins ghir!", ephemeral=True)
        return False
    return app_commands.check(predicate)

def is_owner_or_admin_ctx():
    async def predicate(ctx):
        if ctx.author.id == OWNER_ID or ctx.author.guild_permissions.administrator:
            return True
        await ctx.send("❌ Hada command privet ghir l Owner w Admins!", delete_after=5)
        return False
    return commands.check(predicate)


# ==========================================
# 1. PANELS & EMBEDS
# ==========================================

# --- SOCIALS PANEL ---
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


# --- STATS PANEL ---
class StatsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        total = guild.member_count if guild else 0
        voice = sum(len(c.members) for c in guild.voice_channels) if guild else 0
        self.add_item(Button(label=f"Members : {total}", style=ButtonStyle.secondary, disabled=True))
        self.add_item(Button(label=f"in Voice : {voice}", style=ButtonStyle.secondary, disabled=True))

def get_stats_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="Moon Night Statistics",
        description=(
            f"- <:Fams:1451145463511384094> **Total Members:** `{guild.member_count if guild else 8628}` ⁘\n"
            f"- <:voice:1451145649801269420> **Active in Voice:** `{sum(len(c.members) for c in guild.voice_channels) if guild else 107}` ⁘\n"
            f"- <:premium:1451145621246312529> **Boosters:** `{guild.premium_subscription_count if guild else 48}` ⁘\n\n"
            "Stay active, and enjoy your time in Moon Night"
        ),
        color=EMBED_COLOR
    )
    return embed


# --- RULES PANEL ---
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))

def get_rules_embed():
    embed = discord.Embed(
        description=(
            "> 𝗧𝗼 𝗺𝗮𝗸𝗲 𝗦𝘂𝗿𝗲 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝗲𝗻𝗷𝗼𝘆, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗼𝘀𝗲 𝗴𝘂𝗶𝗱𝗲𝗹𝗶𝗻𝗲𝘀 :\n\n"
            "<a:estrellasbrillando:1442626060134121472> **1. Respect Everyone:** Treat all members with respect. No harassment, hate speech, or toxicity.\n"
            "<a:estrellasbrillando:1442626060134121472> **2. No Spam:** Avoid spamming messages, emojis, or mentions.\n"
            "<a:estrellasbrillando:1442626060134121472> **3. Appropriate Content:** Keep text and media appropriate for the channel."
        ),
        color=EMBED_COLOR
    )
    return embed


# --- SELF ROLES PANEL ---
ROLE_IDS = {
    "boy": 134250000000000001,
    "girl": 134250000000000002,
    "announcement": 134250000000000003,
    "event": 134250000000000004
}

class SelfRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Boy", style=ButtonStyle.primary, custom_id="role_boy", emoji="👨")
    async def btn_boy(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, ROLE_IDS["boy"])

    @discord.ui.button(label="Girl", style=ButtonStyle.danger, custom_id="role_girl", emoji="👩")
    async def btn_girl(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, ROLE_IDS["girl"])

    @discord.ui.button(label="Announcements", style=ButtonStyle.secondary, custom_id="role_announce", emoji="🔔")
    async def btn_announce(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, ROLE_IDS["announcement"])

    @discord.ui.button(label="Events", style=ButtonStyle.secondary, custom_id="role_events", emoji="🎉")
    async def btn_events(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, ROLE_IDS["event"])

    async def toggle_role(self, interaction: Interaction, role_id: int):
        role = interaction.guild.get_role(role_id)
        if not role:
            return await interaction.response.send_message("❌ Role ma m9adch mzyan f bot config!", ephemeral=True)
        
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            await interaction.response.send_message(f"➖ T7yd lik role: **{role.name}**", ephemeral=True)
        else:
            await interaction.user.add_roles(role)
            await interaction.response.send_message(f"➕ Tzad lik role: **{role.name}**", ephemeral=True)

def get_selfroles_embed():
    embed = discord.Embed(
        title="🎭 Self Roles - Moon Night",
        description="Khtar l-roles li bghiti b klik wahed f l-boutonat li te7t:",
        color=EMBED_COLOR
    )
    return embed


# --- ROLE REQUEST PANEL ---
class RoleRequestModal(Modal, title="طلب رتبة / Role Request"):
    role_name = TextInput(label="اسم الرتبة المطلوبة / Role Name", placeholder="مثال: Content Creator, Designer...", required=True)
    proof = TextInput(label="الدليل / Proof (Link, Info)", style=discord.TextStyle.paragraph, placeholder="حط الرابط ولا السبب علاش كتستاهل الرتبة", required=True)

    async def on_submit(self, interaction: Interaction):
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        if log_channel:
            embed = discord.Embed(title="📩 Request Role Jdid", color=0x00ff00)
            embed.add_field(name="User", value=interaction.user.mention, inline=True)
            embed.add_field(name="Role", value=self.role_name.value, inline=True)
            embed.add_field(name="Proof / Reason", value=self.proof.value, inline=False)
            await log_channel.send(embed=embed)
        
        await interaction.response.send_message("✅ الطلب ديالك تصيفط ل الإدارة بنجاح!", ephemeral=True)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="طلب رتبة / Request Role", style=ButtonStyle.success, custom_id="req_role_btn", emoji="📝")
    async def req_btn(self, interaction: Interaction, button: Button):
        await interaction.response.send_modal(RoleRequestModal())

def get_rolerequest_embed():
    embed = discord.Embed(
        title="✨ Request Roles System",
        description="Ila bghiti t-demandi chi role khas (VIP, Creator, Streamer...), اضغط على الزر أسفله وعمر الاستمارة.",
        color=EMBED_COLOR
    )
    return embed


# ==========================================
# MASTER PANEL SENDER COMMAND
# ==========================================
@bot.tree.command(name="send_panel", description="Send Moon Night panels (Owner/Admin Only)")
@app_commands.choices(panel=[
    app_commands.Choice(name="Socials", value="socials"),
    app_commands.Choice(name="Stats", value="stats"),
    app_commands.Choice(name="Rules", value="rules"),
    app_commands.Choice(name="Self Roles", value="selfroles"),
    app_commands.Choice(name="Role Request", value="rolerequest")
])
@is_owner_or_admin_slash()
async def send_panel(interaction: Interaction, panel: str):
    await interaction.response.defer(ephemeral=True)
    if panel == "socials":
        await interaction.channel.send(embed=get_socials_embed(), view=SocialsView())
    elif panel == "stats":
        await interaction.channel.send(embed=get_stats_embed(interaction.guild), view=StatsView(interaction.guild))
    elif panel == "rules":
        await interaction.channel.send(embed=get_rules_embed(), view=RulesView())
    elif panel == "selfroles":
        await interaction.channel.send(embed=get_selfroles_embed(), view=SelfRolesView())
    elif panel == "rolerequest":
        await interaction.channel.send(embed=get_rolerequest_embed(), view=RoleRequestView())
    await interaction.followup.send(f"✅ Panel **{panel}** sent successfully!", ephemeral=True)


# ==========================================
# 2. HELP SYSTEM (SELECT MENU + PAGINATION)
# ==========================================
HELP_DATA = {
    "Information": [
        [("=about", "About the bot."), ("=botinfo", "Bot statistics."), ("=help", "Shows this menu."), ("=invite", "Invite link.")],
        [("=ping", "Pong! check latency"), ("=serverstats", "Display server stats."), ("=vc", "Voice channel stats.")]
    ],
    "Music": [
        [("=join", "Join voice channel"), ("=leave", "Leave voice channel"), ("=play <url/name>", "Plays audio"), ("=stop", "Stops music")]
    ],
    "Voice": [
        [("=moveme <user>", "Move to a member's VC"), ("=rvc", "Random VC user"), ("=vcdeafen <user>", "Deafen a member")],
        [("=vcmute <user>", "Mute a member"), ("=vcunmute <user>", "Unmute a member")]
    ],
    "Moderation": [
        [("=warn <user>", "Warn a user"), ("=unbankai <user>", "Remove ban"), ("=unjail <user>", "Remove from jail")]
    ],
    "Profile": [
        [("=addbg", "Add background (Owner)"), ("=bgshop", "Buy backgrounds"), ("=fullprofile", "Full profile card")]
    ]
}

CATEGORY_EMOJIS = {"Information": "ℹ️", "Music": "🎵", "Voice": "📢", "Moderation": "🔨", "Profile": "👤"}

class HelpSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=cat, emoji=CATEGORY_EMOJIS.get(cat, "📌"), description=f"Explore {cat} commands")
            for cat in HELP_DATA.keys()
        ]
        super().__init__(placeholder="🔍 Choose a category...", options=options, custom_id="help_select")

    async def callback(self, interaction: Interaction):
        view: HelpView = self.view
        view.current_category = self.values[0]
        view.current_page = 0
        await view.update_message(interaction)

class HelpView(View):
    def __init__(self):
        super().__init__(timeout=180)
        self.current_category = None
        self.current_page = 0
        self.add_item(HelpSelect())

    def get_embed(self):
        if not self.current_category:
            embed = discord.Embed(title="🌙 Moon Night - Help Center", description="Welcome to the help menu! Choose a category from the select menu below.", color=EMBED_COLOR)
            embed.set_image(url="https://i.imgur.com/vHqB5o2.png")
            return embed
        
        pages = HELP_DATA[self.current_category]
        page_cmds = pages[self.current_page]
        
        embed = discord.Embed(
            title=f"{CATEGORY_EMOJIS.get(self.current_category, '')} {self.current_category} Commands",
            description=f"**Category:** `{self.current_category}` | **Prefix:** `=`",
            color=EMBED_COLOR
        )
        for cmd, desc in page_cmds:
            embed.add_field(name=f"`{cmd}`", value=f"• {desc}", inline=False)
            
        embed.set_footer(text=f"Page {self.current_page + 1} of {len(pages)}")
        embed.set_image(url="https://i.imgur.com/vHqB5o2.png")
        return embed

    def update_buttons(self):
        self.btn_prev.disabled = self.current_category is None or self.current_page == 0
        self.btn_next.disabled = self.current_category is None or self.current_page == len(HELP_DATA.get(self.current_category, [])) - 1
        self.btn_home.disabled = self.current_category is None

    async def update_message(self, interaction: Interaction):
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    @discord.ui.button(label="Previous", style=ButtonStyle.secondary, custom_id="help_prev", emoji="⬅️", disabled=True)
    async def btn_prev(self, interaction: Interaction, button: Button):
        self.current_page -= 1
        await self.update_message(interaction)

    @discord.ui.button(label="Next", style=ButtonStyle.secondary, custom_id="help_next", emoji="➡️", disabled=True)
    async def btn_next(self, interaction: Interaction, button: Button):
        self.current_page += 1
        await self.update_message(interaction)

    @discord.ui.button(label="Home", style=ButtonStyle.primary, custom_id="help_home", emoji="🏠", disabled=True, row=2)
    async def btn_home(self, interaction: Interaction, button: Button):
        self.current_category = None
        self.current_page = 0
        await self.update_message(interaction)

@bot.command(name="help")
async def custom_help(ctx):
    view = HelpView()
    await ctx.send(embed=view.get_embed(), view=view)


# ==========================================
# 3. VOICE & MUSIC COMMANDS
# ==========================================
ytdl_opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'auto', 'source_address': '0.0.0.0'}
ffmpeg_opts = {'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

@bot.command(name="join")
async def join_vc(ctx):
    if not ctx.author.voice:
        return await ctx.send("❌ Khasak tkon f voice channel b3da!")
    channel = ctx.author.voice.channel
    if ctx.voice_client is not None:
        await ctx.voice_client.move_to(channel)
        return await ctx.send(f"✅ T7awelt l: **{channel.name}**")
    await channel.connect()
    await ctx.send(f"📢 Dkhalt l: **{channel.name}**")

@bot.command(name="leave")
async def leave_vc(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Kherjt mn l-voice channel.")
    else:
        await ctx.send("❌ Mamshtarekh f ta voice channel.")

@bot.command(name="play")
async def play_music(ctx, *, search: str):
    if not ctx.author.voice:
        return await ctx.send("❌ Khasak tkon f voice channel!")
    if not ctx.voice_client:
        await ctx.author.voice.channel.connect()

    async with ctx.typing():
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
        if 'entries' in data:
            data = data['entries'][0]
        url = data['url']
        title = data['title']
        
        ctx.voice_client.stop()
        ctx.voice_client.play(discord.FFmpegPCMAudio(url, **ffmpeg_opts))
        
    await ctx.send(f"🎵 Playing: **{title}**")

@bot.command(name="stop")
async def stop_music(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("🛑 Music stopped.")
    else:
        await ctx.send("❌ Walou khdam daba.")


# ==========================================
# 4. MODERATION & GENERAL COMMANDS
# ==========================================
@bot.command(name="ping")
async def cmd_ping(ctx):
    await ctx.send(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@bot.command(name="warn")
@is_owner_or_admin_ctx()
async def cmd_warn(ctx, member: discord.Member, *, reason="No reason"):
    await ctx.send(f"⚠️ **{member.name}** t3tato inndar! Sabab: {reason}")

@bot.command(name="unjail")
@is_owner_or_admin_ctx()
async def cmd_unjail(ctx, member: discord.Member):
    await ctx.send(f"🔓 **{member.name}** kherj mn l-jail.")

@bot.command(name="vcmute")
@is_owner_or_admin_ctx()
async def cmd_vcmute(ctx, member: discord.Member):
    if member.voice:
        await member.edit(mute=True)
        await ctx.send(f"🔇 {member.mention} t-muta f voice.")
    else:
        await ctx.send("❌ Hada makaynch f voice!")

@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user.name} ({bot.user.id})")
    print(f"🔒 Owner ID: {OWNER_ID}")

bot.run(BOT_TOKEN)
