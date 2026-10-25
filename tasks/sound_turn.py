import time

import motion

TURN_LEFT, TURN_RIGHT = 2, 3  # E_Model.Direction values


def turn_for(angle):
    """Mic-array angle (90 = front, 180 = left, counter-clockwise) -> (direction, degrees)."""
    delta = (angle - 90 + 180) % 360 - 180  # -180..180, positive = sound is to the left
    return (TURN_LEFT if delta > 0 else TURN_RIGHT), abs(delta)


def report(got):
    """Say and print battery % and tilt (pitch/roll from the IMU)."""
    power = got.get_power_status()  # [percent, plugged, status] or None
    pitch, roll = got.read_gyro_data()[:2]
    battery = f"battery {power[0]} percent" if power else "battery unknown"
    msg = f"{battery}, pitch {round(pitch)} degrees, roll {round(roll)} degrees"
    print(msg)
    got.play_audio_tts(msg, 0, True)


def run(got, speed=40, min_angle=15, cooldown=1.0):
    """Turn to face any voice or clap, then report battery and tilt, forever. Ctrl+C to stop."""
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
                    seconds = degrees / (motion.DEG_PER_SEC * speed / 40)
                    (motion.turn_left if direction == TURN_LEFT else motion.turn_right)(got, seconds, speed)
                report(got)
                time.sleep(cooldown)  # so motor/TTS noise isn't heard as a new sound
            time.sleep(0.1)
    finally:
        motion.stop(got)
        got.disable_audio_direction()


if __name__ == "__main__":
    assert turn_for(90) == (TURN_RIGHT, 0)
    assert turn_for(180) == (TURN_LEFT, 90)
    assert turn_for(0) == (TURN_RIGHT, 90)
    assert turn_for(270) == (TURN_RIGHT, 180)
    assert turn_for(300) == (TURN_RIGHT, 150)
    print("ok")
