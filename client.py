import websockets
from websockets import WebSocketClientProtocol as Websocket
import json

from utils import yellow, red, green
from utils import format, C2S

QUERY = C2S['main']
GET = C2S['subjective']
SYS = C2S['system']
seq_num = 0

async def connect(url: str) -> Websocket:
    '''Connect to server'''
    return await websockets.connect(url)

async def process_bd_event(event: dict) -> None:
    '''Process broadcast event'''
    assert 'func' in event.keys(), 'Broadcast error: `func` required'
    assert 'info' in event.keys(), 'Broadcast error: `info` required'
    assert 'gid'  in event.keys(), 'Broadcast error: `gid`  required'
    # TODO
    print(yellow('Recieve broadcast event:\n'), event, '')
    
async def query(websocket: Websocket, data: dict, **kwargs) -> dict:
    '''Query'''
    global seq_num
    await websocket.send(format(data, seq=seq_num, **kwargs))
    seq_num += 1
    while 1:
        response = json.loads(await websocket.recv())
        if not isinstance(response, dict):
            rescue = eval(response)
            if not isinstance(rescue, dict):
                print(red('Rescue failed: invalid response:'), rescue)
                continue
            response = rescue
        if 'seq' in response.keys():
            if int(response['seq']) < 0:
                print(yellow('Recieve server active message:'), response)
                continue
            else:
                if 'code' in response.keys() and 'message' in response.keys():
                    return response
        else:
            await process_bd_event(response)
