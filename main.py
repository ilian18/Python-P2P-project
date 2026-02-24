import threading
import time
from src.node import P2PNode

def main():
    # Instanciation du noeud
    node = P2PNode()
    
    # Lancement du serveur en arrière-plan (Daemon thread)
    # Le daemon permet au serveur de s'arrêter quand on quitte le programme
    server_thread = threading.Thread(target=node.start_server, daemon=True)
    server_thread.start()
    
    # Petite pause pour laisser le serveur démarrer
    time.sleep(0.5)

    print("\n=== P2P DISTRIBUTED SYSTEM ===")
    print(f"Mon IP : {node.my_ip}")
    print("Fichiers à partager : Placez-les dans 'shared_files'")
    print("---------------------------------------------------")

    while True:
        print("\n1. Ajouter un Pair (IP)")
        print("2. Voir la liste des Pairs")
        print("3. Rechercher & Télécharger")
        print("4. Quitter")
        
        try:
            choix = input("Votre choix > ")
        except KeyboardInterrupt:
            break

        if choix == "1":
            ip = input("Entrez l'IP du pair : ")
            node.add_peer(ip)
        
        elif choix == "2":
            print(f"Pairs connectés : {node.peers}")
        
        elif choix == "3":
            fname = input("Nom du fichier (ex: video.mp4) : ")
            sources = node.broadcast_search(fname)
            
            if not sources:
                print("Aucun résultat sur le réseau.")
            else:
                print(f"Trouvé chez : {sources}")
                # Pour l'instant, on télécharge depuis le premier trouvé
                target = sources[0]
                node.download_file(fname, target)
                
        elif choix == "4":
            print("Arrêt du noeud...")
            break

if __name__ == "__main__":
    main()