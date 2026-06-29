"""
Rollback RP Discord Bot - main.py
Hosted on Render with Flask keep-alive thread.
All persistence via database.json.
"""

import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import random
import asyncio
import threading
from flask import Flask
from datetime import datetime

# ─────────────────────────────────────────────
#  FLASK KEEP-ALIVE (prevents Render sleeping)
# ─────────────────────────────────────────────
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Rollback Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

def keep_alive():
    t = threading.Thread(target=run_flask, daemon=True)
    t.start()

# ─────────────────────────────────────────────
#  HARDCODED IDs & CONSTANTS
# ─────────────────────────────────────────────
OWNER_ID               = 1306034100544737461
ADMIN_ROLE_ID          = 1521183344430153849
MILITARY_ON_DUTY_ID    = 1520077188135780494
MILITARY_OFF_DUTY_ID   = 1520084329714421800
NEWCOMER_ROLE_ID       = 1520087730544050436
CITIZEN_ROLE_ID        = 1474724032849907722
MALE_ROLE_ID           = 1476903628714410079
FEMALE_ROLE_ID         = 1476903782112821258

EMOJI_WARN1  = "<a:emoji_26:1520109726065496295>"
EMOJI_WARN2  = "<a:emoji_28:1520109788485128202>"
EMOJI_LOADING = "<a:emoji_26:1520109763952771204>"

DB_FILE = "database.json"

# ─────────────────────────────────────────────
#  DATABASE HELPERS
# ─────────────────────────────────────────────
def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_section(key: str) -> dict:
    db = load_db()
    return db.get(key, {})

def set_section(key: str, value):
    db = load_db()
    db[key] = value
    save_db(db)

def generate_unique_id() -> str:
    """Generate a unique 7-digit national ID starting with '17'."""
    db = load_db()
    identities = db.get("identities", {})
    existing_ids = {v.get("national_id") for v in identities.values()}
    while True:
        suffix = random.randint(10000, 99999)
        candidate = f"17{suffix}"
        if candidate not in existing_ids:
            return candidate

# ─────────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix=["!", "-"], intents=intents)
bot.remove_command("help")

# ─────────────────────────────────────────────
#  PERMISSION HELPERS
# ─────────────────────────────────────────────
def is_owner(user: discord.Member) -> bool:
    return user.id == OWNER_ID

def has_military_on_duty(user: discord.Member) -> bool:
    return any(r.id == MILITARY_ON_DUTY_ID for r in user.roles)

def has_military_any(user: discord.Member) -> bool:
    return any(r.id in (MILITARY_ON_DUTY_ID, MILITARY_OFF_DUTY_ID) for r in user.roles)

def has_admin_role(user: discord.Member) -> bool:
    return any(r.id == ADMIN_ROLE_ID for r in user.roles)

def can_moderate(user: discord.Member) -> bool:
    return is_owner(user) or has_military_on_duty(user) or has_admin_role(user)

# ─────────────────────────────────────────────
#  LIVE SURVEILLANCE LOG UPDATER
# ─────────────────────────────────────────────
async def update_surveillance_log(guild: discord.Guild):
    """Edit the surveillance embed with current military duty statuses."""
    db = load_db()
    log_info = db.get("surveillance_log", {})
    channel_id = log_info.get("channel_id")
    message_id = log_info.get("message_id")
    if not channel_id or not message_id:
        return

    channel = guild.get_channel(int(channel_id))
    if not channel:
        return

    try:
        msg = await channel.fetch_message(int(message_id))
    except (discord.NotFound, discord.HTTPException):
        return

    identities = db.get("identities", {})
    on_duty_role  = guild.get_role(MILITARY_ON_DUTY_ID)
    off_duty_role = guild.get_role(MILITARY_OFF_DUTY_ID)

    on_duty_members  = set(m.id for m in (on_duty_role.members  if on_duty_role  else []))
    off_duty_members = set(m.id for m in (off_duty_role.members if off_duty_role else []))
    all_military = on_duty_members | off_duty_members

    lines = []
    for uid in all_military:
        uid_str = str(uid)
        rp_name = identities.get(uid_str, {}).get("name", f"<@{uid}>")
        if uid in on_duty_members:
            lines.append(f"**{rp_name}** متصل 🟢")
        else:
            lines.append(f"**{rp_name}** غير متصل 🔴")

    description = "\n".join(lines) if lines else "لا يوجد أفراد عسكريون مسجلون حالياً."

    embed = discord.Embed(
        title="البث المراقب لتسجيلات الدخول والخروج",
        description=description,
        color=discord.Color.dark_blue(),
        timestamp=datetime.utcnow()
    )
    embed.set_footer(text="آخر تحديث")

    try:
        await msg.edit(embed=embed)
    except discord.HTTPException:
        pass

# ─────────────────────────────────────────────
#  PERSISTENT VIEW: DUTY TOGGLE  (System 1)
# ─────────────────────────────────────────────
class DutyToggleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="تسجيل دخول وا خروج",
        style=discord.ButtonStyle.success,
        custom_id="duty_toggle_btn"
    )
    async def duty_toggle(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        on_duty_role  = interaction.guild.get_role(MILITARY_ON_DUTY_ID)
        off_duty_role = interaction.guild.get_role(MILITARY_OFF_DUTY_ID)

        has_on  = any(r.id == MILITARY_ON_DUTY_ID  for r in member.roles)
        has_off = any(r.id == MILITARY_OFF_DUTY_ID for r in member.roles)

        if not has_on and not has_off:
            await interaction.response.send_message(
                "❌ هذا الزر مخصص للأفراد العسكريين فقط.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)

        if has_off:
            if off_duty_role:
                await member.remove_roles(off_duty_role)
            if on_duty_role:
                await member.add_roles(on_duty_role)
            await interaction.followup.send("✅ تم تسجيل دخول بنجاح", ephemeral=True)
        else:
            if on_duty_role:
                await member.remove_roles(on_duty_role)
            if off_duty_role:
                await member.add_roles(off_duty_role)
            await interaction.followup.send("✅ تم تسجيل خروج بنجاح", ephemeral=True)

        await update_surveillance_log(interaction.guild)


# ─────────────────────────────────────────────
#  PERSISTENT VIEW: REGISTRATION BUTTON  (System 3)
# ─────────────────────────────────────────────
class RegistrationView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="تسجيل الهوية",
        style=discord.ButtonStyle.primary,
        custom_id="registration_btn",
        emoji="📋"
    )
    async def open_registration(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        has_newcomer = any(r.id == NEWCOMER_ROLE_ID for r in member.roles)
        if not has_newcomer:
            await interaction.response.send_message(
                "❌ هذا الزر مخصص للأعضاء الجدد فقط.", ephemeral=True
            )
            return
        db = load_db()
        if str(member.id) in db.get("identities", {}):
            await interaction.response.send_message(
                "⚠️ لديك هوية مسجلة بالفعل.", ephemeral=True
            )
            return
        await interaction.response.send_modal(RegistrationModal())


class RegistrationModal(discord.ui.Modal, title="نموذج تسجيل الهوية"):
    rp_name = discord.ui.TextInput(
        label="الاسم",
        placeholder="أدخل اسمك داخل اللعبة",
        required=True,
        max_length=50
    )
    age = discord.ui.TextInput(
        label="العمر",
        placeholder="أدخل عمرك",
        required=True,
        max_length=3
    )
    nationality = discord.ui.TextInput(
        label="الجنسية",
        placeholder="أدخل جنسيتك",
        required=True,
        max_length=30
    )
    gender = discord.ui.TextInput(
        label="الجنس (ذكر أو انثى)",
        placeholder="ذكر أو انثى",
        required=True,
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        member = interaction.user
        guild  = interaction.guild

        gender_input = self.gender.value.strip()
        if gender_input not in ("ذكر", "انثى"):
            await interaction.followup.send(
                "❌ الجنس يجب أن يكون **ذكر** أو **انثى** فقط.", ephemeral=True
            )
            return

        national_id = generate_unique_id()

        db = load_db()
        identities = db.get("identities", {})
        identities[str(member.id)] = {
            "name":        self.rp_name.value.strip(),
            "age":         self.age.value.strip(),
            "nationality": self.nationality.value.strip(),
            "gender":      gender_input,
            "national_id": national_id,
            "registered_at": datetime.utcnow().isoformat()
        }
        db["identities"] = identities
        save_db(db)

        newcomer_role = guild.get_role(NEWCOMER_ROLE_ID)
        citizen_role  = guild.get_role(CITIZEN_ROLE_ID)
        male_role     = guild.get_role(MALE_ROLE_ID)
        female_role   = guild.get_role(FEMALE_ROLE_ID)

        roles_to_remove = [r for r in [newcomer_role] if r and r in member.roles]
        roles_to_add    = [r for r in [citizen_role] if r]
        if gender_input == "ذكر" and male_role:
            roles_to_add.append(male_role)
        elif gender_input == "انثى" and female_role:
            roles_to_add.append(female_role)

        try:
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove)
            if roles_to_add:
                await member.add_roles(*roles_to_add)
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ تم تسجيل بياناتك لكن البوت لا يملك صلاحية تعديل أدوارك.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="✅ تم تسجيل هويتك بنجاح!",
            color=discord.Color.green()
        )
        embed.add_field(name="الاسم",       value=self.rp_name.value.strip(), inline=True)
        embed.add_field(name="الرقم الوطني", value=national_id,               inline=True)
        embed.add_field(name="العمر",        value=self.age.value.strip(),     inline=True)
        embed.add_field(name="الجنسية",      value=self.nationality.value.strip(), inline=True)
        embed.add_field(name="الجنس",        value=gender_input,               inline=True)
        embed.set_footer(text="مرحباً بك في Rollback RP!")
        await interaction.followup.send(embed=embed, ephemeral=True)


# ─────────────────────────────────────────────
#  BOT EVENTS
# ─────────────────────────────────────────────
@bot.event
async def on_ready():
    # Re-register persistent views so buttons survive restarts
    bot.add_view(DutyToggleView())
    bot.add_view(RegistrationView())

    try:
        synced = await bot.tree.sync()
        print(f"[BOT] Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"[BOT] Slash sync error: {e}")

    print(f"[BOT] Logged in as {bot.user} (ID: {bot.user.id})")


# ─────────────────────────────────────────────
#  SETUP COMMANDS  (!أبدأ١ / !أبدأ٢ / !أبدأ٣)
# ─────────────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    content = message.content.strip()

    # ── !أبدأ١  (Duty Toggle System) ──────────────────────────
    if content == "!أبدأ١":
        if message.author.id != OWNER_ID:
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        embed = discord.Embed(
            title="🪖 نظام تسجيل الدوام العسكري",
            description="اضغط على الزر أدناه لتسجيل الدخول أو الخروج من الدوام.",
            color=discord.Color.green()
        )
        embed.set_footer(text="Rollback RP • Military System")
        await message.channel.send(embed=embed, view=DutyToggleView())
        return

    # ── !أبدأ٢  (Live Surveillance Log) ───────────────────────
    if content == "!أبدأ٢":
        if message.author.id != OWNER_ID:
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        embed = discord.Embed(
            title="البث المراقب لتسجيلات الدخول والخروج",
            description="جاري التحميل...",
            color=discord.Color.dark_blue(),
            timestamp=datetime.utcnow()
        )
        embed.set_footer(text="آخر تحديث")
        sent = await message.channel.send(embed=embed)

        db = load_db()
        db["surveillance_log"] = {
            "channel_id": str(message.channel.id),
            "message_id": str(sent.id)
        }
        save_db(db)

        await update_surveillance_log(message.guild)
        return

    # ── !أبدأ٣  (Identity & Registration System) ──────────────
    if content == "!أبدأ٣":
        if message.author.id != OWNER_ID:
            return
        try:
            await message.delete()
        except discord.HTTPException:
            pass

        embed = discord.Embed(
            title="📋 نظام تسجيل الهوية",
            description=(
                "مرحباً بك في **Rollback RP**!\n\n"
                "اضغط على الزر أدناه لتسجيل هويتك في اللعبة وإنشاء شخصيتك الخاصة.\n\n"
                "⚠️ **ملاحظة:** هذا الزر مخصص للأعضاء الجدد فقط."
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text="Rollback RP • Identity System")
        await message.channel.send(embed=embed, view=RegistrationView())
        return

    await bot.process_commands(message)


# ─────────────────────────────────────────────
#  PREFIX COMMAND: -رول  (Role Toggle)
# ─────────────────────────────────────────────
@bot.command(name="رول")
async def role_toggle(ctx: commands.Context, member: discord.Member = None, role: discord.Role = None):
    if not can_moderate(ctx.author):
        await ctx.send("❌ ليس لديك صلاحية استخدام هذا الأمر.")
        return

    if member is None or role is None:
        await ctx.send("❌ الاستخدام الصحيح: `-رول @العضو @الرتبة`")
        return

    # Security check: dangerous permissions
    dangerous = (
        role.permissions.administrator or
        role.permissions.manage_guild or
        role.permissions.manage_roles
    )
    if dangerous:
        await ctx.send(
            f"⛔ لا يمكن إعطاء أو إزالة الرتبة **{role.name}** لأنها تحتوي على صلاحيات خطيرة."
        )
        return

    loading_msg = await ctx.send(f"{EMOJI_LOADING} جاري التنفيذ...")

    try:
        if role in member.roles:
            await member.remove_roles(role)
            action = f"تم إزالة رتبة **{role.name}** من {member.mention} ✅"
        else:
            await member.add_roles(role)
            action = f"تم إعطاء رتبة **{role.name}** لـ {member.mention} ✅"
        await loading_msg.edit(content=action)
    except discord.Forbidden:
        await loading_msg.edit(content="❌ البوت لا يملك صلاحية تعديل هذه الرتبة.")
    except discord.HTTPException as e:
        await loading_msg.edit(content=f"❌ حدث خطأ: {e}")


# ─────────────────────────────────────────────
#  PREFIX COMMAND: -تحذيرات  (View Warnings)
# ─────────────────────────────────────────────
@bot.command(name="تحذيرات")
async def view_warnings(ctx: commands.Context, member: discord.Member = None):
    db = load_db()
    warnings_db = db.get("warnings", {})

    if member:
        user_warns = warnings_db.get(str(member.id), [])
        if not user_warns:
            await ctx.send(f"✅ {member.mention} لا يوجد لديه أي تحذيرات.")
            return
        embed = discord.Embed(
            title=f"⚠️ تحذيرات {member.display_name}",
            description=f"إجمالي التحذيرات: **{len(user_warns)}**",
            color=discord.Color.orange()
        )
        for i, w in enumerate(user_warns, 1):
            officer = w.get("officer_name", "غير معروف")
            reason  = w.get("reason", "—")
            date    = w.get("date", "—")
            embed.add_field(
                name=f"تحذير #{i}",
                value=f"📌 السبب: {reason}\n👮 الضابط: {officer}\n📅 التاريخ: {date}",
                inline=False
            )
        await ctx.send(embed=embed)
    else:
        # Global last 10 warnings
        all_warnings = []
        for uid, warns in warnings_db.items():
            for w in warns:
                all_warnings.append({"uid": uid, **w})

        all_warnings.sort(key=lambda x: x.get("date", ""), reverse=True)
        last_10 = all_warnings[:10]

        if not last_10:
            await ctx.send("✅ لا يوجد أي تحذيرات في السيرفر حتى الآن.")
            return

        embed = discord.Embed(
            title="📋 آخر 10 تحذيرات في السيرفر",
            color=discord.Color.red()
        )
        for w in last_10:
            uid     = w.get("uid", "?")
            reason  = w.get("reason", "—")
            officer = w.get("officer_name", "غير معروف")
            date    = w.get("date", "—")
            embed.add_field(
                name=f"<@{uid}>",
                value=f"📌 السبب: {reason}\n👮 الضابط: {officer}\n📅 {date}",
                inline=False
            )
        await ctx.send(embed=embed)


# ─────────────────────────────────────────────
#  SLASH COMMANDS
# ─────────────────────────────────────────────

# /تحذير
@bot.tree.command(name="تحذير", description="تحذير عضو وتسجيل التحذير")
@app_commands.describe(member="العضو المراد تحذيره", reason="سبب التحذير")
async def warn_user(interaction: discord.Interaction, member: discord.Member, reason: str):
    if not can_moderate(interaction.user):
        await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الأمر.", ephemeral=True)
        return

    await interaction.response.send_message(f"{EMOJI_LOADING} جاري التنفيذ...")

    db = load_db()
    warnings = db.get("warnings", {})
    uid_str = str(member.id)
    if uid_str not in warnings:
        warnings[uid_str] = []

    warn_entry = {
        "reason":       reason,
        "officer_id":   str(interaction.user.id),
        "officer_name": interaction.user.display_name,
        "date":         datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    }
    warnings[uid_str].append(warn_entry)
    db["warnings"] = warnings
    save_db(db)

    # Public message
    public_msg = (
        f"{EMOJI_WARN1} {member.mention}\n"
        f"**تم توجيه تحذير رسمي لك**\n"
        f"📌 السبب: **{reason}**\n"
        f"👮 الضابط المسؤول: **{interaction.user.display_name}**"
    )
    await interaction.edit_original_response(content=public_msg)

    # DM to warned user
    dm_embed = discord.Embed(
        title=f"{EMOJI_WARN2} تحذير رسمي",
        description=(
            f"تلقيت تحذيراً رسمياً في سيرفر **Rollback RP**.\n\n"
            f"📌 **السبب:** {reason}\n"
            f"👮 **الضابط المسؤول:** {interaction.user.display_name}\n"
            f"📅 **التاريخ:** {warn_entry['date']}\n\n"
            f"يُرجى الالتزام بقواعد السيرفر لتجنب العواقب."
        ),
        color=discord.Color.red()
    )
    dm_embed.set_footer(text="Rollback RP • Military System")
    try:
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass  # DMs disabled — silently continue


# /شيل
@bot.tree.command(name="شيل", description="مسح جميع تحذيرات عضو")
@app_commands.describe(member="العضو المراد مسح تحذيراته")
async def clear_warnings(interaction: discord.Interaction, member: discord.Member):
    if not can_moderate(interaction.user):
        await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الأمر.", ephemeral=True)
        return

    await interaction.response.send_message(f"{EMOJI_LOADING} جاري المسح...")

    db = load_db()
    warnings = db.get("warnings", {})
    uid_str = str(member.id)

    count = len(warnings.get(uid_str, []))
    if uid_str in warnings:
        del warnings[uid_str]
    db["warnings"] = warnings
    save_db(db)

    await interaction.edit_original_response(
        content=f"✅ تم مسح **{count}** تحذير(ات) للعضو {member.mention}."
    )


# /هويه
@bot.tree.command(name="هويه", description="عرض هوية عضو")
@app_commands.describe(member="العضو المراد عرض هويته")
async def show_identity(interaction: discord.Interaction, member: discord.Member):
    if not can_moderate(interaction.user):
        await interaction.response.send_message("❌ ليس لديك صلاحية استخدام هذا الأمر.", ephemeral=True)
        return

    await interaction.response.defer()

    db = load_db()
    identity = db.get("identities", {}).get(str(member.id))

    if not identity:
        await interaction.followup.send(f"❌ لا توجد هوية مسجلة للعضو {member.mention}.")
        return

    embed = discord.Embed(
        title="🪪 بطاقة الهوية الشخصية",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="الاسم",           value=identity.get("name", "—"),        inline=True)
    embed.add_field(name="الرقم الوطني",    value=identity.get("national_id", "—"), inline=True)
    embed.add_field(name="العمر",           value=identity.get("age", "—"),         inline=True)
    embed.add_field(name="الجنسية",         value=identity.get("nationality", "—"), inline=True)
    embed.add_field(name="الجنس",           value=identity.get("gender", "—"),      inline=True)
    embed.set_footer(text=f"Rollback RP • ID: {identity.get('national_id', '—')}")
    await interaction.followup.send(embed=embed)


# /حذف_هويه
@bot.tree.command(name="حذف_هويه", description="حذف هوية عضو وإعادته للتسجيل (مشرفون فقط)")
@app_commands.describe(member="العضو المراد حذف هويته")
async def delete_identity(interaction: discord.Interaction, member: discord.Member):
    # Strictly requires Admin Role or Owner
    if not (is_owner(interaction.user) or has_admin_role(interaction.user)):
        await interaction.response.send_message(
            "❌ هذا الأمر مخصص لمشرفي الإدارة فقط.", ephemeral=True
        )
        return

    await interaction.response.defer()

    db = load_db()
    identities = db.get("identities", {})
    uid_str = str(member.id)

    if uid_str not in identities:
        await interaction.followup.send(f"❌ لا توجد هوية مسجلة للعضو {member.mention}.")
        return

    del identities[uid_str]
    db["identities"] = identities
    save_db(db)

    # Strip all roles and give Newcomer
    guild = interaction.guild
    newcomer_role = guild.get_role(NEWCOMER_ROLE_ID)
    try:
        # Remove all assignable roles except @everyone and bot-managed roles
        removable = [
            r for r in member.roles
            if r != guild.default_role and not r.managed
        ]
        if removable:
            await member.remove_roles(*removable, reason="حذف الهوية بواسطة الإدارة")
        if newcomer_role:
            await member.add_roles(newcomer_role, reason="إعادة تعيين دور الوافد الجديد")
    except discord.Forbidden:
        await interaction.followup.send(
            "⚠️ تم حذف الهوية من قاعدة البيانات لكن البوت لا يملك صلاحية تعديل الأدوار."
        )
        return

    # DM the affected member
    try:
        dm_embed = discord.Embed(
            title="⚠️ تم حذف هويتك",
            description=(
                f"قام فريق الإدارة في **Rollback RP** بحذف هويتك وإلغاء تسجيلك.\n\n"
                f"يجب عليك إعادة التسجيل من جديد لاستخدام ميزات السيرفر.\n"
                f"للتسجيل، توجه إلى قناة التسجيل واضغط على زر **تسجيل الهوية**."
            ),
            color=discord.Color.dark_red()
        )
        dm_embed.set_footer(text="Rollback RP • Administration")
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    await interaction.followup.send(
        f"✅ تم حذف هوية {member.mention} بالكامل وإعادته إلى دور الوافد الجديد."
    )


# ─────────────────────────────────────────────
#  GLOBAL ERROR HANDLER
# ─────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.MemberNotFound):
        await ctx.send("❌ لم يتم العثور على العضو المذكور.")
    elif isinstance(error, commands.RoleNotFound):
        await ctx.send("❌ لم يتم العثور على الرتبة المذكورة.")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ ينقصك وسيط: `{error.param.name}`")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("❌ وسيط غير صحيح. تحقق من المنشن.")
    else:
        print(f"[ERROR] {error}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    msg = f"❌ حدث خطأ: {error}"
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
    print(f"[SLASH ERROR] {error}")


# ─────────────────────────────────────────────
#  ENTRY POINT
# ─────────────────────────────────────────────
if __name__ == "__main__":
    keep_alive()
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise ValueError("DISCORD_TOKEN environment variable not set!")
    bot.run(token)
