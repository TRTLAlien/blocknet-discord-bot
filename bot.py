import os
import re
import discord
from discord.ext import commands
import httpx
from bs4 import BeautifulSoup

EXPLORER_URL = "https://explorer.blocknetcrypto.com/"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


async def fetch_stats() -> dict:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(EXPLORER_URL)
        r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    stats = {}

    for div in soup.select("div.stat"):
        value = div.select_one("div.stat-v")
        key = div.select_one("div.stat-k")
        if value and key:
            stats[key.get_text(strip=True)] = value.get_text(strip=True)

    # Recent blocks table: Height, Hash (link), Age, Txs
    blocks = []
    rows = soup.select("table tr")[1:]  # skip header
    for row in rows[:5]:
        cols = row.select("td")
        if len(cols) >= 3:
            height = cols[0].get_text(strip=True)
            age = cols[1].get_text(strip=True)
            txs = cols[2].get_text(strip=True)
            blocks.append((height, age, txs))

    stats["_blocks"] = blocks
    return stats


@bot.command(name="stats")
async def stats_command(ctx):
    async with ctx.typing():
        try:
            data = await fetch_stats()
        except Exception as e:
            await ctx.send(f"Failed to fetch stats: {e}")
            return

    blocks = data.pop("_blocks", [])

    embed = discord.Embed(
        title="Blocknet Network Stats",
        url=EXPLORER_URL,
        color=0xAAFF00,
    )

    field_map = {
        "Block Height": "Block Height",
        "Peers": "Peers",
        "Difficulty": "Difficulty",
        "Network Hashrate": "Network Hashrate",
        "Coins Emitted": "Coins Emitted",
        "Remaining (pre-tail)": "Remaining (pre-tail)",
        "Emission Progress": "Emission Progress",
    }

    for key, label in field_map.items():
        if key in data:
            embed.add_field(name=label, value=data[key], inline=True)

    if blocks:
        lines = [f"`{h}` — {age} — {txs} tx" for h, age, txs in blocks]
        embed.add_field(name="Recent Blocks", value="\n".join(lines), inline=False)

    embed.set_footer(text="explorer.blocknetcrypto.com")
    await ctx.send(embed=embed)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user} (id: {bot.user.id})")


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("Set DISCORD_TOKEN environment variable")
    bot.run(token)
