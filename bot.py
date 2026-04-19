import discord
from discord.ext import commands
import aiohttp
import asyncio
import string
import random
import os
import time
from dotenv import load_dotenv

# ============================================================
# ENVIRONMENT VARIABLES (Railway se config hoga)
# ============================================================
load_dotenv()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
USER_TOKEN = os.environ.get("DISCORD_USER_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")
ADMIN_ID = os.environ.get("ADMIN_ID")
PREFIX = os.environ.get("PREFIX", "!")
STATUS = os.environ.get("STATUS", "online")
ACTIVITY = os.environ.get("ACTIVITY", "Promo Hunting")

# Code Settings (Promo codes usually 16 to 24 characters)
CODE_MIN_LENGTH = 16
CODE_MAX_LENGTH = 24

# Safety Checks
if not BOT_TOKEN: exit("BOT_TOKEN Missing")
if not USER_TOKEN: print("Warning: USER_TOKEN missing")

if ADMIN_ID:
    try: ADMIN_ID = int(ADMIN_ID)
    except: ADMIN_ID = None

API_URL = "https://discord.com/api/v9/entitlements/gift-codes/{}"

# ============================================================
# Bot Setup
# ============================================================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

# Global Variables
is_running = False
checked_count = 0
valid_count = 0
start_time = None

# ============================================================
# GENERATOR & CHECKER FUNCTIONS
# ============================================================
def generate_promo_code():
    # Promo codes usually A-Z, 0-9
    chars = string.ascii_uppercase + string.digits
    length = random.randint(CODE_MIN_LENGTH, CODE_MAX_LENGTH)
    return ''.join(random.choice(chars) for _ in range(length))

async def check_code_async(session, code):
    url = API_URL.format(code)
    headers = {
        "Authorization": USER_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        async with session.get(url, headers=headers, timeout=10) as resp:
            if resp.status == 200:
                return "valid"
            elif resp.status == 429:
                return "rate_limited"
            else:
                return "invalid"
    except:
        return "error"

async def send_webhook(embed):
    if WEBHOOK_URL:
        try:
            async with aiohttp.ClientSession() as session:
                webhook = discord.Webhook.from_url(WEBHOOK_URL, session=session)
                await webhook.send(embed=embed)
        except:
            pass

# ============================================================
# COMMANDS
# ============================================================
@bot.command()
async def start(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ Sirf Admin start kar sakta hai.")

    global is_running, checked_count, valid_count, start_time
    if is_running: return await ctx.send("⚠️ Checker already chal raha hai!")

    is_running = True
    checked_count, valid_count = 0, 0
    start_time = time.time()
    
    embed = discord.Embed(title="🚀 Promo Checker Started", description=f"`{PREFIX}stop` se band karo.\nSearching for Promos...", color=discord.Color.green())
    await ctx.send(embed=embed)
    
    # Async Task Start
    asyncio.create_task(run_checker_loop(ctx))

@bot.command()
async def stop(ctx):
    if ADMIN_ID and ctx.author.id != ADMIN_ID:
        return await ctx.send("❌ Sirf Admin stop kar sakta hai.")

    global is_running, start_time
    if not is_running: return await ctx.send("⚠️ Checker band hai.")

    is_running = False
    elapsed = int(time.time() - start_time)
    
    embed = discord.Embed(title="🛑 Checker Stopped", color=discord.Color.red())
    embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Time", value=f"`{elapsed}s`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def status(ctx):
    if not is_running: return await ctx.send("⚠️ Checker band hai.")
    
    elapsed = int(time.time() - start_time)
    # Speed approximation
    speed = checked_count / max(elapsed, 1) if elapsed > 0 else 0
    
    embed = discord.Embed(title="📊 Promo Status", color=discord.Color.blue())
    embed.add_field(name="Checked", value=f"`{checked_count}`", inline=True)
    embed.add_field(name="Valid", value=f"`{valid_count}`", inline=True)
    embed.add_field(name="Speed", value=f"`{speed:.2f}/s`", inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def check(ctx, code: str):
    await ctx.send(f"🔍 Checking single code: `{code}`...")
    
    async with aiohttp.ClientSession() as session:
        res = await check_code_async(session, code.strip())
        
    if res == "valid":
        await ctx.send(f"🎉 **VALID PROMO**: `{code}`")
    elif res == "rate_limited":
        await ctx.send("⏳ Rate Limited")
    else:
        await ctx.send("❌ Invalid")

@bot.command()
async def help(ctx):
    e = discord.Embed(title="Promo Bot Commands", color=discord.Color.purple())
    e.add_field(name=f"{PREFIX}start", value="Start Promo Hunter", inline=False)
    e.add_field(name=f"{PREFIX}stop", value="Stop Checker", inline=False)
    e.add_field(name=f"{PREFIX}status", value="Live Stats", inline=False)
    e.add_field(name=f"{PREFIX}check <code>", value="Manual Check", inline=False)
    await ctx.send(embed=e)

# ============================================================
# MAIN ASYNC LOOP
# ============================================================
async def run_checker_loop(ctx):
    global is_running, checked_count, valid_count
    
    # Concurrency level (Ek saath kitne check karein)
    # Railway ke liye 30-50 safe hai. Zyada karoge toh 429 aayega.
    CONCURRENT_REQUESTS = 100000
    
    connector = aiohttp.TCPConnector(limit=0, ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        while is_running:
            try:
                # Create a batch of tasks
                tasks = []
                for _ in range(CONCURRENT_REQUESTS):
                    code = generate_promo_code()
                    tasks.append(check_code_async(session, code))
                
                # Run all checks at once
                results = await asyncio.gather(*tasks)
                
                # Process results
                batch_checked = len(results)
                checked_count += batch_checked
                
                # Find hits in this batch
                for i, res in enumerate(results):
                    if res == "valid":
                        valid_count += 1
                        # We need to regenerate the code for display or store it, 
                        # but for speed in this demo, we just count. 
                        # For exact code matching, we should refactor to return (code, status).
                        # *Optimized version below:* Let's just send a generic hit alert or modify function.
                        # NOTE: In this loop we lose the specific code string. 
                        # To fix this accurately, we would modify tasks to store (code, result).
                        pass 

                # NOTE: To display exact code, we modify the loop slightly below:
                # Let's re-write the loop part inside 'while' to capture valid codes:
                
                batch_valid_codes = []
                for _ in range(CONCURRENT_REQUESTS):
                    code = generate_promo_code()
                    status = await check_code_async(session, code)
                    checked_count += 1
                    
                    if status == "valid":
                        valid_count += 1
                        batch_valid_codes.append(code)
                        full_link = f"https://discord.gift/{code}"
                        
                        # Send Notification
                        embed = discord.Embed(title="🎉 PROMO CODE FOUND! 🎉", description=f"```\n{full_link}\n```", color=discord.Color.green())
                        embed.set_footer(text="Railway Promo Hunter")
                        await ctx.send(embed=embed)
                        await send_webhook(embed)
                        
                        # Save to file
                        with open("promo_hits.txt", "a") as f:
                            f.write(f"{full_link}\n")
                    
                    elif status == "rate_limited":
                        print("[WARN] Rate Limited detected, pausing...")
                        await asyncio.sleep(10)
                    
                    # Small delay to be nice to the CPU
                    await asyncio.sleep(0.05)

            except Exception as e:
                print(f"Error in loop: {e}")
                await asyncio.sleep(5)

@bot.event
async def on_ready():
    print(f"Bot Ready: {bot.user}")
    await bot.change_presence(status=discord.Status(STATUS), activity=discord.Activity(type=discord.ActivityType.watching, name=ACTIVITY))

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
