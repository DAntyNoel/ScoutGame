import socket  
  
def server_program():  
    # 获取主机名  
    host = socket.gethostname()  
    port = 5000  # 初始化端口号  
  
    server_socket = socket.socket()  # 获取socket实例  
    server_socket.bind((host, port))  # 绑定主机地址和端口号  
  
    server_socket.listen(2)  # 配置socket监听连接，参数指定等待连接的最大数量  
    conn, address = server_socket.accept()  # 接受新连接  
    print("连接来自: " + str(address))  
    while True:  
        # 接收数据  
        data = conn.recv(1024).decode()  
        if not data:  
            # 如果没有数据，跳出循环  
            break  
        print("来自客户端的消息: " + str(data))  
        data = input(' -> ')  
        conn.send(data.encode())  # 发送数据  
  
    conn.close()  # 关闭连接  
  
if __name__ == '__main__':  
    server_program()