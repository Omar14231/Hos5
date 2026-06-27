import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import asyncio
from flask import Flask
from threading import Thread

# ==========================================
# 1. خادم الويب (لحل مشكلة السبات في Render)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "البوت يعمل بنجاح!"

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

# رتب العسكر
ROLE_ON_DUTY = 1520077188135780494
ROLE_OFF_DUTY = 1520084329714421800

# رتب التسجيل والمواطنين
ROLE_NEWCOMER = 1520087730544050436
ROLE_CITIZEN = 1474724032849907722
ROLE_MALE = 1476903628714410079
ROLE_FEMALE = 1476903782112821258

# رتب الاقتصاد والبقاء
ROLE_MERCHANT = 1520153220100522126
ROLE_STARVED = 1520075245308874853

# الايموجيات
EMOJI_WARN_1 = "<a:emoji_26:1520109726065496295>"
EMOJI_WARN_2 = "<a:emoji_28:1520109788485128202>"
EMOJI_LOADING = "<a:emoji_26:1520109763952771204>"

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
# 3. إعدادات البوت والـ Intents
# ==========================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True

bot = commands.Bot(command_prefix=["-", "!"], intents=intents)

# قاعدة بيانات مؤقتة (يُفضل لاحقاً ربطها بـ JSON أو SQLite)
db = {
    "users": {},
    "used_phones": set(),
    "live_log_msg": None,
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
# 4. الأحداث الأساسية ونظام الجوع/العطش
# ==========================================
@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول كـ {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر Slash.")
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")
    
    if not survival_loop.is_running():
        survival_loop.start()

@bot.event
async def on_member_join(member):
    # إعطاء رتبة الوافد الجديد تلقائياً عند الدخول
    newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
    if newcomer_role:
        await member.add_roles(newcomer_role)

@tasks.loop(hours=1)
async def survival_loop():
    """ينقص الجوع والعطش 50% كل ساعة للمتصلين"""
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot: continue
            
            # التحقق إذا كان متصلاً أو يمتلك رتبة عسكري متصل (حتى لو كان مخفي)
            is_active = str(member.status) != "offline" or member.get_role(ROLE_ON_DUTY)
            if is_active:
                u_data = get_user_data(member.id)
                u_data["hunger"] = max(0, u_data["hunger"] - 50)
                u_data["thirst"] = max(0, u_data["thirst"] - 50)
                
                h, t = u_data["hunger"], u_data["thirst"]
                if h == 0 or t == 0:
                    try:
                        # سحب جميع الرتب ما عدا الجنس
                        roles_to_keep = [guild.default_role]
                        if member.get_role(ROLE_MALE): roles_to_keep.append(guild.get_role(ROLE_MALE))
                        if member.get_role(ROLE_FEMALE): roles_to_keep.append(guild.get_role(ROLE_FEMALE))
                        
                        starved_role = guild.get_role(ROLE_STARVED)
                        if starved_role: roles_to_keep.append(starved_role)
                        
                        await member.edit(roles=roles_to_keep)
                        owner = await bot.fetch_user(OWNER_ID)
                        await owner.send(f"⚠️ المستخدم {member.mention} لم يأكل ومات من الجوع/العطش وهو متصل.")
                    except: pass
                elif (h <= 15 or t <= 15):
                    try: await member.send(f"🚨 **تحذير خطير:** جوعك أو عطشك وصل 15% أو أقل! كُل أو اشرب فوراً أو سيتم توقيفك.")
                    except: pass
                elif (h <= 25 or t <= 25):
                    try: await member.send(f"⚠️ **تحذير:** أنت جائع أو عطشان. نسبتك وصلت 25%. يرجى شراء طعام.")
                    except: pass

async def update_live_log():
    if not db["live_log_msg"]: return
    channel_id, msg_id = db["live_log_msg"]
    try:
        channel = bot.get_channel(channel_id)
        msg = await channel.fetch_message(msg_id)
        guild = channel.guild
        on_duty_role = guild.get_role(ROLE_ON_DUTY)
        
        lines = ["**سجل الدخول والخروج العسكري المباشر**"]
        for member in guild.members:
            # دمج معلومات الهوية مع حالة الاتصال
            if member.get_role(ROLE_ON_DUTY) or member.get_role(ROLE_OFF_DUTY):
                u_data = get_user_data(member.id)
                name = u_data.get("identity", {}).get("name", member.display_name)
                status = "متصل 🟢" if on_duty_role in member.roles else "غير متصل 🔴"
                lines.append(f"{name} {status}")
                
        embed = discord.Embed(title="حالة العساكر", description="\n".join(lines), color=discord.Color.blue())
        await msg.edit(embed=embed)
    except: pass

# ==========================================
# 5. واجهات الأزرار (Views)
# ==========================================
class DutyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="تسجيل دخول / خروج", style=discord.ButtonStyle.success, custom_id="toggle_duty")
    async def toggle_duty(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        on_duty = member.guild.get_role(ROLE_ON_DUTY)
        off_duty = member.guild.get_role(ROLE_OFF_DUTY)
        
        if on_duty in member.roles:
            await member.remove_roles(on_duty)
            if off_duty: await member.add_roles(off_duty)
            await interaction.response.send_message("تم تسجيل خروجك بنجاح.", ephemeral=True)
        elif off_duty in member.roles:
            await member.remove_roles(off_duty)
            if on_duty: await member.add_roles(on_duty)
            await interaction.response.send_message("تم تسجيل دخولك بنجاح.", ephemeral=True)
        else:
            await interaction.response.send_message("ليس لديك رتبة عسكرية للقيام بذلك.", ephemeral=True)
            
        await update_live_log()

class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="أكمل", style=discord.ButtonStyle.primary, custom_id="verify_start")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
        
        if newcomer_role not in member.roles:
            return await interaction.response.send_message("لقد قمت بالتسجيل مسبقاً أو لا تملك رتبة التسجيل.", ephemeral=True)
            
        await interaction.response.send_message("تم إرسال رسالة لك في الخاص لإكمال تسجيلك.", ephemeral=True)
        
        try:
            await member.send("مرحباً بك في سيرفر رولباك! هل تريد أن تصنع هويتك في السيرفر للمزح واللعب فقط؟ (نعم/لا)")
            def check(m): return m.author == member and isinstance(m.channel, discord.DMChannel)
            
            resp1 = await bot.wait_for('message', check=check, timeout=120)
            if resp1.content.lower() != 'نعم':
                return await member.send("تم إلغاء العملية.")

            await member.send("حسناً، اكتب اسمك المزيف أو الحقيقي (على سبيل المثال: أبو أحمد):")
            name_msg = await bot.wait_for('message', check=check, timeout=120)
            if name_msg.content == "الغاء": return await member.send("تم الإلغاء.")
            name = name_msg.content

            phone = ""
            while True:
                await member.send("هل تريد صنع رقم هاتف مزيف 100% للسيرفر؟ (متى ما تريد إغلاق الخيار كلم الدعم)\nاكتب رقم يبدأ بـ 17 مكون من 7 أرقام (مثال: 1712345):")
                phone_msg = await bot.wait_for('message', check=check, timeout=120)
                phone_input = phone_msg.content.strip()
                if phone_input == "الغاء": return await member.send("تم الإلغاء.")
                
                if phone_input.startswith("17") and len(phone_input) == 7:
                    if phone_input in db["used_phones"]:
                        await member.send("هذا الرقم عند شخص آخر، الرجاء اختيار رقم مختلف.")
                    else:
                        phone = phone_input
                        db["used_phones"].add(phone)
                        break
                else:
                    await member.send("الرقم غلط. يجب أن يبدأ بـ 17 ويكون طوله 7 أرقام. (اكتب 'الغاء' لإلغاء العملية).")

            await member.send("آخر شيء، ما جنسيتك؟ (اكتب 'ولد' أو 'بنت')")
            gender = ""
            while True:
                gender_msg = await bot.wait_for('message', check=check, timeout=120)
                g_input = gender_msg.content.strip()
                if g_input in ['ولد', 'بنت']:
                    gender = g_input
                    break
                await member.send("الرجاء كتابة 'ولد' أو 'بنت'.")

            # الحفظ وإعطاء الرتب
            u_data = get_user_data(member.id)
            u_data["identity"] = {"name": name, "phone": phone, "gender": gender, "nationality": "مواطن"}
            
            await member.remove_roles(newcomer_role)
            citizen_role = member.guild.get_role(ROLE_CITIZEN)
            gender_role = member.guild.get_role(ROLE_MALE if gender == "ولد" else ROLE_FEMALE)
            
            await member.add_roles(citizen_role, gender_role)
            await member.send(f"مرحباً بك في سيرفر رولباك يا {name}! تم توثيق هويتك بنجاح.")
            
        except asyncio.TimeoutError:
            await member.send("انتهى وقت التسجيل. الرجاء الضغط على الزر في السيرفر مرة أخرى.")
        except discord.Forbidden:
            pass 

# ==========================================
# 6. أوامر الإدارة والعسكر
# ==========================================
@bot.command(name="رول")
async def role_cmd(ctx, member: discord.Member = None, role: discord.Role = None):
    if not ctx.author.guild_permissions.manage_roles and ctx.author.id != OWNER_ID: return
    if member is None or role is None:
        return await ctx.send("اكتب الأمر بالطريقة هذه: `-رول @منشن_الشخص @منشن_الرتبة`")
        
    # حماية من الرتب القوية
    if role.permissions.administrator or role.permissions.manage_guild or role.permissions.manage_roles or role.permissions.ban_members:
        return await ctx.send("هذي رتبة عالية بشكل كبير، تم إلغاء العملية.")

    try:
        if role in member.roles:
            await member.remove_roles(role)
            await ctx.send(f"تم إزالة الرتبة من {member.display_name}.")
        else:
            await member.add_roles(role)
            await ctx.send(f"تم إعطاء الرتبة لـ {member.display_name}.")
    except:
        await ctx.send("حدث خطأ، تأكد من صلاحيات البوت وأنه أعلى من الرتبة المراد إعطاؤها.")

@bot.tree.command(name="تحذير", description="تحذير مستخدم")
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not interaction.user.guild_permissions.kick_members and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("لا تملك الصلاحية.", ephemeral=True)
        
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري التحميل...")
    
    u_data = get_user_data(member.id)
    u_data["warnings_count"] += 1
    db["warnings"].insert(0, {"admin": interaction.user.display_name, "user": member.display_name, "reason": reason})
    
    await interaction.edit_original_response(content=f"{EMOJI_WARN_1} تم تحذير {member.mention} من قبل {interaction.user.mention}\nالسبب: {reason} {EMOJI_WARN_2}")
    
    try:
        await member.send(f"⚠️ **تحذير إداري** ⚠️\nتم تحذيرك من قبل: {interaction.user.display_name}\nالسبب: {reason}\n\nالرجاء قراءة القوانين بتركيز لتجنب العقوبات.")
    except: pass

@bot.tree.command(name="شيل", description="إزالة تحذيرات مستخدم")
async def remove_warn(interaction: discord.Interaction, member: discord.Member):
    if not interaction.user.guild_permissions.kick_members and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("لا تملك الصلاحية.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    u_data["warnings_count"] = 0
    await interaction.response.send_message(f"تم حذف جميع التحذيرات الخاصة بـ {member.mention}")

@bot.command(name="تحذيرات")
async def warnings(ctx, member: discord.Member = None):
    msg = await ctx.send(f"{EMOJI_LOADING} جاري التحميل...")
    if member:
        count = get_user_data(member.id)["warnings_count"]
        if count == 0:
            await msg.edit(content=f"لا يوجد تحذيرات لهذا الشخص.")
        else:
            await msg.edit(content=f"هذا الشخص لديه {count} تحذيرات.")
    else:
        recent = db["warnings"][:10]
        if not recent:
            return await msg.edit(content="لا يوجد تحذيرات.")
            
        lines = []
        for w in recent:
            lines.append(f"الاداري: {w['admin']} | الشخص: {w['user']} | السبب: {w['reason']}")
            
        embed = discord.Embed(title="آخر 10 تحذيرات", description="\n".join(lines), color=discord.Color.red())
        await msg.edit(content=None, embed=embed)

@bot.tree.command(name="هويه", description="عرض هوية شخص")
async def identity(interaction: discord.Interaction, member: discord.Member):
    await interaction.response.send_message(f"{EMOJI_LOADING} جاري التحميل...")
    u_data = get_user_data(member.id)
    idt = u_data.get("identity")
    if not idt:
        return await interaction.edit_original_response(content="هذا الشخص ليس لديه هوية مسجلة.")
        
    embed = discord.Embed(title=f"هوية: {idt['name']}", color=discord.Color.dark_theme())
    embed.add_field(name="الرقم الوطني المزيف", value=idt['phone'], inline=True)
    embed.add_field(name="الجنس", value=idt['gender'], inline=True)
    embed.add_field(name="الجنسية", value=idt['nationality'], inline=True)
    await interaction.edit_original_response(content=None, embed=embed)

@bot.tree.command(name="حذف_هويه", description="للملك فقط: حذف هوية شخص وإرجاعه للتسجيل")
async def delete_identity(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("هذا الأمر للملك فقط.", ephemeral=True)

    guild = interaction.guild
    newcomer_role = guild.get_role(ROLE_NEWCOMER)
    
    await member.edit(roles=[guild.default_role])
    if newcomer_role: await member.add_roles(newcomer_role)
    
    if member.id in db["users"]:
        phone = db["users"][member.id].get("identity", {}).get("phone")
        if phone in db["used_phones"]: db["used_phones"].remove(phone)
        del db["users"][member.id]
        
    await interaction.response.send_message(f"تم حذف هوية {member.mention} وإرجاعه لرتبة التسجيل.")

# ==========================================
# 7. أوامر إعداد الغرف (أبدأ)
# ==========================================
@bot.command(name="أبدأ١")
async def start1(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="تسجيل دخول وخروج للعسكر فقط", color=discord.Color.green())
    await ctx.send(embed=embed, view=DutyView())

@bot.command(name="أبدأ٢")
async def start2(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="حالة العساكر", description="جاري التحميل...", color=discord.Color.blue())
    msg = await ctx.send(embed=embed)
    db["live_log_msg"] = (ctx.channel.id, msg.id)
    await update_live_log()

@bot.command(name="أبدأ٣")
async def start3(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
    await ctx.message.delete()
    embed = discord.Embed(title="التحقق من الهوية", description="السلام عليكم، تأكيد دخولك للسيرفر. اضغط زر أكمل للبدء.", color=discord.Color.gold())
    await ctx.send(embed=embed, view=RegistrationView())

# ==========================================
# 8. نظام الجوع والعطش والمخزون
# ==========================================
@bot.command(name="شنطه")
async def inventory(ctx):
    u_data = get_user_data(ctx.author.id)
    h = u_data["hunger"]
    t = u_data["thirst"]
    
    def get_bar(val, is_hunger):
        filled = int((val / 100) * 10)
        color = "🟧" if is_hunger else "🟦"
        return color * filled + "⬛" * (10 - filled)
        
    embed = discord.Embed(title=f"🎒 شنطة {ctx.author.display_name}", color=discord.Color.dark_gray())
    embed.add_field(name="الجوع", value=f"{h}% {get_bar(h, True)}", inline=False)
    embed.add_field(name="العطش", value=f"{t}% {get_bar(t, False)}", inline=False)
    
    inv = u_data["inventory"]
    items_str = "\n".join([f"**{item}**: {count}" for item, count in inv.items() if count > 0])
    if not items_str: items_str = "الشنطة فارغة."
    
    embed.add_field(name="الأغراض", value=items_str, inline=False)
    embed.set_footer(text="استخدم: -استخدام [اسم الغرض] [منشن شخص اختياري للأعطاء]")
    
    # رسالة خاصة في الروم (تختفي)
    await ctx.send(embed=embed, delete_after=30.0)
    try: await ctx.message.delete()
    except: pass

@bot.command(name="استخدام")
async def use_item(ctx, item_name: str, member: discord.Member = None):
    u_data = get_user_data(ctx.author.id)
    
    if u_data["inventory"].get(item_name, 0) <= 0:
        return await ctx.send("لا تملك هذا الغرض في شنطتك.")
        
    if member is None:
        # أكل الغرض لنفسه
        u_data["inventory"][item_name] -= 1
        if u_data["inventory"][item_name] == 0: del u_data["inventory"][item_name]
        
        stats = ITEMS_DB.get(item_name)
        if stats:
            u_data["hunger"] = min(100, u_data["hunger"] + stats["hunger"])
            u_data["thirst"] = min(100, u_data["thirst"] + stats["thirst"])
            
        await ctx.send(f"🍽️ {ctx.author.mention} تم استخدام {item_name} بنجاح!")
    else:
        # إعطاء الغرض لشخص آخر
        msg = await ctx.send(f"هل تريد أن تعطيه لهذا الشخص {member.mention}؟ (نعم/لا)")
        def check(m): return m.author == ctx.author and m.channel == ctx.channel
        
        try:
            resp = await bot.wait_for('message', check=check, timeout=30.0)
            if resp.content.strip() == 'نعم':
                u_data["inventory"][item_name] -= 1
                if u_data["inventory"][item_name] == 0: del u_data["inventory"][item_name]
                
                t_data = get_user_data(member.id)
                t_data["inventory"][item_name] = t_data["inventory"].get(item_name, 0) + 1
                await ctx.send(f"تم إعطاء الشخص بنجاح.")
            else:
                await ctx.send("تم إلغاء العملية.")
        except asyncio.TimeoutError:
            await ctx.send("انتهى وقت الرد، تم إلغاء العملية.")

@bot.tree.command(name="فول", description="للملك فقط: تعبئة الجوع والعطش")
async def full(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("هذا الأمر للملك فقط.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    u_data["hunger"] = 100
    u_data["thirst"] = 100
    await interaction.response.send_message(f"تم تعبئة الجوع والعطش إلى 100% لـ {member.mention}.")

@bot.tree.command(name="منيو", description="عرض قائمة المتجر")
async def menu(interaction: discord.Interaction):
    embed = discord.Embed(title="🛒 قائمة المتجر", color=discord.Color.purple())
    for item, stats in ITEMS_DB.items():
        desc = []
        if stats["hunger"] > 0: desc.append(f"+{stats['hunger']} جوع")
        if stats["thirst"] > 0: desc.append(f"+{stats['thirst']} عطش")
        embed.add_field(name=item, value=" | ".join(desc), inline=True)
        
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="بيع", description="للتجار فقط: بيع غرض لشخص")
async def sell(interaction: discord.Interaction, item: str, member: discord.Member):
    merchant_role = interaction.guild.get_role(ROLE_MERCHANT)
    if merchant_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("فقط التجار يمكنهم استخدام هذا الأمر.", ephemeral=True)
        
    if item not in ITEMS_DB:
        return await interaction.response.send_message("الغرض غير موجود في المنيو.", ephemeral=True)
        
    t_data = get_user_data(member.id)
    t_data["inventory"][item] = t_data["inventory"].get(item, 0) + 1
    
    await interaction.response.send_message(f"✅ تم بيع {item} وإضافته في شنطة {member.mention}.")

# ==========================================
# 9. التشغيل الرئيسي
# ==========================================
if __name__ == "__main__":
    keep_alive()  # تشغيل خادم الويب في الخلفية لمنع خمول Render
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("خطأ: لم يتم العثور على توكن البوت في المتغيرات (DISCORD_TOKEN)")
    else:
        bot.run(TOKEN)
