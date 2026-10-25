import sys, time
from ugot import ugot
from motion import turn_left

TURN_SPEED = 40
TURN_TIME = 0.3     # tune so each step is about 20 degrees
STEPS = 18

got = ugot.UGOT()
got.initialize(sys.argv[1])
got.open_camera()
print("Model loaded", got.load_models(["apriltag_qrcode"]))
time.sleep(1)

def read_qr():
    for item in got.get_qrcode_total_info() or []:
        if item[0]:
            return item
    return None

found = None
for step in range(STEPS):
    print("Looking, step", step)
    for _ in range(5):
        found = read_qr()
        if found:
            break
        time.sleep(0.2)
    if found:
        break
    turn_left(got, TURN_TIME, TURN_SPEED)
    time.sleep(0.3)

if found:
    text = found[0]
    print("Fragment", text)
    with open("fragment.txt", "w") as f:
        f.write(text)
    got.play_audio_tts("Evidence fragment recovered", 0, True)
else:
    print("No QR code found")
    got.play_audio_tts("No marker found", 0, True)

got.release_models(["apriltag_qrcode"])