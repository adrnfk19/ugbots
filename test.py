import os
import sys

from ugot import ugot

got = ugot.UGOT()

ip = sys.argv[1] if len(sys.argv) > 1 else None

if ip is None:
    devices = got.scan_device()
    print("Found:", devices)

    if not devices:
        sys.exit("No UGOT found — check the robot and laptop network.")

    ip = next(iter(devices.values()))

ip = str(ip).strip()
os.environ["no_grpc_proxy"] = ip

print(f"Connecting to robot: {ip}")
got.initialize(ip)

got.play_audio_tts("Team Jellyfish", 0, True)
