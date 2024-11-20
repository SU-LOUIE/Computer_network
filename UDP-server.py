import socket
import threading

"""
这是测试用的server，以udp传送音频和视频，但是文本还是用tcp比价好
"""
class VideoConferenceServerUDP:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

        self.clients = set()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.server_ip, self.server_port))

        print(f"[启动] 服务器正在 {self.server_ip}:{self.server_port} 上运行...")

    def start(self):
        threading.Thread(target=self.receive_data, daemon=True).start()

    def receive_data(self):
        """接收客户端发送的视频帧"""
        while True:
            try:
                frame_data, client_address = self.sock.recvfrom(65536)

                if client_address not in self.clients:
                    self.clients.add(client_address)
                    print(f"[连接] 新客户端已加入: {client_address}")

                self.broadcast(frame_data, client_address)
            except Exception as e:
                print(f"[错误] 接收数据失败: {e}")

    def broadcast(self, data, source_address):
        for client in list(self.clients):
            # if client != source_address:
            try:
                self.sock.sendto(data, client)
            except Exception as e:
                print(f"[错误] 向 {client} 转发数据失败: {e}")
                self.clients.remove(client)

    def stop(self):
        print("[关闭] 服务器已关闭。")
        self.sock.close()


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 8888
    server = VideoConferenceServerUDP(SERVER_IP, SERVER_PORT)
    server.start()

    try:
        while True:
            pass  # 保持主线程运行
    except KeyboardInterrupt:
        server.stop()
