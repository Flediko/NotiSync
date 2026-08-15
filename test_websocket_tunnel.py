import asyncio
import re
import subprocess
import threading
import time
import websockets
import uvicorn
from main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="warning")

async def test_tunnel():
    print("Starting uvicorn server...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2) # Let server start
    
    print("Starting SSH tunnel...")
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:8000", "nokey@localhost.run"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    
    url_pattern = re.compile(r'\b([a-zA-Z0-9-]+\.(?:lhr\.life|lhr\.rocks|localhost\.run))\b')
    public_url = None
    
    # Wait for tunnel URL
    for line in proc.stdout:
        line_str = line.strip()
        print(f"[Tunnel Log] {line_str}")
        match = url_pattern.search(line_str)
        if match:
            domain = match.group(1).lower()
            if domain not in ["localhost.run", "admin.localhost.run"]:
                public_url = f"wss://{domain}/ws"
                break
                
    if not public_url:
        print("Failed to get public tunnel URL.")
        proc.terminate()
        return
        
    print(f"Testing WebSocket connection to: {public_url}")
    time.sleep(2) # Give tunnel a moment to stabilize
    
    try:
        # Try to connect via external WebSocket protocol
        async with websockets.connect(public_url, close_timeout=5) as ws:
            print("Successfully connected to public WebSocket!")
            # Receive the sync message
            msg = await ws.recv()
            print(f"Received initial sync message: {msg[:100]}...")
            print("TEST SUCCESSFUL!")
    except Exception as e:
        print(f"WebSocket test failed: {e}")
    finally:
        proc.terminate()

if __name__ == "__main__":
    asyncio.run(test_tunnel())
