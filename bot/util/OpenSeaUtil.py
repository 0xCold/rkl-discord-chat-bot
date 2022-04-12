from sys import maxsize
from time import time, sleep
from discord import Embed, Color
from requests import request
from util import Globals, Util

def constructHeaders():
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:47.0) Gecko/20100101 Firefox/47.0",
        "Accept": "application/json",
        "X-API-KEY": Globals.OPENSEA_API_KEY
    }

def fetchOpenSeaAsset(url, params):
    return (request(
        "GET", url, headers=constructHeaders(), params=params
    )).json()


def initializeAssetCache(collection, restTime=Globals.DEFAULT_REST_TIME, maxAttempts=Globals.DEFAULT_MAX_ATTEMPTS):
    Util.log("Initializing asset cache for collection: " + collection)

    timestamp = time()
    cursor = ""
    assets = {}
    numListed = 0
    pageNum = 0
    numFailedAttempts = 0
    params = {
        "collection_slug": Globals.COLLECTIONS[collection]["slug"],
        "order_direction": "desc",
        "include_orders": "true",
        "limit": "50"
    }

    # Iterate through all pages of the API response saving info about the assets.
    while cursor != None:
        page = fetchOpenSeaAsset(Globals.OPENSEA_ASSETS_URL, params)

        # Handle a failed API call, usually due to being rate-limited by OpenSea.
        if not "assets" in page:
            numFailedAttempts += 1
            Util.log("Failed to get page #" + str(pageNum) + " - cursor: " + cursor + " - attempt: " + str(numFailedAttempts), 1)

            # Abort if MAX_ATTEMPTS has been exceeded, to prevent getting caught in a loop and spamming the API further.
            if numFailedAttempts > maxAttempts:
                Util.log("Error while trying to cache collection: " + collection + " - terminating bot", 2)
                failedAssetCache = {
                    "cursor": cursor,
                    "assets": assets
                }
                Util.writeJson(Globals.CACHE_PATH + collection + "-failed-asset-cache.json", failedAssetCache)
                return False

        # Handle a successful API call by adding the returned information to the collection cache.
        else: 
            numFailedAttempts = 0

            # Loop through and extract the relevant data from the assets in the page.
            for asset in page["assets"]:
                id = asset["token_id"]

                # If the asset has no sell orders, it is unlisted.
                listingPrice = None
                if asset["sell_orders"]:
                    listingPrice = asset["sell_orders"][0]["current_price"]
                    numListed += 1
                    
                assets[id] = {
                    "owner": asset["owner"]["address"],
                    "image": {
                        "url": asset["image_url"],
                        "original_url": asset["image_original_url"]
                    },
                    "traits": asset["traits"],
                    "num_sales": asset["num_sales"],
                    "last_sale": asset["last_sale"],
                    "listing_price": listingPrice
                }

            Util.log("Got assets for page #" + str(pageNum) + " - listed: " + str(numListed) + " - total: " + str(len(assets)), 1)

            # Update the call params with the new cursor, allowing the next page of results to be retrieved.
            cursor = page["next"]
            params["cursor"] = cursor
            pageNum += 1

        # Be nice to the OpenSea API.
        # Be extra nice if previous API calls have failed, to try and wait out the rate-limit.
        restTime = restTime * (numFailedAttempts + 1)
        Util.log("Sleeping for " + str(restTime) + " seconds", 2)
        sleep(restTime)

    Util.log("Finished caching assets for " + collection, 1)
    assetCache = {
        "updated": timestamp,
        "assets": assets
    }
    Util.writeJson(Globals.CACHE_PATH + collection + "-asset-cache.json", assetCache)
    return True


def updateAssetCache(collection):
    timestamp = time()
    path = Globals.CACHE_PATH + collection + "-asset-cache.json"
    cache = Util.readJSON(path)

    params = {
        "collection_slug": Globals.COLLECTIONS[collection]["slug"],
        "only_opensea": "true",
        "event_type": "created",
        "occured_after": cache["updated"]
    }

    page = fetchOpenSeaAsset(Globals.OPENSEA_EVENTS_URL, params)
    for event in page["asset_events"]:
        id = event["asset"]["token_id"]
        if id in cache["assets"]:
            cache["assets"][id]["listing_price"] = event["starting_price"]

    cache["updated"] = timestamp
    Util.writeJson(path, cache)
    return True



def calculateFloorStats(assets):
    stats = {
        "Overall": {"floor_price": maxsize, "num_listed": 0},
        "Boosts": {}
    }

    for id in assets:
        asset = assets[id]

        # Only consider assets with active listings when calculating floor stats.
        if asset["listing_price"]:
            newGlobalFloor = min(stats["Overall"]["floor_price"], float(asset["listing_price"]))
            stats["Overall"]["floor_price"] = newGlobalFloor
            stats["Overall"]["num_listed"] += 1

            boosts = 0
            traits = asset["traits"]

            for trait in traits:
                traitType = trait["trait_type"]
                traitValue = trait["value"]

                if traitType not in stats:
                    stats[traitType] = {}

                if traitType in Globals.BOOST_TRAIT_TYPES:
                    boosts += traitValue

                else:
                    if traitValue not in stats[traitType]:
                        stats[traitType][traitValue] = {"floor_price": float(asset["listing_price"]), "num_listed": 1}

                    else:
                        statsEntry = stats[traitType][traitValue]
                        newFloor = min(statsEntry["floor_price"], float(asset["listing_price"]))
                        statsEntry["floor_price"] = newFloor
                        statsEntry["num_listed"] += 1

            # If the asset has no boost level, it is not a Kong and we can skip adding this embed label.
            if boosts > 0:
                rounded = round(boosts / 10) * 10
                if rounded not in stats["Boosts"]:
                    stats["Boosts"][rounded] = {"floor_price": float(asset["listing_price"]), "num_listed": 1}

                else:
                    statsEntry = stats["Boosts"][rounded]
                    newFloor = min(statsEntry["floor_price"], float(asset["listing_price"]))
                    statsEntry["floor_price"] = newFloor
                    statsEntry["num_listed"] += 1

    return stats
    

def constructFloorStatsEmbed(collectionName, assets, filter):
    floorStats = calculateFloorStats(assets)

    embed = Embed(
        title = Globals.COLLECTIONS[collectionName]["verbose"],
        description = "There can be up to a 10 minute delay",
        color = Color.blue()
    )
    
    embed.set_thumbnail(
        url = Globals.COLLECTIONS[collectionName]["image"]
    )
    
    embed.add_field(
        name = "Overall",
        value = "Floor: " + str(Util.fromWei(floorStats["Overall"]["floor_price"])) + "Ξ\nListed: " + str(floorStats["Overall"]["num_listed"]),
        inline = False
    )

    if filter != "":
        for traitValue in floorStats[filter]:
            statsEntry = floorStats[filter][traitValue]
            embed.add_field(
                name = traitValue,
                value = "Floor: " + str(Util.fromWei(statsEntry["floor_price"])) + "Ξ\nListed: " + str(statsEntry["num_listed"]),
                inline = True
            )

    return embed
