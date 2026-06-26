const { Client, GatewayIntentBits, Partials, ActionRowBuilder, ButtonBuilder, ButtonStyle, EmbedBuilder, PermissionFlagsBits } = require('discord.js');
const express = require('express');

// ========== Express لمنع الخمول ==========
const app = express();
// استبدل السطر الموجود بهذا:
const PORT = process.env.PORT || 10000; 
app.listen(PORT, '0.0.0.0', () => console.log(`✅ Express شغال على بورت ${PORT}`));
// ========== البوت ==========
const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMembers,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
    GatewayIntentBits.DirectMessages,
    GatewayIntentBits.GuildPresences,
  ],
  partials: [Partials.Channel, Partials.Message, Partials.GuildMember],
});

// ========== الرتب ==========
const ROLES = {
  SOLDIER_ON:  '1520077188135780494',
  SOLDIER_OFF: '1520084329714421800',
  VISITOR:     '1520087730544050436',
  CITIZEN:     '1474724032849907722',
  MALE:        '1476903628714410079',
  FEMALE:      '1476903782112821258',
  STARVING:    '1520075245308874853',
  SELLER:      '1520153220100522126',
};

const OWNER_ID = '1306034100544737461';

const EMOJI_WARNING1 = '<a:emoji_26:1520109726065496295>';
const EMOJI_WARNING2 = '<a:emoji_28:1520109788485128202>';
const EMOJI_LOADING  = '<a:emoji_26:1520109763952771204>';

// ========== المنيو ==========
const MENU = [
  { name: 'برجر',   hunger: 50,  thirst: 0  },
  { name: 'ماء',    hunger: 0,   thirst: 30 },
  { name: 'عصير',   hunger: 0,   thirst: 20 },
  { name: 'بيتزا',  hunger: 45,  thirst: 0  },
  { name: 'فراوله', hunger: 5,   thirst: 3  },
  { name: 'حلوه',   hunger: 10,  thirst: 0  },
  { name: 'تفاح',   hunger: 15,  thirst: 15 },
  { name: 'ببسي',   hunger: 0,   thirst: 35 },
  { name: 'سفن اب', hunger: 0,   thirst: 35 },
  { name: 'حمضيات', hunger: 0,   thirst: 35 },
  { name: 'ديو',    hunger: 0,   thirst: 35 },
  { name: 'وجبه',   hunger: 100, thirst: 0  },
];

// ========== البيانات ==========
const warnings   = {};
const identities = {};
const bags       = {};
const roomSetup  = {};
const pendingIdentity = {};

// ========== دوال مساعدة ==========
function getBag(userId) {
  if (!bags[userId]) bags[userId] = { hunger: 100, thirst: 100, items: [] };
  return bags[userId];
}
function cap(v) { return Math.min(100, Math.max(0, v)); }
function isSoldier(m) { return m.roles.cache.has(ROLES.SOLDIER_ON) || m.roles.cache.has(ROLES.SOLDIER_OFF); }
function isSeller(m)  { return m.roles.cache.has(ROLES.SELLER); }
function isOwner(m)   { return m.id === OWNER_ID; }
function getIdentityName(uid) { return identities[uid]?.name || null; }

function makeBar(value) {
  const f = Math.round(value / 10);
  return '🟧'.repeat(f) + '⬛'.repeat(10 - f);
}

function isRoleAboveBot(guild, roleId) {
  const role = guild.roles.cache.get(roleId);
  if (!role) return false;
  return role.position >= guild.members.me.roles.highest.position;
}

// ========== نقص الجوع كل ساعة ==========
setInterval(async () => {
  for (const [userId, bag] of Object.entries(bags)) {
    bag.hunger = cap(bag.hunger - 50);
    bag.thirst = cap(bag.thirst - 50);

    for (const guild of client.guilds.cache.values()) {
      try {
        const member = await guild.members.fetch(userId).catch(() => null);
        if (!member) continue;

        if (bag.hunger === 25 || bag.hunger === 15) {
          member.send(`⚠️ انتبه! جوعك ${bag.hunger}% اشتري من المتجر قبل ما تتوقف!`).catch(() => {});
        }
        if (bag.thirst === 25 || bag.thirst === 15) {
          member.send(`⚠️ انتبه! عطشك ${bag.thirst}% اشتري من المتجر قبل ما تتوقف!`).catch(() => {});
        }

        if (bag.hunger <= 0 || bag.thirst <= 0) {
          const owner = await guild.members.fetch(OWNER_ID).catch(() => null);
          if (owner) owner.send(`⚠️ **${member.displayName}** (<@${userId}>) لم يأكل/يشرب وهو متصل!`).catch(() => {});
          const toRemove = member.roles.cache.filter(r => r.id !== ROLES.MALE && r.id !== ROLES.FEMALE && r.id !== guild.roles.everyone.id);
          await member.roles.remove(toRemove).catch(() => {});
          await member.roles.add(ROLES.STARVING).catch(() => {});
        }
      } catch {}
    }
  }
}, 60 * 60 * 1000);

// ========== Ready ==========
client.once('ready', () => {
  console.log(`✅ البوت شغال: ${client.user.tag}`);
  console.log(`✅ في ${client.guilds.cache.size} سيرفر`);
});

// ========== عضو جديد ==========
client.on('guildMemberAdd', async member => {
  try {
    await member.roles.add(ROLES.VISITOR).catch(() => {});
    const setup = roomSetup[member.guild.id];
    if (!setup?.registrationRoomId) return;
    const ch = member.guild.channels.cache.get(setup.registrationRoomId);
    if (!ch) return;
    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId(`confirm_join_${member.id}`).setLabel('أكمل ✅').setStyle(ButtonStyle.Success)
    );
    await ch.send({ content: `السلام عليكم <@${member.id}>! تأكيد دخولك للسيرفر، اضغط الزر للمتابعة.`, components: [row] });
  } catch (e) { console.error('guildMemberAdd error:', e); }
});

// ========== الأزرار ==========
client.on('interactionCreate', async interaction => {
  if (!interaction.isButton()) return;
  const { customId, member, guild } = interaction;

  // زر تأكيد الدخول
  if (customId.startsWith('confirm_join_')) {
    const targetId = customId.replace('confirm_join_', '');
    if (interaction.user.id !== targetId) return interaction.reply({ content: 'هذا الزر مو لك.', ephemeral: true });
    await interaction.reply({ content: 'تم! رسالة خاصة من البوت في طريقها 📨', ephemeral: true });
    startIdentityConversation(interaction.user, guild);
    return;
  }

  // زر تسجيل دخول/خروج
  if (customId === 'soldier_checkin') {
    if (!isSoldier(member)) return interaction.reply({ content: 'هذا الزر للعسكر فقط.', ephemeral: true });
    const setup   = roomSetup[guild.id];
    const logRoom = setup?.logRoomId ? guild.channels.cache.get(setup.logRoomId) : null;
    const name    = getIdentityName(member.id) || member.displayName;

    if (member.roles.cache.has(ROLES.SOLDIER_OFF)) {
      await member.roles.remove(ROLES.SOLDIER_OFF).catch(() => {});
      await member.roles.add(ROLES.SOLDIER_ON).catch(() => {});
      await interaction.reply({ content: '✅ تم تسجيل دخولك بنجاح!', ephemeral: true });
      if (logRoom) await logRoom.send(`**${name}** متصل 🟢`);
    } else {
      await member.roles.remove(ROLES.SOLDIER_ON).catch(() => {});
      await member.roles.add(ROLES.SOLDIER_OFF).catch(() => {});
      await interaction.reply({ content: '✅ تم تسجيل خروجك بنجاح!', ephemeral: true });
      if (logRoom) await logRoom.send(`**${name}** غير متصل 🔴`);
    }
    return;
  }

  // زر إعطاء غرض
  if (customId.startsWith('give_item_')) {
    const parts    = customId.split('_');
    const itemName = parts[2];
    const fromId   = parts[3];
    const toId     = parts[4];
    if (interaction.user.id !== fromId) return interaction.update({ content: 'هذا مو لك.', components: [] });
    const fromBag = getBag(fromId);
    if (!fromBag.items.includes(itemName)) return interaction.update({ content: '❌ ما عاد عندك هذا الغرض!', components: [] });
    fromBag.items = fromBag.items.filter(i => i !== itemName);
    getBag(toId).items.push(itemName);
    return interaction.update({ content: `✅ تم إعطاء **${itemName}** لـ <@${toId}> بنجاح!`, components: [] });
  }

  if (customId === 'cancel_give') {
    return interaction.update({ content: '✅ تم إلغاء العملية.', components: [] });
  }
});

// ========== الرسائل ==========
client.on('messageCreate', async message => {
  if (message.author.bot) return;

  const content = message.content.trim();

  // رسائل الخاص (محادثة الهوية)
  if (!message.guild) {
    if (pendingIdentity[message.author.id]) return handleIdentityDM(message);
    return;
  }

  const guild  = message.guild;
  const member = message.member;
  if (!member) return;

  // ===== !أبدأ١ - روم تسجيل الدخول =====
  if (content === '!أبدأ١') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].loginRoomId = message.channel.id;

    const row = new ActionRowBuilder().addComponents(
      new ButtonBuilder().setCustomId('soldier_checkin').setLabel('تسجيل 🟢').setStyle(ButtonStyle.Success)
    );
    const embed = new EmbedBuilder()
      .setColor(0x00ff00)
      .setDescription('**تسجيل دخول وخروج للعسكر فقط**\nاضغط الزر أدناه لتسجيل حضورك أو غيابك.');
    await message.channel.send({ embeds: [embed], components: [row] });
    return;
  }

  // ===== !أبدأ٢ - روم بث العسكر =====
  if (content === '!أبدأ٢') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].logRoomId = message.channel.id;

    const soldiers = guild.members.cache.filter(m =>
      m.roles.cache.has(ROLES.SOLDIER_ON) || m.roles.cache.has(ROLES.SOLDIER_OFF)
    );

    let txt = '**📋 قائمة العسكر:**\n\n';
    if (soldiers.size === 0) {
      txt += 'لا يوجد عسكر حالياً.';
    } else {
      soldiers.forEach(m => {
        const n      = getIdentityName(m.id) || m.displayName;
        const status = m.roles.cache.has(ROLES.SOLDIER_ON) ? 'متصل 🟢' : 'غير متصل 🔴';
        txt += `**${n}** ${status}\n`;
      });
    }
    await message.channel.send(txt);
    return;
  }

  // ===== !أبدأ٣ - روم التسجيل للزوار =====
  if (content === '!أبدأ٣') {
    if (!isOwner(member)) return;
    await message.delete().catch(() => {});
    if (!roomSetup[guild.id]) roomSetup[guild.id] = {};
    roomSetup[guild.id].registrationRoomId = message.channel.id;

    // خصص الروم للزوار فقط
    await message.channel.permissionOverwrites.set([
      { id: guild.roles.everyone.id, deny: [PermissionFlagsBits.ViewChannel] },
      { id: ROLES.VISITOR, allow: [PermissionFlagsBits.ViewChannel, PermissionFlagsBits.SendMessages] },
    ]).catch(() => {});

    await message.channel.send('✅ تم إعداد روم استقبال الزوار.');
    return;
  }

  // ===== -رول =====
  if (content.startsWith('-رول')) {
    if (!isSoldier(member) && !isOwner(member)) return;
    const target     = message.mentions.members?.first();
    const role       = message.mentions.roles?.first();
    if (!target || !role) return message.channel.send('اكتب الأمر بهذه الطريقة: `-رول @الشخص @الرتبة`');
    if (isRoleAboveBot(guild, role.id) || role.permissions.has(PermissionFlagsBits.Administrator)) {
      return message.channel.send('⚠️ انتبه! هذه رتبة قوية جداً، تم إلغاء العملية.');
    }
    if (target.roles.cache.has(role.id)) {
      await target.roles.remove(role).catch(() => {});
      return message.channel.send(`✅ تم إزالة رتبة **${role.name}** من <@${target.id}>.`);
    } else {
      await target.roles.add(role).catch(() => {});
      return message.channel.send(`✅ تم إعطاء <@${target.id}> رتبة **${role.name}**.`);
    }
  }

  // ===== /تحذير =====
  if (content.startsWith('/تحذير')) {
    if (!isSoldier(member) && !isOwner(member)) return;
    const target      = message.mentions.members?.first();
    const reasonMatch = content.match(/السبب[:\s]+(.+)/);
    const reason      = reasonMatch ? reasonMatch[1].trim() : 'لم يُذكر سبب';
    if (!target) return message.channel.send('اكتب: `/تحذير الشخص:@منشن السبب:النص`');
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    if (!warnings[target.id]) warnings[target.id] = [];
    warnings[target.id].push({ by: member.id, reason, timestamp: Date.now() });
    target.send(
      `${EMOJI_WARNING1} ${EMOJI_WARNING2}\n**تحذير رسمي!**\n━━━━━━━━━━━━━━━━\n` +
      `تم تحذيرك بواسطة: <@${member.id}>\nالسبب: **${reason}**\n━━━━━━━━━━━━━━━━\n📌 اقرأ القوانين وركز!`
    ).catch(() => {});
    return message.channel.send(`${EMOJI_WARNING1} تم تحذير <@${target.id}> — السبب: **${reason}**`);
  }

  // ===== /شيل =====
  if (content.startsWith('/شيل')) {
    if (!isSoldier(member) && !isOwner(member)) return;
    const target = message.mentions.members?.first();
    if (!target) return message.channel.send('اكتب: `/شيل الشخص:@منشن`');
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    warnings[target.id] = [];
    return message.channel.send(`✅ تم إزالة جميع تحذيرات <@${target.id}>.`);
  }

  // ===== -تحذيرات =====
  if (content.startsWith('-تحذيرات')) {
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    const target = message.mentions.members?.first();
    if (target) {
      const w = warnings[target.id];
      if (!w || w.length === 0) return message.channel.send(`✅ لا يوجد تحذيرات لـ <@${target.id}>.`);
      let txt = `📋 **تحذيرات <@${target.id}>:**\n`;
      w.forEach((x, i) => { txt += `${i+1}. بواسطة <@${x.by}> — **${x.reason}**\n`; });
      return message.channel.send(txt);
    } else {
      const all = [];
      for (const [uid, wList] of Object.entries(warnings)) for (const w of wList) all.push({ uid, ...w });
      all.sort((a, b) => b.timestamp - a.timestamp);
      const last10 = all.slice(0, 10);
      if (last10.length === 0) return message.channel.send('لا يوجد تحذيرات.');
      let txt = '📋 **آخر 10 تحذيرات:**\n';
      last10.forEach((w, i) => { txt += `${i+1}. <@${w.uid}> حذّره <@${w.by}> — **${w.reason}**\n`; });
      return message.channel.send(txt);
    }
  }

  // ===== /هويه =====
  if (content.startsWith('/هويه')) {
    if (!isSoldier(member) && !isOwner(member)) return;
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    const target = message.mentions.members?.first();
    if (!target) return message.channel.send('اكتب: `/هويه الشخص:@منشن`');
    const id = identities[target.id];
    if (!id) return message.channel.send(`❌ لا توجد هوية لـ <@${target.id}>.`);
    return message.channel.send(
      `🪪 **هوية <@${target.id}>:**\n` +
      `الاسم: **${id.name}**\n` +
      `رقم الجوال المزيف: **${id.phone}**\n` +
      `الجنس: **${id.gender === 'male' ? 'ولد 👦' : 'بنت 👧'}**`
    );
  }

  // ===== /حذف هويه =====
  if (content.startsWith('/حذف هويه')) {
    if (!isOwner(member)) return;
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    const target = message.mentions.members?.first();
    if (!target) return message.channel.send('اكتب: `/حذف هويه @منشن`');
    delete identities[target.id];
    const toRemove = target.roles.cache.filter(r => r.id !== guild.roles.everyone.id);
    await target.roles.remove(toRemove).catch(() => {});
    await target.roles.add(ROLES.VISITOR).catch(() => {});
    return message.channel.send(`✅ تم حذف هوية <@${target.id}> وإعادته زائر.`);
  }

  // ===== -شنطه =====
  if (content === '-شنطه') {
    const bag = getBag(message.author.id);
    const items = bag.items.length > 0 ? bag.items.join('، ') : 'فارغة';
    return message.channel.send(
      `🎒 **شنطة <@${message.author.id}>:**\n\n` +
      `🟠 الجوع:  ${makeBar(bag.hunger)} ${bag.hunger}%\n` +
      `🔵 العطش: ${makeBar(bag.thirst)} ${bag.thirst}%\n\n` +
      `📦 **المحتويات:** ${items}\n\n` +
      `اكتب اسم الأكلة لأكلها، أو اكتب اسمها + منشن شخص لإعطائه إياها.`
    );
  }

  // ===== /منيو =====
  if (content === '/منيو') {
    let txt = '🛒 **المنيو:**\n\n';
    MENU.forEach(item => {
      txt += `**${item.name}**`;
      if (item.hunger > 0) txt += ` — 🍔 جوع +${item.hunger}`;
      if (item.thirst > 0) txt += ` — 💧 عطش +${item.thirst}`;
      txt += '\n';
    });
    return message.channel.send(txt);
  }

  // ===== /بيع =====
  if (content.startsWith('/بيع')) {
    if (!isSeller(member)) return;
    const target      = message.mentions.members?.first();
    const itemMatch   = content.match(/الغرض[:\s]+(\S+)/);
    const itemName    = itemMatch ? itemMatch[1] : null;
    const menuItem    = MENU.find(i => i.name === itemName);
    if (!target || !menuItem) return message.channel.send(`اكتب: \`/بيع الغرض:اسم الشخص:@منشن\`\nالأغراض: ${MENU.map(i=>i.name).join('، ')}`);
    await message.channel.send(`${EMOJI_LOADING} جاري التحميل...`);
    getBag(target.id).items.push(menuItem.name);
    return message.channel.send(`✅ تم بيع **${menuItem.name}** لـ <@${target.id}>!`);
  }

  // ===== /فول =====
  if (content.startsWith('/فول')) {
    if (!isOwner(member)) return;
    const target = message.mentions.members?.first();
    if (!target) return message.channel.send('اكتب: `/فول @منشن`');
    const bag = getBag(target.id);
    bag.hunger = 100;
    bag.thirst = 100;
    return message.channel.send(`✅ تم ملء بار <@${target.id}> بالكامل!`);
  }

  // ===== أكل من الشنطة أو إعطاء شخص =====
  const bagItem = MENU.find(i => content === i.name || content.startsWith(i.name + ' '));
  if (bagItem) {
    const bag    = getBag(message.author.id);
    const target = message.mentions.members?.first();
    if (!bag.items.includes(bagItem.name)) return message.channel.send(`❌ ما عندك **${bagItem.name}** في شنطتك!`);
    if (target) {
      const row = new ActionRowBuilder().addComponents(
        new ButtonBuilder().setCustomId(`give_item_${bagItem.name}_${message.author.id}_${target.id}`).setLabel('نعم ✅').setStyle(ButtonStyle.Success),
        new ButtonBuilder().setCustomId('cancel_give').setLabel('لا ❌').setStyle(ButtonStyle.Danger),
      );
      return message.channel.send({ content: `هل تريد إعطاء **${bagItem.name}** لـ <@${target.id}>؟`, components: [row] });
    } else {
      bag.items  = bag.items.filter(i => i !== bagItem.name);
      bag.hunger = cap(bag.hunger + bagItem.hunger);
      bag.thirst = cap(bag.thirst + bagItem.thirst);
      return message.channel.send(`✅ أكلت **${bagItem.name}**!\n🟠 الجوع: ${bag.hunger}% | 🔵 العطش: ${bag.thirst}%`);
    }
  }
});

// ========== محادثة الهوية في الخاص ==========
async function startIdentityConversation(user, guild) {
  try {
    pendingIdentity[user.id] = { step: 'start', guild };
    await user.send('مرحباً بك في سيرفر رولباك! 🎮\n\nهل تريد إنشاء هويتك في السيرفر للمزح واللعب فقط؟\n\nاكتب **نعم** أو **لا**');
  } catch { console.log('ما قدر يرسل خاص لـ', user.tag); }
}

async function handleIdentityDM(message) {
  const userId  = message.author.id;
  const state   = pendingIdentity[userId];
  const content = message.content.trim();

  if (content === 'إلغاء' || content === 'الغاء') {
    delete pendingIdentity[userId];
    return message.author.send('✅ تم إلغاء العملية.');
  }

  if (state.step === 'start') {
    if (content === 'نعم') {
      state.step = 'enter_name';
      return message.author.send('حسناً! اكتب اسمك المزيف أو الحقيقي، مثال: **ابو احمد**\n\n(اكتب **إلغاء** للإلغاء)');
    } else {
      delete pendingIdentity[userId];
      return message.author.send('حسناً، يمكنك إنشاء هويتك لاحقاً من خلال الدعم.');
    }
  }

  if (state.step === 'enter_name') {
    state.name = content;
    state.step = 'ask_phone';
    return message.author.send(`تمام **${content}**! 👍\n\nهل تريد صنع رقم جوال مزيف للسيرفر؟ (100% مزيف للمزح فقط)\n\nاكتب **نعم** أو **لا**`);
  }

  if (state.step === 'ask_phone') {
    if (content === 'نعم') {
      state.step = 'enter_phone';
      return message.author.send('اكتب رقمك المزيف، يجب أن يكون 8 أرقام ويبدأ بـ **17**\nمثال: **17123456**');
    } else {
      state.phone = 'غير مسجل';
      state.step  = 'ask_gender';
      return message.author.send('ما جنسك؟ اكتب **ولد** أو **بنت**');
    }
  }

  if (state.step === 'enter_phone') {
    if (!/^17\d{6}$/.test(content)) {
      return message.author.send('❌ الرقم غلط! لازم 8 أرقام يبدأ بـ 17\nمثال: **17123456**\n\n(اكتب **إلغاء** للإلغاء)');
    }
    const dup = Object.entries(identities).find(([id, d]) => d.phone === content && id !== userId);
    if (dup) return message.author.send('❌ هذا الرقم مستخدم عند شخص آخر! اختر رقماً مختلفاً.');
    state.phone = content;
    state.step  = 'ask_gender';
    return message.author.send(`✅ تم تسجيل الرقم: **${content}**\n\nما جنسك؟ اكتب **ولد** أو **بنت**`);
  }

  if (state.step === 'ask_gender') {
    if (content !== 'ولد' && content !== 'بنت') return message.author.send('اكتب **ولد** أو **بنت** فقط.');
    const gender = content === 'ولد' ? 'male' : 'female';
    identities[userId] = { name: state.name, phone: state.phone, gender };

    try {
      const gm = await state.guild.members.fetch(userId);
      await gm.roles.remove(ROLES.VISITOR).catch(() => {});
      await gm.roles.add(ROLES.CITIZEN).catch(() => {});
      await gm.roles.add(gender === 'male' ? ROLES.MALE : ROLES.FEMALE).catch(() => {});
    } catch {}

    delete pendingIdentity[userId];
    return message.author.send(
      `🎉 **أهلاً وسهلاً ${state.name}!**\n\n` +
      `تم إنشاء هويتك بنجاح ✅\n` +
      `الاسم: **${state.name}**\n` +
      `الرقم: **${state.phone}**\n` +
      `الجنس: **${content}**\n\n` +
      `مرحباً بك في سيرفر رولباك! 🎮`
    );
  }
}

// ========== تشغيل البوت ==========
const token = process.env.DISCORD_TOKEN;
if (!token) {
  console.error('❌ ما لقيت DISCORD_TOKEN! أضفه في Environment Variables في Render.');
  process.exit(1);
}
client.login(token).catch(err => {
  console.error('❌ خطأ في تسجيل الدخول:', err.message);
  process.exit(1);
});
