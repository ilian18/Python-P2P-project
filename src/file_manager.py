import os

# Configuration constants
CHUNK_SIZE = 1024 * 1024  # 1 MB
SHARED_FOLDER = "shared_files"
DOWNLOAD_PREFIX = "downloaded_"

class FileManager:
    """Handles disk read and write operations.
    
    Isolates file system logic from the network logic to ensure modularity.
    """
    
    def __init__(self):
        """Initializes the FileManager and creates the shared directory if it does not exist."""
        if not os.path.exists(SHARED_FOLDER):
            os.makedirs(SHARED_FOLDER)

    def get_file_path(self, filename: str) -> str:
        """Retrieves the full path for a given filename within the shared folder.

        Args:
            filename (str): The name of the file.

        Returns:
            str: The absolute or relative path to the file.
        """
        return os.path.join(SHARED_FOLDER, filename)

    def get_total_chunks(self, filename: str) -> int:
        """Calculates the total number of chunks for a given file.

        Args:
            filename (str): The name of the file to evaluate.

        Returns:
            int: The total number of chunks. Returns 0 if the file does not exist.
        """
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return 0
        file_size = os.path.getsize(filepath)
        return (file_size // CHUNK_SIZE) + (1 if file_size % CHUNK_SIZE > 0 else 0)

    def read_chunk(self, filename: str, chunk_index: int) -> bytes | None:
        """Reads a specific chunk from a file on disk.

        Args:
            filename (str): The name of the file to read from.
            chunk_index (int): The index of the chunk to read.

        Returns:
            bytes | None: The binary data of the chunk, or None if the file does not exist.
        """
        filepath = self.get_file_path(filename)
        if not os.path.exists(filepath):
            return None
        with open(filepath, 'rb') as file:
            file.seek(chunk_index * CHUNK_SIZE)
            data = file.read(CHUNK_SIZE)
            return data

    def write_chunk(self, filename: str, chunk_index: int, data: bytes) -> None:
        """Writes a received chunk of data to the destination file.

        Args:
            filename (str): The original name of the file.
            chunk_index (int): The index where the chunk should be written.
            data (bytes): The binary data to write.
        """
        save_name = f"{DOWNLOAD_PREFIX}{filename}"
        filepath = self.get_file_path(save_name)
        
        # Create an empty file if it doesn't exist yet
        if not os.path.exists(filepath):
            with open(filepath, 'wb') as file: 
                pass 
        
        # Write the chunk at the correct byte offset
        with open(filepath, 'r+b') as file:
            file.seek(chunk_index * CHUNK_SIZE)
            file.write(data)