
import asyncio
import json

from websockets.asyncio.server import serve

import server
from server import (
    Player, Gamer,
    Query, Websocket,
    PLAYER, GAMER, 
    red, green, yellow,
    find_player, find_player_ws,
    send, recv
)

DEBUG = True


async def handler(websocket: Websocket):
    '''Server Thread'''
    global PLAYER
    global GAMER
    async for msg in websocket:
        event = json.loads(msg)
        if isinstance(event, str):
            event = eval(event)

        # Response Event
        if 'code' in event.keys() and 'message' in event.keys():
            if not event['code'] == 0:
                print(red(f"error(code={event['code']}): {event['message']}."), f" Websocket: {id(websocket)}")
            elif DEBUG:
                print(green(f"Receive response: {event['message']}."), f" Websocket: {id(websocket)}")
            continue
        
        # Request Event
        try:
            assert 'func' in event.keys(), 'Request error: `func` required'
            f = getattr(server, event['func'])
            await f(Query(event, websocket))
        except AssertionError as e:
            await Query(event, websocket).error(message=str(e), code=400)
            if DEBUG:
                print(red(f"Error: {e}."), f" Websocket: {id(websocket)}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            await Query(event, websocket).error(message=str(e))
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
    assert event['func'] == 'login', 'Connection error: Please login first.'
    if DEBUG:
        print(green(f"Websocket {websocket} connected."))
    name = event['name']
    if find_player(name) is not None:
        await Query(event, websocket).error(message='Player already exists', code=403)
        if DEBUG:
            print(red(f"Player {event['name']} already exists."), f" Websocket: {id(websocket)}")
    else:
        player = Player(name)
        player.login(websocket)
        PLAYER[name] = player
        if DEBUG:
            print(green(f"Player {name} created."), f" Websocket: {id(websocket)}")
        await Query(event, websocket).ok()
    try:
        await handler(websocket)
    except Exception as e:
        del PLAYER[name]
        if DEBUG:
            print(red(f"Connection closed to websocket: {id(websocket)}. \n\tError: {e}."))

async def main():
    async with serve(conn, "localhost", 8001):
        await asyncio.get_running_loop().create_future()  # run forever


if __name__ == "__main__":
    asyncio.run(main())

