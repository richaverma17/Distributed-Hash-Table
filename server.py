"""
FastAPI server for managing and visualizing Chord DHT nodes
"""
import asyncio
import logging
from typing import Dict, List, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import threading
import grpc
from concurrent import futures

from src.node import Node
from src.utils import hash_key, RING_SIZE, RING_BITS
from proto import chord_pb2, chord_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Chord DHT Visualizer")

# Store active nodes
active_nodes: Dict[str, dict] = {}  # address -> {node, server, thread}
next_port = 50051


class NodeCreateRequest(BaseModel):
    join_address: Optional[str] = None


class KeyValueRequest(BaseModel):
    key: str
    value: str
    node_address: str


class KeyRequest(BaseModel):
    key: str
    node_address: str


# WebSocket manager for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


def run_node_server(node: Node, server):
    """Run a node server in a separate thread"""
    try:
        server.start()
        logger.info(f"Node {node.id % 10000} server started")
        server.wait_for_termination()
    except Exception as e:
        logger.error(f"Error running node server: {e}")


@app.get("/")
async def root():
    """Serve the main HTML page"""
    html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Chord DHT Visualizer</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 30px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        .controls {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }}
        .button-group {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        button {{
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.3s;
        }}
        .btn-primary {{
            background: #667eea;
            color: white;
        }}
        .btn-primary:hover {{
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(102, 126, 234, 0.4);
        }}
        .btn-danger {{
            background: #f56565;
            color: white;
        }}
        .btn-danger:hover {{
            background: #e53e3e;
        }}
        .btn-success {{
            background: #48bb78;
            color: white;
        }}
        .btn-success:hover {{
            background: #38a169;
        }}
        input, select {{
            padding: 10px;
            border: 2px solid #e2e8f0;
            border-radius: 5px;
            font-size: 14px;
            flex: 1;
            min-width: 200px;
        }}
        input:focus, select:focus {{
            outline: none;
            border-color: #667eea;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .card h2 {{
            color: #667eea;
            margin-bottom: 15px;
            font-size: 1.5em;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }}
        #ring-canvas {{
            width: 100%;
            height: 500px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            background: #f7fafc;
        }}
        .node-item {{
            background: #f7fafc;
            padding: 12px;
            margin: 8px 0;
            border-radius: 5px;
            border-left: 4px solid #667eea;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .node-info {{
            flex: 1;
        }}
        .node-id {{
            font-weight: bold;
            color: #667eea;
            font-size: 1.1em;
        }}
        .node-address {{
            color: #718096;
            font-size: 0.9em;
        }}
        .status {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #48bb78;
            margin-right: 8px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }}
        .stat-label {{
            color: #718096;
            margin-top: 5px;
        }}
        .log-entry {{
            padding: 8px;
            margin: 4px 0;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        .log-success {{
            background: #c6f6d5;
            color: #22543d;
        }}
        .log-error {{
            background: #fed7d7;
            color: #742a2a;
        }}
        .log-info {{
            background: #bee3f8;
            color: #2c5282;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔗 Chord DHT Visualizer</h1>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value" id="node-count">0</div>
                <div class="stat-label">Active Nodes</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="ring-size">2^{RING_BITS}</div>
                <div class="stat-label">Ring Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="unique-key-count">0</div>
                <div class="stat-label">Unique Keys</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="replica-count">0</div>
                <div class="stat-label">Total Replicas</div>
            </div>
            <div class="stat-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                <div class="stat-value" style="color: white;">3</div>
                <div class="stat-label" style="color: rgba(255,255,255,0.9);">Replication Factor</div>
            </div>
        </div>


        <div class="controls">
            <h2>Node Management</h2>
            <div class="button-group">
                <button class="btn-primary" onclick="createNode()">➕ Add Node</button>
                <button class="btn-primary" onclick="createNode(true)">➕ Add & Join</button>
                <select id="node-select">
                    <option value="">Select node...</option>
                </select>
                <button class="btn-danger" onclick="removeNode()">🗑️ Remove Selected</button>
                <button class="btn-danger" onclick="removeAllNodes()">🗑️ Remove All</button>
            </div>
        </div>

        <div class="controls">
            <h2>Key-Value Operations</h2>
            <div class="button-group">
                <input type="text" id="key-input" placeholder="Key">
                <input type="text" id="value-input" placeholder="Value">
                <select id="operation-node">
                    <option value="">Select node...</option>
                </select>
                <button class="btn-success" onclick="putKey()">PUT</button>
                <button class="btn-primary" onclick="getKey()">GET</button>
                <button class="btn-danger" onclick="deleteKey()">DELETE</button>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>Chord Ring Visualization</h2>
                <canvas id="ring-canvas"></canvas>

            <div style="margin-top: 10px; padding: 10px; background: #f7fafc; border-radius: 5px; font-size: 0.9em;">
                <strong>Legend:</strong>
                <span style="margin-left: 15px;">🔵 Node</span>
                <span style="margin-left: 15px;">🟢 Node with keys</span>
                <span style="margin-left: 15px;"><span style="display: inline-block; width: 30px; height: 2px; background: rgba(72, 187, 120, 0.3); vertical-align: middle;"></span> Replication</span>
                <span style="margin-left: 15px;">🔑 Primary key</span>
                <span style="margin-left: 15px;">📋 Replica</span>
            </div>
            </div>

            <div class="card">
                <h2>Active Nodes</h2>
                <div id="nodes-list"></div>
            </div>
        </div>

        <div class="card">
            <h2>Activity Log</h2>
            <div id="log" style="max-height: 300px; overflow-y: auto;"></div>
        </div>
    </div>

    <script>
        const ws = new WebSocket(`ws://${{window.location.host}}/ws`);
        let nodes = {{}};

        ws.onmessage = (event) => {{
            const data = JSON.parse(event.data);
            handleUpdate(data);
        }};

        ws.onerror = (error) => {{
            console.error('WebSocket error:', error);
            addLog('WebSocket connection error', 'error');
        }};

        ws.onopen = () => {{
            console.log('WebSocket connected');
            addLog('Connected to server', 'success');
        }};

        function handleUpdate(data) {{
            if (data.type === 'nodes_update') {{
                nodes = data.nodes;
                updateNodesDisplay();
                drawRing();
                updateSelects();
                
                // Update key counts
                if (data.unique_keys !== undefined) {{
                    document.getElementById('unique-key-count').textContent = data.unique_keys;
                }}
                if (data.total_replicas !== undefined) {{
                    document.getElementById('replica-count').textContent = data.total_replicas;
                }}
            }} else if (data.type === 'log') {{
                addLog(data.message, data.level);
            }}
        }}

        function updateNodesDisplay() {{
            const nodesList = document.getElementById('nodes-list');
            const nodeCount = document.getElementById('node-count');
            
            nodeCount.textContent = Object.keys(nodes).length;
            
            if (Object.keys(nodes).length === 0) {{
                nodesList.innerHTML = '<p style="color: #718096;">No nodes active</p>';
                return;
            }}

            nodesList.innerHTML = Object.entries(nodes).map(([addr, node]) => {{
                const keysList = node.keys && node.keys.length > 0 
                    ? node.keys.map(k => {{
                        // Determine if this is a primary or replica by checking which node should own it
                        const keyHash = hashString(k);
                        const isPrimary = findResponsibleNode(keyHash) === node.id;
                        const bgColor = isPrimary ? '#c6f6d5' : '#e6fffa';  // Green for primary, cyan for replica
                        const icon = isPrimary ? '🔑' : '📋';
                        return `<span style="background: ${{bgColor}}; padding: 2px 6px; border-radius: 3px; margin: 2px; display: inline-block; font-size: 0.85em;" title="${{isPrimary ? 'Primary' : 'Replica'}}">${{icon}} ${{k}}</span>`;
                    }}).join(' ')
                    : '<span style="color: #a0aec0; font-size: 0.85em;">No keys</span>';
                
                return `
                <div class="node-item" title="Node ${{node.id}} - Keys: ${{node.keys ? node.keys.join(', ') : 'none'}}">
                    <div class="node-info">
                        <div><span class="status"></span><span class="node-id">Node ${{node.id}}</span> <span style="color: #48bb78; font-size: 0.9em;">(${{node.key_count || 0}} keys)</span></div>
                        <div class="node-address">${{node.address}}</div>
                        <div class="node-address">Successor: ${{node.successor_id}} | Predecessor: ${{node.predecessor_id || 'None'}}</div>
                        <div style="margin-top: 6px;">
                            ${{keysList}}
                        </div>
                    </div>
                </div>
                `;
            }}).join('');
        }}

        // Helper function to hash strings (simplified version)
        function hashString(str) {{
            let hash = 0;
            for (let i = 0; i < str.length; i++) {{
                const char = str.charCodeAt(i);
                hash = ((hash << 5) - hash) + char;
                hash = hash & hash;
            }}
            return Math.abs(hash) % 10000;
        }}

        // Helper to find which node should own this key
        function findResponsibleNode(keyHash) {{
            const nodeIds = Object.values(nodes).map(n => n.id).sort((a, b) => a - b);
            for (let nodeId of nodeIds) {{
                if (keyHash <= nodeId) {{
                    return nodeId;
                }}
            }}
            return nodeIds[0];  // Wraparound to first node
        }}

        function updateSelects() {{
            const selects = ['node-select', 'operation-node'];
            const options = Object.entries(nodes).map(([addr, node]) => 
                `<option value="${{addr}}">Node ${{node.id}} (${{addr}})</option>`
            ).join('');
            
            selects.forEach(id => {{
                const select = document.getElementById(id);
                const currentValue = select.value;
                select.innerHTML = '<option value="">Select node...</option>' + options;
                select.value = currentValue;
            }});
        }}

        function drawRing() {{
            const canvas = document.getElementById('ring-canvas');
            const ctx = canvas.getContext('2d');
            const width = canvas.width = canvas.offsetWidth;
            const height = canvas.height = canvas.offsetHeight;
            
            ctx.clearRect(0, 0, width, height);
            
            const centerX = width / 2;
            const centerY = height / 2;
            const radius = Math.min(width, height) / 2 - 50;
            
            // Draw ring
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.strokeStyle = '#cbd5e0';
            ctx.lineWidth = 3;
            ctx.stroke();
            
            const ringSize = {RING_SIZE};
            const nodeArray = Object.entries(nodes);
            
            // First pass: Draw replication lines (so they appear behind nodes)
            nodeArray.forEach(([addr, node]) => {{
                const angle = (node.id / ringSize) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                
                // Draw lines to next 2 nodes (replicas) in lighter color
                let currentId = node.id;
                let replicaCount = 0;
                const maxReplicas = 2;  // Show replication_factor - 1
                
                nodeArray.forEach(([_, otherNode]) => {{
                    if (replicaCount < maxReplicas && otherNode.id > currentId) {{
                        const otherAngle = (otherNode.id / ringSize) * 2 * Math.PI - Math.PI / 2;
                        const otherX = centerX + radius * Math.cos(otherAngle);
                        const otherY = centerY + radius * Math.sin(otherAngle);
                        
                        ctx.beginPath();
                        ctx.moveTo(x, y);
                        ctx.lineTo(otherX, otherY);
                        ctx.strokeStyle = 'rgba(72, 187, 120, 0.2)';  // Green for replication
                        ctx.lineWidth = 2;
                        ctx.setLineDash([3, 3]);
                        ctx.stroke();
                        ctx.setLineDash([]);
                        
                        replicaCount++;
                    }}
                }});
            }});
            
            // Second pass: Draw nodes (on top)
            nodeArray.forEach(([addr, node], idx) => {{
                const angle = (node.id / ringSize) * 2 * Math.PI - Math.PI / 2;
                const x = centerX + radius * Math.cos(angle);
                const y = centerY + radius * Math.sin(angle);
                
                // Draw node
                ctx.beginPath();
                ctx.arc(x, y, 15, 0, 2 * Math.PI);
                ctx.fillStyle = node.key_count > 0 ? '#48bb78' : '#667eea';
                ctx.fill();
                ctx.strokeStyle = 'white';
                ctx.lineWidth = 3;
                ctx.stroke();
                
                // Draw label with key count
                ctx.fillStyle = '#2d3748';
                ctx.font = 'bold 12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(`N${{node.id}}`, x, y - 25);
                
                // Draw key count badge
                if (node.key_count > 0) {{
                    ctx.fillStyle = '#f56565';
                    ctx.beginPath();
                    ctx.arc(x + 10, y - 10, 8, 0, 2 * Math.PI);
                    ctx.fill();
                    ctx.fillStyle = 'white';
                    ctx.font = 'bold 10px Arial';
                    ctx.fillText(node.key_count, x + 10, y - 7);
                }}
            }});
        }}

        function addLog(message, level = 'info') {{
            const log = document.getElementById('log');
            const entry = document.createElement('div');
            entry.className = `log-entry log-${{level}}`;
            entry.textContent = `[${{new Date().toLocaleTimeString()}}] ${{message}}`;
            log.insertBefore(entry, log.firstChild);
            
            // Keep only last 50 entries
            while (log.children.length > 50) {{
                log.removeChild(log.lastChild);
            }}
        }}

        async function createNode(join = false) {{
            try {{
                addLog('Creating node...', 'info');
                const joinAddress = join && Object.keys(nodes).length > 0 ? 
                    Object.keys(nodes)[0] : null;
                
                const response = await fetch('/api/nodes', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{join_address: joinAddress}})
                }});
                
                const data = await response.json();
                if (data.status === 'success') {{
                    addLog(`Node created at ${{data.address}}`, 'success');
                }} else {{
                    addLog(`Failed to create node: ${{data.message}}`, 'error');
                }}
            }} catch (error) {{
                console.error('Error creating node:', error);
                addLog(`Error creating node: ${{error.message}}`, 'error');
            }}
        }}

        async function removeNode() {{
            const select = document.getElementById('node-select');
            const address = select.value;
            if (!address) {{
                addLog('Please select a node', 'error');
                return;
            }}
            
            try {{
                const response = await fetch(`/api/nodes/${{encodeURIComponent(address)}}`, {{
                    method: 'DELETE'
                }});
                
                const data = await response.json();
                addLog(data.message, data.status === 'success' ? 'success' : 'error');
            }} catch (error) {{
                console.error('Error removing node:', error);
                addLog(`Error: ${{error.message}}`, 'error');
            }}
        }}

        async function removeAllNodes() {{
            if (!confirm('Remove all nodes?')) return;
            
            try {{
                const response = await fetch('/api/nodes/all', {{
                    method: 'DELETE'
                }});
                
                const data = await response.json();
                addLog(data.message, 'success');
            }} catch (error) {{
                console.error('Error removing all nodes:', error);
                addLog(`Error: ${{error.message}}`, 'error');
            }}
        }}

        async function putKey() {{
            const key = document.getElementById('key-input').value;
            const value = document.getElementById('value-input').value;
            const nodeAddress = document.getElementById('operation-node').value;
            
            if (!key || !value || !nodeAddress) {{
                addLog('Please fill all fields', 'error');
                return;
            }}
            
            try {{
                const response = await fetch('/api/put', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{key, value, node_address: nodeAddress}})
                }});
                
                const data = await response.json();
                addLog(data.message, data.status === 'success' ? 'success' : 'error');
            }} catch (error) {{
                console.error('Error in PUT:', error);
                addLog(`Error: ${{error.message}}`, 'error');
            }}
        }}

        async function getKey() {{
            const key = document.getElementById('key-input').value;
            const nodeAddress = document.getElementById('operation-node').value;
            
            if (!key || !nodeAddress) {{
                addLog('Please fill key and select node', 'error');
                return;
            }}
            
            try {{
                const response = await fetch(`/api/get?key=${{encodeURIComponent(key)}}&node_address=${{encodeURIComponent(nodeAddress)}}`);
                const data = await response.json();
                
                if (data.status === 'success') {{
                    addLog(`GET '${{key}}' = '${{data.value}}'`, 'success');
                    document.getElementById('value-input').value = data.value;
                }} else {{
                    addLog(data.message, 'error');
                }}
            }} catch (error) {{
                console.error('Error in GET:', error);
                addLog(`Error: ${{error.message}}`, 'error');
            }}
        }}

        async function deleteKey() {{
            const key = document.getElementById('key-input').value;
            const nodeAddress = document.getElementById('operation-node').value;
            
            if (!key || !nodeAddress) {{
                addLog('Please fill key and select node', 'error');
                return;
            }}
            
            try {{
                const response = await fetch('/api/delete', {{
                    method: 'DELETE',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{key, node_address: nodeAddress}})
                }});
                
                const data = await response.json();
                addLog(data.message, data.status === 'success' ? 'success' : 'error');
            }} catch (error) {{
                console.error('Error in DELETE:', error);
                addLog(`Error: ${{error.message}}`, 'error');
            }}
        }}

        // Initial load
        // Initial load
        fetch('/api/nodes').then(r => r.json()).then(data => {{
            nodes = data.nodes;
            updateNodesDisplay();
            drawRing();
            updateSelects();
            
            // Update total keys
            if (data.total_keys !== undefined) {{
                document.getElementById('key-count').textContent = data.total_keys;
            }}
        }}).catch(error => {{
            console.error('Error loading initial nodes:', error);
            addLog('Error loading initial data', 'error');
        }});

        // Redraw ring on window resize
        window.addEventListener('resize', drawRing);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


async def broadcast_nodes_update():
    """Broadcast current nodes state to all connected clients"""
    nodes_data = {}
    total_keys = 0
    total_unique_keys = set()  # Track unique keys across all nodes
    
    for address, node_data in active_nodes.items():
        node = node_data["node"]
        keys = node.storage.get_all_keys()
        key_count = len(keys)
        total_keys += key_count
        
        # Track unique keys
        total_unique_keys.update(keys.keys())
        
        nodes_data[address] = {
            "id": node.id % 10000,
            "address": address,
            "successor_id": node.successor.id % 10000 if node.successor else None,
            "predecessor_id": node.predecessor.id % 10000 if node.predecessor else None,
            "key_count": key_count,
            "keys": list(keys.keys()),  # Send list of key names
            "replication_factor": getattr(node, 'replication_factor', 1)  # Add replication factor
        }
    
    await manager.broadcast({
        "type": "nodes_update",
        "nodes": nodes_data,
        "total_keys": total_keys,
        "unique_keys": len(total_unique_keys),  # Unique keys count
        "total_replicas": total_keys  # Total including replicas
    })


async def broadcast_log(message: str, level: str = "info"):
    """Broadcast a log message to all connected clients"""
    await manager.broadcast({
        "type": "log",
        "message": message,
        "level": level
    })


@app.get("/api/nodes")
async def get_nodes():
    """Get all active nodes"""
    nodes_data = {}
    total_keys = 0
    
    for address, node_data in active_nodes.items():
        node = node_data["node"]
        keys = node.storage.get_all_keys()
        key_count = len(keys)
        total_keys += key_count
        
        nodes_data[address] = {
            "id": node.id % 10000,
            "address": address,
            "successor_id": node.successor.id % 10000 if node.successor else None,
            "predecessor_id": node.predecessor.id % 10000 if node.predecessor else None,
            "key_count": key_count,
            "keys": list(keys.keys()),
            "replication_factor": getattr(node, 'replication_factor', 1)
        }
    
    return {"nodes": nodes_data, "total_keys": total_keys}


@app.post("/api/nodes")
async def create_node(request: NodeCreateRequest):
    """Create a new node"""
    global next_port
    
    try:
        # Create node address
        address = f"localhost:{next_port}"
        next_port += 1
        
        # Create and start node
        node = Node(address)
        server = node.start_server()
        
        # Wait longer for server to fully start and be ready to accept connections
        await asyncio.sleep(1.5)
        
        # Join network if requested
        if request.join_address and request.join_address in active_nodes:
            # Verify the join address node is still active
            if request.join_address not in active_nodes:
                server.stop(0)
                raise Exception(f"Join target node {request.join_address} not found")
            
            success = node.join(request.join_address)
            if not success:
                node.stop_server()
                server.stop(0)
                raise Exception("Failed to join network")
            
            # Wait a bit more for stabilization to propagate
            await asyncio.sleep(1.0)
        else:
            node.join(None)  # Create new ring
        
        # Store node info
        active_nodes[address] = {
            "node": node,
            "server": server
        }
        
        await broadcast_nodes_update()
        await broadcast_log(f"Node created at {address} (ID: {node.id % 10000})", "success")
        
        return {
            "status": "success",
            "address": address,
            "node_id": node.id % 10000
        }
    except Exception as e:
        logger.error(f"Error creating node: {e}")
        await broadcast_log(f"Error creating node: {str(e)}", "error")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/nodes/{address}")
async def remove_node(address: str):
    """Remove a specific node"""
    if address not in active_nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    
    try:
        node_data = active_nodes[address]
        node_data["node"].stop_server()
        node_data["server"].stop(0)
        
        del active_nodes[address]
        
        await broadcast_nodes_update()
        await broadcast_log(f"Node removed: {address}", "success")
        
        return {"status": "success", "message": f"Node {address} removed"}
    except Exception as e:
        logger.error(f"Error removing node: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/nodes/all")
async def remove_all_nodes():
    """Remove all nodes"""
    try:
        for address, node_data in list(active_nodes.items()):
            node_data["node"].stop_server()
            node_data["server"].stop(0)
        
        active_nodes.clear()
        
        await broadcast_nodes_update()
        await broadcast_log("All nodes removed", "success")
        
        return {"status": "success", "message": "All nodes removed"}
    except Exception as e:
        logger.error(f"Error removing all nodes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/put")
async def put_key(request: KeyValueRequest):
    """Store a key-value pair"""
    if request.node_address not in active_nodes:
        raise HTTPException(status_code=404, detail=f"Node {request.node_address} not found")
    
    try:
        node = active_nodes[request.node_address]["node"]
        
        if not node.running:
            raise Exception(f"Node {request.node_address} is not running")
        
        from src.utils import hash_key
        key_hash = hash_key(request.key)
        
        loop = asyncio.get_event_loop()
        responsible_node_info = await loop.run_in_executor(None, node.find_successor, key_hash)
        
        success = await loop.run_in_executor(None, node.put, request.key, request.value)
        
        if success:
            responsible_id = responsible_node_info.id % 10000 if responsible_node_info else "?"
            replication_factor = getattr(node, 'replication_factor', 1)
            
            await broadcast_log(
                f"PUT '{request.key}' = '{request.value}' → Primary: Node {responsible_id} (+ {replication_factor-1} replicas)", 
                "success"
            )
            
            await broadcast_nodes_update()
            
            return {
                "status": "success", 
                "message": f"Key '{request.key}' stored with {replication_factor}x replication",
                "stored_on": responsible_node_info.address if responsible_node_info else "Unknown",
                "replication_factor": replication_factor
            }
        else:
            await broadcast_log(f"Failed to PUT '{request.key}'", "error")
            return {"status": "error", "message": "Failed to store key"}
    except Exception as e:
        logger.error(f"Error in PUT operation: {e}")
        await broadcast_log(f"Error: {str(e)}", "error")
        return {"status": "error", "message": str(e)}

@app.get("/api/get")
async def get_key(key: str, node_address: str):
    """Retrieve a value by key"""
    if node_address not in active_nodes:
        raise HTTPException(status_code=404, detail=f"Node {node_address} not found")
    
    try:
        node = active_nodes[node_address]["node"]
        
        if not node.running:
            raise Exception(f"Node {node_address} is not running")
        
        # Calculate which node should have this key
        from src.utils import hash_key
        key_hash = hash_key(key)
        
        loop = asyncio.get_event_loop()
        responsible_node_info = await loop.run_in_executor(None, node.find_successor, key_hash)
        responsible_id = responsible_node_info.id % 10000 if responsible_node_info else "?"
        responsible_address = responsible_node_info.address if responsible_node_info else "Unknown"
        
        value = await loop.run_in_executor(None, node.get, key)
        
        if value is not None:
            await broadcast_log(
                f"GET '{key}' = '{value}' → From Node {responsible_id} ({responsible_address})", 
                "success"
            )
            return {"status": "success", "value": value}
        else:
            await broadcast_log(f"Key '{key}' not found", "error")
            return {"status": "error", "message": "Key not found"}
    except grpc.RpcError as e:
        error_msg = f"gRPC error: {e.details()}"
        logger.error(f"Error in GET operation: {error_msg}")
        await broadcast_log("Connection error: Node might be down", "error")
        return {"status": "error", "message": f"Connection error: {error_msg}"}
    except Exception as e:
        logger.error(f"Error in GET operation: {e}")
        await broadcast_log(f"Error: {str(e)}", "error")
        return {"status": "error", "message": str(e)}


@app.delete("/api/delete")
async def delete_key(request: KeyRequest):
    """Delete a key"""
    if request.node_address not in active_nodes:
        raise HTTPException(status_code=404, detail=f"Node {request.node_address} not found")
    
    try:
        node = active_nodes[request.node_address]["node"]
        
        if not node.running:
            raise Exception(f"Node {request.node_address} is not running")
        
        # Calculate which node has this key
        from src.utils import hash_key
        key_hash = hash_key(request.key)
        
        loop = asyncio.get_event_loop()
        responsible_node_info = await loop.run_in_executor(None, node.find_successor, key_hash)
        responsible_id = responsible_node_info.id % 10000 if responsible_node_info else "?"
        responsible_address = responsible_node_info.address if responsible_node_info else "Unknown"
        
        found = await loop.run_in_executor(None, node.delete, request.key)
        
        if found:
            await broadcast_log(
                f"DELETE '{request.key}' → Removed from Node {responsible_id} ({responsible_address})", 
                "success"
            )
            # Trigger nodes update to refresh key counts
            await broadcast_nodes_update()
            return {"status": "success", "message": f"Key '{request.key}' deleted"}
        else:
            await broadcast_log(f"Key '{request.key}' not found", "error")
            return {"status": "error", "message": "Key not found"}
    except grpc.RpcError as e:
        error_msg = f"gRPC error: {e.details()}"
        logger.error(f"Error in DELETE operation: {error_msg}")
        await broadcast_log("Connection error: Node might be down", "error")
        return {"status": "error", "message": f"Connection error: {error_msg}"}
    except Exception as e:
        logger.error(f"Error in DELETE operation: {e}")
        await broadcast_log(f"Error: {str(e)}", "error")
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)