import socket
import threading
import json
import uuid
import struct
import time
from src.file_manager import FileManager

PORT = 5001

class P2PNode:
    """
    Gère la logique réseau : Serveur TCP, Client, et Protocole Gossip.
    """
    def __init__(self):
        self.peers = []  # Liste des IP amies
        self.known_messages = set() # Pour éviter les boucles infinies de messages
        self.search_results = {} # Stockage temporaire des résultats de recherche
        self.fm = FileManager() # Instance du gestionnaire de fichiers
        self.my_ip = self.get_local_ip()

    def get_local_ip(self):
        """Récupère l'IP locale utilisée sur le réseau."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def add_peer(self, ip):
        if ip not in self.peers and ip != self.my_ip:
            self.peers.append(ip)
            print(f"[+] Ami ajouté : {ip}")

    # --- COMMUNICATION ---
    def send_json(self, target_ip, data_dict):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((target_ip, PORT))
            sock.send(json.dumps(data_dict).encode('utf-8'))
            sock.close()
        except Exception as e:
            print(f"[x] Impossible de joindre {target_ip}: {e}")

    # --- RECHERCHE (GOSSIP) ---
    def broadcast_search(self, filename):
        print(f"[*] Recherche lancée pour : {filename}...")
        self.search_results[filename] = []
        msg_id = str(uuid.uuid4())
        self.known_messages.add(msg_id)
        
        packet = {
            "command": "SEARCH",
            "id": msg_id,
            "filename": filename,
            "origin_ip": self.my_ip,
            "ttl": 3 # Durée de vie du message (3 sauts max)
        }
        
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
        print(f"\n[Serveur] En ligne sur {self.my_ip}:{PORT}")
        
        while True:
            client, addr = server.accept()
            threading.Thread(target=self.handle_client, args=(client, addr)).start()

    def handle_client(self, client_sock, addr):
        try:
            data = client_sock.recv(1024).decode('utf-8')
            if not data: return
            request = json.loads(data)
            cmd = request.get('command')

            if cmd == "SEARCH":
                self._handle_search(request)
            elif cmd == "FOUND":
                self._handle_found(request)
            elif cmd == "GET_METADATA":
                self._handle_metadata(client_sock, request)
            elif cmd == "GET_CHUNK":
                self._handle_chunk(client_sock, request)

        except Exception:
            pass
        finally:
            client_sock.close()

    # --- SOUS-FONCTIONS SERVEUR ---
    def _handle_search(self, packet):
        msg_id = packet['id']
        filename = packet['filename']
        origin_ip = packet['origin_ip']
        ttl = packet['ttl']

        if msg_id in self.known_messages: return
        self.known_messages.add(msg_id)

        # Si j'ai le fichier, je le dis
        if self.fm.get_total_chunks(filename) > 0:
            resp = {"command": "FOUND", "filename": filename, "peer_ip": self.my_ip}
            self.send_json(origin_ip, resp)
        
        # Sinon je fais passer le message
        elif ttl > 0:
            packet['ttl'] -= 1
            for peer in self.peers:
                if peer != origin_ip:
                    self.send_json(peer, packet)

    def _handle_found(self, packet):
        filename = packet['filename']
        peer_ip = packet['peer_ip']
        print(f"\n[!] FICHIER TROUVÉ ! {filename} chez {peer_ip}")
        if filename not in self.search_results:
            self.search_results[filename] = []
        self.search_results[filename].append(peer_ip)

    def _handle_metadata(self, sock, req):
        filename = req.get('filename')
        total = self.fm.get_total_chunks(filename)
        resp = {"status": "FOUND" if total > 0 else "ERROR", "total_chunks": total}
        sock.send(json.dumps(resp).encode('utf-8'))

    def _handle_chunk(self, sock, req):
        filename = req.get('filename')
        chunk_id = req.get('chunk_id')
        data = self.fm.read_chunk(filename, chunk_id)
        if data:
            sock.send(struct.pack("Q", len(data)))
            sock.sendall(data)
        else:
            sock.send(struct.pack("Q", 0))

    # --- CLIENT TELECHARGEMENT ---
    def download_file(self, filename, target_ip):
        try:
            # 1. Obtenir la taille
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((target_ip, PORT))
            sock.send(json.dumps({"command": "GET_METADATA", "filename": filename}).encode('utf-8'))
            resp = json.loads(sock.recv(1024).decode('utf-8'))
            sock.close()
        except:
            print("[x] Erreur connexion.")
            return

        if resp['status'] != "FOUND":
            print("[x] Fichier introuvable chez le pair.")
            return

        total_chunks = resp['total_chunks']
        print(f"[*] Téléchargement de {total_chunks} morceaux...")

        for i in range(total_chunks):
            self._download_single_chunk(target_ip, filename, i, total_chunks)
        
        print(f"\n[v] Terminé : {DOWNLOAD_PREFIX}{filename}")

    def _download_single_chunk(self, ip, filename, chunk_id, total):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip, PORT))
            req = json.dumps({"command": "GET_CHUNK", "filename": filename, "chunk_id": chunk_id})
            sock.send(req.encode('utf-8'))
            
            header = sock.recv(8)
            if not header: return
            size = struct.unpack("Q", header)[0]
            
            data = b""
            while len(data) < size:
                packet = sock.recv(4096)
                if not packet: break
                data += packet
            
            self.fm.write_chunk(filename, chunk_id, data)
            
            percent = ((chunk_id + 1) / total) * 100
            print(f"\rProgression : {percent:.1f}%", end='')
            sock.close()
        except Exception as e:
            print(f" [Err Chunk {chunk_id}: {e}]")