import time

import motion

# shortcut: unmeasured guesses; flip OFFSET_SIGN if it steers away from the line, raise KP if it drifts off on curves.
KP = 0.05         # speed difference per unit of offset
OFFSET_SIGN = 1   # assumes positive offset = line is to the right


def steer(offset, speed, kp=KP):
    """Track offset -> (left_speed, right_speed), clamped to the motor range."""
    turn = OFFSET_SIGN * kp * offset
    clamp = lambda v: max(-140, min(140, round(v)))
    return clamp(speed + turn), clamp(speed - turn)


def run(got, speed=40):
    """Follow a single line with the camera, forever. Ctrl+C to stop."""
    got.open_camera()
    print("Model loaded", got.load_models(["line_recognition"]))
    got.set_track_recognition_line(0)  # 0 = single track
    try:
        while True:
            offset, line_type, _, _ = got.get_single_track_total_info()
            if line_type == 0:  # no line seen
                motion.stop(got)
            else:
                motion.drive(got, *steer(offset, speed))
            time.sleep(0.05)
    finally:
        motion.stop(got)
        got.release_models(["line_recognition"])


if __name__ == "__main__":
    assert steer(0, 40) == (40, 40)
    assert steer(100, 40) == (55, 25)
    assert steer(-100, 40) == (25, 55)
    assert steer(10000, 40) == (140, -140)
    print("ok")
