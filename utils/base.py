import random
from enum import Enum
from .conn import bd
from .api import BROADCAST as BD, format

from websockets import WebSocketClientProtocol as Websocket

DEBUG = False

class GameOperation:
    '''游戏操作
    
    type_: 操作类型
    
    -1: 游戏开始
    
    0: 出牌
    
    1: 摸牌
    
    2: 摸牌并立刻出牌
    
    detail: 操作细节，游戏开始为None，出牌为PokeCombine，摸牌为Poke，摸牌并立刻出牌为Poke'''
    player: 'Player'
    '''操作玩家'''
    type_: int
    '''操作类型

    -1: 游戏开始

    0: 出牌

    1: 摸牌

    2: 摸牌并立刻出牌
    '''
    detail: 'None|PokeCombine|Poke|Poke'
    '''操作细节'''
    pos: int
    '''摸牌后将牌插入的位置'''
    def __init__(self, player: 'Player', type_: int, detail: 'PokeCombine|Poke|None', pos: int = -1) -> None:
        self.player = player
        self.type_ = type_
        self.detail = detail
        self.pos = pos
        if self.type_ < 1:
            assert self.pos == -1, \
                "Only type 1, 2 can have pos"
        else:
            assert self.pos != -1, \
                "Type 1, 2 must have pos"
    def __str__(self) -> str:
        if self.type_ == 0:
            return f"{self.player.name} 出牌 {self.detail}"
        elif self.type_ == 1:
            return f"{self.player.name} 摸牌 {self.detail}"
        elif self.type_ == 2:
            return f"{self.player.name} 摸牌并立刻出牌"
        elif self.type_ == -1:
            return f"游戏开始: {self.player.name} 先手"
    def full_log(self) -> str:
        if self.type_ == 0:
            return f"{self.player.name} 出牌 {self.detail}"
        elif self.type_ == 1:
            return f"{self.player.name} 摸牌 {self.detail}，插入成为第{self.pos + 1}张"
        elif self.type_ == 2:
            return f"{self.player.name} 摸牌并立刻出牌 {self.detail}，插入成为第{self.pos + 1}张"
        elif self.type_ == -1:
            return f"游戏开始: {self.player.name} 先手"
    def json(self) -> dict:
        return {
            'game_operation': str(self),
            'target_name': self.player.name,
            'type_': self.type_,
            'detail': self.detail.json() if self.detail else None,
        }
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

class Gamer:
    # 游戏基本信息
    gid: int|str
    '''游戏ID'''
    players: list['Player']
    '''玩家列表'''
    playing_num: int
    '''游戏人数'''
    state: GameState
    '''游戏状态'''

    # 牌桌信息（所有玩家可获取）
    info: str
    '''游戏通知信息'''
    all_pokes: list['Poke']
    '''所有扑克牌对象'''
    game_history: list[GameOperation]
    '''游戏历史记录'''
    displayed_pokes: 'PokeCombine'
    '''牌桌上的牌'''

    # 游戏得分信息
    @property
    def ingame_score(self, player: 'Player|None' = None) -> int|list[int]:
        '''当前局得分'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can get ingame score"
        if isinstance(player, Player):
            return player.get_self_score()
        return [player.get_self_score() for player in self.players]
    extra_points: dict[str: int]
    '''单局额外得分'''
    total_score: dict[str: int]
    '''玩家总得分'''

    def __init__(self, gid: int|str) -> None:
        self.gid = gid
        self.players = []
        self.playing_num = 0
        self.set_state(GameState.RECRUIT)

        self.info = "游戏招募中"
        self.all_pokes = []
        self.game_history = []
        self.displayed_pokes = PokeCombine([])

        self.total_score = {}
        self.extra_points = {}

    def _is_started(self) -> bool:
        return self.state.value >= 0
    def _clear_state(self) -> None:
        '''清空单局游戏信息'''
        for poke in self.all_pokes:
            poke._clear_state()
        for player in self.players:
            player._clear_state()
        self.info = "游戏招募中"
        self.set_state(GameState.RECRUIT)
        if len(self.players) == 5:
            self.info = "游戏人数已满，等待开始"
            self.set_state(GameState.FULL)
        self.all_pokes = []
        self.game_history = []
        self.displayed_pokes = PokeCombine([])

        self.extra_points = {player.name: 0 for player in self.players}
    def _has_player(self, player: 'Player') -> bool:
        return player in self.players
    def json(self) -> dict:
        '''获取游戏信息'''
        return {
            'gid': self.gid,
            'players': [player.json() for player in self.players],
            'playing_num': self.playing_num,
            'state': self.state.value,
            'info': self.info,
            'total_score': self.total_score,
            'extra_points': self.extra_points,
            'displayed_pokes': str(self.displayed_pokes),
            'history': [str(op) for op in self.game_history]
        }

    def get_player(self, name: str) -> 'Player|None':
        '''根据名字获取玩家'''
        for player in self.players:
            if player.name == name:
                return player
        return None
    def get_poke(self, value: tuple[str|int]|str) -> 'Poke|None':
        '''根据牌面数字获取牌'''
        for poke in self.all_pokes:
            if poke == value:
                return poke
        return None
    def set_state(self, state: GameState|int) -> None:
        '''设置游戏状态'''
        if isinstance(state, int):
            state = GameState(state)
        elif not isinstance(state, GameState):
            raise AssertionError(
                "State must be an instance of GameState or int"
            )
        self.state = state
    def get_info(self) -> str:
        '''获取游戏信息'''
        return self.info
    def get_history(self) -> list[GameOperation]:
        '''获取游戏历史记录'''
        if self.state == GameState.PLAYING:
            return self.game_history[:-1] #TODO: 优化
        elif self.state == GameState.END:
            return self.game_history
        else:
            raise AssertionError(
                "Only playing or end game can get history"
            )
    def get_total_score(self) -> dict[tuple[str, int]]:
        '''获取玩家总分'''
        return self.total_score
   
    # 游戏招募阶段

    def add_player(self, player: 'Player') -> None:
        '''添加玩家，广播事件'''
        if self.state == GameState.END:
            self.state = GameState.RECRUIT
            self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
            if len(self.players) == 5:
                self.state = GameState.FULL
                self.info = "游戏人数已满，等待开始"
        assert self.state == GameState.RECRUIT, \
            "Only recruiting game can add player"
        self.players.append(player)
        self.playing_num += 1
        self.total_score[player.name] = 0
        self.extra_points[player.name] = 0
        if self.playing_num == 5:
            self.set_state(GameState.FULL)
            self.info = "游戏人数已满，等待开始"   
        bd(get_websockets(self.gid), format(BD['playerJoin'], gid=self.gid, info=self.get_info(), target_name=player.name))
    def remove_player(self, player: 'Player') -> None:
        '''移除玩家，广播事件'''
        if self.state == GameState.END:
            self.state = GameState.RECRUIT
            self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
            if len(self.players) == 5:
                self.state = GameState.FULL
                self.info = "游戏人数已满，等待开始"
        assert player in self.players, \
            "Player must be in the game"
        assert self.state == GameState.RECRUIT or \
               self.state == GameState.FULL, \
            "Only recruiting game can remove player"
        self.players.remove(player)
        self.playing_num -= 1
        self.total_score.pop(player.name)
        self.extra_points.pop(player.name)
        if self.playing_num < 5:
            self.set_state(GameState.RECRUIT)
            self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
        bd(get_websockets(self.gid), format(BD['playerLeave'], gid=self.gid, info=self.get_info(), target_name=player.name))

    def player_ready(self, player: 'Player') -> None|dict[str, str]:
        '''玩家准备，广播事件，当所有玩家准备完毕时返回初始化信息'''
        assert not self._is_started(), \
            "Game has already started"
        self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
        bd(get_websockets(self.gid), format(BD['playerReady'], gid=self.gid, info=self.get_info(), target_name=player.name))
        if all(p.state == PlayerState.READY for p in self.players):
            self.set_state(GameState.INIT)
            self.info = "游戏初始化中"
            return self.init_game()
        return None
    def player_unready(self, player: 'Player') -> None:
        '''玩家取消准备，广播事件'''
        assert not self._is_started(), \
            "Game has already started"
        bd(get_websockets(self.gid), format(BD['playerUnready'], gid=self.gid, info=self.get_info(), target_name=player.name))
    
    # 游戏循环主体

    def init_game(self) -> dict[str, str]:
        '''所有人准备完毕，游戏初始化，广播事件'''
        assert self.state == GameState.INIT, \
            "Only initializing game can start"
        # 生成扑克牌
        for i in range(1, 11):
            for j in range(1, i):
                poke = Poke(j, i, random.choice([True, False]))
                self.all_pokes.append(poke)
        # 分发扑克牌
        random.shuffle(self.all_pokes)
        poke_nums = {
            2: 15,
            3: 15,
            4: 11,
            5: 9
        }
        assert len(self.players) == self.playing_num, \
            "Player number must be equal to playing number"
        player_and_poke = {player.name: '' for player in self.players}
        for i, player in enumerate(self.players):
            pokes = self.all_pokes[i*poke_nums[self.playing_num]:(i+1)*poke_nums[self.playing_num]]
            player.receive_pokes(pokes)
            player_and_poke[player.name] = ' '.join([str(poke) for poke in pokes]) + ',' + ' '.join([poke.str_disable for poke in pokes])
        # 检查并设置玩家状态
        for player in self.players:
            assert player._is_ready(), \
                f"All players must be ready. {player.name} is not ready."
            player.set_state(PlayerState.INIT)
        # 检查牌状态
        distributed_pokes_num = len(self.players) * poke_nums[self.playing_num]
        assert all(poke._is_ready() for poke in self.all_pokes[:distributed_pokes_num]), \
            "All pokes must be ready"
        # 初始化牌局信息
        self.displayed_pokes = PokeCombine([])
        self.extra_points = {player.name: 0 for player in self.players}
        self.info = "游戏开始，玩家选择起始手牌正反序"
        self.init_finish = [False for _ in self.players]
        # 通知玩家游戏开始，选择牌序
        for player in self.players:
            player.game_start()
        bd(get_websockets(self.gid), format(BD['gameInit'], gid=self.gid, info=self.get_info()))
        return player_and_poke
    def player_init_finish(self, player: 'Player') -> None:
        '''玩家起始准备结束，广播事件'''
        assert self.state == GameState.INIT, \
            "Only initializing game can player init finish"
        assert player.state == PlayerState.INIT, \
            "Only player in init state can finish init"
        assert self.init_finish, \
            "Ingame Error: `init_finish` not found. Game is not initialized"
        player.set_state(PlayerState.WAIT)
        self.info = f"已准备 ({sum(self.init_finish)}/{len(self.init_finish)})"
        self.init_finish[self.players.index(player)] = True
        if all(self.init_finish):
            self.set_state(GameState.PLAYING)
            self.info = "游戏开始"
            bd(get_websockets(self.gid), format(BD['gameStart'], gid=self.gid, info=self.get_info(), table=str(self.displayed_pokes)))
            # 第一个玩家开始
            first_player = random.choice(self.players)
            self.game_history.append(GameOperation(first_player, -1, None))
            self.player_turn_act(first_player)

    def player_turn_act(self, player: 'Player') -> None:
        '''通知玩家回合开始'''
        bd(get_websockets(self.gid), format(BD['gameAction'], gid=self.gid, info=self.get_info(), target_name=player.name, table=str(self.displayed_pokes), op=self.game_history[-1].json()))
        assert self.state == GameState.PLAYING, \
            "Ingame Error: Only playing game can player turn act"
        assert player.state == PlayerState.WAIT, \
            "Ingame Error: Only player in wait state can act"
        player.set_state(PlayerState.TURN)
        player.turn_act()
    def player_turn_end(self, op:GameOperation) -> tuple[bool, 'str|Player|None']:
        '''玩家回合结束，广播事件，事件非法时返回False和错误信息，否则返回True和下一位玩家，若有玩家胜利则返回True和None'''
        assert self.state == GameState.PLAYING, \
            "Ingame Error: Only playing game can player turn end"
        assert op.player.state == PlayerState.WAIT, \
            "Ingame Error: Player must be in wait state"
        # 检查操作合法性
        assert op.type_ >= 0, \
            "Ingame Error: Game has already started"
        last_op = self.game_history[-1]
        if last_op.type_ == -1:
            # 游戏开始
            if last_op.player != op.player:
                return False, "Only first player can play first"
        elif last_op.type_ == 0:
            # 上一家出牌
            last_idx = self.players.index(last_op.player)
            target_idx = self.players.index(op.player)
            if (last_idx + 1 - target_idx) % self.playing_num != 0:
                return False, "Only next player in turn can play"
            if op.type_ == 0 and self.displayed_pokes >= op.detail:
                return False, f"Pokes must be greater than table's (0)\n{self.displayed_pokes} >= {op.detail}"
        elif last_op.type_ == 1:
            # 上一家摸牌
            last_idx = self.players.index(last_op.player)
            target_idx = self.players.index(op.player)
            if (last_idx + 1 - target_idx) % self.playing_num != 0:
                return False, "Only next player in turn can draw"
        elif last_op.type_ == 2:
            # 自己摸牌并立刻出牌
            last_idx = self.players.index(last_op.player)
            target_idx = self.players.index(op.player)
            if last_op.player != op.player:
                return False, "Only player himself in turn can draw and play"
            if self.displayed_pokes >= op.detail:
                return False, "Pokes must be greater than table's (2)"
        self.game_history.append(op)
        # 处理操作
        next_player = self.players[(self.players.index(op.player) + 1) % self.playing_num]
        if op.type_ == 0:
            self.player_play_pokes(op)
        elif op.type_ == 1:
            self.player_draw_pokes(op)
        elif op.type_ == 2:
            next_player = op.player
            self.player_draw_pokes(op)
        # 有玩家胜利
        if len(op.player.pokes) == 0:
            assert self.win(op.player), \
                "Ingame Error: Player win is not successful"
            return True, next_player
        # 游戏继续，通知下一位玩家
        bd(get_websockets(self.gid), format(BD['gameAction'], gid=self.gid, info=self.get_info(), table=str(self.displayed_pokes), op=op.json()))
        if op.type_ == 0 or op.type_ == 1:
            self.player_turn_act(self.players[(self.players.index(op.player) + 1) % self.playing_num])
        elif op.type_ == 2:
            self.player_turn_act(op.player)
        return True, None
    
    def player_play_pokes(self, op: GameOperation) -> None:
        '''玩家出牌逻辑处理'''
        player = op.player
        pokes = op.detail
        assert isinstance(player, Player), \
            "Player must be a valid player"
        assert isinstance(pokes, PokeCombine), \
            "Pokes must be a valid combine"
        assert pokes > self.displayed_pokes, \
            "Pokes must be greater than table's"
        # 将牌桌上的牌放入自己的得分区
        for poke in self.displayed_pokes.pokes:
            poke.set_state(PokeState.GOAL)
            poke.owner = player
        # 将手牌中的牌放入牌桌
        for poke in pokes.pokes:
            assert poke in player.pokes, \
                "Pokes must be in player's hand"
            assert poke.owner == player, \
                f"Pokes must be owned by player {player.name}"
            assert poke.state == PokeState.HIDE, \
                "Pokes must be in hand"
            poke.set_state(PokeState.DISPLAY)
            player.pokes.remove(poke)
        # 更新牌桌上的牌
        self.set_displayed_pokes(pokes)
    def player_draw_pokes(self, op: GameOperation) -> None:
        '''玩家摸牌逻辑处理'''
        new_poke = op.detail
        target_poke = self.get_poke([new_poke.value, new_poke.value_disable])
        player = op.player
        pos = op.pos % len(player.pokes)
        assert isinstance(new_poke, Poke), \
            "New poke must be a valid poke"
        assert new_poke.owner == player, \
            "New poke must be owned by player himself"
        assert new_poke.state == PokeState.HIDE, \
            "New poke must be in hand"
        assert isinstance(target_poke, Poke), \
            "Target poke must be in game"
        assert target_poke.state == PokeState.DISPLAY, \
            "Target poke must be in table (1)"
        assert target_poke in self.displayed_pokes.pokes, \
            "Target poke must be in table (2)"
        assert target_poke.owner != player, \
            "Target poke must be owned by original player"
        assert 0 <= pos <= len(player.pokes), \
            "Invalid insert position"
        # 目标牌的拥有者奖励得分
        self.reward_point(target_poke.owner)
        # 销毁目标牌并将新牌添加至牌库池和玩家手牌
        self.all_pokes.remove(target_poke)
        self.all_pokes.append(new_poke)
        player.pokes.insert(pos, new_poke)
        # 更新牌桌上的牌
        remain_pokes = self.displayed_pokes.pokes
        remain_pokes.remove(target_poke)
        self.set_displayed_pokes(PokeCombine(remain_pokes))

    def reward_point(self, player: 'Player') -> None:
        '''奖励得分：自己的牌被别人摸走'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can reward point"
        self.extra_points[player.name] += 1
    
    def get_displayed_pokes(self) -> 'PokeCombine':
        '''获取牌桌上的牌'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can get displayed pokes"
        return self.displayed_pokes
    def set_displayed_pokes(self, pokes: 'PokeCombine') -> None:
        '''设置牌桌上的牌'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can set displayed pokes"
        self.displayed_pokes = pokes
    
    def win(self, player: 'Player') -> bool:
        '''玩家胜利，广播事件'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can set win"
        # 检查玩家手牌是否为空
        if (
            len(player.pokes) != 0 or
            any(poke.state == PokeState.HIDE and \
                poke.owner == player for poke in self.all_pokes)
        ):
            return False
        # 修改玩家状态和游戏状态
        for p in self.players:
            p.set_state(PlayerState.END)
        self.set_state(GameState.END)
        self.info = f"游戏结束，{player.name}获胜！"
        # 记录分数
        for player in self.players:
            if player.name not in self.total_score:
                self.total_score[player.name] = 0
            self.total_score[player.name] += self.get_player_score(player)
        # 通知玩家游戏结束
        for player in self.players:
            player.game_ended()
        bd(get_websockets(self.gid), format(BD['win'], gid=self.gid, info=self.get_info(), target_name=player.name))
        self.confirmed = [False for _ in self.players]
        return True
    def player_confirm_result(self, player: 'Player') -> None:
        '''玩家确认游戏结束，广播事件，仅允许END状态游戏中间态调用，否则无效'''
        if self.state == GameState.END:
            self.confirmed[self.players.index(player)] = True
            bd(get_websockets(self.gid), format(BD['playerConfirm'], gid=self.gid, info=self.get_info(), target_name=player.name))
            # 清空单局游戏信息
            if all(self.confirmed):
                self._clear_state()
                self.state = GameState.RECRUIT
                self.info = "游戏招募中"
                if len(self.players) == 5:
                    self.state = GameState.FULL
                    self.info = "游戏人数已满，等待开始"

    # 游戏进行中随时调用的接口

    def get_player_score(self, player: 'Player') -> int:
        '''获取玩家当前对局得分'''
        return (
            self.extra_points[player.name] 
            + sum(1 for poke in self.all_pokes
                if poke.state == PokeState.GOAL and poke.owner == player) 
            - sum(1 for poke in self.all_pokes   
                if poke.state == PokeState.HIDE and poke.owner == player))
    def get_game_info(self) -> dict:
        '''获取本局公开信息'''
        assert self.state == GameState.PLAYING or \
                self.state == GameState.END, \
            "Only playing or end game can get game info"
        return {
            'turn': len(self.game_history),
            'players': [player.name for player in self.players],
            'goal_pokes': [sum(1 for poke in self.all_pokes if 
                               poke.state == PokeState.GOAL and poke.owner == player) 
                                    for player in self.players],
            'remain_pokes': [sum(1 for poke in self.all_pokes if 
                               poke.state == PokeState.HIDE and poke.owner == player) 
                                    for player in self.players],
            'extra_points': self.extra_points,
            'table': str(self.displayed_pokes),
            'last_op': self.game_history[-1].json() if len(self.game_history) > 0 else None
        }

class PlayerState(Enum):
    '''玩家状态'''
    OFFLINE = -1
    '''离线'''
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

class Player:
    name: str
    '''玩家名'''
    gamer: Gamer|None
    '''游戏对象'''
    pokes: list['Poke']
    '''手牌'''
    state: PlayerState
    '''状态'''
    def __init__(self, name: str) -> None:
        self.name = name
        self.gamer = None
        self.pokes = []
        self.state = PlayerState.OFFLINE
    def _clear_state(self) -> None:
        '''清空玩家对局信息'''
        self.pokes = []
        self.state = PlayerState.OFFLINE
    def json(self) -> dict:
        '''获取玩家信息'''
        return {
            'name': self.name,
            'state': self.state.value,
            'gamer': self.gamer.gid if self.gamer else None,
            'pokes': [[str(poke) for poke in self.pokes], [poke.str_disable for poke in self.pokes]]
        }
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

    def set_gamer(self, gamer: Gamer) -> None:
        '''玩家进入游戏'''
        assert self.state == PlayerState.OFFLINE, \
            "Only offline player can be set to a gamer"
        assert self.gamer == None, \
            "Player must not be in any game"
        assert gamer, \
            "Not a valid gamer"
        self.gamer = gamer
        self.gamer.add_player(self)

    def ready_for_game(self) ->  None|dict[str, str]:
        '''玩家主动准备游戏，将广播事件'''
        assert self.state == PlayerState.OFFLINE or \
               self.state == PlayerState.END, \
            "Only offline or end player can be ready for game"
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
        self.set_state(PlayerState.OFFLINE)
        self.gamer.player_unready(self)

    def quit_game(self) -> None:
        '''玩家退出游戏'''
        assert self.state == PlayerState.OFFLINE or \
               self.state == PlayerState.END, \
            "Only player in gamer but not playing can quit"
        self.set_state(PlayerState.OFFLINE)
        assert self.gamer, \
            "Not participating in any game"
        self.gamer.remove_player(self)
        self.gamer = None
            
    def game_start(self) -> None:
        '''游戏开始事件'''
        assert self.state == PlayerState.INIT, \
            "Ingame Error: Only player in init state can be informed that game starts"
        info = self.gamer.get_info()
        if DEBUG:
            print(info)

    def _is_ready(self) -> bool:
        '''牌局初始化的检查函数'''
        assert self.state == PlayerState.READY, \
            "Only player in ready state can check ready"
        assert all(poke._is_ready() for poke in self.pokes), \
            "All pokes must be ready"
        assert self.gamer, \
            "Player must be set to a gamer before check ready"
        return self.gamer._has_player(self)
    
    # 游戏进行中的接口   
    #  
    def get_pokes(self) -> str:
        '''查看手牌'''
        return ' '.join(str(poke) for poke in self.pokes)+','+' '.join(poke.str_disable for poke in self.pokes)

    def receive_pokes(self, pokes: list['Poke']) -> None:
        '''获取手牌并修改牌的持有者和状态'''
        assert self.state == PlayerState.READY, \
            "Only player in ready state can get pokes"
        self.pokes = pokes
        for poke in self.pokes:
            poke.set_owner(self)
            poke.set_state(PokeState.HIDE)

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
    
    def choose_pokes_index(self, begin:int, end:int) -> 'PokeCombine':
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
    
    def play_pokes(self, pokes: 'PokeCombine') -> 'Player|None':
        '''出牌，将会广播事件，返回下一个出牌玩家，若有玩家胜利则返回None'''
        assert pokes.type_ != 0, \
            "Pokes must be a valid combine"
        assert self.state == PlayerState.TURN, \
            "Only player in turn state can play pokes"
        assert all(poke in self.pokes for poke in pokes.pokes), \
            "Pokes must be in player's hand"
        assert self.gamer, \
            "Player must be set to a gamer before play pokes"
        displayed_pokes = self.gamer.get_displayed_pokes()
        assert pokes > displayed_pokes, \
            "Pokes must be greater than table's"
        return self.turn_end(0, pokes)

    def draw_pokes(self, poke_index: bool, reverse: bool, insert_index: int) -> 'None|Player':
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
        displayed_pokes = self.gamer.get_displayed_pokes()
        assert len(displayed_pokes) > 0, \
            "Displayed pokes must exist"
        target_poke = displayed_pokes.pokes[0 if poke_index else -1]
        new_poke = Poke(up=target_poke.up, down=target_poke.down, side=target_poke.side)
        new_poke.set_owner(self)
        new_poke.set_state(PokeState.HIDE)
        if reverse:
            new_poke.reverse_side()
        return self.turn_end(1, new_poke, pos=insert_index)
            
    def turn_end(self, type_: int, detail: 'PokeCombine|Poke', pos: int = -1) -> 'Player|None':
        '''玩家回合结束，将会广播事件，自动转换状态，通知Gamer并返回下一个出牌玩家
        
        type_: 操作类型，0为出牌，1为摸牌，2为摸牌并立刻出牌
        
        detail: 操作细节，出牌为PokeCombine，摸牌为Poke，摸牌并立刻出牌为Poke'''
        assert self.state == PlayerState.TURN, \
            "Ingame Error: Only player in turn state can end turn"
        assert self.gamer, \
            "Ingame Error: Player must be set to a gamer before end turn"
        self.set_state(PlayerState.WAIT)
        op = GameOperation(self, type_, detail, pos)
        success, info = self.gamer.player_turn_end(op)
        assert success, info
        return info
    
    def game_ended(self) -> None:
        '''游戏结束事件'''
        assert self.state == PlayerState.END, \
            "Ingame Error: Only player in end state can be informed that game ends"
        info = self.gamer.get_info()
        if DEBUG:
            print(info)

    def confirm_result(self) -> None:
        '''确认游戏结果，将会广播事件'''
        assert self.state == PlayerState.END, \
            "Only player in end state can confirm result"
        assert self.gamer, \
            "Player must be set to a gamer before confirm result"
        self.gamer.player_confirm_result()
    
    def get_self_score(self) -> int:
        '''获取玩家当前对局得分'''
        assert self.state.value > 0, \
            "Only player in game can get score"
        assert self.gamer, \
            "Player must be set to a gamer before get score"
        return self.gamer.get_player_score(self)


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

class Poke:
    up: int
    '''正面数字'''
    down: int
    '''背面数字'''
    owner: Player|None
    '''持有者'''
    state: PokeState
    '''状态'''
    side: bool
    '''正反面，True为正面'''
    @property
    def value(self) -> int:
        '''获取生效牌面数字'''
        return self.up if self.side else self.down
    @property
    def value_disable(self) -> int:
        '''获取不生效牌面数字'''
        return self.down if self.side else self.up
    
    def __init__(self, up: int, down: int, side: bool = True) -> None:
        self.up = up
        self.down = down
        self.owner = None
        self.state = PokeState.WAITING
        self.side = side
    def __str__(self) -> str:
        if self.value == 10:
            return 'T'
        return str(self.value)
    @property
    def str_disable(self) -> str:
        '''获取不生效牌面数字的字符串'''
        if self.value_disable == 10:
            return 'T'
        return str(self.value_disable)
    def json(self) -> str:
        return str(self) + ',' + self.str_disable
    def __eq__(self, value: tuple[str|int]|str) -> bool:
        if isinstance(value, tuple):
            return (
                self.up == value[0] and self.down == value[1] or
                self.up == value[1] and self.down == value[0]
            )
        elif isinstance(value, list):
            return (
                self.up == value[0] and self.down == value[1] or
                self.up == value[1] and self.down == value[0]
            )
        elif isinstance(value, str):
            value = value.strip().replace(' ', ',').split(',')
            if len(value) != 2:
                return False
            return (
                self.up == int(value[0]) and self.down == int(value[1]) or
                self.up == int(value[1]) and self.down == int(value[0])
            )
        else:
            return False
    def __gt__(self, other: 'Poke') -> bool:
        return self.value > other.value
    def __ge__(self, other: 'Poke') -> bool:
        return self.value >= other.value
    def _clear_state(self) -> None:
        '''清空牌局信息'''
        self.state = PokeState.WAITING
        self.owner = None
        self.side = True
    def _is_ready(self) -> bool:
        '''牌局初始化的检查函数'''
        return (
            self.state == PokeState.HIDE and
            self.up < self.down and
            self.owner
        )
    def set_owner(self, player: Player) -> None:
        '''设置持有者'''
        self.owner = player
    def set_state(self, state: PokeState|int) -> None:
        '''设置牌状态'''
        if isinstance(state, int):
            state = PokeState(state)
        elif not isinstance(state, PokeState):
            raise AssertionError(
                "State must be an instance of PokeState or int"
            )
        self.state = state
    
    def reverse_side(self) -> None:
        '''翻转正反面'''
        assert self.state == PokeState.HIDE, \
            "Only poke in hand can reverse"
        self.side = not self.side

class PokeCombine:
    '''扑克组合'''
    pokes: list[Poke]
    '''扑克列表'''
    type_: int
    '''组合类型,
    0: 非法组合
    1：单牌
    2：顺子
    3：刻子'''
    def __init__(self, pokes: list[Poke]) -> None:
        self.pokes = pokes
        self.type_ = self._calculate_type()   
    def __len__(self) -> int:
        return len(self.pokes)   
    def __str__(self) -> str:
        return ' '.join(str(poke) for poke in self.pokes) + ',' + ' '.join(poke.str_disable for poke in self.pokes)
    def json(self) -> str:
        return str(self)
    def _calculate_type(self) -> int:
        if len(self.pokes) == 0:
            return 1 # 空牌也视作合法
        if len(self.pokes) == 1:
            return 1
        else:
            values = [poke.value for poke in self.pokes]
            if all(values[i] - values[i-1] == -1 for i in range(1, len(values))) or \
               all(values[i] - values[i-1] ==  1 for i in range(1, len(values))):
                return 2
            if len(set(values)) == 1:
                return 3
        return 0 
    def __gt__(self, other: 'PokeCombine') -> bool:
        # 1. 比较张数
        if len(self.pokes) > len(other.pokes):
            return True
        elif len(self.pokes) < len(other.pokes):
            return False
        # 2. 比较类型
        if self.type_ > other.type_:
            return True
        elif self.type_ < other.type_:
            return False
        # 3. 比较最小值
        self_min = min(poke.value for poke in self.pokes)
        other_min = min(poke.value for poke in other.pokes)
        return self_min > other_min
    def __ge__(self, other: 'PokeCombine') -> bool:
        return self > other or self == other
    def __eq__(self, other: 'PokeCombine') -> bool:
        self_values = sorted([poke.value for poke in self.pokes])
        other_values = sorted([poke.value for poke in other.pokes])
        return self_values == other_values
    
## Server statics

GAMER = {}
'''gid: {gamer: Gamer, startTime: datetime}'''
PLAYER = {}
'''name: {player: Player, websocket: Websocket, gamer: Gamer|None}'''

def find_player(name:str) -> Player|None:
    '''Find player by name'''
    global PLAYER
    global GAMER
    if name in PLAYER:
        return PLAYER[name]['player']
    return None

async def find_player_ws(name:str, websocket: Websocket, gamer: Gamer|None = None) -> Player:
    '''Find player by name. Raise error to client. If gamer specified, player must be in the game'''
    global PLAYER
    global GAMER
    if name in PLAYER:
        if gamer and PLAYER[name]['gamer'] != gamer:
            raise AssertionError('Player not in the game')
        return PLAYER[name]['player']
    else:
        raise AssertionError('Player not found')

def find_game(gid:str) -> Gamer|None:
    '''Find game by gid'''
    global PLAYER
    global GAMER
    if gid in GAMER:
        return GAMER[gid]['gamer']
    return None

async def find_game_ws(gid:str, websocket: Websocket, name: str = '') -> Gamer:
    '''Find game by websocket. Raise error to client. If name specified, player must be in the game'''
    global PLAYER
    global GAMER
    if gid in GAMER:
        gamer:Gamer = GAMER[gid]['gamer']
        if name == '' or gamer._has_player(find_player(name)):
            return GAMER[gid]['gamer']
        raise AssertionError('You are not in the game.')
    raise AssertionError('Game not found.')

def get_websockets(gid:str) -> list[Websocket]:
    '''Get all participants of the game'''
    global PLAYER
    global GAMER
    ret = []
    if gid not in GAMER:
        return ret
    gamer: Gamer = GAMER[gid]['gamer']
    for player in gamer.players:
        ret.append(PLAYER[player.name]['websocket'])
    return ret
