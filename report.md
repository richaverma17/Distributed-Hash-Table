# **CHORD \- DISTRIBUTED HASH TABLE (DHT)**

# **ABSTRACT**

This project implements a fully functional Distributed Hash Table (DHT) based on the **Chord protocol**, a structured peer-to-peer overlay network that provides efficient key lookup, decentralized architecture, dynamic membership handling, and fault tolerance.  
Using **gRPC**, each node runs independently, communicates with other nodes through RPCs, maintains routing state using a **finger table**, and ensures ring consistency through a **stabilization protocol**.

# **INTRODUCTION**

Distributed Hash Tables (DHTs) are fundamental to modern distributed systems — they provide scalable, decentralized lookup services where nodes can join or leave at any time.  
Chord is one of the most influential DHT algorithms, offering:

- A simple, elegant ring-based structure  
- Consistent hashing for balanced data distribution  
- O(log N) lookup routing using finger tables  
- Self-healing via stabilization  
- Decentralized operation (no single point of failure)

This project implements Chord from scratch using Python and gRPC. It extends the base algorithm with **fail-stop fault tolerance**, making the system robust even when nodes crash unexpectedly.

# **OBJECTIVE**

The primary objectives of this project are:

- To implement a fully decentralized Distributed Hash Table (DHT) using the Chord protocol.  
- To enable scalable and efficient key lookup with **O(log N)** routing using finger tables.  
- To support dynamic node joins and leaves without centralized control.  
- To ensure fault tolerance against **fail-stop node failures** using stabilization and heartbeat mechanisms.  
- To build a distributed key-value store supporting **PUT/GET/DELETE** operations.  
- To use **gRPC and Protocol Buffers** for reliable inter-node communication.  
- To provide a simple CLI and REPL interface for interacting with the DHT.

# **MOTIVATION**

This project was undertaken with the goal of exploring and implementing the core concepts behind scalable distributed infrastructure. The specific motivations were:

- **To understand decentralized peer-to-peer architectures** and how nodes cooperate without centralized coordination.  
- **To gain hands-on experience with consistent hashing**, which is widely used in modern systems (e.g., DynamoDB, Cassandra, Ceph, Kubernetes).  
- **To implement real distributed routing**, where lookups traverse multiple nodes using finger tables to achieve O(log N) efficiency.  
- **To study fault tolerance mechanisms** in dynamic and unreliable networks, especially fail-stop behavior.  
- **To build a production-style distributed system using gRPC**, allowing real RPC-based internode communication across processes or machines.

By implementing Chord from the ground up—including routing logic, stabilization, key-value storage, and fault handling—this project provides a practical and comprehensive understanding of how modern scalable distributed systems are designed.

# **ARCHITECTURE OVERVIEW**

- ### Chord Node

  * ### Each node is a fully independent instance running the complete Chord protocol.      A node is responsible for:

    * ### Maintaining its unique identifier (ID)

    * ### Managing routing state (successor, predecessor, finger table)

    * ### Serving lookup and key-value requests

    * ### Communicating with other nodes

  * ### Nodes operate without a central coordinator.

- ### Consistent Hashing Layer

  * Each node and each key is assigned a position in a **circular identifier space** using a hash function (SHA-1, 160-bit).  
  * This layer ensures:  
    * Even distribution of keys  
    * Minimal key movement when nodes join/leave  
    * Deterministic placement of data  
  * This is the mathematical foundation of Chord’s scalability.

- ### Finger Table

  * The finger table is the core data structure enabling **O(log N)** routing.  
  * For a node with identifier n, the i-th finger represents:  
    * start \= (n \+ 2^i) mod 2^m  
    * successor \= node responsible for 'start'  
  * Features:  
    * Exponentially distributed entries  
    * Allows long-distance jumps across ring  
    * Ensures fast convergence to target node during lookups

- ### Successor and Predecessor Pointers

  * Every node stores:  
    * **successor** → next node clockwise  
    * **predecessor** → previous node counterclockwise  
  * These pointers ensure ring integrity.  
  * Even if finger tables temporarily fail, successor pointers maintain correctness.

- ### RPC Communication Layer (gRPC \+ Protobuf)

  * Nodes communicate using a well-defined gRPC interface with methods such as:  
    * FindSuccessor  
    * GetPredecessor   
    * Notify   
    * Ping   
    * Get/Put/Delete  
  * This enables:  
    * Process-to-process communication  
    * Cross-machine deployment  
    * Serialization and structure via Protocol Buffers  
    * Easy debugging and interoperability  
  * This layer abstracts networking complexities from the Chord logic.

- ### Stabilization Layer

  * A dedicated background thread periodically runs maintenance logic:  
    * stabilize() → Repairs successor pointer  
    * notify() → Helps maintain predecessor pointer  
    * fix\_fingers() → Updates routing entries incrementally  
    * check\_predecessor() → Detects failed neighbors  
  * This ensures the Chord ring is self-healing and remains correct even under:  
    * Node joins  
    * Node departures  
    * Node failures  
  * The stabilization processes are decentralized — each node independently repairs its view of the network.

- ### Storage Layer

  * Each node maintains an in-memory dictionary for storing the keys for which it is responsible.  
  * Key responsibilities:  
    * Store local subset of the global keyspace  
    * Support put(), get(), and delete() operations  
    * Maintain data consistency after joins/leaves  
  * The **responsible node** is always the **successor of the key’s hash value**.

- ### Client Interface

  * The user interacts with the DHT via a command-line REPL client.  
  * Supported operations:  
    * put \<key\> \<value\>  
    * get \<key\>  
    * delete \<key\>  
    * ping  
  * The client connects to **any node**, and Chord routing ensures the request reaches the correct node.

- ### Node Launcher

  * This CLI tool manages:  
    * Starting a new Chord node  
    * Creating a new ring  
    * Joining an existing ring  
  * It runs the server and stabilization thread, making the node ready for distributed operation.

Overall, the architecture reflects a clean separation of concerns:

- **Chord protocol layer** handles routing and stabilization  
- **gRPC layer** manages distributed communication  
- **Storage layer** provides the key-value abstraction  
- **Finger table layer** provides efficient routing  
- **CLI and REPL clients** provide user interaction

# **LIMITATION**

- Not Byzantine fault tolerant ented (only primary copy)  
- Storage is in-memory (not persistent)  
- Requires stable network environment

# **CONCLUSION**

This project successfully demonstrates a working implementation of the Chord distributed hash table, showcasing how a decentralized, scalable, and fault-tolerant storage system can be constructed from simple mathematical principles. By integrating consistent hashing, finger-table routing, and stabilization mechanisms, the system efficiently supports O(log N) lookups and remains operational despite node failures.  
Overall, the implementation validates the robustness and elegance of the Chord algorithm. The project provides a strong foundation for understanding fully decentralized systems and their behavior under dynamic conditions.

# **FUTURE IMPLEMENTATION**

- ###  **Data Replication**

  * Currently, only a single node stores each key.  
  * Replicating keys across successor nodes would improve fault tolerance.

- ### **Persistent Storage**

  * Moving from in-memory dictionaries to disk-based storage or databases.  
  * Prevents data loss when nodes restart.  
- **Distributed Garbage Collection**  
  * Automatic cleanup of stale keys after failures or node departures.  
- **Security Features**  
  * Preventing malicious joins (Byzantine behavior).  
  * Authenticating node identity.

- ### **Visualization Tools**

  * Real-time graphical display of the ring structure and finger tables.  
- **Performance Optimization**  
  * Parallelization of stabilization tasks.  
  * Caching of lookup results for frequently accessed keys.

