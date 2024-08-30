
import asyncio
import json
import secrets
from datetime import datetime

from websockets.asyncio.server import serve
from websockets import WebSocketClientProtocol as Websocket
from utils import (
    Player, Gamer,
    PLAYER, GAMER, 
    S2C, format, red, green, yellow,
    find_game, find_game_ws,
    find_player, find_player_ws,
    error, ok, send, recv,
)

DEBUG = True


async def handler(websocket: Websocket):
    '''Server Thread'''
    global PLAYER
    global GAMER
    async for msg in websocket:
        event = json.loads(msg)
        seq = int(event['seq'])

        # Response Event
        if 'code' in event.keys() and 'message' in event.keys():
            if not event['code'] == 0:
                print(red(f"error(code={event['code']}): {event['message']}."), f" Websocket: {id(websocket)}")
            elif DEBUG:
                print(green(f"Receive response: {event['message']}."), f" Websocket: {id(websocket)}")
            continue
        
        # Request Event
        assert 'func' in event.keys(), 'Request error: `func` required'
        assert 'name' in event.keys(), 'Request error: `name` required'
        assert 'gid'  in event.keys(), 'Request error: `gid`  required'
        func = str(event['func'])
        name = str(event['name'])
        gid  = str(event['gid'])
        try:
            player:Player = await find_player_ws(event['name'], websocket)
            if func == 'playerJoin':
                # Player join
                if gid == '':
                    # Alloc new game
                    gid = secrets.token_hex(6)
                    gamer = Gamer(gid)
                    GAMER[gid] = {
                        'gamer': gamer,
                        'startTime': datetime.now(),
                    }
                else:
                    # Join existing game
                    gamer = find_game(gid)
                    if gamer is None:
                        await error(seq, websocket, message='Game not found', code=404)
                        if DEBUG:
                            print(red(f"Game {gid} not found."), f" Websocket: {id(websocket)}")
                        continue
                    if gamer.playing_num == 5:
                        await error(seq, websocket, message='Game is full', code=403)
                        if DEBUG:
                            print(red(f"Game {gid} is full."), f" Websocket: {id(websocket)}")
                        continue
                player.set_gamer(gamer)
                PLAYER[name]['gamer'] = gamer
                await ok(seq, websocket, message=gid)
                if DEBUG:
                    print(green(f"Player {name} joined game {gid}."), f" Websocket: {id(websocket)}")
                continue
            
            # Methods below require gid, and player must be in the game

            gamer:Gamer = await find_game_ws(gid, websocket, name)
            if func == 'playerLeave':
                # Player leave
                player.quit_game()
                PLAYER[name]['gamer'] = None
                if gamer.playing_num == 0:
                    del GAMER[gid]
                await ok(seq, websocket)
                if DEBUG:
                    print(green(f"Player {name} left game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'playerReady':
                # Player ready
                player_and_poke = player.ready_for_game()
                await ok(seq, websocket)
                if DEBUG:
                    print(green(f"Player {name} ready in game {gid}."), f" Websocket: {id(websocket)}")
                    print(green(f"Player and pokes: {player_and_poke}"))
                if player_and_poke:
                    # All players are ready
                    # Distribute pokes
                    for nm, pks in player_and_poke.items():
                        # Check validity
                        await find_player_ws(nm, websocket, gamer)
                        tgt_wbskt = PLAYER[nm]['websocket']
                        await send(tgt_wbskt, format(S2C['distributePokes'], gid=gid, name=nm, pokes=pks, seq=-1))
                        if DEBUG:
                            print(yellow(f"Send pokes {pks} to Player {nm}, target websocket {id(tgt_wbskt)}."), f" Websocket: {id(websocket)}")
            elif func == 'playerUnready':
                # Player unready
                player.unready_for_game()
                await ok(seq, websocket)
                if DEBUG:
                    print(green(f"Player {name} unready in game {gid}."), f" Websocket: {id(websocket)}")

        # Methods below require game initiated

            if func == 'choosePokeOrder':
                # Choose poke side
                # 选择手牌正反序
                reverse = bool(int(event['reverse']))
                player.choose_pokes_side(reverse)
                await ok(seq, websocket)
                if DEBUG:
                    print(green(f"Player {name} choose poke order{' ' if reverse else ' not '}reversed in game {gid}."), f" Websocket: {id(websocket)}")

        # Methods below require game started

            elif func == 'show':
                # Play pokes
                # 出牌，指定手牌索引，b_index从零开始，e_index为-1代表到最后一张牌。
                # # 出牌，pokes为两组数，第一组为正序，第二组为反序，两组之间逗号分隔，数之间空格分隔，T代表10。
                b_index = int(event['b_index'])
                e_index = int(event['e_index'])
                pokes = player.choose_pokes_index(b_index, e_index)
                nxt = player.show(pokes)
                await ok(seq, websocket)
                if DEBUG:
                    if nxt:
                        print(green(f"Player {name} play pokes {pokes} in game {gid}. Next one {nxt.name}"), f" Websocket: {id(websocket)}")
                    else:
                        print(green(f"Player {name} play pokes {pokes} in game {gid}. He wins!"), f" Websocket: {id(websocket)}")
            elif func == 'scout':
                # Draw pokes
                # 摸牌\n index: [0, -1],摸牌位置\n reverse: bool[0, 1],是否反序\n insert_to: int,插入位置
                index = int(event['index'])
                assert index in [0, -1], 'Invalid index. You can only draw from the top or the bottom of the deck.'
                reverse = bool(int(event['reverse']))
                insert_to = int(event['insert_to'])
                nxt = player.scout(index, reverse, insert_to)
                await ok(seq, websocket)
                if DEBUG:
                    if nxt:
                        print(green(f"Player {name} draw pokes in game {gid}. Next one {nxt.name}"), f" Websocket: {id(websocket)}")
                    else:
                        print(yellow(f"Player {name} draw pokes in game {gid}. Game ends unexpectedly!"), f" Websocket: {id(websocket)}")
            elif func == 'confirmResult':
                # Confirm result
                # 确认结果
                player.confirm_result()
                await ok(seq, websocket)
                if DEBUG:
                    print(green(f"Player {name} confirm result in game {gid}."), f" Websocket: {id(websocket)}")

        # Methods below is accepted when game has once started

            elif func == 'getPokes':
                # Get pokes
                # 获取本局手牌，pokes为两组数，第一组为有效，第二组为无效，两组之间逗号分隔，数之间空格分隔，T代表10。
                await ok(seq, websocket, player.get_pokes())
                if DEBUG:
                    print(yellow(f"Player {name} queries pokes in game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'getScore':
                # Get score
                # 获取本局当前得分
                await ok(seq, websocket, gamer.ingame_score(player))
                if DEBUG:
                    print(yellow(f"Player {name} queries score in game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'getInfo':
                # Get info
                # 获取游戏信息（与broadcast相同）
                await ok(seq, websocket, gamer.get_info())
                if DEBUG:
                    print(yellow(f"Player {name} queries info in game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'getGameInfo':
                # Get game info
                # 获取本局公开信息
                # 返回值：
                # turn: int,当前回合
                # players: [str],玩家名单
                # goal_pokes: [int],得分牌
                # remain_pokes: [int],剩余手牌
                # extra_points: [int],额外得分
                # table: [str],桌面上的牌
                # last_op: dict,上一次操作
                await ok(seq, websocket, gamer.get_game_info())
                if DEBUG:
                    print(yellow(f"Player {name} queries game info in game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'getTotalScore':
                # Get total score
                # 获取所有玩家累计总得分
                await ok(seq, websocket, gamer.total_score)
                if DEBUG:
                    print(yellow(f"Player {name} queries total score in game {gid}."), f" Websocket: {id(websocket)}")
            elif func == 'getHistory':
                # Get history
                # 获取本局历史出牌记录
                await ok(seq, websocket, [str(op) for op in gamer.get_history()])
                if DEBUG:
                    print(yellow(f"Player {name} queries history in game {gid}."), f" Websocket: {id(websocket)}")
        except AssertionError as e:
            await error(seq, websocket, message=str(e), code=400)
            if DEBUG:
                print(red(f"Error: {e}."), f" Websocket: {id(websocket)}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            await error(seq, websocket, message=str(e))
            if DEBUG:
                print(red(f"Error: {e}."), f" Websocket: {id(websocket)}")
        finally:
            pass

async def conn(websocket: Websocket):
    '''
    Handle connection
    '''
    global PLAYER
    global GAMER
    event = await recv(websocket)
    seq = event['seq']
    assert event['func'] == 'connect', 'Connection error: `connect` required'
    if DEBUG:
        print(green(f"Websocket {websocket} connected."))
    name = event['name']
    if find_player(name) is not None:
        await error(seq, websocket, message='Player already exists', code=403)
        if DEBUG:
            print(red(f"Player {event['name']} already exists."), f" Websocket: {id(websocket)}")
    else:
        player = Player(name)
        PLAYER[name] = {
            'player': player,
            'websocket': websocket,
        }
        if DEBUG:
            print(green(f"Player {name} created."), f" Websocket: {id(websocket)}")
        await ok(seq, websocket)
    try:
        await handler(websocket)
    except Exception as e:
        PLAYER.pop(name)
        if DEBUG:
            print(red(f"Connection closed to websocket: {id(websocket)}. \n\tError: {e}."))

async def main():
    async with serve(conn, "localhost", 8001):
        await asyncio.get_running_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())

