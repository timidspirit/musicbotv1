import discord
from discord.ext import commands
import youtube_dl
import os
import difflib
import asyncio
from collections import deque

intents = discord.Intents.default()
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
disconnect_timer = 60
current_song = None
song_queue = deque()
cleanup_self_timer = 60
cleanup_local_timer = 60
cleanup_play_timer = 60

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

def find_closest_match(query, file_list):
    closest_match = difflib.get_close_matches(query, file_list, n=1)
    if closest_match:
        return closest_match[0]
    else:
        return None

@bot.command()
async def play(ctx, *args):
    global current_song

    query = " ".join(args)
    voice_channel = ctx.author.voice.channel
    if not voice_channel:
        await ctx.send("You need to be in a voice channel to use this command.")
        return

    try:
        voice_client = await voice_channel.connect()
    except discord.ClientException:
        voice_client = ctx.voice_client

    if voice_client.is_playing():
        voice_client.stop()

    # Check if the query is a YouTube search or a local file search
    if query.startswith('http://') or query.startswith('https://'):
        # YouTube search
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'noplaylist': True,
            'quiet': True,
        }
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(query, download=False)
            url = info['url']
            current_song = url
            voice_client.play(discord.FFmpegPCMAudio(url), after=lambda e: on_music_end(ctx, voice_client))
    else:
        # Local file search
        music_directory = '/mnt/user/Media/Music'  # Replace this with the actual path on your Unraid server
        file_list = []
        for root, dirs, files in os.walk(music_directory):
            for file in files:
                if file.endswith('.mp3'):
                    file_list.append(file)

        closest_match = find_closest_match(query, file_list)
        if closest_match:
            file_path = os.path.join(music_directory, closest_match)
            current_song = closest_match
            voice_client.play(discord.FFmpegPCMAudio(file_path), after=lambda e: on_music_end(ctx, voice_client))
        else:
            await ctx.send("No matching song found in the local music collection.")

def on_music_end(ctx, voice_client):
    global disconnect_timer
    global current_song
    global song_queue

    disconnect_timer = 0
    if disconnect_timer > 0:
        asyncio.run_coroutine_threadsafe(disconnect_after_timer(ctx, voice_client), bot.loop)

    current_song = None

    # Check if there are songs in the queue and play the next one
    if song_queue:
        next_song = song_queue.popleft()
        voice_client.play(discord.FFmpegPCMAudio(next_song), after=lambda e: on_music_end(ctx, voice_client))

async def disconnect_after_timer(ctx, voice_client):
    global disconnect_timer
    await asyncio.sleep(disconnect_timer)
    if voice_client and voice_client.is_connected():
        await voice_client.disconnect()

@bot.command()
async def disctimer(ctx, seconds: int):
    global disconnect_timer
    if 0 <= seconds <= 60:
        disconnect_timer = seconds
        await ctx.send(f"Disconnect timer set to {seconds} seconds after playing music.")
    else:
        await ctx.send("Invalid value. Please set a timer between 0 and 60 seconds.")

@bot.command()
async def stop(ctx):
    voice_client = ctx.voice_client
    if voice_client:
        voice_client.stop()
        await voice_client.disconnect()
    else:
        await ctx.send("I'm not connected to a voice channel.")

@bot.command()
async def playing(ctx):
    global current_song
    if current_song:
        global playing_msg
        playing_msg = await ctx.send(f"Currently playing: {current_song}")
        await ctx.message.delete(delay=30)  # Delete the original !playing command after 15 seconds
    else:
        await ctx.send("No song is currently playing.")

@bot.command()
async def skip(ctx):
    voice_client = ctx.voice_client
    if voice_client and voice_client.is_playing():
        voice_client.stop()
    else:
        await ctx.send("I'm not currently playing any music.")

@bot.command()
async def queue(ctx, *args):
    global song_queue

    query = " ".join(args)
    music_directory = '/mnt/user/Media/Music'  # Replace this with the actual path on your Unraid server
    file_list = []
    for root, dirs, files in os.walk(music_directory):
        for file in files:
            if file.endswith('.mp3'):
                file_list.append(file)

    closest_match = find_closest_match(query, file_list)
    if closest_match:
        file_path = os.path.join(music_directory, closest_match)
        song_queue.append(file_path)
        await ctx.send(f"{closest_match} added to the queue.")
    else:
        await ctx.send("No matching song found in the local music collection.")

@bot.command()
async def viewqueue(ctx):
    global song_queue
    if song_queue:
        queue_list = "\n".join([f"{i+1}. {os.path.basename(song)}" for i, song in enumerate(song_queue)])
        await ctx.send(f"Current queue:\n{queue_list}")
    else:
        await ctx.send("The queue is currently empty.")

@bot.command()
async def remove(ctx, index: int):
    global song_queue
    if 1 <= index <= len(song_queue):
        removed_song = song_queue.pop(index - 1)
        await ctx.send(f"{os.path.basename(removed_song)} removed from the queue.")
    else:
        await ctx.send("Invalid queue index. Please provide a valid index.")

@bot.command()
async def clearqueue(ctx):
    global song_queue
    song_queue.clear()
    await ctx.send("Queue cleared.")

@bot.command()
async def cleanup(ctx, option: str, seconds: int):
    if option.lower() == 'self':
        if 0 <= seconds <= 9000:
            await ctx.message.delete(delay=seconds)
            bot.remove_command('play')
        else:
            await ctx.send("Invalid value. Please set a timer between 0 and 9000 seconds for self-cleanup.")

@bot.command()
async def cleanup_local(ctx, seconds: int):
    if 0 <= seconds <= 9000:
        await ctx.message.delete(delay=seconds)
        bot.remove_command('local')
    else:
        await ctx.send("Invalid value. Please set a timer between 0 and 9000 seconds for cleanup.")

bot.run()
