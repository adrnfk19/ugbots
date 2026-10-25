import sys, time
from ugot import ugot

got = ugot.UGOT()
got.initialize(sys.argv[1])

for m in [11, 31, 41, 61]:
    print("Spinning motor", m)
    got.turn_motor_speed(m, 50)
    time.sleep(2)
    got.stop_motor(m)
    time.sleep(1)