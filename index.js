const { Client, GatewayIntentBits, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } = require('discord.js');
const http = require('http');

// إنشاء خادم وهمي بسيط لكي لا يتعطل البوت عند رفعه على منصة Render كـ Web Service
http.createServer((req, res) => {
    res.write("Bot is running!");
    res.end();
}).listen(process.env.PORT || 8080);

// إعداد البوت والصلاحيات المطلوبة
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
    ]
});

// متغير لحفظ الألعاب النشطة في الرومات
const activeGames = new Map();

// قائمة الأسئلة العشوائية (يمكنك إضافة المزيد كما تشاء)
const questionsList = [
    "هل سبق لك أن ضربت شخصاً بدون سبب؟",
    "هل سبق لك أن سبيت شخصاً في اللعبة وخسرت بسببه؟",
    "هل سبق لك أن سرقت شيئاً صغيراً من سوبر ماركت؟",
    "هل سبق لك أن كذبت على والديك للتهرب من مشكلة؟",
    "هل سبق لك أن نمت في الفصل أثناء الحصة؟",
    "هل سبق لك أن ادعيت المرض لكي لا تذهب للمدرسة/العمل؟",
    "هل سبق لك أن ضحكت في موقف جدي جداً ولا يجب الضحك فيه؟",
    "هل سبق لك أن كسرت شيئاً في المنزل وأخفيت الدليل؟",
    "هل سبق لك أن أكلت طعام شخص آخر من الثلاجة بدون علمه؟",
    "هل سبق لك أن بكيت بسبب فيلم أو مسلسل؟",
    "هل سبق لك أن نسيت اسم شخص وأنت تتحدث معه؟",
    "هل سبق لك أن أرسلت رسالة للشخص الخطأ وكانت رسالة محرجة؟",
    "هل سبق لك أن سقطت في مكان عام وتظاهرت أن شيئاً لم يحدث؟",
    "هل سبق لك أن استخدمت فرشاة أسنان شخص آخر بالخطأ؟",
    "هل سبق لك أن حاولت قص شعرك بنفسك وندمت؟"
];

client.on('ready', () => {
    console.log(`✅ Logged in as ${client.user.tag}!`);
    console.log(`✅ Bot is ready for Render!`);
});

client.on('messageCreate', async (message) => {
    if (message.author.bot) return;

    // أمر البداية
    if (message.content === '-ابدا') {
        if (activeGames.has(message.channel.id)) {
            return message.reply("يوجد لعبة جارية بالفعل في هذا الروم! انتظر حتى تنتهي.");
        }

        // إنشاء زر الانضمام
        const joinButton = new ButtonBuilder()
            .setCustomId('join_game')
            .setLabel('اضغط هنا للانضمام (نحتاج لاعبين)')
            .setStyle(ButtonStyle.Primary);

        const row = new ActionRowBuilder().addComponents(joinButton);

        const msg = await message.reply({
            content: `🎮 **بدأت اللعبة!**\nاللاعب الأول هو: ${message.author}\nننتظر لاعباً آخر ليضغط على الزر أدناه للبدء...`,
            components: [row]
        });

        // إنشاء مساحة اللعبة في هذا الروم
        activeGames.set(message.channel.id, {
            players: [message.author.id], // اللاعب الأول هو من كتب الأمر
            skips: { [message.author.id]: 3 }, // 3 محاولات سكيب للاعب الأول
            turnIndex: 0,
            messageId: msg.id
        });
    }
});

client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;

    const game = activeGames.get(interaction.channel.id);
    if (!game) {
        return interaction.reply({ content: "عذراً، هذه اللعبة انتهت أو غير موجودة.", ephemeral: true });
    }

    // --- التعامل مع زر الانضمام ---
    if (interaction.customId === 'join_game') {
        if (game.players.includes(interaction.user.id)) {
            return interaction.reply({ content: "أنت منضم بالفعل كلاعب أول!", ephemeral: true });
        }

        // إضافة اللاعب الثاني
        game.players.push(interaction.user.id);
        game.skips[interaction.user.id] = 3; // إعطاء اللاعب الثاني 3 محاولات سكيب

        await interaction.update({
            content: `⏳ **يتم التحميل...**\nاكتمل العدد! اللاعبان هما: <@${game.players[0]}> و <@${game.players[1]}>.\nسيتم طرح السؤال الأول الآن...`,
            components: []
        });

        // تأخير بسيط لإعطاء تأثير "التحميل" ثم طرح السؤال
        setTimeout(() => {
            askQuestion(interaction.channel, game);
        }, 3000);
        return;
    }

    // --- التعامل مع أزرار الإجابات ---
    if (['ans_yes', 'ans_no', 'ans_skip'].includes(interaction.customId)) {
        const currentPlayerId = game.players[game.turnIndex];

        // التأكد من أن الشخص الذي ضغط الزر هو الذي عليه الدور
        if (interaction.user.id !== currentPlayerId) {
            return interaction.reply({ content: "ليس دورك للإجابة!", ephemeral: true });
        }

        let responseText = "";

        // فحص اختيار اللاعب
        if (interaction.customId === 'ans_skip') {
            if (game.skips[interaction.user.id] <= 0) {
                return interaction.reply({ content: "❌ لقد استنفدت جميع محاولات السكيب الـ 3 الخاصة بك! يجب عليك الإجابة بنعم أو لا.", ephemeral: true });
            }
            game.skips[interaction.user.id] -= 1;
            responseText = `لقد فعل **سكيب (تخطي)** ⏭️\n*(تبقى له ${game.skips[interaction.user.id]} محاولات سكيب)*`;
        } else if (interaction.customId === 'ans_yes') {
            responseText = `لقد ضغط على **نـعـم** ✅`;
        } else if (interaction.customId === 'ans_no') {
            responseText = `لقد ضغط على **لا** ❌`;
        }

        // إرسال رد واضح يوضح اختيار اللاعب
        await interaction.reply({
            content: `📣 اللاعب <@${interaction.user.id}> ${responseText}`
        });

        // تغيير الدور للاعب الآخر
        game.turnIndex = game.turnIndex === 0 ? 1 : 0;

        // طرح السؤال التالي بعد الإجابة
        setTimeout(() => {
            askQuestion(interaction.channel, game);
        }, 2000);
    }
});

// دالة لطرح سؤال عشوائي مع الأزرار
async function askQuestion(channel, game) {
    const randomQuestion = questionsList[Math.floor(Math.random() * questionsList.length)];
    const currentPlayerId = game.players[game.turnIndex];

    const embed = new EmbedBuilder()
        .setColor('#0099ff')
        .setTitle('❓ سؤال جديد!')
        .setDescription(`**يا <@${currentPlayerId}>، أنت!**\n\n${randomQuestion}`)
        .setFooter({ text: `لديك ${game.skips[currentPlayerId]} محاولات سكيب متبقية.` });

    const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder()
            .setCustomId('ans_yes')
            .setLabel('نعم')
            .setStyle(ButtonStyle.Success),
        new ButtonBuilder()
            .setCustomId('ans_no')
            .setLabel('لا')
            .setStyle(ButtonStyle.Danger),
        new ButtonBuilder()
            .setCustomId('ans_skip')
            .setLabel('سكيب')
            .setStyle(ButtonStyle.Secondary)
    );

    await channel.send({ content: `<@${currentPlayerId}> حان دورك!`, embeds: [embed], components: [row] });
}

// تسجيل الدخول باستخدام التوكن من متغيرات البيئة (Render)
client.login(process.env.DISCORD_TOKEN);
