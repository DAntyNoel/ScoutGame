import asyncio  
import websockets  
  
async def hello():  
    async with websockets.connect("ws://localhost:8765") as websocket:  
        await websocket.send("Hello world!")  
        response = await websocket.recv()  
        print("Received:", response)  
  
asyncio.run(hello())