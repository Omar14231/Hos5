require('dotenv').config();
const { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, ModalBuilder, TextInputBuilder, TextInputStyle, EmbedBuilder, REST, Routes, PermissionsBitField } = require('discord.js');
const fs = require('fs');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers,
        GatewayIntentBits.DirectMessages
    ],
    partials: [Partials.Message, Partials.Channel, Partials.Reaction]
});

// --- الأيديات والرتب ---
const ROLES = {
    OWNER: '1474553962597191804',
    MILITARY: '1520077188135780494',
    CITIZEN: '1474724032849907722',
    UNKNOWN: '1520087730544050436',
    MALE: '1476903628714410079',
    FEMALE: '1476903782112821258',
    VERIFIED: '1520078137902497922',
    SUPPORT: '1522997079356604436',
    ARRESTED: '1520075245308874853'
};
const TICKET_CATEGORY = '1522996604410265720';
const TICKET_IMAGE = 'https://cdn.discordapp.com/attachments/1522992343643459684/1522996429902184478/1783181030915.png';

// --- نظام قواعد البيانات المصغر ---
const dbFile = './database.json';
function loadDB() {
    if (!fs.existsSync(dbFile)) return {};
    return JSON.parse(fs.readFileSync(dbFile));
}
function saveDB(data) {
    fs.writeFileSync(dbFile, JSON.stringify(data, null, 4));
}

// --- عند تشغيل البوت ---
client.on('ready', async () => {
    console.log(`Logged in as ${client.user.tag}!`);
    const rest = new REST({ version: '10' }).setToken(process.env.DISCORD_TOKEN);
    
    // مسح جميع الأوامر السابقة ثم إضافة الجديدة
    const commands = [
        { name: 'حذف_هويه', description: 'حذف هوية شخص وإرجاعه غير معروف', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }] },
        { name: 'mdt', description: 'كشف معلومات الشخص', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }] },
        { name: 'تغير', description: 'تغيير شخصية اللاعب (مثال: مجرم)', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }, { name: 'التغير', type: 3, description: 'الاسم الجديد', required: true }] },
        { name: 'تحذير', description: 'تحذير شخص', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }, { name: 'السبب', type: 3, description: 'سبب التحذير', required: true }] },
        { name: 'شيل', description: 'مسح تحذيرات شخص', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }] },
        { 
            name: 'رول', description: 'إعطاء أو سحب رتب متعددة', 
            options: [
                { name: 'الشخص', type: 6, description: 'العضو', required: true },
                { name: 'الرتبه١', type: 8, description: 'الرتبة 1', required: true },
                { name: 'الرتبه٢', type: 8, description: 'الرتبة 2', required: false },
                { name: 'الرتبه٣', type: 8, description: 'الرتبة 3', required: false },
                { name: 'الرتبه٤', type: 8, description: 'الرتبة 4', required: false },
                { name: 'الرتبه٥', type: 8, description: 'الرتبة 5', required: false }
            ] 
        },
        { name: 'توقيف', description: 'إعطاء رتبة التوقيف وسحب الباقي', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }] },
        { name: 'نقاطي', description: 'عرض نقاطك (للعسكر)' },
        { name: 'كم_نقاطه', description: 'عرض نقاط شخص آخر', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }] },
        { name: 'اعطاء_نقاط', description: 'إعطاء نقاط لشخص', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }, { name: 'الكميه', type: 4, description: 'عدد النقاط', required: true }] },
        { name: 'سحب_نقاط', description: 'سحب نقاط من شخص', options: [{ name: 'الشخص', type: 6, description: 'العضو', required: true }, { name: 'الكميه', type: 4, description: 'عدد النقاط', required: true }] }
    ];

    try {
        await rest.put(Routes.applicationCommands(client.user.id), { body: commands });
        console.log('تم تحديث أوامر السلاش بنجاح.');
    } catch (error) {
        console.error(error);
    }
});

// --- أوامر الأونر بالبادئة (!أبدأ) ---
client.on('messageCreate', async message => {
    if (message.author.bot || !message.member?.roles.cache.has(ROLES.OWNER)) return;

    if (message.content === '!أبدأ١') {
        message.delete();
        const embed = new EmbedBuilder().setColor('Green').setTitle('اصنع هويتك').setDescription('يرجى الضغط على الزر أدناه لصنع هويتك الخاصة بالسيرفر.');
        const btn = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('btn_create_id').setLabel('اصنع هويتك').setStyle(ButtonStyle.Success));
        message.channel.send({ embeds: [embed], components: [btn] });
    }
    else if (message.content === '!أبدأ٢') {
        message.delete();
        const embed = new EmbedBuilder().setColor('Blue').setTitle('رؤية رقمي الوطني').setDescription('اضغط على الزر لمعرفة رقمك الوطني في السيرفر.');
        const btn = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('btn_view_id').setLabel('رؤية رقمي').setStyle(ButtonStyle.Primary));
        message.channel.send({ embeds: [embed], components: [btn] });
    }
    else if (message.content === '!أبدأ٣') {
        message.delete();
        const embed = new EmbedBuilder().setColor('Gold').setTitle('توثيق نفسك').setDescription('توثيق نفسك لفتح جميع الرومات المحددة لك وكل شيء مخصص لك.');
        const btn = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('btn_verify').setLabel('توثيق').setStyle(ButtonStyle.Secondary));
        message.channel.send({ embeds: [embed], components: [btn] });
    }
    else if (message.content === '!أبدأ٤') {
        message.delete();
        const embed = new EmbedBuilder().setColor('DarkRed').setTitle('تكت راقبي').setDescription('للتواصل مع الإدارة أو فتح تذكرة دعم، اضغط على الزر أدناه.').setImage(TICKET_IMAGE);
        const btn = new ActionRowBuilder().addComponents(new ButtonBuilder().setCustomId('btn_open_ticket').setLabel('افتح تكت').setStyle(ButtonStyle.Danger));
        message.channel.send({ embeds: [embed], components: [btn] });
    }
});

// --- التفاعلات (أزرار، مودلز، أوامر سلاش) ---
client.on('interactionCreate', async interaction => {
    const db = loadDB();

    // -- معالجة الأزرار --
    if (interaction.isButton()) {
        const id = interaction.customId;

        if (id === 'btn_create_id') {
            if (!interaction.member.roles.cache.has(ROLES.UNKNOWN)) {
                return interaction.reply({ content: 'ليس لديك رتبة غير معروف لتصنع هوية.', ephemeral: true });
            }
            const modal = new ModalBuilder().setCustomId('modal_create_id').setTitle('صنع هوية');
            modal.addComponents(
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('name').setLabel('وش اسمك المستعار؟').setStyle(TextInputStyle.Short)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('age').setLabel('كم عمرك؟').setStyle(TextInputStyle.Short)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('roblox').setLabel('وش اسمك في روبلوكس؟').setStyle(TextInputStyle.Short)),
                new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('gender').setLabel('ولد ولا بنت؟').setStyle(TextInputStyle.Short))
            );
            await interaction.showModal(modal);
        }

        else if (id === 'btn_view_id') {
            const userDb = db[interaction.user.id];
            if (!userDb || !userDb.national_id) return interaction.reply({ content: 'لم تقم بصنع هوية بعد!', ephemeral: true });
            interaction.reply({ content: `رقمك الوطني هو: **${userDb.national_id}**`, ephemeral: true });
        }

        else if (id === 'btn_verify') {
            const modal = new ModalBuilder().setCustomId('modal_verify').setTitle('توثيق الهوية');
            modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('nat_id').setLabel('اكتب رقمك الوطني').setStyle(TextInputStyle.Short)));
            await interaction.showModal(modal);
        }

        else if (id === 'btn_open_ticket') {
            const modal = new ModalBuilder().setCustomId('modal_ticket').setTitle('فتح تذكرة');
            modal.addComponents(new ActionRowBuilder().addComponents(new TextInputBuilder().setCustomId('reason').setLabel('سبب فتح التذكرة؟').setStyle(TextInputStyle.Paragraph)));
            await interaction.showModal(modal);
        }

        // أزرار التكت
        else if (id === 't_claim') {
            if (!interaction.member.roles.cache.has(ROLES.SUPPORT)) return interaction.reply({ content: 'ليس لديك صلاحية.', ephemeral: true });
            await interaction.channel.permissionOverwrites.edit(ROLES.SUPPORT, { SendMessages: true });
            
            const btnRow = ActionRowBuilder.from(interaction.message.components[0]);
            btnRow.components[0].setDisabled(true).setStyle(ButtonStyle.Secondary);
            await interaction.message.edit({ components: [btnRow] });
            interaction.reply({ content: `تم استلام التكت بواسطة ${interaction.user}` });
        }
        else if (id === 't_close') {
            if (!interaction.member.roles.cache.has(ROLES.SUPPORT)) return interaction.reply({ content: 'ليس لديك صلاحية.', ephemeral: true });
            interaction.reply('سيتم إغلاق التكت خلال 3 ثواني...');
            setTimeout(() => interaction.channel.delete(), 3000);
        }
        else if (id === 't_summon_owner') {
            interaction.reply({ content: `استدعاء للأونر <@&${ROLES.OWNER}> من قبل ${interaction.user}` });
        }
        else if (id === 't_summon_support') {
            interaction.reply({ content: `استدعاء للدعم <@&${ROLES.SUPPORT}> من قبل ${interaction.user}` });
        }
    }

    // -- معالجة المودلز (النوافذ المنبثقة) --
    if (interaction.isModalSubmit()) {
        if (interaction.customId === 'modal_create_id') {
            const name = interaction.fields.getTextInputValue('name');
            const age = interaction.fields.getTextInputValue('age');
            const roblox = interaction.fields.getTextInputValue('roblox');
            const genderInput = interaction.fields.getTextInputValue('gender').trim();
            
            const nat_id = Math.floor(100000 + Math.random() * 900000).toString();
            
            db[interaction.user.id] = {
                national_id: nat_id, name, age, roblox, character: 'مواطن', warnings: [], points: 0,
                joinedAt: new Date().toLocaleDateString()
            };
            saveDB(db);

            await interaction.member.roles.remove(ROLES.UNKNOWN);
            await interaction.member.roles.add(ROLES.CITIZEN);
            if (genderInput.includes('بنت')) await interaction.member.roles.add(ROLES.FEMALE);
            else await interaction.member.roles.add(ROLES.MALE);

            interaction.reply({ content: `تم صنع هويتك بنجاح!\nرقمك الوطني: **${nat_id}**`, ephemeral: true });
        }

        else if (interaction.customId === 'modal_verify') {
            const inputId = interaction.fields.getTextInputValue('nat_id').trim();
            const userDb = db[interaction.user.id];
            if (userDb && userDb.national_id === inputId) {
                await interaction.member.roles.add(ROLES.VERIFIED);
                interaction.reply({ content: 'تم التوثيق بنجاح وإعطائك الرتبة!', ephemeral: true });
            } else {
                interaction.reply({ content: 'الرقم الوطني خاطئ!', ephemeral: true });
            }
        }

        else if (interaction.customId === 'modal_ticket') {
            const reason = interaction.fields.getTextInputValue('reason');
            const userDb = db[interaction.user.id];
            const nat_id = userDb ? userDb.national_id : interaction.user.username;

            const channel = await interaction.guild.channels.create({
                name: `┇🔖┇✧・${nat_id}`,
                parent: TICKET_CATEGORY,
                permissionOverwrites: [
                    { id: interaction.guild.id, deny: [PermissionsBitField.Flags.ViewChannel] },
                    { id: interaction.user.id, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] },
                    { id: ROLES.SUPPORT, allow: [PermissionsBitField.Flags.ViewChannel], deny: [PermissionsBitField.Flags.SendMessages] },
                    { id: ROLES.OWNER, allow: [PermissionsBitField.Flags.ViewChannel, PermissionsBitField.Flags.SendMessages] }
                ]
            });

            const row = new ActionRowBuilder().addComponents(
                new ButtonBuilder().setCustomId('t_claim').setLabel('استلام').setStyle(ButtonStyle.Success),
                new ButtonBuilder().setCustomId('t_close').setLabel('قفل التكت').setStyle(ButtonStyle.Danger),
                new ButtonBuilder().setCustomId('t_summon_owner').setLabel('استدعاء الاونر').setStyle(ButtonStyle.Primary),
                new ButtonBuilder().setCustomId('t_summon_support').setLabel('استدعاء مسؤولين التكت').setStyle(ButtonStyle.Secondary)
            );

            await channel.send({
                content: `تكت جديد من ${interaction.user} \nمنشن للدعم: <@&${ROLES.SUPPORT}>\n**السبب:** ${reason}`,
                components: [row]
            });

            interaction.reply({ content: `تم فتح التكت الخاص بك: ${channel}`, ephemeral: true });
        }
    }

    // -- معالجة أوامر السلاش --
    if (interaction.isChatInputCommand()) {
        const { commandName, options, member } = interaction;
        const targetMember = options.getMember('الشخص');
        const targetId = targetMember?.id;

        // التحقق من الصلاحيات المبدئية
        const isOwner = member.roles.cache.has(ROLES.OWNER);
        const isMilitary = member.roles.cache.has(ROLES.MILITARY);

        if (commandName === 'حذف_هويه') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            delete db[targetId];
            saveDB(db);
            await targetMember.roles.set([ROLES.UNKNOWN]);
            interaction.reply(`تم حذف هوية ${targetMember} بنجاح وإرجاعه غير معروف.`);
        }

        else if (commandName === 'mdt') {
            if (!isOwner && !isMilitary) return interaction.reply({ content: 'للعسكر والاونر فقط.', ephemeral: true });
            const data = db[targetId];
            if (!data) return interaction.reply('لا توجد بيانات لهذا الشخص.');
            
            const embed = new EmbedBuilder().setTitle(`MDT: ${targetMember.user.username}`).setColor('Blue')
                .addFields(
                    { name: 'الرقم الوطني', value: data.national_id || 'لا يوجد' },
                    { name: 'الشخصية', value: data.character || 'مواطن' },
                    { name: 'النقاط', value: `${data.points}` },
                    { name: 'عدد التحذيرات', value: `${data.warnings.length}` },
                    { name: 'تاريخ التسجيل بالديسكورد', value: targetMember.user.createdAt.toLocaleDateString() }
                );
            interaction.reply({ embeds: [embed] });
        }

        else if (commandName === 'تغير') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            const newVal = options.getString('التغير');
            if (!db[targetId]) db[targetId] = {};
            db[targetId].character = newVal;
            saveDB(db);
            interaction.reply(`تم تغيير شخصية ${targetMember} إلى: **${newVal}**`);
        }

        else if (commandName === 'تحذير') {
            if (!isOwner && !isMilitary) return interaction.reply({ content: 'للعسكر والاونر فقط.', ephemeral: true });
            const reason = options.getString('السبب');
            if (!db[targetId]) db[targetId] = { warnings: [] };
            if (!db[targetId].warnings) db[targetId].warnings = [];
            db[targetId].warnings.push(reason);
            saveDB(db);

            try {
                await targetMember.send(`تم تحذيرك من قبل ${interaction.user}\n**السبب:** ${reason}\n<a:AttentionAnimated:1478492988421443757> <a:emoji_26:1520109726065496295>`);
            } catch(e) {} // إذا كان الخاص مغلق
            interaction.reply(`تم تحذير ${targetMember} بنجاح وتسجيله في MDT.`);
        }

        else if (commandName === 'شيل') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            if (db[targetId]) {
                db[targetId].warnings = [];
                saveDB(db);
            }
            interaction.reply(`تم مسح جميع تحذيرات ${targetMember}.`);
        }

        else if (commandName === 'رول') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            const selectedRoles = [
                options.getRole('الرتبه١'), options.getRole('الرتبه٢'), 
                options.getRole('الرتبه٣'), options.getRole('الرتبه٤'), options.getRole('الرتبه٥')
            ].filter(r => r !== null);

            const roleIds = selectedRoles.map(r => r.id);
            if (new Set(roleIds).size !== roleIds.length) {
                return interaction.reply({ content: 'يوجد خطأ: لقد قمت بتكرار رتبة في الخانات!', ephemeral: true });
            }

            for (const role of selectedRoles) {
                if (targetMember.roles.cache.has(role.id)) {
                    await targetMember.roles.remove(role);
                } else {
                    await targetMember.roles.add(role);
                }
            }
            interaction.reply(`تمت عملية تبديل الرتب لـ ${targetMember} بنجاح.`);
        }

        else if (commandName === 'توقيف') {
            if (!isOwner && !isMilitary) return interaction.reply({ content: 'للعسكر والاونر فقط.', ephemeral: true });
            await targetMember.roles.set([ROLES.ARRESTED]);
            interaction.reply(`تم توقيف ${targetMember} وسحب جميع رتبه.`);
        }

        else if (commandName === 'نقاطي') {
            if (!isMilitary && !isOwner) return interaction.reply({ content: 'للعسكر فقط.', ephemeral: true });
            const points = db[interaction.user.id]?.points || 0;
            interaction.reply({ content: `لديك "${points}" من النقاط.`, ephemeral: true });
        }

        else if (commandName === 'كم_نقاطه') {
            if (!isOwner && !isMilitary) return interaction.reply({ content: 'للعسكر والاونر فقط.', ephemeral: true });
            const points = db[targetId]?.points || 0;
            interaction.reply(`النقاط الحالية لـ ${targetMember} هي: **${points}**`);
        }

        else if (commandName === 'اعطاء_نقاط') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            const amount = options.getInteger('الكميه');
            if (!db[targetId]) db[targetId] = { points: 0 };
            db[targetId].points = (db[targetId].points || 0) + amount;
            saveDB(db);
            interaction.reply(`تم إضافة ${amount} نقاط لـ ${targetMember}. الإجمالي: ${db[targetId].points}`);
        }

        else if (commandName === 'سحب_نقاط') {
            if (!isOwner) return interaction.reply({ content: 'للاونر فقط.', ephemeral: true });
            const amount = options.getInteger('الكميه');
            if (!db[targetId]) db[targetId] = { points: 0 };
            db[targetId].points -= amount;
            if (db[targetId].points < 0) db[targetId].points = 0;
            saveDB(db);
            interaction.reply(`تم سحب النقاط من ${targetMember}. الإجمالي الحالي: ${db[targetId].points}`);
        }
    }
});

client.login(process.env.DISCORD_TOKEN);
