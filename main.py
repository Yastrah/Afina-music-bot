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


@client.event
async def on_member_join(member):  # вызывается при первом появлении пользователя на серввере
    channel = discord.utils.get(member.guild.text_channels)
    await channel.send(f'Добро пожаловать **{member}**. Напишите **.help**, чтобы узнать больше.')


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
    data[guild.id] = {'queue': [], 'repeat': False, 'playlists': {}, 'vote_to_skip': False,
                      'delete_ban_words': [False, []], 'language': 'ru'}
    # queue - текущая очередь(url) | repeat - повторять или нет текущую очередь | playlists - словарь плейлистов в формате:
    # {'имя плейлиста': ['url1', 'url2']} | vote_to_skip - будеьт ли голосование при пропуске песни
    # delete_ban_words - удалять ban-слова [да\нет, [список ban-слов]] | language - язык бота для сервера(ru)
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

    if message.author == client.user or message.content.startswith('.'):  # не бот и не команда
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
    await ctx.message.delete()  # удаление команды

    file = open('Db.json', 'r')  # получение данных из Bd->
    data = json.loads(file.read())
    file.close()
    settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

    if value is None:  # отображение настроек если параметры не заданы
        embed = discord.Embed(title='Настройки сервера', color=discord.Color.darker_gray())
        embed.add_field(name=f'``language``', value=settings['language'])
        embed.add_field(name=f'``banwords``', value='on' if settings['delete_ban_words'][0] else 'off')
        embed.add_field(name=f'``voteskip``', value='on' if settings['vote_to_skip'] else 'off')
        embed.add_field(name=f'``playlists``', value=len(settings['playlists']))
        embed.set_footer(text=f'Вы можете изменить настройки командой:\n {PREFIX}setting «настройка» «параметр» «значение»')
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
                                  {PREFIX}settings banwords list «слова через , или пробел»''')
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
                        value=f'''Сохраненные плейлисты. Плейлист можно проиграть командой: **{PREFIX}play list «имя»**\n
                        Просмотреть сохраненные плейлисты можно командой: **{PREFIX}lists**\n
                        Создать новый плейлист можно командой: **{PREFIX}lists create**''')
        return await ctx.send(embed=embed)

    # ------------------------------------------------------------------------------------------------------------------#
    if value[0] in ['language', 'languages']:  # параметр playlists
        return await ctx.send('*К сожаление на данный момент доступен только **один** язык.*')

    return await ctx.send(rf'**Такого параметра __settings__ не существует!**')


@client.command()
async def help(ctx, type=None):  # помощь по командам и боту->
    await ctx.message.delete()  # удаление команды

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
        embed.add_field(name='Команды', value=f'{PREFIX}help commands')
        # embed.add_field(name='Плеер', value=f'{PREFIX}help player')
        return await ctx.send(embed=embed)

    if type.lower() in ['commands', 'command', 'com']:
        embed = discord.Embed(color=0x500ac2, title='Команды', description='предисловие', inline=False)
        embed.add_field(name=f'``{PREFIX}play (p)``', value='Начинает проигрывание. Можно добавить __url__ с Ютуба, '
                                                            '__название__(бот сам найдет наиболее подходящий трек) или '
                                                            'название ранее добавленного __плейлиста__.', inline=False)
        embed.add_field(name=f'``{PREFIX}stop (st)``', value='__Очищает очередь__. Бот покидает голосовой канал(отключается).', inline=False)
        embed.add_field(name=f'``{PREFIX}queue (q)``', value='Отображает текущую __очередь__.', inline=False)
        embed.add_field(name=f'``{PREFIX}skip (s)``', value='__Пропуск__ текущего трека(можно настроить на голосование параметром settings **voteskip**).', inline=False)
        embed.add_field(name=f'``{PREFIX}repeat (rep)``', value='Очередь будет __повторяться__. '
                                                                'После отключения от голосового канала функция автоматически отключается.', inline=False)
        embed.add_field(name=f'``{PREFIX}unrepeat (unrep)``', value='Если *repeat* включено, то вручную __отключает повторение__.', inline=False)
        embed.add_field(name=f'``{PREFIX}pause``', value='Ставит проигрыватель на паузу. После **10** минут бездействия __бот покидает канал и очищает очередь__.', inline=False)
        embed.add_field(name=f'``{PREFIX}resume``', value='Снимает проигрыватель с паузы.', inline=False)
        embed.add_field(name=f'``{PREFIX}search (find)``', value='По названию ищет песни(5 наиболее подходящих вариантов)', inline=False)
        embed.add_field(name=f'``{PREFIX}playlists (pl)``', value='Взаимодействие с плейлистами. '
                                                                  'Параметры: create(создаёт плейлист), add(добавляет треки в существующий плейлист), '
                                                                  'delete(удаляет плейлист). Чтобы просмотреть плейлисте используйте **.playlists**', inline=False)

        embed.add_field(name=f'``{PREFIX}settings (set)``', value='__Настройки сервера__. Без параметров можно просмотреть __текущие настройки__. '
                                                            'Параметры: language(текущий язык сервера), '
                                                            'banwords(настройки автоматического удаления сообщений с запрещёнными словами), '
                                                            'voteskip(голосования для пропуска трека), playlists(кол-во сохраненных плейлистов).', inline=False)
        embed.add_field(name=f'``{PREFIX}clear (cl)``', value='Удаляет заданное число сообщений в чате (если не указано число, то 1). **Только для админов.**', inline=False)
        embed.add_field(name=f'``{PREFIX}kick``', value='Выгоняет указанного через @ пользователя. Нужно иметь достаточные права.', inline=False)
        embed.add_field(name=f'``{PREFIX}ban``', value='Банит указанного через @ пользователя. Нужно иметь достаточные права.', inline=False)

        return await ctx.send(embed=embed)

    if type.lower() in ['player', 'play', 'music']:
        embed = discord.Embed(color=0x500ac2, title='Список команд:', description='предисловие')
        embed.add_field(name=f'``{PREFIX}ban``', value='описание команды kick')
        embed.add_field(name=f'``{PREFIX}ban``', value='описание команды ban')
        return await ctx.send(embed=embed)


@client.command()
async def tell(ctx, *, text):  # повторение текста с упоминанием автора->
    await ctx.message.delete()  # удаление команды

    embed = discord.Embed(color=0xff9900, description=text)  # embed нормально не работает с mention
    embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)  # размещаю сверху ник и аватар автора
    await ctx.send(embed=embed)


@client.command(aliases=['cl'])
@commands.has_permissions(manage_messages=True)  # использовать эту команду могут только те, у кого есть права администратора
async def clear(ctx, amount=1):  # очистить чат на х сообщений(по умолчанию 1) только администратор, amoumnt - сколько сообщений удалиться по умолчанию
    await ctx.channel.purge(limit=amount+1)


@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):  # кикнуть конкретного пользователя только администратор->
    await ctx.message.delete()  # удаление команды

    if member == ctx.author:  # защита от дурака
        await ctx.send('Нельзя выгнать себя')
    else:
        await member.kick()
        if reason != None:
            await ctx.send(f'{ctx.author} выгнал пользователя {member.mention} по причине: "{reason}"')
        else:
            await ctx.send(f'{ctx.author} выгнал пользователя {member.mention}')


@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason='"не указана"'):  # забанить конкретного пользователя только администратор->
    await ctx.message.delete()  # удаление команды

    if member == ctx.author:  # защита от дурака
        await ctx.send('Нельзя забанить себя')
    else:
        await member.ban(reason=reason)

        embed = discord.Embed(color=0x990000, title='Has banned', description='По причине: {}'.format(reason))  # embed нормально не работает с mention
        embed.set_author(name=str(member), icon_url=member.avatar_url)  # размещаю сверху ник и аватар пользователя, которого кикнули
        embed.set_footer(text='Забанен админом {}'.format(ctx.author.name), icon_url=ctx.author.avatar_url)
        await ctx.send(embed=embed)


@client.command()
async def secret_setup(ctx):
    print('setup-command')
    data = {}
    file = open('Db.json', 'w')
    for guild in client.guilds:
        data[guild.id] = {'queue': [], 'repeat': False, 'playlists': {}, 'vote_to_skip': False,
                          'delete_ban_words': [False, []], 'language': 'ru'}
        # queue_url - текущая очередь(url) | queue_title - текущая очередь(name) | playlists - словарь плейлистов в формате:
        # {'имя плейлиста': ['url1', 'url2']} | vote_to_skip - будеьт ли голосование при пропуске песни
        # delete_ban_words - удалять ban-слова [да\нет, [список ban-слов]] | language - язык бота для сервера(ru или en)

    # print(data)
    json.dump(data, file)
    file.close()


# запуск
client.add_cog(Player(client))

TOKEN = open('token-file.txt', 'r').readline()
client.run(TOKEN)


# ctx.message.guild - сервер если None то личка
# @commands.has_role("admin") - только для роли "admin"
# await ctx.channel.purge(limit=1)  # удаление последнего сообщения
# await ctx.message.delete()  # удаление команды
# len(ctx.voice_client.channel.members) кол-во пользователей в канале
# ctx.message.guild.roles  # все роли сервера
# await ctx.send(f"This command is on cooldown, try again after {round(error.retry_after)} seconds.", delete_after=5)

# poll = await ctx.send(embed=embed)
# poll.id  # id сообщения
# await poll.clear_reactions()  # очистить реакции
# await poll.edit(embed=embed)  # редактировать сообщение
# await poll.delete()  # удалить конкретное сообщение

# ▶⏸⏹⏩🔁❌❗✔

# file = open('Db.json', 'r')  # получение данных из Bd->
# data = json.loads(file.read())
# file.close()
# settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

# data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
# file = open('Db.json', 'w')
# json.dump(data, file)
# file.close()


# async def on_message(message):
#     prefix = ...  # Здесь ты получаешь префикс бота на сервере
#     bot.command_prefix = prefix
#     await bot.process_commands(message)


#Bot_user = discord.Client()
#Данные:
# helloWords = ['hi', 'hello', 'q', 'ку', 'привет', 'здарова']
# answerWords = ['информация', 'команды', 'что здесь делать', 'команды бота']
# goodbyeWords = ['by', 'пока', 'всем пока', 'удачи']
#события:
# @client.event   #bkb это или команды
# async def on_message(message):
#     msg = message.content.lower()#lower() - нижний регистр
#
#     if msg in helloWords:
#         await message.channel.send(f'Приветствую и тебя {message.author.mention}')
#
#     if msg in answerWords:
#         await message.channel.send('Пропиши в чат команду -help')
#
#     if msg in goodbyeWords:
#         await message.channel.send('Пока, удачи тебе!')
# import discord
# from discord.ext import commands
# TOKEN = 'ODkyMTU2ODIxNjM1MjA3MjI5.YVIzyQ.3xgtE34O_zTMpyP9Ei9Ti6tB3ME'
#
# bot = commands.Bot(command_prefix='-')
#
# @bot.command() #разрешаем передавать агрументы
# async def test(canal): #создаем асинхронную фунцию бота
#     await canal.send('hi!') #отправляем обратно аргумент
#
# async def translate(canal):
#     await canal.
# bot.run(TOKEN)



# import discord
#
# client = discord.Client()
#
# @client.event
# async def on_ready():
#     print('We have logged in as {0.user}'.format(client))
#
# @client.event
# async def on_message(message):
#     if message.author == client.user:
#         return
#
#     if message.content.startswith('-test'):
#         await message.channel.send(f'{message.author.mention} Hello!')
#
# client.run('token')





#------------------------работа с голосовыми каналами---------------------------------------#

# #присоединение к голосовому каналу->
# @client.command()
# async def join(ctx):
#     await ctx.channel.purge(limit=1)#удаление команды
#
#     if ctx.author.voice is None:
#         await ctx.send('Вы не подключены к голосовому каналу')
#     else:
#         channel = ctx.author.voice.channel
#         voice = get(client.voice_clients, guild=ctx.guild )
#
#         if voice and voice.is_connected():
#             await voice.move_to(channel)
#         else:
#             voice = await channel.connect()
# #остальное доделать->
#
# #отключение от голосового канала->
# @client.command()
# async def leave(ctx):
#     await ctx.channel.purge(limit=1)#удаление команды
#
#     # voice = get(client.voice_clients, guild=ctx.guild )
#     #
#     # if voice and voice.is_connected():
#     #     await voice.disconnect()
#
#
# #play->
# # @client.command()
# # async def play(ctx, url: str):
# #     await ctx.channel.purge(limit=1)#удаление команды
# #     #подключение к голосовому каналу->
# #     channel = ctx.author.voice.channel
# #     voice = get(client.voice_clients, guild=ctx.guild )
# #     if voice and voice.is_connected():
# #         await voice.move_to(channel)
# #     else:
# #         if not voice.is_connected():
# #             voice = await channel.connect()
#
#
#
#
#
#
# # @client.command(pass_context=True, brief="This will play a song 'play [url]'", aliases=['pl'])
# # async def play(ctx, url: str):
# #     await ctx.channel.purge(limit=1)  # удаление команды
# #
# #     if ctx.author.voice is None:
# #         await ctx.send('Вы не подключены к голосовому каналу')
# #     else:
# #         channel = ctx.author.voice.channel
# #         voice = get(client.voice_clients, guild=ctx.guild)
# #
# #         if voice and voice.is_connected():
# #             await voice.move_to(channel)
# #         else:
# #             voice = await channel.connect()
# #
# #
# #
# #
# #     song_there = os.path.isfile("song.mp3")
# #     try:
# #         if song_there:
# #             os.remove("song.mp3")
# #     except PermissionError:
# #         await ctx.send("Wait for the current playing music end or use the 'stop' command")
# #         return
# #     await ctx.send("Getting everything ready, playing audio soon")
# #     print("Someone wants to play music let me get that ready for them...")
#     # #voice = get(client.voice_clients, guild=ctx.guild)
#     # ydl_opts = {
#     #     'format': 'bestaudio/best',
#     #     'postprocessors': [{
#     #         'key': 'FFmpegExtractAudio',
#     #         'preferredcodec': 'mp3',
#     #         'preferredquality': '192',
#     #     }],
#     # }
#     # with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#     #     ydl.download([url])
#     # for file in os.listdir("./"):
#     #     if file.endswith(".mp3"):
#     #         os.rename(file, 'song.mp3')
#     # voice.play(discord.FFmpegPCMAudio("song.mp3"))
#     # voice.volume = 100
#     # voice.is_playing()
#
#
# @client.command()
# async def play(ctx, arg):
#     global vc
#
#     try:
#         voice_channel = ctx.author.voice.channel
#         vc = await voice_channel.connect()
#     except:
#         print('Уже подключен или не удалось подключиться')
#
#     if vc.is_playing():
#         await ctx.send(f'{ctx.author.mention}, музыка уже проигрывается.')
#
#     else:
#         with YoutubeDL(YDL_OPTIONS) as ydl:
#             info = ydl.extract_info(arg, download=False)
#
#         URL = info['formats'][0]['url']
#
#         vc.play(discord.FFmpegPCMAudio(executable="C:\\Programming\\ffmpeg\\bin\\ffmpeg.exe", source=URL, **FFMPEG_OPTIONS))
#
#         while vc.is_playing():
#             await sleep(0.1)
#         if not vc.is_paused():
#             await vc.disconnect()
#
#
#
#
# #stop->
# @client.command()
# async def stop(ctx, url: str):
#     pass
#
#
# #pause->
# @client.command()
# async def pause(ctx):
#     await ctx.channel.purge(limit=1)#удаление команды
#
#     if not vc.is_paused():
#         vc.pause()
#         await ctx.send('paused')
#     else:
#         await ctx.send('is already paused')
#
#     # channel = ctx.author.voice.channel
#     # voice = get(client.voice_clients, guild=ctx.guild )
#     # if voice.is_plaing():
#     #     voice.pause()
#     # else:
#     #     ctx.send('нет играющих треков')
#
#
# #resume->
# @client.command()
# async def resume(ctx):
#     await ctx.channel.purge(limit=1)#удаление команды
#
#     if vc.is_paused():
#         vc.resume()
#         await ctx.send('playing')
#     else:
#         await ctx.send('is already playing')
#
#     # channel = ctx.author.voice.channel
#     # voice = get(client.voice_clients, guild=ctx.guild )
#     # if voice.is_paused():
#     #     voice.resume()
#     # else:
#     #     ctx.send('нет поставленных на паузу треков')