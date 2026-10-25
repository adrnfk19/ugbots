import time

TURN_LEFT, TURN_RIGHT, DEGREES = 2, 3, 2  # E_Model.Direction / E_Model.Unit values


def turn_for(angle):
    """Mic-array angle (90 = front, 180 = left, counter-clockwise) -> (direction, degrees)."""
    delta = (angle - 90 + 180) % 360 - 180  # -180..180, positive = sound is to the left
    return (TURN_LEFT if delta > 0 else TURN_RIGHT), abs(delta)


def run(got, chassis="mecanum", speed=90, min_angle=15, cooldown=1.0):
    """Turn to face any voice or clap, forever. Ctrl+C to stop."""
    turn = getattr(got, f"{chassis}_turn_speed_times")
    got.enable_audio_direction()
    print("Listening - clap or talk...")
    try:
        while True:
            # Raw angle instead of get_audio_direction(), which only returns Front/Left/Right/Back.
            res = got.AUDIO.getDirectionOfAudio()
            if res.code == 0 and res.angle != -1:
                direction, degrees = turn_for(res.angle)
                print(f"Sound at {res.angle} deg -> turn {'left' if direction == TURN_LEFT else 'right'} {degrees}")
                if degrees >= min_angle:
                    turn(direction, speed, degrees, DEGREES)
                    time.sleep(degrees / speed)  # let the turn finish
                time.sleep(cooldown)  # so motor noise isn't heard as a new sound
            time.sleep(0.1)
    finally:
        getattr(got, f"{chassis}_stop")()
        got.disable_audio_direction()


if __name__ == "__main__":
    assert turn_for(90) == (TURN_RIGHT, 0)
    assert turn_for(180) == (TURN_LEFT, 90)
    assert turn_for(0) == (TURN_RIGHT, 90)
    assert turn_for(270) == (TURN_RIGHT, 180)
    assert turn_for(300) == (TURN_RIGHT, 150)
    print("ok")
