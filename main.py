import discord
from discord.ext import commands
import yt_dlp
import asyncio
from discord import FFmpegPCMAudio
import json
import os

# --- Intents ---
intents = discord.Intents.default()
intents.message_content = True

# --- Bot instance ---
bot = commands.Bot(command_prefix="m", intents=intents, help_command=None)

# --- Global vars ---
queues = {}
volumes = {}
loop_song = {}
loop_queue = {}
FFMPEG_PATH = r"C:\ffmpeg\ffmpeg.exe"

# --- Leaderboard system ---
def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(data):
    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)

user_data = load_users()

# --- yt_dlp options ---
ytdl_opts = {
    "format": "bestaudio/best",
    "quiet": True,
    "noplaylist": True,
    "default_search": "ytsearch",
    "source_address": "0.0.0.0"
}

# --- Events ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# --- Music Functions ---
async def play_next(ctx):
    guild_id = ctx.guild.id
    if guild_id not in queues or len(queues[guild_id]) == 0:
        return

    if loop_song.get(guild_id):
        url = queues[guild_id][0]
        await play_music(ctx, url)
        return

    url = queues[guild_id].pop(0)
    if loop_queue.get(guild_id):
        queues[guild_id].append(url)

    await play_music(ctx, url)

async def play_music(ctx, url):
    voice = ctx.voice_client
    if not voice:
        return await ctx.send("Bot is not connected to a voice channel.")

    with yt_dlp.YoutubeDL(ytdl_opts) as ytdl:
        info = ytdl.extract_info(url, download=False)
        audio_url = info["url"]

    raw = FFmpegPCMAudio(
        audio_url,
        executable=FFMPEG_PATH,
        before_options="-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        options="-vn"
    )

    volume = volumes.get(ctx.guild.id, 0.5)
    source = discord.PCMVolumeTransformer(raw, volume=volume)

    voice.play(
        source,
        after=lambda e: asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
    )

# --- Commands ---
@bot.command()
async def join(ctx):
    if ctx.author.voice:
        if not ctx.voice_client:
            await ctx.author.voice.channel.connect()
        else:
            await ctx.send("Nasa VC ka na MONTANGA")
    else:
        await ctx.send("Join ka muna sa VC POTANGINAMO")

@bot.command()
async def play(ctx, *, url):
    if not ctx.voice_client:
        await ctx.invoke(join)

    queues.setdefault(ctx.guild.id, [])
    volumes.setdefault(ctx.guild.id, 0.5)

    # TRACK USER USAGE
    user_id = str(ctx.author.id)
    if user_id not in user_data:
        user_data[user_id] = 0
    user_data[user_id] += 1
    save_users(user_data)

    if ctx.voice_client.is_playing():
        queues[ctx.guild.id].append(url)
        await ctx.send("Added to queue")
    else:
        queues[ctx.guild.id].append(url)
        await play_next(ctx)
        await ctx.send("Playing now")

@bot.command()
async def users(ctx):
    if not user_data:
        return await ctx.send("Walang gumagamit pa.")

    sorted_users = sorted(user_data.items(), key=lambda x: x[1], reverse=True)
    msg = "**Music Leaderboard:**\n"
    for i, (user_id, count) in enumerate(sorted_users[:10], 1):
        user = await bot.fetch_user(int(user_id))
        msg += f"{i}. {user.name} — {count} uses\n"

    await ctx.send(msg)

@bot.command()
async def loop(ctx, mode: str):
    guild_id = ctx.guild.id
    if mode.lower() == "song":
        loop_song[guild_id] = True
        loop_queue[guild_id] = False
        await ctx.send("Looping ur current song")
    elif mode.lower() == "queue":
        loop_queue[guild_id] = True
        loop_song[guild_id] = False
        await ctx.send("Looping ur entire queue")
    elif mode.lower() == "off":
        loop_song[guild_id] = False
        loop_queue[guild_id] = False
        await ctx.send("Looping turned off")
    else:
        await ctx.send("Usage: mloop song|queue|off")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Skipped")

@bot.command()
async def pause(ctx):
    if ctx.voice_client:
        ctx.voice_client.pause()
        await ctx.send("Paused")

@bot.command()
async def resume(ctx):
    if ctx.voice_client:
        ctx.voice_client.resume()
        await ctx.send("Resumed")

@bot.command()
async def volume(ctx, vol: int):
    if vol < 0 or vol > 50000:
        return await ctx.send("0 - 50000 lang")
    volumes[ctx.guild.id] = vol / 100
    if ctx.voice_client and ctx.voice_client.source:
        ctx.voice_client.source.volume = vol / 100
    await ctx.send(f"Volume set to {vol}%")

@bot.command()
async def leave(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()

@bot.command()
async def help(ctx):
    await ctx.send(
        "**Commands:**\n"
        "**uji/kel**\n"
        "mjoin\n"
        "mplay <Youtube URL>\n"
        "mskip\n"
        "mpause\n"
        "mresume\n"
        "mvolume <0 - 50000 tanga>\n"
        "mloop song|queue|off - Use loop before playing music\n"
        "musers - LeaderBoard\n"
        "mleave"
    )

# --- Run Bot ---
bot.run(os.getenv("TOKEN"))

