import random
from .states import GameState, PlayerState, PokeState, DEBUG
from .conn import bd
from .api import BROADCAST as BD, format, yellow
from .poke import Poke, PokeCombine
from .player import Player

from websockets import WebSocketClientProtocol as Websocket

class GameOperation:
    '''游戏操作
    
    type_: 操作类型
    
    -1: 游戏开始
    
    0: 出牌
    
    1: 摸牌
    
    2: 摸牌并立刻出牌

    -2: 游戏结束
    
    detail: 操作细节，游戏开始/游戏结束为None，出牌为PokeCombine，摸牌为Poke，摸牌并立刻出牌为Poke'''
    player: Player
    '''操作玩家'''
    type_: int
    '''操作类型'''
    detail: None|PokeCombine|Poke|Poke
    '''操作细节'''
    pos: int
    '''摸牌后将牌插入的位置'''
    def __init__(self, player: Player, type_: int, detail: PokeCombine|Poke|None, pos: int = -1) -> None:
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
            return f"{self.player.name} 摸牌 {self.detail}并立刻出牌"
        elif self.type_ == -1:
            return f"游戏开始: {self.player.name} 先手"
        elif self.type_ == -2:
            return f"游戏结束: {self.player.name} 打出了所有牌/让所有人摸牌"
    def full_log(self) -> str:
        if self.type_ == 0:
            return f"{self.player.name} 出牌 {self.detail}"
        elif self.type_ == 1:
            return f"{self.player.name} 摸牌 {self.detail}，插入成为第{self.pos + 1}张"
        elif self.type_ == 2:
            return f"{self.player.name} 摸牌{self.detail}，插入成为第{self.pos + 1}张并立刻出牌"
        elif self.type_ == -1:
            return f"游戏开始: {self.player.name} 先手"
        elif self.type_ == -2:
            return f"游戏结束: {self.player.name} 打出了所有牌/让所有人摸牌"
    def json(self) -> dict:
        return {
            'game_operation': str(self),
            'target_name': self.player.name,
            'type_': self.type_,
            'detail': self.detail.json() if self.detail else None,
        }

class Gamer:
    _is_online: bool
    '''是否为在线服务器'''
    _is_private: bool
    '''是否为私人房间'''
    # 游戏基本信息
    gid: int|str
    '''游戏ID'''
    players: list[Player]
    '''玩家列表'''
    host_idx: int
    '''房主index'''
    state: GameState
    '''游戏状态'''

    # 牌桌信息（所有玩家可获取）
    info: str
    '''游戏通知信息'''
    all_pokes: list[Poke]
    '''所有扑克牌对象'''
    game_history: list[GameOperation]
    '''游戏历史记录'''
    displayed_pokes: PokeCombine
    '''牌桌上的牌'''
    scout_and_show: list[Player]
    '''本局使用过 摸牌并立刻出牌 的玩家'''

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

    def __init__(self, gid: int|str, online: bool = True) -> None:
        self._is_online = online
        self._is_private = False

        self.gid = gid
        self.players = []
        self.host_idx = 0
        self.set_state(GameState.RECRUIT)

        self.info = "游戏招募中"
        self.all_pokes = []
        self.game_history = []
        self.displayed_pokes = PokeCombine([])
        self.scout_and_show = []

        self.total_score = {}
        self.extra_points = {}

    def _is_started(self) -> bool:
        return self.state.value >= GameState.INIT.value
    def _has_player(self, player: Player) -> bool:
        return player in self.players
    def _is_host(self, player: Player) -> bool:
        return self.players[self.host_idx] == player
    def json(self) -> dict:
        '''获取游戏信息'''
        return {
            'gid': self.gid,
            'players': [player.json() for player in self.players],
            'playing_num': len(self.players),
            'state': self.state.value,
            'info': self.info,
            'total_score': self.total_score,
            'extra_points': self.extra_points,
            'displayed_pokes': self.displayed_pokes.json(),
            'history': [str(op) for op in self.game_history]
        }
    def get_websockets(self) -> list[Websocket]:
        '''获取所有玩家的websocket'''
        assert all(player._is_logged for player in self.players), \
            "All players must be logged in"
        return [player.ws for player in self.players]

    def clear(self) -> None:
        '''清空单局游戏信息'''
        for poke in self.all_pokes:
            poke.clear()
        for player in self.players:
            player.clear()
        self.info = "游戏招募中"
        self.set_state(GameState.RECRUIT)
        if len(self.players) == 5:
            self.info = "游戏人数已满，等待开始"
            self.set_state(GameState.FULL)
        self.all_pokes = []
        self.game_history = []
        self.displayed_pokes = PokeCombine([])
        self.scout_and_show = []

        self.extra_points = {player.name: 0 for player in self.players}
    def get_player(self, name: str) -> Player|None:
        '''根据名字获取玩家'''
        for player in self.players:
            if player.name == name:
                return player
        return None
    def get_host(self) -> Player:
        '''获取房主'''
        return self.players[self.host_idx]
    def get_poke(self, value: tuple[str|int]|str) -> Poke|None:
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
   
    # 游戏招募阶段全体操作

    def add_player(self, player: Player) -> None:
        '''添加玩家，广播事件'''
        assert not self._is_private, \
            "Only public game can add player"
        if self.state == GameState.END:
            self.state = GameState.RECRUIT
            self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
            if len(self.players) == 5:
                self.state = GameState.FULL
                self.info = "游戏人数已满，等待开始"
        assert self.state == GameState.RECRUIT, \
            "Only recruiting game can add player"
        self.players.append(player)
        self.total_score[player.name] = 0
        self.extra_points[player.name] = 0
        if len(self.players) == 5:
            self.set_state(GameState.FULL)
            self.info = "游戏人数已满，等待开始"   
        if self._is_online:
            bd(self.get_websockets(), format(BD['playerJoin'], gid=self.gid, info=self.get_info(), target_name=player.name))
    def remove_player(self, player: Player) -> None:
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
        self.total_score.pop(player.name)
        self.extra_points.pop(player.name)
        if len(self.players) < 5:
            self.set_state(GameState.RECRUIT)
            self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
        if self._is_online:
            bd(self.get_websockets(), format(BD['playerLeave'], gid=self.gid, info=self.get_info(), target_name=player.name))

    def player_ready(self, player: Player) -> None|dict[str, str]:
        '''玩家准备，广播事件，当所有玩家准备完毕时返回初始化信息'''
        assert not self._is_started(), \
            "Game has already started"
        self.info = f"游戏招募中，已准备 {sum(1 for p in self.players if p.state == PlayerState.READY)}/{len(self.players)}"
        if self._is_online:
            bd(self.get_websockets(), format(BD['playerReady'], gid=self.gid, info=self.get_info(), target_name=player.name))
        if all(p.state == PlayerState.READY for p in self.players) and \
            2 <= len(self.players) <= 5:
            if DEBUG:
                print(yellow(f"Game {self.gid} is ready to start. Players: {[p.name for p in self.players]}"))
            self.set_state(GameState.INIT)
            self.info = "游戏初始化中"
            return self.init_game()
        return None
    def player_unready(self, player: Player) -> None:
        '''玩家取消准备，广播事件'''
        assert not self._is_started(), \
            "Game has already started"
        if self._is_online:
            bd(self.get_websockets(), format(BD['playerUnready'], gid=self.gid, info=self.get_info(), target_name=player.name))
    
    # 游戏招募阶段房主操作

    def lock_room(self, player: Player) -> None:
        '''锁定房间，广播事件'''
        assert not self._is_started(), \
            "Game has already started"
        assert self._is_host(player), \
            "Only host can lock room"
        self._is_private = True
        if self._is_online:
            bd(self.get_websockets(), format(BD['lockRoom'], gid=self.gid, info=self.get_info()))
    def unlock_room(self, player: Player) -> None:
        '''解锁房间，广播事件'''
        assert not self._is_started(), \
            "Game has already started"
        assert self._is_host(player), \
            "Only host can unlock room"
        self._is_private = False
        if self._is_online:
            bd(self.get_websockets(), format(BD['unlockRoom'], gid=self.gid, info=self.get_info()))
    def set_host(self, player: Player|str) -> None:
        '''设置房主，广播事件'''
        assert not self._is_started(), \
            "Game has already started"
        assert self._is_host(player), \
            "Only host can set host"
        if isinstance(player, str):
            player = self.get_player(player)
        assert player in self.players, \
            "Player must be in the game"
        self.host_idx = self.players.index(player)
        if self._is_online:
            bd(self.get_websockets(), format(BD['setHost'], gid=self.gid, info=self.get_info(), target_name=player.name))
    
    # 游戏主程序

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
            2: 11,
            3: 12,
            4: 11,
            5: 9
        }
        player_and_poke = {player.name: '' for player in self.players}
        num = len(self.players)
        for i, player in enumerate(self.players):
            pokes = self.all_pokes[i*poke_nums[num]:(i+1)*poke_nums[num]]
            player.receive_pokes(pokes)
            player_and_poke[player.name] = ' '.join([str(poke) for poke in pokes]) + ',' + ' '.join([poke.str_disable for poke in pokes])
        # 检查并设置玩家状态
        for player in self.players:
            assert player.is_ready(), \
                f"All players must be ready. {player.name} is not ready."
            player.set_state(PlayerState.INIT)
        # 检查牌状态
        distributed_pokes_num = len(self.players) * poke_nums[num]
        assert all(poke.is_ready() for poke in self.all_pokes[:distributed_pokes_num]), \
            "All pokes must be ready"
        # 初始化牌局信息
        self.displayed_pokes = PokeCombine([])
        self.extra_points = {player.name: 0 for player in self.players}
        self.info = "游戏开始，玩家选择起始手牌正反序"
        self.init_finish = [False for _ in self.players]
        # 通知玩家游戏开始，选择牌序
        for player in self.players:
            player.game_start()
        if self._is_online:
            bd(self.get_websockets(), format(BD['gameInit'], gid=self.gid, info=self.get_info()))
        return player_and_poke
    def player_init_finish(self, player: Player) -> None:
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
            if DEBUG:
                print(yellow(f"Game {self.gid} starts!. Players: {[p.name for p in self.players]}"))
            self.set_state(GameState.PLAYING)
            self.info = "游戏开始"
            if self._is_online:
                bd(self.get_websockets(), format(BD['gameStart'], gid=self.gid, info=self.get_info(), table=self.displayed_pokes.json()))
            # 第一个玩家开始
            first_player = random.choice(self.players) # TODO
            self.game_history.append(GameOperation(first_player, -1, None))
            self.player_turn_act(first_player)

    def player_turn_act(self, player: Player) -> None:
        '''通知玩家回合开始，广播事件'''
        if self._is_online:
            bd(self.get_websockets(), format(BD['gameAction'], gid=self.gid, info=self.get_info(), target_name=player.name, table=self.displayed_pokes.json(), op=self.game_history[-1].json()))
        assert self.state == GameState.PLAYING, \
            "Ingame Error: Only playing game can player turn act"
        assert player.state == PlayerState.WAIT, \
            "Ingame Error: Only player in wait state can act"
        player.set_state(PlayerState.TURN)
        player.turn_act()
    def player_turn_end(self, op: tuple|GameOperation) -> tuple[bool, str|Player|None]:
        '''玩家回合结束，将会广播事件，事件非法时返回False和错误信息，否则返回True和下一位玩家，若有玩家胜利则返回True和None'''
        if isinstance(op, tuple):
            op = GameOperation(*op)
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
            if (last_idx + 1 - target_idx) % len(self.players) != 0:
                return False, "Only next player in turn can play"
            if op.type_ == 0 and self.displayed_pokes >= op.detail:
                return False, f"Pokes must be greater than table's (0)\n{self.displayed_pokes} >= {op.detail}"
        elif last_op.type_ == 1:
            # 上一家摸牌
            last_idx = self.players.index(last_op.player)
            target_idx = self.players.index(op.player)
            if (last_idx + 1 - target_idx) % len(self.players) != 0:
                return False, "Only next player in turn can draw"
        elif last_op.type_ == 2:
            # 自己摸牌并立刻出牌
            last_idx = self.players.index(last_op.player)
            target_idx = self.players.index(op.player)
            if last_op.player != op.player:
                return False, "Only player himself in turn can draw and play"
            if op.type_ != 0:
                return False, "Player must show pokes after scout and show"
            if self.displayed_pokes >= op.detail:
                return False, "Pokes must be greater than table's (2)"
        self.game_history.append(op)
        # 处理操作
        next_player = self.players[(self.players.index(op.player) + 1) % len(self.players)]
        if op.type_ == 0:
            self.player_show(op)
        elif op.type_ == 1:
            self.player_scout(op)
        elif op.type_ == 2:
            if op.player in self.scout_and_show:
                self.game_history.pop()
                return False, "Player can only scout and show once in a game"
            self.scout_and_show.append(op.player)
            next_player = op.player
            self.player_scout(op)
        # 有玩家胜利
        if len(self.players) > 2 and \
            all(op.type_ == 1 for op in self.game_history[-len(self.players) + 1:]):
            assert self.beat_all(self.game_history[-len(self.players)].player), \
                "Ingame Error: Player win: beat all is not successful"
            return True, None
        if len(op.player.pokes) == 0:
            assert self.show_all(op.player), \
                "Ingame Error: Player win: show all is not successful"
            return True, None
        # 游戏继续，通知下一位玩家
        self.player_turn_act(next_player)
        return True, next_player
    
    def player_show(self, op: GameOperation) -> None:
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
        self.displayed_pokes = pokes
    def player_scout(self, op: GameOperation) -> None:
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
        self.displayed_pokes = PokeCombine(remain_pokes)

    def reward_point(self, player: Player) -> None:
        '''奖励得分：自己的牌被别人摸走'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can reward point"
        self.extra_points[player.name] += 1
    
    def show_all(self, player: Player) -> bool:
        '''游戏结束事件，玩家出完了所有手牌，广播事件'''
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
        self.info = f"游戏结束，{player.name}出完了他的手牌！"
        self.game_history.append(GameOperation(player, -2, None))
        if DEBUG:
                print(yellow(f"Game {self.gid} ends! {player.name} shows all pokes."))
        # 记录分数
        scores = {player.name: self.get_player_score(player) for player in self.players}
        for player in self.players:
            if player.name not in self.total_score:
                self.total_score[player.name] = 0
            self.total_score[player.name] += scores[player.name]
        # 通知玩家游戏结束
            player.game_ended()
        if self._is_online:
            bd(self.get_websockets(), format(BD['gameEnd'], gid=self.gid, info=self.get_info(), target_name=player.name, scores=scores))
        self.confirmed = [False for _ in self.players]
        return True
    def beat_all(self, player: Player) -> bool:
        '''游戏结束事件，玩家打败所有玩家，广播事件'''
        assert self.state == GameState.PLAYING, \
            "Only playing game can set win"
        # 修改玩家状态和游戏状态
        for p in self.players:
            p.set_state(PlayerState.END)
        self.set_state(GameState.END)
        self.info = f"游戏结束，{player.name}打败了所有玩家！"
        self.game_history.append(GameOperation(player, -2, None))
        if DEBUG:
                print(yellow(f"Game {self.gid} ends! {player.name} beats all players."))
        # 记录分数
        scores = {player.name: self.get_player_score(player) for player in self.players}
        for player in self.players:
            if player.name not in self.total_score:
                self.total_score[player.name] = 0
            self.total_score[player.name] += scores[player.name]
        # 通知玩家游戏结束
            player.game_ended()
        if self._is_online:
            bd(self.get_websockets(), format(BD['gameEnd'], gid=self.gid, info=self.get_info(), target_name=player.name, scores=scores))
        self.confirmed = [False for _ in self.players]
        return True
    def player_confirm_result(self, player: Player) -> None:
        '''玩家确认游戏结束，广播事件，仅允许END状态游戏中间态调用，否则无效'''
        if self.state == GameState.END:
            self.confirmed[self.players.index(player)] = True
            if self._is_online:
                bd(self.get_websockets(), format(BD['playerConfirm'], gid=self.gid, info=self.get_info(), target_name=player.name))
            # 清空单局游戏信息
            if all(self.confirmed):
                self._clear_state()
                self.state = GameState.RECRUIT
                self.info = "游戏招募中"
                if len(self.players) == 5:
                    self.state = GameState.FULL
                    self.info = "游戏人数已满，等待开始"

    # 游戏进行中随时调用的接口

    def get_player_score(self, player: Player) -> int:
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
            'table': self.displayed_pokes.json(),
            'last_op': self.game_history[-1].json() if len(self.game_history) > 0 else None
        }
