from .utils import RING_BITS, RING_SIZE, NodeInfo


class FingerEntry:
    """
    Single entry in the finger table
    """
    def __init__(self, start: int, successor: NodeInfo):
        self.start = start
        self.successor = successor


class FingerTable:
    """
    Finger table for Chord protocol
    """
    def __init__(self, node_id: int, address: str):
        self.node_id = node_id
        self.address = address
        self.m = RING_BITS
        self.fingers = [None] * self.m

    def start(self, i: int) -> int:
        """Calculate the start of the i-th finger interval."""
        return (self.node_id + 2 ** i) % RING_SIZE

    def get_interval(self, i: int) -> tuple[int, int]:
        start = self.start(i)

        if i + 1 < self.m:
            end = self.start(i + 1)
        else:
            # last finger
            end = self.node_id
        return (start, end)

    def __getitem__(self, i: int):
        """Allow indexing like finger_table[i]"""
        return self.fingers[i]

    def __setitem__(self, i: int, entry: FingerEntry):
        """Allow assignment like finger_table[i] = TableEntry(...)"""
        self.fingers[i] = entry

    def __len__(self):
        return len(self.fingers)