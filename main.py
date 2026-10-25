import sys
from ugot import ugot

# Usage: python main.py [ROBOT_IP]  (no IP -> scan the LAN and pick the first robot)
got = ugot.UGOT()
ip = sys.argv[1] if len(sys.argv) > 1 else None
if ip is None:
    devices = got.scan_device()
    print("Found:", devices)
    if not devices:
        sys.exit("No UGOT found - same Wi-Fi as the robot?")
    ip = next(iter(devices.values()))

got.initialize(ip)
got.play_audio_tts("connected", 0, True)
