import discord
import aiohttp
import asyncio
from bs4 import BeautifulSoup
import os
from keep_alive import keep_alive

TOKEN = os.getenv("TOKEN")

UPDATE_USERS = {
    1336476202856349726,  # Replace with real user IDs
    1191329208350277662,
    408341332621262849,
    974028296314564628,
    933828014037426237,
    791617716342882324,
    684795332101799938,
    789406964709851166,
    575367541300396032,
    1262929588812648505,
    629954774829105153,


}

ONLINE_USER_ID = 1336476202856349726

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

client = discord.Client(intents=intents)

last_updates = {}
welcomed_users = set()

UPDATE_PAGES = {
    "CrossFire West": "https://crossfirefps.fandom.com/wiki/Template:Updates#WE",
    "CrossFire China": "https://crossfirefps.fandom.com/wiki/Template:Updates#CN",
    "CrossFire Vietnam": "https://crossfirefps.fandom.com/wiki/Template:Updates#VN",
    "CrossFire Philippines": "https://crossfirefps.fandom.com/wiki/Template:Updates#PH",
    "CrossFire Brazil": "https://crossfirefps.fandom.com/wiki/Template:Updates#BR",
    "Events": "https://crossfire.z8games.com/events.html"
}

def categorize_lines(lines):
    categories = {
        "Maps": [],
        "Weapons": [],
        "Skins": [],
        "VIP": [],
        "Infinity": [],
        "New Maps": [],
        "Others": []
    }
    for line in lines:
        l = line.lower()
        if any(k in l for k in ["map", "maps"]):
            categories["Maps"].append(line)
        elif any(k in l for k in ["weapon", "gun", "rifle", "firearm"]):
            categories["Weapons"].append(line)
        elif any(k in l for k in ["skin", "character"]):
            categories["Skins"].append(line)
        elif "vip" in l:
            categories["VIP"].append(line)
        elif "infinity" in l:
            categories["Infinity"].append(line)
        elif "new map" in l or "new maps" in l:
            categories["New Maps"].append(line)
        else:
            categories["Others"].append(line)
    return categories

async def fetch_wiki_update(name, url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")
                content_div = soup.find("div", class_="mw-parser-output")
                if not content_div:
                    print(f"No content div found for {name}")
                    return [], []

                lines = []
                images = []

                # امنع استدعاء find_all على None
                elements = content_div.find_all(['p', 'li', 'div', 'ul'])
                if not elements:
                    print(f"No elements found in content div for {name}")
                    return [], []

                for elem in elements:
                    text = elem.get_text(separator="\n").strip()
                    if text:
                        lines.extend([line.strip() for line in text.splitlines() if line.strip()])

                    imgs = elem.find_all('img')
                    if imgs:
                        for img in imgs:
                            src = img.get('src')
                            if src and src.startswith("//"):
                                src = "https:" + src
                            if src and src not in images:
                                images.append(src)

                return lines, images

        except Exception as e:
            print(f"Error fetching wiki update {name}: {e}")
            return [], []

async def fetch_events():
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(UPDATE_PAGES["Events"]) as resp:
                html = await resp.text()
                soup = BeautifulSoup(html, "html.parser")

                events_data = []

                container = soup.find("div", class_="events-list")
                if not container:
                    print("No events container found.")
                    return []

                event_divs = container.find_all("div", recursive=False)
                if not event_divs:
                    print("No event divs found.")
                    return []

                for event_div in event_divs:
                    title_tag = event_div.find("h3")
                    title = title_tag.get_text(strip=True) if title_tag else "New Event"

                    img_tag = event_div.find("img")
                    img_url = img_tag['src'] if img_tag else None
                    if img_url and img_url.startswith("//"):
                        img_url = "https:" + img_url

                    desc_tag = event_div.find("p")
                    description = desc_tag.get_text(strip=True) if desc_tag else "No description available."

                    events_data.append({
                        "title": title,
                        "image": img_url,
                        "description": description
                    })
                return events_data
        except Exception as e:
            print(f"Error fetching events page: {e}")
            return []

async def send_welcome_message(user):
    try:
        await user.send(
            "👋 Welcome! The CrossFire Update Bot is now online and will send updates when available."
        )
        print(f"Sent welcome message to {user.id}")
    except Exception as e:
        print(f"Failed to send welcome message to {user.id}: {e}")

async def check_updates():
    await client.wait_until_ready()
    for user_id in UPDATE_USERS:
        if user_id not in welcomed_users:
            user = await client.fetch_user(user_id)
            await send_welcome_message(user)
            welcomed_users.add(user_id)

    while not client.is_closed():
        for name, url in UPDATE_PAGES.items():
            if name == "Events":
                events = await fetch_events()
                if not events:
                    print("No new events found.")
                    await asyncio.sleep(180)
                    continue

                current_snapshot = "".join([e['title'] + e['description'] for e in events])
                if last_updates.get(name) == current_snapshot:
                    print("No new events update.")
                    await asyncio.sleep(180)
                    continue

                last_updates[name] = current_snapshot

                for user_id in UPDATE_USERS:
                    try:
                        user = await client.fetch_user(user_id)
                        for event in events:
                            embed = discord.Embed(
                                title=event['title'],
                                description=event['description'],
                                color=discord.Color.blue()
                            )
                            if event['image']:
                                embed.set_image(url=event['image'])
                            await user.send(embed=embed)
                        print(f"Sent events updates to {user_id}")
                    except Exception as e:
                        print(f"Failed to send events update to {user_id}: {e}")

            else:
                lines, images = await fetch_wiki_update(name, url)
                if not lines:
                    print(f"No content found for {name}")
                    await asyncio.sleep(180)
                    continue

                current_snapshot = "".join(lines)
                if last_updates.get(name) == current_snapshot:
                    print(f"No new update for {name}")
                    await asyncio.sleep(180)
                    continue

                last_updates[name] = current_snapshot
                categories = categorize_lines(lines)

                for user_id in UPDATE_USERS:
                    try:
                        user = await client.fetch_user(user_id)
                        content = f"📢 New Update for {name}\n\n"
                        for cat, items in categories.items():
                            if items:
                                content += f"{cat}:\n"
                                for i in items:
                                    content += f"- {i}\n"
                                content += "\n"
                        # Mention user
                        content = f"<@{user_id}>\n" + content

                        await user.send(content)
                        for img_url in images:
                            embed = discord.Embed()
                            embed.set_image(url=img_url)
                            await user.send(embed=embed)
                        print(f"Sent update to {user_id} for {name}")
                    except Exception as e:
                        print(f"Failed to send update to {user_id} for {name}: {e}")

        await asyncio.sleep(180)

async def send_online_message():
    await client.wait_until_ready()
    while not client.is_closed():
        try:
            user = await client.fetch_user(ONLINE_USER_ID)
            await user.send("✅ Bot is online and working.")
            print(f"Sent online message to {ONLINE_USER_ID}")
        except Exception as e:
            print(f"Failed to send online message to {ONLINE_USER_ID}: {e}")
        await asyncio.sleep(60)

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    client.loop.create_task(check_updates())
    client.loop.create_task(send_online_message())

# Keep_alive with debug=False to hide Flask warning
def run_flask():
    from flask import Flask
    from threading import Thread

    app = Flask('')

    @app.route('/')
    def home():
        return "Bot is alive!"

    def run():
        app.run(host='0.0.0.0', port=8080, debug=False, use_reloader=False)

    t = Thread(target=run)
    t.start()

# Start the flask server to keep Replit awake
run_flask()

client.run(TOKEN)