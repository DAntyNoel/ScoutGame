import asyncio  
import websockets  
import datetime  
import threading  
  
async def send_time_to_server(websocket):  
    # 每隔1秒向服务器发送当前时间  
    while True:  
        await asyncio.sleep(1)  
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")  
        await websocket.send(current_time)  
  
async def receive_from_server(websocket):  
    # 接收服务器发送的消息  
    async for message in websocket:  
        print(f"Received from server: {message}")  
  
async def main():  
    uri = "ws://localhost:8765"  
    async with websockets.connect(uri) as websocket:  
        # 启动两个后台任务，一个用于发送时间，一个用于接收时间  
        asyncio.create_task(send_time_to_server(websocket))  
        asyncio.create_task(receive_from_server(websocket))  
          
        # # 等待用户输入，以便在需要时关闭连接  
        input("Press Enter to close the connection...\n")  
  
# 在主线程中运行客户端  
if __name__ == "__main__":  
    asyncio.run(main())