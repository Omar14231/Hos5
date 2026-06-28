import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
import json
import time
from flask import Flask
from threading import Thread

# ==========================================
# 1. خادم الويب (لحل مشكلة السبات في Render)
# =========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل بنجاح! - سيرفر رولباك"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 2. الايديات والرتب (Hardcoded)
# ==========================================
OWNER_ID = 1306034100544737461
BACKUP_CHANNEL_ID = 1520532277795356742 # روم الحفظ والداتا
LOG_CHANNEL_ID = 1520583906305507388    # روم سجل السجلات

# رتب العسكر والتدريب
ROLE_ON_DUTY = 1520077188135780494
ROLE_OFF_DUTY = 1520084329714421800
ROLE_TRAINEE = 1520079957811003582
ROLE_TRAINER = 1520079854413021375
ROLE_MILITARY = 1520077188135780494
ROLE_SOLDIER = 1520407218753769492
ROLE_ENTER = 1520078078817341500
ROLE_VERIFIED = 1520078137902497922
ROLE_JAIL = 1520075299159801917

# رتب التسجيل والمواطنين
ROLE_NEWCOMER = 1520087730544050436
ROLE_CITIZEN = 1474724032849907722
ROLE_MALE = 1476903628714410079
ROLE_FEMALE = 1476903782112821258
CHANNEL_WELCOME = 1520074304447053915

# رتب الاقتصاد والبقاء
ROLE_MERCHANT = 1520153220100522126
ROLE_DEAD = 1520075245308874853

# الاغراض والمخزون
ITEMS_DB = {
    "برجر": {"hunger": 50, "thirst": 0},
    "ماء": {"hunger": 0, "thirst": 30},
    "عصير": {"hunger": 0, "thirst": 20},
    "بيتزا": {"hunger": 40, "thirst": 0},
    "فراوله": {"hunger": 5, "thirst": 3},
    "حلوه": {"hunger": 10, "thirst": 0},
    "تفاح": {"hunger": 15, "thirst": 15},
    "ببسي": {"hunger": 0, "thirst": 35},
    "سفن اب": {"hunger": 0, "thirst": 35},
    "حمضيات": {"hunger": 0, "thirst": 35},
    "ديو": {"hunger": 0, "thirst": 35},
    "وجبه": {"hunger": 100, "thirst": 0}
}

# ==========================================
# 3. إعدادات البوت وقاعدة البيانات (Persistence)
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=["-", "!"], intents=intents)

db = {
    "users": {},
    "used_phones": set(),
    "live_log_msg": None,
    "warnings": [],
    "registering_users": set()
}

DB_FILE = "database.json"

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            db["users"] = data.get("users", {})
            db["used_phones"] = set(data.get("used_phones", []))
            db["live_log_msg"] = data.get("live_log_msg", None)
            db["warnings"] = data.get("warnings", [])
            db["registering_users"] = set(data.get("registering_users", []))

def save_db():
    data = {
        "users": db["users"],
        "used_phones": list(db["used_phones"]),
        "live_log_msg": db["live_log_msg"],
        "warnings": db["warnings"],
        "registering_users": list(db["registering_users"])
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_user_data(user_id):
    uid = str(user_id)
    if uid not in db["users"]:
        db["users"][uid] = {
            "identity": None,
            "hunger": 100,
            "thirst": 100,
            "health": 100,
            "inventory": {},
            "warnings_count": 0,
            "last_duty_start": None, # وقت تسجيل الدخول
            "total_duty_time": 0     # إجمالي وقت الخدمة
        }
        save_db()
    return db["users"][uid]

def format_time(seconds):
    mins = int(seconds // 60)
    hours = int(mins // 60)
    mins = mins % 60
    if hours > 0: return f"{hours} ساعة و {mins} دقيقة"
    return f"{mins} دقيقة"

async def update_live_log():
    if not db["live_log_msg"]: return
    channel_id, msg_id = db["live_log_msg"]
    try:
        channel = bot.get_channel(channel_id)
        msg = await channel.fetch_message(msg_id)
        guild = channel.guild
        on_duty_role = guild.get_role(ROLE_ON_DUTY)
        
        lines = []
        for member in guild.members:
            if member.get_role(ROLE_ON_DUTY) or member.get_role(ROLE_OFF_DUTY):
                u_data = get_user_data(member.id)
                name = u_data.get("identity", {}).get("name", member.display_name)
                if on_duty_role in member.roles:
                    lines.append(f"{name} تسجيل دخول 🟢")
                else:
                    lines.append(f"{name} خروج 🔴")
                
        if not lines:
            lines.append("لا يوجد أي عسكري في السجلات حالياً.")
            
        embed = discord.Embed(title="البث المراقب لتسجيلات الدخول والخروج", description="\n".join(lines), color=discord.Color.blue())
        await msg.edit(embed=embed)
    except: pass

# ==========================================
# 4. الأحداث ونظام البقاء والباك اب
# ==========================================
@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول كـ {bot.user}")
    
    if not os.path.exists(DB_FILE):
        print("ملف البيانات غير موجود محلياً، جاري البحث في روم الداتا...")
        backup_channel = bot.get_channel(BACKUP_CHANNEL_ID)
        if backup_channel:
            async for msg in backup_channel.history(limit=20):
                if msg.attachments and msg.attachments[0].filename == DB_FILE:
                    await msg.attachments[0].save(DB_FILE)
                    print("✅ تم استرجاع قاعدة البيانات من الديسكورد بنجاح!")
                    break
    
    load_db()
    
    # إعطاء رتبة الدخول للجدد
    for guild in bot.guilds:
        newcomer_role = guild.get_role(ROLE_NEWCOMER)
        if newcomer_role:
            for member in guild.members:
                if not member.bot and len(member.roles) == 1:
                    try: await member.add_roles(newcomer_role)
                    except: pass

    try:
        synced = await bot.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر Slash.")
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")
    
    if not minute_survival_loop.is_running(): minute_survival_loop.start()
    if not backup_db_loop.is_running(): backup_db_loop.start()

@bot.event
async def on_member_join(member):
    newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
    if newcomer_role: await member.add_roles(newcomer_role)

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    # روم سجل السجلات
    if message.channel.id == LOG_CHANNEL_ID:
        if message.mentions:
            target = message.mentions[0]
            u_data = get_user_data(target.id)
            total_time = u_data.get("total_duty_time", 0)
            
            if u_data.get("last_duty_start"):
                total_time += (time.time() - u_data["last_duty_start"])
                
            name = u_data.get("identity", {}).get("name", target.display_name)
            await message.channel.send(f"مدة تفاعل {name} الكلية هي: **{format_time(total_time)}**.")
            
        elif message.content.strip() == "من":
            lines = []
            for member in message.guild.members:
                if member.bot: continue
                u_data = get_user_data(member.id)
                total_time = u_data.get("total_duty_time", 0)
                
                if u_data.get("last_duty_start"):
                    total_time += (time.time() - u_data["last_duty_start"])
                    
                if total_time > 0:
                    name = u_data.get("identity", {}).get("name", member.display_name)
                    lines.append(f"**{name}:** {format_time(total_time)}")
                    
            if not lines: lines.append("لا يوجد تفاعل مسجل حتى الآن.")
            embed = discord.Embed(title="سجل تفاعل العساكر", description="\n".join(lines), color=discord.Color.gold())
            await message.channel.send(embed=embed)

    await bot.process_commands(message) # هام جداً لتشغيل أوامر !أبدأ

@tasks.loop(hours=2)
async def backup_db_loop():
    save_db()
    channel = bot.get_channel(BACKUP_CHANNEL_ID)
    if channel and os.path.exists(DB_FILE):
        with open(DB_FILE, "rb") as f:
            await channel.send("📂 **نسخة احتياطية تلقائية لقاعدة البيانات (Persistence)**", file=discord.File(f, DB_FILE))

@tasks.loop(minutes=1)
async def minute_survival_loop():
    needs_save = False
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot: continue
            
            is_active = str(member.status) != "offline" or member.get_role(ROLE_ON_DUTY)
            if is_active:
                u_data = get_user_data(member.id)
                u_data["hunger"] = max(0, u_data["hunger"] - 1)
                u_data["thirst"] = max(0, u_data["thirst"] - 1)
                needs_save = True
                
                h, t, hp = u_data["hunger"], u_data["thirst"], u_data["health"]
                
                if h == 25 or t == 25:
                    try: await member.send("⚠️ **تحذير:** أنت جائع أو عطشان. نسبتك وصلت 25%.")
                    except: pass
                elif h == 5 or t == 5:
                    try: await member.send("☠️ **تنبيه أخير:** باقي لك 5 وتروح للتوقيف! تصرف فوراً.")
                    except: pass

                if h == 0 and t == 0:
                    u_data["health"] = max(0, hp - 2)
                    if u_data["health"] == 0:
                        try:
                            roles_to_keep = [guild.default_role]
                            if member.get_role(ROLE_MALE): roles_to_keep.append(guild.get_role(ROLE_MALE))
                            if member.get_role(ROLE_FEMALE): roles_to_keep.append(guild.get_role(ROLE_FEMALE))
                            dead_role = guild.get_role(ROLE_DEAD)
                            if dead_role: roles_to_keep.append(dead_role)
                            await member.edit(roles=roles_to_keep)
                        except: pass
    if needs_save: save_db()

# ==========================================
# 5. واجهات الأزرار (Views)
# ==========================================
class InventoryView(discord.ui.View):
    def __init__(self, user_id, inventory):
        super().__init__(timeout=15.0)
        self.user_id = str(user_id)
        for item_name, count in inventory.items():
            if count > 0:
                btn = discord.ui.Button(label=f"{item_name} ({count})", style=discord.ButtonStyle.primary, custom_id=f"use_{item_name}")
                btn.callback = self.create_callback(item_name)
                self.add_item(btn)

    def create_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            if str(interaction.user.id) != self.user_id:
                return await interaction.response.send_message("❌ هذه الشنطة ليست لك!", ephemeral=True)
            
            u_data = get_user_data(self.user_id)
            if u_data["inventory"].get(item_name, 0) <= 0:
                return await interaction.response.send_message("لم يعد لديك هذا الغرض.", ephemeral=True)

            u_data["inventory"][item_name] -= 1
            if u_data["inventory"][item_name] == 0: del u_data["inventory"][item_name]
            
            stats = ITEMS_DB.get(item_name)
            if stats:
                u_data["hunger"] = min(100, u_data["hunger"] + stats["hunger"])
                u_data["thirst"] = min(100, u_data["thirst"] + stats["thirst"])
                u_data["health"] = min(100, u_data["health"] + 5)
            
            save_db()
            await interaction.response.send_message(f"🍽️ تم أكل/شرب **{item_name}** بنجاح!", ephemeral=True)
            self.stop() 
        return callback

class DutyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تسجيل دخول / خروج", style=discord.ButtonStyle.success, custom_id="toggle_duty")
    async def toggle_duty(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        on_duty = interaction.guild.get_role(ROLE_ON_DUTY)
        off_duty = interaction.guild.get_role(ROLE_OFF_DUTY)
        u_data = get_user_data(member.id)
        
        if on_duty in member.roles: # يريد الخروج
            await member.remove_roles(on_duty)
            if off_duty: await member.add_roles(off_duty)
            
            if u_data.get("last_duty_start"):
                duration = time.time() - u_data["last_duty_start"]
                u_data["total_duty_time"] = u_data.get("total_duty_time", 0) + duration
                u_data["last_duty_start"] = None
                
            save_db()
            await interaction.response.send_message("تم تسجيل الخروج بنجاح.", ephemeral=True)
            
        elif off_duty in member.roles: # يريد الدخول
            await member.remove_roles(off_duty)
            if on_duty: await member.add_roles(on_duty)
            
            u_data["last_duty_start"] = time.time()
            save_db()
            await interaction.response.send_message("تم تسجيل الدخول بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("ليس لديك رتبة عسكرية للقيام بذلك.", ephemeral=True)
            
        await update_live_log()

class VerifyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="توثيق الحساب", style=discord.ButtonStyle.success, custom_id="verify_btn")
    async def verify_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_VERIFIED)
        if role: await interaction.user.add_roles(role)
        await interaction.response.send_message("تم توثيق حسابك بنجاح.", ephemeral=True)

class TraineeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="انضمام كمتدرب", style=discord.ButtonStyle.primary, custom_id="trainee_btn")
    async def trainee_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(ROLE_TRAINEE)
        if role in interaction.user.roles: return await interaction.response.send_message("أنت مسجل بالفعل.", ephemeral=True)
        if role: await interaction.user.add_roles(role)
        await interaction.response.send_message("تم إعطاؤك رتبة متدرب.", ephemeral=True)

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="أكمل", style=discord.ButtonStyle.primary, custom_id="verify_start")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
        
        if newcomer_role not in member.roles:
            return await interaction.response.send_message("لقد قمت بالتسجيل مسبقاً أو لا تملك رتبة التسجيل.", ephemeral=True)
        if member.id in db["registering_users"]:
            return await interaction.response.send_message("تم إرسال رسالة لك في الخاص بالفعل!", ephemeral=True)
            
        db["registering_users"].add(member.id)
        save_db()
        await interaction.response.send_message("تم إرسال رسالة لك في الخاص لإكمال تسجيلك.", ephemeral=True)
        
        try:
            await member.send("مرحباً بك في سيرفر رولباك! هل تريد أن تصنع هويتك؟ (نعم/لا)")
            def check(m): return m.author == member and isinstance(m.channel, discord.DMChannel)
            
            resp1 = await bot.wait_for('message', check=check, timeout=120)
            if resp1.content.lower() != 'نعم':
                db["registering_users"].remove(member.id)
                save_db()
                return await member.send("تم الإلغاء.")

            await member.send("حسناً، اكتب اسمك المستعار أو الحقيقي:")
            name_msg = await bot.wait_for('message', check=check, timeout=120)
            name = name_msg.content

            phone = ""
            while True:
                await member.send("اكتب رقم هاتف مزيف يبدأ بـ 17 مكون من 7 أرقام:")
                phone_msg = await bot.wait_for('message', check=check, timeout=120)
                phone_input = phone_msg.content.strip()
                
                if phone_input.startswith("17") and len(phone_input) == 7:
                    if phone_input in db["used_phones"]:
                        await member.send("هذا الرقم محجوز، اختر رقماً آخر.")
                    else:
                        phone = phone_input
                        db["used_phones"].add(phone)
                        break
                else:
                    await member.send("الرقم غلط. يجب أن يبدأ بـ 17 ويكون 7 أرقام.")

            await member.send("آخر شيء، ولد ولا بنت؟ (اكتب 'ولد' أو 'بنت')")
            gender = ""
            while True:
                gender_msg = await bot.wait_for('message', check=check, timeout=120)
                g_input = gender_msg.content.strip()
                if g_input in ['ولد', 'بنت']:
                    gender = g_input
                    break
                await member.send("الرجاء كتابة 'ولد' أو 'بنت' فقط.")

            u_data = get_user_data(member.id)
            u_data["identity"] = {"name": name, "phone": phone, "gender": gender, "nationality": "مواطن"}
            
            await member.remove_roles(newcomer_role)
            citizen_role = member.guild.get_role(ROLE_CITIZEN)
            gender_role = member.guild.get_role(ROLE_MALE if gender == "ولد" else ROLE_FEMALE)
            
            await member.add_roles(citizen_role, gender_role)
            await member.send(f"تم توثيق هويتك بنجاح.")
            
            welcome_channel = bot.get_channel(CHANNEL_WELCOME)
            if welcome_channel: await welcome_channel.send(f"منور ام السيرفر يا {name} {member.mention}")
                
            db["registering_users"].remove(member.id)
            save_db()
            
        except asyncio.TimeoutError:
            if member.id in db["registering_users"]:
                db["registering_users"].remove(member.id)
                save_db()
            await member.send("انتهى وقت التسجيل. اضغط على الزر مجدداً.")

# ==========================================
# 6. أوامر السيرفر (Slash)
# ==========================================
@bot.tree.command(name="رول", description="إعطاء أو إزالة رتبة من شخص")
async def slash_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("لا تملك صلاحية.", ephemeral=True)
    try:
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"تم سحب رتبة {role.name} من {member.mention}.")
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"تم إعطاء رتبة {role.name} لـ {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("حدث خطأ بصلاحيات البوت.", ephemeral=True)

@bot.tree.command(name="تفتيش", description="تفتيش شنطة شخص (للعسكر)")
async def search_inv(interaction: discord.Interaction, member: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("للعسكر فقط.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    inv = u_data["inventory"]
    items_str = "\n".join([f"**{item}**: {count}" for item, count in inv.items() if count > 0])
    if not items_str: items_str = "الشنطة فارغة تماماً."
    await interaction.response.send_message(f"🎒 **تفتيش شنطة {member.display_name}:**\n{items_str}")

@bot.tree.command(name="شنطه", description="عرض مخزونك أو إهداء غرض لشخص آخر")
@app_commands.describe(اهداء="اسم الغرض الذي تريد إهداءه", شخص="الشخص الذي تريد أن تعطيه الغرض")
async def slash_inventory(interaction: discord.Interaction, اهداء: str = None, شخص: discord.Member = None):
    user_id = str(interaction.user.id)
    u_data = get_user_data(user_id)
    
    if اهداء and شخص:
        if اهداء not in u_data["inventory"] or u_data["inventory"][اهداء] <= 0:
            return await interaction.response.send_message(f"❌ أنت لا تملك **{اهداء}** في شنطتك لإهدائه!", ephemeral=True)
        if شخص.bot:
            return await interaction.response.send_message("❌ لا يمكنك إهداء البوتات!", ephemeral=True)
            
        u_data["inventory"][اهداء] -= 1
        if u_data["inventory"][اهداء] == 0: del u_data["inventory"][اهداء]
            
        target_id = str(شخص.id)
        t_data = get_user_data(target_id)
        t_data["inventory"][اهداء] = t_data["inventory"].get(اهداء, 0) + 1
        
        save_db() 
        return await interaction.response.send_message(f"🎁 تم إهداء **{اهداء}** بنجاح إلى {شخص.mention}!")

    h, t, hp = u_data["hunger"], u_data["thirst"], u_data["health"]
    def get_bar(val, color_emoji):
        filled = int((val / 100) * 10)
        return color_emoji * filled + "⬛" * (10 - filled)
        
    embed = discord.Embed(title=f"🎒 شنطة {interaction.user.display_name}", color=discord.Color.dark_gray())
    embed.add_field(name="الصحة", value=f"{hp}% {get_bar(hp, '🟩')}", inline=False)
    embed.add_field(name="الجوع", value=f"{h}% {get_bar(h, '🟧')}", inline=False)
    embed.add_field(name="العطش", value=f"{t}% {get_bar(t, '🟦')}", inline=False)
    
    view = InventoryView(interaction.user.id, u_data["inventory"])
    await interaction.response.send_message(embed=embed, view=view)
    
    await asyncio.sleep(15)
    try: await interaction.delete_original_response()
    except: pass

@bot.tree.command(name="بيع", description="للتجار فقط: بيع غرض لشخص")
async def sell(interaction: discord.Interaction, item: str, member: discord.Member):
    merchant_role = interaction.guild.get_role(ROLE_MERCHANT)
    if merchant_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("فقط التجار.", ephemeral=True)
        
    if item not in ITEMS_DB: return await interaction.response.send_message("الغرض غير موجود.", ephemeral=True)
        
    t_data = get_user_data(member.id)
    t_data["inventory"][item] = t_data["inventory"].get(item, 0) + 1
    save_db()
    await interaction.response.send_message(f"✅ تم بيع {item} لـ {member.mention}.")

# ==========================================
# 7. أوامر التجهيزات الإدارية (!أبدأ) - للملك فقط
# ==========================================
@bot.command(name="أبدأ١")
async def start1(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="تسجيل الدخول / الخروج العسكري", description="الرجاء الضغط على الزر أدناه لتحديث حالتك.", color=discord.Color.dark_gray())
    await ctx.send(embed=embed, view=DutyView())

@bot.command(name="أبدأ٢")
async def start2(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="البث المراقب لتسجيلات الدخول والخروج", description="جاري التحميل...", color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    db["live_log_msg"] = [ctx.channel.id, msg.id]
    save_db()
    await update_live_log()

@bot.command(name="أبدأ٣")
async def start3(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="التحقق من الهوية", description="السلام عليكم، تأكيد دخولك للسيرفر. اضغط زر أكمل للبدء.", color=discord.Color.gold())
    await ctx.send(embed=embed, view=RegistrationView())

@bot.command(name="أبدأ٤")
async def start4(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="التوثيق", description="هل تريد التوثيق؟", color=discord.Color.blue())
    await ctx.send(embed=embed, view=VerifyView())

@bot.command(name="أبدأ٥")
async def start5(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="التجنيد العسكري", description="مرحبا بكم هل تريدو ان تكون جندي عسكري\nاضغط الزر وا سا ندربك بشكل افضل وا كبير جدا", color=discord.Color.dark_red())
    await ctx.send(embed=embed, view=TraineeView())

# ==========================================
# 8. التشغيل
# ==========================================
if __name__ == "__main__":
    keep_alive() 
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("خطأ: لم يتم العثور على توكن البوت في المتغيرات")
    else:
        bot.run(TOKEN)
