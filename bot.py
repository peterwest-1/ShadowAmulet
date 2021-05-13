import discord
import os
import requests
import json
import asyncio
import concurrent
from dotenv import load_dotenv
from dataclasses import dataclass


shadow_amulet = 215
load_dotenv()


@dataclass
class Match:
    match_id: str
    player_slot: int


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
        m_id = match["match_id"]
        p_slot = match["player_slot"]
        matches_list.append(Match(m_id, p_slot))

    return matches_list


def get_sa_games():
    matches_list = get_matches()

    match_urls = []
    for match in matches_list:
        match_urls.append(
            "https://api.opendota.com/api/matches/{0}".format(match.match_id))

    with concurrent.futures.ThreadPoolExecutor() as executor:
        match_response = [executor.submit(
            request_get, url) for url in match_urls]
        concurrent.futures.wait(match_response)

    my_response = []

    for i in range(len(matches_list)):
        data = match_response[i].result().json()
        players = data["players"]
        for player in players:
            if player["player_slot"] == matches_list[i].player_slot:
                my_response.append(player)
    return my_response


def get_toxic():

    toxic_list = []

    for response in get_sa_games():
        item_list = []

        item_list.append(response["item_0"])
        item_list.append(response["item_1"])
        item_list.append(response["item_2"])
        item_list.append(response["item_3"])
        item_list.append(response["item_4"])
        item_list.append(response["item_5"])
        item_list.append(response["backpack_0"])
        item_list.append(response["backpack_1"])
        item_list.append(response["backpack_2"])

        for item in item_list:
            if item == shadow_amulet:
                toxic_list.append(response)

    with open('heroes.json') as heroes_files:
        heroes = json.load(heroes_files)["heroes"]

    heroes_files.close()

    toxic = toxic_list[0]
    hero_id = toxic["hero_id"]

    for hero in heroes:
        if hero["id"] == hero_id:
            hero_name = hero["localized_name"]

    dotabuff_url = "https://www.dotabuff.com/matches/{0}".format(
        toxic["match_id"])

    kills = toxic["kills"]
    deaths = toxic["deaths"]
    assists = toxic["assists"]
    text = "Jacko recently bought a Shadow Amulet in a game as {0}, dying {1} times and getting {2} kills.".format(
        hero_name, deaths, kills)
    return (text, dotabuff_url)


client = discord.Client()


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    for guild in client.guilds:
        if guild.name == os.getenv('DISCORD_GUILD'):
            break

    print(
        f'{guild.name}(id: {guild.id})'
    )


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == '!shadow':
        response = get_toxic()

        await message.channel.send(response[0])
        await message.channel.send(response[1])


client.run(os.getenv('TOKEN'))
