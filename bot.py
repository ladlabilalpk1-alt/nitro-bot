import discord
from discord.ext import commands
import requests
import string
import random
import time
import asyncio
import os
from dotenv import load_dotenv # <--- Yeh add kiya hai

# ============================================================
# CONFIGURATION & ENVIRONMENT VARIABLES
# ============================================================

# 1. Load .env file (Agar local par chal raha hai toh file se lega)
# 2. Railway par file nahi milegi toh error throw nahi karega,
#    aur seedha system environment variables (Dashboard) se lega.
load_dotenv()

# Variables fetch kar rahe hain
BOT_TOKEN = os.environ.get("BOT_TOKEN")
DISCORD_USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = os.environ.get("ADMIN_ID")
PREFIX = os.environ.get("PREFIX", "!")
STATUS = os.environ.get("STATUS", "online")
ACTIVITY = os.environ.get("ACTIVITY", "Nitro Checking")

# Safety Checks
if not BOT_TOKEN:
    print("[FATAL] BOT_TOKEN missing! Dashboard ya .env file mein check karo.")
    exit(1)

if not DISCORD_USER_TOKEN:
    print("[WARNING] DISCORD_USER_TOKEN missing! Checker function nahi chalega.")

# Admin ID Convert to Int (Agar set hai toh)
if ADMIN_ID:
    try:
        ADMIN_ID = int(ADMIN_ID)
    except ValueError:
        print("[WARNING] ADMIN_ID Invalid format.")
        ADMIN_ID = None

GIFT_CODE_API_URL = "https://discord.com/api/v9/entitlements/gift-codes/{}"

# ============================================================
# Bot Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# ============================================================
# Global Variables
# ============================================================
is_running = False
checked_count = 0
valid_count = 0
start_time = None

# ============================================================
# Functions
# ============================================================
def generate_random_string():
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(18))

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

def send_webhook(embed):
    if WEBHOOK_URL:
        try:
            data = {"embeds": [embed.to_dict()]}
            requests.post(WEBHOOK_URL, json=data)
        except:
            pass

# ============================================================
# Commands
# ============================================================
@bot.command()
async def start(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ Sirf Admin ye command use kar sakte hai.")
    
    global is_running, checked_count, valid_count, start_time
    if is_running: return await ctx.send("⚠️ Checker already running hai!")

    is_running = True
    checked_count, valid_count = 0, 0
    start_time = time.time()
    
    await ctx.send(f"🚀 Checker Shuru! `{PREFIX}stop` se band karein.")
    asyncio.create_task(run_checker(ctx))

@bot.command()
async def stop(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ Sirf Admin ye command use kar sakte hai.")

    global is_running, start_time
    if not is_running: return await ctx.send("⚠️ Checker band hai.")

    is_running = False
    elapsed = int(time.time() - start_time)
    await ctx.send(f"🛑 Stopped. Checked: `{checked_count}` | Valid: `{valid_count}` | Time: `{elapsed}s`")

@bot.command()
async def status(ctx):
    if not is_running: return await ctx.send("⚠️ Checker chal nahi raha.")
    elapsed = int(time.time() - start_time)
    speed = checked_count / max(elapsed, 1)
    await ctx.send(f"📊 Running | Checked: `{checked_count}` | Valid: `{valid_count}` | Speed: `{speed:.1f}/s`")

@bot.command()
async def check(ctx, code: str):
    result = check_gift_code(code)
    if result is True:
        await ctx.send(f"🎉 Valid: `{code}`")
    elif result == "rate_limited":
        await ctx.send("⏳ Rate Limited")
    else:
        await ctx.send("❌ Invalid")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="Commands", color=discord.Color.blue())
    e.add_field(name=f"{PREFIX}start", value="Start checker", inline=False)
    e.add_field(name=f"{PREFIX}stop", value="Stop checker", inline=False)
    e.add_field(name=f"{PREFIX}status", value="Check status", inline=False)
    e.add_field(name=f"{PREFIX}check <code>", value="Check single code", inline=False)
    await ctx.send(embed=e)

# ============================================================
# Tasks & Events
# ============================================================
async def run_checker(ctx):
    global is_running, checked_count, valid_count
    while is_running:
        try:
            code = generate_random_string()
            res = check_gift_code(code)
            checked_count += 1

            if res is True:
                valid_count += 1
                embed = discord.Embed(title="✅ VALID CODE", description=f"```\n{code}\n```", color=discord.Color.green())
                await ctx.send(embed=embed)
                send_webhook(embed)
                with open("valid_codes.txt", "a") as f:
                    f.write(f"{code}\n")
            
            elif res == "rate_limited":
                await asyncio.sleep(10)
            elif res == "error":
                await asyncio.sleep(5)
            
            await asyncio.sleep(1)
        except Exception as e:
            print(f"Error: {e}")
            await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    activity_type = discord.ActivityType.watching
    await bot.change_presence(status=discord.Status(STATUS), activity=discord.Activity(type=activity_type, name=ACTIVITY))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
