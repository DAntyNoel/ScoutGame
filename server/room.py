from .static import *

async def getGamePlayers(query: Query):
    '''Get all players in the game'''
    await query.ok([p.name for p in query.gamer.players])
    if DEBUG:
        print(yellow(f"Player {query.name} queries game players in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getHost(query: Query):
    '''Get host of the game'''
    await query.ok(query.gamer.players[query.gamer.host_idx].name)
    if DEBUG:
        print(yellow(f"Player {query.name} queries host in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def setHost(query: Query):
    '''Set host of the game. Require host permission'''
    query.gamer.set_host(query.get('target_name'))
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} set host in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def lockRoom(query: Query):
    '''Lock the room. Require host permission'''
    query.gamer.lock_room(query.player)
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} set game {query.gid} private."), f" Websocket: {id(query.ws)}")

async def unlockRoom(query: Query):
    '''Unlock the room. Require host permission'''
    query.gamer.unlock_room(query.player)
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} set game {query.gid} public."), f" Websocket: {id(query.ws)}")