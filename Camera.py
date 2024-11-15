import cv2
import tkinter as tk
from tkinter import Label, Button
from PIL import Image, ImageTk


class VideoConferenceClient:
    def __init__(self, Window):
        self.root = Window
        self.root.title("Video Conference Client")
        self.root.geometry("800x600")
        self.root.resizable(False, False)  # 禁止调整窗口大小

        self.camera_button = Button(self.root, text="打开摄像头", command=self.toggle_camera)
        self.camera_button.pack(side='top', fill='x', pady=10)  # 按钮放在顶部，并占据整个宽度，留 10 像素的上下间距

        self.video_label = Label(self.root)
        self.video_label.pack(expand=True)
        self.cap = None  # 进去的时候摄像头默认是关闭的
        self.is_camera_on = False

        # self.root.protocol("WM_DELETE_WINDOW", self.on_closing)  # 绑定窗口关闭的事件

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
            self.video_label.config(image='')  # 清空显示的画面

    def update_video(self):
        """不断从摄像头捕获视频帧并更新到 UI 界面"""
        if self.is_camera_on and self.cap:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                image_tk = ImageTk.PhotoImage(image)
                self.video_label.config(image=image_tk)
                self.video_label.image = image_tk
            self.root.after(10, self.update_video)

    def on_closing(self):
        # 关闭摄像头并释放资源
        self.is_camera_on = False
        if self.cap:
            self.cap.release()
        self.root.destroy()


# 创建 Tkinter 主窗口
root = tk.Tk()
app = VideoConferenceClient(root)
root.mainloop()
