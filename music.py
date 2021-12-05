import discord
from discord.ext import commands
import youtube_dl
import asyncio
import json


class Player(commands.Cog):
    def __init__(self, client):
        self.client = client

    async def check_queue(self, ctx):  # проверка на наличие песен в очереди. Если есть то отправляет запрос в play_song
        print('check_queue')
        file = open('Db.json', 'r')  # получение данных из Bd->
        data = json.loads(file.read())
        file.close()
        settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

        if settings['repeat']:
            settings['queue'].append(settings['queue'][0])
            settings['queue'].pop(0)
            ctx.voice_client.stop()
            await self.play_song(ctx, settings['queue'][0])
        else:
            if len(settings['queue']) > 0:
                ctx.voice_client.stop()
                settings['queue'].pop(0)
            if len(settings['queue']) > 0:
                await self.play_song(ctx, settings['queue'][0])

        data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
        file = open('Db.json', 'w')
        json.dump(data, file)
        file.close()

    async def search_song(self, amount, song):  # поиск одной песни для немедленного проигрывания
        print('search_song')
        ydl_opts = {'format': 'bestaudio', 'queue': 'True', 'simulate': 'True', 'preferredquality': '192',
                    'preferredcodec': 'mp3', 'key': 'FFmpegExtractAudio'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f'ytsearch{amount}:{song}', download=False, ie_key='YoutubeSearch')
        if len(info['entries']) == 0:
            return None

        return info

    async def play_song(self, ctx, song):  # непосредственно проигрывание песни с готовым url
        print('play_song')
        print(song)
        ydl_opts = {'format': 'bestaudio', 'queue': 'True', 'simulate': 'True', 'preferredquality': '192',
                    'preferredcodec': 'mp3', 'key': 'FFmpegExtractAudio'}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(song, download=False)

        url = info['formats'][0]['url']
        source = discord.FFmpegPCMAudio(url)

        ctx.voice_client.play(source, after=lambda error: self.client.loop.create_task(self.check_queue(ctx)))
        ctx.voice_client.source.volume = 0.5

    @commands.command(aliases=['p'])
    async def play(self, ctx, *, song=None):  # play->
        print('play')

        if ctx.voice_client.is_paused():
            ctx.voice_client.resume()

        if song is None:
            return await ctx.send('*Вы должны указать трек!*')

        file = open('Db.json', 'r')  # получение данных из Bd->
        data = json.loads(file.read())
        file.close()
        settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

        if song.split()[0].lower() in ['list', 'playlist', 'l', 'pl']:  # проигрывание плейлиста
            print('playlist')
            try:
                await ctx.message.delete()  # удаление команды
            finally:

                if song.split()[1].lower() in list(settings['playlists']):
                    settings['queue'] = settings['playlists'][song.split()[1].lower()]

                    if ctx.voice_client.source is not None:
                        ctx.voice_client.stop()
                        await self.play_song(ctx, settings['queue'][0])
                    else:
                        await self.play_song(ctx, settings['queue'][0])

                    data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                    file = open('Db.json', 'w')
                    json.dump(data, file)
                    file.close()

                    return await ctx.send(f'*Играет плейлист **{song.split()[1].lower()}***')
                else:
                    return await ctx.send(f'*Плейлист **{song.split()[1].lower()}** __не найден__ ❌* ')

        if not ('youtube.com/watch?' in song or 'https://youtu.be/' in song):  # поиск песни если это не url
            print('searching')
            msg = await ctx.send('**Поик трека...**')

            info = await self.search_song(1, song)
            try:
                await msg.delete()  # Удаление сообщения 'поиск песни...'
            finally:

                if info is None:
                    return await ctx.send('*Не удалось найти трек!*')
                song = info['entries'][0]['webpage_url']

                seconds = info['entries'][0]['duration']
                hour = seconds // 3600
                seconds %= 3600
                minutes = seconds // 60
                seconds %= 60
                if hour > 0:
                    duration = "%d:%02d:%02d" % (hour, minutes, seconds)
                elif minutes > 0:
                    duration = "%02d:%02d" % (minutes, seconds)
                else:
                    duration = "%02d" % seconds

                await ctx.send(f'{song}  ({duration})')

        if ctx.voice_client.source is not None:
            if song in settings['queue']:
                return await ctx.send('*Этот трек уже добавлен в очередь!*')
            else:
                if len(settings['queue']) < 30:
                    settings['queue'].append(song)
                    data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                    file = open('Db.json', 'w')
                    json.dump(data, file)
                    file.close()
                    return await ctx.send('*Трек добавлен в очередь*')
                else:
                    return await ctx.send('*Уже добавлено слишком монго треков!*')

        settings['queue'].append(song)

        data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
        file = open('Db.json', 'w')
        json.dump(data, file)
        file.close()

        await self.play_song(ctx, song)
        # await ctx.send(f'Сейчас играет: ***{name}***')

    @play.before_invoke
    async def connect_voice(self, ctx):  # вызывается перед вызовом play
        if discord.utils.get(ctx.author.roles, name='muted'):
            await ctx.send('*❌ Вам запрещено использовать эту команду!*')
            raise commands.CommandError("Author is muted.")

        if ctx.voice_client is None:
            if ctx.author.voice:
                await ctx.author.voice.channel.connect()
            else:
                await ctx.send("Вы не подключены к голосовому каналу")
                raise commands.CommandError("Author not connected to a voice channel.")

    @commands.command(aliases=['find'])
    async def search(self, ctx, *, song=None):  # поиск песен по названию (5 вариантов)
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if song is None:
                return await ctx.send('**Вы должны указать трек!**')

            wait = await ctx.send(f'**поиск `{song}`...**')

            info = await self.search_song(5, song)
            if info is None:
                return await ctx.send('Не удалось найти трек')

            result = f'**Пожалуйста, выберите трек отправив число от 1 до 5:**\n'
            amount = 0
            urls = []
            for entry in info['entries']:
                amount += 1
                urls.append(entry['webpage_url'])

                seconds = entry['duration']
                hour = seconds // 3600
                seconds %= 3600
                minutes = seconds // 60
                seconds %= 60
                if hour > 0:
                    duration = "%d:%02d:%02d" % (hour, minutes, seconds)
                elif minutes > 0:
                    duration = "%02d:%02d" % (minutes, seconds)
                else:
                    duration = "%02d" % seconds
                result += f"**{amount}:** {entry['title']}\n({duration})\n"

            try:
                await wait.delete()
            finally:
                pass
            res = await ctx.send(result)

            try:  # ожидание ответа
                confirm = await self.client.wait_for("message", check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=35)
            except asyncio.TimeoutError:
                return await res.edit(content=res.content + '\n **Время для выбора трека вышло!**')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            if confirm.content == '1':
                settings['queue'].append(urls[0])

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                try:
                    await confirm.delete()
                finally:
                    pass
                await ctx.send(f'**Вы выбрали трек {confirm.content}:** {urls[0]}')

                if ctx.voice_client.is_playig():
                    return
                await self.connect_voice(ctx)
                await self.play_song(ctx, urls[0])

            elif confirm.content == '2':
                settings['queue'].append(urls[1])

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                try:
                    await confirm.delete()
                finally:
                    pass
                await ctx.send(f'**Вы выбрали трек {confirm.content}:** {urls[1]}')

                if ctx.voice_client.is_playig():
                    return
                await self.connect_voice(ctx)
                await self.play_song(ctx, urls[1])

            elif confirm.content == '3':
                settings['queue'].append(urls[2])

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                try:
                    await confirm.delete()
                finally:
                    pass
                await ctx.send(f'**Вы выбрали трек {confirm.content}:** {urls[2]}')

                if ctx.voice_client.is_playig():
                    return
                await self.connect_voice(ctx)
                await self.play_song(ctx, urls[2])

            elif confirm.content == '4':
                settings['queue'].append(urls[3])

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                try:
                    await confirm.delete()
                finally:
                    pass
                await ctx.send(f'**Вы выбрали трек {confirm.content}:** {urls[3]}')

                if ctx.voice_client.is_playig():
                    return
                await self.connect_voice(ctx)
                await self.play_song(ctx, urls[3])

            elif confirm.content == '5':
                settings['queue'].append(urls[4])

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()

                try:
                    await confirm.delete()
                finally:
                    pass
                await ctx.send(f'**Вы выбрали трек {confirm.content}:** {urls[4]}')

                if ctx.voice_client.is_playig():
                    return
                await self.connect_voice(ctx)
                await self.play_song(ctx, urls[4])

            else:
                try:
                    await confirm.delete()
                finally:
                    pass
                return await ctx.send('**Вы ввели недопустимое значение!**')

    @commands.command(aliases=['q'])
    async def queue(self, ctx):  # отобразить очередь->
        try:
            await ctx.message.delete()  # удаление команды
        finally:

            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            if len(settings['queue']) == 0:
                return await ctx.send('**Очередь треков пуста**')

            wait = await ctx.send(f'**Обработка очереди....**')

            ydl_opts = {'format': 'bestaudio', 'queue': 'True', 'simulate': 'True', 'preferredquality': '192',
                        'preferredcodec': 'mp3', 'key': 'FFmpegExtractAudio'}

            queue_list = '**----Очередь треков----**\n'

            count = 0
            for song in settings['queue']:
                with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(song, download=False)
                count += 1

                seconds = info['duration']
                hour = seconds // 3600
                seconds %= 3600
                minutes = seconds // 60
                seconds %= 60
                if hour > 0:
                    duration = "%d:%02d:%02d" % (hour, minutes, seconds)
                elif minutes > 0:
                    duration = "%02d:%02d" % (minutes, seconds)
                else:
                    duration = "%02d" % seconds

                queue_list += f"**{count}:** {info['title']} \n    ({duration})\n"
            queue_list += '**------------------------------**'
            try:
                await wait.delete()
            finally:
                pass
            await ctx.send(queue_list)

    @commands.command(aliases=['s'])
    async def skip(self, ctx):  # пропуск текущего трека->
        print('skip')
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            if settings['vote_to_skip']:  # если голосование включено
                embed = discord.Embed(title=f'Голосование __пропустить__ текущий трек',
                                      description='**50% голосов позволит пропустить текущий трек**',
                                      color=discord.Color.blue())
                embed.set_author(name=ctx.author, icon_url=ctx.author.avatar_url)
                embed.add_field(name='Пропустить', value=':white_check_mark:')
                embed.add_field(name='Оставить', value=':no_entry_sign:')
                embed.set_footer(text='Голосование завершится через 15 секунд!')

                poll = await ctx.send(embed=embed)

                await poll.add_reaction(u'\u2705')
                await poll.add_reaction(u'\U0001F6AB')

                await asyncio.sleep(15)  # 15 секунд ожидание
                poll = await ctx.channel.fetch_message(poll.id)

                votes = {u'\u2705': 0, u'\U0001F6AB': 0}
                reacted = []

                for reaction in poll.reactions:
                    if reaction.emoji in [u'\u2705', u'\U0001F6AB']:
                        async for user in reaction.users():
                            if ctx.author.voice.channel.id == ctx.voice_client.channel.id and user.id not in reacted and not user.bot:
                                votes[reaction.emoji] += 1
                                reacted.append(user.id)
                skip = False

                if votes[u'\u2705'] > 0:
                    if votes[u'\U0001F6AB'] == 0 or votes[u'\u2705'] / (votes[u'\u2705'] + votes[u'\U0001F6AB']) > 0.49:  # 50% или больше
                        skip = True
                        embed = discord.Embed(title='Пропуск __подтверждён__',
                                              description=' ***Трек был пропущен голосованием***',
                                              color=discord.Color.green())

                if not skip:
                    embed = discord.Embed(title='Пропуск __отменён__',
                                          description=' *Трек не был пропущен голосованием*\n***Текущий трек будет оставлен***',
                                          color=discord.Color.red())

                await poll.clear_reactions()
                await poll.edit(embed=embed)

                if skip:
                    ctx.voice_client.stop()

            else:  # если голосование отключено
                await ctx.send(f'*Текущий трек был **пропущен** ⏩ {ctx.author}*')
                ctx.voice_client.stop()

    @commands.command(aliases=['pl', 'playlist'])
    async def playlists(self, ctx, type=None, name=None, *, value=None):
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            if type is None:
                if len(list(settings['playlists'])) == 0:
                    return await ctx.send('*Ни одного плейлиста пока не создано!\n '
                                          'Для того чтобы создать плейлист используйте команду:*\n '
                                          '`.playlists create <имя(одно слово)> <несколько url> или **queue**'
                                          '(текущая очередь добавиться в плейлист)`')

                lists = '**----Список плейлистов----**\n'
                for playlist in list(settings['playlists']):
                    lists += f'**{playlist}**  |  треков: **{len(settings["playlists"][playlist])}**\n'
                lists += '**----------------------------------**'
                return await ctx.send(lists)

            if type.lower() in ['create', 'new']:
                if value is None or name is None:
                    return await ctx.send('**Вы ввели не все аргументы!**\n'
                                          'Чтобы создать плейлист используйте параметры:\n'
                                          '`.pl create <имя(одно слово)> queue` (в плейлист будет добавлена текущая очередь)  **или**\n'
                                          '`.pl create <имя(одно слово)> <url1, url2, и т.д>` (в плейлист будут добавлены только треки по ссылкам с YouTube)')

                if ('youtube.com/watch?' in name.lower() or 'https://youtu.be/' in name.lower()):
                    return await ctx.send('*Недопустимое имя плейлиста!*')

                if name.lower() in list(settings['playlists']):
                    return await ctx.send('**Плейлист с таким именем уже существует!**')

                if value.split()[0] in ['queue', 'q']:  # если хочу создать через очередь
                    if len(settings['queue']) == 0:
                        return await ctx.send('**Текущая очередь пуста, нельзя создать плейлист без треков!**')

                    settings['playlists'][name.lower()] = settings['queue']
                else:
                    settings['playlists'][name.lower()] = value.split()

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()
                return await ctx.send(f'*Плейлист **{name}** успешно **создан**\n'
                                      f'Удалить плейлист можно командой:*\n'
                                      f'**.playlists delete <название>**')

            if type.lower() in ['delete', 'del', 'remove']:
                if name is None:
                    return await ctx.send(f'**Вы не ввели имя плейлиста!**')

                if not name.lower() in list(settings['playlists']):
                    return await ctx.send('**Плейлиста с таким именем не существует!**')

                del settings['playlists'][name.lower()]

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()
                return await ctx.send(f'*Плейлист **{name}** успешно **удален** *')

            if type.lower() in ['add']:
                if name is None:
                    return await ctx.send(f'**Вы не ввели имя плейлиста!**')

                if value is None:
                    return await ctx.send(f'**Вы не ввели url для добавления!**')

                if not name.lower() in list(settings['playlists']):
                    return await ctx.send('**Плейлиста с таким именем не существует!**')

                if value.split()[0] in ['queue', 'q']:  # если хочу добавить через очередь
                    if len(settings['queue']) == 0:
                        return await ctx.send('**Текущая очередь пуста, нельзя создать плейлист без треков!**')

                    settings['playlists'][name.lower()] = settings['queue']
                else:
                    settings['playlists'][name.lower()] = value.split()

                data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
                file = open('Db.json', 'w')
                json.dump(data, file)
                file.close()
                return await ctx.send(f'*Плейлист **{name}** успешно* **расширен**')

            return await ctx.send(f'**Такого параметра __playlists__ не существует!**')

    @commands.command(aliases=['st'])
    async def stop(self, ctx):  # очистка queue и отключение->
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            settings['queue'] = []
            settings['repeat'] = False

            data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
            file = open('Db.json', 'w')
            json.dump(data, file)
            file.close()

            return await ctx.voice_client.disconnect()

    @commands.command(aliases=['rep'])
    async def repeat(self, ctx):  # очистка queue и отключение->
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            file = open('Db.json', 'r')  # получение данных из Bd->
            data = json.loads(file.read())
            file.close()
            settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

            if settings['repeat']:
                return await ctx.send('*Текущая очередь уже **повторяется** 🔁*')

            settings['repeat'] = True

            data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
            file = open('Db.json', 'w')
            json.dump(data, file)
            file.close()

            await ctx.send('*Текущая очередь будет **повторяться** 🔁*')

    @commands.command(aliases=['unrep'])
    async def unrepeat(self, ctx):  # очистка queue и отключение->
        await ctx.message.delete()  # удаление команды
        if discord.utils.get(ctx.author.roles, name='muted'):
            return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

        if ctx.voice_client is None:
            return await ctx.send('*Я не нахожусь в голосовом канале!*')

        if ctx.author.voice is None:
            return await ctx.send('*Вы не в голосовом кнале!*')

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

        file = open('Db.json', 'r')  # получение данных из Bd->
        data = json.loads(file.read())
        file.close()
        settings = data[str(ctx.message.guild.id)]  # settings содержит все настройки для этого сервера

        if not settings['repeat']:
            return await ctx.send('*Текущая очередь уже **не повторялась** *')

        settings['repeat'] = False

        data[str(ctx.message.guild.id)] = settings  # Запись новых данных в Bd->
        file = open('Db.json', 'w')
        json.dump(data, file)
        file.close()

        await ctx.send('*Текущая очередь **перестала повторяться***')

    @commands.command()
    async def pause(self, ctx):  # пауза->
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            if not ctx.voice_client.is_paused():
                print('pause')
                await ctx.send('*пауза* ⏸')
                ctx.voice_client.pause()

            time = 0  # если бот стоит на паузе больше 5 мин то он покидает голосовой канал и чистит очередь
            while ctx.voice_client.is_paused():  # Checks if voice is playing
                await asyncio.sleep(1)
                time += 1
                if time > 300:  # 5 мин
                    file = open('Db.json', 'r')
                    data = json.loads(file.read())
                    file.close()
                    data[str(ctx.message.guild.id)]['queue'] = []
                    data[str(ctx.message.guild.id)]['repeat'] = False
                    file = open('Db.json', 'w')
                    json.dump(data, file)

                    print('auto-leave')
                    await ctx.send('**Бот слишком долго стоял на паузе. Очередь была очищена**')
                    return await ctx.voice_client.disconnect()

    @commands.command()
    async def resume(self, ctx):  # продолжить->
        try:
            await ctx.message.delete()  # удаление команды
        finally:
            if discord.utils.get(ctx.author.roles, name='muted'):
                return await ctx.send('*❌ Вам запрещено использовать эту команду!*')

            if ctx.voice_client is None:
                return await ctx.send('*Я не нахожусь в голосовом канале!*')

            if ctx.author.voice is None:
                return await ctx.send('*Вы не в голосовом кнале!*')

            if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
                return await ctx.send('*Вы не находитесь со мной в одном голосовом канале!*')

            if ctx.voice_client.is_paused():
                print('resume')
                await ctx.send('*Продолжить* ▶')
                ctx.voice_client.resume()

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):  # вызывается при подключении\отключении от голосового канала
        if member == self.client.user or before.channel is None:
            return

        if self.client.user in before.channel.members:
            count = 0
            for user in before.channel.members:
                if not user.bot:
                    count += 1

            if count == 0:
                for voice in self.client.voice_clients:
                    if voice.channel.id == before.channel.id:
                        if voice.is_paused():
                            return
                        print('auto-pause')
                        voice.pause()

                        time = 0  # если бот стоит на паузе больше 2 мин то он покидает голосовой канал и чистит очередь
                        while voice.is_paused():  # Checks if voice is playing
                            await asyncio.sleep(1)
                            time += 1
                            if time > 120:  # 2 мин
                                file = open('Db.json', 'r')
                                data = json.loads(file.read())
                                file.close()
                                data[str(voice.guild.id)]['queue'] = []
                                data[str(voice.guild.id)]['repeat'] = False
                                file = open('Db.json', 'w')
                                json.dump(data, file)

                                print('auto-leave')
                                return await voice.disconnect()