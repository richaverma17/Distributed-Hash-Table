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
        # Return the server
        return server

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


    # ================================ RPC Methods ================================
    def FindSuccessor(self, request, context):
        """
        Find the successor of the given ID
        """
        id = int(request.id)
        successor = self.find_successor(id)
        return self._node_info_to_proto(successor)

    def Ping(self, request, context):
        """
        Check if the node is alive
        """
        return chord_pb2.Empty()
