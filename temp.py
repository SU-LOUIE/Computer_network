import socket
import threading
import cv2
import time
from PIL import Image, ImageTk
import tkinter as tk
from io import BytesIO
import numpy as np


class VideoConferenceClient:
    def __init__(self, server_ip, server_port, root):
        self.server_ip = server_ip
        self.server_port = server_port
        self.root = root
        self.root.title("多人视频会议客户端")
        self.root.geometry("1500x600")  # 调整窗口大小
        self.root.resizable(False, False)

        # 创建主框架（用于容纳本地视频和远程视频）
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # 配置grid的权重，使左右两列的宽度相等
        self.main_frame.grid_columnconfigure(0, weight=1)  # 左侧视频区域
        self.main_frame.grid_columnconfigure(1, weight=1)  # 右侧视频区域

        # 左边的框架用于显示本地视频
        self.local_frame = tk.Frame(self.main_frame)
        self.local_frame.grid(row=0, column=0, sticky="nsew", padx=10)
        self.local_title = tk.Label(self.local_frame, text="本地视频", font=("Arial", 14, "bold"))
        self.local_title.pack(side="top", pady=5)
        # 右边的框架用于显示远程视频
        self.remote_frame = tk.Frame(self.main_frame)
        self.remote_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        self.remote_title = tk.Label(self.remote_frame, text="远程视频", font=("Arial", 14, "bold"))
        self.remote_title.pack(side="top", pady=5)
        # 本地摄像头视频显示
        self.local_video_label = tk.Label(self.local_frame)
        self.local_video_label.pack(fill="both", expand=True)

        # 远程视频显示
        self.remote_video_label = tk.Label(self.remote_frame)
        self.remote_video_label.pack(fill="both", expand=True)

        # 摄像头相关参数
        self.cap = None
        self.is_camera_on = False

        # 控制摄像头的按钮
        self.camera_button = tk.Button(self.root, text="打开摄像头", command=self.toggle_camera)
        self.camera_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)

        # 连接到服务器
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
            self.camera_button.config(text="关闭摄像头")
            self.update_video()  # 开始显示摄像头画面
        else:
            # 关闭摄像头
            self.is_camera_on = False
            self.camera_button.config(text="打开摄像头")
            if self.cap:
                self.cap.release()
                self.cap = None
            self.local_video_label.config(image='')  # 清空显示的画面

    def update_video(self):
        """不断从摄像头捕获视频帧并更新到 UI 界面"""
        if self.is_camera_on and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # 转换为RGB格式并显示在UI
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb).convert('RGB')
                image_tk = ImageTk.PhotoImage(image)
                self.local_video_label.config(image=image_tk)
                self.local_video_label.image = image_tk  # 保持对图片的引用

                # 压缩图像为JPEG格式
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                jpeg_data = buffer.getvalue()

                # 发送视频帧到服务器
                self.send_video(jpeg_data)

            self.root.after(10, self.update_video)  # 每10ms更新一次

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
                imgtk = ImageTk.PhotoImage(image=img)

                # 更新远程视频显示
                self.remote_video_label.config(image=imgtk)
                self.remote_video_label.image = imgtk  # 保持对图片的引用
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
        self.root.quit()
        self.root.destroy()


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'  # 服务器IP地址
    SERVER_PORT = 8888  # 服务器端口号
    root = tk.Tk()
    client = VideoConferenceClient(SERVER_IP, SERVER_PORT, root)
    root.protocol("WM_DELETE_WINDOW", client.on_closing)  # 绑定关闭窗口事件
    root.mainloop()
