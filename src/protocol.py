import uuid

class P2PProtocol:
    """Defines the communication rules and message structures for the P2P network.
    
    Centralizes the creation of JSON packets to ensure consistency and prevent typos 
    across the network communication layer.
    """
    
    # Command constants
    SEARCH = "SEARCH"
    FOUND = "FOUND"
    GET_METADATA = "GET_METADATA"
    GET_CHUNK = "GET_CHUNK"

    @staticmethod
    def create_search(filename: str, origin_ip: str, ttl: int = 3) -> dict:
        """Creates a search request packet.

        Args:
            filename (str): The name of the file being searched for.
            origin_ip (str): The IP address of the node initiating the search.
            ttl (int, optional): Time-to-live for the broadcast message. Defaults to 3.

        Returns:
            dict: The formatted search packet.
        """
        return {
            "command": P2PProtocol.SEARCH,
            "id": str(uuid.uuid4()),
            "filename": filename,
            "origin_ip": origin_ip,
            "ttl": ttl
        }

    @staticmethod
    def create_found(filename: str, peer_ip: str) -> dict:
        """Creates a packet indicating a file was found.

        Args:
            filename (str): The name of the found file.
            peer_ip (str): The IP address of the peer hosting the file.

        Returns:
            dict: The formatted found packet.
        """
        return {
            "command": P2PProtocol.FOUND,
            "filename": filename,
            "peer_ip": peer_ip
        }
    
    @staticmethod
    def request_metadata(filename: str) -> dict:
        """Creates a packet to request file metadata (e.g., total chunks).

        Args:
            filename (str): The name of the file.

        Returns:
            dict: The formatted metadata request packet.
        """
        return {"command": P2PProtocol.GET_METADATA, "filename": filename}

    @staticmethod
    def request_chunk(filename: str, chunk_id: int) -> dict:
        """Creates a packet to request a specific file chunk.

        Args:
            filename (str): The name of the file.
            chunk_id (int): The index of the requested chunk.

        Returns:
            dict: The formatted chunk request packet.
        """
        return {
            "command": P2PProtocol.GET_CHUNK, 
            "filename": filename, 
            "chunk_id": chunk_id
        }