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
        self.tcp_conn2 = None # 负责接收指令的tcp连接
        self.support_data_types = ['screen', 'camera', 'audio', 'text']  # for some types of data
        self.conference_id = None  # 存储当前所在的会议号
        self.conference_ip = None  # *主服务器提供*
        self.conference_port = None  # 这个负责会议室接收数据，也就是说client往这里发送数据。*主服务器提供*
        self.conference_conn = None  # 利用上面这两个创建一个udp套接字，然后放在这里，之后往会议室传数据都用这个。*客户端自己生成*

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        send_buffer_size = 6553600  # 例如，将缓冲区大小设置为 65536 字节
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, send_buffer_size)
        self.recv_video_data = {}  # you may need to save received streamd data from other clients in conference {client_id: data}
        self.recv_screen_data = {} # {client_id: {id:(data[0],data[1],data[2]...data[n])}} 里面的这个id是自增维护号，n设为7-1=6

        self.udp_sockets = []  # 存储收资料的udp套接字
        self.udp_conn = None  # 用于接收数据的udp套接字
        self.others = set()  # 除自己以外所有在会议室的人的id
        self.mode = None
        self.p2p_ip = None
        self.p2p_port = None
        self.p2p_conn = None

    def create_conference(self):
        """
        create a conference: send create-conference request to server and obtain necessary data to
        """
        # print(self.conns)
        if self.on_meeting:
            print(f"You have already joined the conference {self.conference_id} "
                  f"({self.conference_ip}:{self.conference_port})")
        else:
            udp_ip, udp_port = self.sock.getsockname()
            print(f"UDP {udp_ip}:{udp_port}")
            cmd = f"create {self.id} {udp_ip} {udp_port}"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                if isinstance(data, dict):
                    status = data["status"]
                    if status == "success":
                        self.conference_id = data["conference_id"]
                        self.conference_ip = data["conference_ip"]
                        self.conference_port = data["conference_port"]
                        self.on_meeting = True

                        self.conference_conn = (self.conference_ip, int(self.conference_port))
                        print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

                        # text = f"{NAME} comes in"
                        # text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                        # text_tuple = (self.id, 'text', text)
                        # text_tuple = pickle.dumps(text_tuple)
                        # self.sock.sendto(text_tuple, self.conference_conn)

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
        elif conference_id > 0:
            udp_ip, udp_port = self.sock.getsockname()
            print(f"UDP {udp_ip}:{udp_port}")
            cmd = f"join {self.id} {conference_id} {udp_ip} {udp_port}"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("字典:", data)
            try:
                if isinstance(data, dict):
                    status = data["status"]
                    if status == "success":
                        self.conference_id = data["conference_id"]
                        self.conference_ip = data["conference_ip"]
                        self.conference_port = data["conference_port"]
                        self.on_meeting = True

                        self.conference_conn = (self.conference_ip, int(self.conference_port))
                        print(f"已连接到会议室{self.conference_id} ({self.conference_ip}:{self.conference_port})")

                        # text = f"{NAME} comes in"
                        # text = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} {NAME}:{text}"
                        # text_tuple = (self.id, 'text', text)
                        # text_tuple = pickle.dumps(text_tuple)
                        # self.sock.sendto(text_tuple, self.conference_conn)

            except ConnectionError as e:
                print(f"连接失败: {e}")
                self.conference_conn = None
            except TypeError as e:  # 报错的话，返回的不是字典，是str,会有TypeError
                print(e)
            except Exception as e:
                print(e)
        else:
            udp_ip, udp_port = self.sock.getsockname()
            print(f"UDP {udp_ip}:{udp_port}")
            cmd = "search"
            self.tcp_conn.sendall(pickle.dumps(cmd))  # 序列化发送内容
            data = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的data
            print("available conference: ", data)
            

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
                self.reset()

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
                    self.reset()
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
                #compressed_screen = compress_image(image=screen, quality=0)
                compressed_screen = compress_image(screen.resize((600, 400), Image.LANCZOS))
                audio_tuple = (self.id, 'audio', audio_data)
                image_tuple = (self.id, 'image', compressed_image)
                screen_tuple = (self.id, 'screen', compressed_screen)
                audio_tuple = pickle.dumps(audio_tuple)
                image_tuple = pickle.dumps(image_tuple)
                screen_tuple = pickle.dumps(screen_tuple)
                #分支
                if self.mode == 'p2p':
                    print("p2p mode")
                    if self.is_screen_on:
                        print("sending screen data to p2p")
                        self.sock.sendto(screen_tuple, self.p2p_conn)
                    if self.is_camera_on:
                        print("sending camera data to p2p")
                        self.sock.sendto(image_tuple, self.p2p_conn)
                    if self.is_audio_on:
                        print("sending audio data to p2p")
                        self.sock.sendto(audio_tuple, self.p2p_conn)
                else:
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
                cmd = f'switch screen off {self.id} {self.conference_id}'
                self.tcp_conn.sendall(pickle.dumps(cmd))
                print("switch screen off")
        if data_type == 'camera':
            self.is_camera_on = not self.is_camera_on
            if self.is_camera_on:
                print("switch camera on")
            else:
                cmd = f'switch camera off {self.id} {self.conference_id}'
                self.tcp_conn.sendall(pickle.dumps(cmd))
                print("switch camera off")
        if data_type == 'audio':
            self.is_audio_on = not self.is_audio_on
            if self.is_audio_on:
                print("switch audio on")
            else:
                cmd = f'switch audio off {self.id} {self.conference_id}'
                self.tcp_conn.sendall(pickle.dumps(cmd))
                print("switch audio off")

    def keep_recv(self):
        while True:
            if not self.on_meeting:
                time.sleep(0.03)  # 控制刷新率
                continue
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
            except (socket.error, OSError) as e:
                print(f"Socket error: {e}")
                break

    def reset(self):
        self.on_meeting = False
        self.conference_id = None
        self.conference_ip = None
        self.conference_port = None
        self.is_screen_on = False
        self.is_camera_on = False
        self.is_audio_on = False
        self.conference_conn = None
        self.others.clear()

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

        self.others.add(0)
        self.others.add(1)
        while True:
            self.recv_video_data[0] = capture_camera()
            self.recv_screen_data[0] = capture_screen()
            # self.recv_video_data[1] = capture_camera()
            # self.recv_screen_data[1] = capture_screen()
            others_copy = self.others.copy()
            for client_id in others_copy:
                if client_id in self.recv_video_data and client_id in self.recv_screen_data:
                    cv2.imshow(str(client_id), np.array(
                        overlay_camera_images(self.recv_screen_data[client_id], [self.recv_video_data[client_id]])))
                    cv2.waitKey(1)
                elif client_id in self.recv_video_data:
                    cv2.imshow(str(client_id), np.array(self.recv_video_data[client_id]))
                    cv2.waitKey(1)
                elif client_id in self.recv_screen_data:
                    cv2.imshow(str(client_id), np.array(self.recv_screen_data[client_id].resize((1920, 1080), Image.LANCZOS)))
                    cv2.waitKey(1)

            # for client_id in frames2:
            #     cv2.imshow(str(client_id), np.array(overlay_camera_images(frames2[client_id],None)))
            # if client_id in self.recv_screen_data and client_id in frames1:
            #     combined_image = overlay_camera_images(frames2[client_id], frames1[client_id])
            # cv2.imshow(str(i), np.array(combined_image))

            # for client_id, data in self.recv_video_data.items():
            #     frames.append(data)
            # for client_id, data in self.recv_screen_data.items():
            #     frames.append(data)
            # frames.append(self.recv_screen_data[0])
            # self.recv_video_data.clear()
            # self.recv_screen_data.clear()
            # combined_frame = np.hstack(frames)
            # cv2.imshow(, combined_frame)
            # cv2.waitKey(1)
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
                elif cmd_input == 'join':
                    self.join_conference(0)
                else:
                    recognized = False
            elif len(fields) == 2:
                if fields[0] == 'join':
                    input_conf_id = fields[1]
                    if input_conf_id.isdigit():
                        self.join_conference(int(input_conf_id))
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

    def keep_receive_instruction(self):
        while True:
            if not self.on_meeting:
                time.sleep(0.03)  # 控制刷新率
                continue
            try:
                data = pickle.loads(self.tcp_conn2.recv(1024)) #id,  'text', text
                print(f"Received data: {data}")  # 调试信息
                other_id, type_, text = data
                if type_ == 'text':
                    # text = pickle.loads(self.tcp_conn2.recv(1024))
                    print(text)
                elif type_ == 'switch':
                    #todo: maintain set others
                    print("switch")
                elif type_ == 'join':
                    self.others.add(other_id)
                    print(f"Client {other_id} joined")
                    print(self.others)
                elif type_ == 'quit':
                    self.others.discard(other_id)
                    if other_id in self.recv_video_data:
                        del self.recv_video_data[other_id]
                    if other_id in self.recv_screen_data:
                        del self.recv_screen_data[other_id]
                    print(f"Client {other_id} left")
                    print(self.others)
                elif type_ == 'exit':
                    print(f"Conference {self.conference_id} has been canceled")
                    self.reset()
                    pass
                elif type_ == 'p2p' and self.mode == 'cs':
                    self.mode = 'p2p'
                    print("switch mode to p2p")
                    self.p2p_ip = text[0]
                    self.p2p_port = int(text[1])
                    self.p2p_conn = (self.p2p_ip, self.p2p_port)
                elif type_ == 'cs' and self.mode == 'p2p':
                    self.mode = 'cs'
                    print("switch mode to cs")


            except (socket.error, OSError) as e:
                print(f"Socket error: {e}")
                break


    def run(self):
        threads = [
            threading.Thread(target=self.keep_share),
            threading.Thread(target=self.keep_recv),
            threading.Thread(target=self.start),
            threading.Thread(target=self.display_combined),
            threading.Thread(target=self.keep_receive_instruction)
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

    def connection_establish(self, server_ip, server_port, server_port2):
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            client_socket.connect((server_ip, int(server_port)))
            print(f"已连接到服务器 {server_ip}:{server_port}")
            self.tcp_conn2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_conn2.connect((server_ip, int(server_port2)))
            print(f"已建立第二个TCP连接到服务器 {server_ip}:{server_port2}")
            self.tcp_conn = client_socket
            self.server_addr = (server_ip, server_port)

            self.id = pickle.loads(self.tcp_conn.recv(1024))  # 反序列化收到的id
            print(f"分配到的客户端id:{self.id}")

            # 获取本机 IP 地址,绑定UDP套接字
            # hostname = socket.gethostname()
            # local_ip = socket.gethostbyname(hostname)
            self.sock.bind((LOCAL_IP, 20615 + self.id * 2))
            print(f"本机UDP地址: {LOCAL_IP}:{20615 + self.id * 2}")

            # Establish a second TCP connection


        except ConnectionError as e:
            print(f"连接失败: {e}")
            self.tcp_conn = None
            self.tcp_conn2 = None


if __name__ == '__main__':
    client1 = ConferenceClient()
    client1.connection_establish(SERVER_IP, MAIN_SERVER_PORT, MAIN_SERVER_PORT2)
    client1.run()
