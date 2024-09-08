
from .static import *

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
                
