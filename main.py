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
JAIL_ROLE_ID = int(os.getenv("JAIL_ROLE_ID", "1482902118137462896")) # Bdl id d jail role ila bghiti

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

def is_owner_or_admin_slash():
    async def predicate(interaction: Interaction):
        if interaction.user.id == OWNER_ID or interaction.user.guild_permissions.administrator:
            return True
        await interaction.response.send_message("❌ Had l-command khas b Owners/Admins ghir!", ephemeral=True)
        return False
    return app_commands.check(predicate)


# ==========================================
# 1. PANELS & VIEWS
# ==========================================

# --- SOCIALS PANEL (B SERVER ICON LI FIHA L-CADRE L-AHMAR) ---
class SocialsView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="Instagram", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Tiktok", style=ButtonStyle.link, url="https://tiktok.com"))
        self.add_item(Button(label="IG Group", style=ButtonStyle.link, url="https://instagram.com"))
        self.add_item(Button(label="Store", style=ButtonStyle.link, url="https://store.moonnight.com"))

def get_socials_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="Hey @everyone",
        description=(
            "-# > 𝗦𝘁𝗮𝘆 𝗰𝗼𝗻𝗻𝗲𝗰𝘁𝗲𝗱 𝘄𝗶𝘁𝗵 **𝗠𝗼𝗼𝗻 𝗡𝗶𝗴𝗵𝘁** 𝗼𝗻 𝗮𝗹𝗹 𝗼𝘂𝗿 𝗽𝗹𝗮𝘁𝗳𝗼𝗿𝗺𝘀.\n\n"
            "### * **Instagram :** ***Follow us for news & highlights.***\n"
            "### * **TikTok :** ***Follow us for videos & updates***\n"
            "### * **IG Group :** ***Stay close to the community.***\n"
            "### * **Store :** ***Shop exclusive Moon Night items.***\n\n"
            "-# 𝑴𝒐𝒐𝒏 𝑵𝒊𝒈𝒉𝒕 𝑾𝒉𝒆𝒓𝒆 𝑴𝒐𝒎𝒆𝒏𝒕𝒔 𝑩𝒆𝒄𝒐𝒎𝒆 𝑴𝒆𝒎𝒐𝒓𝒊𝒆𝒔"
        ),
        color=EMBED_COLOR
    )
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed


# --- RULES PANEL ---
class RulesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(Button(label="• Join Need Help!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))
        self.add_item(Button(label="• Open A Ticket!", style=ButtonStyle.link, url="https://discord.com/channels/1482902524376780932"))

def get_rules_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="• Moon Night : Rules •",
        description=(
            "> To make Sure everyone enjoy, please follow those guidelines :\n\n"
            "➔ Follow the [Discord TOS](https://dis.gd/tos) and The [Discord Community Guidelines](https://dis.gd/guidelines)\n"
            "➔ **Aya NSFW content f server = jail**\n"
            "➔ **Respect aya member f server, kifma kan!**\n"
            "➔ **Abusing any power treportat biha b preuve = warn ⇝ remove role**\n"
            "➔ **Need help daret bach it7alo lmachakil, machi bach trolli, troll f nh = blacklist n.h.**\n"
            "➔ **Sbek chi wahd 3ndo role (staff, high role, admin...) matseboch, tla3 need help reporti bih, ghadi itremova lih role**\n"
            "➔ **Staff provoque 3liha punishment**\n\n"
            "-# `© 2026 Moon Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    if guild and guild.icon:
        embed.set_image(url=guild.icon.url)
    return embed


# --- SELF ROLES PANEL (HYDNA MNHA PROFIL D SRV F L-BQYIN) ---
class SelfRolesGamesSelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Valorant", emoji="🎮", value="1482902155219304549"),
            discord.SelectOption(label="GTA V / Grand RP", emoji="🚗", value="1482902157324849333"),
            discord.SelectOption(label="League of Legends", emoji="⚔️", value="1515406788395008170")
        ]
        super().__init__(placeholder="Select A Games Role!", options=options, custom_id="self_game_select")

    async def callback(self, interaction: Interaction):
        role_id = int(self.values[0])
        role = interaction.guild.get_role(role_id)
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed role: **{role.name}**", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Added role: **{role.name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Role malkahch f server!", ephemeral=True)

class SelfRolesView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(SelfRolesGamesSelect())

    async def toggle_role(self, interaction: Interaction, role_id: int):
        role = interaction.guild.get_role(role_id)
        if role:
            if role in interaction.user.roles:
                await interaction.user.remove_roles(role)
                await interaction.response.send_message(f"❌ Removed role: **{role.name}**", ephemeral=True)
            else:
                await interaction.user.add_roles(role)
                await interaction.response.send_message(f"✅ Added role: **{role.name}**", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Role malkahch f server!", ephemeral=True)

    @discord.ui.button(label="• Heartless", style=ButtonStyle.secondary, custom_id="role_heartless")
    async def btn_heartless(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902118137462896)

    @discord.ui.button(label="• Taken", style=ButtonStyle.secondary, custom_id="role_taken")
    async def btn_taken(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902117693001898)

    @discord.ui.button(label="• Single", style=ButtonStyle.secondary, custom_id="role_single")
    async def btn_single(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902116858331217)

    @discord.ui.button(label="• Female", style=ButtonStyle.secondary, custom_id="role_female", row=1)
    async def btn_female(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902047236952117)

    @discord.ui.button(label="• Male", style=ButtonStyle.secondary, custom_id="role_male", row=1)
    async def btn_male(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902046653943870)

    @discord.ui.button(label="• Trans", style=ButtonStyle.secondary, custom_id="role_trans", row=1)
    async def btn_trans(self, interaction: Interaction, button: Button):
        await self.toggle_role(interaction, 1482902043558547650)

def get_selfroles_embeds(guild: discord.Guild):
    embed1 = discord.Embed(
        title=":11pm_redflower: : Situation Roles ÷",
        description="### What's your actual situation?\n@Heartless\n@Taken\n@Single",
        color=EMBED_COLOR
    )
    if guild and guild.icon:
        embed1.set_thumbnail(url=guild.icon.url) # Ghi f lowel

    embed2 = discord.Embed(
        title=":gendersheaven: : Gender Roles ÷",
        description="### What's your gender?\n@Female\n@Male\n@Trans",
        color=EMBED_COLOR
    )

    embed3 = discord.Embed(
        title=":game: : Games Roles ÷",
        description="### Do you play any games?",
        color=EMBED_COLOR
    )
    return [embed1, embed2, embed3]


# --- ROLE REQUEST PANEL (B ACCEPT / REFUSE WORKFLOW) ---
class RoleRequestActionView(View):
    def __init__(self, user_id: int, category: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.category = category

    @discord.ui.button(label="Accept", style=ButtonStyle.green, custom_id="req_accept_btn")
    async def accept_btn(self, interaction: Interaction, button: Button):
        guild = interaction.guild
        user = guild.get_member(self.user_id)
        
        role_mapping = {
            "req_powers": 1482902118137462896,
            "req_special": 1482902117693001898,
            "req_special2": 1482902116858331217,
            "req_girls": 1482902047236952117
        }
        role_id = role_mapping.get(self.category)
        if user and role_id:
            role = guild.get_role(role_id)
            if role:
                await user.add_roles(role)

        if user:
            try:
                await user.send(f"✅ Your role request for `{self.category}` has been **accepted** by {interaction.user.mention}!")
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

class RoleRequestCategorySelect(Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Powers", description="Special Functionalities", emoji="⚡", value="req_powers"),
            discord.SelectOption(label="Special Roles", description="Showcase Your Identity", emoji="💎", value="req_special"),
            discord.SelectOption(label="Special Roles 2", description="Given By Owners", emoji="🎩", value="req_special2"),
            discord.SelectOption(label="Girls Roles", description="Designed Especially For Girls", emoji="🌸", value="req_girls"),
            discord.SelectOption(label="Remove 1 Of Your Roles", description="Get Rid Of Cringe Roles", emoji="⭐", value="req_remove")
        ]
        super().__init__(placeholder="Select A Role Category", options=options, custom_id="role_req_select")

    async def callback(self, interaction: Interaction):
        category = self.values[0]
        log_channel = interaction.guild.get_channel(LOG_CHANNEL_ID)
        embed = discord.Embed(title="📥 New Role Request", description=f"Category: `{category}`", color=EMBED_COLOR)
        embed.add_field(name="User", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        view = RoleRequestActionView(user_id=interaction.user.id, category=category)
        if log_channel:
            await log_channel.send(embed=embed, view=view)
        await interaction.response.send_message(f"📩 Request category `{category}` has been sent to admins!", ephemeral=True)

class RoleRequestView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleRequestCategorySelect())

def get_rolerequest_embed():
    embed = discord.Embed(
        title="💦 You've Officially Unlocked The Right To Beg For Some Fancy Roles :",
        description=(
            "⚡ | **Powers**\n➔ Unlock Special Functionalities And Privileges\n\n"
            "💎 | **Special Roles**\n➔ Showcase Your Identity With Distinctive Roles\n\n"
            "🎩 | **Special Roles 2 (Only Given By Owners)**\n➔ Exclusive Titles Assigned By Owners\n\n"
            "🌸 | **Girls Roles**\n➔ Express Your Personality With Girls Roles\n\n"
            "⭐ | **Remove 1 Of Your Roles**\n➔ Get Rid Of That Cringe Role\n\n"
            "-# `© 2026 Moon Night™. All rights reserved.`"
        ),
        color=EMBED_COLOR
    )
    return embed


# --- MAP GUIDE & STAFF APPLY PANELS ---
def get_map_guide_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="🗺️ Moon Night - Server Map & Guide",
        description=(
            "Welcome to **Moon Night**! Navigate the server easily:\n\n"
            "📌 **#rules** - Read guidelines\n"
            "🎭 **#self-roles** - Get profile roles\n"
            "💬 **#general** - Chat with members\n"
            "🔊 **Voice** - Temporary VC"
        ),
        color=EMBED_COLOR
    )
    if guild and guild.icon:
        embed.set_image(url=guild.icon.url)
    return embed

class StaffApplyView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Apply for Staff", style=ButtonStyle.success, custom_id="btn_apply_staff")
    async def apply_staff(self, interaction: Interaction, button: Button):
        await interaction.response.send_message("📝 Staff application form coming soon!", ephemeral=True)

def get_staff_apply_embed(guild: discord.Guild):
    embed = discord.Embed(
        title="Staff Apply For Moon Night ©",
        description="Accepting staff applications! Join our team and grow with us.\n\n**• Staff Requirements:** Active & 17+",
        color=EMBED_COLOR
    )
    if guild and guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    return embed


# ==========================================
# 2. COMMAND SENDER PANEL
# ==========================================
@bot.tree.command(name="send_panel", description="Send Moon Night panels")
@app_commands.choices(panel=[
    app_commands.Choice(name="Rules", value="rules"),
    app_commands.Choice(name="Self Roles", value="selfroles"),
    app_commands.Choice(name="Role Request", value="rolerequest"),
    app_commands.Choice(name="Staff Apply", value="staffapply"),
    app_commands.Choice(name="Map Guide", value="mapguide"),
    app_commands.Choice(name="Socials", value="socials")
])
@is_owner_or_admin_slash()
async def send_panel(interaction: Interaction, panel: str):
    await interaction.response.defer(ephemeral=True)
    if panel == "rules":
        await interaction.channel.send(embed=get_rules_embed(interaction.guild), view=RulesView())
    elif panel == "selfroles":
        await interaction.channel.send(embeds=get_selfroles_embeds(interaction.guild), view=SelfRolesView())
    elif panel == "rolerequest":
        await interaction.channel.send(embed=get_rolerequest_embed(), view=RoleRequestView())
    elif panel == "staffapply":
        await interaction.channel.send(embed=get_staff_apply_embed(interaction.guild), view=StaffApplyView())
    elif panel == "mapguide":
        await interaction.channel.send(embed=get_map_guide_embed(interaction.guild))
    elif panel == "socials":
        await interaction.channel.send(embed=get_socials_embed(interaction.guild), view=SocialsView())
    
    await interaction.followup.send(f"✅ Panel **{panel}** sent successfully!", ephemeral=True)


# ==========================================
# 3. MODERATION & VOICE SLASH COMMANDS
# ==========================================

@bot.tree.command(name="mute", description="Mute a member in text/chat (Add Jail role)")
@app_commands.describe(member="Member to mute")
@is_owner_or_admin_slash()
async def slash_mute(interaction: Interaction, member: discord.Member):
    role = interaction.guild.get_role(JAIL_ROLE_ID)
    if role:
        await member.add_roles(role)
        await interaction.response.send_message(f"🔇 **{member.name}** t-muta (t-jata w ma b9ach ki9dr ykteb).")
    else:
        await interaction.response.send_message("❌ Jail Role ID makaynch wla ghalat f configuration!", ephemeral=True)

@bot.tree.command(name="unmute", description="Unmute a member from jail")
@app_commands.describe(member="Member to unmute")
@is_owner_or_admin_slash()
async def slash_unmute(interaction: Interaction, member: discord.Member):
    role = interaction.guild.get_role(JAIL_ROLE_ID)
    if role and role in member.roles:
        await member.remove_roles(role)
        await interaction.response.send_message(f"🔊 **{member.name}** t-unmuta (kherj mn jail).")
    else:
        await interaction.response.send_message("❌ Had l-member mashi f jail wla role makaynch.", ephemeral=True)

@bot.tree.command(name="disconnect", description="Disconnect a member from voice channel")
@app_commands.describe(member="Member to disconnect")
@is_owner_or_admin_slash()
async def slash_disconnect(interaction: Interaction, member: discord.Member):
    if member.voice:
        await member.move_to(None)
        await interaction.response.send_message(f"🔌 **{member.name}** t-twa hrg mn voice channel.")
    else:
        await interaction.response.send_message("❌ Had l-member makaynch f ta voice channel!", ephemeral=True)

@bot.tree.command(name="move", description="Move a member to your voice channel")
@app_commands.describe(member="Member to move")
@is_owner_or_admin_slash()
async def slash_move(interaction: Interaction, member: discord.Member):
    if not interaction.user.voice:
        return await interaction.response.send_message("❌ Khasak tkon f voice channel b3da!", ephemeral=True)
    if not member.voice:
        return await interaction.response.send_message("❌ Had l-member makaynch f voice channel!", ephemeral=True)
    
    channel = interaction.user.voice.channel
    await member.move_to(channel)
    await interaction.response.send_message(f"📥 T-movi **{member.name}** l voice dyalk: **{channel.name}**")

@bot.tree.command(name="vcmute", description="Mute member in voice")
@app_commands.describe(member="Member to vc mute")
@is_owner_or_admin_slash()
async def slash_vcmute(interaction: Interaction, member: discord.Member):
    if member.voice:
        await member.edit(mute=True)
        await interaction.response.send_message(f"🔇 {member.mention} t-muta f voice.")
    else:
        await interaction.response.send_message("❌ Makaynch f voice!", ephemeral=True)

@bot.tree.command(name="vcunmute", description="Unmute member in voice")
@app_commands.describe(member="Member to vc unmute")
@is_owner_or_admin_slash()
async def slash_vcunmute(interaction: Interaction, member: discord.Member):
    if member.voice:
        await member.edit(mute=False)
        await interaction.response.send_message(f"🔊 {member.mention} t-unmuta f voice.")
    else:
        await interaction.response.send_message("❌ Makaynch f voice!", ephemeral=True)

@bot.tree.command(name="ping", description="Check bot latency")
async def slash_ping(interaction: Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`")


# ==========================================
# 4. BOT ON READY
# ==========================================
@bot.event
async def on_ready():
    print(f"✅ Bot Online: {bot.user.name} ({bot.user.id})")
    print(f"🔒 Owner ID: {OWNER_ID}")

bot.run(BOT_TOKEN)
