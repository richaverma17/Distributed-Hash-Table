import hashlib
from dataclasses import dataclass

# Ring size 
RING_BITS = 8
RING_SIZE = 2 ** RING_BITS # m-bit identifier space


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


def hash_key(key: str) -> int:
    """Hash a key to an integer in the Chord identifier space."""
    sha1 = hashlib.sha1(key.encode('utf-8'))
    # Convert the SHA-1 hash to an integer in the range [0, RING_SIZE)
    return int(sha1.hexdigest(), 16) % RING_SIZE
