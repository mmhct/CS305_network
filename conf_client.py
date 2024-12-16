
import threading
import pickle
import socket
import time
from datetime import datetime

from util import *

class ConferenceClient:
    def __init__(self):
        self.id = 0  # client id,由服务器给出，服务器给出的第一个id是1， 0是无效id
        self.is_working = True
        self.is_screen_on = False
        self.is_camera_on = False
        self.is_audio_on = False
        self.server_addr = None  # server addr
        self.on_meeting = False  # status
        self.tcp_conn = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = ['screen', 'camera', 'audio', 'text']  # for some types of data
        self.conference_id = None  # 存储当前所在的会议号
        self.conference_ip = None  # *主服务器提供*
        self.conference_port = None  # 这个负责会议室接收数据，也就是说client往这里发送数据。*主服务器提供*
        self.conference_conn = None  # 利用上面这两个创建一个udp套接字，然后放在这里，之后往会议室传数据都用这个。*客户端自己生成*

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # self.sock.bind(('', 18020))  # 绑定本地端口
        send_buffer_size = 6553600  # 例如，将缓冲区大小设置为 65536 字节
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, send_buffer_size)
        self.recv_video_data = {}  # you may need to save received streamd data from other clients in conference
        self.recv_screen_data = {}

        self.udp_sockets = []  # 存储收资料的udp套接字
        self.udp_conn = None  # 用于接收数据的udp套接字

    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        # print(self.conns)
        if self.on_meeting:
            print(f"You have already joined the conference {self.conference_id} "
                  f"({self.conference_ip}:{self.conference_port})")
        else:
            cmd = "create"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                if isinstance(data, dict):
                    status = data["status"]
                    self.conference_id = data["conference_id"]
                    self.conference_ip = data["conference_ip"]
                    self.conference_port = data["conference_port"]
                    self.on_meeting = True

                    self.conference_conn = (self.conference_ip, int(self.conference_port))
                    print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

                    text = f"{NAME} comes in"
                    text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                    text_tuple = (self.id, 'text', text)
                    text_tuple = pickle.dumps(text_tuple)
                    self.sock.sendto(text_tuple, self.conference_conn)

            except ConnectionError as e:
                print(f"连接失败: {e}")
                self.conference_conn = None
            except TypeError as e:  # 报错的话，返回的不是字典，是str,会有TypeError
                print(e)
            except Exception as e:
                print(e)

    def join_conference(self, conference_id):
        """
        join a conference: send join-conference request with given conference_id, and obtain necessary data to
        """
        if self.on_meeting:
            print(f"You have already joined the conference {self.conference_id} "
                  f"({self.conference_ip}:{self.conference_port})")
        else:
            cmd = f"join {conference_id}"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                if isinstance(data, dict):
                    status = data["status"]
                    self.conference_id = data["conference_id"]
                    self.conference_ip = data["conference_ip"]
                    self.conference_port = data["conference_port"]
                    self.on_meeting = True

                    self.conference_conn = (self.conference_ip, int(self.conference_port))
                    print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

                    text = f"{NAME} comes in"
                    text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                    text_tuple = (self.id, 'text', text)
                    text_tuple = pickle.dumps(text_tuple)
                    self.sock.sendto(text_tuple, self.conference_conn)

            except ConnectionError as e:
                print(f"连接失败: {e}")
                self.conference_conn = None
            except TypeError as e:  # 报错的话，返回的不是字典，是str,会有TypeError
                print(e)
            except Exception as e:
                print(e)

    def quit_conference(self):
        """
        quit your on-going conference
        """
        if not self.on_meeting:
            print("You are not currently in any conference.")
            return

        cmd = f"quit {self.id} {self.conference_id}"
        try:
            # 发送退出会议的命令到主服务器
            self.tcp_conn.sendall(pickle.dumps(cmd))
            data = pickle.loads(self.tcp_conn.recv(1024))
            print("字典:", data)

            if isinstance(data, dict) and data["status"] == "success":
                # 关闭与会议服务器的UDP连接
                if self.conference_conn:
                    text = f"{NAME} quit"
                    text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                    text_tuple = (self.id, 'text', text)
                    text_tuple = pickle.dumps(text_tuple)
                    self.sock.sendto(text_tuple, self.conference_conn)
                    self.conference_conn = None

                # 更新客户端状态
                print(f"已成功退出会议 {self.conference_id}")
                self.on_meeting = False
                self.conference_id = None
                self.conference_ip = None
                self.conference_port = None

                self.is_screen_on = False
                self.is_camera_on = False
                self.is_audio_on = False
                self.conference_conn = None

            else:
                print("Quit failed:", data)
        except Exception as e:
            print(f"Quit failed: {e}")

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        if not self.on_meeting:
            print("You are not currently in any conference.")
        else:
            cmd = "cancel"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("字典:", data)

            try:
                status = data["status"]
                if status == "success":
                    if self.conference_conn:
                        text = f"{NAME} quit"
                        text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                        text_tuple = (self.id, 'text', text)
                        text_tuple = pickle.dumps(text_tuple)
                        self.sock.sendto(text_tuple, self.conference_conn)
                        self.conference_conn = None

                    print(f"Conference {self.conference_id} has been successfully cancelled.")
                    # 重置会议相关状态
                    self.on_meeting = False
                    self.conference_id = None
                    self.conference_ip = None
                    self.conference_port = None

                    self.is_screen_on = False
                    self.is_camera_on = False
                    self.is_audio_on = False
                    self.conference_conn = None
                else:
                    print(f"Failed to cancel the conference: {data}")
            except TypeError as e:  # 如果返回的不是字典
                print(f"Received invalid data from server: {e}")
            except Exception as e:
                print(f"An error occurred: {e}")

    def keep_share(self):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        while True:
            if not self.on_meeting:
                time.sleep(0.03)  # 控制刷新率
                continue
            try:
                frame = capture_camera()
                screen = capture_screen()
                audio_data = streamin.read(CHUNK)
                # pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                compressed_image = compress_image(frame)
                compressed_screen = compress_image(screen)
                audio_tuple = (self.id, 'audio', audio_data)
                image_tuple = (self.id, 'image', compressed_image)
                screen_tuple = (self.id, 'screen', compressed_screen)
                audio_tuple = pickle.dumps(audio_tuple)
                image_tuple = pickle.dumps(image_tuple)
                screen_tuple = pickle.dumps(screen_tuple)
                if self.is_screen_on:
                    print("sending screen data to server")
                    self.sock.sendto(screen_tuple, self.conference_conn)
                if self.is_camera_on:
                    print("sending camera data to server")
                    self.sock.sendto(image_tuple, self.conference_conn)
                if self.is_audio_on:
                    print("sending audio data to server")
                    self.sock.sendto(audio_tuple, self.conference_conn)
                print("keep sharing data")
            except (socket.error, OSError) as e:
                print(f"Socket error: {e}")

            time.sleep(0.03)  # 控制刷新率

    def share_switch(self, data_type):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        if data_type == 'screen':
            self.is_screen_on = not self.is_screen_on
            if self.is_screen_on:
                print("switch screen on")
            else:
                print("switch screen off")
        if data_type == 'camera':
            self.is_camera_on = not self.is_camera_on
            if self.is_camera_on:
                print("switch camera on")
            else:
                print("switch camera off")
        if data_type == 'audio':
            self.is_audio_on = not self.is_audio_on
            if self.is_audio_on:
                print("switch audio on")
            else:
                print("switch audio off")

    def keep_recv(self):
        while True:
            try:
                data, addr = self.sock.recvfrom(6553500)
                received_tuple = pickle.loads(data)
                print(f"received data from {addr}: {len(data)} bytes")
                id = received_tuple[0]
                type_ = received_tuple[1]
                if type_ == 'image':
                    image = decompress_image(received_tuple[2])
                    # frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    self.store_image(id, image)
                elif type_ == 'audio':
                    audio_data = received_tuple[2]
                    self.play_audio(audio_data)
                elif type_ == 'screen':
                    screen = decompress_image(received_tuple[2])
                    # screen = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
                    self.store_screen(id, screen)
                elif type_ == 'text':
                    text = received_tuple[2]
                    print(text)
                elif type_ == 'exit':
                    self.on_meeting = False
                    self.conference_id = None
                    self.conference_ip = None
                    self.conference_port = None

                    self.is_screen_on = False
                    self.is_camera_on = False
                    self.is_audio_on = False
                    self.conference_conn = None
            except (socket.error, OSError) as e:
                print(f"Socket error: {e}")
                break

    def play_audio(self, audio_data):
        """
        播放音频数据
        """
        print('[Info]: Playing audio...')
        streamout.write(audio_data)  # 播放音频数据

    def store_image(self, id, image_data):
        """
        存储图像数据
        """
        self.recv_video_data[id] = image_data

    def store_screen(self, id, screen_data):
        """
        存储屏幕数据
        """
        self.recv_screen_data[id] = screen_data

    def display_combined(self):
        """
        显示图像和屏幕数据
        """
        while True:
            frames1 = []
            frames2 = []
            self.recv_video_data[0] = capture_camera()
            self.recv_screen_data[0] = capture_screen()
            # self.recv_video_data[1] = capture_camera()
            # self.recv_screen_data[1] = capture_screen()

            for client_id, data in self.recv_video_data.items():
                frames1.append(data)
            for client_id, data in self.recv_screen_data.items():
                frames2.append(data)
            # frames1.append(self.recv_video_data[0])
            # frames2.append(self.recv_screen_data[0])
            # frames1.append(self.recv_video_data[0])
            # frames2.append(self.recv_screen_data[0])
            # combined_image = overlay_camera_images(self.recv_screen_data[0], frames1)
            for i in range(len(frames2)):
                combined_image = overlay_camera_images(frames2[0], frames1)
                cv2.imshow(str(i), np.array(combined_image))

            # for client_id, data in self.recv_video_data.items():
            #     frames.append(data)
            # for client_id, data in self.recv_screen_data.items():
            #     frames.append(data)
            # frames.append(self.recv_screen_data[0])
            # self.recv_video_data.clear()
            # self.recv_screen_data.clear()
            # combined_frame = np.hstack(frames)
            # cv2.imshow(, combined_frame)
            cv2.waitKey(1)
            time.sleep(0.03)  # 控制刷新率

    def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''

    def close_conference(self):
        '''
        close all conns to servers or other clients and cancel the running tasks
        pay attention to the exception handling
        '''

    def start(self):
        """
        execute functions based on the command line input
        """
        while True:
            if not self.on_meeting:
                status = 'Free'
            else:
                status = f'OnMeeting-{self.conference_id}'

            recognized = True
            cmd_input = input(f'({status}) Please enter a operation (enter "?" to help): ').strip().lower()
            fields = cmd_input.split(maxsplit=1)

            if fields[0] == 'text':
                text = fields[1]
                text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                text_tuple = (self.id, 'text', text)
                text_tuple = pickle.dumps(text_tuple)
                print("sending text data to server")
                self.sock.sendto(text_tuple, self.conference_conn)

            elif len(fields) == 1:
                if cmd_input in ('?', '？'):
                    print(HELP)
                elif cmd_input == 'create':
                    self.create_conference()
                elif cmd_input == 'quit':
                    self.quit_conference()
                elif cmd_input == 'cancel':
                    self.cancel_conference()
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    input_conf_id = fields[1]
                    if input_conf_id.isdigit():
                        self.join_conference(input_conf_id)
                    else:
                        print('[Warn]: Input conference ID must be in digital form')
                elif fields[0] == 'switch':
                    data_type = fields[1]
                    if data_type in self.support_data_types:
                        self.share_switch(data_type)
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')
            time.sleep(0.1)  # 给其他任务留出时间执行

    def run(self):
        threads = [
            threading.Thread(target=self.keep_share),
            threading.Thread(target=self.keep_recv),
            threading.Thread(target=self.start),
            threading.Thread(target=self.display_combined)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def connection_establish(self, server_ip, server_port):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((server_ip, int(server_port)))
            print(f"已连接到服务器 {server_ip}:{server_port}")
            self.tcp_conn = client_socket
            self.server_addr = (server_ip, server_port)

            self.id = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的id
            print(f"分配到的客户端id:{self.id}")

            self.sock.bind(("", 20000 + self.id * 2))

        except ConnectionError as e:
            print(f"连接失败: {e}")
            self.tcp_conn = None


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.connection_establish(SERVER_IP, MAIN_SERVER_PORT)
    client1.run()
