import time

LEFT_MOTORS = [11, 31]
RIGHT_MOTORS = [41, 61]
LEFT_SIGN = -1
RIGHT_SIGN = 1

def drive(got, left_speed, right_speed):
    for m in LEFT_MOTORS:
        got.turn_motor_speed(m, LEFT_SIGN * left_speed)
    for m in RIGHT_MOTORS:
        got.turn_motor_speed(m, RIGHT_SIGN * right_speed)

def stop(got):
    for m in LEFT_MOTORS + RIGHT_MOTORS:
        got.stop_motor(m)

def forward(got, seconds, speed=40):
    drive(got, speed, speed)
    time.sleep(seconds)
    stop(got)

def turn_left(got, seconds, speed=40):
    drive(got, -speed, speed)
    time.sleep(seconds)
    stop(got)

def turn_right(got, seconds, speed=40):
    drive(got, speed, -speed)
    time.sleep(seconds)
    stop(got)