
from .static import *

import secrets
from datetime import datetime

async def getGids(query: Query):
    '''Get all running game ids'''
    await query.ok(list(GAMER.keys()))
    if DEBUG:
        print(yellow(f"Player {query.name} queries game ids."), f" Websocket: {id(query.ws)}")

async def getOnlinePlayers(query: Query):
    '''Get all online players'''
    await query.ok(list(PLAYER.keys()))
    if DEBUG:
        print(yellow(f"Player {query.name} queries online players."), f" Websocket: {id(query.ws)}")

async def playerJoin(query: Query):
    '''Player join the game'''
    if query.gid == '':
        # Create a new game
        gid = secrets.token_hex(6)
        gamer = Gamer(gid)
        global GAMER
        GAMER[gid] = {'gamer': gamer, 'startTime': datetime.now()}
    else:
        # Join existing game
        gamer = find_game(query.gid)
        if gamer is None:
            await query.error(message='Game not found', code=404)
            if DEBUG:
                print(red(f"Game {query.gid} not found."), f" Websocket: {id(query.ws)}")
            return
        if len(gamer.players) == 5:
            await query.error(message='Game is full', code=403)
            if DEBUG:
                print(red(f"Game {query.gid} is full."), f" Websocket: {id(query.ws)}")
            return
    query.player.set_gamer(gamer)
    await query.ok(gamer.gid)
    if DEBUG:
        print(green(f"Player {query.name} joins game {gamer.gid}."), f" Websocket: {id(query.ws)}")
                
