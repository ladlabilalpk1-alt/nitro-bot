import discord
from discord.ext import commands
import aiohttp
import string
import random
import time
import asyncio
import os

# ============================================================
# ENVIRONMENT VARIABLES
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = os.environ.get("ADMIN_ID")
BOT_PREFIX = os.environ.get("PREFIX", "!")
BOT_STATUS = os.environ.get("STATUS", "online")
BOT_ACTIVITY = os.environ.get("ACTIVITY", "Nitro Gift Codes")

if not BOT_TOKEN:
    print("[FATAL] BOT_TOKEN nahi mila!")
    exit(1)

if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except:
        ADMIN_ID = None

# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents, help_command=None)

is_running = False
checked_count = 0
valid_count = 0
start_time = None

# ============================================================
def generate_random_string():
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(18))

# ============================================================
async def check_gift_code(code, session):
    url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        async with session.get(url, headers=headers, timeout=12) as resp:
            if resp.status == 200:
                return True
            elif resp.status == 429:
                retry = int(resp.headers.get("Retry-After", 8))
                return ("rate_limited", retry)
            else:
                return False
    except:
        return "error"

# ============================================================
async def send_to_webhook(embed):
    if WEBHOOK_URL:
        try:
            async with aiohttp.ClientSession() as session:
                await session.post(WEBHOOK_URL, json={"embeds": [embed.to_dict()]})
        except:
            pass

# ============================================================
@bot.command()
async def start(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ **Access Denied!** Sirf Admin hi use kar sakta hai.")

    global is_running, checked_count, valid_count, start_time
    if is_running:
        return await ctx.send("⚠️ Checker already chal raha hai!")

    is_running = True
    checked_count = 0
    valid_count = 0
    start_time = time.time()

    embed = discord.Embed(title="🚀 Checker Started", color=discord.Color.green())
    embed.description = f"**Auto Gift Code Checker ON**\n`{BOT_PREFIX}stop` | `{BOT_PREFIX}status`"
    await ctx.send(embed=embed)

    asyncio.create_task(run_checker(ctx))

# ============================================================
@bot.command()
async def stop(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ **Access Denied!**")

    global is_running
    if not is_running:
        return await ctx.send("⚠️ Checker already band hai!")

    is_running = False
    elapsed = int(time.time() - start_time)
    embed = discord.Embed(title="🛑 Checker Stopped", color=discord.Color.red())
    embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Time", value=f"`{elapsed//60}m {elapsed%60}s`", inline=True)
    await ctx.send(embed=embed)

# ============================================================
@bot.command()
async def status(ctx):
    if not is_running:
        return await ctx.send("❌ Checker band hai. `!start` karo.")

    elapsed = int(time.time() - start_time)
    speed = round(checked_count / max(elapsed, 1), 2)
    embed = discord.Embed(title="📊 Live Status", color=discord.Color.green())
    embed.add_field(name="Status", value="🟢 Running", inline=True)
    embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Speed", value=f"`{speed}/sec`", inline=True)
    embed.add_field(name="Uptime", value=f"`{elapsed//60}m {elapsed%60}s`", inline=True)
    await ctx.send(embed=embed)

# ============================================================
async def run_checker(ctx):
    global is_running, checked_count, valid_count
    async with aiohttp.ClientSession() as session:
        while is_running:
            try:
                code = generate_random_string()
                result = await check_gift_code(code, session)
                checked_count += 1

                if result is True:
                    valid_count += 1
                    embed = discord.Embed(
                        title="🎉 VALID GIFT CODE FOUND! 🎉",
                        description=f"```fix\n{code}\n```",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="Total Checked", value=f"`{checked_count}`")
                    embed.add_field(name="Valid Found", value=f"`{valid_count}`")
                    await ctx.send(embed=embed)
                    await send_to_webhook(embed)

                    with open("valid_codes.txt", "a") as f:
                        f.write(f"{code}\n")

                elif isinstance(result, tuple):
                    await asyncio.sleep(result[1] + 2)
                else:
                    await asyncio.sleep(0.75)

            except:
                await asyncio.sleep(5)

# ============================================================
@bot.event
async def on_ready():
    print("="*60)
    print(f"✅ Bot Online → {bot.user}")
    print(f"Admin ID: {ADMIN_ID}")
    print("="*60)

    await bot.change_presence(
        status=discord.Status(BOT_STATUS),
        activity=discord.Activity(type=discord.ActivityType.watching, name=BOT_ACTIVITY)
    )

# ============================================================
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
