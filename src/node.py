import grpc
from concurrent import futures
import logging
from typing import Optional

# Module imports
from proto import chord_pb2, chord_pb2_grpc
from .utils import hash_key, NodeInfo
from .finger_table import FingerTable, FingerEntry


class Node(chord_pb2_grpc.ChordServiceServicer):
    """
    Chord Node
    """

    def __init__(self, address: str):
        """
        Initialize the Chord node.
        """
        self.address = address
        self.running = False
        # hash the address to get the node id
        self.id = hash_key(address)
        # Initialize at logger for the node
        self.logger = logging.getLogger(f"ChordNode-{self.id % 10000}")
        # initialize the finger table
        self.finger_table = FingerTable(self.id, self.address)
        # successor and predecessor of the node
        self.successor = NodeInfo(id=self.id, address=self.address)
        self.predecessor = None

        # Stabilization state
        self.next_finger = 0 # for fix_fingers
        self._stabilization_thread = None
        self._stabilization_running = False

    def _create_stub(self, address: str):
        """
        Create a stub for the given address
        to make gRPC calls to the node
        """
        channel = grpc.insecure_channel(address)
        return chord_pb2_grpc.ChordServiceStub(channel)

    def _node_info_to_proto(self, node_info: NodeInfo) -> chord_pb2.NodeInfo:
        """Convert NodeInfo to protobuf NodeInfo."""
        return chord_pb2.NodeInfo(id=str(node_info.id), address=node_info.address)

    def _proto_to_node_info(self, proto_node: chord_pb2.NodeInfo) -> NodeInfo:
        """Convert protobuf NodeInfo to NodeInfo."""
        if not proto_node.id or not proto_node.address:
            return None
        return NodeInfo(id=int(proto_node.id), address=proto_node.address)

    def _init_finger_table(self):
        """
        Initialize finger table by finding the successor for each finger.
        This is called after joining a network.
        """
        self.logger.info("Initializing finger table...")
        
        for i in range(len(self.finger_table)):
            start = self.finger_table.start(i)
            # Find successor for this finger
            finger_succ = self.find_successor(start)
            self.finger_table[i] = FingerEntry(start=start, successor=finger_succ)
        self.logger.info("Finger table initialized")

    def _in_range(self, key: int, start: int, end: int, 
                  inclusive_start=False, inclusive_end=False) -> bool:
        """
        Check if key is in range (start, end) on the circular identifier space.
        
        By default: (start, end) - exclusive on both ends
        """
        if start == end:
            return inclusive_start or inclusive_end
        
        if start < end:
            # Normal case: no wraparound
            if inclusive_start and inclusive_end:
                return start <= key <= end
            elif inclusive_start:
                return start <= key < end
            elif inclusive_end:
                return start < key <= end
            else:
                return start < key < end
        else:
            # Wraparound case
            if inclusive_start and inclusive_end:
                return key >= start or key <= end
            elif inclusive_start:
                return key >= start or key < end
            elif inclusive_end:
                return key > start or key <= end
            else:
                return key > start or key < end


    def start_server(self):
        server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
        chord_pb2_grpc.add_ChordServiceServicer_to_server(self, server)
        # Start the server on the given address
        server.add_insecure_port(f'{self.address}')
        # Set the running flag to True
        self.running = True
        # Start the server
        server.start()
        # Log the server start
        self.logger.info(f"Chord Node {self.id} server started at {self.address}")
        # Start stabilization thread
        self.start_stabilization()
        # Return the server
        return server

    def stop_server(self):
        """Stop the server and stabilization."""
        self.logger.info("Stopping server...")
        self.running = False
        self.stop_stabilization()

    def join(self, existing_node_address: Optional[str] = None):
        """
        Join a Chord ring.
        
        If existing_node_address is None, create a new ring.
        Otherwise, join the existing ring through that node.
        """
        if existing_node_address:
            self.logger.info(f"Joining existing Chord network via {existing_node_address}")
            
            try:
                stub = self._create_stub(existing_node_address)
                # Find our successor
                response = stub.FindSuccessor(chord_pb2.FindSuccessorRequest(id=str(self.id)))
                self.successor = self._proto_to_node_info(response)
                
                if not self.successor:
                    raise Exception("Failed to get successor information")
                
                self.logger.info(f"Found successor: Node {self.successor.id % 10000} at {self.successor.address}")
                
                # Predecessor will be set by stabilization
                self.predecessor = None
                
                # Initialize finger table
                self._init_finger_table()
                
                self.logger.info("Successfully joined the Chord network")
                return True
                
            except Exception as e:
                self.logger.error(f"Failed to join Chord network: {e}")
                return False
        else:
            # Creating a new Chord ring
            self.logger.info("Creating new Chord network")
            self.successor = NodeInfo(id=self.id, address=self.address)
            self.predecessor = None
            
            # Initialize all fingers to point to self
            for i in range(len(self.finger_table)):
                start = self.finger_table.start(i)
                self.finger_table[i] = FingerEntry(
                    start=start,
                    successor=NodeInfo(id=self.id, address=self.address)
                )
            
            self.logger.info("New Chord network created")
            return True
    
    def closest_preceding_finger(self, id: int) -> NodeInfo:
        """
        Find the closest finger preceding id in our finger table.
        Search from highest to lowest for efficiency.
        """
        # Search finger table from highest to lowest
        for i in range(len(self.finger_table) - 1, -1, -1):
            finger_entry = self.finger_table[i]
            if finger_entry and finger_entry.successor:
                finger_node = finger_entry.successor
                # Check if finger is in range (self.id, id)
                if self._in_range(finger_node.id, self.id, id):
                    return finger_node
        
        # If no finger is closer, return self
        return NodeInfo(self.id, self.address)

    def find_successor(self, id: int) -> NodeInfo:
        """
        Find the successor node for a given ID.
        
        Core Chord lookup algorithm:
        - If id is in (n, successor], return successor
        - Otherwise, forward to closest preceding node
        """
        # If id is in (n, successor], return successor
        if self._in_range(id, self.id, self.successor.id, inclusive_start=True, inclusive_end=True):
            return self.successor
        
        # Otherwise, forward to closest preceding node
        closest_node = self.closest_preceding_finger(id)
        
        if closest_node.id == self.id:
            # No closer node found, return successor
            return self.successor

        try:
            # Ask the closest node to find the successor
            stub = self._create_stub(closest_node.address)
            response = stub.FindSuccessor(chord_pb2.FindSuccessorRequest(id=str(id)))
            return self._proto_to_node_info(response)
        except Exception as e:
            self.logger.error(f"Error finding successor via {closest_node.address}: {e}")
            return self.successor

    def stabilize(self):
        """
        Periodically verify n's immediate successor and tell the successor about n.
        This is the core of the stabilization protocol.
        """
        try:
            # Get our successor's predecessor
            stub = self._create_stub(self.successor.address)
            response = stub.GetPredecessor(chord_pb2.Empty())
            x = self._proto_to_node_info(response)
            
            # If x exists and is between us and our successor, it should be our new successor
            if x and x.id != self.id and self._in_range(x.id, self.id, self.successor.id):
                self.logger.info(f"Updating successor from {self.successor.id % 10000} to {x.id % 10000}")
                self.successor = x
                # Also update first finger
                self.finger_table[0] = FingerEntry(
                    start=self.finger_table.start(0),
                    successor=self.successor
                )
            
            # Notify successor that we might be its predecessor
            stub = self._create_stub(self.successor.address)
            stub.Notify(self._node_info_to_proto(NodeInfo(self.id, self.address)))
            
        except Exception as e:
            self.logger.error(f"Error in stabilize: {e}")
            # Successor might have failed, handle this in check_predecessor

    def notify(self, node: NodeInfo):
        """
        Node n' thinks it might be our predecessor.
        
        Args:
            node: The node that might be our predecessor
        """
        # If we don't have a predecessor, or if node is between our predecessor and us,
        # then node becomes our new predecessor
        if (self.predecessor is None or 
            self._in_range(node.id, self.predecessor.id, self.id)):
            self.logger.info(f"Updating predecessor to Node {node.id % 10000}")
            self.predecessor = node

    def fix_fingers(self):
        """
        Periodically refresh finger table entries.
        Each time this is called, it updates the next finger in round-robin fashion.
        """
        try:
            # Refresh next_finger
            start = self.finger_table.start(self.next_finger)
            successor = self.find_successor(start)
            
            if successor:
                self.finger_table[self.next_finger] = FingerEntry(
                    start=start,
                    successor=successor
                )
                self.logger.debug(f"Fixed finger[{self.next_finger}] to Node {successor.id % 10000}")
            
            # Move to next finger (round-robin)
            self.next_finger = (self.next_finger + 1) % len(self.finger_table)
            
        except Exception as e:
            self.logger.error(f"Error in fix_fingers: {e}")

    def check_predecessor(self):
        """
        Periodically check if predecessor has failed.
        If predecessor doesn't respond to ping, clear it.
        """
        if self.predecessor:
            try:
                stub = self._create_stub(self.predecessor.address)
                stub.Ping(chord_pb2.Empty(), timeout=2.0)
            except Exception as e:
                self.logger.warning(f"Predecessor {self.predecessor.id % 10000} failed: {e}")
                self.predecessor = None

    def start_stabilization(self, interval: float = 1.0):
        """
        Start periodic stabilization in a background thread.
        
        Args:
            interval: Time between stabilization runs in seconds
        """
        import threading
        import time
        
        def stabilization_loop():
            self.logger.info("Stabilization started")
            while self._stabilization_running:
                try:
                    self.stabilize()
                    self.fix_fingers()
                    self.check_predecessor()
                except Exception as e:
                    self.logger.error(f"Error in stabilization loop: {e}")
                
                time.sleep(interval)
            self.logger.info("Stabilization stopped")
        
        self._stabilization_running = True
        self._stabilization_thread = threading.Thread(target=stabilization_loop, daemon=True)
        self._stabilization_thread.start()

    def stop_stabilization(self):
        """Stop the stabilization thread."""
        if self._stabilization_running:
            self._stabilization_running = False
            if self._stabilization_thread:
                self._stabilization_thread.join(timeout=5.0)


    # ================================ RPC Methods ================================
    def FindSuccessor(self, request, context):
        """
        Find the successor of the given ID
        """
        id = int(request.id)
        successor = self.find_successor(id)
        return self._node_info_to_proto(successor)

    def GetPredecessor(self, request, context):
        """
        Return this node's predecessor.
        """
        if self.predecessor:
            return self._node_info_to_proto(self.predecessor)
        else:
            # Return empty NodeInfo if no predecessor
            return chord_pb2.NodeInfo()

    def Notify(self, request, context):
        """
        RPC handler for Notify.
        Another node is notifying us that it might be our predecessor.
        """
        node = self._proto_to_node_info(request)
        if node:
            self.notify(node)
        return chord_pb2.Empty()


    def Ping(self, request, context):
        """
        Check if the node is alive
        """
        return chord_pb2.Empty()
