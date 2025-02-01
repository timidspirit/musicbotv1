import discord
from discord.ext import commands, tasks
from youtube_dl import YoutubeDL
import asyncio
import os
from datetime import datetime, timedelta

# Dynamic prefix support
def get_prefix(bot, message):
    return os.getenv("PREFIX", "!")  # Default prefix is "!"

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix=get_prefix, intents=intents)

# Cache directory
cache_dir = os.getenv("CACHE_DIR", "cache")
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

# Idle disconnect time (default: 10 minutes)
idle_timeout = int(os.getenv("IDLE_TIMEOUT", 10))  # Timeout in minutes

# YouTubeDL settings
ytdl_opts = {
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'outtmpl': f'{cache_dir}/%(title)s.%(ext)s',
    'quiet': True
}
ytdl = YoutubeDL(ytdl_opts)

queue = []
last_activity = datetime.now()

@tasks.loop(minutes=1)
async def check_idle_disconnect():
    """Checks for idle timeout and disconnects if necessary."""
    if bot.voice_clients:
        vc = bot.voice_clients[0]
        if not vc.is_playing() and (datetime.now() - last_activity).total_seconds() > idle_timeout * 60:
            await vc.disconnect()

async def play_next(ctx):
    """Plays the next track in the queue with crossfade."""
    global last_activity
    last_activity = datetime.now()

    if not queue:
        await ctx.voice_client.disconnect()
        return

    next_track = queue.pop(0)
    url = next_track['url']
    info = ytdl.extract_info(url, download=False)
    audio_url = info['url']
    title = info['title']

    await ctx.send(f"Now playing: {title} (requested by {next_track['requester']})")

    crossfade_filter = "afade=t=out:st=29:d=1,afade=t=in:st=0:d=1"
    ctx.voice_client.play(
        discord.FFmpegPCMAudio(audio_url, options=f"-af {crossfade_filter}"),
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

@bot.command()
async def setprefix(ctx, *, new_prefix):
    """Sets a new command prefix."""
    os.environ["PREFIX"] = new_prefix
    await ctx.send(f"Prefix changed to: {new_prefix}")

@bot.command()
async def join(ctx):
    """Joins the user's voice channel."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You must be in a voice channel for me to join!")

@bot.command()
async def play(ctx, *, url):
    """Plays a YouTube track or queues it if already playing."""
    global last_activity
    last_activity = datetime.now()

    if not ctx.voice_client:
        await join(ctx)

    queue.append({'url': url, 'requester': ctx.author.name})
    await ctx.send(f"Added to queue: {url} (requested by {ctx.author.name})")

    if not ctx.voice_client.is_playing():
        await play_next(ctx)

@bot.command()
async def skip(ctx):
    """Force skips the current track."""
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped the current track!")
        await play_next(ctx)

@bot.command()
async def stop(ctx):
    """Stops playback and clears the queue."""
    global last_activity
    last_activity = datetime.now()

    queue.clear()
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    await ctx.send("Stopped playback and cleared the queue.")

@bot.command()
async def shuffle(ctx):
    """Shuffles the queue."""
    import random
    random.shuffle(queue)
    await ctx.send("Queue shuffled!")

# Start idle disconnect task
check_idle_disconnect.start()

bot.run(os.getenv("DISCORD_TOKEN"))
