require('dotenv').config();
const { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder } = require('discord.js');
const express = require('express');
const fs = require('fs');

// --- نظام البقاء متصلاً على Render ---
const app = express();
const port = process.env.PORT || 3000;
app.get('/', (req, res) => res.send('البوت يعمل بكفاءة!'));
app.listen(port, () => console.log(`الخادم يعمل على المنفذ ${port}`));

// --- إعداد البوت ---
const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.DirectMessages,
    ],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

// قاعدة بيانات الحفظ
const dbFile = './database.json';
let db = { warnings: {}, users: {}, statusChannel: null };
if (fs.existsSync(dbFile)) {
    db = JSON.parse(fs.readFileSync(dbFile));
}
function saveDB() {
    fs.writeFileSync(dbFile, JSON.stringify(db, null, 4));
}

// الرتب والأشخاص
const OWNER_ID = '1306034100544737461';
const MILITARY_ONLINE = '1520077188135780494';
const MILITARY_OFFLINE = '1520084329714421800';
const REGISTRATION_ROLE = '1520087730544050436';
const VERIFIED_ROLE = '1474724032849907722';
const BOY_ROLE = '1476903628714410079';
const GIRL_ROLE = '1476903782112821258';
const DEAD_ROLE = '1520075245308874853';
const SELLER_ROLE = '1520153220100522126';

const EMOJI_LOAD = '<a:emoji_26:1520109763952771204>';
const EMOJI_WARN1 = '<a:emoji_26:1520109726065496295>';
const EMOJI_WARN2 = '<a:emoji_28:1520109788485128202>';

// أسعار ومقادير قائمة الطعام
const shopItems = {
    'برجر': { hunger: 50, thirst: 0 },
    'ماء': { hunger: 0, thirst: 30 },
    'عصير': { hunger: 0, thirst: 20 },
    'بيتزا': { hunger: 40, thirst: 0 },
    'فراوله': { hunger: 5, thirst: 3 },
    'حلوه': { hunger: 10, thirst: 0 },
    'تفاح': { hunger: 15, thirst: 15 },
    'ببسي': { hunger: 0, thirst: 35 },
    'سفن اب': { hunger: 0, thirst: 35 },
    'حمضيات': { hunger: 0, thirst: 35 },
    'ديو': { hunger: 0, thirst: 35 },
    'وجبه': { hunger: 100, thirst: 0 }
};

client.on('ready', () => {
    console.log(`تم تسجيل الدخول باسم ${client.user.tag}`);
    
    // نظام تقليل الجوع والعطش
    setInterval(() => {
        for (const userId in db.users) {
            let user = db.users[userId];
            if (user.hunger > 0) user.hunger = Math.max(0, user.hunger - 50);
            if (user.thirst > 0) user.thirst = Math.max(0, user.thirst - 50);
            
            if (user.hunger === 0 || user.thirst === 0) {
                const guild = client.guilds.cache.first();
                if (guild) {
                    const member = guild.members.cache.get(userId);
                    if (member) {
                        const rolesToKeep = [BOY_ROLE, GIRL_ROLE];
                        const newRoles = member.roles.cache.filter(r => rolesToKeep.includes(r.id)).map(r => r.id);
                        newRoles.push(DEAD_ROLE);
                        member.roles.set(newRoles).catch(console.error);
                        
                        client.users.fetch(OWNER_ID).then(owner => {
                            owner.send(`الشخص <@${userId}> لم يأكل ومات من الجوع/العطش! وهو متصل`).catch(()=>{});
                        });
                    }
                }
            }
        }
        saveDB();
    }, 3600000);
});

client.on('messageCreate', async message => {
    if (message.author.bot) return;

    const args = message.content.split(' ');
    const command = args[0];

    // أوامر العسكر
    if (command === '-رول') {
        const target = message.mentions.members.first();
        const role = message.mentions.roles.first();
        if (!target || !role) return message.reply('اكتب الأمر بالطريقة هذه:\n-رول @الشخص @الرتبة');
        
        if (role.permissions.has('Administrator')) {
            return message.reply('هذي رتبة عالية بشكل كبير! انتبه ترا في رتبة قوية أنت بتحاول تعطيها. تم إلغاء العملية.');
        }

        if (target.roles.cache.has(role.id)) {
            await target.roles.remove(role);
            message.channel.send(`تم إزالة الرتبة من ${target}`);
        } else {
            await target.roles.add(role);
            message.channel.send(`تم إعطاء الرتبة لـ ${target}`);
        }
    }

    if (command === '/تحذير') {
        const target = message.mentions.members.first();
        const reason = message.content.split('السبب:')[1]?.trim() || 'بدون سبب';
        if (!target) return message.reply('منشن الشخص!');

        let msg = await message.channel.send(`تحميل... ${EMOJI_LOAD}`);
        
        if (!db.warnings[target.id]) db.warnings[target.id] = [];
        db.warnings[target.id].push({ by: message.author.id, reason: reason });
        saveDB();

        setTimeout(() => {
            msg.edit(`تم تحذير الشخص ${target}\nالسبب: ${reason} ${EMOJI_WARN1}`);
            target.send(`تم تحذيرك من قبل <@${message.author.id}>!\nالسبب: ${reason}\nاقرأ القوانين وركز! ${EMOJI_WARN2}`).catch(()=>{});
        }, 2000);
    }

    if (command === '/شيل') {
        const target = message.mentions.members.first();
        if (!target) return message.reply('منشن الشخص!');
        db.warnings[target.id] = [];
        saveDB();
        message.channel.send(`تم حذف جميع تحذيرات ${target}`);
    }

    if (command === '-تحذيرات') {
        const target = message.mentions.members.first();
        let msg = await message.channel.send(`تحميل... ${EMOJI_LOAD}`);
        
        setTimeout(() => {
            if (target) {
                const count = db.warnings[target.id]?.length || 0;
                let reply = `هذا الشخص لديه ${count} تحذيرات.`;
                if (count === 0) reply = 'مفي تحذيرات!';
                else if (count > 3) reply = `هل هذا الشخص له تحذيرات كثيرة؟ نعم لديه ${count} تحذيرات!`;
                msg.edit(reply);
            } else {
                let allWarns = [];
                for (let user in db.warnings) {
                    db.warnings[user].forEach(w => allWarns.push({user, ...w}));
                }
                if (allWarns.length === 0) return msg.edit('لا يوجد تحذيرات.');
                
                let text = allWarns.slice(-10).map((w, i) => `${i+1}- المحذر: <@${w.user}> | بواسطة: <@${w.by}> | السبب: ${w.reason}`).join('\n');
                msg.edit(`**آخر 10 تحذيرات:**\n${text}`);
            }
        }, 2000);
    }

    if (command === '/هويه') {
        const target = message.mentions.users.first();
        if (!target) return message.reply('منشن الشخص!');
        const userData = db.users[target.id];
        
        let msg = await message.channel.send(`تحميل... ${EMOJI_LOAD}`);
        setTimeout(() => {
            if (!userData || !userData.phone) return msg.edit('هذا الشخص لا يملك هوية.');
            msg.edit(`**هوية الشخص:**\nالاسم: ${userData.name}\nالرقم الوطني: ${userData.phone}\nالجنس: ${userData.gender === 'boy' ? 'ولد' : 'بنت'}`);
        }, 2000);
    }

    if (command === '/حذف' && args[1] === 'هويه:') {
        if (message.author.id !== OWNER_ID) return;
        const target = message.mentions.members.first();
        if (!target) return message.reply('منشن الشخص!');
        
        db.users[target.id] = undefined;
        saveDB();
        
        await target.roles.set([REGISTRATION_ROLE]);
        message.channel.send(`تم حذف هوية ${target}`);
    }

    // أوامر التجهيز
    if (command === '!أبدأ١') {
        message.delete();
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('toggle_duty').setLabel('تسجيل دخول / خروج').setStyle(ButtonStyle.Success),
        );
        message.channel.send({ content: '```yaml\nتسجيل دخول وخروج للعسكر فقط\n```', components: [row] });
    }

    if (command === '!أبدأ٢') {
        message.delete();
        db.statusChannel = message.channel.id;
        saveDB();
        message.channel.send('تم تعيين هذا الروم لبث حالة العسكر (فولدر 11).');
    }

    if (command === '!أبدأ٣') {
        message.delete();
        const row = new ActionRowBuilder().addComponents(
            new ButtonBuilder().setCustomId('start_identity').setLabel('أكمل').setStyle(ButtonStyle.Primary),
        );
        message.channel.send({ content: 'السلام عليكم، لتأكيد دخولك للسيرفر اضغط زر أكمل:', components: [row] });
    }

    // الشنطة والبيع
    if (command === '-شنطه') {
        const user = db.users[message.author.id] || { hunger: 100, thirst: 100, inventory: [] };
        
        let blueBar = '🟦'.repeat(Math.ceil(user.thirst / 10)) + '⬛'.repeat(10 - Math.ceil(user.thirst / 10));
        let orangeBar = '🟧'.repeat(Math.ceil(user.hunger / 10)) + '⬛'.repeat(10 - Math.ceil(user.hunger / 10));
        
        let invText = user.inventory && user.inventory.length > 0 ? user.inventory.join(', ') : 'الشنطة فارغة';
        
        message.author.send(`**محتويات شنطتك:**\nالأغراض: ${invText}\n\nالعطش: ${blueBar} (${user.thirst}%)\nالجوع: ${orangeBar} (${user.hunger}%)`).catch(() => {
            message.channel.send('افتح الخاص عشان أقدر أرسلك الشنطة!');
        });
    }

    if (command === '/بيع' && args[1] === 'الغرض:') {
        if (!message.member.roles.cache.has(SELLER_ROLE)) return message.reply('ليس لديك رتبة البائع!');
        const target = message.mentions.members.first();
        const item = args.slice(3).join(' '); 
        
        if (!target || !item) return message.reply('الطريقة الصحيحة: /بيع الغرض: [اسم الغرض] الشخص: @منشن');
        if (!shopItems[item]) return message.reply('هذا الغرض غير موجود في المنيو!');

        if (!db.users[target.id]) db.users[target.id] = { hunger: 100, thirst: 100, inventory: [] };
        if (!db.users[target.id].inventory) db.users[target.id].inventory = [];
        
        db.users[target.id].inventory.push(item);
        saveDB();
        
        message.channel.send(`تم بيع ${item} لـ ${target} بنجاح.`);
    }

    if (command === '/منيو') {
        let menuText = '**قائمة البيع:**\n';
        for (let item in shopItems) {
            menuText += `- ${item}\n`;
        }
        message.channel.send(menuText);
    }

    if (command === '/فول') {
        if (message.author.id !== OWNER_ID) return;
        const target = message.mentions.members.first();
        if (!target) return message.reply('منشن الشخص!');
        
        if (!db.users[target.id]) db.users[target.id] = { hunger: 100, thirst: 100, inventory: [] };
        db.users[target.id].hunger = 100;
        db.users[target.id].thirst = 100;
        saveDB();
        
        message.channel.send(`تم تفويل طاقة ${target} بنجاح.`);
    }

    // الأكل المباشر
    if (shopItems[message.content]) {
        const item = message.content;
        let user = db.users[message.author.id];
        
        if (user && user.inventory && user.inventory.includes(item)) {
            const itemIndex = user.inventory.indexOf(item);
            user.inventory.splice(itemIndex, 1);
            
            user.hunger = Math.min(100, user.hunger + shopItems[item].hunger);
            user.thirst = Math.min(100, user.thirst + shopItems[item].thirst);
            saveDB();
            
            message.channel.send(`أنت استهلكت ${item}. الجوع: ${user.hunger}% | العطش: ${user.thirst}%`);
        }
    }
});

// التفاعلات
client.on('interactionCreate', async interaction => {
    if (!interaction.isButton()) return;

    if (interaction.customId === 'toggle_duty') {
        const member = interaction.member;
        
        if (member.roles.cache.has(MILITARY_OFFLINE)) {
            await member.roles.remove(MILITARY_OFFLINE);
            await member.roles.add(MILITARY_ONLINE);
            await interaction.reply({ content: 'تم تسجيل دخولك بنجاح 🟢', ephemeral: true });
            updateMilitaryStatus(interaction.guild);
        } 
        else if (member.roles.cache.has(MILITARY_ONLINE)) {
            await member.roles.remove(MILITARY_ONLINE);
            await member.roles.add(MILITARY_OFFLINE);
            await interaction.reply({ content: 'تم تسجيل خروجك بنجاح 🔴', ephemeral: true });
            updateMilitaryStatus(interaction.guild);
        } else {
            await interaction.reply({ content: 'أنت لا تملك رتبة عسكرية.', ephemeral: true });
        }
    }

    if (interaction.customId === 'start_identity') {
        await interaction.reply({ content: 'تم إرسال رسالة لك في الخاص.', ephemeral: true });
        
        try {
            const dmChannel = await interaction.user.createDM();
            await dmChannel.send('مرحباً بك في سيرفر رولباك، هل تريد أن تصنع هويتك في السيرفر للمزح واللعب فقط؟ (اكتب نعم أو لا)');
            
            const filter = m => m.author.id === interaction.user.id;
            const collector = dmChannel.createMessageCollector({ filter, time: 300000 });
            
            let step = 0;
            let tempUserData = {};

            collector.on('collect', async m => {
                if (m.content === 'إلغاء') {
                    collector.stop();
                    return m.reply('تم إلغاء العملية.');
                }

                if (step === 0 && m.content === 'نعم') {
                    step++;
                    m.reply('حسناً، اكتب اسمك المزيف أو الحقيقي (على سبيل المثال ابو احمد)');
                } 
                else if (step === 1) {
                    tempUserData.name = m.content;
                    step++;
                    m.reply('طيب، هل تريد صنع رقم مزيف للهاتف؟ إذا نعم اكتب 17 متبوعاً بـ 5 أرقام (مثال: 1712345).');
                }
                else if (step === 2) {
                    const phone = m.content;
                    if (!phone.startsWith('17') || phone.length !== 7 || isNaN(phone)) {
                        return m.reply('غلط! يجب أن يبدأ بـ 17 ويكون طوله 7 أرقام. (لإلغاء العملية اكتب إلغاء)');
                    }
                    
                    let isUsed = Object.values(db.users).some(u => u.phone === phone);
                    if (isUsed) return m.reply('هذا الرقم عند شخص آخر! اكتب رقماً جديداً يبدأ بـ 17.');

                    tempUserData.phone = phone;
                    step++;
                    m.reply('ممتاز. آخر شيء، ما جنسيتك؟ (اكتب: ولد أو بنت)');
                }
                else if (step === 3) {
                    if (m.content !== 'ولد' && m.content !== 'بنت') return m.reply('اكتب فقط: ولد أو بنت');
                    
                    tempUserData.gender = m.content === 'ولد' ? 'boy' : 'girl';
                    tempUserData.hunger = 100;
                    tempUserData.thirst = 100;
                    tempUserData.inventory = [];
                    
                    db.users[interaction.user.id] = tempUserData;
                    saveDB();
                    
                    m.reply('مرحباً بك في سيرفر رولباك!');
                    collector.stop();

                    const member = interaction.guild.members.cache.get(interaction.user.id);
                    if (member) {
                        await member.roles.remove(REGISTRATION_ROLE).catch(()=>{});
                        await member.roles.add(VERIFIED_ROLE).catch(()=>{});
                        if (tempUserData.gender === 'boy') await member.roles.add(BOY_ROLE).catch(()=>{});
                        else await member.roles.add(GIRL_ROLE).catch(()=>{});
                    }
                }
            });
        } catch (e) {
            console.error('لا يمكن إرسال رسالة خاصة.');
        }
    }
});

async function updateMilitaryStatus(guild) {
    if (!db.statusChannel) return;
    const channel = guild.channels.cache.get(db.statusChannel);
    if (!channel) return;

    await guild.members.fetch();
    const online = guild.roles.cache.get(MILITARY_ONLINE)?.members.map(m => {
        let name = db.users[m.id]?.name || m.user.username;
        return `${name} متصل 🟢`;
    }) || [];
    
    const offline = guild.roles.cache.get(MILITARY_OFFLINE)?.members.map(m => {
        let name = db.users[m.id]?.name || m.user.username;
        return `${name} غير متصل 🔴`;
    }) || [];

    let text = [...online, ...offline].join('\n');
    if (!text) text = 'لا يوجد عساكر مسجلين حالياً.';

    channel.send(`**تحديث حالة العساكر:**\n${text}`);
}

client.login(process.env.DISCORD_TOKEN);
