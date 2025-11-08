#!/usr/bin/env python3

import argparse
import grpc
import sys
import cmd
from proto import chord_pb2, chord_pb2_grpc


class ChordClient(object):
    """Client for interacting with chord DHT"""

    def __init__(self, node_address: str):
        self.node_address = node_address
        self.channel = grpc.insecure_channel(node_address)
        self.stub = chord_pb2_grpc.ChordServiceStub(self.channel)


    def put(self, key: str, value: str) -> bool:
        try:
            request = chord_pb2.PutRequest(key=key, value=value)
            response = self.stub.Put(request)
            return response.success
        except Exception as e:
            print(f"Error putting key to {self.node_address}: {e}")
            return False

    def get(self, key: str) -> tuple[bool, str]:
        try:
            request = chord_pb2.GetRequest(key=key)
            response = self.stub.Get(request, timeout=10.0)
            return response.found, response.value
        except Exception as e:
            print(f"Error getting key from {self.node_address}: {e}")
            return False, ""

    def delete(self, key: str) -> bool:
        try:
            request = chord_pb2.DeleteRequest(key=key)
            response = self.stub.Delete(request, timeout=10.0)
            return response.found
        except Exception as e:
            print(f"Error deleting key from {self.node_address}: {e}")
            return False

    def ping(self) -> bool:
        try:
            request = chord_pb2.PingRequest()
            response = self.stub.Ping(request, timeout=10.0)
            return response.alive
        except Exception as e:
            print(f"Error pinging {self.node_address}: {e}")
            return False

    def close(self):
        self.channel.close()


class ClientREPL(cmd.Cmd):
    intro = """
    Chord DHT REPL

    Type 'help' or '?' for available commands.
    Type 'exit' or 'quit' to exit.
    """

    prompt = 'chord> '

    def __init__(self, client: ChordClient):
        super().__init__()
        self.client = client
        print(f"Connected to {client.node_address}\n")

    def do_put(self, arg: str):
        """Store a key-value pair: put <key> <value>"""
        parts = arg.split(maxsplit=1)
        if len(parts) < 2:
            print("Usage: put <key> <value>")
            return

        key, value = parts
        success = self.client.put(key, value)
        if success:
            print(f"Key '{key}' stored successfully")
        else:
            print(f"Failed to store key '{key}'")

    def do_get(self, arg: str):
        """Retrieve a value by key: get <key>"""
        if not arg:
            print("Usage: get <key>")
            return

        key = arg.strip()
        found, value = self.client.get(key)
        if found:
            print(f"Value for key '{key}': {value}")
        else:
            print(f"Key '{key}' not found")

    def do_delete(self, arg: str):
        """Delete a key-value pair: delete <key>"""
        if not arg:
            print("Usage: delete <key>")
            return

        key = arg.strip()
        success = self.client.delete(key)
        if success:
            print(f"Key '{key}' deleted successfully")
        else:
            print(f"Failed to delete key '{key}'")

    def do_ping(self, arg: str):
        """Check if the node is alive: ping"""
        alive = self.client.ping()
        if alive:
            print("Node is alive")
        else:
            print("Node is not alive")

    def do_exit(self, arg: str):
        """Exit the REPL: exit"""
        print("Exiting...")
        self.client.close()
        return True

    def do_quit(self, arg: str):
        """Quit the REPL: quit"""
        print("Quitting...")
        self.client.close()
        return True

    def do_EOF(self, arg):
        """Exit on EOF (Ctrl+D)"""
        print()
        return True
    
    def emptyline(self):
        """Do nothing on empty line"""
        pass
    
    def default(self, line):
        """Handle unknown commands"""
        print(f"❌ Unknown command: {line}")
        print("Type 'help' for available commands")

    def do_help(self, arg: str):
        """Display help: help"""
        print("Available commands:")
        print("put <key> <value> - Store a key-value pair")
        print("get <key> - Retrieve a value by key")
        print("delete <key> - Delete a key-value pair")
        print("ping - Check if the node is alive")


def main():
    parser = argparse.ArgumentParser(description='Chord DHT REPL Client')
    parser.add_argument('--node-address', type=str, required=True, help='Address of the node to connect to')
    args = parser.parse_args()

    # Validate the node address
    if not args.node_address.count(':') == 1:
        print("Error: Invalid node address format. Use <host>:<port>")
        sys.exit(1)
    
    print(f"Connecting to {args.node_address}...")

    # Create the client and REPL
    try:
        client = ChordClient(args.node_address)
        repl = ClientREPL(client)
        repl.cmdloop()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()