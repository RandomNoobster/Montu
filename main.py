from dotenv import load_dotenv
import keep_alive
import pymongo
import os
import ssl
import discord
from discord.ext import commands
intents = discord.Intents.default()
intents.members = True
load_dotenv()

client = pymongo.MongoClient(os.getenv("pymongolink"), ssl_cert_reqs=ssl.CERT_NONE)
version = os.getenv("version")
mongo = client[str(version)]

bot = commands.Bot(command_prefix='$', intents=intents)

@bot.event
async def on_ready():
    print('Bot is ready')
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.watching, name="your wars"))
    print('We have logged in as {0.user}'.format(bot))

@bot.event
async def on_application_command_error(ctx: discord.ApplicationContext, error):
    debug_channel = bot.get_channel(949609712557637662)
    print(error)
    await ctx.send("Oh no! An unknown error occurred! Contact RandomNoobster#0093, and he might be able to help you out.")
    await debug_channel.send(f'**Exception raised!**\nAuthor: {ctx.author}\nServer: {ctx.guild}\nCommand: {ctx.command}\n\nError:```{error}```')

@bot.slash_command(name="ping", description="Pong!")
async def ping(ctx: discord.ApplicationContext):
    await ctx.respond(f'Pong! {round(bot.latency * 1000)}ms')


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

keep_alive.keep_alive()
bot.run(os.getenv("bot_token"))