import discord
from discord.ext import commands
from discord import app_commands
import os
import random
import json
import asyncio
from datetime import datetime
from flask import Flask
from threading import Thread

# ==========================================
# 1. خادم الويب (لمنع خمول البوت على Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "بوت رولباك الشامل يعمل بنجاح وبثبات!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 2. المعطيات الثابتة (IDs الرتب والصلاحيات)
# ==========================================
OWNER_ID = 1306034100544737461
ROLE_ADMIN = 1521183344430153849        # الإدارة والإعداد
ROLE_MILITARY_ADMIN = 1521212742910873651 # مسؤول العسكر

ROLE_ON_DUTY = 1520077188135780494      # عسكري مسجل دخول
ROLE_OFF_DUTY = 1520084329714421800     # عسكري مسجل خروج

ROLE_NEWCOMER = 1520087730544050436     # رتبة الجدد
ROLE_CITIZEN = 1474724032849907722      # مواطن
ROLE_TAWTHEEQ = 1520078137902497922     # موثق
ROLE_MALE = 1476903628714410079         # ولد
ROLE_FEMALE = 1476903782112821258       # بنت

EMOJI_LOADING = "<a:emoji_26:1520109763952771204>"
EMOJI_WARN1 = "⚠️" # استبدلها بإيموجي السيرفر إذا أردت
EMOJI_WARN2 = "🛑"

# ==========================================
# 3. إعدادات البوت وقاعدة البيانات
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

class RollbackBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # تسجيل الأزرار لكي تظل تعمل حتى بعد إطفاء وتشغيل البوت
        self.add_view(DutyView())
        self.add_view(RegistrationView())
        self.add_view(TawtheeqView())
        self.add_view(PointsView())

bot = RollbackBot()

DB_FILE = "database.json"
db = {"users": {}, "warnings": {}, "system": {}}

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    if "users" not in db: db["users"] = {}
    if "warnings" not in db: db["warnings"] = {}
    if "system" not in db: db["system"] = {}
    return db

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def generate_unique_id():
    while True:
        num = random.randint(1000000, 9999999)
        num_str = f"17{str(num)[2:]}"
        exists = any(u.get("national_id") == num_str for u in db["users"].values())
        if not exists: return num_str

# التحقق من الصلاحيات
def is_military_or_admin(user: discord.Member):
    roles = [r.id for r in user.roles]
    return any(r in roles for r in [ROLE_ON_DUTY, ROLE_OFF_DUTY, ROLE_MILITARY_ADMIN, ROLE_ADMIN]) or user.id == OWNER_ID

# ==========================================
# 4. تحديث البث المباشر (أبدأ٢)
# ==========================================
async def update_broadcast():
    if "broadcast_channel" not in db["system"] or "broadcast_message" not in db["system"]:
        return
    
    channel_id = db["system"]["broadcast_channel"]
    message_id = db["system"]["broadcast_message"]
    
    channel = bot.get_channel(channel_id)
    if not channel: return
    
    try:
        msg = await channel.fetch_message(message_id)
        
        on_duty_role = channel.guild.get_role(ROLE_ON_DUTY)
        off_duty_role = channel.guild.get_role(ROLE_OFF_DUTY)
        
        embed = discord.Embed(title="📡 البث المراقب لتسجيلات الدخول والخروج", color=discord.Color.dark_grey())
        
        description_lines = []
        # جلب العساكر المسجلين دخول
        for member in on_duty_role.members:
            u_data = db["users"].get(str(member.id), {})
            name = u_data.get("name", member.display_name)
            description_lines.append(f"**{name}** مسجل دخول 🟢")
            
        # جلب العساكر المسجلين خروج
        for member in off_duty_role.members:
            u_data = db["users"].get(str(member.id), {})
            name = u_data.get("name", member.display_name)
            description_lines.append(f"**{name}** غير مسجل دخول 🔴")
            
        if not description_lines:
            embed.description = "لا يوجد عساكر في السجلات حالياً."
        else:
            embed.description = "\n".join(description_lines)
            
        embed.set_footer(text=f"آخر تحديث: {datetime.now().strftime('%H:%M:%S')}")
        await msg.edit(embed=embed)
    except discord.NotFound:
        pass

# ==========================================
# 5. واجهات التفاعل (الاستمارات والأزرار)
# ==========================================

# 1. نظام الهوية
class IdentityModal(discord.ui.Modal, title="استمارة الهوية الوطنية"):
    name_input = discord.ui.TextInput(label="الاسم الكامل أو المستعار", min_length=3, max_length=30)
    age_input = discord.ui.TextInput(label="العمر", min_length=2, max_length=2)
    nationality_input = discord.ui.TextInput(label="الجنسية", min_length=3, max_length=20)
    gender_input = discord.ui.TextInput(label="الجنس (ولد أو بنت)", placeholder="ولد أو بنت", min_length=3, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        gender_text = self.gender_input.value.strip()
        if gender_text not in ["ولد", "بنت"]:
            return await interaction.followup.send("❌ اكتب 'ولد' أو 'بنت' فقط.", ephemeral=True)
            
        national_id = generate_unique_id()
        user_id = str(interaction.user.id)
        
        db["users"][user_id] = {
            "name": self.name_input.value.strip(),
            "age": self.age_input.value.strip(),
            "nationality": self.nationality_input.value.strip(),
            "gender": gender_text,
            "national_id": national_id,
            "status": "مواطن",
            "points": 0
        }
        save_db()
        
        guild = interaction.guild
        member = interaction.user
        roles_to_add = [guild.get_role(ROLE_CITIZEN), guild.get_role(ROLE_MALE if gender_text == "ولد" else ROLE_FEMALE)]
        roles_to_add = [r for r in roles_to_add if r]
        
        newcomer_role = guild.get_role(ROLE_NEWCOMER)
        if newcomer_role in member.roles: 
            await member.remove_roles(newcomer_role)
        if roles_to_add: 
            await member.add_roles(*roles_to_add)
        
        embed = discord.Embed(title="✅ تم إصدار هويتك بنجاح", color=discord.Color.green())
        embed.add_field(name="الاسم", value=self.name_input.value)
        embed.add_field(name="الرقم الوطني", value=f"`{national_id}`")
        await interaction.followup.send(embed=embed, ephemeral=True)

class RegistrationView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="تسجيل الهوية 📋", style=discord.ButtonStyle.primary, custom_id="reg_btn")
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.guild.get_role(ROLE_NEWCOMER) not in interaction.user.roles:
            return await interaction.response.send_message("❌ أنت مسجل مسبقاً!", ephemeral=True)
        await interaction.response.send_modal(IdentityModal())

# 2. نظام الدخول والخروج للعسكر
class DutyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="تسجيل خروج / دخول 👮", style=discord.ButtonStyle.success, custom_id="duty_btn")
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        role_on = interaction.guild.get_role(ROLE_ON_DUTY)
        role_off = interaction.guild.get_role(ROLE_OFF_DUTY)
        
        if role_on in member.roles:
            await member.remove_roles(role_on)
            await member.add_roles(role_off)
            await interaction.response.send_message("🔴 تم تسجيل الخروج بنجاح.", ephemeral=True)
        elif role_off in member.roles:
            await member.remove_roles(role_off)
            await member.add_roles(role_on)
            await interaction.response.send_message("🟢 تم تسجيل الدخول بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك رتبة عسكرية للتسجيل.", ephemeral=True)
            return
        await update_broadcast()

# 3. نظام التوثيق
class TawtheeqView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="توثيق ✔️", style=discord.ButtonStyle.primary, custom_id="tawtheeq_btn")
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        tawtheeq_role = interaction.guild.get_role(ROLE_TAWTHEEQ)
        if tawtheeq_role in interaction.user.roles:
            return await interaction.response.send_message("أنت موثق بالفعل.", ephemeral=True)
        await interaction.user.add_roles(tawtheeq_role)
        await interaction.response.send_message("✅ تم استلام الرتبة وتوثيقك بنجاح.", ephemeral=True)

# 4. نظام النقاط للعسكر
class PointsView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="كم عندي نقاط؟ 🏆", style=discord.ButtonStyle.secondary, custom_id="points_btn")
    async def btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        uid = str(interaction.user.id)
        pts = db["users"].get(uid, {}).get("points", 0)
        await interaction.response.send_message(f"👮 إجمالي نقاطك العسكرية الحالية: **{pts}** نقطة.", ephemeral=True)

# ==========================================
# 6. أوامر الإعداد المخفية (!أبدأ 1 إلى 5)
# ==========================================
@bot.command(name="أبدأ١")
async def start1(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(title="نظام الدوام العسكري", description="اضغط لتسجيل الدخول أو الخروج."), view=DutyView())

@bot.command(name="أبدأ٢")
async def start2(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="📡 البث المراقب لتسجيلات الدخول والخروج", description="جاري التحميل...")
    msg = await ctx.send(embed=embed)
    db["system"]["broadcast_channel"] = ctx.channel.id
    db["system"]["broadcast_message"] = msg.id
    save_db()
    await update_broadcast()

@bot.command(name="أبدأ٣")
async def start3(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(title="إصدار الهوية الوطنية", description="اضغط لتعبئة بياناتك."), view=RegistrationView())

@bot.command(name="أبدأ٤")
async def start4(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(title="نظام التوثيق الرسمي", description="اضغط لتوثيق حسابك بالمدينة."), view=TawtheeqView())

@bot.command(name="أبدأ٥")
async def start5(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    await ctx.send(embed=discord.Embed(title="نقاط العسكر المكتسبة", description="استعلم عن نقاطك."), view=PointsView())

# ==========================================
# 7. أوامر السلاش (للعسكر والإدارة)
# ==========================================

@bot.tree.command(name="هويه", description="عرض بيانات الهوية")
async def slash_id(interaction: discord.Interaction, شخص: discord.Member):
    if not is_military_or_admin(interaction.user):
        return await interaction.response.send_message("❌ للعسكر فقط.", ephemeral=True)
    u_data = db["users"].get(str(شخص.id))
    if not u_data or not u_data.get("national_id"): return await interaction.response.send_message("❌ ليس لديه هوية.")
    
    embed = discord.Embed(title="🪪 الهوية الوطنية", color=discord.Color.blue())
    if شخص.avatar: embed.set_thumbnail(url=شخص.avatar.url)
    embed.add_field(name="الاسم", value=u_data["name"])
    embed.add_field(name="الرقم الوطني", value=f"`{u_data['national_id']}`")
    embed.add_field(name="الحالة", value=u_data.get("status", "مواطن"))
    embed.add_field(name="الجنس", value=u_data["gender"])
    embed.add_field(name="العمر", value=u_data["age"])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="تغير", description="تغيير حالة/مهنة الشخص في الهوية")
async def change_status(interaction: discord.Interaction, شخص: discord.Member, التغير: str):
    if not is_military_or_admin(interaction.user): return await interaction.response.send_message("❌ غير مصرح.", ephemeral=True)
    uid = str(شخص.id)
    if uid not in db["users"]: return await interaction.response.send_message("❌ ليس مسجل بالنظام.")
    
    db["users"][uid]["status"] = التغير
    save_db()
    await interaction.response.send_message(f"✅ تم تغيير حالة {شخص.mention} إلى: **{التغير}**")

@bot.tree.command(name="mdt", description="النظام الجنائي للعسكر")
async def mdt_system(interaction: discord.Interaction, شخص: discord.Member):
    if not is_military_or_admin(interaction.user): return await interaction.response.send_message("❌ للعسكر فقط.", ephemeral=True)
    u_data = db["users"].get(str(شخص.id))
    if not u_data: return await interaction.response.send_message("❌ غير مسجل.")
    
    warns = len(db["warnings"].get(str(شخص.id), []))
    status = u_data.get("status", "مواطن")
    is_on_duty = interaction.guild.get_role(ROLE_ON_DUTY) in شخص.roles
    
    embed = discord.Embed(title="📱 MDT السجل المركزي", color=discord.Color.dark_theme())
    if شخص.avatar: embed.set_thumbnail(url=شخص.avatar.url)
    embed.add_field(name="الاسم", value=u_data["name"])
    embed.add_field(name="الرقم", value=u_data["national_id"])
    embed.add_field(name="الحالة الجنائية/المهنة", value=f"⚠️ {status}", inline=False)
    embed.add_field(name="التحذيرات", value=f"{warns} تحذير")
    embed.add_field(name="العسكرية", value="مسجل دخول 🟢" if is_on_duty else "غير مسجل 🔴")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="نقاط", description="إعطاء نقاط لعسكري")
async def give_points(interaction: discord.Interaction, شخص: discord.Member, كم: int):
    # مخصص لمسؤول العسكر أو الأونر
    if interaction.guild.get_role(ROLE_MILITARY_ADMIN) not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ هذا الأمر لمسؤول العسكر فقط.", ephemeral=True)
        
    uid = str(شخص.id)
    if uid not in db["users"]: return await interaction.response.send_message("❌ غير مسجل.")
    
    db["users"][uid]["points"] = db["users"][uid].get("points", 0) + كم
    save_db()
    await interaction.response.send_message(f"✅ تم إضافة **{كم}** نقطة للعسكري {شخص.mention}.")

@bot.tree.command(name="حذف_هويه", description="مسح هوية مواطن وإرجاعه للبداية")
async def wipe_id(interaction: discord.Interaction, شخص: discord.Member):
    if interaction.guild.get_role(ROLE_ADMIN) not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ للإدارة فقط.", ephemeral=True)
        
    uid = str(شخص.id)
    if uid in db["users"]: del db["users"][uid]
    if uid in db["warnings"]: del db["warnings"][uid]
    save_db()
    
    # سحب جميع الرتب وإعطاء رتبة الدخول
    try:
        await شخص.edit(roles=[interaction.guild.get_role(ROLE_NEWCOMER)])
        await شخص.send("⚠️ تم مسح هويتك من قبل الإدارة وسحب رتبك. يرجى التوجه لمقر التسجيل لإصدار هوية جديدة.")
    except discord.Forbidden:
        pass
    
    await interaction.response.send_message(f"✅ تم مسح هوية {شخص.mention} بالكامل وتصفير رتبه.")

@bot.tree.command(name="رول", description="إعطاء أو سحب رتبة")
async def toggle_role(interaction: discord.Interaction, شخص: discord.Member, رتبه: discord.Role):
    if not is_military_or_admin(interaction.user):
        return await interaction.response.send_message("❌ ليس لديك صلاحية.", ephemeral=True)
    if رتبه.permissions.administrator or رتبه.permissions.manage_roles:
        return await interaction.response.send_message("❌ هذه الرتبة إدارية وخطيرة.", ephemeral=True)
        
    if رتبه in شخص.roles:
        await شخص.remove_roles(رتبه)
        await interaction.response.send_message(f"➖ تم سحب رتبة {رتبه.name} من {شخص.mention}")
    else:
        await شخص.add_roles(رتبه)
        await interaction.response.send_message(f"➕ تم إعطاء رتبة {رتبه.name} إلى {شخص.mention}")

# ==========================================
# أوامر التحذيرات (Moderation)
# ==========================================
@bot.tree.command(name="تحذير", description="إعطاء تحذير رسمي")
async def warn_user(interaction: discord.Interaction, شخص: discord.Member, السبب: str):
    if not is_military_or_admin(interaction.user): return await interaction.response.send_message("❌ غير مصرح.")
    
    uid = str(شخص.id)
    if uid not in db["warnings"]: db["warnings"][uid] = []
    db["warnings"][uid].append({"reason": السبب, "officer": interaction.user.display_name, "date": datetime.now().strftime("%Y-%m-%d")})
    save_db()
    
    await interaction.response.send_message(f"{EMOJI_WARN1} تم توجيه تحذير لـ {شخص.mention}\n📌 السبب: **{السبب}**\n👮 بواسطة: {interaction.user.display_name}")
    try: await شخص.send(f"🛑 تلقيت تحذيراً بالسيرفر.\nالسبب: {السبب}")
    except: pass

@bot.tree.command(name="شيل", description="مسح تحذيرات عضو")
async def clear_warns(interaction: discord.Interaction, شخص: discord.Member):
    if not is_military_or_admin(interaction.user): return await interaction.response.send_message("❌ غير مصرح.")
    uid = str(شخص.id)
    if uid in db["warnings"]: del db["warnings"][uid]
    save_db()
    await interaction.response.send_message(f"✅ تم تصفير تحذيرات {شخص.mention}.")

# ==========================================
# 8. التشغيل والمزامنة
# ==========================================
@bot.event
async def on_ready():
    load_db()
    print(f"تم التشغيل: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"تم مزامنة {len(synced)} أمر سلاش.")
    except Exception as e: print(e)

if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    bot.run(TOKEN)
