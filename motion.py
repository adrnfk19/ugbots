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

def turn_degrees(got, degrees, left, speed=40, timeout=5):
    """Spin in place until the IMU yaw has moved `degrees`, or `timeout` seconds pass."""
    prev = got.read_gyro_data()[2]
    turned = 0
    drive(got, -speed, speed) if left else drive(got, speed, -speed)
    end = time.time() + timeout  # in case the IMU stops reporting
    try:
        while abs(turned) < degrees and time.time() < end:
            yaw = got.read_gyro_data()[2]
            turned += (yaw - prev + 180) % 360 - 180  # step change, safe across the +-180 wrap
            prev = yaw
            time.sleep(0.02)
    finally:
        stop(got)
    return abs(turned)


if __name__ == "__main__":
    class FakeGot:  # yaw goes up 7 deg per read and wraps at 180, like the real IMU
        yaw = 170.0
        def turn_motor_speed(self, m, s): pass
        def stop_motor(self, m): pass
        def read_gyro_data(self):
            FakeGot.yaw = (FakeGot.yaw + 7 + 180) % 360 - 180
            return [0, 0, FakeGot.yaw]
    assert 90 <= turn_degrees(FakeGot(), 90, True) < 97
    print("ok")
