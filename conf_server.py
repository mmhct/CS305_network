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
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.owner_ip = None  # the client who create the conference
        self.owner_port = None  # the port for the owner client
        self.clients_info = {}  # 实际上应该是一个字典，key包含client_ip;value包含UDP的ip,port
        self.mode = 'Client-Server'  # or 'P2P' if you want to support peer-to-peer conference mode
        self.loop = asyncio.new_event_loop()
        self.tasks = []

    async def handle_data(self, reader, writer, data_type):
        """
        running task: receive sharing stream data from a client and decide how to forward them to the rest clients
        """
        while self.running:
            # handle data
            await asyncio.sleep(1)

    # async def handle_client(self, reader, writer):
    #     """
    #     running task: handle the in-meeting requests or messages from clients
    #     """
    #     while self.running:
    #         # handle client
    #         await asyncio.sleep(1)

    async def handle_client(self, data, addr, transport):
        """
        Async function to handle the reception and forwarding of data.
        """
        print(f"Received data from {addr}: {data.decode()}")
        # Forward data to other clients
        for client in self.clients_info.values():
            if client != addr:  # Don't send back to the sender
                transport.sendto(data, client)  # Forward data to other clients

    async def log(self):
        while self.running:
            # print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def join_conference(self):
        pass

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.loop.stop()

    '''
    非异步的版本
    '''
    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''

        print((self.conference_ip, self.conference_port))

        # 创建服务器的UDP套接字
        serverSocket = socket(AF_INET, SOCK_DGRAM)
        try:
            # 绑定服务器套接字到指定的IP和端口
            serverSocket.bind((self.conference_ip, self.conference_port))
            print(f"Conference server listening on {self.conference_ip}:{self.conference_port}")

            self.running = True
            while self.running:
                # 接收来自客户端的数据
                data, addr = serverSocket.recvfrom(65535)  # 缓冲区大小为65535字节
                print(f"Received data from {addr}: {len(data)}bytes")

                # 将发送者的地址加入到客户端列表
                if addr not in self.clients_info.values():
                    client_id, _, _ = pickle.dumps(data)
                    self.clients_info[client_id] = addr
                    print(f"New client added: {addr}")

                # 将数据转发给其他客户端
                for client in self.clients_info.values():
                    if client != addr:  # 不回发给发送者
                        serverSocket.sendto(data, client)
                        print(f"Forwarded data to {client}")
        except OSError as e:
            print(f"Error occurred: {e}")
        finally:
            # 关闭套接字
            serverSocket.close()
            print("Server socket closed.")

        # # Create asyncio transport to use for UDP communication
        # loop = asyncio.new_event_loop()
        # asyncio.set_event_loop(loop)
        # server_transport, server_protocol = loop.run_until_complete(
        #     loop.create_datagram_endpoint(
        #         lambda: DatagramProtocol(self),
        #         local_addr=(self.conference_ip, self.conference_port)
        #     )
        # )
        #
        # self.loop.run_forever()


# class DatagramProtocol(asyncio.DatagramProtocol):
#     def __init__(self, server):
#         self.server = server
#         self.transport = None  # Initialize transport attribute
#
#     def connection_made(self, transport):
#         """
#         This is where we get the transport object.
#         """
#         self.transport = transport
#
#     def datagram_received(self, data, addr):
#         """
#         Handle the incoming data and forward it to other clients.
#         """
#         print(f"Received data from {addr}: {data.decode()}")
#         self.server.clients.append(addr)  # Add the client to the list
#         # Handle client in a new task
#         task = self.server.loop.create_task(self.server.handle_client(data, addr, self.transport))
#         self.server.tasks.append(task)
#

class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager
        self.max_conference_id = 0
        self.max_client_id = 0

    def handle_create_conference(self, addr):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        conference_id = self.generate_conference_id()
        conference_port = conference_id * 2 + 10000 # 我这里10001有冲突就换了一个
        # conference_port = 12345
        conference_server = ConferenceServer()
        conference_server.conference_id = conference_id
        conference_server.conference_ip = self.server_ip
        conference_server.conference_port = conference_port
        conference_server.owner_ip = addr[0]
        conference_server.owner_port = addr[1]
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

    def handle_join_conference(self, client_address, conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """

        if conference_id in self.conference_servers:
            conference_server = self.conference_servers[conference_id]
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

    def handle_quit_conference(self, client_address):
        """
        quit conference (in-meeting request & or no need to request)
        """
        for conference in self.conference_servers:
            if client_address in conference.clients_info:
                del conference.clients_info[client_address]
                return "successfully quit conference"

        return "Not in conference"

    def handle_cancel_conference(self, client_address):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        for conference in self.conference_servers:
            if client_address[0] == conference.owner_ip and client_address[1] == conference.owner_port:
                asyncio.run(conference.cancel_conference())
                return "successfully canceled conference"
        return "You are not the owner of the conference"

    def request_handler(self, addr, message):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """

        if message.startswith('create'):
            for conference in self.conference_servers.values():  # 遍历字典
                if conference.owner_ip == addr[0] and conference.owner_port == addr[1]:
                    return "You have already created a conference"

            return self.handle_create_conference(addr)  # 这里不能放在else之后
        elif message.startswith('join'):
            conference_id = int(message.split(' ')[1])
            return self.handle_join_conference(addr, conference_id)
        elif message.startswith('quit'):
            return self.handle_quit_conference(addr)
        elif message.startswith('cancel'):
            return self.handle_cancel_conference(addr)
        # invalid 指令
        else:
            return "Invalid command"

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
                # print(f"sentence:{sentence}")
                message = self.request_handler(addr, sentence)
                # print(f"message:{message}")
                serialized_message = pickle.dumps(message)  # 序列化为字节流
                connectionSocket.send(serialized_message)
        finally:
            connectionSocket.close()
            print(f"{addr} Client disconnected")
            # Handle the client disconnection

    def start(self):
        """
        start MainServer
        """
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind((self.server_ip, self.server_port))
        serverSocket.listen(100)
        print("The server is ready to receive")
        while True:
            connectionSocket, addr = serverSocket.accept()
            print(f"接受到来自 {addr} 的连接请求")

            # 在建立TCP连接时，给客户端分配不重复的id
            self.max_client_id += 1
            serialized_id = pickle.dumps(self.max_client_id)  # 序列化为字节流
            connectionSocket.send(serialized_id)

            client_thread = threading.Thread(target=self.handle_client, args=(connectionSocket, addr))
            client_thread.start()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
