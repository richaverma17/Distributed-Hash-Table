Chord - DHT

```
Distributed-Hash-Table/
├── proto/
│   └── chord.proto
├── src/
│   ├── __init__.py
│   ├── chord_node.py        # Main Node class
│   ├── chord_server.py      # gRPC server implementation
│   ├── chord_client.py      # gRPC client wrapper
│   ├── storage.py           # Key-value storage
│   ├── finger_table.py      # Chord finger table
│   └── utils.py             # Hashing utilities
├── node.py                  # Entry point for running a node
├── requirements.txt
└── README.md
```

1. Protocol Buffer Definition (proto/chord.proto)
```
syntax = "proto3";

package chord;

// Chord DHT Service
service ChordService {
    // Key-value operations
    rpc Put(PutRequest) returns (PutResponse);
    rpc Get(GetRequest) returns (GetResponse);
    rpc Delete(DeleteRequest) returns (DeleteResponse);
    
    // Chord protocol operations
    rpc FindSuccessor(FindSuccessorRequest) returns (FindSuccessorResponse);
    rpc FindPredecessor(FindPredecessorRequest) returns (FindPredecessorResponse);
    rpc GetSuccessor(GetSuccessorRequest) returns (GetSuccessorResponse);
    rpc GetPredecessor(GetPredecessorRequest) returns (GetPredecessorResponse);
    rpc Notify(NotifyRequest) returns (NotifyResponse);
    rpc ClosestPrecedingFinger(ClosestPrecedingFingerRequest) returns (ClosestPrecedingFingerResponse);
    
    // Node management
    rpc Ping(PingRequest) returns (PingResponse);
    rpc TransferKeys(TransferKeysRequest) returns (TransferKeysResponse);
}

message NodeInfo {
    string id = 1;       // Hash ID as string
    string address = 2;  // IP:Port
}

message PutRequest {
    string key = 1;
    string value = 2;
}

message PutResponse {
    bool success = 1;
    string message = 2;
}

message GetRequest {
    string key = 1;
}

message GetResponse {
    bool found = 1;
    string value = 2;
}

message DeleteRequest {
    string key = 1;
}

message DeleteResponse {
    bool success = 1;
}

message FindSuccessorRequest {
    string id = 1;
}

message FindSuccessorResponse {
    NodeInfo node = 1;
}

message FindPredecessorRequest {
    string id = 1;
}

message FindPredecessorResponse {
    NodeInfo node = 1;
}

message GetSuccessorRequest {}

message GetSuccessorResponse {
    NodeInfo node = 1;
}

message GetPredecessorRequest {}

message GetPredecessorResponse {
    NodeInfo node = 1;
    bool has_predecessor = 2;
}

message NotifyRequest {
    NodeInfo node = 1;
}

message NotifyResponse {
    bool success = 1;
}

message ClosestPrecedingFingerRequest {
    string id = 1;
}

message ClosestPrecedingFingerResponse {
    NodeInfo node = 1;
}

message PingRequest {}

message PingResponse {
    bool alive = 1;
}

message KeyValue {
    string key = 1;
    string value = 2;
}

message TransferKeysRequest {
    repeated KeyValue keys = 1;
}

message TransferKeysResponse {
    bool success = 1;
}
```

2. Requirements (requirements.txt)
```
grpcio==1.60.0
grpcio-tools==1.60.0
protobuf==4.25.1
```

3. Utilities (src/utils.py)
```
import hashlib

# Chord ring size (m-bit identifier space)
M = 160  # Using SHA-1 for 160-bit identifiers
RING_SIZE = 2 ** M


def hash_key(key: str) -> int:
    """Hash a key to an integer in the Chord identifier space."""
    sha1 = hashlib.sha1(key.encode('utf-8'))
    return int(sha1.hexdigest(), 16) % RING_SIZE


def in_range(value: int, start: int, end: int, inclusive_start: bool = False, 
             inclusive_end: bool = False) -> bool:
    """
    Check if value is in range (start, end) on the Chord ring.
    Handles wraparound.
    """
    if start == end:
        return inclusive_start or inclusive_end
    
    if start < end:
        if inclusive_start and inclusive_end:
            return start <= value <= end
        elif inclusive_start:
            return start <= value < end
        elif inclusive_end:
            return start < value <= end
        else:
            return start < value < end
    else:  # Wraparound case
        if inclusive_start and inclusive_end:
            return value >= start or value <= end
        elif inclusive_start:
            return value >= start or value < end
        elif inclusive_end:
            return value > start or value <= end
        else:
            return value > start or value < end


def distance(start: int, end: int) -> int:
    """Calculate distance from start to end on the Chord ring."""
    if end >= start:
        return end - start
    else:
        return RING_SIZE - start + end
```

4. Storage (src/storage.py)
```
from typing import Dict, List, Tuple
import threading


class Storage:
    """Thread-safe key-value storage for a Chord node."""
    
    def __init__(self):
        self.data: Dict[str, str] = {}
        self.lock = threading.RLock()
    
    def put(self, key: str, value: str) -> bool:
        """Store a key-value pair."""
        with self.lock:
            self.data[key] = value
            return True
    
    def get(self, key: str) -> tuple[bool, str]:
        """Retrieve a value by key."""
        with self.lock:
            if key in self.data:
                return True, self.data[key]
            return False, ""
    
    def delete(self, key: str) -> bool:
        """Delete a key-value pair."""
        with self.lock:
            if key in self.data:
                del self.data[key]
                return True
            return False
    
    def get_keys_in_range(self, start_id: int, end_id: int) -> List[Tuple[str, str]]:
        """Get all keys whose hash falls in range (start_id, end_id]."""
        from .utils import hash_key, in_range
        
        with self.lock:
            result = []
            for key, value in self.data.items():
                key_hash = hash_key(key)
                if in_range(key_hash, start_id, end_id, 
                           inclusive_start=False, inclusive_end=True):
                    result.append((key, value))
            return result
    
    def remove_keys(self, keys: List[str]) -> None:
        """Remove multiple keys from storage."""
        with self.lock:
            for key in keys:
                self.data.pop(key, None)
    
    def add_keys(self, keys: List[Tuple[str, str]]) -> None:
        """Add multiple key-value pairs."""
        with self.lock:
            for key, value in keys:
                self.data[key] = value
    
    def get_all_keys(self) -> List[Tuple[str, str]]:
        """Get all key-value pairs."""
        with self.lock:
            return list(self.data.items())
    
    def size(self) -> int:
        """Return number of stored keys."""
        with self.lock:
            return len(self.data)
```

5. Finger Table (src/finger_table.py)
```
from typing import Optional, List
from dataclasses import dataclass
import threading


@dataclass
class NodeInfo:
    """Information about a node in the Chord ring."""
    id: int
    address: str
    
    def __eq__(self, other):
        if isinstance(other, NodeInfo):
            return self.id == other.id
        return False
    
    def __hash__(self):
        return hash(self.id)


class FingerTable:
    """Finger table for Chord protocol."""
    
    def __init__(self, node_id: int, m: int = 160):
        self.node_id = node_id
        self.m = m  # Number of bits in identifier space
        self.ring_size = 2 ** m
        self.fingers: List[Optional[NodeInfo]] = [None] * m
        self.lock = threading.RLock()
    
    def start(self, i: int) -> int:
        """Calculate the start of the i-th finger interval."""
        return (self.node_id + 2 ** i) % self.ring_size
    
    def update_finger(self, i: int, node: NodeInfo) -> None:
        """Update the i-th finger entry."""
        with self.lock:
            if 0 <= i < self.m:
                self.fingers[i] = node
    
    def get_finger(self, i: int) -> Optional[NodeInfo]:
        """Get the i-th finger entry."""
        with self.lock:
            if 0 <= i < self.m:
                return self.fingers[i]
            return None
    
    def closest_preceding_node(self, id: int) -> Optional[NodeInfo]:
        """Find the closest finger preceding id."""
        from .utils import in_range
        
        with self.lock:
            for i in range(self.m - 1, -1, -1):
                if self.fingers[i] is not None:
                    finger_id = self.fingers[i].id
                    if in_range(finger_id, self.node_id, id, 
                              inclusive_start=False, inclusive_end=False):
                        return self.fingers[i]
            return None
    
    def get_all_fingers(self) -> List[Optional[NodeInfo]]:
        """Get all finger entries."""
        with self.lock:
            return self.fingers.copy()
```

6. gRPC Client (src/chord_client.py)
```
import grpc
from typing import Optional, List, Tuple
import sys
import os

# Add proto directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'proto'))

import chord_pb2
import chord_pb2_grpc
from .finger_table import NodeInfo


class ChordClient:
    """Client for making gRPC calls to other Chord nodes."""
    
    @staticmethod
    def create_channel(address: str, timeout: int = 5):
        """Create a gRPC channel with timeout."""
        return grpc.insecure_channel(
            address,
            options=[
                ('grpc.max_send_message_length', 50 * 1024 * 1024),
                ('grpc.max_receive_message_length', 50 * 1024 * 1024),
            ]
        )
    
    @staticmethod
    def find_successor(address: str, id: int) -> Optional[NodeInfo]:
        """Find the successor of given id."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.FindSuccessorRequest(id=str(id))
                response = stub.FindSuccessor(request, timeout=5.0)
                if response.node:
                    return NodeInfo(int(response.node.id), response.node.address)
        except Exception as e:
            print(f"Error finding successor from {address}: {e}")
        return None
    
    @staticmethod
    def get_predecessor(address: str) -> Optional[NodeInfo]:
        """Get the predecessor of a node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.GetPredecessorRequest()
                response = stub.GetPredecessor(request, timeout=5.0)
                if response.has_predecessor and response.node:
                    return NodeInfo(int(response.node.id), response.node.address)
        except Exception as e:
            print(f"Error getting predecessor from {address}: {e}")
        return None
    
    @staticmethod
    def notify(address: str, node: NodeInfo) -> bool:
        """Notify a node about another node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                node_info = chord_pb2.NodeInfo(id=str(node.id), address=node.address)
                request = chord_pb2.NotifyRequest(node=node_info)
                response = stub.Notify(request, timeout=5.0)
                return response.success
        except Exception as e:
            print(f"Error notifying {address}: {e}")
        return False
    
    @staticmethod
    def closest_preceding_finger(address: str, id: int) -> Optional[NodeInfo]:
        """Get closest preceding finger from a node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.ClosestPrecedingFingerRequest(id=str(id))
                response = stub.ClosestPrecedingFinger(request, timeout=5.0)
                if response.node:
                    return NodeInfo(int(response.node.id), response.node.address)
        except Exception as e:
            print(f"Error getting closest preceding finger from {address}: {e}")
        return None
    
    @staticmethod
    def ping(address: str) -> bool:
        """Ping a node to check if it's alive."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.PingRequest()
                response = stub.Ping(request, timeout=2.0)
                return response.alive
        except:
            return False
    
    @staticmethod
    def put(address: str, key: str, value: str) -> bool:
        """Store a key-value pair on a node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.PutRequest(key=key, value=value)
                response = stub.Put(request, timeout=5.0)
                return response.success
        except Exception as e:
            print(f"Error putting key to {address}: {e}")
        return False
    
    @staticmethod
    def get(address: str, key: str) -> Tuple[bool, str]:
        """Get a value by key from a node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.GetRequest(key=key)
                response = stub.Get(request, timeout=5.0)
                return response.found, response.value
        except Exception as e:
            print(f"Error getting key from {address}: {e}")
        return False, ""
    
    @staticmethod
    def delete(address: str, key: str) -> bool:
        """Delete a key from a node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                request = chord_pb2.DeleteRequest(key=key)
                response = stub.Delete(request, timeout=5.0)
                return response.success
        except Exception as e:
            print(f"Error deleting key from {address}: {e}")
        return False
    
    @staticmethod
    def transfer_keys(address: str, keys: List[Tuple[str, str]]) -> bool:
        """Transfer keys to another node."""
        try:
            with ChordClient.create_channel(address) as channel:
                stub = chord_pb2_grpc.ChordServiceStub(channel)
                key_values = [chord_pb2.KeyValue(key=k, value=v) for k, v in keys]
                request = chord_pb2.TransferKeysRequest(keys=key_values)
                response = stub.TransferKeys(request, timeout=10.0)
                return response.success
        except Exception as e:
            print(f"Error transferring keys to {address}: {e}")
        return False
```