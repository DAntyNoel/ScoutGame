from enum import Enum

class PokeState(Enum):
    '''扑克牌状态'''
    WAITING = -1
    '''未初始化'''
    DISPLAY = 1
    '''牌桌上显示'''
    HIDE = 2
    '''手牌中'''
    GOAL = 3
    '''得分区'''

class PlayerState(Enum):
    '''玩家状态'''
    ONLINE = -2
    '''在线'''
    ROOM = -1
    '''房间中'''
    READY = 0
    '''准备中'''
    INIT = 1
    '''牌局开始，发牌后选择'''
    WAIT = 2
    '''等待出牌'''
    TURN = 3
    '''出牌中'''
    END = 4
    '''牌局结束''' # 连续对局中间态

class GameState(Enum):
    RECRUIT = -2
    '''招募中'''
    FULL = -1
    '''人数已满但未开始'''
    INIT = 0
    '''游戏初始化'''
    PLAYER_INIT = 1
    '''玩家起始准备'''
    PLAYING = 2
    '''游戏中'''
    END = 3
    '''单局结束''' # 连续对局中间态