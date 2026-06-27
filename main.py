import discord
from discord.ext import commands, tasks
import os
import json
from flask import Flask
from threading import Thread

# ==========================================
# 1. نظام حماية البوت من الخمول (Render Keep-Alive)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "سيرفر الرول بلاي يعمل بنجاح!"

def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==========================================
# 2. إعدادات البوت والبيانات
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=['-', '!', '/'], intents=intents)

# ملف حفظ البيانات (الهويات، التحذيرات، الجوع، الشنطة)
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

db = load_data()

# ==========================================
# 3. نظام رتب العسكر
# ==========================================
@bot.command(name="رول")
async def give_role(ctx, member: discord.Member = None, role: discord.Role = None):
    if not ctx.author.guild_permissions.manage_roles:
        return await ctx.send("❌ ما عندك صلاحية.")
    if not member or not role:
        return await ctx.send("❌ اكتب الأمر بالطريقة هذي: `-رول @الشخص @الرتبة`")
    
    # حماية رتب الأونر (مثال: إذا كانت الرتبة عالية جداً)
    if role.permissions.administrator:
        return await ctx.send("⚠️ انتبه! هذي رتبة قوية جداً (إدارة)، تم إلغاء العملية.")

    if role in member.roles:
        await member.remove_roles(role)
        await ctx.send(f"✅ تم سحب الرتبة {role.name} من {member.mention}.")
    else:
        await member.add_roles(role)
        await ctx.send(f"✅ تم إعطاء الرتبة {role.name} إلى {member.mention}.")

# ==========================================
# 4. نظام التحذيرات
# ==========================================
@bot.command(name="تحذير")
async def warn_user(ctx, member: discord.Member, *, reason=None):
    if not ctx.author.guild_permissions.kick_members:
        return await ctx.send("❌ ما عندك صلاحية.")
    
    loading_msg = await ctx.send("<a:emoji_26:1520109763952771204> جاري التحميل...")
    
    user_id = str(member.id)
    if user_id not in db:
        db[user_id] = {"warnings": [], "inventory": [], "hunger": 100, "thirst": 100, "identity": None}
    elif "warnings" not in db[user_id]:
        db[user_id]["warnings"] = []

    db[user_id]["warnings"].append({"by": ctx.author.name, "reason": reason})
    save_data(db)

    await loading_msg.edit(content=f"<a:emoji_26:1520109726065496295> تم تحذير {member.mention} بنجاح!\nالسبب: {reason}")
    try:
        await member.send(f"⚠️ لقد تم تحذيرك في السيرفر من قبل {ctx.author.name}.\nالسبب: {reason}\nالرجاء قراءة القوانين!")
    except:
        pass

@bot.command(name="تحذيرات")
async def check_warnings(ctx, member: discord.Member = None):
    target = member or ctx.author
    user_id = str(target.id)
    
    loading_msg = await ctx.send("<a:emoji_26:1520109763952771204> جاري البحث في السجلات...")
    
    if user_id not in db or "warnings" not in db[user_id] or len(db[user_id]["warnings"]) == 0:
        return await loading_msg.edit(content=f"✅ {target.mention} لا يوجد لديه أي تحذيرات.")
    
    warns = db[user_id]["warnings"][-10:] # آخر 10 تحذيرات
    msg = f"📜 تحذيرات {target.mention} (العدد: {len(db[user_id]['warnings'])}):\n"
    for i, w in enumerate(warns):
        msg += f"{i+1}. من: {w['by']} | السبب: {w['reason']}\n"
    
    await loading_msg.edit(content=msg)

@bot.command(name="شيل")
async def remove_warnings(ctx, member: discord.Member):
    if not ctx.author.guild_permissions.kick_members:
        return
    user_id = str(member.id)
    if user_id in db and "warnings" in db[user_id]:
        db[user_id]["warnings"] = []
        save_data(db)
        await ctx.send(f"✅ تم مسح جميع التحذيرات عن {member.mention}.")

# ==========================================
# 5. نظام الجوع، العطش، والشنطة
# ==========================================
@tasks.loop(minutes=60.0) # ينقص كل ساعة
async def hunger_thirst_loop():
    for user_id, data in db.items():
        if "hunger" in data and "thirst" in data:
            data["hunger"] = max(0, data["hunger"] - 10)
            data["thirst"] = max(0, data["thirst"] - 15)
    save_data(db)

@bot.command(name="شنطه")
async def inventory(ctx):
    user_id = str(ctx.author.id)
    if user_id not in db:
        db[user_id] = {"warnings": [], "inventory": [], "hunger": 100, "thirst": 100, "identity": None}
    
    data = db[user_id]
    inv = "\n".join(data["inventory"]) if data["inventory"] else "الشنطة فارغة"
    
    msg = f"🎒 **شنطة {ctx.author.name}**\n\n"
    msg += f"📦 الأغراض:\n{inv}\n\n"
    msg += f"🔵 العطش: {data['thirst']}/100\n"
    msg += f"🟠 الجوع: {data['hunger']}/100"
    
    # رسالة مخفية تظهر للشخص فقط
    await ctx.send(msg, delete_after=20)

@bot.command(name="فول")
async def full_stats(ctx, member: discord.Member):
    # مخصصة للملك
    if ctx.author.id != 1306034100544737461:
        return await ctx.send("❌ هذا الأمر للملك فقط.")
    
    user_id = str(member.id)
    if user_id not in db:
        db[user_id] = {"warnings": [], "inventory": [], "hunger": 100, "thirst": 100, "identity": None}
    
    db[user_id]["hunger"] = 100
    db[user_id]["thirst"] = 100
    save_data(db)
    await ctx.send(f"✅ تم تعبئة الجوع والعطش بالكامل لـ {member.mention}")

# ==========================================
# أحداث تشغيل البوت
# ==========================================
@bot.event
async def on_ready():
    print(f'✅ البوت متصل في ديسكورد باسم: {bot.user}')
    if not hunger_thirst_loop.is_running():
        hunger_thirst_loop.start()

# تشغيل خادم الويب
keep_alive()

# تشغيل البوت
token = os.environ.get('DISCORD_TOKEN')
if token:
    bot.run(token)
else:
    print("❌ خطأ: التوكن غير موجود في إعدادات رندر!")
