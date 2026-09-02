import os
import time
import asyncio
import discord
from discord.ext import commands
from discord import app_commands, Interaction, ButtonStyle
from discord.ui import View, Button, Select
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
# 1. PANELS & VIEWS
# ==========================================

# --- 1. SOCIALS PANEL ---
class SocialsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Instagram", style=ButtonStyle.link, url="https://instagram.com", emoji="<:INSTA:1532413334261993602>"))
        self.add_item(Button(label="TikTok", style=ButtonStyle.link, url="https://tiktok.com", emoji="<:TIKTOK:1532413262669283451>"))
        self.add_item(Button(label="IG Group", style=ButtonStyle.link, url="https://instagram.com", emoji="<:popcornpandita:1529830303483429025>"))
        self.add_item(Button(label="Store", style=ButtonStyle.link, url="https://store.moonnight.com", emoji="<:5143storeg:1532413144876585056>"))

@bot.tree.command(name="socials", description="Show Moon Night social platforms")
async def cmd_socials(interaction: Interaction):
    embed = discord.Embed(
        description=(
            "-# > 𝗦𝘁𝗮𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝘄𝗶𝘁𝗵 **𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁** 𝗼𝗻 𝗮𝗹𝗹 𝗼𝘂𝗿 𝗽𝗹𝗮𝘁𝗳𝒐𝗿𝗺𝘀.\n\n"
            "<:INSTA:1532413334261993602> **Instagram :** ***Follow us for news & highlights.***\n"
            "<:TIKTOK:1532413262669283451> **TikTok :** ***Follow us for videos & updates***\n"
            "<:popcornpandita:1529830303483429025> **IG Group :** ***Stay close to the community.***\n"
            "<:5143storeg:1532413144876585056> **Store :** ***Shop exclusive Moon Night items.***\n\n"
            "-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑴𝒆𝒎𝒐𝒓𝒊𝒆𝒔 <:bunny_moon:1532388030411833344>"
        ),
        color=EMBED_COLOR
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.channel.send(content="# **Hey  @everyone  ** <:theCall_pink_hi:1509305726655402185>", embed=embed, view=SocialsView())
    await interaction.response.send_message("✅ Socials panel sent!", ephemeral=True)


# --- 2. RULES PANEL ---
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Join Need Help!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))

@bot.tree.command(name="rules", description="Show Moon Night Rules")
async def cmd_rules(interaction: Interaction):
    embed = discord.Embed(
        title="・Moon Night : Rules・",
        description=(
            "> 𝗧𝗼 𝗺𝗮𝗸𝗲 𝗦𝘂𝗿𝗲 𝗲𝘃𝗲𝗿𝘆𝗼𝗻𝗲 𝗲𝗻𝗷𝗼𝘆, 𝗽𝗹𝗲𝗮𝘀𝗲 𝗳𝗼𝗹𝗹𝗼𝘄 𝘁𝗵𝗼𝘀𝗲 𝗴𝘂𝗶𝗱𝗲𝗹𝗶𝗻𝗲𝘀 :\n\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ Follow the [Discord TOS](https://discord.com/terms) and The [Discord Community Guidelines](https://discord.com/guidelines)**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Aya NSFW content f server = jail__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Respect aya member f server, kifma kan!__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Abusing any power treportat biha b preuve = warn ⇝ remove role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Need help daret bach it7alo lmachakil, machi bach trolli, troll f nh = blacklist n.h.__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Sbek chi wahd 3ndo role (staff, high role, admin...) matseboch, tla3 need help reporti bih, ghadi itremova lih role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Staff provoque 3liha punishment. pd: 3essas 9damet, jib chi haja jdida__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Bghiti trolli, tseb, tla9 sb's, dir one tap dialek, ou lockiha (.v lock) ou hara mat3ich, room opened = respect the rules!__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Abusa 3lik chi wahed 3ndo role (staff, high role, admin...) tla3 n.h. wla 7el ticket hna : <#1482902524376780932> ou ghadi it7ayed lih role__**\n"
            "<a:estrellasbrillando:1442626060134121472> **⇝ __Pub ou pub vc 3liha jail, chi wahd spammak, wla dar pub vc, tla3 need help ou report it (don't forget screen / record)__**\n\n"
            "**⇾ __Have questions or issues? Our team is ready to help you!__**\n"
            "**⇾ __Questions, problems, or requests? Open a ticket now!__**\n\n"
            "-# `© 2026 Moon Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    if interaction.guild and interaction.guild.icon:
        embed.set_image(url=interaction.guild.icon.url)
    await interaction.channel.send(embed=embed, view=RulesView())
    await interaction.response.send_message("✅ Rules panel sent!", ephemeral=True)


# --- 3. MAP GUIDE PANEL ---
@bot.tree.command(name="mapguide", description="Show Moon Night Server Map & Guide")
async def cmd_mapguide(interaction: Interaction):
    embed = discord.Embed(
        title="Welcome To Moon Night!",
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
    if interaction.guild and interaction.guild.icon:
        embed.set_image(url=interaction.guild.icon.url)
    await interaction.channel.send(content="# <a:welcome:1442626577690132663> ◜__Welcome To Moon Night!__◞", embed=embed)
    await interaction.response.send_message("✅ Map Guide sent!", ephemeral=True)


# --- 4. STAFF APPLY PANEL ---
class StaffApplyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", style=ButtonStyle.success, custom_id="btn_apply_staff")
    async def apply_staff(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("📝 Staff application form coming soon!", ephemeral=True)

    @discord.ui.button(label="Apply for Game Mods", style=ButtonStyle.success, custom_id="btn_apply_gamemods")
    async def apply_gamemods(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("🎮 Game Mods application form coming soon!", ephemeral=True)

@bot.tree.command(name="staffapply", description="Show Staff Apply Panel")
async def cmd_staffapply(interaction: Interaction):
    embed = discord.Embed(
        title="__Staff Apply For Moon Night  ©__",
        description=(
            "-# Moon  Night  ©'s now is accepting staff applications! Be a part of our family! We would love to bring new people to our team that would help grow this family together!\n\n"
            "### - __Staff__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "### - __Game Mods__\n"
            "> ﹒At Least 17 Years Old\n"
            "> ﹒Voice Level 5+\n"
            "> ﹒Active & Respectful\n\n"
            "-# Copyright © 2026 Lisa X Moon  Night  ©"
        ),
        color=EMBED_COLOR
    )
    await interaction.channel.send(embed=embed, view=StaffApplyView())
    await interaction.response.send_message("✅ Staff Apply panel sent!", ephemeral=True)


# --- 5. STATISTICS PANEL ---
class StatsView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        total = guild.member_count if guild else 0
        voice = sum(len(c.members) for c in guild.voice_channels) if guild else 0
        self.add_item(Button(label=f"Members : {total}", style=ButtonStyle.secondary, disabled=True))
        self.add_item(Button(label=f"in Voice : {voice}", style=ButtonStyle.secondary, disabled=True))

@bot.tree.command(name="stats", description="Show server statistics")
async def cmd_stats(interaction: Interaction):
    guild = interaction.guild
    embed = discord.Embed(
        title="Moon Night Statistics",
        description=(
            f"- <:Fams:1451145463511384094> **Total Members:** `{guild.member_count if guild else 0}`  ⁘\n"
            f"- <:voice:1451145649801269420> **Active in Voice:** `{sum(len(c.members) for c in guild.voice_channels) if guild else 0}`  ⁘\n"
            f"- <:premium:1451145621246312529> **Boosters:** `{guild.premium_subscription_count if guild else 0}`  ⁘\n\n"
            "Stay active, and enjoy your time in Moon Night"
        ),
        color=EMBED_COLOR
    )
    await interaction.channel.send(embed=embed, view=StatsView(guild))
    await interaction.response.send_message("✅ Stats panel sent!", ephemeral=True)


# --- 6. SELF ROLES & BOOSTERS ROLES (B MENTION ROLES BHAL BOOSTER) ---
class SelfRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="• Situation Roles", style=ButtonStyle.secondary, custom_id="btn_sit_roles")
    async def btn_sit(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("🎭 Situation Roles menu clicked!", ephemeral=True)

    @discord.ui.button(label="• Gender Roles", style=ButtonStyle.secondary, custom_id="btn_gender_roles")
    async def btn_gender(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("👥 Gender Roles menu clicked!", ephemeral=True)

@bot.tree.command(name="selfroles", description="Show Self Roles panel")
async def cmd_selfroles(interaction: Interaction):
    embed1 = discord.Embed(
        title="⋮ __Situation Roles__ ⊹",
        description=(
            "## __What's your actual situation?__\n"
            "<@&1482902155219304549>\n"
            "<@&1482902157324849333>\n"
            "<@&1515406788395008170>\n"
            "<@&1482902156364484661>\n\n"
            "-# © 2026 Moon Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )
    embed1.set_author(name="Moon Night", icon_url=interaction.guild.icon.url if interaction.guild and interaction.guild.icon else None)

    embed2 = discord.Embed(
        title="⋮ __Gender Roles__ ⊹",
        description=(
            "## __What's your gender?__\n"
            "<@&1482902134071754832>\n"
            "<@&1482902134545580123>\n\n"
            "-# © 2026 Moon Night. All rights reserved."
        ),
        color=EMBED_COLOR
    )
    
    await interaction.channel.send(content="# <a:11pm_redflower:1508777764994416791>", embeds=[embed1, embed2], view=SelfRolesView())
    await interaction.response.send_message("✅ Self Roles panel sent!", ephemeral=True)


@bot.tree.command(name="boosterroles", description="Show Booster Roles panel")
async def cmd_boosterroles(interaction: Interaction):
    embed = discord.Embed(
        title="৳ Choose your booster role",
        description=(
            "-# Pick one of the roles down as a thanks for boosting!\n"
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
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("✅ Booster Roles panel sent!", ephemeral=True)


# --- 7. ROLE REQUEST WITH ADMIN APPROVAL WORKFLOW ---
class RoleRequestActionView(View):
    def __init__(self, user_id: int, category: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.category = category

    @discord.ui.button(label="Accept", style=ButtonStyle.green, custom_id="req_accept_btn")
    async def accept_btn(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        
        # Hna katzid role IDs 3la hsab l category
        role_mapping = {
            "req_powers": 1482902118137462896,
            "req_special": 1482902117693001898,
            "req_special2": 1482902116858331217,
            "req_girls": 1482902047236952117,
            "req_remove": None
        }
        role_id = role_mapping.get(self.category)
        role_status = ""
        
        if user and role_id:
            role = guild.get_role(role_id)
            if role:
                await user.add_roles(role)
                role_status = f" w t3tah l-role: {role.name}"

        if user:
            try:
                await user.send(f"✅ Your role request for `{self.category}` has been **accepted** by {interaction.user.mention}!{role_status}")
            except:
                pass

        await interaction.response.send_message(f"✅ Accepted by {interaction.user.mention}.", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @discord.ui.button(label="Refuse", style=ButtonStyle.red, custom_id="req_refuse_btn")
    async def refuse_btn(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        
        if user:
            try:
                await user.send(f"❌ Your role request for `{self.category}` was **refused** by {interaction.user.mention}.")
            except:
                pass
                
        await interaction.response.send_message(f"❌ Refused by {interaction.user.mention}.", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

class RoleRequestSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Powers", description="Special Functionalities", emoji="⚡", value="req_powers"),
            discord.SelectOption(label="Special Roles", description="Showcase Your Identity", emoji="💎", value="req_special"),
            discord.SelectOption(label="Special Roles 2", description="Given By Owners", emoji="🎩", value="req_special2"),
            discord.SelectOption(label="Girls Roles", description="Designed For Girls", emoji="🌸", value="req_girls"),
            discord.SelectOption(label="Remove Role", description="Remove Cringe Role", emoji="⭐", value="req_remove")
        ]
        super().__init__(placeholder="Select A Role Category", options=options, custom_id="role_req_select_menu")

    async def callback(self, interaction: Interaction):
        category = self.values[0]
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)

        embed = discord.Embed(
            title="📥 New Role Request",
            description=f"Category requested: `{category}`",
            color=EMBED_COLOR
        )
        embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        embed.timestamp = discord.utils.utcnow()

        view = RoleRequestActionView(user_id=interaction.user.id, category=category)
        if log_channel:
            await log_channel.send(embed=embed, view=view)

        await interaction.response.send_message(f"request category `{category}` has been sent to admins wait accept", ephemeral=True)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleRequestSelect())

@bot.tree.command(name="request_role", description="Show Role Request Panel")
async def cmd_request_role(interaction: Interaction):
    embed = discord.Embed(
        title="◜__Moon Night's Role Request Panel__◞",
        description=(
            "## <a:butterfly:1432369241474076692> You’ve Officially Unlocked The Right To Beg For Some Fancy Roles :\n\n"
            "<:powersheaven:1400669588596719679> **| Powers**\n"
            "⇝ Unlock Special Functionalities And Privileges Within The Server\n\n"
            "<:specialheaven1:1400670272352161815> **| Special Roles**\n"
            "⇝ Showcase Your Identity With Distinctive And Stylish Roles\n\n"
            "<:special2heaven:1400670604121739385> **| Special Roles 2 (Only Given By Owners)**\n"
            "⇝ Exclusive Titles Personally Assigned By The Server Owners\n\n"
            "<:girlsheaven:1400671165885710386> **| Girls Roles**\n"
            "⇝ Express Your Personality With Roles Designed Especially For Girls\n\n"
            "<:removeheaven:1400671588935798815> **| Remove 1 Of Your Roles**\n"
            "⇝ Get Rid Of That Cringe Role You Picked At 3AM\n\n"
            "-# **`© 2026 Moon Night™. All rights reserved.`**"
        ),
        color=EMBED_COLOR
    )
    await interaction.channel.send(embed=embed, view=RoleRequestView())
    await interaction.response.send_message("✅ Role Request panel sent!", ephemeral=True)


# ==========================================
# 2. BOT COMMANDS & MUSIC (ALL SLASH COMMANDS)
# ==========================================
ytdl_opts = {'format': 'bestaudio/best', 'quiet': True, 'default_search': 'auto', 'source_address': '0.0.0.0'}
ffmpeg_opts = {'options': '-vn'}
ytdl = yt_dlp.YoutubeDL(ytdl_opts)

@bot.tree.command(name="join", description="Make bot join your voice channel")
async def slash_join(interaction: Interaction):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Khasak tkon f voice channel b3da!", ephemeral=True)
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.move_to(channel)
        return await interaction.response.send_message(f"✅ T7awelt l: **{channel.name}**")
    await channel.connect()
    await interaction.response.send_message(f"📢 Dkhalt l: **{channel.name}**")

@bot.tree.command(name="leave", description="Make bot leave voice channel")
async def slash_leave(interaction: Interaction):
    if interaction.guild.voice_client:
        await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("👋 Kherjt mn l-voice channel.")
    else:
        await interaction.response.send_message("❌ Mamshtarekh f ta voice channel.", ephemeral=True)

@bot.tree.command(name="play", description="Play a song from YouTube")
@app_commands.describe(search="Song name or URL")
async def slash_play(interaction: Interaction, search: str):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Khasak tkon f voice channel!", ephemeral=True)
    
    await interaction.response.defer()
    if not interaction.guild.voice_client:
        await interaction.user.voice.channel.connect()

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(f"ytsearch:{search}", download=False))
    if 'entries' in data:
        data = data['entries'][0]
    url = data['url']
    title = data['title']
    
    vc = interaction.guild.voice_client
    if vc.is_playing():
        vc.stop()
    vc.play(discord.FFmpegPCMAudio(url, **ffmpeg_opts))
    
    await interaction.followup.send(f"🎵 Playing: **{title}**")

@bot.tree.command(name="stop", description="Stop current music")
async def slash_stop(interaction: Interaction):
    vc = interaction.guild.voice_client
    if vc and vc.is_playing():
        vc.stop()
        await interaction.response.send_message("🛑 Music stopped.")
    else:
        await interaction.response.send_message("❌ Walou khdam daba.", ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")

@bot.tree.command(name="warn", description="Warn a member")
@app_commands.describe(member="Member to warn", reason="Reason for warning")
@is_owner_or_admin_slash()
async def slash_warn(interaction: Interaction, member: discord.Member, reason: str = "No reason"):
    await interaction.response.send_message(f"⚠️ **{member.name}** t3tato inndar! Sabab: {reason}")

@bot.tree.command(name="unjail", description="Unjail a member")
@app_commands.describe(member="Member to unjail")
@is_owner_or_admin_slash()
async def slash_unjail(interaction: Interaction, member: discord.Member):
    await interaction.response.send_message(f"🔓 **{member.name}** kherj mn l-jail.")

@bot.tree.command(name="vcmute", description="Mute a member in voice channel")
@app_commands.describe(member="Member to mute")
@is_owner_or_admin_slash()
async def slash_vcmute(interaction: Interaction, member: discord.Member):
    if member.voice:
        await member.edit(mute=True)
        await interaction.response.send_message(f"🔇 {member.mention} t-muta f voice.")
    else:
        await interaction.response.send_message("❌ Hada makaynch f voice!", ephemeral=True)

@bot.tree.command(name="about", description="About Moon Night Bot")
async def slash_about(interaction: Interaction):
    await interaction.response.send_message("🌙 Moon Night Bot - Custom Moderation & Utility Bot.", ephemeral=True)


# ==========================================
# 3. ON READY EVENT
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user.name} ({bot.user.id})")
    print(f"🔒 Owner ID: {OWNER_ID}")

bot.run(BOT_TOKEN)
