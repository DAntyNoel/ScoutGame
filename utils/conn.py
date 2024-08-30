import json

from websockets import WebSocketClientProtocol as Websocket
from websockets.asyncio.server import broadcast as bd

async def send(websocket: Websocket, data: dict) -> None:
    '''Send data to client'''
    await websocket.send(json.dumps(data))

async def recv(websocket: Websocket) -> dict:
    '''Receive data from client'''
    resp = json.loads(await websocket.recv())
    if not isinstance(resp, dict):
        rescue = eval(resp)
        if not isinstance(rescue, dict):
            return {}
        return rescue
    return resp

async def error(seq: int, websocket: Websocket, message: str, code: int = -1) -> None:
    '''Send error message to client'''
    await send(websocket, {
        'code': code,
        'seq': seq,
        'message': message
    })

async def ok(seq: int, websocket: Websocket, message: str|list|dict = 'ok') -> None:
    '''Respond ok/message to client'''
    await send(websocket, {
        'code': 0,
        'seq': seq,
        'message': message
   })