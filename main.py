import os
import asyncio
import threading
from flask import Flask
import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp

# --- سيرفر HTTP عشان Render ما يطفي البوت ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running online 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

threading.Thread(target=run_flask, daemon=True).start()

# --- إعدادات ديسكورد ---
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="-", intents=intents)

# إعدادات الصوت والبحث (يدعم الروابط والبحث بالنص)
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'default_search': 'ytsearch', # هذي تخلي البوت يبحث بالنص إذا ما عطيته رابط
    'source_address': '0.0.0.0',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

@bot.event
async def on_ready():
    print(f'تم تشغيل البوت باسم: {bot.user.name}')
    await bot.tree.sync()

# --- أمر الدخول للروم (-ادخل) ---
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.strip() == "-ادخل":
        if message.author.voice and message.author.voice.channel:
            channel = message.author.voice.channel
            if message.guild.voice_client is not None:
                await message.guild.voice_client.move_to(channel)
            else:
                await channel.connect()
            await message.channel.send("🎤 دخلت معك في الروم الصوتي!")
        else:
            await message.channel.send("لازم تكون في روم صوتي أول عشان أدخل معك!")

    # مهم عشان باقي الأوامر تشتغل
    await bot.process_commands(message)

# --- أمر التشغيل (/play) ---
@bot.tree.command(name="play", description="تشغيل مقطع عن طريق رابط أو اكتب اسم المقطع للبحث")
@app_commands.describe(بحث="حط الرابط هنا، أو اكتب اسم المقطع للبحث عنه")
async def play_audio(interaction: discord.Interaction, بحث: str):
    await interaction.response.defer()

    voice_client = interaction.guild.voice_client

    # إذا البوت مو في الروم، يدخل تلقائي
    if not voice_client:
        if interaction.user.voice and interaction.user.voice.channel:
            voice_client = await interaction.user.voice.channel.connect()
        else:
            await interaction.followup.send("البوت مو في الروم! اكتب `-ادخل` أو ادخل روم صوتي.")
            return

    try:
        loop = asyncio.get_event_loop()
        # استخراج البيانات (سواء رابط أو نص)
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(بحث, download=False))

        # إذا كان بحث نصي، بيجيب أول نتيجة
        if 'entries' in data:
            data = data['entries'][0]

        audio_url = data['url']
        title = data.get('title', 'مقطع صوتي')

        # إيقاف أي مقطع شغال حالياً
        if voice_client.is_playing():
            voice_client.stop()

        # التشغيل
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        voice_client.play(source)

        await interaction.followup.send(f"🎧 جاري تشغيل: **{title}**")

    except Exception as e:
        await interaction.followup.send("معليش، ما قدرت أشغل هذا المقطع. جرب رابط ثاني أو غير كلمات البحث.")
        print(f"Error: {e}")

# --- تشغيل البوت ---
TOKEN = os.getenv("DISCORD_TOKEN")
if TOKEN:
    bot.run(TOKEN)
else:
    print("خطأ: التوكن غير موجود في متغيرات البيئة!")
