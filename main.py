import socket
import threading
import os
import json
import struct
import time
import uuid

# --- CONFIGURATION ---
PORT = 5001
CHUNK_SIZE = 1024 * 1024  # 1 Mo
SHARED_FOLDER = "shared_files"
DOWNLOAD_PREFIX = "downloaded_"

# Création du dossier partagé
if not os.path.exists(SHARED_FOLDER):
    os.makedirs(SHARED_FOLDER)

# --- GESTIONNAIRE DE FICHIERS (Issu de finale.py) ---
class FileManager:
    def get_file_path(self, filename):
        return os.path.join(SHARED_FOLDER, filename)

    def get_total_chunks(self, filename):
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return 0
        file_size = os.path.getsize(filepath)
        return (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE > 0 else 0)

    def read_chunk(self, filename, chunk_index):
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            f.seek(chunk_index * CHUNK_SIZE)
            data = f.read(CHUNK_SIZE)
            return data

    def write_chunk(self, filename, chunk_index, data):
        save_name = f"{DOWNLOAD_PREFIX}{filename}"
        filepath = self.get_file_path(save_name)
        if not os.path.exists(filepath):
            with open(filepath, 'wb') as f: pass 
        with open(filepath, 'r+b') as f:
            f.seek(chunk_index * CHUNK_SIZE)
            f.write(data)

fm = FileManager()

# --- NOEUD P2P (Fusion Client/Serveur) ---
class P2PNode:
    def __init__(self):
        self.peers = []  # Liste des amis (IPs)
        self.known_messages = set() # Historique des IDs de messages (anti-boucle)
        self.search_results = {} # Stocke temporairement qui a quel fichier
        self.my_ip = self.get_local_ip()

    def get_local_ip(self):
        """Récupère l'IP locale (LAN) pour tester facilement entre 2 ordis"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Astuce pour trouver son IP utilisée vers l'extérieur
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

    # --- ENVOI DE MESSAGES ---
    def send_json(self, target_ip, data_dict):
        """Envoie une commande JSON simple à un pair"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2) # Timeout court pour ne pas bloquer
            sock.connect((target_ip, PORT))
            sock.send(json.dumps(data_dict).encode('utf-8'))
            sock.close()
        except Exception as e:
            print(f"[x] Impossible de joindre {target_ip}: {e}")

    # --- LOGIQUE DE RECHERCHE (Gossip/Flooding) ---
    def broadcast_search(self, filename):
        print(f"[*] Lancement de la recherche pour : {filename}...")
        self.search_results[filename] = [] # Reset des résultats
        msg_id = str(uuid.uuid4())
        self.known_messages.add(msg_id)
        
        packet = {
            "command": "SEARCH",
            "id": msg_id,
            "filename": filename,
            "origin_ip": self.my_ip,
            "ttl": 3 # Saut de 3 noeuds max
        }
        
        # Envoyer à tous mes pairs
        for peer in self.peers:
            threading.Thread(target=self.send_json, args=(peer, packet)).start()

        # On attend un peu les réponses
        print("[*] Attente des réponses (3s)...")
        time.sleep(3)
        
        results = self.search_results.get(filename, [])
        return results

    # --- LOGIQUE SERVEUR ---
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

            # 1. Quelqu'un cherche un fichier (SEARCH)
            if cmd == "SEARCH":
                self.handle_search_request(request)

            # 2. Quelqu'un me dit qu'il a le fichier (FOUND)
            elif cmd == "FOUND":
                filename = request['filename']
                peer_ip = request['peer_ip']
                print(f"\n[!] FICHIER TROUVÉ ! {filename} est chez {peer_ip}")
                if filename not in self.search_results:
                    self.search_results[filename] = []
                self.search_results[filename].append(peer_ip)

            # 3. Quelqu'un demande la taille (GET_METADATA)
            elif cmd == "GET_METADATA":
                filename = request.get('filename')
                total = fm.get_total_chunks(filename)
                resp = {"status": "FOUND" if total > 0 else "ERROR", "total_chunks": total}
                client_sock.send(json.dumps(resp).encode('utf-8'))

            # 4. Quelqu'un télécharge un bout (GET_CHUNK)
            elif cmd == "GET_CHUNK":
                self.handle_chunk_request(client_sock, request)

        except Exception as e:
            # print(f"[Erreur Serveur] {e}") # Debug off pour propreté
            pass
        finally:
            client_sock.close()

    def handle_search_request(self, packet):
        msg_id = packet['id']
        filename = packet['filename']
        origin_ip = packet['origin_ip']
        ttl = packet['ttl']

        # A. Déjà vu ?
        if msg_id in self.known_messages:
            return
        self.known_messages.add(msg_id)

        # B. Est-ce que j'ai le fichier ?
        if os.path.exists(fm.get_file_path(filename)):
            # Oui ! Je réponds directement à celui qui cherche
            resp = {"command": "FOUND", "filename": filename, "peer_ip": self.my_ip}
            self.send_json(origin_ip, resp)
        
        # C. Relais aux autres (si TTL > 0)
        elif ttl > 0:
            packet['ttl'] -= 1
            for peer in self.peers:
                if peer != origin_ip: # Ne pas renvoyer à l'envoyeur
                    self.send_json(peer, packet)

    def handle_chunk_request(self, sock, req):
        filename = req.get('filename')
        chunk_id = req.get('chunk_id')
        data = fm.read_chunk(filename, chunk_id)
        if data:
            sock.send(struct.pack("Q", len(data))) # Header taille
            sock.sendall(data)
        else:
            sock.send(struct.pack("Q", 0))

    # --- TÉLÉCHARGEMENT (CLIENT) ---
    def download_file(self, filename, target_ip):
        # 1. Demande métadonnées
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((target_ip, PORT))
            sock.send(json.dumps({"command": "GET_METADATA", "filename": filename}).encode('utf-8'))
            resp = json.loads(sock.recv(1024).decode('utf-8'))
            sock.close()
        except:
            print("[x] Erreur connexion au pair.")
            return

        if resp['status'] != "FOUND":
            print("[x] Erreur bizarre: le pair n'a plus le fichier.")
            return

        total_chunks = resp['total_chunks']
        print(f"[*] Démarrage du téléchargement ({total_chunks} morceaux) depuis {target_ip}...")

        # 2. Boucle de téléchargement
        for i in range(total_chunks):
            self.download_single_chunk(target_ip, filename, i, total_chunks)
        
        print(f"\n[v] Téléchargement terminé : {DOWNLOAD_PREFIX}{filename}")

    def download_single_chunk(self, ip, filename, chunk_id, total):
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
            
            fm.write_chunk(filename, chunk_id, data)
            
            # Affichage progression
            percent = ((chunk_id + 1) / total) * 100
            print(f"\rProgression : [{chunk_id+1}/{total}] {percent:.1f}%", end='')
            sock.close()
        except Exception as e:
            print(f" [Erreur Chunk {chunk_id}: {e}]")

# --- INTERFACE UTILISATEUR ---
if __name__ == "__main__":
    node = P2PNode()
    
    # Lancer le serveur en fond
    t = threading.Thread(target=node.start_server, daemon=True)
    t.start()
    time.sleep(0.5)

    print("\n=== P2P GLOBAL NODE ===")
    print(f"Mon IP : {node.my_ip}")
    print("Mettez vos fichiers dans le dossier 'shared_files'.")
    print("---------------------------------------------------")

    while True:
        print("\n1. Ajouter un ami (IP)")
        print("2. Voir mes amis")
        print("3. Rechercher et Télécharger un fichier")
        print("4. Quitter")
        choix = input("Votre choix : ")

        if choix == "1":
            ip = input("IP de l'ami : ")
            node.add_peer(ip)
        elif choix == "2":
            print(f"Amis connectés : {node.peers}")
        elif choix == "3":
            fname = input("Nom du fichier (ex: video.mp4) : ")
            # 1. Recherche réseau
            sources = node.broadcast_search(fname)
            
            if not sources:
                print("Aucun résultat trouvé sur le réseau.")
            else:
                print(f"\nSources trouvées : {sources}")
                # Pour simplifier, on prend le premier qui l'a.
                # Plus tard, on pourrait télécharger des bouts chez tout le monde !
                target = sources[0] 
                node.download_file(fname, target)
                
        elif choix == "4":
            break