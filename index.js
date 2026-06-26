const { Client, GatewayIntentBits, Partials, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle } = require('discord.js');
const http = require('http');
const fs = require('fs');

// ==========================================
// 1. نظام الحماية لرندر (تجنب الخمول)
// ==========================================
http.createServer((req, res) => {
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('Bot is Active - Render Keep-Alive');
}).listen(3000);

// ==========================================
// 2. إعدادات البوت وقاعدة البيانات
// ==========================================
const client = new Client({
    intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent, GatewayIntentBits.GuildMembers, GatewayIntentBits.DirectMessages],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

const ownerID = '1306034100544737461';
let db = { users: {}, warnings: {}, identities: {}, serverBoard: {} };

// حفظ واسترجاع البيانات تلقائياً
const loadDB = () => {
    if (fs.existsSync('./database.json')) {
        db = JSON.parse(fs.readFileSync('./database.json', 'utf8'));
    }
};
const saveDB = () => fs.writeFileSync('./database.json', JSON.stringify(db, null, 4));
loadDB();

// قائمة أسعار الأكل والشرب
const shopItems = {
    "برجر": { hunger: 50, thirst: 0 },
    "ماء": { hunger: 0, thirst: 30 },
    "عصير": { hunger: 0, thirst: 20 },
    "بيتزا": { hunger: 30, thirst: 0 },
    "فراوله": { hunger: 5, thirst: 3 },
    "حلوه": { hunger: 10, thirst: 0 },
    "تفاح": { hunger: 15, thirst: 15 },
    "ببسي": { hunger: 0, thirst: 35 },
    "سفن اب": { hunger: 0, thirst: 35 },
    "حمضيات": { hunger: 0, thirst: 35 },
    "ديو": { hunger: 0, thirst: 35 },
    "وجبه": { hunger: 100, thirst: 0 }
};

client.once('ready', () => {
    console.log(`[READY] Logged in as ${client.user.tag}`);
});

// ==========================================
// 3. الأوامر (الرتب، التحذيرات، الهوية، الأكل)
// ==========================================
client.on('messageCreate', async (msg) => {
    if (msg.author.bot) return;

    const args = msg.content.split(' ');
    const command = args[0];

    // ----- أمر الرول -----
    if (command === '-رول') {
        const member = msg.mentions.members.first();
        const role = msg.mentions.roles.first();
        if (!member || !role) return msg.reply('اكتب الأمر بالطريقة هذي: -رول @الشخص @الرتبه');
        
        // منع إعطاء رتب قوية (تقدر تضيف أيدي الرتب القوية هنا)
        const dangerousRoles = ['أيدي_رتبة_الأونر_هنا']; 
        if (dangerousRoles.includes(role.id)) {
            return msg.reply('انتبه! ترا في رتبة قوية أنت بتحاول تعطيها، تم إلغاء العملية.');
        }

        if (member.roles.cache.has(role.id)) {
            await member.roles.remove(role);
            return msg.channel.send(`تم إزالة الرتبة ${role.name} من ${member.user.username}`);
        } else {
            await member.roles.add(role);
            return msg.channel.send(`تم إعطاء الرتبة ${role.name} لـ ${member.user.username}`);
        }
    }

    // ----- أوامر التحذير -----
    if (command === '/تحذير') {
        const member = msg.mentions.members.first();
        const reason = args.slice(2).join(' ');
        if (!member || !reason) return msg.reply('الطريقة: /تحذير @الشخص السبب');

        msg.channel.send(`جاري التحميل... <a:emoji_26:1520109763952771204>`).then(m => {
            setTimeout(() => {
                if (!db.warnings[member.id]) db.warnings[member.id] = [];
                db.warnings[member.id].push({ reason, by: msg.author.id });
                saveDB();
                
                m.edit(`تم تحذير الشخص ${member} <a:emoji_26:1520109726065496295>`);
                member.send(`تم تحذيرك من قبل <@${msg.author.id}> بسبب: ${reason}\nاقرأ القوانين وركز! ⚠️`).catch(() => {});
            }, 2000);
        });
    }

    if (command === '/شيل') {
        const member = msg.mentions.members.first();
        if (!member) return;
        delete db.warnings[member.id];
        saveDB();
        msg.reply('تم إزالة جميع التحذيرات عن هذا الشخص.');
    }

    if (command === '-تحذيرات') {
        const member = msg.mentions.members.first();
        if (member) {
            const warns = db.warnings[member.id] || [];
            return msg.reply(warns.length > 0 ? `هذا الشخص لديه ${warns.length} تحذيرات.` : 'هذا الشخص ليس لديه تحذيرات.');
        } else {
            // جلب آخر 10 تحذيرات
            msg.reply('جاري التحميل... <a:emoji_26:1520109763952771204>').then(m => {
                // كود مبسط لعرض التحذيرات
                m.edit('تم جلب البيانات: (سيتم عرض التحذيرات هنا)');
            });
        }
    }

    // ----- أوامر الهوية -----
    if (command === '/هويه') {
        const member = msg.mentions.members.first();
        if (!member) return msg.reply('منشن الشخص!');
        const idData = db.identities[member.id];
        if (!idData) return msg.reply('هذا الشخص ليس لديه هوية.');
        
        const embed = new EmbedBuilder()
            .setTitle('هوية المواطن')
            .addFields(
                { name: 'الاسم', value: idData.name, inline: true },
                { name: 'الرقم الوطني', value: idData.phone, inline: true },
                { name: 'الجنس', value: idData.gender, inline: true }
            );
        msg.channel.send({ embeds: [embed] });
    }

    if (command === '/حذف' && args[1] === 'هويه:') {
        if (msg.author.id !== ownerID) return msg.reply('هذا الأمر للملك فقط!');
        const member = msg.mentions.members.first();
        if (!member) return;
        
        delete db.identities[member.id];
        saveDB();
        
        member.roles.set(['1520087730544050436']); // إزالة كل الرتب وإعطاء رتبة الهوية
        msg.reply(`تم حذف هوية ${member} وإعادة تعيين رتبه.`);
    }

    // ----- نظام الشنطة والبيع -----
    if (command === '-شنطه') {
        let user = db.users[msg.author.id];
        if (!user) user = { hunger: 100, thirst: 100, inventory: [] };

        const embed = new EmbedBuilder()
            .setTitle('الشنطة الخاصة بك')
            .setDescription('محتويات حقيبتك:')
            .addFields(
                { name: 'الجوع', value: `${Math.floor(user.hunger)}% 🟧`, inline: true },
                { name: 'العطش', value: `${Math.floor(user.thirst)}% 🟦`, inline: true },
                { name: 'الأغراض', value: user.inventory.length > 0 ? user.inventory.join('\n') : 'الشنطة فارغة', inline: false }
            );
        msg.author.send({ embeds: [embed] }).catch(() => msg.reply('افتح الخاص عشان أرسلك الشنطة!'));
        msg.reply('تم إرسال الشنطة لك في الخاص.');
    }

    if (command === '/منيو') {
        let menuTxt = "منيو البيع:\n";
        for (let item in shopItems) {
            menuTxt += `- ${item}\n`;
        }
        msg.reply(menuTxt);
    }

    if (command === '/بيع') {
        // التحقق من رتبة البائع 
        if (!msg.member.roles.cache.has('1520153220100522126')) return;
        
        const member = msg.mentions.members.first();
        const item = args.slice(2).join(' ');
        
        if (!member || !shopItems[item]) return msg.reply('تأكد من المنشن واسم الغرض من المنيو.');
        
        if (!db.users[member.id]) db.users[member.id] = { hunger: 100, thirst: 100, inventory: [] };
        db.users[member.id].inventory.push(item);
        saveDB();
        
        msg.reply(`تم بيع ${item} لـ ${member}`);
    }

    if (command === '/فول') {
        if (msg.author.id !== ownerID) return;
        const member = msg.mentions.members.first();
        if (!member) return;
        
        if (!db.users[member.id]) db.users[member.id] = { hunger: 100, thirst: 100, inventory: [] };
        db.users[member.id].hunger = 100;
        db.users[member.id].thirst = 100;
        saveDB();
        msg.reply(`تم تفويل طاقة ${member}`);
    }

    // استهلاك الأكل/الشرب من الشنطة
    if (shopItems[msg.content]) {
        let user = db.users[msg.author.id];
        if (!user || !user.inventory.includes(msg.content)) return; // ماعنده الغرض

        const itemData = shopItems[msg.content];
        user.hunger = Math.min(100, user.hunger + itemData.hunger);
        user.thirst = Math.min(100, user.thirst + itemData.thirst);
        
        // إزالة غرض واحد من الشنطة
        const index = user.inventory.indexOf(msg.content);
        if (index > -1) user.inventory.splice(index, 1);
        saveDB();
        
        msg.reply(`تم استهلاك ${msg.content}. جوعك: ${user.hunger}%, عطشك: ${user.thirst}%`);
    }

    // ----- أوامر الإعداد (أبدأ) -----
    if (command === '!أبدأ١') {
        msg.delete();
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('toggle_duty').setLabel('تسجيل دخول / خروج').setStyle(ButtonStyle.Success)
        );
        msg.channel.send({ content: 'تسجيل دخول وخروج للعسكر فقط', components: [row] });
    }

    if (command === '!أبدأ٢') {
        db.serverBoard.channelId = msg.channel.id;
        saveDB();
        msg.reply('تم تعيين هذا الروم للوحة بيانات العساكر.');
    }

    if (command === '!ابدا٣') {
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('start_id').setLabel('أكمل').setStyle(ButtonStyle.Primary)
        );
        msg.channel.send({ content: 'السلام عليكم، تأكيد دخولك للسيرفر', components: [row] });
    }
});

// ==========================================
// 4. نظام الأزرار (تسجيل العسكر، الهوية)
// ==========================================
client.on('interactionCreate', async (interaction) => {
    if (!interaction.isButton()) return;

    if (interaction.customId === 'toggle_duty') {
        const member = interaction.member;
        const onlineRole = '1520077188135780494';
        const offlineRole = '1520084329714421800';

        if (member.roles.cache.has(offlineRole)) {
            await member.roles.remove(offlineRole);
            await member.roles.add(onlineRole);
            interaction.reply({ content: 'تم تسجيل دخولك بنجاح 🟢', ephemeral: true });
        } else if (member.roles.cache.has(onlineRole)) {
            await member.roles.remove(onlineRole);
            await member.roles.add(offlineRole);
            interaction.reply({ content: 'تم تسجيل خروجك بنجاح 🔴', ephemeral: true });
        } else {
            interaction.reply({ content: 'ليس لديك رتبة عسكري!', ephemeral: true });
        }
        updateBoard(interaction.guild);
    }

    if (interaction.customId === 'start_id') {
        if (!interaction.member.roles.cache.has('1520087730544050436')) return interaction.reply({content: 'ليس لديك صلاحية', ephemeral: true});
        
        interaction.reply({ content: 'تم إرسال رسالة لك في الخاص.', ephemeral: true });
        interaction.user.send('مرحباً بك في سيرفر رولباك! هل تريد أن تصنع هويتك؟ (نعم/لا)');
        // يتطلب بناء نظام Collector في الخاص لاستقبال الاسم والرقم (مختصر هنا للحجم)
    }
});

// تحديث لوحة العسكر (!أبدأ٢)
async function updateBoard(guild) {
    if (!db.serverBoard.channelId) return;
    const channel = guild.channels.cache.get(db.serverBoard.channelId);
    if (!channel) return;

    const onlineRole = guild.roles.cache.get('1520077188135780494');
    const offlineRole = guild.roles.cache.get('1520084329714421800');
    
    let text = "حالة العساكر:\n\n";
    if (onlineRole) onlineRole.members.forEach(m => text += `${m.user.username} متصل 🟢\n`);
    if (offlineRole) offlineRole.members.forEach(m => text += `${m.user.username} غير متصل 🔴\n`);

    // البحث عن آخر رسالة للبوت وتعديلها أو إرسال جديدة
    channel.messages.fetch({ limit: 10 }).then(messages => {
        const botMsg = messages.find(m => m.author.id === client.user.id);
        if (botMsg) botMsg.edit(text);
        else channel.send(text);
    });
}

// ==========================================
// 5. نظام الجوع والعطش (كل ساعة)
// ==========================================
setInterval(() => {
    for (const userId in db.users) {
        let user = db.users[userId];
        user.hunger = Math.max(0, user.hunger - 50);
        user.thirst = Math.max(0, user.thirst - 50);

        // التحذيرات إذا قرب يموت
        if (user.hunger === 25 || user.hunger === 15) {
            client.users.cache.get(userId)?.send('أنت جائع! سيتم توقيفك إذا لم تأكل من المتجر.');
        }
        if (user.hunger === 0) {
            client.users.cache.get(ownerID)?.send(`هذا الشخص <@${userId}> لم يأكل وهو متصل!`);
            // سحب الرتب وإعطاء رتبة الإغماء
            // client.guilds.cache.first().members.cache.get(userId).roles.set(['1520075245308874853']);
        }
    }
    saveDB();
}, 3600000); // 3600000 ملي ثانية = ساعة

// ==========================================
client.login(process.env.DISCORD_TOKEN);
