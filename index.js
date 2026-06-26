const { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder, PermissionFlagsBits } = require('discord.js');
const express = require('express');

// ========== إعداد Express لمنع الخمول في Render ==========
const app = express();
app.get('/', (req, res) => res.send('البوت شغال ✅'));
app.listen(3000, () => console.log('السيرفر الوهمي شغال على بورت 3000'));

// ========== البوت ==========
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
  ],
  partials: [Partials.Channel, Partials.Message],
});

// ========== الرتب والمعرفات ==========
const ROLES = {
  SOLDIER_ON:   '1520077188135780494',  // عسكري متصل
  SOLDIER_OFF:  '1520084329714421800',  // عسكري غير متصل
  VISITOR:      '1520087730544050436',  // زائر / ضيف
  CITIZEN:      '1474724032849907722',  // مواطن
  MALE:         '1476903628714410079',  // ولد
  FEMALE:       '1476903782112821258',  // بنت
  STARVING:     '1520075245308874853',  // جائع (ميت)
  SELLER:       '1520153220100522126',  // بيع
};

const OWNER_ID = '1306034100544737461';

// ========== الإيموجيات ==========
const EMOJI_WARNING1 = '<a:emoji_26:1520109726065496295>';
const EMOJI_WARNING2 = '<a:emoji_28:1520109788485128202>';
const EMOJI_LOADING  = '<a:emoji_26:1520109763952771204>';

// ========== المنيو ==========
const MENU = [
  { name: 'برجر',    hunger: 50,  thirst: 0  },
  { name: 'ماء',     hunger: 0,   thirst: 30 },
  { name: 'عصير',    hunger: 0,   thirst: 20 },
  { name: 'بيتزا',   hunger: 45,  thirst: 0  },
  { name: 'فراوله',  hunger: 5,   thirst: 3  },
  { name: 'حلوه',    hunger: 10,  thirst: 0  },
  { name: 'تفاح',    hunger: 15,  thirst: 15 },
  { name: 'ببسي',    hunger: 0,   thirst: 35 },
  { name: 'سفن اب',  hunger: 0,   thirst: 35 },
  { name: 'حمضيات',  hunger: 0,   thirst: 35 },
  { name: 'ديو',     hunger: 0,   thirst: 35 },
  { name: 'وجبه',    hunger: 100, thirst: 0  },
];

// ========== قاعدة البيانات في الذاكرة ==========
// التحذيرات: { userId: [{ by, reason, timestamp }] }
const warnings = {};

// الهويات: { userId: { name, phone, gender } }
const identities = {};

// الشنط (جوع وعطش): { userId: { hunger: 0-100, thirst: 0-100, items: [] } }
const bags = {};

// الأدمن المؤقت لإعداد الروم
// roomSetup: { guildId: { loginRoomId, logRoomId, registrationRoomId } }
const roomSetup = {};

// ========== دوال مساعدة ==========
function getBag(userId) {
  if (!bags[userId]) bags[userId] = { hunger: 100, thirst: 100, items: [] };
  return bags[userId];
}

function cap(val) { return Math.min(100, Math.max(0, val)); }

function isSoldier(member) {
  return member.roles.cache.has(ROLES.SOLDIER_ON) || member.roles.cache.has(ROLES.SOLDIER_OFF);
}

function isSeller(member) {
  return member.roles.cache.has(ROLES.SELLER);
}

function isOwner(member) {
  return member.id === OWNER_ID;
}

function getIdentityName(userId) {
  return identities[userId]?.name || null;
}

// رتبة أعلى من البوت؟
function roleAboveBot(guild, roleId) {
  const botMember = guild.members.me;
  const role = guild.roles.cache.get(roleId);
  if (!role) return false;
  return role.position >= botMember.roles.highest.position;
}

// ========== نقص الجوع والعطش كل ساعة ==========
setInterval(() => {
  const now = Date.now();
  for (const [userId, bag] of Object.entries(bags)) {
    bag.hunger  = cap(bag.hunger  - 50);
    bag.thirst  = cap(bag.thirst  - 50);

    // لو وصل الجوع صفر → أعطه رتبة الجائع
    if (bag.hunger <= 0 || bag.thirst <= 0) {
      client.guilds.cache.forEach(async guild => {
        try {
          const member = await guild.members.fetch(userId).catch(() => null);
          if (!member) return;

          // أبلغ الشخص إذا بقي 15 أو 25
          if ((bag.hunger === 15 || bag.hunger === 25) && bag.hunger > 0) {
            member.send(`⚠️ انتبه! أنت جائع، إذا لم تأكل ستتوقف! اشتر من المتجر.`).catch(() => {});
          }
          if (bag.hunger <= 0 || bag.thirst <= 0) {
            // أشعر الأونر
            const owner = await guild.members.fetch(OWNER_ID).catch(() => null);
            if (owner) owner.send(`⚠️ **${member.displayName}** لم يأكل/يشرب وهو متصل! (<@${userId}>)`).catch(() => {});

            // شيل كل الرتب إلا الولد/بنت
            const toRemove = member.roles.cache.filter(r =>
              r.id !== ROLES.MALE && r.id !== ROLES.FEMALE && r.id !== guild.roles.everyone.id
            );
            await member.roles.remove(toRemove).catch(() => {});
            await member.roles.add(ROLES.STARVING).catch(() => {});
          }
        } catch {}
      });
    }
  }
}, 60 * 60 * 1000); // كل ساعة

// ========== لما البوت يكون جاهز ==========
client.once('ready', () => {
  console.log(`✅ البوت شغال: ${client.user.tag}`);
});

// ========== استقبال الأعضاء الجدد ==========
client.on('guildMemberAdd', async member => {
  try {
    await member.roles.add(ROLES.VISITOR).catch(() => {});

    // اشوف لو في روم التسجيل
    const setup = roomSetup[member.guild.id];
    if (!setup?.registrationRoomId) return;

    const regRoom = member.guild.channels.cache.get(setup.registrationRoomId);
    if (!regRoom) return;

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId(`confirm_join_${member.id}`).setLabel('أكمل ✅').setStyle(ButtonStyle.Success)
    );

    await regRoom.send({
      content: `السلام عليكم <@${member.id}>، تأكيد دخولك للسيرفر. إذا ضغطت زر أكمل رح يوصلك رسالة خاصة من البوت.`,
      components: [row],
    });
  } catch (e) { console.error(e); }
});

// ========== الأزرار ==========
client.on('interactionCreate', async interaction => {
  if (!interaction.isButton()) return;

  const { customId, member, guild } = interaction;

  // ===== زر تأكيد الدخول =====
  if (customId.startsWith('confirm_join_')) {
    const targetId = customId.replace('confirm_join_', '');
    if (interaction.user.id !== targetId) {
      return interaction.reply({ content: 'هذا الزر مو لك.', ephemeral: true });
    }
    await interaction.reply({ content: 'تم! راح يوصلك رسالة في الخاص من البوت 📨', ephemeral: true });

    // ابدأ محادثة الهوية في الخاص
    startIdentityConversation(interaction.user, guild);
    return;
  }

  // ===== زر تسجيل الدخول/الخروج =====
  if (customId === 'soldier_checkin') {
    if (!isSoldier(member)) {
      return interaction.reply({ content: 'هذا الزر للعسكر فقط.', ephemeral: true });
    }

    const setup = roomSetup[guild.id];
    const logRoom = setup?.logRoomId ? guild.channels.cache.get(setup.logRoomId) : null;

    if (member.roles.cache.has(ROLES.SOLDIER_OFF)) {
      // غير متصل → متصل
      await member.roles.remove(ROLES.SOLDIER_OFF).catch(() => {});
      await member.roles.add(ROLES.SOLDIER_ON).catch(() => {});
      await interaction.reply({ content: '✅ تم تسجيل دخولك بنجاح!', ephemeral: true });
      if (logRoom) {
        const name = getIdentityName(member.id) || member.displayName;
        await logRoom.send(`**${name}** متصل 🟢`);
      }
    } else if (member.roles.cache.has(ROLES.SOLDIER_ON)) {
      // متصل → غير متصل
      await member.roles.remove(ROLES.SOLDIER_ON).catch(() => {});
      await member.roles.add(ROLES.SOLDIER_OFF).catch(() => {});
      await interaction.reply({ content: '✅ تم تسجيل خروجك بنجاح!', ephemeral: true });
      if (logRoom) {
        const name = getIdentityName(member.id) || member.displayName;
        await logRoom.send(`**${name}** غير متصل 🔴`);
      }
    }
    return;
  }
});

// ========== محادثة الهوية في الخاص ==========
const pendingIdentity = {}; // { userId: { step, name, phone } }

async function startIdentityConversation(user, guild) {
  try {
    pendingIdentity[user.id] = { step: 'name', guild };
    await user.send('مرحباً بك في سيرفر رولباك! 🎮\n\nهل تريد أن تصنع هويتك في السيرفر للمزح واللعب فقط؟\n\nاكتب **نعم** أو **لا**');
  } catch {
    console.log('ما قدر يرسل خاص لـ', user.tag);
  }
}

// ========== استقبال الرسائل ==========
client.on('messageCreate', async message => {
  if (message.author.bot) return;

  const content = message.content.trim();
  const guild = message.guild;

  // ===== محادثة الهوية في الخاص =====
  if (!guild && pendingIdentity[message.author.id]) {
    return handleIdentityDM(message);
  }

  if (!guild) return;

  const member = message.member;
  if (!member) return;

  // ===== أوامر الإعداد =====
  if (content === '!أبدأ١') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].loginRoomId = message.channel.id;
    roomSetup[guild.id].logRoomId = null; // سيُحدد بـ !أبدأ٢

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId('soldier_checkin').setLabel('تسجيل 🟢').setStyle(ButtonStyle.Success)
    );
    const embed = new EmbedBuilder()
      .setColor(0x00ff00)
      .setDescription('**تسجيل دخول وخروج للعسكر فقط**\nاضغط الزر أدناه لتسجيل حضورك أو غيابك.');
    await message.channel.send({ embeds: [embed], components: [row] });
    return;
  }

  if (content === '!أبدأ٢') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].logRoomId = message.channel.id;

    // اعرض قائمة العسكر المتصلين وغير المتصلين
    const soldiers = guild.members.cache.filter(m =>
      m.roles.cache.has(ROLES.SOLDIER_ON) || m.roles.cache.has(ROLES.SOLDIER_OFF)
    );

    let txt = '**📋 قائمة العسكر:**\n\n';
    if (soldiers.size === 0) {
      txt += 'لا يوجد عسكر حالياً.';
    } else {
      soldiers.forEach(m => {
        const name = getIdentityName(m.id) || m.displayName;
        const status = m.roles.cache.has(ROLES.SOLDIER_ON) ? 'متصل 🟢' : 'غير متصل 🔴';
        txt += `**${name}** ${status}\n`;
      });
    }
    await message.channel.send(txt);
    return;
  }

  if (content === '!أبدأ٣') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].registrationRoomId = message.channel.id;

    // اجعل الروم مخصص للعسكر فقط (اعرض للعسكر، خفِ عن الباقين)
    await message.channel.permissionOverwrites.set([
      { id: guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
      { id: ROLES.VISITOR,           allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
    ]).catch(() => {});

    await message.channel.send('✅ تم إعداد روم التسجيل. أي زائر جديد رح يشوف هذا الروم.');
    return;
  }

  // ===== أمر الرول =====
  // -رول @شخص @رتبة
  if (content.startsWith('-رول')) {
    if (!isSoldier(member) && !isOwner(member)) return;

    const mentions = message.mentions.members;
    const roleMentions = message.mentions.roles;

    if (!mentions || mentions.size === 0 || !roleMentions || roleMentions.size === 0) {
      return message.channel.send(`اكتب الأمر بهذه الطريقة: \`-رول @الشخص @الرتبة\``);
    }

    const target = mentions.first();
    const role   = roleMentions.first();

    // تحقق من الرتبة القوية
    if (roleAboveBot(guild, role.id)) {
      return message.channel.send(`⚠️ انتبه! هذه رتبة قوية جداً ما أقدر أعطيها. تم إلغاء العملية.`);
    }
    if (role.permissions.has(PermissionFlagsBits.Administrator)) {
      return message.channel.send(`⚠️ هذه رتبة بصلاحيات الأونر! تم إلغاء العملية.`);
    }

    if (target.roles.cache.has(role.id)) {
      await target.roles.remove(role).catch(() => {});
      return message.channel.send(`✅ تم إزالة رتبة **${role.name}** من <@${target.id}>.`);
    } else {
      await target.roles.add(role).catch(() => {});
      return message.channel.send(`✅ تم إعطاء <@${target.id}> رتبة **${role.name}**.`);
    }
  }

  // ===== أمر التحذير =====
  // /تحذير الشخص:@منشن السبب:النص
  if (content.startsWith('/تحذير')) {
    if (!isSoldier(member) && !isOwner(member)) return;

    const targetMember = message.mentions.members?.first();
    const reasonMatch  = content.match(/السبب[:\s]+(.+)/);
    const reason       = reasonMatch ? reasonMatch[1].trim() : 'لم يُذكر سبب';

    if (!targetMember) {
      return message.channel.send(`اكتب الأمر بهذه الطريقة:\n\`/تحذير الشخص:@منشن السبب:النص\``);
    }

    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);

    if (!warnings[targetMember.id]) warnings[targetMember.id] = [];
    warnings[targetMember.id].push({
      by:        member.id,
      reason,
      timestamp: Date.now(),
    });

    // أرسل تحذير في الخاص بشكل مرهب
    try {
      await targetMember.send(
        `${EMOJI_WARNING1} ${EMOJI_WARNING2}\n` +
        `**تحذير رسمي من السيرفر!**\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        `تم تحذيرك بواسطة: <@${member.id}>\n` +
        `السبب: **${reason}**\n` +
        `━━━━━━━━━━━━━━━━━━━━\n` +
        `📌 اقرأ القوانين وركز! أي مخالفة أخرى ستعرضك للطرد.`
      );
    } catch {}

    return message.channel.send(`${EMOJI_WARNING1} تم تحذير <@${targetMember.id}> بسبب: **${reason}**`);
  }

  // ===== أمر شيل التحذيرات =====
  // /شيل الشخص:@منشن
  if (content.startsWith('/شيل')) {
    if (!isSoldier(member) && !isOwner(member)) return;

    const targetMember = message.mentions.members?.first();
    if (!targetMember) {
      return message.channel.send(`اكتب الأمر بهذه الطريقة:\n\`/شيل الشخص:@منشن\``);
    }

    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);

    warnings[targetMember.id] = [];
    return message.channel.send(`✅ تم إزالة جميع تحذيرات <@${targetMember.id}>.`);
  }

  // ===== أمر التحذيرات =====
  // -تحذيرات أو -تحذيرات @منشن
  if (content.startsWith('-تحذيرات')) {
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);

    const targetMember = message.mentions.members?.first();

    if (targetMember) {
      // تحذيرات شخص معين
      const w = warnings[targetMember.id];
      if (!w || w.length === 0) {
        return message.channel.send(`✅ لا يوجد تحذيرات لـ <@${targetMember.id}>.`);
      }
      let txt = `📋 **تحذيرات <@${targetMember.id}>:**\n`;
      w.forEach((warn, i) => {
        txt += `${i + 1}. بواسطة <@${warn.by}> — السبب: **${warn.reason}**\n`;
      });
      return message.channel.send(txt);
    } else {
      // آخر 10 تحذيرات في السيرفر
      const allWarnings = [];
      for (const [userId, wList] of Object.entries(warnings)) {
        for (const w of wList) {
          allWarnings.push({ userId, ...w });
        }
      }
      allWarnings.sort((a, b) => b.timestamp - a.timestamp);
      const last10 = allWarnings.slice(0, 10);

      if (last10.length === 0) {
        return message.channel.send('لا يوجد تحذيرات.');
      }

      let txt = '📋 **آخر 10 تحذيرات:**\n';
      last10.forEach((w, i) => {
        txt += `${i + 1}. <@${w.userId}> حذّره <@${w.by}> — السبب: **${w.reason}**\n`;
      });
      return message.channel.send(txt);
    }
  }

  // ===== أمر الهوية =====
  // /هويه الشخص:@منشن
  if (content.startsWith('/هويه')) {
    if (!isSoldier(member) && !isOwner(member)) return;

    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);

    const targetMember = message.mentions.members?.first();
    if (!targetMember) {
      return message.channel.send(`اكتب الأمر بهذه الطريقة:\n\`/هويه الشخص:@منشن\``);
    }

    const id = identities[targetMember.id];
    if (!id) {
      return message.channel.send(`❌ لا توجد هوية لـ <@${targetMember.id}>.`);
    }

    return message.channel.send(
      `🪪 **هوية <@${targetMember.id}>:**\n` +
      `الاسم: **${id.name}**\n` +
      `رقم الجوال المزيف: **${id.phone}**\n` +
      `الجنس: **${id.gender === 'male' ? 'ولد' : 'بنت'}**`
    );
  }

  // ===== أمر حذف الهوية (الملك فقط) =====
  // /حذف هويه:@منشن
  if (content.startsWith('/حذف هويه')) {
    if (!isOwner(member)) return;

    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);

    const targetMember = message.mentions.members?.first();
    if (!targetMember) return message.channel.send(`اكتب: \`/حذف هويه:@منشن\``);

    delete identities[targetMember.id];

    // شيل كل الرتب وأعطه رتبة الزائر
    const toRemove = targetMember.roles.cache.filter(r => r.id !== guild.roles.everyone.id);
    await targetMember.roles.remove(toRemove).catch(() => {});
    await targetMember.roles.add(ROLES.VISITOR).catch(() => {});

    return message.channel.send(`✅ تم حذف هوية <@${targetMember.id}> وإعادة تعيينه كزائر.`);
  }

  // ===== أمر الشنطة =====
  if (content === '-شنطه') {
    const bag = getBag(message.author.id);
    const hungerBar  = makeBar(bag.hunger);
    const thirstBar  = makeBar(bag.thirst, 'blue');
    const itemsText  = bag.items.length > 0 ? bag.items.join('، ') : 'فارغة';

    return message.channel.send({
      content: `🎒 **شنطة <@${message.author.id}>:**\n\n🔴 الجوع:   ${hungerBar} ${bag.hunger}%\n🔵 العطش:  ${thirstBar} ${bag.thirst}%\n\n📦 **المحتويات:** ${itemsText}\n\nاكتب اسم الأكلة لأكلها، أو اكتب اسمها ومنشن شخص لإعطائه إياها.`,
    });
  }

  // ===== أكل من الشنطة أو إعطاء شخص =====
  const bagItem = MENU.find(i => content.startsWith(i.name));
  if (bagItem) {
    const bag = getBag(message.author.id);
    const targetMention = message.mentions.members?.first();

    if (!bag.items.includes(bagItem.name)) {
      return message.channel.send(`❌ ما عندك **${bagItem.name}** في شنطتك!`);
    }

    if (targetMention) {
      // إعطاء شخص
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId(`give_item_${bagItem.name}_${message.author.id}_${targetMention.id}`).setLabel('نعم ✅').setStyle(ButtonStyle.Success),
        new ButtonBuilder().setCustomId(`cancel_give`).setLabel('لا ❌').setStyle(ButtonStyle.Danger),
      );
      return message.channel.send({ content: `هل تريد إعطاء **${bagItem.name}** لـ <@${targetMention.id}>؟`, components: [row] });
    } else {
      // أكل
      bag.items = bag.items.filter(i => i !== bagItem.name);
      bag.hunger = cap(bag.hunger + bagItem.hunger);
      bag.thirst = cap(bag.thirst + bagItem.thirst);
      return message.channel.send(`✅ أكلت **${bagItem.name}**! الجوع: ${bag.hunger}% | العطش: ${bag.thirst}%`);
    }
  }

  // ===== أمر المنيو =====
  if (content === '/منيو') {
    let txt = '🛒 **المنيو:**\n\n';
    MENU.forEach(item => {
      txt += `**${item.name}** — `;
      if (item.hunger > 0) txt += `جوع +${item.hunger} `;
      if (item.thirst > 0) txt += `عطش +${item.thirst}`;
      txt += '\n';
    });
    return message.channel.send(txt);
  }

  // ===== أمر البيع =====
  // /بيع الغرض:اسم الشخص:@منشن
  if (content.startsWith('/بيع')) {
    if (!isSeller(member)) return;

    const targetMember = message.mentions.members?.first();
    const itemMatch    = content.match(/الغرض[:\s]+([^\s@]+)/);
    const itemName     = itemMatch ? itemMatch[1].trim() : null;
    const menuItem     = MENU.find(i => i.name === itemName);

    if (!targetMember || !menuItem) {
      return message.channel.send(`اكتب: \`/بيع الغرض:الاسم الشخص:@منشن\`\n\nالأغراض المتاحة: ${MENU.map(i => i.name).join('، ')}`);
    }

    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    const bag = getBag(targetMember.id);
    bag.items.push(menuItem.name);
    return message.channel.send(`✅ تم بيع **${menuItem.name}** لـ <@${targetMember.id}>!`);
  }

  // ===== أمر فول (الملك فقط) =====
  // /فول الشخص:@منشن
  if (content.startsWith('/فول')) {
    if (!isOwner(member)) return;

    const targetMember = message.mentions.members?.first();
    if (!targetMember) return message.channel.send(`اكتب: \`/فول الشخص:@منشن\``);

    const bag = getBag(targetMember.id);
    bag.hunger = 100;
    bag.thirst = 100;
    return message.channel.send(`✅ تم ملء بار <@${targetMember.id}> بالكامل!`);
  }
});

// ===== زر إعطاء الغرض =====
client.on('interactionCreate', async interaction => {
  if (!interaction.isButton()) return;
  const { customId } = interaction;

  if (customId.startsWith('give_item_')) {
    const parts     = customId.split('_');
    const itemName  = parts[2];
    const fromId    = parts[3];
    const toId      = parts[4];

    if (interaction.user.id !== fromId) {
      return interaction.reply({ content: 'هذا مو لك.', ephemeral: true });
    }

    const fromBag = getBag(fromId);
    const toBag   = getBag(toId);
    const item    = MENU.find(i => i.name === itemName);

    if (!fromBag.items.includes(itemName)) {
      return interaction.update({ content: '❌ ما عاد عندك هذا الغرض!', components: [] });
    }

    fromBag.items = fromBag.items.filter(i => i !== itemName);
    toBag.items.push(itemName);
    return interaction.update({ content: `✅ تم إعطاء **${itemName}** لـ <@${toId}> بنجاح!`, components: [] });
  }

  if (customId === 'cancel_give') {
    return interaction.update({ content: '✅ تم إلغاء العملية.', components: [] });
  }
});

// ========== محادثة الهوية في الخاص ==========
async function handleIdentityDM(message) {
  const userId  = message.author.id;
  const state   = pendingIdentity[userId];
  const content = message.content.trim();

  if (content === 'إلغاء' || content === 'الغاء') {
    delete pendingIdentity[userId];
    return message.author.send('✅ تم إلغاء العملية.');
  }

  if (state.step === 'name') {
    if (content === 'نعم') {
      pendingIdentity[userId].step = 'enter_name';
      return message.author.send('حسناً! اكتب اسمك المزيف أو الحقيقي، مثال: **ابو احمد**');
    } else if (content === 'لا') {
      delete pendingIdentity[userId];
      return message.author.send('حسناً، يمكنك إنشاء هويتك لاحقاً.');
    }
  }

  if (state.step === 'enter_name') {
    pendingIdentity[userId].name  = content;
    pendingIdentity[userId].step  = 'ask_phone';
    return message.author.send(`تمام! هل تريد صنع رقم مزيف للهاتف؟ (مزيف 100% للسيرفر فقط)\n\nاكتب **نعم** أو **لا**`);
  }

  if (state.step === 'ask_phone') {
    if (content === 'نعم') {
      pendingIdentity[userId].step = 'enter_phone';
      return message.author.send('اكتب رقمك المزيف بهذا الشكل: **17******* (8 أرقام تبدأ بـ 17)');
    } else {
      pendingIdentity[userId].phone = 'غير مسجل';
      pendingIdentity[userId].step  = 'ask_gender';
      return message.author.send('ما جنسيتك؟ اكتب **ولد** أو **بنت**');
    }
  }

  if (state.step === 'enter_phone') {
    // تحقق من الرقم
    if (!/^17\d{6}$/.test(content)) {
      return message.author.send('❌ الرقم غلط! لازم يكون 8 أرقام يبدأ بـ 17 مثال: **17123456**\n\nاكتب **إلغاء** لإلغاء العملية.');
    }
    // تحقق من التكرار
    const duplicate = Object.entries(identities).find(([id, data]) => data.phone === content && id !== userId);
    if (duplicate) {
      return message.author.send('❌ هذا الرقم عند شخص آخر! اختر رقماً مختلفاً.');
    }
    pendingIdentity[userId].phone = content;
    pendingIdentity[userId].step  = 'ask_gender';
    return message.author.send('تم تسجيل الرقم ✅\n\nما جنسيتك؟ اكتب **ولد** أو **بنت**');
  }

  if (state.step === 'ask_gender') {
    if (content !== 'ولد' && content !== 'بنت') {
      return message.author.send('اكتب **ولد** أو **بنت** فقط.');
    }

    const gender = content === 'ولد' ? 'male' : 'female';
    identities[userId] = {
      name:   state.name,
      phone:  state.phone,
      gender,
    };

    // أعطه الرتب المناسبة
    const guild = state.guild;
    try {
      const guildMember = await guild.members.fetch(userId);
      await guildMember.roles.remove(ROLES.VISITOR).catch(() => {});
      await guildMember.roles.add(ROLES.CITIZEN).catch(() => {});
      await guildMember.roles.add(gender === 'male' ? ROLES.MALE : ROLES.FEMALE).catch(() => {});
    } catch {}

    delete pendingIdentity[userId];
    return message.author.send(`🎉 مرحباً بك في سيرفر رولباك **${state.name}**!\n\nتم إنشاء هويتك بنجاح ✅`);
  }
}

// ========== شريط الجوع/العطش ==========
function makeBar(value, color = 'orange') {
  const filled = Math.round(value / 10);
  const empty  = 10 - filled;
  const char   = color === 'blue' ? '🔵' : '🟠';
  return char.repeat(filled) + '⚫'.repeat(empty);
}

// ========== تشغيل البوت ==========
client.login(process.env.DISCORD_TOKEN);
