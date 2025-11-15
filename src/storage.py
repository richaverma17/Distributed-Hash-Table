import logging
from typing import Dict, Optional


class Storage:
    """
    Simple in-memory key-value storage for a Chord node.
    Each node stores keys that it is responsible for.
    """
    
    def __init__(self, node_id: int):
        """
        Initialize storage for a node.
        
        Args:
            node_id: The ID of the node this storage belongs to
        """
        self.node_id = node_id
        self.data: Dict[str, str] = {}
        self.logger = logging.getLogger(f"Storage-{node_id % 10000}")
    
    def put(self, key: str, value: str) -> bool:
        """
        Store a key-value pair.
        
        Args:
            key: The key to store
            value: The value to store
            
        Returns:
            True if successful
        """
        self.data[key] = value
        self.logger.info(f"Stored key '{key}' with value '{value[:50]}...' (total keys: {len(self.data)})")
        return True
    
    def get(self, key: str) -> Optional[str]:
        """
        Retrieve a value by key.
        
        Args:
            key: The key to retrieve
            
        Returns:
            The value if found, None otherwise
        """
        value = self.data.get(key)
        if value is not None:
            self.logger.info(f"Retrieved key '{key}'")
        else:
            self.logger.info(f"Key '{key}' not found")
        return value
    
    def delete(self, key: str) -> bool:
        """
        Delete a key-value pair.
        
        Args:
            key: The key to delete
            
        Returns:
            True if key existed and was deleted, False otherwise
        """
        if key in self.data:
            del self.data[key]
            self.logger.info(f"Deleted key '{key}' (total keys: {len(self.data)})")
            return True
        else:
            self.logger.info(f"Key '{key}' not found for deletion")
            return False
    
    
    def __len__(self):
        """Return the number of key-value pairs stored."""
        return len(self.data)