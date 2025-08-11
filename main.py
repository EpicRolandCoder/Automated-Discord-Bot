import os
import asyncio
import logging
import aiohttp
import discord
from discord.ext import commands

#helper functions
from bom import weather as bom_weather
from compass import get_compass_classes
from xkcd import get_random_xkcd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord_bot")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=",", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Bot is online as {bot.user} (id: {bot.user.id})")


async def fetch_reddit_urls(subreddit: str, limit: int = 5):
    """
    Asynchronously fetches top posts (old.reddit JSON) and returns a list of post URLs (image/link).
    """
    url = f"https://old.reddit.com/r/{subreddit}.json"
    headers = {"User-Agent": "DiscordBot (by /u/yourusername)"}
    results = []
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Reddit returned status {resp.status}")
                data = await resp.json()
        except Exception as e:
            raise RuntimeError(f"Failed to fetch subreddit '{subreddit}': {e}")

    for child in data.get("data", {}).get("children", [])[:limit]:
        post = child.get("data", {})
        # url_overridden_by_dest often contains image/link
        link = post.get("url_overridden_by_dest") or post.get("url")
        if link:
            results.append({"title": post.get("title"), "url": link})
    return results


@bot.command(name="helpme")
async def helpme(ctx):
    await ctx.send(
        "I can fetch memes from subreddits and a few other things.\n"
        "Commands:\n"
        ",meme — top posts from r/memes\n"
        ",dankmeme — top posts from r/dankmemes\n"
        ",shitpost — top posts from r/shitposting\n"
        ",subreddit <name> [limit] — fetch posts from any subreddit (limit default 5)\n"
        ",weather <city> <stateAcronym> — BOM 7-day forecast (e.g. ,weather melbourne vic)\n"
        ",classes <studentCode> <password> — fetch Compass classes (runs selenium so may take a few seconds)\n"
        ",xkcd — returns a random XKCD comic\n"
    )


@bot.command(name="meme")
async def meme(ctx, limit: int = 5):
    try:
        posts = await fetch_reddit_urls("memes", limit=limit)
    except Exception as e:
        await ctx.send(f"Error fetching memes: {e}")
        return
    if not posts:
        await ctx.send("No posts found.")
        return
    for p in posts:
        # If the URL points to an image, embed it; otherwise just send the link/title
        embed = discord.Embed(title=p["title"][:256])
        embed.description = p["url"]
        #if URL is an image it will preview
        embed.set_image(url=p["url"])
        await ctx.send(embed=embed)


@bot.command(name="dankmeme")
async def dankmeme(ctx, limit: int = 5):
    try:
        posts = await fetch_reddit_urls("dankmemes", limit=limit)
    except Exception as e:
        await ctx.send(f"Error fetching dankmemes: {e}")
        return
    if not posts:
        await ctx.send("No posts found.")
        return
    for p in posts:
        embed = discord.Embed(title=p["title"][:256])
        embed.description = p["url"]
        embed.set_image(url=p["url"])
        await ctx.send(embed=embed)


@bot.command(name="shitpost")
async def shitpost(ctx, limit: int = 5):
    try:
        posts = await fetch_reddit_urls("shitposting", limit=limit)
    except Exception as e:
        await ctx.send(f"Error fetching shitposting: {e}")
        return
    if not posts:
        await ctx.send("No posts found.")
        return
    for p in posts:
        embed = discord.Embed(title=p["title"][:256])
        embed.description = p["url"]
        embed.set_image(url=p["url"])
        await ctx.send(embed=embed)


@bot.command(name="subreddit")
async def subreddit(ctx, name: str = None, limit: int = 5):
    if not name:
        await ctx.send("Usage: ,subreddit <name> [limit]")
        return
    try:
        posts = await fetch_reddit_urls(name, limit=limit)
    except Exception as e:
        await ctx.send(f"Error fetching subreddit '{name}': {e}")
        return
    if not posts:
        await ctx.send(f"No posts found for r/{name}.")
        return
    for p in posts:
        embed = discord.Embed(title=p["title"][:256])
        embed.description = p["url"]
        embed.set_image(url=p["url"])
        await ctx.send(embed=embed)


@bot.command(name="insult")
async def insult(ctx, *, task: str = None):
    if not task:
        await ctx.send("Usage: ,insult <target>")
        return
    if task.lower() == "roland":
        await ctx.send("stfu")
        return
    await ctx.send(f"{task} is a bum")


@bot.command(name="weather")
async def weather_cmd(ctx, city: str = None, state: str = None):
    """
    Example: ,weather melbourne vic
    """
    if not city or not state:
        await ctx.send("Usage: ,weather <city> <stateAcronym>  (e.g. ,weather melbourne vic)")
        return
    await ctx.send(f"Fetching BOM forecast for {city.capitalize()}, {state.upper()} — this may take a few seconds...")
    try:
        # bom_weather is blocking (requests + BeautifulSoup), run in thread to avoid blocking event loop
        forecast = await asyncio.to_thread(bom_weather, city, state, True, True)
    except Exception as e:
        await ctx.send(f"Error running BOM scraper: {e}")
        return

    # forecast is a 2D list: [ [min, max, summary], ... ] (depending on process=True)
    try:
        day0 = forecast[0]
        min_t, max_t, summary = day0[0], day0[1], day0[2]
        # ensure they are strings
        min_t = min_t or "N/A"
        max_t = max_t or "N/A"
        summary = summary or "N/A"
        await ctx.send(f"Today in {city.capitalize()} — min: {min_t}, max: {max_t}\n{summary}")
    except Exception as e:
        await ctx.send(f"Unexpected forecast format: {e}")


@bot.command(name="classes")
async def classes_cmd(ctx, student_code: str = None, password: str = None):
    """
    Usage: ,classes <studentCode> <password>
    WARNING: this will run a Selenium webdriver and requires correct driver in PATH (geckodriver/chromedriver).
    """
    if not student_code or not password:
        await ctx.send("Usage: ,classes <studentCode> <password>")
        return
    await ctx.send("Logging in to Compass — this will run a Selenium browser in the background and can take ~10s.")
    try:
        classes = await asyncio.to_thread(get_compass_classes, student_code, password)
    except Exception as e:
        await ctx.send(f"Error fetching classes: {e}")
        return
    if not classes:
        await ctx.send("No classes found or login failed.")
        return
    # send as a formatted message
    await ctx.send("Your classes:\n" + "\n".join(classes))


@bot.command(name="xkcd")
async def xkcd_cmd(ctx):
    """
    Returns a random XKCD comic (image, title and alt text).
    """
    await ctx.send("Fetching a random XKCD...")
    try:
        comic = await asyncio.to_thread(get_random_xkcd)
    except Exception as e:
        await ctx.send(f"Error fetching XKCD: {e}")
        return
    if not comic:
        await ctx.send("Could not fetch a comic.")
        return
    embed = discord.Embed(title=f"{comic.get('num')}: {comic.get('title')}", description=comic.get("alt")[:2048])
    img_url = comic.get("img")
    embed.set_image(url=img_url)
    embed.url = f"https://xkcd.com/{comic.get('num')}/"
    await ctx.send(embed=embed)


if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN") or os.environ.get("Token")
    if not token:
        logger.error("DISCORD_TOKEN (or Token) environment variable not set. Exiting.")
        raise SystemExit("Missing DISCORD_TOKEN environment variable.")
    bot.run(token)
