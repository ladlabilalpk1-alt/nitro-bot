import discord
from discord.ext import commands
import aiohttp
import string
import random
import time
import asyncio
import os
from dotenv import load_dotenv  # ← Added

# ============================================================
# Load Environment Variables
# ============================================================
load_dotenv()  # .env file ko load karega (agar ho to)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
DISCORD_USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN")

if not BOT_TOKEN or not DISCORD_USER_TOKEN:
    print("[FATAL] BOT_TOKEN aur DISCORD_USER_TOKEN nahi mile!")
    print("Railway pe Variables add karo ya local mein .env file banao.")
    exit(1)

# ============================================================
# Bot Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# Global Variables
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
        "Authorization": DISCORD_USER_TOKEN,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return True
            elif resp.status == 429:
                retry = int(resp.headers.get("Retry-After", 8))
                return ("rate_limited", retry)
            elif resp.status in (400, 404):
                return False
            else:
                return ("error", resp.status)
    except asyncio.TimeoutError:
        return "timeout"
    except Exception as e:
        print(f"[API Error] {code} | {e}")
        return "error"

# ============================================================
# Commands (same as before)
# ============================================================
@bot.command()
async def start(ctx):
    global is_running, checked_count, valid_count, start_time
    if is_running:
        return await ctx.send("⚠️ Checker already chal raha hai!")

    is_running = True
    checked_count = 0
    valid_count = 0
    start_time = time.time()

    embed = discord.Embed(title="🚀 Checker Started Successfully!", color=discord.Color.green())
    embed.description = "**Gift Code Checker Running**\n`!stop` • `!status`"
    await ctx.send(embed=embed)

    asyncio.create_task(run_checker(ctx))

@bot.command()
async def stop(ctx):
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

@bot.command()
async def status(ctx):
    if not is_running:
        return await ctx.send("❌ Checker band hai. `!start` karo")

    elapsed = int(time.time() - start_time)
    speed = round(checked_count / max(elapsed, 1), 2)
    
    embed = discord.Embed(title="📊 Live Status", color=discord.Color.green())
    embed.add_field(name="Status", value="🟢 Running", inline=True)
    embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid Found", value=f"`{valid_count}`", inline=True)
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
                        title="🎉 VALID GIFT CODE FOUND 🎉",
                        description=f"```fix\n{code}\n```",
                        color=discord.Color.gold()
                    )
                    embed.add_field(name="Total Checked", value=f"`{checked_count}`")
                    embed.add_field(name="Valid", value=f"`{valid_count}`")
                    await ctx.send(embed=embed)

                    with open("valid_codes.txt", "a", encoding="utf-8") as f:
                        f.write(f"{code}\n")

                elif isinstance(result, tuple) and result[0] == "rate_limited":
                    await asyncio.sleep(result[1] + 2)
                else:
                    await asyncio.sleep(0.7)

            except Exception as e:
                print(f"[Loop Error]: {e}")
                await asyncio.sleep(5)

# ============================================================
@bot.event
async def on_ready():
    print("="*60)
    print(f"✅ Bot Online → {bot.user}")
    print(f"Host: Railway / Local")
    print("="*60)

# ============================================================
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
