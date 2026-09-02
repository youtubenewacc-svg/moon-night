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
# 1. ORIGINAL EMBEDS & PANELS
# ==========================================

# --- RULES PANEL (L-QDIM) ---
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Join Need Help!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))

def get_rules_embed():
    embed = discord.Embed(
        title="• Moon Night : Rules •",
        description=(
            "> To make Sure everyone enjoy, please follow those guidelines :\n\n"
            "id ➔ Follow the [Discord TOS](https://dis.gd/tos) and The [Discord Community Guidelines](https://dis.gd/guidelines)\n"
            "id ➔ **Aya NSFW content f server = jail**\n"
            "id ➔ **Respect aya member f server, kifma kan!**\n"
            "id ➔ **Abusing any power treportat biha b preuve = warn ➔ remove role**\n"
            "id ➔ **Need help daret bach it7alo lmachakil, machi bach trolli, troll f nh = blacklist n.h.**\n"
            "id ➔ **Sbek chi wahd 3ndo role (staff, high role, admin...) matseboch, tla3 need help reporti bih, ghadi itremova lih role**\n"
            "id ➔ **Staff provoque 3liha punishment. pd: 3essas 9damet, jib chi haja jdida**\n"
            "id ➔ **Bghiti trolli, tseb, tla9 sb's, dir one tap dialek, ou lockiha (.v lock) ou hara mat3ich, room opened = respect the rules!**\n"
            "id ➔ **Abusa 3lik chi wahed 3ndo role (staff, high role, admin...) tla3 n.h. wla 7el ticket hna : <#1482902524376780932> ou ghadi it7ayed lih role**\n"
            "id ➔ **Pub ou pub vc 3liha jail, chi wahd spammak, wla dar pub vc, tla3 need help ou report it (don't forget screen / record)**\n\n"
            "id ➔ **Have questions or issues? Our team is ready to help you!**\n"
            "id ➔ **Questions, problems, or requests? Open a ticket now!**"
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="© 2026 Moon Night™. All rights reserved.")
    return embed


# --- SELF ROLES PANEL (L-QDIM B 3 EMBEDS & SELECT MENU) ---
class SelfRolesGamesSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Valorant", emoji="🎮", value="game_val"),
            discord.SelectOption(label="GTA V / Grand RP", emoji="🚗", value="game_gta"),
            discord.SelectOption(label="League of Legends", emoji="⚔️", value="game_lol"),
            discord.SelectOption(label="Minecraft", emoji="⛏️", value="game_mc"),
            discord.SelectOption(label="Free Fire", emoji="🔥", value="game_ff")
        ]
        super().__init__(placeholder="Select A Games Role!", options=options, custom_id="self_game_select")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message(f"✅ Selected: {self.values[0]}", ephemeral=True)

class SelfRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRolesGamesSelect())

    @discord.ui.button(label="• Heartless", style=ButtonStyle.secondary, custom_id="role_heartless")
    async def btn_heartless(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Heartless Role", ephemeral=True)

    @discord.ui.button(label="• Taken", style=ButtonStyle.secondary, custom_id="role_taken")
    async def btn_taken(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Taken Role", ephemeral=True)

    @discord.ui.button(label="• Single", style=ButtonStyle.secondary, custom_id="role_single")
    async def btn_single(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Single Role", ephemeral=True)

    @discord.ui.button(label="• Female", style=ButtonStyle.secondary, custom_id="role_female", row=1)
    async def btn_female(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Female Role", ephemeral=True)

    @discord.ui.button(label="• Male", style=ButtonStyle.secondary, custom_id="role_male", row=1)
    async def btn_male(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Male Role", ephemeral=True)

    @discord.ui.button(label="• Trans", style=ButtonStyle.secondary, custom_id="role_trans", row=1)
    async def btn_trans(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("Toggle Trans Role", ephemeral=True)

def get_selfroles_embeds():
    embed1 = discord.Embed(
        title=":11pm_redflower: : Situation Roles ÷",
        description="### What's your actual situation?\n@rôle inconnu\n@rôle inconnu\n@rôle inconnu",
        color=EMBED_COLOR
    )
    embed1.set_footer(text="© 2026 Moon Night. All rights reserved.")

    embed2 = discord.Embed(
        title=":gendersheaven: : Gender Roles ÷",
        description="### What's your gender?\n@rôle inconnu\n@rôle inconnu\n@rôle inconnu",
        color=EMBED_COLOR
    )
    embed2.set_footer(text="© 2026 Moon Night. All rights reserved.")

    embed3 = discord.Embed(
        title=":game: : Games Roles ÷",
        description="### Do you play any games?",
        color=EMBED_COLOR
    )
    embed3.set_footer(text="© 2026 Moon Night™. All rights reserved.")

    return [embed1, embed2, embed3]


# --- ROLE REQUEST PANEL (L-QDIM B SELECT MENU) ---
class RoleRequestCategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Powers", description="Special Functionalities & Privileges", emoji="⚡", value="req_powers"),
            discord.SelectOption(label="Special Roles", description="Showcase Your Identity", emoji="💎", value="req_special"),
            discord.SelectOption(label="Special Roles 2", description="Given By Owners", emoji="🎩", value="req_special2"),
            discord.SelectOption(label="Girls Roles", description="Designed Especially For Girls", emoji="🌸", value="req_girls"),
            discord.SelectOption(label="Remove 1 Of Your Roles", description="Get Rid Of Cringe Roles", emoji="⭐", value="req_remove")
        ]
        super().__init__(placeholder="Select A Role Category", options=options, custom_id="role_req_select")

    async def callback(self, interaction: Interaction):
        await interaction.response.send_message(f"📩 Opened category: **{self.values[0]}**", ephemeral=True)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleRequestCategorySelect())

def get_rolerequest_embed():
    embed = discord.Embed(
        title="💦 You've Officially Unlocked The Right To Beg For Some Fancy Roles :",
        description=(
            ":powersheaven: | **Powers**\n➔ Unlock Special Functionalities And Privileges Within The Server\n\n"
            ":specialheaven1: | **Special Roles**\n➔ Showcase Your Identity With Distinctive And Stylish Roles\n\n"
            ":special2heaven: | **Special Roles 2 (Only Given By Owners)**\n➔ Exclusive Titles Personally Assigned By The Server Owners\n\n"
            ":girlsheaven: | **Girls Roles**\n➔ Express Your Personality With Roles Designed Especially For Girls\n\n"
            ":removeheaven: | **Remove 1 Of Your Roles**\n➔ Get Rid Of That Cringe Role You Picked At 3AM\n\n"
            ":clickheaven: | **Click The Select Menu Below And Choose Category**"
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="© 2026 Moon Night™. All rights reserved.")
    return embed


# --- STAFF APPLY PANEL (L-QDIM) ---
class StaffApplyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", style=ButtonStyle.success, custom_id="btn_apply_staff")
    async def apply_staff(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("📝 Staff application form coming soon!", ephemeral=True)

    @discord.ui.button(label="Apply for Game Mods", style=ButtonStyle.success, custom_id="btn_apply_gamemods")
    async def apply_gamemods(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("🎮 Game Mods application form coming soon!", ephemeral=True)

def get_staff_apply_embed():
    embed = discord.Embed(
        title="Staff Apply For Moon Night ©",
        description=(
            "Moon Night © is now accepting staff applications! Be a part of our family! "
            "We would love to bring new people to our team that would help grow this family together!\n\n"
            "**• Staff**\n"
            "• At Least 17 Years Old\n"
            "• Voice Level 5+\n"
            "• Active & Respectful\n\n"
            "**• Game Mods**\n"
            "• At Least 17 Years Old\n"
            "• Voice Level 5+\n"
            "• Active & Respectful"
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="Copyright © 2026 Lisa X Moon Night ©")
    return embed


# --- MAP GUIDE PANEL (L-QDIM) ---
def get_map_guide_embed():
    embed = discord.Embed(
        title="🗺️ Moon Night - Server Map & Guide",
        description=(
            "Welcome to **Moon Night**! Here is your quick guide to navigate the server:\n\n"
            "📌 <#1482902524376780932> - Read server rules & info.\n"
            "🎭 **#self-roles** - Pick your roles.\n"
            "💬 **#general** - Chat with community.\n"
            "🔊 **Voice Channels** - Hangout & play games."
        ),
        color=EMBED_COLOR
    )
    embed.set_footer(text="© 2026 Moon Night™. All rights reserved.")
    return embed


# --- SOCIALS & STATS (L-JDAD) ---
class SocialsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Instagram", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Tiktok", style=ButtonStyle.link, url="https://tiktok.com"))
        self.add_item(Button(label="IG Group", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Store", style=ButtonStyle.link, url="https://store.moonnight.com"))

def get_socials_embed():
    embed = discord.Embed(
        title="Hey @everyone",
        description=(
            "-# > 𝗦𝘁𝗮𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝘄𝗶𝘁𝗵 **𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁** 𝗼𝗻 𝗮𝗹𝗹 𝗼𝘂𝗿 𝗽𝗹𝗮𝘁𝗳𝗼𝗿𝗺𝘀.\n\n"
            "### * **Instagram :** *** Follow us for news & highlights. ***\n"
            "### * **TikTok :** ***Follow us for videos & updates***\n"
            "### * **IG Group :** *** Stay close to the community. ***\n"
            "### * **Store :** *** Shop exclusive Moon Night items. ***\n\n"
            "-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑩𝒆𝒎𝒐𝒓𝒊𝒆𝒔"
        ),
        color=EMBED_COLOR
    )
    return embed

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
            f"- **Total Members:** `{guild.member_count if guild else 0}` ⁘\n"
            f"- **Active in Voice:** `{sum(len(c.members) for c in guild.voice_channels) if guild else 0}` ⁘\n"
            f"- **Boosters:** `{guild.premium_subscription_count if guild else 0}` ⁘\n\n"
            "Stay active, and enjoy your time in Moon Night"
        ),
        color=EMBED_COLOR
    )
    return embed


# ==========================================
# MASTER PANEL SENDER COMMAND
# ==========================================
@bot.tree.command(name="send_panel", description="Send Moon Night panels (Owner/Admin Only)")
@app_commands.choices(panel=[
    app_commands.Choice(name="Rules", value="rules"),
    app_commands.Choice(name="Self Roles", value="selfroles"),
    app_commands.Choice(name="Role Request", value="rolerequest"),
    app_commands.Choice(name="Staff Apply", value="staffapply"),
    app_commands.Choice(name="Map Guide", value="mapguide"),
    app_commands.Choice(name="Socials", value="socials"),
    app_commands.Choice(name="Stats", value="stats")
])
@is_owner_or_admin_slash()
async def send_panel(interaction: Interaction, panel: str):
    await interaction.response.defer(ephemeral=True)
    if panel == "rules":
        await interaction.channel.send(embed=get_rules_embed(), view=RulesView())
    elif panel == "selfroles":
        await interaction.channel.send(embeds=get_selfroles_embeds(), view=SelfRolesView())
    elif panel == "rolerequest":
        await interaction.channel.send(embed=get_rolerequest_embed(), view=RoleRequestView())
    elif panel == "staffapply":
        await interaction.channel.send(embed=get_staff_apply_embed(), view=StaffApplyView())
    elif panel == "mapguide":
        await interaction.channel.send(embed=get_map_guide_embed())
    elif panel == "socials":
        await interaction.channel.send(embed=get_socials_embed(), view=SocialsView())
    elif panel == "stats":
        await interaction.channel.send(embed=get_stats_embed(interaction.guild), view=StatsView(interaction.guild))
    
    await interaction.followup.send(f"✅ Panel **{panel}** sent successfully!", ephemeral=True)


# ==========================================
# 2. HELP SYSTEM
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
# 3. VOICE, MUSIC & MODERATION COMMANDS
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
