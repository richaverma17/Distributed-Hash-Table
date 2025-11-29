# Chord Distributed Hash Table (DHT) with Replication

A Python implementation of the Chord distributed hash table protocol with built-in replication for fault tolerance and a real-time web visualization interface.

## 🎯 What is Chord DHT?

Chord is a distributed hash table protocol that provides efficient key lookup in a peer-to-peer network. It uses consistent hashing to distribute keys across nodes in a circular identifier space (ring). Each node is responsible for a portion of the key space and maintains routing information (finger table) to efficiently locate keys in O(log N) hops.

## ✨ Features

- **Chord Protocol Implementation**: Full implementation of the Chord DHT protocol
  - Efficient key lookup using finger tables (O(log N) complexity)
  - Automatic node joining and stabilization
  - Consistent hashing for key distribution
  
- **Fault Tolerance with Replication**:
  - Configurable replication factor (default: 3x replication)
  - Keys are replicated across multiple successor nodes
  - Automatic replica synchronization during PUT/DELETE operations
  - Quorum-based writes for consistency
  
- **Real-time Web Visualization**:
  - Interactive web UI showing the Chord ring
  - Live node status and key distribution
  - Visual distinction between primary keys and replicas
  - Real-time activity logs
  - WebSocket-based updates
  
- **Key-Value Operations**:
  - PUT: Store key-value pairs with replication
  - GET: Retrieve values with replica fallback
  - DELETE: Consistent deletion across all replicas
  
- **Persistent Storage**:
  - JSON-based persistence for each node
  - Automatic recovery on node restart

## 🏗️ Architecture

### Project Structure

```
Distributed-Hash-Table/
├── proto/
│   ├── chord.proto          # gRPC service definitions
│   ├── chord_pb2.py         # Generated protocol buffers
│   └── chord_pb2_grpc.py    # Generated gRPC stubs
├── src/
│   ├── __init__.py
│   ├── node.py              # Core Chord node implementation
│   ├── storage.py           # Persistent key-value storage
│   ├── finger_table.py      # Chord finger table
│   └── utils.py             # Hashing and utility functions
├── data/                    # Storage directory (created automatically)
├── server.py                # FastAPI web server & visualizer
├── client.py                # CLI client for testing
├── run.py                   # Node runner script
├── requirements.txt
└── README.md
```

### Key Components

1. **Node (`src/node.py`)**: 
   - Implements Chord protocol operations (find_successor, stabilize, fix_fingers, etc.)
   - Handles replication across successor nodes
   - Manages finger table for efficient routing
   - Performs periodic stabilization and failure detection

2. **Storage (`src/storage.py`)**: 
   - Persistent JSON-based storage per node
   - Thread-safe operations
   - Automatic disk persistence

3. **Finger Table (`src/finger_table.py`)**: 
   - Maintains routing information for O(log N) lookups
   - Periodically refreshed during stabilization

4. **Web Server (`server.py`)**: 
   - FastAPI-based visualization interface
   - Manages multiple nodes in a single process
   - Real-time updates via WebSocket
   - Provides REST API for node/key operations

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

## 🚀 Setup Instructions

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd Distributed-Hash-Table
```

### 2. Create Virtual Environment (Recommended)

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

The project requires:
- `grpcio` and `grpcio-tools` - For gRPC communication between nodes
- `protobuf` - Protocol buffer support
- `fastapi` and `uvicorn` - Web server and API framework
- `websockets` - Real-time updates
- `pyyaml` and `python-dotenv` - Configuration management

### 4. Generate Protocol Buffers (If Modified)

If you modify `proto/chord.proto`, regenerate the Python files:

```bash
python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. proto/chord.proto
```

### 5. Create Data Directory

The data directory is created automatically, but you can create it manually if needed:

```bash
mkdir -p data
```

## 🎮 Usage

### Option 1: Web Visualizer (Recommended)

Start the web server with visualization interface:

```bash
python server.py
```

Then open your browser to: **http://localhost:8000**

#### Using the Web Interface:

1. **Add Nodes**: 
   - Click **"➕ Add Node"** to create the first node (forms a new ring)
   - Click **"➕ Add & Join"** to add more nodes to the existing ring
   - Recommended: Start with 4-5 nodes to see replication in action

2. **Store Data**:
   - Enter a key (e.g., "user123") and value (e.g., "John Doe")
   - Select any node to contact
   - Click **"PUT"** to store (will be replicated 3x automatically)
   - Watch the activity log to see which nodes store the replicas

3. **Retrieve Data**:
   - Enter a key
   - Select any node (doesn't have to be the one you used for PUT)
   - Click **"GET"** (will find the key even if a node fails)

4. **Delete Data**:
   - Enter a key
   - Click **"DELETE"** (removes from all replicas to maintain consistency)

5. **Visualize**:
   - See the Chord ring with all nodes positioned by their hash IDs
   - Green dashed lines show replication relationships
   - Keys shown with 🔑 (primary) or 📋 (replica) icons
   - Green badge shows number of keys per node

#### Understanding the UI:

- **Stats Cards**: Show active nodes, ring size, unique keys, total replicas, and replication factor
- **Chord Ring**: Visual representation of nodes on the identifier space
- **Active Nodes Panel**: Lists all nodes with their keys, successors, and predecessors
- **Activity Log**: Real-time log of all operations

### Option 2: Command Line (Advanced)

Run individual nodes in separate terminals:

```bash
# Terminal 1: Start first node
python run.py --port 50051

# Terminal 2: Join second node
python run.py --port 50052 --join localhost:50051

# Terminal 3: Join third node
python run.py --port 50053 --join localhost:50051
```

Use the CLI client:

```bash
# Store a key
python client.py --node localhost:50051 put mykey myvalue

# Retrieve a key
python client.py --node localhost:50052 get mykey

# Delete a key
python client.py --node localhost:50053 delete mykey
```

## 🔧 Configuration

### Replication Factor

To change the replication factor, modify `src/node.py` line 18:

```python
def __init__(self, address: str, replication_factor: int = 3):
    # ...
    self.replication_factor = replication_factor  # Change this value (1-N)
```

Higher replication factor = more fault tolerance but more storage overhead.

### Ring Size

The identifier space is defined in `src/utils.py`:

```python
RING_BITS = 14  # 2^14 = 16,384 possible positions
RING_SIZE = 2 ** RING_BITS
```

Larger ring = more positions for nodes, but visualization becomes harder.

### Stabilization Interval

Adjust how frequently nodes run stabilization (in `src/node.py`):

```python
def start_stabilization(self, interval: float = 1.0):  # seconds
```

Lower interval = faster convergence but more network traffic.

### Storage Path

Data files are stored in the `data/` directory by default. Change in `src/node.py`:

```python
persist_path = "data"  # Change to your preferred path
```

## 🧪 Testing Fault Tolerance

### Basic Replication Test:

1. **Start 5 nodes** using the web interface (click "Add & Join" 4 times)
2. **Store a key** (e.g., key="test", value="hello")
3. **Observe** in the UI that 3 nodes have this key (look for 🔑 and 📋 icons)
4. **Remove the primary node** (the one with 🔑)
5. **Try to GET the key** from another node - should still work!

### Consistency Test:

1. **Start 4 nodes**
2. **Store multiple keys** (e.g., key1, key2, key3)
3. **Delete one key** from any node
4. **Verify** the key is gone from ALL replicas (check all nodes in the UI)

### Load Distribution Test:

1. **Start 6 nodes**
2. **Add 20 different keys** with various names
3. **Observe** how keys are distributed across nodes
4. **Note** that each key appears on exactly 3 nodes (replication_factor)

## 📊 How Replication Works

### PUT Operation (Write):
1. Hash the key to find its position in the ring
2. Find the successor node (responsible node)
3. Store on **primary node** (key's successor)
4. Store on **next 2 successors** (replication_factor - 1)
5. Return success if stored on **quorum** (≥ 2 nodes for RF=3)

### GET Operation (Read):
1. Find responsible nodes for the key
2. Try to retrieve from **primary** first
3. If primary fails, try **replicas** in order
4. Return value from first successful read

### DELETE Operation:
1. Find all nodes storing the key
2. Delete from **ALL replicas synchronously**
3. Ensures no stale data remains
4. Return success if key was found and deleted

## 🎯 Performance Characteristics

- **Lookup Time**: O(log N) hops where N = number of nodes
- **Storage Overhead**: Each key stored R times (R = replication_factor)
- **Write Consistency**: Quorum-based (majority of replicas must succeed)
- **Read Availability**: High (can read from any replica)
- **Fault Tolerance**: Can survive R-1 node failures per key
- **Network Overhead**: O(R) messages per write operation

## 🐛 Troubleshooting

### "Failed to store key" Error
**Possible causes:**
- Not enough nodes in the ring (need at least `replication_factor` nodes)
- Nodes haven't stabilized yet (wait 2-3 seconds after adding nodes)
- Data directory permission issues

**Solutions:**
- Ensure at least 3 nodes are running
- Wait a few seconds between operations
- Check terminal logs for specific errors
- Verify `data/` directory exists and is writable

### Keys Not Showing in UI
**Possible causes:**
- WebSocket connection issues
- Browser cache problems
- Stabilization in progress

**Solutions:**
- Check browser console for errors (F12)
- Refresh the page (Ctrl+R or Cmd+R)
- Wait 2-3 seconds after adding nodes
- Check if WebSocket shows "Connected to server" in activity log

### "Connection refused" Errors
**Possible causes:**
- Node not started or crashed
- Port already in use
- Firewall blocking connections

**Solutions:**
- Verify nodes are running: check terminal output
- Try different ports
- Check firewall settings
- Ensure no other process is using ports 50051+

### Nodes Disappear or Crash
**Possible causes:**
- Rapid succession of operations
- Insufficient stabilization time
- Bug in finger table updates

**Solutions:**
- Wait 1-2 seconds between adding nodes
- Don't remove all nodes at once
- Check logs for exceptions
- Restart the server: `python server.py`

### Storage Files Corrupted
**Solutions:**
```bash
# Stop all nodes
# Remove data directory
rm -rf data/
mkdir data

# Restart server
python server.py
```

## 📚 Chord Protocol Resources

- [Original Chord Paper](https://pdos.csail.mit.edu/papers/chord:sigcomm01/chord_sigcomm.pdf) - Stoica et al., 2001
- [Chord Protocol Overview](https://en.wikipedia.org/wiki/Chord_(peer-to-peer))
- [Consistent Hashing](https://www.toptal.com/big-data/consistent-hashing)

## 🔬 Technical Details

### Hash Function
Uses SHA-1 hash truncated to fit the ring size (default: 14 bits = 16,384 positions)

### Finger Table
Each node maintains m entries where entry i points to the first node ≥ (n + 2^i) mod 2^m

### Stabilization Protocol
Runs every 1 second to:
1. Verify and update successor
2. Notify potential predecessors  
3. Fix one finger table entry (round-robin)
4. Check if predecessor is alive

### Replication Strategy
Chain replication: primary stores first, then forwards to R-1 successors in sequence.

## 🤝 Contributing

Contributions are welcome! Areas for improvement:
- Implement successor list for better fault tolerance
- Add authentication and encryption
- Improve network partition handling
- Add load balancing
- Implement virtual nodes for better distribution
- Add metrics and monitoring

## 📝 License

[Specify your license here - MIT, Apache 2.0, etc.]

## 👥 Authors

[Your name/team]

## 🙏 Acknowledgments

Based on the Chord protocol by Stoica, Morris, Karger, Kaashoek, and Balakrishnan (MIT, 2001).

---

**⚠️ Note**: This is an educational implementation. For production use, consider additional features like authentication, encryption, more sophisticated failure detection, network partition handling, and proper security measures.
