from .states import PokeState

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .player import Player

class Poke:
    up: int
    '''正面数字'''
    down: int
    '''背面数字'''
    owner: 'Player'
    '''拥有者'''
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
    
    def __init__(self, up: int, down: int, side: bool = True) -> None:
        self.up = up
        self.down = down
        self.owner = None
        self.state = PokeState.WAITING
        self.side = side

    def json(self) -> str:
        return str(self) + ',' + self.str_disable
    def clear(self) -> None:
        '''清空牌局信息'''
        self.state = PokeState.WAITING
        self.side = True
        self.owner = None
    def is_ready(self) -> bool:
        '''牌局初始化的检查函数'''
        return (
            self.state == PokeState.HIDE and
            self.owner is not None
        )

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
    
    def set_state(self, state: PokeState|int) -> None:
        '''设置牌状态'''
        if isinstance(state, int):
            state = PokeState(state)
        elif not isinstance(state, PokeState):
            raise AssertionError(
                "State must be an instance of PokeState or int"
            )
        self.state = state
    
    def set_owner(self, owner: 'Player') -> None:
        '''设置牌拥有者'''
        self.owner = owner
    
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
    def __len__(self) -> int:
        return len(self.pokes)   
    def __str__(self) -> str:
        return ' '.join(str(poke) for poke in self.pokes)
    
    def __init__(self, pokes: list[Poke]) -> None:
        self.pokes = pokes
        self.type_ = self.calculate() 
    def json(self) -> str:
        return ' '.join(str(poke) for poke in self.pokes) + ',' + ' '.join(poke.str_disable for poke in self.pokes)
    def calculate(self) -> int:
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