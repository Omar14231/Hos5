import os
import asyncio
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

# --- 1. إعداد سيرفر HTTP لتوافق Render (Web Service) ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running online 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# تشغيل سيرفر HTTP في خيط منفصل (Thread)
threading.Thread(target=run_flask, daemon=True).start()


# --- 2. إعدادات بوت ديسكورد ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

# خيارات استخراج الصوت بدقة فائقة من مختلف المنصات
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -filter:a "volume=1.25"', # تحسين جودة ورفع مستوى الصوت قليلاً
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

# --- 3. الأحداث والأوامر ---

@bot.event
async def on_ready():
    print(f'تم تسجبل الدخول باسم: {bot.user.name}')
    try:
        synced = await bot.tree.sync()
        print(f"تم مزامنة {len(synced)} من أوامر السلاش (/ commands).")
    except Exception as e:
        print(f"خطأ في مزامنة الأوامر: {e}")

# الاستجابة للرسالة "-ادخل"
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # التأكد من النص
    if message.content.strip() == "-ادخل":
        # حذف رسالة المستخدم
        try:
            await message.delete()
        except discord.errors.Forbidden:
            pass

        # التحقق مما إذا كان العضو في روم صوتي
        if message.author.voice and message.author.voice.channel:
            channel = message.author.voice.channel
            # الانضمام للروم
            if message.guild.voice_client is not None:
                await message.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
        else:
            # إذا لم يكن في روم صوتي، يرسل تنبيه مؤقت
            temp_msg = await message.channel.send(f"{message.author.mention}، يجب أن تكون في روم صوتي أولاً!")
            await asyncio.sleep(5)
            await temp_msg.delete()

    await bot.process_commands(message)

# أمر السلاش: /link
@bot.tree.command(name="link", description="تشغيل صوت المقطع من أي منصة (تيك توك، تويتر، يوتيوب...)")
@app_commands.describe(المقطع="رابط المقطع المراد تشغيله")
async def play_link(interaction: discord.Interaction, المقطع: str):
    await interaction.response.defer() # الانتظار لعدم حدوث Timeout

    # التحقق من وجود البوت في روم صوتي أو وجود المستخدم في روم
    guild = interaction.guild
    voice_client = guild.voice_client

    if not voice_client:
        if interaction.user.voice and interaction.user.voice.channel:
            voice_client = await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("البوت ليس في روم صوتي! اكتب `-ادخل` في الشات أولاً أو انضم لروم صوتي.")
            return

    try:
        # استخراج بيانات الرابط بواسطة yt-dlp
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(المقطع, download=False))

        if 'entries' in data:
            data = data['entries'][0]

        audio_url = data['url']
        title = data.get('title', 'مقطع فيديو')

        # إيقاف أي صوت شغال حالياً
        if voice_client.is_playing():
            voice_client.stop()

        # تشغيل الصوت من خلال FFmpeg
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        voice_client.play(source)

        embed = discord.Embed(
            title="🎶 جاري تشغيل الصوت بأعلى جودة",
            description=f"**العنوان/المقطع:** [{title}]({المقطع})",
            color=discord.Color.green()
        )
        embed.set_footer(text="يمكنك فتح الرابط لمشاهدة الفيديو أثناء الاستماع للصوت!")
        
        await interaction.followup.send(embed=embed)

    except Exception as e:
        await interaction.followup.send(f"حدث خطأ أثناء جلب الرابط، تأكد من صحة الرابط أو جرب رابطاً آخر.\n`التفاصيل: {e}`")

# --- 4. تشغيل البوت ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("خطأ: متغير DISCORD_TOKEN غير موجود!")
