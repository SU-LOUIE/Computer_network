import socket
import threading
import cv2
import time
from PIL import Image, ImageTk
import tkinter as tk
from io import BytesIO
import numpy as np


class VideoConferenceClientUDP:
    def __init__(self, server_ip, server_port, root):
        self.server_ip = server_ip
        self.server_port = server_port
        self.root = root
        self.root.title("多人视频会议客户端 (UDP)")
        self.root.geometry("1500x600")
        self.root.resizable(False, False)

        # 和之前一样的界面布局
        self.main_frame = tk.Frame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_columnconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(1, weight=1)

        self.local_frame = tk.Frame(self.main_frame)
        self.local_frame.grid(row=0, column=0, sticky="nsew", padx=10)
        self.local_title = tk.Label(self.local_frame, text="本地视频", font=("Arial", 14, "bold"))
        self.local_title.pack(side="top", pady=5)

        self.remote_frame = tk.Frame(self.main_frame)
        self.remote_frame.grid(row=0, column=1, sticky="nsew", padx=10)
        self.remote_title = tk.Label(self.remote_frame, text="远程视频", font=("Arial", 14, "bold"))
        self.remote_title.pack(side="top", pady=5)

        self.local_video_label = tk.Label(self.local_frame)
        self.local_video_label.pack(fill="both", expand=True)

        self.remote_video_label = tk.Label(self.remote_frame)
        self.remote_video_label.pack(fill="both", expand=True)

        self.cap = None
        self.is_camera_on = False
        self.camera_button = tk.Button(self.root, text="打开摄像头", command=self.toggle_camera)
        self.camera_button.grid(row=1, column=0, columnspan=2, sticky="ew", pady=10)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.server_ip,self.server_port))
        self.is_running = True

        self.receive_thread = threading.Thread(target=self.receive_and_display, daemon=True)
        self.receive_thread.start()

    def toggle_camera(self):
        if not self.is_camera_on:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                print("无法访问摄像头")
                return
            self.is_camera_on = True
            self.camera_button.config(text="关闭摄像头")
            self.update_video()
        else:
            self.is_camera_on = False
            self.camera_button.config(text="打开摄像头")
            if self.cap:
                self.cap.release()
                self.cap = None
            self.local_video_label.config(image='')

    def update_video(self):
        if self.is_camera_on and self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame_rgb).convert('RGB')
                image_tk = ImageTk.PhotoImage(image)
                self.local_video_label.config(image=image_tk)
                self.local_video_label.image = image_tk

                # 压缩图像并发送
                buffer = BytesIO()
                image.save(buffer, format="JPEG")
                jpeg_data = buffer.getvalue()
                self.send_video(jpeg_data)

            self.root.after(10, self.update_video)

    def send_video(self, jpeg_data):
        """使用UDP发送视频帧"""
        try:
            frame_length = len(jpeg_data)
            if frame_length > 65507:  # UDP数据包大小限制
                print("[警告] 单帧数据过大，可能无法发送")
                return
            self.sock.sendto(jpeg_data, (self.server_ip, self.server_port))
        except Exception as e:
            print(f"[错误] 发送视频数据失败: {e}")
            self.is_running = False

    def receive_and_display(self):
        try:
            while self.is_running:
                # 接收数据
                frame_data, addr = self.sock.recvfrom(65536)  # 接收最大数据包

                if not frame_data:
                    print("[警告] 接收到的数据为空")
                    continue

                try:
                    # 尝试解码为图像
                    buffer = BytesIO(frame_data)
                    img = Image.open(buffer)
                    imgtk = ImageTk.PhotoImage(image=img)
                    self.remote_video_label.config(image=imgtk)
                    self.remote_video_label.image = imgtk
                except Exception as e:
                    print(f"[错误] 解码图像失败: {e}")
                    continue
        except Exception as e:
            print(f"[错误] 接收和显示线程出错: {e}")
            self.is_running = False

    def on_closing(self):
        print("[关闭] 关闭客户端。")
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.sock.close()
        self.root.quit()
        self.root.destroy()

if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'  # 服务器IP地址
    SERVER_PORT = 8888  # 服务器端口号
    root = tk.Tk()
    client = VideoConferenceClientUDP(SERVER_IP, SERVER_PORT, root)
    root.protocol("WM_DELETE_WINDOW", client.on_closing)  # 绑定关闭窗口事件
    root.mainloop()