import asyncio
import threading
from socket import socket, AF_INET, SOCK_STREAM

from util import *


class ConferenceServer:
    def __init__(self):
        # async server
        self.running = False
        self.conference_id = None  # conference_id for distinguish difference conference
        self.conf_serve_ports = None
        self.data_serve_ports = {}
        self.data_types = ['screen', 'camera', 'audio']  # example data types in a video conference
        self.owner_ip = None  # the client who create the conference
        self.owner_port = None  # the port for the owner client
        self.clients_info = None  # 这里写的是tcp连接的ip和port以及udp的ip和port，实际上应该是一个字典，key包含TCP的ip,port;value包含UDP的ip,port
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

    async def handle_client(self, reader, writer):
        """
        running task: handle the in-meeting requests or messages from clients
        """
        while self.running:
            # handle client
            await asyncio.sleep(1)

    async def log(self):
        while self.running:
            print('Something about server status')
            await asyncio.sleep(LOG_INTERVAL)

    async def cancel_conference(self):
        """
        handle cancel conference request: disconnect all connections to cancel the conference
        """
        self.running = False
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks, return_exceptions=True)
        self.loop.stop()

    def start(self):
        '''
        start the ConferenceServer and necessary running tasks to handle clients in this conference
        '''
        self.running = True
        self.tasks = [
            self.loop.create_task(self.handle_client(None, None)),
            self.loop.create_task(self.handle_data(None, None, None)),
            self.loop.create_task(self.log())
        ]
        self.loop.run_forever()


class MainServer:
    def __init__(self, server_ip, main_port):
        # async server
        self.server_ip = server_ip
        self.server_port = main_port
        self.main_server = None

        self.conference_conns = None
        self.conference_servers = {}  # self.conference_servers[conference_id] = ConferenceManager

    def handle_create_conference(self, ):
        """
        create conference: create and start the corresponding ConferenceServer, and reply necessary info to client
        """
        conference_id = self.generate_conference_id()
        conference_port = conference_id + 10000
        conference_server = ConferenceServer()
        conference_server.conference_port = conference_port
        self.conference_servers[conference_id] = conference_server
        threading.Thread(target=conference_server.start).start()
        return {"status": "success", "conference_id": conference_id, "conference_port": conference_port}

    def generate_conference_id(self):
        """
        Generate a unique conference ID
        """
        return len(self.conference_servers) + 1

    def handle_join_conference(self, conference_id):
        """
        join conference: search corresponding conference_info and ConferenceServer, and reply necessary info to client
        """
        if conference_id in self.conference_servers:
            conference_server = self.conference_servers[conference_id]
            # Perform operations on the existing conference_server thread
            # For example, you can call a method on the conference_server
            conference_server.handle_join_conference()#这个要定义
            return {"status": "success", "conference_id": conference_id}
        else:
            return {"status": "error", "message": "Conference ID not found"}

    def handle_quit_conference(self, client_address):
        """
        quit conference (in-meeting request & or no need to request)
        """
        for conference in self.conference_servers:
            if client_address in conference.clients_info:
                del conference.clients_info[client_address]
                return "success"

        return "Not in conference"

    def handle_cancel_conference(self, client_address):
        """
        cancel conference (in-meeting request, a ConferenceServer should be closed by the MainServer)
        """
        for conference in self.conference_servers:
            if client_address[0] == conference.owner_ip and client_address[1] == conference.owner_port:
                asyncio.run(conference.cancel_conference())
                return "success"
        return "You are not the owner of the conference"

    def request_handler(self, addr, message):
        """
        running task: handle out-meeting (or also in-meeting) requests from clients
        """

        if message.startswith('create'):
            for conference in self.conference_servers:
                if conference.owner_ip == addr[0] & conference.owner_port == addr[1]:
                    return "You have already created a conference"
                else:
                    return self.handle_create_conference()
        elif message.startswith('join'):
            conference_id = message.split(' ')[1]
            return self.handle_join_conference(conference_id)
        elif message.startswith('quit'):
            return self.handle_quit_conference(addr)
        elif message.startswith('cancel'):
            return self.handle_cancel_conference(addr)

    def handle_client(self, connectionSocket, addr):
        """
        Handle the client connection in a separate thread.
        """
        try:
            while True:
                sentence = connectionSocket.recv(1024).decode()
                if not sentence:
                    break
                message = self.request_handler(addr, sentence)
                connectionSocket.send(message.encode())
        finally:
            connectionSocket.close()
            # Handle the client disconnection

    def start(self):
        """
        start MainServer
        """
        serverSocket = socket(AF_INET, SOCK_STREAM)
        serverSocket.bind(('', self.server_port))
        serverSocket.listen(100)
        print("The server is ready to receive")
        while True:
            connectionSocket, addr = serverSocket.accept()
            client_thread = threading.Thread(target=self.handle_client, args=(connectionSocket, addr))
            client_thread.start()


if __name__ == '__main__':
    server = MainServer(SERVER_IP, MAIN_SERVER_PORT)
    server.start()
