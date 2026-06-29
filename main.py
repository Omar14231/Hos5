import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import random
import json
import asyncio
from flask import Flask
from threading import Thread

# ==========================================
# 1. خادم الويب لمنع خمول البوت على Render
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل بنجاح وبثبات 100%!"

def run_server():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run_server)
    t.start()

# ==========================================
# 2. الإعدادات والمعطيات الثابتة (IDs)
# ==========================================
OWNER_ID = 1306034100544737461
ADMIN_ROLE_ID = 1521183344430153849  # رتبة الإدارة لحذف الهوية

# رتب العسكر
ROLE_MILITARY = 1520077188135780494  # رتبة عسكري
ROLE_ON_DUTY = 1520077188135780494   # عسكري متصل
ROLE_OFF_DUTY = 1520084329714421800  # عسكري غير متصل

# رتب المواطنين والتسجيل
ROLE_NEWCOMER = 1520087730544050436  # رتبة الدخول والجدد
ROLE_CITIZEN = 1474724032849907722   # رتبة مواطن
ROLE_MALE = 1476903628714410079      # رتبة ولد
ROLE_FEMALE = 1476903782112821258    # رتبة بنت

# إيموجيات التحذير والتحميل المخصصة
EMOJI_WARN1 = "<a:emoji_26:1520109726065496295>"
EMOJI_WARN2 = "<a:emoji_28:1520109788485128202>"
EMOJI_LOADING = "<a:emoji_26:1520109763952771204>"

# ==========================================
# 3. إعدادات البوت وقاعدة البيانات المحلية
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="-", intents=intents)

# قاعدة بيانات لحفظ الهويات والتحذيرات وروم البث المباشر
DB_FILE = "database.json"
db = {"users": {}, "warnings_log": [], "live_log_msg": None}

def load_db():
    global db
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            db = json.load(f)
    if "users" not in db: db["users"] = {}
    if "warnings_log" not in db: db["warnings_log"] = []
    if "live_log_msg" not in db: db["live_log_msg"] = None

def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=4)

def generate_unique_id():
    while True:
        num = random.randint(1000000, 9999999)
        num_str = f"17{str(num)[2:]}" # ضمان البداية بـ 17 وطول 7 أرقام
        exists = any(u.get("national_id") == num_str for u in db["users"].values())
        if not exists:
            return num_str

# ==========================================
# 4. واجهات التفاعل والأزرار (UI / Modals)
# ==========================================

# نافذة إدخال الهوية الكاملة (Modal) التي تظهر على الشاشة
class IdentityModal(discord.ui.Modal, title="استمارة الهوية الوطنية - سيرفر رولباك"):
    name_input = discord.ui.TextInput(label="الاسم الكامل أو المستعار", placeholder="مثال: ابو احمد", min_length=3, max_length=30)
    age_input = discord.ui.TextInput(label="العمر", placeholder="مثال: 22", min_length=2, max_length=2)
    nationality_input = discord.ui.TextInput(label="الجنسية (من وين؟)", placeholder="مثال: سعودي", min_length=3, max_length=20)
    gender_input = discord.ui.TextInput(label="الجنس (ولد أو بنت)", placeholder="اكتب: ولد أو بنت", min_length=3, max_length=3)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        
        gender_text = self.gender_input.value.strip()
        if gender_text not in ["ولد", "بنت"]:
            return await interaction.followup.send("❌ خطأ: يجب كتابة 'ولد' أو 'بنت' فقط في خانة الجنس. أعد المحاولة.", ephemeral=True)
            
        national_id = generate_unique_id()
        user_id = str(interaction.user.id)
        
        db["users"][user_id] = {
            "name": self.name_input.value.strip(),
            "age": self.age_input.value.strip(),
            "nationality": self.nationality_input.value.strip(),
            "gender": gender_text,
            "national_id": national_id,
            "warnings": db["users"].get(user_id, {}).get("warnings", [])
        }
        save_db()
        
        # إدارة الرتب تلقائياً
        guild = interaction.guild
        member = interaction.user
        
        newcomer_role = guild.get_role(ROLE_NEWCOMER)
        citizen_role = guild.get_role(ROLE_CITIZEN)
        gender_role = guild.get_role(ROLE_MALE if gender_text == "ولد" else ROLE_FEMALE)
        
        if newcomer_role: await member.remove_roles(newcomer_role)
        roles_to_add = [r for r in [citizen_role, gender_role] if r]
        if roles_to_add: await member.add_roles(*roles_to_add)
        
        embed = discord.Embed(title="✅ تم إصدار هويتك بنجاح", color=discord.Color.green())
        embed.add_field(name="الاسم المستعار", value=self.name_input.value, inline=True)
        embed.add_field(name="الرقم الوطني", value=f"||{national_id}||", inline=True)
        embed.add_field(name="الجنسية", value=self.nationality_input.value, inline=True)
        await interaction.followup.send(embed=embed, ephemeral=True)

class Start3View(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="أكمل تسجيل الهوية 📋", style=discord.ButtonStyle.primary, custom_id="start_id_modal")
    async def complete_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(IdentityModal())

# نظام الحضور والانصراف (أبدأ 1)
class DutyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="تسجيل دخول / خروج 🪪", style=discord.ButtonStyle.success, custom_id="duty_toggle")
    async def toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        on_duty = interaction.guild.get_role(ROLE_ON_DUTY)
        off_duty = interaction.guild.get_role(ROLE_OFF_DUTY)
        
        if on_duty in member.roles:
            await member.remove_roles(on_duty)
            if off_duty: await member.add_roles(off_duty)
            await interaction.response.send_message("🟢 تم تسجيل خروجك بنجاح وتحويلك للحالة غير متصل.", ephemeral=True)
        elif off_duty in member.roles or len(member.roles) > 1:
            if off_duty in member.roles: await member.remove_roles(off_duty)
            if on_duty: await member.add_roles(on_duty)
            await interaction.response.send_message("🟢 تم تسجيل دخولك بنجاح وتحويلك للحالة متصل وبدء الخدمة.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ ليس لديك الرتب العسكرية اللازمة لتسجيل الدخول.", ephemeral=True)
        
        await update_live_log(interaction.guild)

async def update_live_log(guild):
    if not db.get("live_log_msg"): return
    ch_id, msg_id = db["live_log_msg"]
    try:
        channel = guild.get_channel(ch_id)
        msg = await channel.fetch_message(msg_id)
        on_duty_role = guild.get_role(ROLE_ON_DUTY)
        
        lines = []
        for m in guild.members:
            if m.bot: continue
            if m.get_role(ROLE_ON_DUTY) or m.get_role(ROLE_OFF_DUTY):
                u_data = db["users"].get(str(m.id), {})
                name = u_data.get("name", m.display_name)
                status = "متصل 🟢" if on_duty_role in m.roles else "غير متصل 🔴"
                lines.append(f"**{name}** {status}")
                
        if not lines: lines.append("لا يوجد عساكر مسجلين حالياً.")
        embed = discord.Embed(title="البث المراقب لتسجيلات الدخول والخروج العسكرية", description="\n".join(lines), color=discord.Color.blue())
        await msg.edit(embed=embed)
    except: pass

# ==========================================
# 5. أحداث البوت (Events)
# ==========================================
@bot.event
async def on_ready():
    load_db()
    print(f"تم تشغيل البوت بنجاح كـ: {bot.user.name}")
    try:
        synced = await bot.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر Slash بنجاح.")
    except Exception as e:
        print(f"خطأ بمزامنة السلاش: {e}")

@bot.event
async def on_member_join(member):
    newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
    if newcomer_role: await member.add_roles(newcomer_role)

# ==========================================
# 6. الأوامر العادية والمودريشن (Prefix Commands)
# ==========================================

@bot.command(name="رول")
async def give_role(ctx, member: discord.Member = None, role: discord.Role = None):
    # التحقق من رتبة العسكري أو الأونر
    military_role = ctx.guild.get_role(ROLE_MILITARY)
    if military_role not in ctx.author.roles and ctx.author.id != OWNER_ID:
        return
        
    if not member or not role:
        return await ctx.send("اكتب الأمر بطريقة هذه: -رول @الشخص @الرتبة")
        
    # فحص الرتب القوية جداً لحماية السيرفر
    if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles:
        return await ctx.send(f"انتبه ترا في رتبه قويه انت بتعطيه ايه ({role.name}) تم الغاء العمليه لحماية السيرفر.")

    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"تم ازالة الرتبة {role.name} من الشخص بنجاح.")
        else:
            await member.add_roles(role)
            await ctx.send(f"تم اعطاء الرتبة {role.name} للشخص بنجاح.")
    except discord.Forbidden:
        await ctx.send("حدث خطأ، لا أملك صلاحية كافية للتحكم بهذه الرتبة.")

@bot.command(name="تحذيرات")
async def show_warnings(ctx, member: discord.Member = None):
    await ctx.send(f"{EMOJI_LOADING} جاري التحميل وعرض السجلات...")
    await asyncio.sleep(1)
    
    if member:
        # عرض تحذيرات شخص معين
        user_id = str(member.id)
        user_data = db["users"].get(user_id, {})
        user_warns = user_data.get("warnings", [])
        
        if not user_warns:
            return await ctx.send(f"هذا الشخص ليس له أي تحذيرات مسبقة، حسابه نظيف 100%.")
            
        embed = discord.Embed(title=f"سجل تحذيرات الشخص: {member.display_name}", color=discord.Color.red())
        for i, w in enumerate(user_warns, 1):
            embed.add_field(name=f"تحذير رقم {i}", value=f"**السبب:** {w['reason']}\n**بواسطة:** <@{w['by']}>", inline=False)
        await ctx.send(embed=embed)
    else:
        # عرض آخر 10 تم تحذيرهم بالسيرفر
        if not db["warnings_log"]:
            return await ctx.send("لا يوجد أي تحذيرات مسجلة في السيرفر حالياً.")
            
        embed = discord.Embed(title="آخر 10 تحذيرات في السيرفر", color=discord.Color.orange())
        for w in db["warnings_log"][-10:]:
            embed.add_field(name=f"المحذّر: {w['target_name']}", value=f"السبب: {w['reason']} | بواسطة: <@{w['by_id']}>", inline=False)
        await ctx.send(embed=embed)

# ==========================================
# 7. أوامر السلاش المتقدمة (Slash Commands)
# ==========================================

@bot.tree.command(name="تحذير", description="تحذير شخص محدد مع إرسال تفاصيل بالعام والخاص")
async def slash_warn(interaction: discord.Interaction, شخص: discord.Member, السبب: str):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ هذا الأمر مخصص للعسكر والإدارة فقط.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري تحميل معالجة العقوبة وإصدار التحذير...")
    await asyncio.sleep(1.5)
    
    user_id = str(شخص.id)
    if user_id not in db["users"]: db["users"][user_id] = {"warnings": []}
    if "warnings" not in db["users"][user_id]: db["users"][user_id]["warnings"] = []
    
    warn_entry = {"reason": السبب, "by": interaction.user.id}
    db["users"][user_id]["warnings"].append(warn_entry)
    
    log_entry = {"target_name": شخص.display_name, "reason": السبب, "by_id": interaction.user.id}
    db["warnings_log"].append(log_entry)
    save_db()
    
    # الإرسال في العام
    await interaction.channel.send(f"{EMOJI_WARN1} تم تحذير هذا الشخص {شخص.mention} بنجاح بواسطة {interaction.user.mention}. السبب: **{السبب}**")
    
    # الإرسال في الخاص للشخص المحذور بشكل رسمي
    try:
        embed_dm = discord.Embed(title=f"{EMOJI_WARN2} تنبيه رسمي: تم تحذيرك في السيرفر", color=discord.Color.dark_red())
        embed_dm.add_field(name="السبب المذكور", value=السبب)
        embed_dm.add_field(name="بواسطة المسؤول", value=interaction.user.display_name)
        embed_dm.description = "الرجاء قراءة القوانين بعناية والالتزام بنظام الحية الواقعية لتجنب التوقيف والسجن."
        await شخص.send(embed=embed_dm)
    except: pass

@bot.tree.command(name="شيل", description="حذف وإلغاء جميع التحذيرات الموجهة لشخص")
async def slash_clear_warns(interaction: discord.Interaction, شخص: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ هذا الأمر مخصص للعسكر والإدارة.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري تنظيف السجلات وحذف تحذيراته...")
    
    user_id = str(شخص.id)
    if user_id in db["users"] and "warnings" in db["users"][user_id]:
        db["users"][user_id]["warnings"] = []
        db["warnings_log"] = [w for w in db["warnings_log"] if w["target_name"] != شخص.display_name]
        save_db()
        await interaction.channel.send(f"✅ تم حذف وتنظيف جميع التحذيرات السابقة للشخص {شخص.mention} بنجاح.")
    else:
        await interaction.channel.send("هذا الشخص ليس لديه أي سجل تحذيرات لحذفه.")

@bot.tree.command(name="هويه", description="عرض بيانات الهوية الوطنية المزيفة الخاصة بالشخص")
async def slash_identity(interaction: discord.Interaction, شخص: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ هذا الأمر مخصص للعساكر فقط لرؤية الهويات.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري فحص النظام المركزي للاستعلام عن الهوية...")
    await asyncio.sleep(1)
    
    u_data = db["users"].get(str(شخص.id))
    if not u_data or not u_data.get("national_id"):
        return await interaction.channel.send(f"❌ الشخص {شخص.mention} ليس لديه هوية وطنية مسجلة في النظام حتى الآن.")
        
    embed = discord.Embed(title=f"🪪 الهوية الوطنية الإلكترونية للـمواطن", color=discord.Color.blue())
    embed.add_field(name="الاسم الكامل", value=u_data["name"], inline=True)
    embed.add_field(name="الرقم الوطني المزيف", value=u_data["national_id"], inline=True)
    embed.add_field(name="العمر", value=u_data["age"], inline=True)
    embed.add_field(name="الجنسية والبلد", value=u_data["nationality"], inline=True)
    embed.add_field(name="الجنس", value=u_data["gender"], inline=True)
    await interaction.channel.send(embed=embed)

@bot.tree.command(name="حذف_هويه", description="مسح هوية الشخص تماماً وتجريده من رتبه (للإدارة فقط)")
async def slash_delete_identity(interaction: discord.Interaction, شخص: discord.Member):
    admin_role = interaction.guild.get_role(ADMIN_ROLE_ID)
    if admin_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("❌ هذا الأمر مخصص لأصحاب رتبة الإدارة العليا المحددة فقط.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري حذف الهوية من قاعدة البيانات وتجريد الرتب...")
    
    user_id = str(شخص.id)
    if user_id in db["users"]:
        db["users"][user_id]["national_id"] = None
        db["users"][user_id]["name"] = None
        save_db()
        
        # سحب جميع الرتب وإعطاء رتبة الدخول
        try:
            newcomer_role = interaction.guild.get_role(ROLE_NEWCOMER)
            await شخص.edit(roles=[newcomer_role] if newcomer_role else [])
            await شخص.send("⚠️ تم مسح هويتك الوطنية من قبل الإدارة وسحب رتبك، يرجى إعادة تقديم الهوية مجدداً.")
        except: pass
        
        await interaction.channel.send(f"✅ تم حذف هوية {شخص.mention} بنجاح وإعادته لرتبة الدخول لتسجيل هوية جديدة.")
    else:
        await interaction.channel.send("الشخص غير مسجل بالأساس في النظام.")

# ==========================================
# 8. أوامر التجهيزات الإدارية الفريدة (!أبدأ)
# ==========================================

@bot.command(name="أبدأ١")
async def setup_start1(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="تسجيل دخول وخروج العسكر", description="اضغط على الزر بالأسفل لتغيير حالتك بين متصل (On Duty) وغير متصل (Off Duty) تلقائياً.", color=discord.Color.green())
    await ctx.send(embed=embed, view=DutyView())

@bot.command(name="أبدأ٢")
async def setup_start2(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="البث المراقب لتسجيلات الدخول والخروج العسكرية", description="جاري تهيئة البث المباشر وعرض العساكر...", color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    db["live_log_msg"] = [ctx.channel.id, msg.id]
    save_db()
    await update_live_log(ctx.guild)

@bot.command(name="أبدأ٣")
async def setup_start3(ctx):
    if ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="تأكيد وتوثيق الدخول للسيرفر رولباك", description="أهلاً بك في مدينة الحياة الواقعية. يرجى الضغط على الزر أدناه لتعبئة بيانات الهوية الوطنية الخاصة بك عبر النافذة الرسمية مباشرة.", color=discord.Color.gold())
    await ctx.send(embed=embed, view=Start3View())

# ==========================================
# 9. تشغيل البوت النهائي
# ==========================================
if __name__ == "__main__":
    keep_alive() # تشغيل خادم الويب للحماية من النوم
    TOKEN = os.getenv("DISCORD_TOKEN")
    if TOKEN:
        bot.run(TOKEN)
    else:
        print("❌ خطأ: لم يتم العثور على المتغير DISCORD_TOKEN في إعدادات Render.")
