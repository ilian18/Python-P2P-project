import socket
import threading
import json
import struct
import time
from src.file_manager import FileManager
from src.protocol import P2PProtocol  # <--- On importe le protocole ici

PORT = 5001

class P2PNode:
    def __init__(self):
        self.peers = []
        self.known_messages = set()
        self.search_results = {}
        self.fm = FileManager()
        self.my_ip = self.get_local_ip()

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception: ip = '127.0.0.1'
        finally: s.close()
        return ip

    def add_peer(self, ip):
        if ip not in self.peers and ip != self.my_ip:
            self.peers.append(ip)
            print(f"[+] Ami ajouté : {ip}")

    # --- ENVOI RESEAU ---
    def send_json(self, target_ip, data_dict):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target_ip, PORT))
            sock.send(json.dumps(data_dict).encode('utf-8'))
            sock.close()
        except Exception: pass

    # --- RECHERCHE (GOSSIP) ---
    def broadcast_search(self, filename):
        print(f"[*] Recherche lancée pour : {filename}...")
        self.search_results[filename] = []
        
        # UTILISATION DU PROTOCOL.PY ICI
        packet = P2PProtocol.create_search(filename, self.my_ip)
        msg_id = packet['id']
        self.known_messages.add(msg_id)
        
        for peer in self.peers:
            threading.Thread(target=self.send_json, args=(peer, packet)).start()

        print("[*] Attente des réponses (3s)...")
        time.sleep(3)
        return self.search_results.get(filename, [])

    # --- SERVEUR ---
    def start_server(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(('0.0.0.0', PORT))
        server.listen(10)
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client, addr)).start()

    def handle_client(self, client_sock, addr):
        try:
            data = client_sock.recv(1024).decode('utf-8')
            if not data: return
            request = json.loads(data)
            cmd = request.get('command')

            # On compare avec les constantes du Protocole
            if cmd == P2PProtocol.SEARCH:
                self._handle_search(request)
            elif cmd == P2PProtocol.FOUND:
                self._handle_found(request)
            elif cmd == P2PProtocol.GET_METADATA:
                self._handle_metadata(client_sock, request)
            elif cmd == P2PProtocol.GET_CHUNK:
                self._handle_chunk(client_sock, request)

        except Exception: pass
        finally: client_sock.close()

    # --- SOUS-FONCTIONS ---
    def _handle_search(self, packet):
        msg_id = packet['id']
        if msg_id in self.known_messages: return
        self.known_messages.add(msg_id)

        if self.fm.get_total_chunks(packet['filename']) > 0:
            # Réponse propre via Protocol
            resp = P2PProtocol.create_found(packet['filename'], self.my_ip)
            self.send_json(packet['origin_ip'], resp)
        elif packet['ttl'] > 0:
            packet['ttl'] -= 1
            for peer in self.peers:
                if peer != packet['origin_ip']:
                    self.send_json(peer, packet)

    def _handle_found(self, packet):
        filename = packet['filename']
        peer_ip = packet['peer_ip']
        if filename not in self.search_results:
            self.search_results[filename] = []
        self.search_results[filename].append(peer_ip)

    def _handle_metadata(self, sock, req):
        total = self.fm.get_total_chunks(req.get('filename'))
        status = P2PProtocol.FOUND if total > 0 else "ERROR"
        resp = {"status": status, "total_chunks": total}
        sock.send(json.dumps(resp).encode('utf-8'))

    def _handle_chunk(self, sock, req):
        data = self.fm.read_chunk(req.get('filename'), req.get('chunk_id'))
        sock.send(struct.pack("Q", len(data) if data else 0))
        if data: sock.sendall(data)

    # --- TELECHARGEMENT ---
    def download_file(self, filename, target_ip):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((target_ip, PORT))
            # Demande via Protocol
            sock.send(json.dumps(P2PProtocol.request_metadata(filename)).encode('utf-8'))
            resp = json.loads(sock.recv(1024).decode('utf-8'))
            sock.close()
        except: return

        if resp['status'] != P2PProtocol.FOUND:
            print("[x] Fichier non trouvé.")
            return

        total = resp['total_chunks']
        print(f"[*] Téléchargement ({total} paquets)...")
        for i in range(total):
            self._download_chunk(target_ip, filename, i, total)
        print(f"\n[v] Terminé : {filename}")

    def _download_chunk(self, ip, filename, chunk_id, total):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PORT))
            # Demande via Protocol
            req = P2PProtocol.request_chunk(filename, chunk_id)
            sock.send(json.dumps(req).encode('utf-8'))
            
            header = sock.recv(8)
            if not header: return
            size = struct.unpack("Q", header)[0]
            
            data = b""
            while len(data) < size:
                packet = sock.recv(4096)
                if not packet: break
                data += packet
            
            self.fm.write_chunk(filename, chunk_id, data)
            print(f"\rProgression : {((chunk_id+1)/total)*100:.1f}%", end='')
            sock.close()
        except Exception: pass