import discord
from discord.ext import commands
import json
from datetime import date
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------- Helper functions ----------
def add_user(id, name):
    return supabase.table("users").upsert({"id": id, "name": name}).execute()

def get_user(id):
    return supabase.table("users").select('*').eq("id",id).execute()

def get_user_records(id):
    records = supabase.table("records")\
    .select("*")\
    .eq("user_id",id)\
    .execute()

def get_user_daily_points(id):
    today_str = date.today().isoformat()

    points =  supabase.table("records")\
    .select("points")\
    .eq("user_id", id)\
    .eq("date",today_str)\
    .execute().data

    total_points = 0
    for pts in points:
        total_points += pts['points']
    return total_points

def get_daily_leaderboard():
    today_str = date.today().isoformat()
    return supabase.rpc("daily_leaderboard", {"today":today_str}).execute().data

def get_all_time_leaderboard():
    return supabase.rpc("alltime_leaderboard").execute().data

def add_record(id, oz, points, date):
    supabase.table("records")\
    .insert({"user_id": id, "oz":oz, "points": points, "date": date})\
    .execute()

def add_goal(id, goal_oz, goal_time):
    supabase.table("users").update({"goal_oz":goal_oz, "goal_time": goal_time})\
    .eq("id",id)\
    .execute()

def get_points(oz):
    if oz <-120: return -2
    if oz <-90: return -1.5
    if oz <-60: return -1
    if oz <-24: return -0.5
    if oz < 24: return 0
    if oz < 60: return 0.5
    if oz < 90: return 1
    if oz < 120: return 1.5
    return 2

# ---------- Bot Commands ----------
@bot.event
async def on_ready():
    print(f'Bot connected as {bot.user}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    content = message.content.strip().lower()

    user = get_user(message.author.id)
    if user.count is None:
        user = add_user(message.author.id, message.author.name)
    print(f"USER: {user}")
    
    response = ""

    # Command: help
    print(content)
    if content in ("!help", "help"):
        response = (
            "**Water Tracker Commands:**\n"
            "- `!log` → send a number (e.g., 60) to log water in oz\n"
            "- `!today` → view today's points\n"
            "- `!leaderboard` → view top points\n"
            "- `!help` → show this message"
        )

    # Command: leaderboard
    elif content in ("!leaderboard", "leaderboard"):
        daily_leaderboard = get_daily_leaderboard()
        all_leaderboard = get_all_time_leaderboard()
        print(f"daily: {daily_leaderboard}")
        print(f"all: {all_leaderboard}")
        if daily_leaderboard:
            lines = [f"{i+1}. {u['user_id']}: {u['total_points']}" for i, u in enumerate(daily_leaderboard[:10])]
            res1 = "**🏆 Daily Leaderboard:**\n" + "\n".join(lines)
        else:
            res1 = "**🏆 Daily Leaderboard:**\nNo entries so far today...\n"

        if all_leaderboard:
            lines = [f"{i+1}. {u['user_id']}: {u['total_points']}" for i, u in enumerate(all_leaderboard[:10])]
            res2 = "\n**🏆 All Time Leaderboard:**\n" + "\n".join(lines)
        else:
            res2 = "\n**🏆 All Time Leaderboard:**\nNo entries at all."
        response = res1 + res2

    # Command: today
    elif content in ("!today", "today"):
        todays_points = get_user_daily_points(message.author.name)
        response = f"💧 {message.author.name}, today you have {todays_points} points."

    # Number input → log water
    elif "log" in content:
        print("helloooo")
        cmd,oz = content.split()
        print(cmd)
        print(oz)
        oz = float(oz)
        pts = get_points(oz)
        add_record(message.author.name, oz, pts, date.today().isoformat())
        response = f"Added {oz} oz → +{pts} points!"

    await message.channel.send(response)

# Run bot
bot.run(TOKEN)

# Connect to port for Render Deployment
class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_dummy_server():
    server = HTTPServer(("0.0.0.0", 10000), DummyHandler)
    server.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
