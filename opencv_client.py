import socket
import threading
import cv2
import time
from io import BytesIO
import numpy as np
from PIL import Image


class VideoConferenceClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port

        # 本地摄像头相关参数
        self.cap = None
        self.is_camera_on = False

        # 创建Socket连接
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.server_port))
        self.is_running = True

        # 启动接收视频的线程
        self.receive_thread = threading.Thread(target=self.receive_and_display, daemon=True)
        self.receive_thread.start()

    def toggle_camera(self):
        if not self.is_camera_on:
            # 打开摄像头
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("无法访问摄像头")
                return

            self.is_camera_on = True
            # 不要递归调用，直接开始显示摄像头画面
        else:
            self.is_camera_on = False
            if self.cap:
                self.cap.release()
                self.cap = None

    def update_video(self):
        """不断从摄像头捕获视频帧并更新到窗口"""
        if self.is_camera_on and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # 转换为RGB格式并显示
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # 压缩图像为JPEG格式
                buffer = BytesIO()
                image = Image.fromarray(frame_rgb).convert('RGB')
                image.save(buffer, format="JPEG")
                jpeg_data = buffer.getvalue()

                # 发送视频帧到服务器
                self.send_video(jpeg_data)

                # 显示本地视频
                self.local_video = frame

            cv2.waitKey(1)  # 等待1毫秒，继续显示下一个帧

    def send_video(self, jpeg_data):
        """将压缩的图像数据发送到服务器"""
        try:
            frame_length = len(jpeg_data)
            self.sock.sendall(frame_length.to_bytes(4, byteorder='big') + jpeg_data)
        except Exception as e:
            print(f"[错误] 发送视频数据失败: {e}")
            self.is_running = False

    def receive_and_display(self):
        """接收并显示从服务器回传的视频画面"""
        try:
            while self.is_running:
                # 接收视频帧的长度
                raw_length = self.recvall(4)
                if not raw_length:
                    print("[断开] 服务器已断开连接。")
                    self.is_running = False
                    break
                frame_length = int.from_bytes(raw_length, byteorder='big')

                # 接收视频帧数据
                frame_data = self.recvall(frame_length)
                if not frame_data:
                    print("[断开] 服务器已断开连接。")
                    self.is_running = False
                    break

                # 解压JPEG数据
                buffer = BytesIO(frame_data)
                img = Image.open(buffer)
                img = np.array(img)
                img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

                # 显示远程视频
                self.remote_video = img_bgr

                # 如果本地视频和远程视频都已经获取，拼接显示
                if hasattr(self, 'local_video') and hasattr(self, 'remote_video'):
                    # 横向拼接
                    combined_frame = np.hstack((self.local_video, self.remote_video))
                    cv2.imshow("Local and Remote Video", combined_frame)

                # 等待键盘事件，退出或继续
                if cv2.waitKey(1) & 0xFF == ord('q'):  # 按 'q' 键退出
                    break

        except Exception as e:
            print(f"[错误] 接收和显示线程出错: {e}")
            self.is_running = False

    def recvall(self, n):
        """接收n个字节的数据"""
        data = bytearray()
        while len(data) < n:
            packet = self.sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data

    def on_closing(self):
        """关闭客户端时释放资源"""
        print("[关闭] 关闭客户端。")
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        cv2.destroyAllWindows()  # 关闭OpenCV窗口


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'  # 服务器IP地址
    SERVER_PORT = 8888  # 服务器端口号
    client = VideoConferenceClient(SERVER_IP, SERVER_PORT)

    # 启动本地摄像头
    client.toggle_camera()

    # 在程序退出时清理资源
    try:
        while client.is_running:
            client.update_video()  # 只调用一次，不再递归
            time.sleep(0.03)  # 控制更新频率
    except KeyboardInterrupt:
        client.on_closing()
