import socket  
  
def client_program():  
    host = socket.gethostname()  # 服务器主机名  
    port = 5000  # 服务器端口号  
  
    client_socket = socket.socket()  # 实例化socket  
    client_socket.connect((host, port))  # 连接到服务器  
  
    message = input(" -> ")  # 允许用户输入信息  
  
    while message.lower().strip() != 'bye':  
        client_socket.send(message.encode())  # 发送消息  
        data = client_socket.recv(1024).decode()  # 接收响应  
  
        print('收到来自服务器的消息: ' + data)  # 显示接收到的数据  
  
        message = input(" -> ")  # 再次输入信息  
  
    client_socket.close()  # 关闭连接  
  
if __name__ == '__main__':  
    client_program()