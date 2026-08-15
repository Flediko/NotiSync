import asyncio
import os
import socket
import subprocess
import sys
import threading
import time
import qrcode

# Configure stdout to support UTF-8 characters (like emojis and QR blocks) without crashing
sys.stdout.reconfigure(encoding='utf-8')

def get_local_ip():
    """Detects the computer's local network IP address."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not need to actually connect, just routes packets
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def print_qr_code(url: str):
    """Prints a beautiful text-based QR code in the terminal."""
    try:
        qr = qrcode.QRCode(border=1)
        qr.add_data(url)
        qr.make(fit=True)
        # print_ascii uses special unicode blocks to print a dense QR code in CLI
        qr.print_ascii()
    except Exception as e:
        print(f"Could not render QR code in terminal: {e}")

def run_ssh_tunnel():
    """Spawns the localhost.run SSH tunnel in a background thread and parses its output."""
    import re
    time.sleep(2) # Give uvicorn a moment to start up
    
    print("\n[Tunnel] Initializing secure internet tunnel via localhost.run...")
    # Command to request reverse port forwarding on port 80 to our local 8000
    cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-R", "80:127.0.0.1:8000", "nokey@localhost.run"]
    
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        
        # Pattern to match subdomains of lhr.life, lhr.rocks, or localhost.run
        # Must have a subdomain segment (e.g. subdomain.lhr.life)
        url_pattern = re.compile(r'\b([a-zA-Z0-9-]+\.(?:lhr\.life|lhr\.rocks|localhost\.run))\b')
        
        url_found = False
        for line in proc.stdout:
            line_str = line.strip()
            # print(f"[SSH DEBUG] {line_str}") # Uncomment for debugging
            
            if not url_found:
                match = url_pattern.search(line_str)
                if match:
                    domain = match.group(1).lower()
                    # Skip administrative/system domains
                    if domain not in ["localhost.run", "admin.localhost.run"]:
                        url = f"https://{domain}"
                        
                        print("\n" + "="*60)
                        print("🎉 NOTISYNC REMOTE MODE ACTIVE 🎉")
                        print("="*60)
                        print(f"Public URL: {url}")
                        print("Scan the QR code below on your phone to connect from college:")
                        print("-" * 60)
                        print_qr_code(url)
                        print("="*60 + "\n")
                        
                        url_found = True
            
            # Print other tunnel information (like connection status) to console
            if not url_found and "Welcome to" not in line_str and "To set up" not in line_str and "More details" not in line_str:
                if line_str:
                    print(f"[Tunnel] {line_str}")
                    
    except Exception as e:
        print(f"\n[Tunnel Error] Failed to start SSH tunnel: {e}")

def main():
    print("="*60)
    print("         NotiSync - Notification Sync Service")
    print("="*60)
    
    local_ip = get_local_ip()
    local_url = f"http://{local_ip}:8000"
    
    print("\nSelect Connection Mode:")
    print("1. Local Network Mode (Fast, private, devices must be on same Wi-Fi)")
    print("2. Internet Remote Mode (Access from anywhere, e.g. at college)")
    
    try:
        choice = input("\nEnter choice [1 or 2, default=1]: ").strip()
    except (KeyboardInterrupt, SystemExit):
        print("\nExiting...")
        return
        
    if choice == "2":
        mode = "internet"
    else:
        mode = "local"
        
    print(f"\nSelected Mode: {mode.upper()}")
    
    if mode == "local":
        print("\n" + "="*60)
        print("🎉 NOTISYNC LOCAL MODE ACTIVE 🎉")
        print("="*60)
        print(f"Local URL: {local_url}")
        print("Scan this QR code with your phone (must be on the same Wi-Fi):")
        print("-" * 60)
        print_qr_code(local_url)
        print("="*60 + "\n")
    else:
        # Start SSH tunnel in a separate background thread
        tunnel_thread = threading.Thread(target=run_ssh_tunnel, daemon=True)
        tunnel_thread.start()
        
    # Start the FastAPI server using uvicorn
    # Import uvicorn locally to avoid import errors if uvicorn is not fully set up yet
    import uvicorn
    
    print("Starting FastAPI notification server...")
    # Bind to 0.0.0.0 so both localhost, local IP, and the SSH tunnel can reach it
    uvicorn.run("main:app", host="0.0.0.0", port=8000, log_level="warning")

if __name__ == "__main__":
    main()
