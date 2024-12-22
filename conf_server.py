import asyncio
import pickle
import threading
from socket import socket, AF_INET, SOCK_STREAM, SOCK_DGRAM

from util import *


class ConferenceServer:
    def __init__(self):
        # async server
        self.running = False
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conference_ip = None
        self.conference_port = None  # 会议室传输控制指令的端口号
        self.data_serve_ports = {}  # 会议室传输数据的端口号
        self.data_types = ['screen', 'camera', 'audio', 'text']  # example data types in a video conference
        self.owner_ip = None  # the client who create the conference
        self.owner_port = None  # the port for the owner client
        self.clients_info = {}  # 实际上应该是一个字典，key包含client_id;value包含UDP的(ip,camera_port,screen_port,audio_port)
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.serverSocket = socket(AF_INET, SOCK_DGRAM)
        self.serverSockets = {}  # {client_id:(camera_socket, screen_socket, audio_socket)}
        self.MainServer = None

    def cancel_conference(self):
        self.running = False
        # self.conference_id = None
        # self.conference_ip = None
        # self.conference_port = None
        # self.owner_ip = None
        # self.owner_port = None

    def create_udp(self, id):
        '''
        创建UDP套接字
        '''
        socket_camera = socket(AF_INET, SOCK_DGRAM)
        socket_camera.bind((self.conference_ip, self.conference_port))
        self.conference_port += 1
        socket_screen = socket(AF_INET, SOCK_DGRAM)
        socket_screen.bind((self.conference_ip, self.conference_port))
        self.conference_port += 1
        socket_audio = socket(AF_INET, SOCK_DGRAM)
        socket_audio.bind((self.conference_ip, self.conference_port))
        self.conference_port += 1
        self.serverSockets[id] = (socket_camera, socket_screen, socket_audio)

        user_thread = threading.Thread(target=self.user_udp_thread_start, args=(id, 0))
        user_thread.start()
        user_thread = threading.Thread(target=self.user_udp_thread_start, args=(id, 1))
        user_thread.start()
        user_thread = threading.Thread(target=self.user_udp_thread_start, args=(id, 2))
        user_thread.start()

        return socket_camera, socket_screen, socket_audio

    def user_udp_thread_start(self, id, index):
        '''
        启动用户的UDP套接字进程
        0: camera 1: screen 2: audio
        '''
        print((self.conference_ip, self.serverSockets[id]))
        try:


            print(f"Conference server listening on {self.conference_ip}:{self.serverSockets[id]}")
            socket_=self.serverSockets[id][index]
            while id in self.clients_info:
                # 接收来自客户端的数据
                data, addr = socket_.recvfrom(65535)  # 缓冲区大小为65535字节
                print(f"Received data from {addr}: {len(data)}bytes")

                # 将发送者的地址加入到客户端列表
                # if addr not in self.clients_info.values():
                #     client_id, _, _ = pickle.loads(data)
                #     self.clients_info[client_id] = addr
                #     print(f"New client added: {addr}")

                # 将数据转发给其他客户端
                for client in self.clients_info.values():
                    # if client != addr:  # 不回发给发送者
                    socket_.sendto(data, (client[0], client[index+1]))
                    print(f"Forwarded data to {client}")
        except OSError as e:
            print(f"Error occurred: {e}")
        finally:
            # 关闭套接字
            self.serverSockets[id][index].close()
            print(f"Conference server {self.serverSockets[id][index]} socket closed.")

    '''
    非异步的版本
    '''

    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''

        print((self.conference_ip, self.conference_port))

        # 创建服务器的UDP套接字

        try:
            # 绑定服务器套接字到指定的IP和端口
            self.serverSocket.bind((self.conference_ip, self.conference_port))
            print(f"Conference server listening on {self.conference_ip}:{self.conference_port}")

            self.running = True
            while self.running:
                # 接收来自客户端的数据
                data, addr = self.serverSocket.recvfrom(65535)  # 缓冲区大小为65535字节
                print(f"Received data from {addr}: {len(data)}bytes")

                # 将发送者的地址加入到客户端列表
                # if addr not in self.clients_info.values():
                #     client_id, _, _ = pickle.loads(data)
                #     self.clients_info[client_id] = addr
                #     print(f"New client added: {addr}")

                # 将数据转发给其他客户端
                for client in self.clients_info.values():
                    # if client != addr:  # 不回发给发送者
                    self.serverSocket.sendto(data, client)
                    print(f"Forwarded data to {client}")
        except OSError as e:
            print(f"Error occurred: {e}")
        finally:
            # 关闭套接字
            data = pickle.dumps(('', 'exit', ''))
            for client in self.clients_info.keys():
                self.MainServer.tcp_conns_to_clients2[client].send(data)
            self.clients_info.clear()
            self.serverSocket.close()
            print(f"Conference server {self.conference_id} socket closed.")


class MainServer:
    def __init__(self, server_ip, main_port, main_port2):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.server_port2 = main_port2
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager
        self.max_conference_id = 0
        self.max_client_id = 0
        self.tcp_conns_to_clients = {}  # {client_id:发送给客户端用的tcp套接字}
        self.tcp_conns_to_clients2 = {}  # {client_id:发送给客户端keep_receive_instruction用的tcp套接字}

    def handle_create_conference(self, addr, client_id, udp_ip, udp_port):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        conference_id = self.generate_conference_id()
        conference_port = conference_id * 2 + 10000  # 我这里10001有冲突就换了一个
        # conference_port = 12345
        conference_server = ConferenceServer()
        conference_server.conference_id = conference_id
        conference_server.conference_ip = self.server_ip
        conference_server.conference_port = conference_port
        conference_server.owner_ip = addr[0]
        conference_server.owner_port = addr[1]
        conference_server.MainServer = self
        conference_server.clients_info[client_id] = (udp_ip, udp_port)  # 将用户id和udp套接字地址存入
        print(f"Client{client_id} added to Conference{conference_id}: UDP {(udp_ip, udp_port)}")
        self.conference_servers[conference_id] = conference_server
        threading.Thread(target=conference_server.start).start()
        print({"status": "success", "conference_id": conference_id,
               "conference_ip": conference_server.conference_ip,
               "conference_port": conference_port})
        return {"status": "success", "conference_id": conference_id,
                "conference_ip": conference_server.conference_ip,
                "conference_port": conference_port}

    def generate_conference_id(self):
        """
        Generate a unique conference ID
        """
        # 如果删除会议，可能会有重复ID
        self.max_conference_id += 1
        return self.max_conference_id

    def handle_join_conference(self, client_address, client_id, conference_id, udp_ip, udp_port):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """

        if conference_id in self.conference_servers:
            conference_server = self.conference_servers[conference_id]
            for client in conference_server.clients_info:
                self.tcp_conns_to_clients2[client].send(
                    pickle.dumps((client_id, "join", f"Client {client_id} comes in.")))
                self.tcp_conns_to_clients2[client_id].send(pickle.dumps((client, "join", f"Client {client} exists.")))
            conference_server.clients_info[client_id] = (udp_ip, udp_port)
            print(f"Client{client_id} added to Conference{conference_id}: UDP {(udp_ip, udp_port)}")
            print(f"client info {conference_server.clients_info}")
            # Perform operations on the existing conference_server thread
            # For example, you can call a method on the conference_server
            # conference_server.join_conference()  # 这个要定义
            return {"status": "success", "conference_id": conference_id,
                    "conference_ip": conference_server.conference_ip,
                    "conference_port": conference_server.conference_port}
            # return f"success {conference_id} {conference_server.conference_port}"

        else:
            return {"status": "error", "conference_id": None, "conference_ip": None,
                    "conference_port": None}
            # return f"error"

    def handle_quit_conference(self, client_id, conference_id):
        """
        quit conference (in-meeting request & or no need to request)
        """

        if conference_id in self.conference_servers:
            if client_id in self.conference_servers[conference_id].clients_info:
                del self.conference_servers[conference_id].clients_info[client_id]
                print(f'Client {client_id} has quit conference{conference_id}')
                for client in self.conference_servers[conference_id].clients_info:
                    self.tcp_conns_to_clients2[client].send(
                        pickle.dumps((client_id, "quit", f"client {client_id} has quit conference")))
                if len(self.conference_servers[conference_id].clients_info) == 0:
                    # 如果所有人离开会议，自动取消会议
                    self.conference_servers[conference_id].cancel_conference()
                    del self.conference_servers[conference_id]
                return {"status": "success", "conference_id": None,
                        "conference_ip": None,
                        "conference_port": None}

        return {"status": "error", "conference_id": None, "conference_ip": None,
                "conference_port": None}

    def handle_cancel_conference(self, client_address):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        for conference in self.conference_servers:
            if (client_address[0] == self.conference_servers[conference].owner_ip and
                    client_address[1] == self.conference_servers[conference].owner_port):
                self.conference_servers[conference].cancel_conference()
                del self.conference_servers[conference]
                return {"status": "success", "conference_id": None,
                        "conference_ip": None,
                        "conference_port": None}
        return {"status": "error", "conference_id": None, "conference_ip": None,
                "conference_port": None}

    def handle_switch_conference(self, message):
        """
        switch conference: tell other clients to maintain others list
        """
        client_id = int(message.split(' ')[3])
        conference_id = int(message.split(' ')[4])

        if conference_id in self.conference_servers:
            conference_server = self.conference_servers[conference_id]
            for other_client_id, addr in conference_server.clients_info.items():
                if other_client_id != client_id:
                    try:
                        temp = (client_id, 'switch', message)
                        print(f"temp:{temp}")
                        data = pickle.dumps(temp)
                        self.tcp_conns_to_clients2[other_client_id].send(data)
                        print(f"Forwarded switch message to client {other_client_id}")
                    except Exception as e:
                        print(f"Failed to forward switch message to client {other_client_id}: {e}")
            return {"status": "success"}
        else:
            return {"status": "error", "message": "Conference not found"}

    def handle_search_conference(self):
        """
        search conference: return all the available conference
        """
        return " ".join(str(key) for key in self.conference_servers.keys())

    def request_handler(self, addr, message):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """

        if message.startswith('create'):
            for conference in self.conference_servers.values():  # 遍历字典
                if conference.owner_ip == addr[0] and conference.owner_port == addr[1]:
                    return "You have already created a conference"
            client_id = int(message.split(' ')[1])
            udp_ip = message.split(' ')[2]
            udp_port = int(message.split(' ')[3])
            return self.handle_create_conference(addr, client_id, udp_ip, udp_port)  # 这里不能放在else之后
        elif message.startswith('join'):
            client_id = int(message.split(' ')[1])
            conference_id = int(message.split(' ')[2])
            udp_ip = message.split(' ')[3]
            udp_port = int(message.split(' ')[4])
            return self.handle_join_conference(addr, client_id, conference_id, udp_ip, udp_port)
        elif message.startswith('quit'):
            client_id = int(message.split(' ')[1])
            conference_id = int(message.split(' ')[2])
            return self.handle_quit_conference(client_id, conference_id)
        elif message.startswith('cancel'):
            return self.handle_cancel_conference(addr)
        elif message.startswith('switch'):
            return self.handle_switch_conference(message)
        elif message.startswith('search'):
            return self.handle_search_conference()
        # invalid 指令
        else:
            return "Invalid command"

    def find_conference_and_client_by_ip(self, conference_server, ip):
        for conference_id, conference in conference_server.items():
            for client_id, client_address in conference.clients_info.items():
                client_ip, _ = client_address
                if client_ip == ip:
                    return client_id, conference_id
        return None, None  # 如果没有找到该地址，返回 None  

    # 测试

    def handle_client(self, connectionSocket, addr):
        """
        Handle the client connection in a separate thread.
        """
        try:
            while True:
                sentence = connectionSocket.recv(1024)
                # print(sentence)
                if not sentence:
                    # print("出现空字符串")
                    break
                sentence = pickle.loads(sentence)  # 反序列化
                print(f"sentence:{sentence}")
                message = self.request_handler(addr, sentence)
                # print(f"message:{message}")
                serialized_message = pickle.dumps(message)  # 序列化为字节流
                connectionSocket.send(serialized_message)
        except (OSError, pickle.PickleError) as e:
            ip, _ = addr
            client_id, conference_id = self.find_conference_and_client_by_ip(self.conference_servers, ip)
            print(f"client_id:{client_id}, conference_id:{conference_id}")
            self.handle_quit_conference(client_id, conference_id)
            print(f"[Error] Handling client {addr} failed: {e}")

        finally:
            connectionSocket.close()
            print(f"{addr} Client disconnected")
            # Handle the client disconnection

    def start(self):
        """
        start MainServer
        """
        try:
            serverSocket = socket(AF_INET, SOCK_STREAM)
            serverSocket.bind((self.server_ip, self.server_port))
            serverSocket.listen(100)

            serverSocket2 = socket(AF_INET, SOCK_STREAM)
            serverSocket2.bind((self.server_ip, self.server_port2))
            serverSocket2.listen(100)
            print(f"The server{(self.server_ip, self.server_port)} is ready to receive")
        except OSError as e:
            print(f"[Error] Server initialization failed: {e}")
            return

        while True:
            try:
                connectionSocket, addr = serverSocket.accept()
                print(f"接受到来自 {addr} 的连接请求")
                connectionSocket2, addr = serverSocket2.accept()
            except OSError as e:
                print(f"[Error] Accepting connection failed: {e}")
                continue

            try:
                # 在建立TCP连接时，给客户端分配不重复的id
                self.max_client_id += 1
                serialized_id = pickle.dumps(self.max_client_id)  # 序列化为字节流
                connectionSocket.send(serialized_id)
                self.tcp_conns_to_clients[self.max_client_id] = connectionSocket
                self.tcp_conns_to_clients2[self.max_client_id] = connectionSocket2
            except (OSError, pickle.PickleError) as e:
                print(f"[Error] Sending client ID to {addr} failed: {e}")
                connectionSocket.close()
                continue

            try:
                client_thread = threading.Thread(target=self.handle_client, args=(connectionSocket, addr))
                client_thread.start()
            except Exception as e:
                print(f"[Error] Starting thread for client {addr} failed: {e}")
                connectionSocket.close()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT, MAIN_SERVER_PORT2)
    server.start()
