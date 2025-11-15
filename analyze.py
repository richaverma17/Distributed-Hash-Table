#!/usr/bin/env python3
"""
Chord Key Distribution Analyzer
Helps understand which keys map to which nodes
"""
import hashlib

RING_BITS = 160
RING_SIZE = 2 ** RING_BITS

def hash_key(key: str) -> int:
    """Hash a key to an integer in the Chord identifier space."""
    sha1 = hashlib.sha1(key.encode('utf-8'))
    return int(sha1.hexdigest(), 16) % RING_SIZE

def find_successor_node(key_hash: int, nodes: list) -> dict:
    """Find which node is responsible for a given key hash."""
    # Sort nodes by ID
    sorted_nodes = sorted(nodes, key=lambda x: x['id'])
    
    # Find the first node whose ID is >= key_hash (successor)
    for node in sorted_nodes:
        if node['id'] >= key_hash:
            return node
    
    # If no node found, wrap around to first node
    return sorted_nodes[0]

def analyze_chord_ring(node_addresses: list):
    """Analyze a Chord ring and suggest keys for testing."""
    
    # Calculate node IDs
    nodes = []
    for addr in node_addresses:
        node_id = hash_key(addr)
        nodes.append({
            'address': addr,
            'id': node_id,
            'id_short': node_id % 10000  # For display
        })
    
    # Sort by ID
    nodes.sort(key=lambda x: x['id'])
    
    print("=" * 70)
    print("CHORD RING STRUCTURE")
    print("=" * 70)
    
    for i, node in enumerate(nodes):
        print(f"\nNode {i+1}: {node['address']}")
        print(f"  Full ID: {node['id']}")
        print(f"  Short ID: {node['id_short']}")
    
    # Calculate ranges
    print("\n" + "=" * 70)
    print("KEY RESPONSIBILITY RANGES")
    print("=" * 70)
    
    for i, node in enumerate(nodes):
        prev_node = nodes[i-1]  # Works due to wrap-around
        if i == 0:
            # First node handles wrap-around
            print(f"\nNode {node['address']} is responsible for:")
            print(f"  Keys with hash in ({prev_node['id']}, {node['id']}]")
            print(f"  (This includes wrap-around from max to {node['id']})")
        else:
            print(f"\nNode {node['address']} is responsible for:")
            print(f"  Keys with hash in ({prev_node['id']}, {node['id']}]")
    
    # Generate test keys
    print("\n" + "=" * 70)
    print("FINDING TEST KEYS FOR EACH NODE")
    print("=" * 70)
    
    test_keys_per_node = {node['address']: [] for node in nodes}
    
    # Try common words/patterns to find keys for each node
    test_words = [
        # Common names
        "alice", "bob", "charlie", "david", "eve", "frank", "grace",
        "henry", "ivy", "jack", "kate", "leo", "mia", "noah",
        # Numbers
        "key0", "key1", "key2", "key3", "key4", "key5",
        "data1", "data2", "data3", "value1", "value2", "value3",
        # Random words
        "apple", "banana", "cherry", "date", "elderberry",
        "test", "demo", "sample", "example", "foo", "bar", "baz",
        "hello", "world", "python", "chord", "dht",
        # More variations
        "user_1", "user_2", "user_3", "item_a", "item_b", "item_c",
        "record1", "record2", "record3",
    ]
    
    # Also try some systematic patterns
    for i in range(100):
        test_words.append(f"test_{i}")
        test_words.append(f"key_{i}")
    
    for key in test_words:
        key_hash = hash_key(key)
        responsible_node = find_successor_node(key_hash, nodes)
        
        # Collect at most 5 keys per node
        if len(test_keys_per_node[responsible_node['address']]) < 5:
            test_keys_per_node[responsible_node['address']].append(key)
    
    # Print test keys
    for node in nodes:
        addr = node['address']
        print(f"\n📍 Keys that will be stored on {addr}:")
        for key in test_keys_per_node[addr]:
            key_hash = hash_key(key)
            print(f"   '{key}' (hash: {key_hash % 10000})")
    
    # Generate test script
    print("\n" + "=" * 70)
    print("TEST COMMANDS FOR YOUR CLIENT")
    print("=" * 70)
    print("\n# You can connect to ANY node and store these keys:")
    print("# They will be automatically routed to the correct node!\n")
    
    for node in nodes:
        addr = node['address']
        keys = test_keys_per_node[addr]
        if keys:
            print(f"\n# These will end up on {addr}:")
            for key in keys[:3]:  # Show first 3
                print(f"put {key} 'value_for_{key}'")
    
    print("\n# Then verify distribution by checking each node's storage:")
    for node in nodes:
        addr = node['address']
        print(f"# Connect to {addr} and check its local storage")

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        # Use provided addresses
        addresses = sys.argv[1:]
    else:
        # Default to 3 local nodes
        addresses = [
            "localhost:50051",
            "localhost:50052",
            "localhost:50053"
        ]
    
    print(f"\nAnalyzing Chord ring with {len(addresses)} nodes...")
    analyze_chord_ring(addresses)