from .static import *

import secrets
from datetime import datetime

##############
# Game Open  #
##############

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

async def playerLeave(query: Query):
    '''Player leave the game'''
    gamer = query.gamer
    query.player.quit_game()
    if len(gamer.players) == 0:
        del GAMER[gamer.gid]
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} leaves game."), f" Websocket: {id(query.ws)}")


async def playerReady(query: Query):
    '''Player ready for the game'''
    pap = query.player.ready_for_game()
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} ready in game {query.gid}."), f" Websocket: {id(query.ws)}")
        print(green(f"Player and pokes: {pap}"))
    if pap:
        # All players are ready
        # Distribute pokes
        for nm, pks in pap.items():
            ply = await find_player_ws(nm, gamer=query.gamer)
            tgt_ws = ply.ws
            await send(tgt_ws, format(S2C['distributePokes'], gid=query.gid, name=nm, pokes=pks, seq=-1))
            if DEBUG:
                print(yellow(f"Send pokes {pks} to Player {nm}, target websocket {id(tgt_ws)}."), f" Websocket: {id(query.ws)}")

async def playerUnready(query: Query):
    '''Player unready for the game'''
    query.player.unready_for_game()
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} unready in game {query.gid}."), f" Websocket: {id(query.ws)}")

##############
# Game Init  #
##############

async def choosePokeOrder(query: Query):
    '''Choose poke order 选择手牌正反序'''
    reverse = bool(int(query.get('reverse')))
    query.player.choose_pokes_side(reverse)
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} choose poke order{' ' if reverse else ' not '}reversed in game {query.gid}."), f" Websocket: {id(query.ws)}")

##############
# Game Start #
##############

async def show(query: Query):
    '''Show pokes 出牌，指定手牌索引，b_index从零开始，e_index为-1代表到最后一张牌。
    
    出牌，pokes为两组数，第一组为正序，第二组为反序，两组之间逗号分隔，数之间空格分隔，T代表10。
    '''
    b_index = int(query.get('b_index'))
    e_index = int(query.get('e_index'))
    pokes = query.player.choose_pokes_index(b_index, e_index)
    nxt = query.player.show(pokes)
    await query.ok()
    if DEBUG:
        if nxt:
            print(green(f"Player {query.name} shows pokes {pokes.json()} in game {query.gid}. Next one {nxt.name}"), f" Websocket: {id(query.ws)}")
        else:
            print(green(f"Player {query.name} shows pokes {pokes.json()} in game {query.gid}. Game ends!"), f" Websocket: {id(query.ws)}")
    
async def scout(query: Query):
    '''Scout pokes 摸牌
    
    index: [0, -1],摸牌位置

    reverse: bool[0, 1],是否反序

    insert_to: int,插入位置
    '''
    index = int(query.get('index'))
    assert index in [0, -1], 'Invalid index. You can only draw from the top or the bottom of the deck.'
    reverse = bool(int(query.get('reverse')))
    insert_to = int(query.get('insert_to'))
    nxt = query.player.scout(index, reverse, insert_to)
    await query.ok()
    if DEBUG:
        if nxt:
            print(green(f"Player {query.name} scout pokes in game {query.gid}. Next one {nxt.name}"), f" Websocket: {id(query.ws)}")
        else:
            print(green(f"Player {query.name} scout pokes in game {query.gid}. Game ends!"), f" Websocket: {id(query.ws)}")

async def scoutAndShow(query: Query):
    '''Scout and show pokes 摸牌并出牌。该回合仅摸牌，下回合再出牌
    
    index: [0, -1],摸牌位置

    reverse: bool[0, 1],是否反序

    insert_to: int,插入位置
    '''
    index = int(query.get('index'))
    assert index in [0, -1], 'Invalid index. You can only draw from the top or the bottom of the deck.'
    reverse = bool(int(query.get('reverse')))
    insert_to = int(query.get('insert_to'))
    nxt = query.player.scout_and_show(index, reverse, insert_to)
    await query.ok()
    if DEBUG:
        if nxt:
            print(green(f"Player {query.name} scout-and-play in game {query.gid}. Next one {nxt.name}"), f" Websocket: {id(query.ws)}")
        else:
            print(red(f"Player {query.name} scout-and-play in game {query.gid}. Game ends unexpectedly!"), f" Websocket: {id(query.ws)}")

##############
#  Game End  #
##############

async def confirmResult(query: Query):
    '''Confirm result 确认结果'''
    query.player.confirm_result()
    await query.ok()
    if DEBUG:
        print(green(f"Player {query.name} confirm result in game {query.gid}."), f" Websocket: {id(query.ws)}")

##############
# Game Func  #
##############

async def getPokes(query: Query):
    '''Get pokes 获取本局手牌，pokes为两组数，第一组为有效，第二组为无效，两组之间逗号分隔，数之间空格分隔，T代表10。'''
    await query.ok(query.player.get_pokes())
    if DEBUG:
        print(yellow(f"Player {query.name} queries pokes in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getScore(query: Query):
    '''Get score 获取本局当前得分'''
    await query.ok(query.gamer.ingame_score(query.player))
    if DEBUG:
        print(yellow(f"Player {query.name} queries score in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getInfo(query: Query):
    '''Get info 获取游戏信息（与broadcast相同）'''
    await query.ok(query.gamer.get_info())
    if DEBUG:
        print(yellow(f"Player {query.name} queries info in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getGameInfo(query: Query):
    '''Get game info 获取游戏信息'''
    # 返回值：
    # turn: int,当前回合
    # players: [str],玩家名单
    # goal_pokes: [int],得分牌
    # remain_pokes: [int],剩余手牌
    # extra_points: [int],额外得分
    # table: [str],桌面上的牌
    # last_op: dict,上一次操作
    await query.ok(query.gamer.get_game_info())
    if DEBUG:
        print(yellow(f"Player {query.name} queries game info in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getTotalScore(query: Query):
    '''Get total score 获取所有玩家累计总得分'''
    await query.ok(query.gamer.total_score)
    if DEBUG:
        print(yellow(f"Player {query.name} queries total score in game {query.gid}."), f" Websocket: {id(query.ws)}")

async def getHistory(query: Query):
    '''Get history 获取本局历史出牌记录'''
    await query.ok([str(op) for op in query.gamer.get_history()])
    if DEBUG:
        print(yellow(f"Player {query.name} queries history in game {query.gid}."), f" Websocket: {id(query.ws)}")

