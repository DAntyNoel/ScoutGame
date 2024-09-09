
import json
import os

from .core import (
    Player, Gamer,
    Websocket,
    send, recv,
    green, yellow, red, 
    S2C, C2S, BD, format,
    DEBUG
)

GAMER = {}
'''$gid: {gamer: Gamer, startTime: datetime}'''
PLAYER = {}
'''$name: Player'''

class Query:
    '''Websocket query'''
    event: dict
    '''Event data'''
    ws: Websocket
    '''Websocket'''

    def __init__(self, event, ws) -> None:
        self.event = event
        self.ws = ws
    @property
    def seq(self) -> int:
        '''Sequence number'''
        assert 'seq' in self.event.keys(), 'Request error: `seq` required'
        return int(self.event['seq'])
    @property
    def func(self) -> str:
        '''Function name'''
        assert 'func' in self.event.keys(), 'Request error: `func` required'
        return str(self.event['func'])
    @property
    def name(self) -> str:
        '''Player name'''
        assert 'name' in self.event.keys(), 'Request error: `name` required'
        return str(self.event['name'])
    @property
    def gid(self) -> str:
        '''Game id'''
        assert 'gid' in self.event.keys(), 'Request error: `gid` required'
        return str(self.event['gid'])
    @property
    def player(self) -> 'Player':
        '''Player object. Raise error if not found'''
        plyr = find_player(self.name)
        if plyr is None:
            raise AssertionError('Player not found')
        return plyr
    @property
    def gamer(self) -> 'Gamer':
        '''Game object. Raise error if not found'''
        game = find_game(self.gid)
        if game is None:
            raise AssertionError('Game not found')
        return game
    
    def get(self, key:str, default: None|object = None) -> object:
        '''Get value from event. Return default if not found. Raise error if default is None'''
        if key in self.event:
            return self.event[key]
        if default is None:
            raise AssertionError(f'Request error: `{key}` required')
        return default
    
    async def ok(self, message: str|list|dict = 'ok') -> None:
        '''Respond ok/message to client'''
        await send(self.ws, {
            'code': 0,
            'seq': self.seq,
            'message': message
        })
    
    async def error(self, message: str, code: int = -1) -> None:
        '''Send error message to client'''
        await send(self.ws, {
            'code': code,
            'seq': self.seq,
            'message': message
        })

def find_player(name:str) -> 'Player|None':
    '''Find player by name'''
    global PLAYER
    global GAMER
    if name in PLAYER:
        return PLAYER[name]
    return None

async def find_player_ws(name:str, websocket: Websocket|None = None, gamer: 'Gamer|None' = None) -> 'Player':
    '''Find player by name. Raise error to client. 
    If gamer specified, player must be in the game.
    If websocket specified, check if the websocket is verified.'''
    global PLAYER
    global GAMER
    if name in PLAYER:
        player:'Player' = PLAYER[name]
        if gamer and player.gamer != gamer:
            raise AssertionError('Player not in the game')
        if websocket and id(player.ws) != id(websocket):
            raise AssertionError('Player not logged in')
        return PLAYER[name]
    else:
        raise AssertionError('Player not found')

def find_game(gid:str) -> 'Gamer|None':
    '''Find game by gid'''
    global PLAYER
    global GAMER
    if gid in GAMER:
        return GAMER[gid]['gamer']
    return None

async def find_game_ws(gid:str, websocket: Websocket|None = None, name: str = '') -> 'Gamer':
    '''Find game by websocket. Raise error to client. 
    If name specified, player must be in the game. '''
    global PLAYER
    global GAMER
    if gid in GAMER:
        gamer:'Gamer' = GAMER[gid]['gamer']
        if name == '' or gamer._has_player(find_player(name)):
            return GAMER[gid]['gamer']
        raise AssertionError('You are not in the game.')
    raise AssertionError('Game not found.')

