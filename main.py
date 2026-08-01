import discord
import io
import os
from flask import Flask
from threading import Thread

# --- إعدادات خادم الويب الوهمي لمنصة Render ---
app = Flask(__name__)

@app.route('/')
def home():
    return "Discord Bot is running!"

def run():
    # Render يعين منفذاً تلقائياً في متغير PORT
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# ----------------------------------------------

# --- إعدادات بوت ديسكورد ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.attachments:
        files_to_send = []
        image_found = False

        for attachment in message.attachments:
            if attachment.content_type and attachment.content_type.startswith('image'):
                image_found = True
                image_data = await attachment.read()
                files_to_send.append(discord.File(io.BytesIO(image_data), filename=attachment.filename))
        
        if image_found:
            try:
                await message.delete()
                await message.channel.send(content=message.content if message.content else None, files=files_to_send)
                # رابط الصورة الثابتة كما طلبته
                await message.channel.send("https://cdn.discordapp.com/attachments/1517925146134970461/1533200565872365638/1785613867680_edit_1785613887566.png?ex=6a6f9fcc&is=6a6e4e4c&hm=6e4e0bf1867f0b57244250d860eddff6c80dd9c12811d4c079791aa82e839dfc&")
            except Exception as e:
                print(f"حدث خطأ أثناء إرسال الرسالة: {e}")

# جلب التوكن من متغيرات البيئة (Environment Variables) في رندر
TOKEN = os.getenv('DISCORD_TOKEN')

if TOKEN:
    keep_alive()  # تشغيل خادم الويب الوهمي أولاً
    client.run(TOKEN) # ثم تشغيل البوت
else:
    print("خطأ: لم يتم العثور على مفتاح DISCORD_TOKEN. تأكد من إضافته في إعدادات البيئة (Environment Variables) في Render.")
