import threading
import time
from src.node import P2PNode

def main() -> None:
    """Main entry point for the P2P application.
    
    Initializes the node, starts the background server, and runs the CLI loop.
    """
    # Node instantiation
    p2p_node = P2PNode()
    
    # Launching the server in the background (Daemon thread)
    # Daemon ensures the server thread stops when the main program exits
    server_thread = threading.Thread(target=p2p_node.start_server, daemon=True)
    server_thread.start()
    
    # Brief pause to allow the server socket to bind properly
    time.sleep(0.5)

    print("\n=== P2P DISTRIBUTED SYSTEM ===")
    print(f"My IP: {p2p_node.local_ip}")
    print("Files to share: Place them in the 'shared_files' directory")
    print("---------------------------------------------------")

    while True:
        print("\n1. Add a Peer (IP)")
        print("2. View Peer List")
        print("3. Search & Download")
        print("4. Exit")
        
        try:
            user_choice = input("Your choice > ")
        except KeyboardInterrupt:
            break

        if user_choice == "1":
            target_ip = input("Enter the peer's IP address: ")
            p2p_node.add_peer(target_ip)
        
        elif user_choice == "2":
            print(f"Connected peers: {p2p_node.peers}")
        
        elif user_choice == "3":
            filename = input("Filename (e.g., video.mp4): ")
            available_sources = p2p_node.broadcast_search(filename)
            
            if not available_sources:
                print("No results found on the network.")
            else:
                print(f"Found at: {available_sources}")
                # For now, default to downloading from the first available source
                target_node = available_sources[0]
                p2p_node.download_file(filename, target_node)
                
        elif user_choice == "4":
            print("Shutting down the node...")
            break

if __name__ == "__main__":
    main()