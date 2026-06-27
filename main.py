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

db = {
    "users": {},
    "used_phones": set(),
    "live_log_msg": None,
    "warnings": [],
    "registering_users": set() # لمنع التكرار في زر الهوية
}

def get_user_data(user_id):
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "identity": None,
            "hunger": 100,
            "thirst": 100,
            "health": 100, # نظام الصحة الجديد
            "inventory": {},
            "warnings_count": 0
        }
    return db["users"][user_id]

# ==========================================
# 4. الأحداث ونظام البقاء (الصحة والجوع)
# ==========================================
@bot.event
async def on_ready():
    print(f"تم تسجيل الدخول كـ {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"تمت مزامنة {len(synced)} أمر Slash.")
    except Exception as e:
        print(f"خطأ في المزامنة: {e}")
    
    if not minute_survival_loop.is_running():
        minute_survival_loop.start()

@bot.event
async def on_member_join(member):
    newcomer_role = member.guild.get_role(ROLE_NEWCOMER)
    if newcomer_role:
        await member.add_roles(newcomer_role)

@tasks.loop(minutes=1)
async def minute_survival_loop():
    """لوب ينفذ كل دقيقة لنظام البقاء والصحة"""
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot: continue
            
            is_active = str(member.status) != "offline" or member.get_role(ROLE_ON_DUTY)
            if is_active:
                u_data = get_user_data(member.id)
                # انخفاض الجوع والعطش ببطء (تقريباً 1 كل دقيقة = 60 في الساعة)
                u_data["hunger"] = max(0, u_data["hunger"] - 1)
                u_data["thirst"] = max(0, u_data["thirst"] - 1)
                
                h, t, hp = u_data["hunger"], u_data["thirst"], u_data["health"]
                
                # التنبيهات
                if h == 25 or t == 25:
                    try: await member.send("⚠️ **تحذير:** أنت جائع أو عطشان. نسبتك وصلت 25%. يرجى الشراء والأكل.")
                    except: pass
                elif h == 15 or t == 15:
                    try: await member.send("🚨 **تحذير خطير:** نسبتك وصلت 15%! كُل أو اشرب فوراً.")
                    except: pass
                elif h == 5 or t == 5:
                    try: await member.send("☠️ **تنبيه أخير:** باقي لك 5 وتروح للتوقيف! تصرف فوراً.")
                    except: pass

                # نظام الصحة (ينقص 2 إذا الجوع والعطش 0)
                if h == 0 and t == 0:
                    u_data["health"] = max(0, hp - 2)
                    if u_data["health"] == 0:
                        try:
                            # يعطيه رتبة الميت/التوقيف
                            roles_to_keep = [guild.default_role]
                            if member.get_role(ROLE_MALE): roles_to_keep.append(guild.get_role(ROLE_MALE))
                            if member.get_role(ROLE_FEMALE): roles_to_keep.append(guild.get_role(ROLE_FEMALE))
                            
                            dead_role = guild.get_role(ROLE_DEAD)
                            if dead_role: roles_to_keep.append(dead_role)
                            
                            await member.edit(roles=roles_to_keep)
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
class InventoryView(discord.ui.View):
    def __init__(self, user_id, inventory):
        super().__init__(timeout=15.0) # يختفي بعد 15 ثانية
        self.user_id = user_id
        for item_name, count in inventory.items():
            if count > 0:
                btn = discord.ui.Button(label=f"{item_name} ({count})", style=discord.ButtonStyle.primary, custom_id=f"use_{item_name}")
                btn.callback = self.create_callback(item_name)
                self.add_item(btn)

    def create_callback(self, item_name):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return await interaction.response.send_message("❌ هذه الشنطة ليست لك، لا يمكنك استخدامها!", ephemeral=True)
            
            u_data = get_user_data(self.user_id)
            if u_data["inventory"].get(item_name, 0) <= 0:
                return await interaction.response.send_message("لم يعد لديك هذا الغرض.", ephemeral=True)

            # خصم الغرض واستخدامه
            u_data["inventory"][item_name] -= 1
            if u_data["inventory"][item_name] == 0: del u_data["inventory"][item_name]
            
            stats = ITEMS_DB.get(item_name)
            if stats:
                u_data["hunger"] = min(100, u_data["hunger"] + stats["hunger"])
                u_data["thirst"] = min(100, u_data["thirst"] + stats["thirst"])
                u_data["health"] = min(100, u_data["health"] + 5) # ريفريش بسيط للصحة
            
            await interaction.response.send_message(f"🍽️ تم أكل/شرب **{item_name}** بنجاح!", ephemeral=True)
            self.stop() # يوقف الأزرار بعد الاستخدام لتحديث الشنطة
        return callback

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
        if role in interaction.user.roles:
            return await interaction.response.send_message("أنت مسجل بالفعل.", ephemeral=True)
        
        if role: await interaction.user.add_roles(role)
        await interaction.response.send_message("تم إعطاؤك رتبة متدرب. سيتم تدريبك قريباً.", ephemeral=True)

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
            return await interaction.response.send_message("تم إرسال رسالة لك في الخاص بالفعل! راجع رسائلك وإذا أردت الإلغاء اكتب 'لا' هناك.", ephemeral=True)
            
        db["registering_users"].add(member.id)
        await interaction.response.send_message("تم إرسال رسالة لك في الخاص لإكمال تسجيلك.", ephemeral=True)
        
        try:
            await member.send("مرحباً بك في سيرفر رولباك! هل تريد أن تصنع هويتك في السيرفر للمزح واللعب فقط؟ (نعم/لا)")
            def check(m): return m.author == member and isinstance(m.channel, discord.DMChannel)
            
            resp1 = await bot.wait_for('message', check=check, timeout=120)
            if resp1.content.lower() != 'نعم':
                db["registering_users"].remove(member.id)
                return await member.send("تم الإلغاء. يمكنك العودة للسيرفر والضغط على الزر متى ما شئت.")

            await member.send("حسناً، اكتب اسمك المستعار أو الحقيقي:")
            name_msg = await bot.wait_for('message', check=check, timeout=120)
            if name_msg.content == "الغاء": 
                db["registering_users"].remove(member.id)
                return await member.send("تم الإلغاء.")
            name = name_msg.content

            phone = ""
            while True:
                await member.send("اكتب رقم هاتف مزيف يبدأ بـ 17 مكون من 7 أرقام (مثال: 1712345):")
                phone_msg = await bot.wait_for('message', check=check, timeout=120)
                phone_input = phone_msg.content.strip()
                if phone_input == "الغاء":
                    db["registering_users"].remove(member.id)
                    return await member.send("تم الإلغاء.")
                
                if phone_input.startswith("17") and len(phone_input) == 7:
                    if phone_input in db["used_phones"]:
                        await member.send("هذا الرقم عند شخص آخر، الرجاء اختيار رقم مختلف.")
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
            
            # رسالة الترحيب في الروم المخصص
            welcome_channel = bot.get_channel(CHANNEL_WELCOME)
            if welcome_channel:
                await welcome_channel.send(f"منور ام السيرفر يا {name} {member.mention}")
                
            db["registering_users"].remove(member.id)
            
        except asyncio.TimeoutError:
            db["registering_users"].discard(member.id)
            await member.send("انتهى وقت التسجيل. الرجاء الضغط على الزر في السيرفر مرة أخرى.")
        except discord.Forbidden:
            db["registering_users"].discard(member.id)

# ==========================================
# 6. أوامر السيرفر (Slash)
# ==========================================
@bot.tree.command(name="رول", description="إعطاء أو إزالة رتبة من شخص")
async def slash_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    if not interaction.user.guild_permissions.manage_roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("لا تملك صلاحية.", ephemeral=True)
        
    if role.permissions.administrator or role.permissions.manage_guild or role.permissions.ban_members:
        return await interaction.response.send_message("هذه رتبة إدارية عليا، ممنوع.", ephemeral=True)

    try:
        if role in member.roles:
            await member.remove_roles(role)
            await interaction.response.send_message(f"تم سحب رتبة {role.name} من {member.mention}.")
        else:
            await member.add_roles(role)
            await interaction.response.send_message(f"تم إعطاء رتبة {role.name} لـ {member.mention}.")
    except discord.Forbidden:
        await interaction.response.send_message("حدث خطأ! رتبة البوت أقل من الرتبة المراد إعطاؤها. ارفع رتبة البوت في الإعدادات.", ephemeral=True)

@bot.tree.command(name="حبس", description="حجز/حبس شخص")
async def jail(interaction: discord.Interaction, member: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("للعسكر فقط.", ephemeral=True)
        
    jail_role = interaction.guild.get_role(ROLE_JAIL)
    await member.add_roles(jail_role)
    await interaction.response.send_message(f"تم حبس {member.mention} بنجاح.")

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

@bot.tree.command(name="شنطه", description="عرض مخزونك واستخدام الأغراض")
async def slash_inventory(interaction: discord.Interaction):
    u_data = get_user_data(interaction.user.id)
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
    
    # حذف الرسالة بعد 15 ثانية للتنظيف
    await asyncio.sleep(15)
    try: await interaction.delete_original_response()
    except: pass

@bot.tree.command(name="هويه", description="عرض هوية شخص (للعسكر)")
async def identity(interaction: discord.Interaction, member: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("هذا الأمر للعسكر فقط.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    idt = u_data.get("identity")
    if not idt: return await interaction.response.send_message("هذا الشخص ليس لديه هوية.")
        
    embed = discord.Embed(title=f"هوية: {idt['name']}", color=discord.Color.dark_theme())
    embed.add_field(name="الرقم الوطني", value=idt['phone'], inline=True)
    embed.add_field(name="الجنس", value=idt['gender'], inline=True)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="دخول", description="الموافقة/الرفض على دخول شخص (للعسكر)")
@app_commands.choices(choice=[
    app_commands.Choice(name="نعم", value="yes"),
    app_commands.Choice(name="لا", value="no")
])
async def enter_cmd(interaction: discord.Interaction, choice: app_commands.Choice[str], member: discord.Member):
    military_role = interaction.guild.get_role(ROLE_MILITARY)
    if military_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("للعسكر فقط.", ephemeral=True)
        
    enter_role = interaction.guild.get_role(ROLE_ENTER)
    if choice.value == "yes":
        await member.add_roles(enter_role)
        await interaction.response.send_message(f"تم الموافقة لـ {member.mention} وإعطاؤه الرتبة.")
    else:
        if enter_role in member.roles: await member.remove_roles(enter_role)
        await interaction.response.send_message(f"تم رفض دخول {member.mention} (وسحب الرتبة إن وجدت).")

@bot.tree.command(name="انهاء", description="إنهاء تدريب عسكري")
async def finish_training(interaction: discord.Interaction, member: discord.Member):
    trainer_role = interaction.guild.get_role(ROLE_TRAINER)
    if trainer_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("هذا الأمر للمدربين فقط.", ephemeral=True)
        
    trainee_role = interaction.guild.get_role(ROLE_TRAINEE)
    if trainee_role not in member.roles:
        return await interaction.response.send_message("هذا الشخص ليس لديه رتبة متدرب.", ephemeral=True)
        
    await member.remove_roles(trainee_role)
    await member.add_roles(interaction.guild.get_role(ROLE_MILITARY), interaction.guild.get_role(ROLE_SOLDIER))
    
    await interaction.response.send_message(f"🎉 تم إنهاء تدريب {member.mention} وتخريجه كجندي عسكري!")

@bot.tree.command(name="منيو", description="عرض قائمة المتجر")
async def menu(interaction: discord.Interaction):
    merchant_role = interaction.guild.get_role(ROLE_MERCHANT)
    if merchant_role not in interaction.user.roles and interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("فقط التجار يمكنهم رؤية/كتابة المنيو.", ephemeral=True)
        
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

@bot.tree.command(name="فول", description="للملك فقط: تعبئة الجوع والعطش والصحة")
async def full(interaction: discord.Interaction, member: discord.Member):
    if interaction.user.id != OWNER_ID:
        return await interaction.response.send_message("هذا الأمر للملك فقط.", ephemeral=True)
        
    u_data = get_user_data(member.id)
    u_data["hunger"] = 100
    u_data["thirst"] = 100
    u_data["health"] = 100
    await interaction.response.send_message(f"تم تعبئة الجوع والعطش والصحة إلى 100% لـ {member.mention}.")

# ==========================================
# 7. أوامر التجهيزات الإدارية (!أبدأ)
# ==========================================
@bot.command(name="أبدأ٣")
async def start3(ctx):
    if not ctx.author.guild_permissions.administrator and ctx.author.id != OWNER_ID: return
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
