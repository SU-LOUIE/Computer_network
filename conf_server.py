import asyncio
import threading
from util import *
import socket


class ConferenceServer:
    def __init__(self, ):
        # async server
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.clients_info = None
        self.client_conns = None
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode


    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """

    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None
        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager
        self.clients = []
        self.clients_lock = threading.Lock()

    def handle_creat_conference(self, ):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """

    def handle_join_conference(self, conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """

    def handle_quit_conference(self):
        """
        quit conference (in-meeting request & or no need to request)
        """
        pass

    def handle_cancel_conference(self):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        pass

    async def request_handler(self, reader, writer):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """
        pass

    def handle_client(self, client_socket, addr):
        print(f"[连接] {addr} 已连接。")
        try:
            while True:
                # 接收帧长度
                raw_length = self.recvall(client_socket, 4)  # 前四个字节通常用来表示后面需要接收的字节数
                if not raw_length:
                    print(f"[断开] {addr} 已断开连接。")
                    break
                frame_length = int.from_bytes(raw_length, byteorder='big')  # 把它转换成一个整数

                frame_data = self.recvall(client_socket, frame_length)
                if not frame_data:
                    print(f"[断开] {addr} 已断开连接。")
                    break
                """
                对于服务器来说，其实不需要去分辨数据对应的客户端是谁，直接发给客户端自行去判断就行了
                客户端就要根据前16字节来判断是哪一个成员，然后找到对应的label去更新它的画面，如果没有的话还要新建一个画面，然后调整整个界面的布局
                """
                for c in self.clients:
                    if c != client_socket:
                        c.sendall(raw_length + frame_data)  # 然后把这个数据给传回去
        except Exception as e:
            print(f"[错误] 处理 {addr} 时出错: {e}")
        finally:
            client_socket.close()

    def recvall(self, conn, n):
        """接收n个字节的数据"""
        data = bytearray()
        while len(data) < n:
            packet = conn.recv(n - len(data))  # 每次都尝试获取剩下的
            if not packet:
                return None
            data.extend(packet)
        return data

    def start(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.server_ip, MAIN_SERVER_PORT))
        server_socket.listen(5)
        print('Server listening on port 8888')

        try:
            while True:
                client_socket, address = server_socket.accept()
                with self.clients_lock:
                    self.clients.append(client_socket)
                print(f"Accept connection from {address}")
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, address), daemon=True)
                client_thread.start()
        finally:
            server_socket.close()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
