import asyncio  
import websockets  
import datetime  
import json  
  
# 用于存储所有连接的客户端websocket对象  
connected_clients = set()  
  
async def client_handler(websocket, path):  
    # 将新连接的客户端添加到集合中  
    connected_clients.add(websocket)  
    try:  
        # 接收客户端发送的消息  
        async for message in websocket:  
            # 打印接收到的消息  
            print(f"Received from {websocket.remote_address}: {message}")  
    except websockets.exceptions.ConnectionClosed:  
        # 当客户端断开连接时，从集合中移除该客户端  
        connected_clients.remove(websocket)  
        print(f"Client disconnected: {websocket.remote_address}")  
  
async def send_time_to_clients():  
    # 每隔5秒向所有客户端发送当前时间和客户端名称  
    while True:  
        await asyncio.sleep(5)  
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
        message = json.dumps({"time": current_time})  
        connected_clients_copy = connected_clients.copy()
        for websocket in connected_clients_copy:  
            try:  
                # 发送消息给客户端  
                await websocket.send(message)  
            except websockets.exceptions.ConnectionClosed:  
                # 如果客户端已经断开连接，则从集合中移除  
                connected_clients.remove(websocket)  
  
async def main():  
    # 启动WebSocket服务器  
    async with websockets.serve(client_handler, "localhost", 8765):  
        # 在后台任务中定期向客户端发送时间  
        await send_time_to_clients()  
  
asyncio.run(main())