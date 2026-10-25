import sys, time
from ugot import ugot

got = ugot.UGOT()
got.initialize(sys.argv[1])
got.open_camera()
time.sleep(1)                  # let the camera warm up

frame = got.read_camera_data()
print("Type", type(frame))

if isinstance(frame, (bytes, bytearray)):
    with open("photo.jpg", "wb") as f:
        f.write(frame)
    print("Saved photo.jpg")
else:
    print("Unexpected format", str(frame)[:200])