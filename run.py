import os

from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import urllib.parse
import urllib.request
import re
from discord.player import FFmpegPCMAudio, PCMVolumeTransformer
from youtube_dl import YoutubeDL
from youtube_dl.utils import DownloadError, ExtractorError
import validators
import asyncio

load_dotenv()
# TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN = os.environ['DISCORD_TOKEN']

bot_name = 'Gaine'

bot = discord.Client()
bot = commands.Bot(command_prefix="!", case_insensitive=True)

music_title = ''
music_url = ''
music_thumbnail = ''
queue = []
bot_activity = 'NOTHING'
repeat = 'none'

YDL_OPTIONS = {'format': 'bestaudio/best', 'noplaylist': 'True'}
FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-vn'}


@tasks.loop(seconds=1)
async def bot_check():
    if queue:
        await bot.change_presence(activity=discord.Game(name=bot_activity), status=discord.Status.online)
    if not queue:
        await bot.change_presence(activity=discord.Game(name='NOTHING'), status=discord.Status.idle)


@bot.event
async def on_ready():
    bot_check.start()
    print(f'{bot.user} has connected to Discord!')


@bot.event
async def on_voice_state_update(member, before, after):
    try:
        voice = after.channel.guild.voice_client
        while voice.is_playing():  # Checks if voice is playing
            await asyncio.sleep(1)  # While it's playing it sleeps for 1 second
        else:
            await asyncio.sleep(300)  # If it's not playing it waits 300 seconds / 5 minutes
            while voice.is_playing():  # and checks once again if the bot is not playing
                break  # if it's playing it breaks
            else:
                await voice.disconnect()  # if not it disconnects
                channel = bot.get_channel(505615259638300687)
                await channel.send(embed=discord.Embed(description='Disconneted due to inactivity. *(If bot is inactive for 5 minutes it will automatically disconnects. Use* **!join** *to reconnect bot.)*'))
    except AttributeError:
        print(f'Disconnected due to inactivity')
        


def player(ctx, voice):
    global music_title
    global music_thumbnail
    global music_url
    global bot_activity

    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(queue[0], download=False)
    URL = info['formats'][0]['url']
    bot_activity = info.get('title', None)
    music_url = queue[0]
    music_title = info.get('title', None)
    music_thumbnail = info.get('thumbnail')
    voice.play(FFmpegPCMAudio(
        URL, executable="ffmpeg", **FFMPEG_OPTIONS), after=lambda e: play_queue(ctx, voice))
    voice.is_playing()


def play_queue(ctx, voice):
    global repeat
    try:
        if repeat == 'yes':
            player(ctx, voice)
        elif len(queue) >= 1:
            del queue[0]
            player(ctx, voice)
    except IndexError:
        print(f'Queue finish')


@bot.command(name='join', aliases=['summon'], help='Joins the voice channel')
async def summon(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if not ctx.message.author.voice:
        await ctx.message.add_reaction('✖')
        await ctx.send(embed=discord.Embed(description='You are not connected to a voice channel.'))
    else:
        if voice is None:
            channel = ctx.message.author.voice.channel
            await ctx.message.add_reaction('🆗')
            await channel.connect()
            await ctx.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
        else:
            await ctx.send(embed=discord.Embed(title=bot_name+' is already connected somewhere'))


@bot.command(name='play', aliases=['p'], help='Plays song from youtube')
async def play(ctx, *, url: str):
    channel = ctx.message.author.voice.channel
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)

    if not ctx.message.author.voice:
        await ctx.message.add_reaction('✖')
        await ctx.send(embed=discord.Embed(description='You are not connected to a voice channel.'))


    if voice is None:
        await channel.connect()
        await ctx.guild.change_voice_state(channel=channel, self_mute=False, self_deaf=True)
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' is already connected somewhere'))


    y_link = 'https://www.youtube.com/results?search_query='
    query_string = urllib.parse.urlencode({'search_query': url})
    htm_content = urllib.request.urlopen(y_link + query_string)
    link = y_link + url.replace(' ', '+')
    search_results = re.findall(
        r"watch\?v=(\S{11})", htm_content.read().decode())
    top_result = 'http://www.youtube.com/watch?v=' + search_results[0]

    valid_url = validators.url(url)
    try:
        if not voice.is_playing():
            if valid_url == True:
                try:
                    queue.append(url)
                    music_url = url
                    await ctx.send('Searching for '+url)
                    player(ctx, voice)
                    await ctx.message.add_reaction('▶')
                    await ctx.send('Playing ' + music_title)
                    embed = discord.Embed(
                        title='Now Playing', url=music_url, description='[' + music_title+ '](' + music_url + ')')
                    embed.set_footer(text=f'Requested by {ctx.message.author}')
                    embed.set_thumbnail(url=music_thumbnail)
                    await ctx.send(embed=embed)
                except ExtractorError:
                    await ctx.send(embed=discord.Embed(description='Invalid link'))
                except DownloadError:
                    await ctx.send(embed=discord.Embed(description='Invalid link'))
            else:
                queue.append(top_result)
                music_url = top_result
                await ctx.send('Searching for '+ url)
                player(ctx, voice)
                await ctx.message.add_reaction('▶')
                await ctx.send('Playing ' + music_title)
                embed = discord.Embed(
                    title='Now Playing', url=music_url, description='[' + music_title+ '](' + music_url + ')')
                embed.set_footer(text=f'Requested by {ctx.message.author}')
                embed.set_thumbnail(url=music_thumbnail)
                await ctx.send(embed=embed)
        else:
            if valid_url == True:
                queue.append(url)
                await ctx.message.add_reaction('🆗')
                await ctx.send(embed=discord.Embed(description='Added to queue'))
            else:
                queue.append(top_result)
                await ctx.message.add_reaction('🆗')
                await ctx.send(embed=discord.Embed(description='Added to queue'))
    except AttributeError:
        await ctx.send(embed=discord.Embed(description='Joined a voice channel, please use the command again to play'))


@play.error
async def play_error(ctx, error):
    if isinstance(error, discord.ext.commands.errors.MissingRequiredArgument):
        await ctx.send(embed=discord.Embed(description='Please include URL after **!play** command to play song.'))


@bot.command(name='nowplaying', aliases=['np', 'currently'], help='Displays currently playing song')
async def now(ctx):
    global music_title
    global music_url
    global music_thumbnail
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice:
        if voice.is_playing():
            await ctx.send('Playing ' + music_title)
            embed = discord.Embed(
                title='Now Playing', url=music_url, description='[' + music_title+ '](' + music_url + ')')
            embed.set_footer(text=f'Requested by {ctx.message.author}')
            embed.set_thumbnail(url=music_thumbnail)
            await ctx.send(embed=embed)
        else:
            await ctx.send(embed=discord.Embed(description='Nothing is playing.'))
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' not connected to voice.'))


@bot.command(name='queue', help='Displays the queue')
async def queue_display(ctx):
    global queue_list
    if len(queue) == 0:
        await ctx.send(embed=discord.Embed(description='No queue available'))
    else:
        i = 0
        for x in queue:
            with YoutubeDL(YDL_OPTIONS) as ydl:
                info = ydl.extract_info(x, download=False)
            i = i + 1
            title = str(info.get('title'))
            queue_list = f'```\n{i}. {title}\n```'
            await ctx.send(embed=discord.Embed(description=queue_list))


@bot.command(name='skip', aliases=['next'], help='Skips currently playing song')
async def skip(ctx):
    global music_title
    global music_url
    global music_thumbnail
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        try:
            if repeat == 'yes':
                await ctx.send('Skipping current song')
                voice.pause()
                del queue[0]
                play_queue(ctx, voice)
                await ctx.send('Playing ' + music_title)
                embed = discord.Embed(
                    title='Now Playing', url=music_url, description='[' + music_title+ '](' + music_url + ')')
                embed.set_footer(text=f'Requested by {ctx.message.author}')
                embed.set_thumbnail(url=music_thumbnail)
                await ctx.send(embed=embed)
            elif repeat == 'none':
                await ctx.send('Skipping current song')
                voice.pause()
                # del queue[0]
                play_queue(ctx, voice)
                await ctx.send('Playing ' + music_title)
                embed = discord.Embed(
                    title='Now Playing', url=music_url, description='[' + music_title+ '](' + music_url + ')')
                embed.set_footer(text=f'Requested by {ctx.message.author}')
                embed.set_thumbnail(url=music_thumbnail)
                await ctx.send(embed=embed)
        except IndexError:
            await ctx.send('No song in queue.')
    else:
        await ctx.send('No music playing')


@bot.command(name='loop', aliases=['repeat'], help='Loops the current playing song')
async def loop(ctx):
    global repeat
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        if repeat == 'none':
            repeat = 'yes'
            await ctx.send(embed=discord.Embed(description=music_title+' is now in loop.'))
        elif repeat == 'yes':
            repeat = 'none'
            await ctx.send(embed=discord.Embed(description='Loop disabled'))
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' is not playing.'))


@bot.command(name='pause', help='Pauses currently playing song')
async def pause(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_playing():
        voice.pause()
        await ctx.message.add_reaction('⏸')
        await ctx.send(embed=discord.Embed(description=bot_name+' is paused'))
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' is not playing.'))


@bot.command(name='resume', help='Resumes the paused song')
async def resume(ctx):
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice.is_paused():
        voice.resume()
        await ctx.message.add_reaction('▶')
        await ctx.send(embed=discord.Embed(description=bot_name+' is resumed'))
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' is not paused'))


@bot.command(name='stop', help='Stops the song')
async def stop(ctx):
    global queue
    global queue_list
    global bot_activity
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    queue.clear()
    queue_list = ''
    voice.stop()
    bot_activity = 'nothing'
    await ctx.message.add_reaction('⏹')
    await ctx.send(embed=discord.Embed(description=bot_name+' is stopped'))


@bot.command(name='leave', aliases=['dc', 'disconnect'], help='Disconnects from the voice channel')
async def leave(ctx):
    global queue
    global queue_list
    global bot_activity
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if voice and voice.is_connected():
        queue.clear()
        queue_list = ''
        bot_activity = 'NOTHING'
        await voice.disconnect()
        await ctx.message.add_reaction('🆗')
        await ctx.send(embed=discord.Embed(description=bot_name+' is disconnected'))
    else:
        await ctx.send(embed=discord.Embed(description=bot_name+' is not connected to voice channels'))


@bot.command(name='ping', help='Latency for the bot')
async def ping(ctx):
    await ctx.send(embed=discord.Embed(description=f'Pong! In {round(bot.latency * 1000)}ms'))


@bot.command(name='type', help='**Sends the typed message in selected channel')
async def type(ctx, channel_name: str, *, msg: str):
    admin = ctx.message.author.guild_permissions.administrator
    if admin:
        get_channel = discord.utils.get(
            ctx.guild.channels, guild=ctx.guild, name=channel_name)
        channel_id = get_channel.id
        channel = bot.get_channel(channel_id)
        await channel.send(msg)
    else:
        await ctx.send(embed=discord.Embed(description='You dont have permission to use this command.'))


@bot.command(name='user', help='Grabs the user details')
async def user(ctx, member: discord.Member):
    name = member.name
    id = member.id
    avatar = member.avatar_url
    joined_at = member.joined_at.strftime("%b %d, %Y")
    created_at = member.created_at.strftime("%b %d, %Y")
    embed = discord.Embed(type='rich', title=name, thumbnail=avatar,
                          description=f'User Details', color=discord.Color.blurple())
    embed.add_field(name=f'ID', value=id, inline=True)
    embed.add_field(name=f'Discord Created', value=created_at, inline=False)
    embed.add_field(name=f'Server Joined', value=joined_at, inline=False)
    embed.set_thumbnail(url=avatar)
    await ctx.send(embed=embed)


@bot.command(name='invite', help='Gives the invite link of the discord server')
async def invite(ctx):
    invite_link = await ctx.channel.create_invite(max_age=300)
    await ctx.message.author.send('Here is the invite link. \n' + str(invite_link))


@bot.command(name='clear', help='Clears message')
async def clear(ctx, amount=1):
    admin = ctx.message.author.guild_permissions.administrator
    if admin:
        await ctx.channel.purge(limit=amount)
    else:
        await ctx.send(embed=discord.Embed(description='You dont have permission to use this command.'))


@bot.command(name='volume', aliases=['vol'], help='**Changes volume of bot')
async def vol(ctx, vol: float):
    admin = ctx.message.author.guild_permissions.administrator
    voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
    if admin:
        voice.source = PCMVolumeTransformer(voice.source, volume=vol)
        await ctx.send(embed=discord.Embed(description=f'Successfully changed volume to {vol}'))
    else:
        await ctx.send(embed=discord.Embed(description='You dont have permission to use this command.'))


@bot.command(name='memcount', help='Counts members and bots')
async def count(ctx):
    total_member = ctx.guild.member_count

    embed = discord.Embed(title='Member Count')
    embed.add_field(name='Total Members with bots',
                    value=f'**{total_member}**', inline=True)
    await ctx.send(embed=embed)

bot.run(TOKEN)
