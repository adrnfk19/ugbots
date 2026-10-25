import sys, time
from ugot import ugot

got = ugot.UGOT()
got.initialize(sys.argv[1])
got.open_camera()
print("Model loaded", got.load_models(["apriltag_qrcode"]))
time.sleep(1)

for attempt in range(30):
    a = got.get_qrcode_total_info()
    b = got.get_qrcode_apriltag_total_info()
    print(attempt, "qrcode", a, "qrcode_apriltag", b)

    for result in (a, b):
        if result and result[0] and result[0][0]:
            text = result[0][0]
            print("Fragment", text)
            with open("fragment.txt", "w") as f:
                f.write(str(text))
            got.play_audio_tts("Evidence fragment recovered", 0, True)
            got.release_models(["apriltag_qrcode"])
            sys.exit()

    time.sleep(0.3)

print("No QR code found")
got.release_models(["apriltag_qrcode"])