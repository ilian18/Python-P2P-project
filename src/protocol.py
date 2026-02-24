import uuid

class P2PProtocol:
    """
    Définit les règles de communication (le 'Langage') du réseau P2P.
    Centralise la création des paquets JSON pour éviter les erreurs de frappe.
    """
    # Constantes des commandes
    SEARCH = "SEARCH"
    FOUND = "FOUND"
    GET_METADATA = "GET_METADATA"
    GET_CHUNK = "GET_CHUNK"

    @staticmethod
    def create_search(filename, origin_ip, ttl=3):
        return {
            "command": P2PProtocol.SEARCH,
            "id": str(uuid.uuid4()),
            "filename": filename,
            "origin_ip": origin_ip,
            "ttl": ttl
        }

    @staticmethod
    def create_found(filename, peer_ip):
        return {
            "command": P2PProtocol.FOUND,
            "filename": filename,
            "peer_ip": peer_ip
        }
    
    @staticmethod
    def request_metadata(filename):
        return {"command": P2PProtocol.GET_METADATA, "filename": filename}

    @staticmethod
    def request_chunk(filename, chunk_id):
        return {
            "command": P2PProtocol.GET_CHUNK, 
            "filename": filename, 
            "chunk_id": chunk_id
        }