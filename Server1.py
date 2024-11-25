# server.py
import socket
import threading

# 配置服务器
SERVER_IP = '0.0.0.0'
VIDEO_PORT = 5004
AUDIO_PORT = 5005

# 创建UDP套接字
video_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
audio_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

video_socket.bind((SERVER_IP, VIDEO_PORT))
audio_socket.bind((SERVER_IP, AUDIO_PORT))

print(f"服务器已启动，监听视频端口 {SERVER_IP}:{VIDEO_PORT} 和音频端口 {SERVER_IP}:{AUDIO_PORT}")


def handle_video():
    while True:
        try:
            data, client_address = video_socket.recvfrom(65535)
            if not data:
                continue
            print(f"[视频] 收到来自 {client_address} 的数据包，大小：{len(data)} 字节")

            video_recv_port = 5006
            video_socket.sendto(data, (client_address[0], video_recv_port))
        except Exception as e:
            print(f"[视频] 发生错误: {e}")
            break


def handle_audio():
    while True:
        try:
            data, client_address = audio_socket.recvfrom(65535)
            if not data:
                continue
            print(f"[音频] 收到来自 {client_address} 的数据包，大小：{len(data)} 字节")
            # 回传到客户端的接收音频端口（5007）
            audio_recv_port = 5007
            audio_socket.sendto(data, (client_address[0], audio_recv_port))
        except Exception as e:
            print(f"[音频] 发生错误: {e}")
            break


# 启动线程处理视频和音频
video_thread = threading.Thread(target=handle_video, daemon=True)
audio_thread = threading.Thread(target=handle_audio, daemon=True)

video_thread.start()
audio_thread.start()

# 保持主线程运行
try:
    while True:
        pass
except KeyboardInterrupt:
    print("服务器关闭")
finally:
    video_socket.close()
    audio_socket.close()
