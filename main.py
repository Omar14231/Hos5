import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from flask import Flask
from threading import Thread

# ==========================================
# 1. Keep-Alive Web Server (Render Fix)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Active and Running!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 2. Hardcoded IDs & Emojis
# ==========================================
OWNER_ID = 1306034100544737461

# Military Roles
ROLE_ON_DUTY = 1520077188135780494
ROLE_OFF_DUTY = 1520084329714421800

# Registration & Citizen Roles
ROLE_NEWCOMER = 1520087730544050436
ROLE_CITIZEN = 1474724032849907722
ROLE_MALE = 1476903628714410079
ROLE_FEMALE = 1476903782112821258

# Economy / Survival Roles
ROLE_MERCHANT = 1520153220100522126
ROLE_STARVED = 1520075245308874853

# Emojis
EMOJI_WARN_1 = "<a:emoji_26:1520109726065496295>"
EMOJI_WARN_2 = "<a:emoji_28:1520109788485128202>"
EMOJI_LOADING = "<a:emoji_26:1520109763952771204>"

# Items & Stats Dictionary
ITEMS_DB = {
    "Burger": {"hunger": 50, "thirst": 0},
    "Water": {"hunger": 0, "thirst": 30},
    "Juice": {"hunger": 0, "thirst": 20},
    "Pizza": {"hunger": 40, "thirst": 0},
    "Strawberry": {"hunger": 5, "thirst": 3},
    "Candy": {"hunger": 10, "thirst": 0},
    "Sweet": {"hunger": 10, "thirst": 0},
    "Apple": {"hunger": 15, "thirst": 15},
    "Pepsi": {"hunger": 0, "thirst": 35},
    "7Up": {"hunger": 0, "thirst": 35},
    "Citrus": {"hunger": 0, "thirst": 35},
    "Dew": {"hunger": 0, "thirst": 35},
    "Meal": {"hunger": 100, "thirst": 0}
}

# ==========================================
# 3. Bot Setup & Intents (Fix 1)
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=["-", "!"], intents=intents)

# In-Memory Database (For a real server, consider migrating this to a JSON file or SQLite later)
db = {
    "users": {},
    "used_phones": set(),
    "live_log_msg": None, # (channel_id, message_id)
    "warnings": []
}

def get_user_data(user_id):
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "identity": None,
            "hunger": 100,
            "thirst": 100,
            "inventory": {},
            "warnings_count": 0
        }
    return db["users"][user_id]

# ==========================================
# 4. Core Bot Events & Tasks
# ==========================================
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")
    
    if not survival_loop.is_running():
        survival_loop.start()

@tasks.loop(hours=1)
async def survival_loop():
    """Decreases Hunger and Thirst by 50% every hour for active users."""
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            # Checking if active (Online or on Duty)
            is_active = str(member.status) != "offline" or member.get_role(ROLE_ON_DUTY)
            if is_active:
                u_data = get_user_data(member.id)
                u_data["hunger"] = max(0, u_data["hunger"] - 50)
                u_data["thirst"] = max(0, u_data["thirst"] - 50)
                
                # Penalties
                h, t = u_data["hunger"], u_data["thirst"]
                if h == 0 or t == 0:
                    try:
                        # Strip roles except gender
                        roles_to_keep = [guild.default_role]
                        if member.get_role(ROLE_MALE): roles_to_keep.append(guild.get_role(ROLE_MALE))
                        if member.get_role(ROLE_FEMALE): roles_to_keep.append(guild.get_role(ROLE_FEMALE))
                        
                        starved_role = guild.get_role(ROLE_STARVED)
                        if starved_role: roles_to_keep.append(starved_role)
                        
                        await member.edit(roles=roles_to_keep)
                        
                        owner = await bot.fetch_user(OWNER_ID)
                        await owner.send(f"⚠️ User {member.mention} ({member.id}) has starved to death while online.")
                    except:
                        pass
                elif (h <= 15 or t <= 15):
                    try: await member.send("🚨 **CRITICAL WARNING:** Your hunger/thirst is at 15% or below! Eat/drink immediately or you will die!")
                    except: pass
                elif (h <= 25 or t <= 25):
                    try: await member.send("⚠️ **WARNING:** Your hunger/thirst is at 25% or below. Find food or water soon.")
                    except: pass

async def update_live_log():
    if not db["live_log_msg"]: return
    channel_id, msg_id = db["live_log_msg"]
    try:
        channel = bot.get_channel(channel_id)
        msg = await channel.fetch_message(msg_id)
        
        guild = channel.guild
        on_duty_role = guild.get_role(ROLE_ON_DUTY)
        
        lines = ["**Live Military Duty Log**"]
        for member in guild.members:
            if member.get_role(ROLE_ON_DUTY) or member.get_role(ROLE_OFF_DUTY):
                status = "🟢" if on_duty_role in member.roles else "🔴"
                lines.append(f"{member.display_name} {status}")
                
        embed = discord.Embed(title="Military Duty Status", description="\n".join(lines), color=discord.Color.blue())
        await msg.edit(embed=embed)
    except:
        pass

# ==========================================
# 5. UI Views (Buttons)
# ==========================================
class DutyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Duty On/Off", style=discord.ButtonStyle.success, custom_id="toggle_duty")
    async def toggle_duty(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        on_duty = member.guild.get_role(ROLE_ON_DUTY)
        off_duty = member.guild.get_role(ROLE_OFF_DUTY)
        
        if on_duty in member.roles:
            await member.remove_roles(on_duty)
            if off_duty: await member.add_roles(off_duty)
            await interaction.response.send_message("You are now OFF duty.", ephemeral=True)
        elif off_duty in member.roles:
            await member.remove_roles(off_duty)
            if on_duty: await member.add_roles(on_duty)
            await interaction.response.send_message("You are now ON duty.", ephemeral=True)
        else:
            await interaction.response.send_message("You don't have military roles.", ephemeral=True)
            
        await update_live_log()

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Verify / Continue", style=discord.ButtonStyle.primary, custom_id="verify_start")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
        
        if newcomer_role not in member.roles:
            return await interaction.response.send_message("You are already registered or do not have the Newcomer role.", ephemeral=True)
            
        await interaction.response.send_message("Check your DMs to continue registration.", ephemeral=True)
        
        # Start DM Flow
        try:
            await member.send("Welcome to Rollback Server. Do you want to create an identity? (Yes/No)")
            def check(m): return m.author == member and isinstance(m.channel, discord.DMChannel)
            
            resp1 = await bot.wait_for('message', check=check, timeout=120)
            if resp1.content.lower() not in ['yes', 'y']:
                return await member.send("Registration cancelled.")

            await member.send("Enter your real or fake name (e.g., Abu Ahmed):")
            name_msg = await bot.wait_for('message', check=check, timeout=120)
            name = name_msg.content

            phone = ""
            while True:
                await member.send("Enter a fake phone number starting with 17 (e.g., 17XXXXX):")
                phone_msg = await bot.wait_for('message', check=check, timeout=120)
                phone_input = phone_msg.content.strip()
                if phone_input.startswith("17") and len(phone_input) >= 6 and phone_input not in db["used_phones"]:
                    phone = phone_input
                    db["used_phones"].add(phone)
                    break
                else:
                    await member.send("Invalid number. Must start with 17, have correct length, and not be taken.")

            await member.send("Are you Male or Female? (Type 'Male' or 'Female')")
            gender = ""
            while True:
                gender_msg = await bot.wait_for('message', check=check, timeout=120)
                g_input = gender_msg.content.lower()
                if g_input in ['male', 'female']:
                    gender = g_input.capitalize()
                    break
                await member.send("Please reply with either 'Male' or 'Female'.")

            # Finalize
            u_data = get_user_data(member.id)
            u_data["identity"] = {"name": name, "phone": phone, "gender": gender, "nationality": "Citizen"}
            
            await member.remove_roles(newcomer_role)
            citizen_role = member.guild.get_role(ROLE_CITIZEN)
            gender_role = member.guild.get_role(ROLE_MALE if gender == "Male" else ROLE_FEMALE)
            
            roles_to_add = [r for r in [citizen_role, gender_role] if r]
            await member.add_roles(*roles_to_add)
            
            await member.send(f"✅ Registration complete! Welcome to the city, {name}.")
            
        except asyncio.TimeoutError:
            await member.send("Registration timed out. Please click the button in the server again.")
        except discord.Forbidden:
            pass # Cannot DM user

# ==========================================
# 6. Admin & Military Commands
# ==========================================
@bot.command()
async def role(ctx, member: discord.Member = None, role: discord.Role = None):
    if not ctx.author.guild_permissions.manage_roles and ctx.author.id != OWNER_ID:
        return
    if member is None or role is None:
        return await ctx.send("Syntax error. Use: `-role @user @role`")
        
    if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.ban_members:
        return await ctx.send("❌ You are trying to give a very powerful role. Operation cancelled.")

    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"Removed {role.name} from {member.display_name}.")
        else:
            await member.add_roles(role)
            await ctx.send(f"Added {role.name} to {member.display_name}.")
    except Exception as e:
        await ctx.send("Failed to update role. Check my hierarchy permissions.")

@bot.tree.command(name="delete_identity", description="Owner Only. Strips roles and sets to Registration Phase.")
async def delete_identity(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ This command is restricted to the Owner.", ephemeral=True)

    guild = interaction.guild
    newcomer_role = guild.get_role(ROLE_NEWCOMER)
    
    roles_to_keep = [guild.default_role]
    await member.edit(roles=roles_to_keep)
    if newcomer_role:
        await member.add_roles(newcomer_role)
    
    # Reset Data
    if member.id in db["users"]:
        phone = db["users"][member.id].get("identity", {}).get("phone")
        if phone in db["used_phones"]: db["used_phones"].remove(phone)
        del db["users"][member.id]
        
    await interaction.response.send_message(f"Identity deleted for {member.mention}. They are back in Registration Phase.")

# ==========================================
# 7. Warning System
# ==========================================
@bot.tree.command(name="warn", description="Warn a user.")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided."):
    if not interaction.user.guild_permissions.kick_members and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("No permission.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} Processing warning...")
    
    u_data = get_user_data(member.id)
    u_data["warnings_count"] += 1
    db["warnings"].insert(0, f"{member.display_name} - {reason}")
    
    # Edit original response
    await interaction.edit_original_response(content=f"{EMOJI_WARN_1} {member.mention} has been warned by {interaction.user.mention}. Reason: {reason} {EMOJI_WARN_2}")
    
    try:
        await member.send(f"Dear {member.display_name},\n\nYou have received a formal warning in Rollback Server.\n**Issued by:** {interaction.user.display_name}\n**Reason:** {reason}\n\nPlease ensure you read the rules carefully to avoid further penalties.")
    except:
        pass

@bot.tree.command(name="remove_warn", description="Delete all warnings for a user.")
async def remove_warn(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.kick_members and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("No permission.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    u_data["warnings_count"] = 0
    await interaction.response.send_message(f"All warnings removed for {member.mention}.")

@bot.command()
async def warnings(ctx, member: discord.Member = None):
    if member:
        count = get_user_data(member.id)["warnings_count"]
        await ctx.send(f"{member.display_name} has {count} warnings.")
    else:
        if not db["warnings"]:
            return await ctx.send("No warnings found.")
        recent = db["warnings"][:10]
        embed = discord.Embed(title="Global Warnings (Last 10)", description="\n".join(recent), color=discord.Color.red())
        await ctx.send(embed=embed)

# ==========================================
# 8. Start Commands (Duty & Registration)
# ==========================================
@bot.command()
async def start1(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="Military Duty Station", description="Click the button below to toggle your Duty Status.", color=discord.Color.green())
    await ctx.send(embed=embed, view=DutyView())

@bot.command()
async def start2(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="Military Duty Status", description="Initializing...", color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    db["live_log_msg"] = (ctx.channel.id, msg.id)
    await update_live_log()

@bot.command()
async def start3(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    embed = discord.Embed(title="Registration & Immigration", description="Welcome! Click the button below to verify and create your identity.", color=discord.Color.gold())
    await ctx.send(embed=embed, view=RegistrationView())

@bot.tree.command(name="identity", description="Check a user's identity.")
async def identity(interaction: discord.Interaction, member: discord.Member):
    u_data = get_user_data(member.id)
    idt = u_data.get("identity")
    if not idt:
        return await interaction.response.send_message("This user has no registered identity.", ephemeral=True)
        
    embed = discord.Embed(title=f"ID Card: {idt['name']}", color=discord.Color.dark_theme())
    embed.add_field(name="Phone", value=idt['phone'], inline=True)
    embed.add_field(name="Gender", value=idt['gender'], inline=True)
    embed.add_field(name="Nationality", value=idt['nationality'], inline=True)
    await interaction.response.send_message(embed=embed)

# ==========================================
# 9. Survival, Inventory & Store
# ==========================================
@bot.command()
async def inventory(ctx):
    u_data = get_user_data(ctx.author.id)
    h = u_data["hunger"]
    t = u_data["thirst"]
    
    def get_bar(val):
        filled = int((val / 100) * 10)
        return "🟩" * filled + "🟥" * (10 - filled)
        
    embed = discord.Embed(title=f"🎒 {ctx.author.display_name}'s Inventory", color=discord.Color.orange())
    embed.add_field(name="Hunger (Orange)", value=f"{h}% {get_bar(h)}", inline=False)
    embed.add_field(name="Thirst (Blue)", value=f"{t}% {get_bar(t)}", inline=False)
    
    inv = u_data["inventory"]
    items_str = "\n".join([f"**{item}**: {count}" for item, count in inv.items() if count > 0])
    if not items_str: items_str = "Empty"
    
    embed.add_field(name="Items", value=items_str, inline=False)
    embed.set_footer(text="Use '-consume [Item]' to eat/drink, or '-give [Item] @user' to transfer.")
    
    # Note: Using ctx.send but as a normal message since -commands aren't natively ephemeral.
    # To mimic ephemeral for text commands, we DM or delete. Here we will send and delete after 30s.
    await ctx.send(embed=embed, delete_after=30.0)
    try: await ctx.message.delete()
    except: pass

@bot.command()
async def consume(ctx, item_name: str):
    u_data = get_user_data(ctx.author.id)
    item_name = item_name.capitalize()
    
    if u_data["inventory"].get(item_name, 0) <= 0:
        return await ctx.send("You don't have this item in your inventory.")
        
    if item_name not in ITEMS_DB:
        return await ctx.send("Invalid item.")
        
    # Consume
    u_data["inventory"][item_name] -= 1
    if u_data["inventory"][item_name] == 0:
        del u_data["inventory"][item_name]
        
    stats = ITEMS_DB[item_name]
    u_data["hunger"] = min(100, u_data["hunger"] + stats["hunger"])
    u_data["thirst"] = min(100, u_data["thirst"] + stats["thirst"])
    
    await ctx.send(f"🍽️ {ctx.author.mention} consumed {item_name}. Hunger/Thirst stats replenished!")

@bot.command()
async def give(ctx, item_name: str, member: discord.Member):
    u_data = get_user_data(ctx.author.id)
    item_name = item_name.capitalize()
    
    if u_data["inventory"].get(item_name, 0) <= 0:
        return await ctx.send("You don't have this item to give.")
        
    msg = await ctx.send(f"Are you sure you want to give {item_name} to {member.mention}? (Yes/No)")
    
    def check(m): return m.author == ctx.author and m.channel == ctx.channel
    try:
        resp = await bot.wait_for('message', check=check, timeout=30.0)
        if resp.content.lower() in ['yes', 'y']:
            u_data["inventory"][item_name] -= 1
            if u_data["inventory"][item_name] == 0: del u_data["inventory"][item_name]
            
            target_data = get_user_data(member.id)
            target_data["inventory"][item_name] = target_data["inventory"].get(item_name, 0) + 1
            await ctx.send(f"✅ Successfully gave 1x {item_name} to {member.mention}.")
        else:
            await ctx.send("Transfer cancelled.")
    except asyncio.TimeoutError:
        await ctx.send("Transfer timed out.")

@bot.tree.command(name="full", description="Owner Only. Instantly refills hunger and thirst to 100%.")
async def full(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ This command is restricted to the Owner.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    u_data["hunger"] = 100
    u_data["thirst"] = 100
    await interaction.response.send_message(f"Stats refilled to 100% for {member.mention}.")

@bot.tree.command(name="menu", description="Displays the store menu.")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 Store Menu", color=discord.Color.purple())
    for item, stats in ITEMS_DB.items():
        desc = []
        if stats["hunger"] > 0: desc.append(f"+{stats['hunger']} Hunger")
        if stats["thirst"] > 0: desc.append(f"+{stats['thirst']} Thirst")
        embed.add_field(name=item, value=", ".join(desc), inline=True)
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sell", description="Merchant Only. Sells/Transfers an item to a user.")
async def sell(interaction: discord.Interaction, item: str, member: discord.Member):
    merchant_role = interaction.guild.get_role(ROLE_MERCHANT)
    if merchant_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ Only Merchants can use this command.", ephemeral=True)
        
    item = item.capitalize()
    if item not in ITEMS_DB:
        return await interaction.response.send_message("❌ Invalid item. Check `/menu`.", ephemeral=True)
        
    t_data = get_user_data(member.id)
    t_data["inventory"][item] = t_data["inventory"].get(item, 0) + 1
    
    await interaction.response.send_message(f"✅ Successfully transferred 1x {item} to {member.mention}'s inventory.")

# ==========================================
# 10. Startup
# ==========================================
if __name__ == "__main__":
    keep_alive()  # Starts the background web server
    # Load Token Securely via Environment Variable
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("ERROR: DISCORD_TOKEN environment variable not set.")
    else:
        bot.run(TOKEN)
