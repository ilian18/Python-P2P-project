import socket
import threading
import json
import struct
import time
from src.file_manager import FileManager
from src.protocol import P2PProtocol 

PORT = 5001

class P2PNode:
    """Represents a single node in the Peer-to-Peer network.
    
    Handles peer discovery, broadcasting searches, and file transfers.
    """
    
    def __init__(self):
        """Initializes the P2P node with default configurations and instantiates the FileManager."""
        self.peers = []
        self.known_messages = set()
        self.search_results = {}
        self.file_manager = FileManager()
        self.local_ip = self.get_local_ip()

    def get_local_ip(self) -> str:
        """Determines the local IP address of the machine.

        Returns:
            str: The local IPv4 address, or '127.0.0.1' as a fallback.
        """
        temp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Doesn't need to actually connect, just evaluates the routing table
            temp_socket.connect(('8.8.8.8', 80))
            ip_address = temp_socket.getsockname()[0]
        except Exception: 
            ip_address = '127.0.0.1'
        finally: 
            temp_socket.close()
        return ip_address

    def add_peer(self, ip_address: str) -> None:
        """Adds a new peer to the known peers list.

        Args:
            ip_address (str): The IP address of the peer to add.
        """
        if ip_address not in self.peers and ip_address != self.local_ip:
            self.peers.append(ip_address)
            print(f"[+] Peer added: {ip_address}")

    # --- NETWORK TRANSMISSION ---
    
    def send_json(self, target_ip: str, data_dict: dict) -> None:
        """Sends a JSON-serializable dictionary to a target IP over TCP.

        Args:
            target_ip (str): The destination IP address.
            data_dict (dict): The data payload to send.
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(2)
            client_socket.connect((target_ip, PORT))
            client_socket.send(json.dumps(data_dict).encode('utf-8'))
            client_socket.close()
        except Exception: 
            pass  # Silent fail for unreachable nodes

    # --- SEARCH (GOSSIP PROTOCOL) ---
    
    def broadcast_search(self, filename: str) -> list:
        """Broadcasts a search request for a file to all known peers.

        Args:
            filename (str): The name of the file to search for.

        Returns:
            list: A list of IP addresses that host the requested file.
        """
        print(f"[*] Initiating search for: {filename}...")
        self.search_results[filename] = []
        
        packet = P2PProtocol.create_search(filename, self.local_ip)
        message_id = packet['id']
        self.known_messages.add(message_id)
        
        for peer in self.peers:
            threading.Thread(target=self.send_json, args=(peer, packet)).start()

        print("[*] Waiting for responses (3s)...")
        time.sleep(3)
        return self.search_results.get(filename, [])

    # --- SERVER ---
    
    def start_server(self) -> None:
        """Starts the TCP server to listen for incoming P2P connections."""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind(('0.0.0.0', PORT))
        server_socket.listen(10)
        
        while True:
            client_socket, client_address = server_socket.accept()
            threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()

    def handle_client(self, client_socket: socket.socket, client_address: tuple) -> None:
        """Processes incoming requests from other peers.

        Args:
            client_socket (socket.socket): The socket object for the connected client.
            client_address (tuple): The address tuple (IP, port) of the client.
        """
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data: 
                return
            
            request = json.loads(data)
            command = request.get('command')

            if command == P2PProtocol.SEARCH:
                self._handle_search(request)
            elif command == P2PProtocol.FOUND:
                self._handle_found(request)
            elif command == P2PProtocol.GET_METADATA:
                self._handle_metadata(client_socket, request)
            elif command == P2PProtocol.GET_CHUNK:
                self._handle_chunk(client_socket, request)

        except Exception: 
            pass
        finally: 
            client_socket.close()

    # --- HANDLERS ---
    
    def _handle_search(self, packet: dict) -> None:
        """Handles incoming SEARCH packets."""
        message_id = packet['id']
        if message_id in self.known_messages: 
            return
        self.known_messages.add(message_id)

        # Check if we have the file
        if self.file_manager.get_total_chunks(packet['filename']) > 0:
            response = P2PProtocol.create_found(packet['filename'], self.local_ip)
            self.send_json(packet['origin_ip'], response)
        # Otherwise, propagate the search if TTL allows
        elif packet['ttl'] > 0:
            packet['ttl'] -= 1
            for peer in self.peers:
                if peer != packet['origin_ip']:
                    self.send_json(peer, packet)

    def _handle_found(self, packet: dict) -> None:
        """Handles incoming FOUND packets."""
        filename = packet['filename']
        peer_ip = packet['peer_ip']
        if filename not in self.search_results:
            self.search_results[filename] = []
        self.search_results[filename].append(peer_ip)

    def _handle_metadata(self, client_socket: socket.socket, request: dict) -> None:
        """Handles requests for file metadata (chunk count)."""
        total_chunks = self.file_manager.get_total_chunks(request.get('filename'))
        status = P2PProtocol.FOUND if total_chunks > 0 else "ERROR"
        response = {"status": status, "total_chunks": total_chunks}
        client_socket.send(json.dumps(response).encode('utf-8'))

    def _handle_chunk(self, client_socket: socket.socket, request: dict) -> None:
        """Handles requests to send a specific file chunk."""
        data = self.file_manager.read_chunk(request.get('filename'), request.get('chunk_id'))
        # Send an 8-byte unsigned long long representing the payload size
        client_socket.send(struct.pack("Q", len(data) if data else 0))
        if data: 
            client_socket.sendall(data)

    # --- DOWNLOAD FLOW ---
    
    def download_file(self, filename: str, target_ip: str) -> None:
        """Manages the full download process of a file from a specific peer.

        Args:
            filename (str): The name of the file to download.
            target_ip (str): The IP address of the peer hosting the file.
        """
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((target_ip, PORT))
            
            # Request metadata to know how many chunks to download
            client_socket.send(json.dumps(P2PProtocol.request_metadata(filename)).encode('utf-8'))
            response = json.loads(client_socket.recv(1024).decode('utf-8'))
            client_socket.close()
        except Exception: 
            return

        if response['status'] != P2PProtocol.FOUND:
            print("[x] File not found on remote node.")
            return

        total_chunks = response['total_chunks']
        print(f"[*] Downloading ({total_chunks} chunks)...")
        
        for i in range(total_chunks):
            self._download_chunk(target_ip, filename, i, total_chunks)
            
        print(f"\n[v] Download completed: {filename}")

    def _download_chunk(self, target_ip: str, filename: str, chunk_id: int, total_chunks: int) -> None:
        """Downloads a single chunk from a peer and writes it to disk."""
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((target_ip, PORT))
            
            request = P2PProtocol.request_chunk(filename, chunk_id)
            client_socket.send(json.dumps(request).encode('utf-8'))
            
            # Read the 8-byte header to know incoming payload size
            header = client_socket.recv(8)
            if not header: 
                return
            payload_size = struct.unpack("Q", header)[0]
            
            data = b""
            while len(data) < payload_size:
                packet = client_socket.recv(4096)
                if not packet: 
                    break
                data += packet
            
            self.file_manager.write_chunk(filename, chunk_id, data)
            print(f"\rProgress: {((chunk_id + 1) / total_chunks) * 100:.1f}%", end='')
            
            client_socket.close()
        except Exception: 
            pass