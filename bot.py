import discord
import os
import requests
import json
import concurrent
from dotenv import load_dotenv

load_dotenv()


def request_get(url):
    return requests.get(url)


def check_valid_status_code(request):
    if request.status_code == 200:
        return request.json()
    return False


def get_matches():
    url = "https://api.opendota.com/api/players/{0}/recentMatches".format(
        os.getenv('STEAM'))
    response = requests.get(url)

    if not check_valid_status_code(response):
        print(response.status_code)
        return False

    matches = check_valid_status_code(response)

    matches_list = []
    for match in matches:
        matches_list.append((match["match_id"], match["player_slot"]))

    return matches_list


def get_sa_games():
    matches_list = get_matches()

    match_urls = []
    for match in matches_list:
        match_urls.append(
            "https://api.opendota.com/api/matches/{0}".format(match[0]))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        match_response = [executor.submit(
            request_get, url) for url in match_urls]
        concurrent.futures.wait(match_response)

    my_response = []

    for i in range(len(matches_list)):
        data = match_response[i].result().json()
        players = data["players"]
        for player in players:
            if player["player_slot"] == matches_list[i][1]:
                my_response.append(player)
    return my_response


def get_toxic():

    toxic_list = []

    for response in get_sa_games():
        item_list = []

        for i in range(6):
            item_list.append(response["item_{0}".format(i)])

        for j in range(3):
            item_list.append(response["backpack_{0}".format(j)])

        for item in item_list:
            if item == 215:
                toxic_list.append((response, "bought a Shadow Amulet"))

        empty_inv = 0
        for item in item_list:
            empty_inv += item
        if empty_inv == 0:
            toxic_list.append((response, "destroyed all his items"))

    return toxic_list


def create_message():
    with open('heroes.json') as heroes_files:
        heroes = json.load(heroes_files)["heroes"]

    heroes_files.close()

    tlist = get_toxic()

    toxic = tlist[0][0]

    hero_id = toxic["hero_id"]
    kills = toxic["kills"]
    deaths = toxic["deaths"]
    match_id = toxic["match_id"]
    reason = tlist[0][1]

    for hero in heroes:
        if hero["id"] == hero_id:
            hero_name = hero["localized_name"]

    text = "Jacko recently {0} in a game as {1}, dying {2} times and getting {3} kills.".format(
        reason, hero_name, deaths, kills)
    dotabuff_url = "https://www.dotabuff.com/matches/{0}".format(match_id)
    return (text, dotabuff_url)


client = discord.Client()


@ client.event
async def on_ready():
    for guild in client.guilds:
        if guild.name == os.getenv('DISCORD_GUILD'):
            break

    print(f'{client.user} has connected to {guild.name}')


@ client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == '!shadow':
        async with message.channel.typing():
            response = create_message()

        await message.channel.send(response[0])
        await message.channel.send(response[1])


client.run(os.getenv('TOKEN'))
