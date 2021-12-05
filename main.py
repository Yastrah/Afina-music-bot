import discord
from discord.ext import commands
from music import Player
import json

PREFIX = '.'
client = commands.Bot(command_prefix=PREFIX, intents=discord.Intents.all())
client.remove_command('help')


@client.event
async def on_ready():  # вызывается при подключении
    print(f'We have logged in as {client.user}')
    await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name=f'{PREFIX}help'))  # статус бота

    file = open('Db.json', 'r')  # получение данных из Bd->
    data = json.loads(file.read())
    file.close()

    for guild in client.guilds:
        if not str(guild.id) in list(data):
            data[str(guild.id)] = {'queue': [], 'repeat': False, 'playlists': {}, 'vote_to_skip': False,
                                   'delete_ban_words': [False, []]}
            file = open('Db.json', 'w')
            json.dump(data, file)
            file.close()


@client.event
async def on_member_join(member):  # вызывается при первом появлении пользователя на серввере
    channel = discord.utils.get(member.guild.text_channels)
    await channel.send(f'Добро пожаловать {member.mention}. Напишите **.help**, чтобы узнать больше.')

@client.event
async def on_guild_join(guild):  # вызывается при присоединении бота к серверу
    print('setup')
    file = open('Db.json', 'r')  # получение данных из Bd->
    data = file.read()
    if data != '' and data != '{}':
        data = json.loads(data)
    else:
        data = {}
    file.close()

    file = open('Db.json', 'w')
    data[str(guild.id)] = {'queue': [], 'repeat': False, 'playlists': {}, 'vote_to_skip': False,
                      'delete_ban_words': [False, []]}
    json.dump(data, file)
    file.close()

    for role in guild.roles:
        if role.name == 'muted':
            return
    return await guild.create_role(name="muted", color=0x9F0E0E)

@client.event
async def on_guild_remove(guild):  # вызывается если бота кикнули\забанили на сервере
    print('del up')
    file = open('Db.json', 'r')  # получение данных из Bd->
    data = json.loads(file.read())
    file.close()
    del data[str(guild.id)]
    file = open('Db.json', 'w')
    json.dump(data, file)
    file.close()

@client.event
async def on_message(message):  # вызывается, когда кто-нибудь пишет в чат
    await client.process_commands(message)  # !!!!!!разрешение использовать команды после вызова on_message()

    if message.author == client.user or message.content.startswith('.set'):
        return

    file = open('Db.json', 'r')  # получение данных из Bd->
    data = json.loads(file.read())
    file.close()
    settings = data[str(message.guild.id)]  # settings содержит все настройки для этого сервера

    if settings['delete_ban_words'][0] and message.author != client.user:
        msg = message.content.lower()  # сообщение в нижнем регистре
        ban_words = settings['delete_ban_words'][1]

        for word in msg.split():  # удаление запрещённых слов
            if word in ban_words:
                await message.delete()  # удалить сообщение
                print('delete_message')
                return

#--------------------------команды--------------------------#

@client.command(aliases=['settings', 'set'])
@commands.has_permissions(administrator=True)
async def setting(ctx, *, value=None):  # изменение параметров delete_ban_words
    try:
        await ctx.message.delete()  # удаление команды
    finally:
        file = open('Db.json', 'r')  # получение данных из Bd->
        data = json.loads(file.read())
        file.close()
        settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

        if value is None:  # отображение настроек если параметры не заданы
            embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
            embed.add_field(name=f'``banwords``', value='on' if settings['delete_ban_words'][0] else 'off')
            embed.add_field(name=f'``voteskip``', value='on' if settings['vote_to_skip'] else 'off')
            embed.add_field(name=f'``playlists``', value=len(settings['playlists']))
            embed.set_footer(text=f'Вы можете изменить настройки командой:\n {PREFIX}setting <настройка> <параметр> <значение>')
            return await ctx.send(embed=embed)


        value = value.lower().split()
        # ------------------------------------------------------------------------------------------------------------------#
        if value[0] in ['banwords', 'bw']:  # параметр banwords

            if len(value) == 1:
                embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
                embed.add_field(name='banwords',
                                value=f'''Если **on**, все сообщения, содержащие запрещённые слова, будут автоматически удаляться.\n
                                      Чтобы изменить параметр добавьте __on\off__.\n
                                      Список запретных слов можно просмотреть или изменить командой:\n 
                                      ``{PREFIX}settings banwords list <слова через запятую или пробел>``''')
                return await ctx.send(embed=embed)

            if value[1] == 'on':
                settings['delete_ban_words'][0] = True

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                embed = discord.Embed(title='Настройки сервера', description='Параметр **banwords** успешно изменён на **on**',
                                      color=discord.Color.green())  # embed нормально не работает с mention
                return await ctx.send(embed=embed)

            if value[1] == 'off':
                settings['delete_ban_words'][0] = False

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                embed = discord.Embed(title='Настройки сервера', description='Параметр **banwords** успешно изменён на **off**',
                                      color=discord.Color.red())  # embed нормально не работает с mention
                return await ctx.send(embed=embed)

            if value[1] in ['list', 'l']:

                if len(value) == 2:
                    embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
                    embed.add_field(name='banwords list', value=', '.join(settings['delete_ban_words'][1]))
                    return await ctx.send(embed=embed)

                if value[2] in ['clear', 'none', 'cl']:
                    settings['delete_ban_words'][1] = []

                    data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                    file = open('Db.json', 'w')
                    json.dump(data, file)
                    file.close()

                    embed = discord.Embed(title='Настройки сервера', color=discord.Color.green(),
                                          description='Список **banwords list** успешно **очищен**')
                    return await ctx.send(embed=embed)


                settings['delete_ban_words'][1] = ' '.join(value[2:len(value)]).split(',') if ',' in value[2:len(value)] else ' '.join(value[2:len(value)]).split()

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                embed = discord.Embed(description='Список **banwords** успешно перезаписан!', color=discord.Color.green())
                return await ctx.send(embed=embed)

            return await ctx.send(rf'После **banwords** должен идти параметр **__on\off__** или **__list__!**')

        #------------------------------------------------------------------------------------------------------------------#
        if value[0] in ['voteskip', 'v', 'vote']:  # параметр vote_to_skip

            if len(value) == 1:
                embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
                embed.add_field(name='voteskip',
                                value=f'''Если **on**, то команда **skip** будет создавать голосование на 15 сек, трек будет пропущен только, если 50% или больше выберут __пропустить__.\n
                                      Чтобы изменить параметр добавьте __on\off__.  ''')
                return await ctx.send(embed=embed)

            if value[1] == 'on':
                settings['vote_to_skip'] = True

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                embed = discord.Embed(title='Настройки сервера',
                                      description='Параметр **voteskip** успешно изменён на **on**',
                                      color=discord.Color.green())  # embed нормально не работает с mention
                return await ctx.send(embed=embed)

            if value[1] == 'off':
                settings['vote_to_skip'] = False

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                embed = discord.Embed(title='Настройки сервера',
                                      description='Параметр **voteskip** успешно изменён на **off**',
                                      color=discord.Color.red())  # embed нормально не работает с mention
                return await ctx.send(embed=embed)


            return await ctx.send(rf'**После voteskip должен идти параметр __on\off__!**')

        #------------------------------------------------------------------------------------------------------------------#
        if value[0] in ['list', 'playlist', 'l', 'pl']:  # параметр playlists
            embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
            embed.add_field(name='playlists',
                            value=f'''Сохраненные плейлисты. Плейлист можно проиграть командой: ``{PREFIX}play list <имя>``\n
                            Просмотреть сохраненные плейлисты можно командой: ``{PREFIX}lists``\n
                            Создать новый плейлист можно командой: ``{PREFIX}lists create <имя> queue(тогда добавятся треки из очереди)\<url1 url2 url3>``''')
            return await ctx.send(embed=embed)


        return await ctx.send(rf'**Такого параметра __settings__ не существует!**')

@client.command()
async def help(ctx, type=None):  # помощь по командам и боту->
    try:
        await ctx.message.delete()  # удаление команды
    finally:
        if type is None:
            embed = discord.Embed(color=0x500ac2, title='Athena',
                                  description='**Athena** - это многофункциональный бот, сделанный ***Yastrah*** и предназначенный в основном для __прослушивания музыки__.\n\n'
                                              'У бота есть множество **расширенных возможностей** для вашего удобства, например: '
                                              'возможность решать, пропустить трек или нет, с помощью __голосования__, '
                                              'создавать __свои плейлисты__ и проигрывать их одной командой, включить __повторение__ текущей очереди.\n\n'
                                              'Также Athena поможет вам и в **модерации сервера!** '
                                              'Вы можете включить и настроить функцию __удаления сообщений с запрещёнными словами__, '
                                              'использовать команды __kick__ и __ban__.\n\n'
                                              'Athena сможет как развлечь пользователей, так и помочь админам.')
            embed.add_field(name='Плеер', value=f'`{PREFIX}help player`', inline=False)
            embed.add_field(name='Модерация', value=f'`{PREFIX}help moder`', inline=False)
            embed.add_field(name='Развлечения', value=f'`{PREFIX}help fun`', inline=False)
            return await ctx.send(embed=embed)


        if type.lower() in ['player', 'play', 'music']:  # команды плеера
            embed = discord.Embed(color=0x500ac2, title='Команды для плеера:', description='Команды для взаимодействия с музыкой, плейлистами и т.д.')
            embed.add_field(name=f'`{PREFIX}play (p)`', value='Начинает проигрывание.\n Параметры: **<url с YouTube>**(бот проиграет трек по ссылке), '
                                                              '**<имя трека\видео>**(бот найдёт наиболее подходящий по названию трек), '
                                                              '**list <имя плейлиста>**(в очередь будут добавлены треки из этого плейлиста)', inline=False)
            embed.add_field(name=f'`{PREFIX}stop (st)`', value='__Очищает очередь__. Бот покидает голосовой канал(отключается).', inline=False)
            embed.add_field(name=f'`{PREFIX}queue (q)`', value='Отображает текущую __очередь__.', inline=False)
            embed.add_field(name=f'`{PREFIX}skip (s)`', value='__Пропуск__ текущего трека(можно настроить на голосование параметром settings **voteskip**).', inline=False)
            embed.add_field(name=f'`{PREFIX}repeat (rep)`', value='Очередь будет __повторяться__. '
                                                                  'После отключения от голосового канала функция автоматически отключается.', inline=False)
            embed.add_field(name=f'`{PREFIX}unrepeat (unrep)`', value='Если *repeat* включено, то вручную __отключает повторение__.', inline=False)
            embed.add_field(name=f'`{PREFIX}pause`', value='Ставит проигрыватель на паузу. После **10** минут бездействия __бот покидает канал и очищает очередь__.', inline=False)
            embed.add_field(name=f'`{PREFIX}resume`', value='Снимает проигрыватель с паузы.', inline=False)
            embed.add_field(name=f'`{PREFIX}search (find)`', value='По названию ищет песни(5 наиболее подходящих вариантов). '
                                                                   'Чтобы сразу добавить в очередь в течение **25 секунд** отправить чило **от 1 до 5**.', inline=False)
            embed.add_field(name=f'`{PREFIX}playlists (pl)`', value='Взаимодействие с плейлистами.\n'
                                                                    'Параметры: **create**(создаёт плейлист), **add**(добавляет треки в существующий плейлист), '
                                                                    '**delete**(удаляет плейлист).\n Чтобы просмотреть плейлисте используйте `.playlists`\n'
                                                                    'Чтобы проиграть плейлист используйте команду: `.play list <имя плейлиста>`', inline=False)
            return await ctx.send(embed=embed)


        if type.lower() in ['moder', 'moderation', 'mod']:  # команды модерации
            embed = discord.Embed(color=0x500ac2, title='Команды для модерации:', description='Команды для настрйки бота и помощи в модерации сервера.')
            embed.add_field(name=f'`{PREFIX}settings (set)`', value='***Настройки сервера***. Без параметров можно просмотреть __текущие настройки__. '
                                                                    'Параметры: **banwords**(настройки автоматического удаления сообщений с запрещёнными словами), '
                                                                    '**voteskip**(голосования для пропуска трека), **playlists**(кол-во сохраненных плейлистов).', inline=False)
            embed.add_field(name=f'`{PREFIX}clear (cl)`', value='Удаляет заданное число сообщений в чате (если не указано число, то 1). **Только для админов.**', inline=False)
            embed.add_field(name=f'`{PREFIX}kick`', value='Выгоняет указанного через **@** пользователя. Нужно иметь достаточные **права**!', inline=False)
            embed.add_field(name=f'`{PREFIX}ban`', value='Банит указанного через **@** пользователя. Нужно иметь достаточные **права**!', inline=False)

            return await ctx.send(embed=embed)


        if type.lower() in ['fun', 'funny', 'games']:  # команды для развлечений
            embed = discord.Embed(color=0x500ac2, title='Команды для развлечений:', description='Команды для мини-игр и других развлечений.')
            embed.add_field(name=f'`{PREFIX}tell`', value='Бот отправляет сообщение с вашим текстом: `.tell <текст>`', inline=False)

            return await ctx.send(embed=embed)


@client.command()
async def tell(ctx, *, text):  # повторение текста с упоминанием автора->
    try:
        await ctx.message.delete()  # удаление команды
    finally:
        embed = discord.Embed(color=0xff9900, description=text)  # embed нормально не работает с mention
        embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)  # размещаю сверху ник и аватар автора
        await ctx.send(embed=embed)

@client.command(aliases=['cl'])
@commands.has_permissions(manage_messages=True)  # использовать эту команду могут только те, у кого есть права администратора
async def clear(ctx, amount=None):  # очистить чат на х сообщений(по умолчанию 1) только администратор, amoumnt - сколько сообщений удалиться по умолчанию
    if amount is None or amount.isdigit():
        if amount is None:
            amount = 1
        try:
            await ctx.channel.purge(limit=int(amount)+1)
            return await ctx.send(f'*Удалено **{amount}** сообщений!*')
        except PermissionError:
            return await ctx.send(f'*❌ Ошибка, возможно вы ограничили права боту!*')
    else:
        return await ctx.send(f'*❌ Вы ввели недопустимое количество!*')

@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):  # кикнуть конкретного пользователя только администратор->
    try:
        await ctx.message.delete()  # удаление команды
    finally:
        if member == ctx.author:  # защита от дурака
            await ctx.send('Нельзя выгнать себя')
        else:
            try:
                await member.kick()
                if reason != None:
                    await ctx.send(f'{ctx.author} выгнал пользователя {member.mention} по причине: "{reason}"')
                else:
                    await ctx.send(f'{ctx.author} выгнал пользователя {member.mention}')
            except PermissionError:
                return await ctx.send(f'*❌ Ошибка, возможно вы ограничили права боту!*')

@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason='"не указана"'):  # забанить конкретного пользователя только администратор->
    try:
        await ctx.message.delete()  # удаление команды
    finally:
        if member == ctx.author:  # защита от дурака
            await ctx.send('Нельзя забанить себя')
        else:
            try:
                await member.ban(reason=reason)

                embed = discord.Embed(color=0x990000, title='Has banned', description='По причине: {}'.format(reason))  # embed нормально не работает с mention
                embed.set_author(name=str(member), icon_url=member.avatar_url)  # размещаю сверху ник и аватар пользователя, которого кикнули
                embed.set_footer(text='Забанен админом {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
                await ctx.send(embed=embed)
            except PermissionError:
                return await ctx.send(f'*❌ Ошибка, возможно вы ограничили права боту!*')


# запуск
client.add_cog(Player(client))

TOKEN = open('token-file.txt', 'r').readline()
client.run(TOKEN)