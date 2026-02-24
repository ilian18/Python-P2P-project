# 🌐 Decentralized P2P File Sharing System

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat&logo=python)
![Networking](https://img.shields.io/badge/Networking-TCP%2FSockets-green)
![Concurrency](https://img.shields.io/badge/Concurrency-Multi--Threading-orange)

A robust, decentralized file-sharing application built from scratch in Python. This project implements a **Gossip Protocol** for resource discovery and handles binary file transfer via **TCP Sockets**.

## 🚀 Key Features

* **Decentralized Architecture:** No central server; every node acts as both client and server.
* **Gossip Protocol (Flooding):** Efficient resource discovery with TTL (Time-To-Live) management to prevent network congestion.
* **Binary Chunking:** Large files are split into 1MB chunks for reliable transmission and memory optimization.
* **Multi-threading:** Non-blocking interface allowing simultaneous uploads, downloads, and user interaction.
* **Resilience:** Custom JSON-based protocol for peer communication (`SEARCH`, `FOUND`, `GET_CHUNK`).

## 🛠️ Installation & Usage

### Prerequisites
* Python 3.x
* No external dependencies required (uses standard library).

### 1. Clone the repository
```bash
git clone [https://github.com/ilian18/Python-P2P-project.git](https://github.com/ilian18/Python-P2P-project.git)
cd Python-P2P-project

### 2. Run the Node

```bash
python main.py

### 3. How to use

1. **Start multiple nodes** (on different terminals or machines).
2. **Connect peers** using option 1. Add Peer.
3. Place files to share in the shared_files/ directory.
4. **Search & Download** using option 3.

##📂 Project Structure

/src
    ├── node.py          # Network logic (Server/Client/Gossip)
    ├── file_manager.py  # Disk I/O & Chunking logic
    └── protocol.py      # JSON message definitions
main.py                  # Entry point & CLI Interface

## 🧠 Technical Highlights for Engineers

* **Socket Programming:** Direct manipulation of TCP sockets for low-level control over data streams.
* **Concurrency:** Implementation of threading.Thread with Daemon mode to handle background server listening.
* **Scalability:** Scalability: The gossip protocol is designed to scale with the number of nodes, using a known_messages set to avoid infinite loops.

---

Developed by Mohamed Ilian SBAI - 2026