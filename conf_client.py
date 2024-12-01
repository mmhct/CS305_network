import pickle

from util import *
import socket


class ConferenceClient:
    def __init__(self, ):
        # sync client
        self.is_working = True
        self.server_addr = None  # server addr
        self.on_meeting = False  # status
        self.conns = None  # you may need to maintain multiple conns for a single conference
        self.support_data_types = []  # for some types of data
        self.share_data = {}
        self.conference_id = None  # 存储当前所在的会议号
        self.conference_ip = None  # you may need to save and update some conference_info regularly
        self.conference_port = None
        self.conference_conn = None

        self.recv_data = None  # you may need to save received streamd data from other clients in conference

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

    def keep_share(self, data_type, send_conn, capture_function, compress=None, fps_or_frequency=30):
        '''
        running task: keep sharing (capture and send) certain type of data from server or clients (P2P)
        you can create different functions for sharing various kinds of data
        '''
        pass

    def share_switch(self, data_type):
        '''
        switch for sharing certain type of data (screen, camera, audio, etc.)
        '''
        pass

    def keep_recv(self, recv_conn, data_type, decompress=None):
        '''
        running task: keep receiving certain type of data (save or output)
        you can create other functions for receiving various kinds of data
        '''

    def output_data(self):
        '''
        running task: output received stream data
        '''
        if self.recv_data is None:
            print('[Warn]: No data received yet.')
            return

        # 具体处理接收到的数据类型
        for data_type, data in self.recv_data.items():
            if data_type == 'audio':
                # 这里我们假设音频数据是字节流，可以播放音频
                self.play_audio(data)
            elif data_type == 'camera' or data_type == 'screen':
                # 这里我们假设是图像数据（视频帧）
                self.display_image(data)
            else:
                print(f'[Warn]: Unsupported data type {data_type}')

    def play_audio(self, audio_data):
        """
        播放音频数据
        """
        # 你可以使用 pyaudio 或其他库来播放音频数据
        print('[Info]: Playing audio...')
        streamout.write(audio_data)  # 播放音频流

    def display_image(self, image_data):
        """
        显示图像数据
        """
        print('[Info]: Displaying image...')
        image = decompress_image(image_data)
        image.show()  # 使用 PIL 显示图像

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
