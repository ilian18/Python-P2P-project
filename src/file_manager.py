import os

# Configuration
CHUNK_SIZE = 1024 * 1024  # 1 Mo
SHARED_FOLDER = "shared_files"
DOWNLOAD_PREFIX = "downloaded_"

class FileManager:
    """
    Gère les opérations de lecture et d'écriture sur le disque.
    Isole la logique fichier de la logique réseau.
    """
    def __init__(self):
        # Création automatique du dossier partagé s'il n'existe pas
        if not os.path.exists(SHARED_FOLDER):
            os.makedirs(SHARED_FOLDER)

    def get_file_path(self, filename):
        return os.path.join(SHARED_FOLDER, filename)

    def get_total_chunks(self, filename):
        """Calcule le nombre de morceaux (chunks) pour un fichier donné."""
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return 0
        file_size = os.path.getsize(filepath)
        return (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE > 0 else 0)

    def read_chunk(self, filename, chunk_index):
        """Lit un morceau spécifique du fichier."""
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as f:
            f.seek(chunk_index * CHUNK_SIZE)
            data = f.read(CHUNK_SIZE)
            return data

    def write_chunk(self, filename, chunk_index, data):
        """Écrit un morceau reçu dans le fichier de destination."""
        save_name = f"{DOWNLOAD_PREFIX}{filename}"
        filepath = self.get_file_path(save_name)
        
        # Si le fichier n'existe pas, on le crée
        if not os.path.exists(filepath):
            with open(filepath, 'wb') as f: 
                pass 
        
        # Écriture du chunk au bon endroit
        with open(filepath, 'r+b') as f:
            f.seek(chunk_index * CHUNK_SIZE)
            f.write(data)