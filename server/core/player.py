from .conn import Websocket
from .states import PlayerState, PokeState
from .poke import Poke, PokeCombine

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # Avoid circular import
    from .gamer import Gamer
    
    
class Player:
    name: str
    '''玩家名'''
    gamer: 'Gamer|None'
    '''游戏对象'''
    pokes: list[Poke]
    '''手牌'''
    state: PlayerState
    '''状态'''
    ws: Websocket
    '''websocket对象'''
    database: dict[str, object]
    '''数据库对象'''
    _is_logged: bool
    '''是否登录'''
    def __init__(self, name: str) -> None:
        self.name = name
        self.gamer = None
        self.pokes = []
        self.state = PlayerState.ONLINE
        self.ws = None
        self.database = {}
        self._is_logged = False
    def login(self, ws: Websocket) -> tuple[bool, str]:
        '''玩家登录'''
        if self.ws:
            return False, 'Already logged in'
        self.ws = ws
        self.database = {
            'username': self.name,
            'uid': -1,
            'pwd_hash': '',
            'last_login': '',
            'points': 0,
            'ip': '',
            'counts': 0,
            'info': ''
        } # TODO
        self._is_logged = True
        return True, 'Login success'
    def offline(self) -> None:
        '''离线模式'''
        self.ws = None
        self._is_logged = False
        self.database = {
            'username': self.name,
            'uid': -1,
            'pwd_hash': '',
            'last_login': '',
            'points': 0,
            'ip': '',
            'counts': 0,
            'info': ''
        }
    def get_ip(self) -> str:
        '''获取玩家IP'''
        assert self.ws, \
            "Player must be logged in"
        addr = self.ws.remote_address
        if addr == None:
            return 'Unknown'
        if isinstance(addr, tuple):
            return addr[0]
        return addr
    def json(self) -> dict:
        '''获取玩家信息'''
        if self._is_logged:
            return {
                'name': self.name,
                'username': self.database['username'],
                'uid': self.database['uid'],
                'state': self.state.value,
                'gamer': self.gamer.gid if self.gamer else None,
                'pokes': [[str(poke) for poke in self.pokes], [poke.str_disable for poke in self.pokes]],
                'ip': self.get_ip(),
                'points': self.database['points'],
                'counts': self.database['counts'],
            }
        return {
            'name': self.name,
            'state': self.state.value,
            'gamer': self.gamer.gid if self.gamer else None,
            'pokes': [[str(poke) for poke in self.pokes], [poke.str_disable for poke in self.pokes]]
        }
    def sync_database(self, **kwargs) -> None:
        '''同步数据库'''
        for key, value in kwargs.items():
            self.database[key] = value
        # self.database.write() TODO
        
    def clear(self) -> None:
        '''清空玩家对局信息'''
        self.pokes = []
        self.state = PlayerState.ROOM if self.gamer else PlayerState.ONLINE
    def set_state(self, state: PlayerState|int) -> None:
        '''设置玩家状态'''
        if isinstance(state, int):
            state = PlayerState(state)
        elif not isinstance(state, PlayerState):
            raise AssertionError(
                "State must be an instance of PlayerState or int"
            )
        self.state = state
    def get_total_score(self) -> dict[tuple[str, int]]:
        '''获取所有玩家总得分'''
        assert self.state.value > 0, \
            "Only player in end state can get total score"
        assert self.gamer, \
            "Player must be set to a gamer before get total score"
        return self.gamer.get_total_score()

    # 游戏准备阶段的接口

    def set_gamer(self, gamer: 'Gamer') -> None:
        '''玩家进入游戏'''
        assert self.state == PlayerState.ONLINE, \
            "Only ONLINE player can be set to a gamer"
        assert self.gamer == None, \
            "Player must not be in any game"
        gamer.add_player(self)
        self.gamer = gamer
        self.set_state(PlayerState.ROOM)

    def ready_for_game(self) ->  None|dict[str, str]:
        '''玩家主动准备游戏，将广播事件'''
        assert self.state == PlayerState.ROOM or \
               self.state == PlayerState.END, \
            "Only in room or end player can be ready for game"
        assert self.gamer , \
            "Player must be set to a gamer before ready for game"
        self.set_state(PlayerState.READY)
        return self.gamer.player_ready(self)

    def unready_for_game(self) -> None:
        '''玩家取消准备游戏'''
        assert self.state == PlayerState.READY, \
            "Only player in ready state can unready for game"
        assert self.gamer, \
            "Player must be set to a gamer before unready for game"
        self.gamer.player_unready(self)
        self.set_state(PlayerState.ROOM)

    def quit_game(self) -> None:
        '''玩家退出游戏'''
        assert self.state == PlayerState.ROOM or \
               self.state == PlayerState.END, \
            "Only player in gamer but not playing can quit"
        assert self.gamer, \
            "Not participating in any game"
        self.gamer.remove_player(self)
        self.gamer = None
        self.set_state(PlayerState.ONLINE)
            
    def game_start(self) -> None:
        '''游戏开始事件'''
        assert self.state == PlayerState.INIT, \
            "Ingame Error: Only player in init state can be informed that game starts"
        info = self.gamer.get_info()
        self.sync_database(counts=self.database['counts']+1)

    def is_ready(self) -> bool:
        '''牌局初始化的检查函数'''
        assert self.state == PlayerState.READY, \
            "Only player in ready state can check ready"
        assert all(poke.is_ready() for poke in self.pokes), \
            "All pokes must be ready"
        assert self.gamer, \
            "Player must be set to a gamer before check ready"
        return self.gamer._has_player(self)
    
    # 游戏进行中的接口   

    def get_pokes(self) -> str:
        '''查看手牌'''
        return ' '.join(str(poke) for poke in self.pokes)+','+' '.join(poke.str_disable for poke in self.pokes)

    def receive_pokes(self, pokes: list[Poke]) -> None:
        '''获取手牌并修改牌的状态'''
        assert self.state == PlayerState.READY, \
            "Only player in ready state can get pokes"
        self.pokes = pokes
        for poke in self.pokes:
            poke.set_state(PokeState.HIDE)
            poke.set_owner(self)

    def choose_pokes_side(self, reverse: bool) -> None:
        '''牌局开始时，选择手牌正反面，将广播事件'''
        assert self.state == PlayerState.INIT, \
            "Ingame Error: Only player in init state can upset pokes"
        assert self.gamer, \
            "Ingame Error: Player must be set to a gamer before upset pokes"
        if reverse:
            for poke in self.pokes:
                poke.reverse_side()
        self.gamer.player_init_finish(self)
    
    def choose_pokes_index(self, begin:int, end:int) -> PokeCombine:
        '''选择手牌组合'''
        assert self.pokes != [], \
            "Player must have pokes to choose"
        assert 0 <= begin < end <= len(self.pokes), \
            "Invalid begin and end index"
        return PokeCombine(self.pokes[begin:end])
    
    def turn_act(self) -> None:
        '''玩家回合开始事件'''
        assert self.state == PlayerState.TURN, \
            "Ingame Error: Only player in turn state can act"
        assert self.gamer, \
            "Ingame Error: Player must be set to a gamer before act"
        info = '轮到你出牌了'
    
    def show(self, pokes: PokeCombine) -> 'Player|None':
        '''出牌，将会广播事件，返回下一个出牌玩家，若有玩家胜利则返回None'''
        assert pokes.type_ != 0, \
            f"Pokes must be a valid combine: {pokes.json()}"
        assert self.state == PlayerState.TURN, \
            "Only player in turn state can play pokes"
        assert all(poke in self.pokes for poke in pokes.pokes), \
            "Pokes must be in player's hand"
        assert self.gamer, \
            "Player must be set to a gamer before play pokes"
        displayed_pokes = self.gamer.displayed_pokes
        assert pokes > displayed_pokes, \
            f"Pokes must be greater than table's. Your's: {pokes}, Table's: {displayed_pokes}"
        return self.turn_end(0, pokes)

    def scout(self, poke_index: bool, reverse: bool, insert_index: int) -> 'None|Player':
        '''摸牌，将会广播事件，返回下一个出牌玩家，若有玩家胜利则返回None

        poke_index: 摸牌位置, Ture为头部，False为尾部

        reverse: 摸上来牌是否翻转

        insert_index: 摸上来牌放入自己手牌的位置

        displayed_pokes: 牌桌上的牌
        '''
        assert self.state == PlayerState.TURN, \
            "Only player in turn state can draw pokes"
        assert self.gamer, \
            "Player must be set to a gamer before play pokes"
        displayed_pokes = self.gamer.displayed_pokes
        assert len(displayed_pokes) > 0, \
            "Displayed pokes must exist"
        target_poke = displayed_pokes.pokes[0 if poke_index else -1]
        new_poke = Poke(up=target_poke.up, down=target_poke.down, side=target_poke.side)
        new_poke.set_state(PokeState.HIDE)
        new_poke.set_owner(self)
        if reverse:
            new_poke.reverse_side()
        return self.turn_end(1, new_poke, pos=insert_index)
    
    def scout_and_show(self, poke_index: bool, reverse: bool, insert_index: int) -> 'Player|None':
        '''摸牌并立刻出牌，将会广播事件，返回下一个出牌玩家，若有玩家胜利则返回None

        poke_index: 摸牌位置, Ture为头部，False为尾部

        reverse: 摸上来牌是否翻转

        insert_index: 摸上来牌放入自己手牌的位置

        displayed_pokes: 牌桌上的牌
        '''
        assert self.state == PlayerState.TURN, \
            "Only player in turn state can draw pokes"
        assert self.gamer, \
            "Player must be set to a gamer before play pokes"
        assert self not in self.gamer.scout_and_show, \
            "Player can only scout and show once in a game"
        displayed_pokes = self.gamer.displayed_pokes
        assert len(displayed_pokes) > 0, \
            "Displayed pokes must exist"
        target_poke = displayed_pokes.pokes[0 if poke_index else -1]
        new_poke = Poke(up=target_poke.up, down=target_poke.down, side=target_poke.side)
        new_poke.set_state(PokeState.HIDE)
        new_poke.set_owner(self)
        if reverse:
            new_poke.reverse_side()
        return self.turn_end(2, new_poke, pos=insert_index)
            
    def turn_end(self, type_: int, detail: 'PokeCombine|Poke', pos: int = -1) -> 'Player|None':
        '''玩家回合结束，将会广播事件，自动转换状态，通知Gamer并返回下一个出牌玩家
        
        type_: 操作类型，0为出牌，1为摸牌，2为摸牌并立刻出牌
        
        detail: 操作细节，出牌为PokeCombine，摸牌为Poke，摸牌并立刻出牌为Poke'''
        assert self.state == PlayerState.TURN, \
            "Ingame Error: Only player in turn state can end turn"
        assert self.gamer, \
            "Ingame Error: Player must be set to a gamer before end turn"
        self.set_state(PlayerState.WAIT)
        op = (self, type_, detail, pos)
        success, info = self.gamer.player_turn_end(op)
        assert success, info
        return info
    
    def game_ended(self) -> None:
        '''游戏结束事件'''
        assert self.state == PlayerState.END, \
            "Ingame Error: Only player in end state can be informed that game ends"
        info = self.gamer.get_info()
        score = self.get_self_score()
        self.sync_database(points=self.database['points']+score)

    def confirm_result(self) -> None:
        '''确认游戏结果，将会广播事件'''
        assert self.state == PlayerState.END, \
            "Only player in end state can confirm result"
        assert self.gamer, \
            "Player must be set to a gamer before confirm result"
        self.gamer.player_confirm_result()
    
    def get_self_score(self) -> int:
        '''获取玩家当前对局得分'''
        assert self.state.value > PlayerState.READY.value, \
            "Only player in game can get score"
        assert self.gamer, \
            "Player must be set to a gamer before get score"
        return self.gamer.get_player_score(self)
