#!/bin/bash

SCRIPT_PATH="/usr/share/kali-themes/xfce4-panel-genmon-vpnip.sh"

echo "[*] Installing VPN IP panel script..."

sudo tee "$SCRIPT_PATH" > /dev/null << 'EOF'
#!/bin/bash

interface="$(ip tuntap show | cut -d : -f1 | head -n 1)"
ip="$(ip -4 a show "${interface}" 2>/dev/null \
      | grep -oP '(?<=inet\s)\d+(\.\d+){3}')"

if [ -n "$ip" ]; then
    echo "<icon>network-vpn-symbolic</icon>"
    echo "<txt>$ip</txt>"
    echo "<tool>VPN IP</tool>"
else
    echo "<txt></txt>"
fi
EOF

sudo chmod +x "$SCRIPT_PATH"

echo "[+] Installed successfully at:"
echo "    $SCRIPT_PATH"
echo ""
echo "Next step: Add 'Generic Monitor' in the XFCE panel and set the command to:"
echo "    $SCRIPT_PATH"
