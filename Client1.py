# client.py
import cv2
import socket
import struct
import time
import numpy as np
import sounddevice as sd
import threading

# 服务器IP和端口
SERVER_IP = '127.0.0.1'  # 根据实际情况修改
VIDEO_SEND_PORT = 5004
VIDEO_RECV_PORT = 5006
AUDIO_SEND_PORT = 5005
AUDIO_RECV_PORT = 5007

VIDEO_PAYLOAD_TYPE = 26  # JPEG
AUDIO_PAYLOAD_TYPE = 10  # L16 mono 44100

AUDIO_RATE = 16000  # 采样率
AUDIO_CHANNELS = 1  # 单声道
AUDIO_CHUNK = 2048  # 每个音频块的帧数


def send_video(video_send_socket):
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("[视频发送] 无法打开摄像头")
        return

    sequence_number = 0  # RTP序列号
    ssrc = 12345  # 随机选择一个SSRC

    while True:
        ret, frame = cap.read()
        if not ret:
            print("[视频发送] 无法读取摄像头帧")
            break

        # 压缩帧以减少数据量
        encoded, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
        jpeg_bytes = buffer.tobytes()

        # 封装RTP包
        version = 2
        padding = 0
        extension = 0
        csrc_count = 0
        marker = 0
        payload_type = VIDEO_PAYLOAD_TYPE  # JPEG
        timestamp = int(time.time())  # 简单的时间戳

        rtp_header = struct.pack('!BBHII',
                                 (version << 6) | (padding << 5) | (extension << 4) | csrc_count,
                                 (marker << 7) | payload_type,
                                 sequence_number,
                                 timestamp,
                                 ssrc)

        rtp_packet = rtp_header + jpeg_bytes
        video_send_socket.sendto(rtp_packet, (SERVER_IP, VIDEO_SEND_PORT))
        # print(f"[视频发送] 序列号={sequence_number}, 大小={len(rtp_packet)} 字节")
        sequence_number = (sequence_number + 1) % 65536
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    video_send_socket.close()


def receive_video(video_recv_socket):
    # 设置接收超时
    video_recv_socket.settimeout(5)

    while True:
        try:
            # 接收数据包
            data, _ = video_recv_socket.recvfrom(65535)
            if not data:
                continue
            # 解析RTP头部（前12字节）
            if len(data) < 12:
                print("[视频接收] 数据包长度不足12字节，无法解析RTP头部")
                continue
            rtp_header = data[:12]
            payload = data[12:]  # 提取负载部分

            # Debug: 打印负载长度
            print(f"[视频接收] 接收到的负载长度: {len(payload)} 字节")

            if len(payload) == 0:
                print("[视频接收] 接收到的负载为空")
                continue

            # 解码JPEG图像
            nparr = np.frombuffer(payload, dtype=np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is not None:
                cv2.imshow('Received Video', frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                print("[视频接收] 解码失败: frame is None")
        except socket.timeout:
            continue
        except Exception as e:
            print(f"[视频接收] 发生错误: {e}")
            break

    # 清理
    video_recv_socket.close()


def send_audio(audio_send_socket):
    # 打开音频流
    def callback(indata, frames, time_info, status):
        nonlocal sequence_number, timestamp
        if status:
            print(f"[音频发送] 状态: {status}")
        # 将音频数据转换为bytes
        audio_bytes = indata.tobytes()

        version = 2
        padding = 0
        extension = 0
        csrc_count = 0
        marker = 0
        payload_type = AUDIO_PAYLOAD_TYPE  # L16 mono
        timestamp += frames

        rtp_header = struct.pack('!BBHII',
                                 (version << 6) | (padding << 5) | (extension << 4) | csrc_count,
                                 (marker << 7) | payload_type,
                                 sequence_number,
                                 timestamp,
                                 ssrc)

        rtp_packet = rtp_header + audio_bytes

        # 发送RTP包
        audio_send_socket.sendto(rtp_packet, (SERVER_IP, AUDIO_SEND_PORT))

        print(f"[音频发送] 序列号={sequence_number}, 大小={len(rtp_packet)} 字节")

        # 更新序列号
        sequence_number = (sequence_number + 1) % 65536

    sequence_number = 0
    ssrc = 67890  # 随机选择一个SSRC
    timestamp = 0

    with sd.InputStream(samplerate=AUDIO_RATE, channels=AUDIO_CHANNELS,
                        callback=callback, blocksize=AUDIO_CHUNK,
                        dtype='int16'):
        print("[音频发送] 正在发送音频... 按下 Ctrl+C 停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("[音频发送] 停止发送音频")

    # 清理
    audio_send_socket.close()


def receive_audio(audio_recv_socket):
    # 设置接收超时
    audio_recv_socket.settimeout(5)

    # 打开音频播放流
    def callback(outdata, frames, time_info, status):
        nonlocal audio_buffer
        if status:
            print(f"[音频接收] 状态: {status}")
        # 填充输出缓冲区
        if len(audio_buffer) >= frames * AUDIO_CHANNELS * 2:  # 16-bit PCM
            out_chunk = audio_buffer[:frames * AUDIO_CHANNELS * 2]
            audio_buffer = audio_buffer[frames * AUDIO_CHANNELS * 2:]
            outdata[:] = np.frombuffer(out_chunk, dtype=np.int16).reshape(-1, AUDIO_CHANNELS)
        else:
            outdata[:] = np.zeros((frames, AUDIO_CHANNELS), dtype=np.int16)

    audio_buffer = bytearray()

    with sd.OutputStream(samplerate=AUDIO_RATE, channels=AUDIO_CHANNELS,
                         callback=callback, blocksize=AUDIO_CHUNK,
                         dtype='int16'):
        print("[音频接收] 正在接收音频... 按下 Ctrl+C 停止")
        while True:
            try:
                # 接收数据包
                data, _ = audio_recv_socket.recvfrom(65535)
                if not data:
                    continue
                # 解析RTP头部（前12字节）
                if len(data) < 12:
                    print("[音频接收] 数据包长度不足12字节，无法解析RTP头部")
                    continue
                rtp_header = data[:12]
                payload = data[12:]  # 提取负载部分

                # Debug: 打印负载长度
                print(f"[音频接收] 接收到的负载长度: {len(payload)} 字节")

                if len(payload) == 0:
                    print("[音频接收] 接收到的负载为空")
                    continue

                # 将音频数据添加到缓冲区
                audio_buffer.extend(payload)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[音频接收] 发生错误: {e}")
                break

    # 清理
    audio_recv_socket.close()


def main():
    # 创建UDP套接字用于发送视频和音频
    video_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    audio_send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 创建UDP套接字用于接收视频和音频
    video_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    video_recv_socket.bind(('', VIDEO_RECV_PORT))  # 绑定到接收视频的端口

    audio_recv_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    audio_recv_socket.bind(('', AUDIO_RECV_PORT))  # 绑定到接收音频的端口

    # 创建线程处理视频发送和接收
    video_send_thread = threading.Thread(target=send_video, args=(video_send_socket,), daemon=True)
    video_recv_thread = threading.Thread(target=receive_video, args=(video_recv_socket,), daemon=True)

    # 创建线程处理音频发送和接收
    audio_send_thread = threading.Thread(target=send_audio, args=(audio_send_socket,), daemon=True)
    audio_recv_thread = threading.Thread(target=receive_audio, args=(audio_recv_socket,), daemon=True)

    # 启动所有线程
    video_send_thread.start()
    video_recv_thread.start()
    audio_send_thread.start()
    audio_recv_thread.start()

    print("客户端已启动，正在发送和接收视频及音频。按下 Ctrl+C 退出。")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("客户端关闭")


if __name__ == "__main__":
    main()
