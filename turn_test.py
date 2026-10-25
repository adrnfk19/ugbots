import sys, time
from ugot import ugot

got = ugot.UGOT()
got.initialize(sys.argv[1])

print("Trying mecanum turn")
got.mecanum_turn_speed_times(2, 45, 45, 2)
time.sleep(2)

print("Trying balance turn")
got.balance_start_balancing()
time.sleep(2)
got.balance_turn_speed_times(2, 45, 45, 2)
time.sleep(2)

print("Trying universal move")
got.model_common_move(0, 40)
time.sleep(1.5)
got.model_common_move(0, 0)

print("Done")