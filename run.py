"""
Chord DHT Node CLI
"""
import argparse
import sys
import time
import logging
from src.node import Node

def main():
    # Configure logging FIRST
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    parser = argparse.ArgumentParser(description='Start a Chord DHT node')
    parser.add_argument(
        '--host',
        type=str,
        default='localhost',
        help='Host to bind to (default: localhost)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=50051,
        help='Port to bind to (default: 50051)'
    )
    parser.add_argument(
        '--join',
        type=str,
        help='Address of an existing node to join (format: host:port)'
    )
    
    args = parser.parse_args()
    
    # Create node address
    address = f"{args.host}:{args.port}"
    
    # Create and start node
    print(f"Creating node at {address}...")
    node = Node(address)
    server = node.start_server()
    
    # Give server time to start
    time.sleep(1)

    # Join the network if a join address is provided
    if args.join:
        print(f"Attempting to join network via {args.join}...")
        result = node.join(args.join)
        if result:
            print("✓ Successfully joined network")
        else:
            print("✗ Failed to join network")
    else:
        print("Creating new network...")
        node.join(None)
    
    try:
        print(f"\nChord node running at {address}")
        print(f"Node ID: {node.id % 10000}")
        print("Press Ctrl+C to stop...\n")
        
        # Keep the server running
        while True:
            time.sleep(86400)
    except KeyboardInterrupt:
        print("\nShutting down...")
        node.stop_server()
        server.stop(0)
        sys.exit(0)

if __name__ == '__main__':
    main()