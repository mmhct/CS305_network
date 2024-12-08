import pickle
import threading

from util import *
import socket


class ConferenceClient:
    def __init__(self, ):
        # sync client
        self.id = 0  # client id,由服务器给出，服务器给出的第一个id是1， 0是无效id
        self.is_working = True
        self.is_camera_on = False
        self.is_audio_on = False
        self.server_addr = None  # server addr
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_id = None  # 存储当前所在的会议号
        self.conference_ip = None  # *主服务器提供*
        self.conference_port = None  # 这个负责会议室接收数据，也就是说client往这里发送数据。*主服务器提供*
        self.conference_conn = None  # 利用上面这两个创建一个udp套接字，然后放在这里，之后往会议室传数据都用这个。*客户端自己生成*

        self.sock= socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.recv_video_data = {}  # you may need to save received streamd data from other clients in conference
        self.recv_screen_data={}

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
            self.conns.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.conns.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                status = data["status"]
                self.conference_id = data["conference_id"]
                self.conference_ip = data["conference_ip"]
                self.conference_port = data["conference_port"]
                self.on_meeting = True

                # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # client_socket.connect((self.conference_ip, int(self.conference_port)))
                # self.conference_conn = client_socket
                # print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

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
            self.conns.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.conns.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                status = data["status"]
                self.conference_id = data["conference_id"]
                self.conference_ip = data["conference_ip"]
                self.conference_port = data["conference_port"]
                self.on_meeting = True

                # client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                # client_socket.connect((self.conference_ip, int(self.conference_port)))
                # self.conference_conn = client_socket
                # print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

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
        cmd = "quit"
        self.conns.sendall(pickle.dumps(cmd))

    def cancel_conference(self):
        """
        cancel your on-going conference (when you are the conference manager): ask server to close all clients
        """
        cmd = "cancel"
        self.conns.sendall(pickle.dumps(cmd))

    def keep_share(self):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        while True:
            if not self.on_meeting:
                break
            frame = capture_camera()
            screen= capture_screen()
            audio_data=streamin.read(CHUNK)
            pil_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            compressed_image = compress_image(pil_image)
            compressed_screen=compress_image(screen)
            audio_tuple = (self.id, 'audio', audio_data)
            image_tuple = (self.id, 'image', compressed_image)
            screen_tuple=(self.id, 'screen', compressed_screen)
            audio_tuple = pickle.dumps(audio_tuple)
            image_tuple = pickle.dumps(image_tuple)
            screen_tuple=pickle.dumps(screen_tuple)
            if self.is_camera_on:
                self.sock.sendto(image_tuple, self.conference_conn)
                self.sock.sendto(screen_tuple, self.conference_conn)
            if self.is_audio_on:
                self.sock.sendto(audio_tuple, self.conference_conn)

    def create_recv_thread(self, udp_socket):
        t = threading.Thread(target=self.keep_recv, args=udp_socket)
        t.start()

    def keep_recv(self, udp_socket):

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((udp_socket[0], udp_socket[1]))

        while True:
            try:
                data, addr = sock.recvfrom(65535)
                received_tuple = pickle.loads(data)
                id = received_tuple[0]
                type_ = received_tuple[1]
                if type_ == 'image' :
                    image = decompress_image(received_tuple[2])
                    frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                    self.store_image(id, frame)
                elif type_ == 'audio':
                    audio_data = received_tuple[2]
                    self.play_audio(audio_data)
                elif type_ == 'screen':
                    screen=decompress_image(received_tuple[2])
                    screen=cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
                    self.store_screen(id, screen)
            except (socket.error, OSError) as e:
                print(f"Socket error: {e}")
                break

    # def output_data(self):
    #     '''
    #     running task: output received stream data
    #     '''
    #     if self.recv_data is None:
    #         print('[Warn]: No data received yet.')
    #         return
    #
    #     # 具体处理接收到的数据类型
    #     for data_type, data in self.recv_data.items():
    #         if data_type == 'audio':
    #             # 这里我们假设音频数据是字节流，可以播放音频
    #             self.play_audio(data)
    #         elif data_type == 'camera' or data_type == 'screen':
    #             # 这里我们假设是图像数据（视频帧）
    #             self.display_image(data)
    #         else:
    #             print(f'[Warn]: Unsupported data type {data_type}')

    def play_audio(self, audio_data):
        """
        播放音频数据
        """
        print('[Info]: Playing audio...')
        streamout.write(audio_data) # 播放音频数据
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
    def display_image(self):
        """
        显示图像数据
        """
        while True:
            frames = []
            self.recv_video_data[0]=capture_camera()
            frames.append(self.recv_video_data[0])
            for data in self.recv_video_data.items():
                frames.append(data)
            self.recv_video_data.clear()
            combined_frame = np.hstack(frames)
            cv2.imshow('Combined Video Feed', combined_frame)
    def display_screen(self):
        """
        显示屏幕数据
        """
        while True:
            frames = []
            self.recv_screen_data[0]=capture_screen()
            frames.append(self.recv_screen_data[0])
            for data in self.recv_screen_data.items():
                frames.append(data)
            self.recv_screen_data.clear()
            combined_frame = np.hstack(frames)
            cv2.imshow('Combined Screen Feed', combined_frame)

    def start_conference(self):
        '''
        init conns when create or join a conference with necessary conference_info
        and
        start necessary running task for conference
        '''
        if self.on_meeting:
            print('[Warn]: Already in a conference.')
            return

        if not self.server_addr:
            print('[Error]: Server address not set.')
            return

        if not self.conference_info:
            print('[Error]: No conference info available.')
            return

        self.on_meeting = True
        self.conns = {}  # 初始化连接字典

        for data_type in self.support_data_types:
            # 对每种数据类型创建连接
            self.conns[data_type] = self.create_connection(data_type)

        # 启动接收数据的任务
        print('[Info]: Starting to receive data...')
        for data_type in self.support_data_types:
            self.keep_recv()


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
            if len(fields) == 1:
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
                    if data_type in self.share_data.keys():
                        self.share_switch(data_type)
                else:
                    recognized = False
            else:
                recognized = False

            if not recognized:
                print(f'[Warn]: Unrecognized cmd_input {cmd_input}')

    def connection_establish(self, server_ip, server_port):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((server_ip, int(server_port)))
            print(f"已连接到服务器 {server_ip}:{server_port}")
            self.conns = client_socket
            self.server_addr = (server_ip, server_port)

        except ConnectionError as e:
            print(f"连接失败: {e}")
            self.conns = None


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.connection_establish(SERVER_IP, MAIN_SERVER_PORT)
    client1.start()
