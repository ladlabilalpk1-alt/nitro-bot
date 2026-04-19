import discord
from discord.ext import commands
import requests
import string
import random
import time
import asyncio
import os

# ============================================================
# ENVIRONMENT VARIABLES (Railway se aayengi)
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DISCORD_USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN")
GIFT_CODE_API_URL = "https://discord.com/api/v9/entitlements/gift-codes/{}"

# Safety check - agar tokens nahi mile toh bot nahi chalega
if not BOT_TOKEN or not DISCORD_USER_TOKEN:
    print("[FATAL] BOT_TOKEN ya DISCORD_USER_TOKEN environment mein nahi mila!")
    print("[FATAL] Railway dashboard se add karo Variables section mein")
    exit(1)

# ============================================================
# Bot Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
# Global Variables
# ============================================================
is_running = False
checked_count = 0
valid_count = 0
start_time = None

# ============================================================
# Generate Random 18 Character Code
# ============================================================
def generate_random_string():
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(18))

# ============================================================
# Check Gift Code via Discord API
# ============================================================
def check_gift_code(code):
    url = GIFT_CODE_API_URL.format(code)
    headers = {
        "Authorization": f"Bearer {DISCORD_USER_TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            return True
        elif response.status_code == 429:
            return "rate_limited"
        else:
            return False
    except:
        return "error"

# ============================================================
# COMMAND: !start
# ============================================================
@bot.command()
async def start(ctx):
    global is_running, checked_count, valid_count, start_time

    if is_running:
        embed = discord.Embed(
            title="⚠️ Already Running",
            description="Checker already chal raha hai!",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return

    is_running = True
    checked_count = 0
    valid_count = 0
    start_time = time.time()

    embed = discord.Embed(
        title="🚀 Checker Started",
        description="Gift code checker shuru ho gaya!\n`!stop` se roko\n`!status` se dekho",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)
    asyncio.create_task(run_checker(ctx))

# ============================================================
# COMMAND: !stop
# ============================================================
@bot.command()
async def stop(ctx):
    global is_running, start_time

    if not is_running:
        embed = discord.Embed(
            title="⚠️ Not Running",
            description="Checker pehle se band hai!",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        return

    is_running = False
    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60

    embed = discord.Embed(title="🛑 Checker Stopped", color=discord.Color.red())
    embed.add_field(name="Total Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid Found", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Time Ran", value=f"`{minutes}m {seconds}s`", inline=True)
    await ctx.send(embed=embed)

# ============================================================
# COMMAND: !status
# ============================================================
@bot.command()
async def status(ctx):
    global is_running, checked_count, valid_count, start_time

    if not is_running:
        embed = discord.Embed(
            title="📊 Status",
            description="Checker band hai. `!start` se shuru karo.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return

    elapsed = int(time.time() - start_time)
    minutes = elapsed // 60
    seconds = elapsed % 60
    speed = checked_count / max(elapsed, 1)

    embed = discord.Embed(title="📊 Live Status", color=discord.Color.green())
    embed.add_field(name="Status", value="🟢 Running", inline=True)
    embed.add_field(name="Total Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid Found", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Speed", value=f"`{speed:.1f} codes/sec`", inline=True)
    embed.add_field(name="Uptime", value=f"`{minutes}m {seconds}s`", inline=True)
    await ctx.send(embed=embed)

# ============================================================
# COMMAND: !check <code>
# ============================================================
@bot.command()
async def check(ctx, code: str):
    await ctx.send(f"🔍 Checking `{code}`...")
    result = check_gift_code(code)

    if result is True:
        embed = discord.Embed(title="🎉 VALID CODE!", description=f"```\n{code}\n```", color=discord.Color.green())
    elif result == "rate_limited":
        embed = discord.Embed(title="⏳ Rate Limited", description="Thoda ruko phir try karo", color=discord.Color.yellow())
    elif result == "error":
        embed = discord.Embed(title="❌ Error", description="API se connection nahi hua", color=discord.Color.red())
    else:
        embed = discord.Embed(title="❌ Invalid Code", description=f"`{code}` valid nahi hai", color=discord.Color.red())

    await ctx.send(embed=embed)

# ============================================================
# COMMAND: !help
# ============================================================
@bot.command()
async def help(ctx):
    embed = discord.Embed(title="🤖 Bot Commands", color=discord.Color.blue())
    embed.add_field(name="!start", value="Checker shuru karo", inline=False)
    embed.add_field(name="!stop", value="Checker band karo", inline=False)
    embed.add_field(name="!status", value="Live status dekho", inline=False)
    embed.add_field(name="!check <code>", value="Specific code check karo", inline=False)
    embed.add_field(name="!help", value="Yeh message dekho", inline=False)
    await ctx.send(embed=embed)

# ============================================================
# Background Task - Code Checker Loop
# ============================================================
async def run_checker(ctx):
    global is_running, checked_count, valid_count

    while is_running:
        try:
            code = generate_random_string()
            result = check_gift_code(code)
            checked_count += 1

            if result is True:
                valid_count += 1
                embed = discord.Embed(
                    title="🎉 VALID GIFT CODE FOUND! 🎉",
                    description=f"```\n{code}\n```",
                    color=discord.Color.green()
                )
                embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
                embed.add_field(name="Valid So Far", value=f"`{valid_count}`", inline=True)
                embed.set_footer(text="Code found via Railway Hosted Bot")
                await ctx.send(embed=embed)

                # File mein save karo
                with open("valid_codes.txt", "a") as f:
                    f.write(f"{code}\n")

            elif result == "rate_limited":
                await asyncio.sleep(10)

            elif result == "error":
                await asyncio.sleep(5)

            await asyncio.sleep(1)

        except Exception as e:
            print(f"[ERROR] Checker loop error: {e}")
            await asyncio.sleep(5)

# ============================================================
# Bot Ready Event
# ============================================================
@bot.event
async def on_ready():
    print("=" * 50)
    print(f"  Bot: {bot.user}")
    print(f"  ID: {bot.user.id}")
    print(f"  Servers: {len(bot.guilds)}")
    print(f"  Host: Railway")
    print(f"  Status: ONLINE")
    print("=" * 50)

# ============================================================
# Keep Alive - Railway ko sleep nahi hone dene ke liye
# ============================================================
async def keep_alive():
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60)

# ============================================================
# Run
# ============================================================
if __name__ == "__main__":
    bot.loop.create_task(keep_alive())
    bot.run(BOT_TOKEN)
