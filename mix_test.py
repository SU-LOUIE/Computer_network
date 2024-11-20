import socket
import threading
import time
import zlib
from io import BytesIO

import cv2
import numpy as np
import pyaudio
from PIL import Image

"""
这个实现的是从客户端接收数据然后传给服务器，服务器再回传给客户端，客户端把接收到的数据展示出来
但是这个版本现在只支持1对1，因为没有给udp传输包里面加上tag，无法区分是哪一个客户端发过来
"""
class VideoAudioClient:
    def __init__(self, server_ip, server_port):
        self.server_ip = server_ip
        self.server_port = server_port
        self.cap = None
        self.is_camera_on = False
        self.is_audio_on = False

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.connect((self.server_ip, self.server_port))  # 可以不用connect，不过每次发送都要附带地址比较麻烦
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
        else:
            self.is_camera_on = False
            if self.cap:
                self.cap.release()
                self.cap = None

    def toggle_audio(self):
        if not self.is_audio_on:
            self.audio_stream = pyaudio.PyAudio().open(format=pyaudio.paInt16,
                                                       channels=1,
                                                       rate=16000,
                                                       input=True,
                                                       frames_per_buffer=2048)
            self.stream_output = pyaudio.PyAudio().open(format=pyaudio.paInt16,
                                                        channels=1,
                                                        rate=16000,
                                                        output=True,
                                                        frames_per_buffer=2048)
            self.is_audio_on = True
        else:
            self.is_audio_on = False
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
                self.audio_stream = None
            if self.stream_output:
                self.stream_output.stop_stream()
                self.stream_output.close()
                self.stream_output = None

    def update_video(self):
        """不断从摄像头捕获视频帧并更新到窗口"""
        if self.is_camera_on and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # 转换为RGB格式并显示
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                buffer = BytesIO()
                image = Image.fromarray(frame_rgb).convert('RGB')
                image.save(buffer, format="JPEG")
                jpeg_data = buffer.getvalue()
                self.send_data(0, jpeg_data)  # 0代表视频数据
                self.local_video = frame
            cv2.waitKey(1)

    def update_audio(self):
        if self.is_audio_on and self.audio_stream:
            audio_data = self.audio_stream.read(2048)

            compressed_audio = zlib.compress(audio_data)
            self.send_data(1, compressed_audio)  # 1代表音频数据

    def send_data(self, data_type, data):
        try:
            packet = data_type.to_bytes(1, byteorder='big') + data
            self.sock.sendto(packet, (self.server_ip, self.server_port))
        except Exception as e:
            print(f"[错误] 发送数据失败: {e}")
            self.is_running = False

    def receive_and_display(self):
        try:
            while self.is_running:
                raw_data, _ = self.sock.recvfrom(65535)
                if not raw_data:
                    print("[断开] 服务器已断开连接。")
                    self.is_running = False
                    break

                data_type = int.from_bytes(raw_data[0:1], byteorder='big')
                frame_data = raw_data[1:]

                if data_type == 0:
                    try:
                        buffer = BytesIO(frame_data)
                        img = Image.open(buffer)
                        img = np.array(img)
                        img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
                        self.remote_video = img_bgr
                        if hasattr(self, 'local_video') and hasattr(self, 'remote_video'):
                            combined_frame = np.hstack((self.local_video, self.remote_video))
                            cv2.imshow("Local and Remote Video", combined_frame)
                    except Exception as e:
                        print(f"[错误] 处理视频数据失败: {e}")
                elif data_type == 1:
                    try:
                        decompressed_audio = zlib.decompress(frame_data)
                        self.play_audio(decompressed_audio)
                    except Exception as e:
                        print(f"[错误] 处理音频数据失败: {e}")
                if cv2.waitKey(1) & 0xFF == ord('q'):  # 按'q'键退出
                    break

        except Exception as e:
            print(f"[错误] 接收和显示线程出错: {e}")
            self.is_running = False



    def play_audio(self, audio_data):
        self.stream_output.write(audio_data)

    def on_closing(self):
        """关闭客户端时释放资源"""
        print("[关闭] 关闭客户端。")
        self.is_running = False
        if self.cap:
            self.cap.release()
        self.sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    SERVER_IP = '127.0.0.1'
    SERVER_PORT = 8888
    client = VideoAudioClient(SERVER_IP, SERVER_PORT)

    client.toggle_camera()
    client.toggle_audio()

    try:
        while client.is_running:
            client.update_video()
            client.update_audio()
            time.sleep(0.02)
    except KeyboardInterrupt:
        client.on_closing()