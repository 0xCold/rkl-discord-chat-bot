from os.path import exists
import discord
from discord.ext import commands
from googleapiclient.discovery import build
from util import Globals, Util, OpenSeaUtil, KongUtil
from time import time, sleep


def initializeBot():
    Util.log("Initializing Discord bot with token: " + Globals.DISCORD_TOKEN)
    bot = commands.Bot(command_prefix="!", case_insensitive=True)
    registerCommands(bot)
    bot.run(Globals.DISCORD_TOKEN)
    return bot


# Include chat commands within this function to ensure they are registered on startup
def registerCommands(bot):

    # == !IAmKong ====================================================================
    @bot.command(
        help="I am Kong!", 
        brief="I am Kong!"
    )
    async def iamkong(ctx, *_args):
        gif = discord.File(Globals.MEMES_PATH + "iamkong.gif")
        await ctx.channel.send(file=gif)

    # == !Yes =========================================================================
    @bot.command(
        help="Yes.", 
        brief="Yes."
    )
    async def yes(ctx, *_args):
        image = discord.File(Globals.MEMES_PATH + "yes.png")
        await ctx.channel.send(file=image)

    # == !Praise =======================================================================
    @bot.command(
        help="Give thanks to the RKL team members.", 
        brief="name (string): Name of the team member to praise"
    )
    async def praise(ctx, *args):
        name = args[0]
        if name not in Globals.STAFF:
            name = "team"
            
        gif = Globals.STAFF_PATH + Globals.STAFF[name]
        await ctx.channel.send(file=discord.File(gif))

    # == !Image =========================================================================
    @bot.command(
        help="Get the image of a Rumble Kong by id.", 
        brief="id (number): Token ID of the Kong to display"
    )
    async def image(ctx, *args):
        id = args[0]

        imageString = "image_url"
        if len(args) > 1:
            if args[1] == "hd":
                imageString = "image_original_url"

        params = {
            "token_ids": id,
            "collection_slug": "rumble-kong-league"
        }
        kongUrl = OpenSeaUtil.fetchOpenSeaAsset(Globals.OPENSEA_ASSETS_URL, params)["assets"][0][imageString]
        await ctx.channel.send(str(kongUrl))

    # == !Jersey ===========================================================================
    @bot.command(
        help="Rep your team's jersey on your Kong.", 
        brief="id (number): Token ID of the Kong to display, team (string): Name of the team to use the jersey from"
    )
    async def jersey(ctx, *args):
        id = args[0]
        teamJersey = args[1]

        kong = KongUtil.drawNakedKong(int(id))
        jerseyKong = KongUtil.applyDrip(kong, teamJersey, True)
        jerseyKong.save(Globals.TMP_PATH + "testkong.png")

        image = discord.File(Globals.TMP_PATH + "testkong.png")
        await ctx.channel.send(file=image)

    # == !Drip =============================================================================
    @bot.command(
        help="Add some drip to your Kong.", 
        brief="id (number): Token ID of the Kong to display, team (string): Name of the drip to apply"
    )
    async def drip(ctx, *args):
        id = args[0]
        dripType = args[1]

        kong = KongUtil.drawNakedKong(int(id))
        drippedKong = KongUtil.applyDrip(kong, dripType, False)
        drippedKong.save(Globals.TMP_PATH + "testkong.png")

        image = discord.File(Globals.TMP_PATH + "testkong.png")
        await ctx.channel.send(file=image)

    # == !Vote =============================================================================
    @bot.command(
        help="Vote for your favorite jersey", 
        brief="team (string): Name of the team who's jersey you are voting for"
    )
    async def vote(ctx, *_args):
        rows = [
            ctx.message.author.name,
            ctx.message.author.id,
            ctx.message.content,
            Util.getFormattedDatetime(),
        ]

        credentials = Util.readServiceAccountCredentials(Globals.SERVICE_ACCOUNT_KEY_FILE)
        service = build("sheets", "v4", credentials=credentials)

        service.spreadsheets().values().append(
            spreadsheetId=Globals.VOTING_SPREADSHEET_ID,
            range="Sheet1!A:Z",
            body={"majorDimension": "ROWS", "values": [rows]},
            valueInputOption="USER_ENTERED",
        ).execute()
        await ctx.channel.send("Your Vote has been logged")

    # == !Floor ============================================================================
    @bot.command(
        help="Get statistics about the floor price of RKL collections.", 
        brief="collection (string):"
    )
    async def floor(ctx, *args):
        collection = args[0]

        filter = ""
        if len(args) > 1:
            filter = args[1].title()
        if collection == "sneakers":
            filter = "Sneakers"
        
        listings = Util.readJSON(Globals.CACHE_PATH + collection + "-asset-cache.json")["assets"]
        embed = OpenSeaUtil.constructFloorStatsEmbed(collection, listings, filter)
        await ctx.channel.send(embed=embed)


if __name__ == "__main__":

    if Globals.LOG:
        Util.initializeLog()
    
    success = True
    for collection in Globals.COLLECTIONS:
        if exists(Globals.CACHE_PATH + collection + "-asset-cache.json"):
            Util.log("Skipping caching assets for " + collection + " because file already exists")
            
        else:
            success = OpenSeaUtil.initializeAssetCache(collection)
            if success == False:
                break

    if success:
        bot = initializeBot()

        #while True:
        #    OpenSeaUtil.updateAssetCache(collection)
        #    sleep(Globals.CACHE_UPDATE_RATE)