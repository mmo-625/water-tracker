import discord
from discord.ext import commands
import json
from datetime import date
import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

url = os.getenv('SUPABASE_URL')
key = os.getenv('SUPABASE_KEY')
supabase: Client = create_client(url, key)



DB_FILE = "data.json"

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

def load_db():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"users": []}

def save_db(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

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

#def get_user(data, user_id, username):
#    user = next((u for u in data["users"] if u["id"] == user_id), None)
#    if not user:
#        user = {"id": user_id, "name": username, "records": []}
#        data["users"].append(user)
#    return user

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

    #data = load_db()
    #user = get_user(data, str(message.author.id), message.author.name)

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
        #leaderboard = sorted(
        #    [{"name": u["name"], "points": sum(r["points"] for r in u["records"])}
        #     for u in data["users"]],
        #    key=lambda x: x["points"],
        #    reverse=True
        #)
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
            res2 = "**🏆 All Time Leaderboard:**\n" + "\n".join(lines)
        else:
            res2 = "**🏆 All Time Leaderboard:**\nNo entries at all."
        response = res1 + res2
        #if leaderboard:
        #    lines = [f"{i+1}. {u['name']}: {u['points']}" for i, u in enumerate(leaderboard[:10])]
        #    response = "**🏆 Leaderboard:**\n" + "\n".join(lines)
        #else:
        #    response = "No entries yet."

    # Command: today
    elif content in ("!today", "today"):
        #today_str = date.today().isoformat()
        #today_points = sum(r["points"] for r in user["records"] if r["date"] == today_str)
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

    #else:
    #    try:
    #        oz = float(content)
    #        pts = get_points(oz)
    #        user["records"].append({"date": date.today().isoformat(), "oz": oz, "points": pts})
    #        save_db(data)
    #         response = f"Added {oz} oz → +{pts} points!"
    #    except ValueError:
    #        response = "Unrecognized command. Type `!help` for options."

    await message.channel.send(response)

# Run bot
bot.run(TOKEN)
