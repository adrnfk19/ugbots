import argparse
import base64
import time

import cv2
import numpy as np
from ugot import ugot
import sys

# Stops the robot STOP_CM before a wall. Doesn't drive - movement is someone else's code.
# Check wall_ahead() every loop of your driving code (see drive_example.py):
#   import wall_stop
#   sensor_id = wall_stop.find_tof(got)
#   while True:
#       if wall_stop.wall_ahead(got, sensor_id):
#           wall_stop.stop_robot(got)
#           break
#       ... your driving code ...
STOP_CM = 25
PRESET_MODELS = ('mecanum', 'balance', 'transform', 'wheel_legged', 'spider', 'dog', 'engineer')


def find_tof(got):
    # The ToF distance sensor shows up as type 'Infrared' in the peripheral list (e.g. id 51)
    sensors = [d for d in got.get_peripheral_devices_list() if d['type'] == 'Infrared']
    if not sensors:
        sys.exit("No distance sensor found - is it plugged in?")
    return int(sensors[0]['deviceId'])


def wall_ahead(got, sensor_id, stop_cm=STOP_CM):
    distance = got.read_distance_data(sensor_id)
    # -1 / 0 mean no reading yet, not "touching the wall"
    return 0 < distance <= stop_cm


def stop_robot(got, motors=None):
    # Preset models stop through the chassis; custom builds ('box') stop every motor.
    # motors=None stops all motors on the robot.
    if got.DEVICE.getDeviceModel() in PRESET_MODELS:
        got.stop_chassis()
        return
    if motors is None:
        motors = [int(d['deviceId']) for d in got.get_peripheral_devices_list() if d['type'].lower() == 'motor']
    got.stop_motor(motors, lock=True)

# ---------------- Configuration ----------------
BLACK_THRESHOLD = 60
MIN_TAPE_AREA = 30          # Minimum contour area in pixels.
FORWARD_SPEED = 8          # cm/s; mecanum configuration.
STEERING_GAIN = 40         # degrees/s per unit of normalised error.
MAX_TURN_SPEED = 30        # degrees/s.
CAMERA_INTERVAL = 0.10     # Request at most approximately 10 FPS.

# Top-down image proportions.
# Use a floor rectangle with the same width:length ratio, e.g. 40 × 60 cm.
W, H = 400, 600

parser = argparse.ArgumentParser()
parser.add_argument("ip", help="Robot IP address")
parser.add_argument("--servo-id", type=int, required=True,
                    help="Camera tilt servo ID, e.g. 22")
parser.add_argument("--drive", action="store_true",
                    help="Enable mecanum wheel commands")
parser.add_argument("--step-cm", type=int, default=5,
                    help="Distance per movement step in cm (1-360; default 5)")
parser.add_argument("--pause-seconds", type=float, default=0.5,
                    help="Stopped settling time before the next photo (default 0.5)")
parser.add_argument("--skip-calibration", action="store_true",
                    help="Detect directly in the original camera image")
parser.add_argument("--servo-min", type=int,
                    help="Mechanically safe minimum servo angle")
parser.add_argument("--servo-max", type=int,
                    help="Mechanically safe maximum servo angle")
args = parser.parse_args()
if not 1 <= args.step_cm <= 360:
    parser.error("--step-cm must be between 1 and 360")
if not np.isfinite(args.pause_seconds) or args.pause_seconds < 0:
    parser.error("--pause-seconds must be a finite non-negative number")

robot = ugot.UGOT()
connected = False
last_camera_request = 0.0
last_camera_warning = 0.0


# ---------------- Camera access ----------------
def get_frame():
    """Return a decoded image, or None if the camera returns no image."""
    global last_camera_request, last_camera_warning

    delay = CAMERA_INTERVAL - (time.monotonic() - last_camera_request)
    if delay > 0:
        time.sleep(delay)

    last_camera_request = time.monotonic()

    # Internal interface exposes the status hidden by read_camera_data().
    response = robot.VISION.readCameraData()

    if response.code != 0 or response.nDataLen <= 0:
        # Avoid flooding the terminal.
        now = time.monotonic()
        if now - last_camera_warning >= 1.0:
            print(
                f"Camera: code={response.code}, "
                f"data_length={response.nDataLen}",
                flush=True,
            )
            last_camera_warning = now
        return None

    try:
        image_bytes = base64.b64decode(response.pdata)
    except (ValueError, TypeError):
        return None

    if not image_bytes:
        return None

    return cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )


def label(image, text):
    """Draw text on a debugging image."""
    cv2.putText(
        image, text, (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2,
    )


def missing_camera_view():
    """Show an explicit warning instead of leaving an old frame visible."""
    image = np.zeros((480, 640, 3), dtype=np.uint8)
    label(image, "No camera frame - paused | Q quit")
    return image


# ---------------- Servo adjustment ----------------
def adjust_camera():
    """Adjust camera tilt before calibration. Does not move the wheels."""
    angles = robot.read_servo_angle(args.servo_id)
    current = angles.get(str(args.servo_id))
    
  
    if current is None:
        raise RuntimeError(
            f"Cannot read servo {args.servo_id}. Check its device ID."
        )

    angle = int(round(current))

    # Default to a small range around the current position.
    # Override only with limits that are clear of the arm/body.
    minimum = (
        args.servo_min if args.servo_min is not None
        else max(-180, angle - 15)
    )
    maximum = (
        args.servo_max if args.servo_max is not None
        else min(180, angle + 15)
    )

    if not (-180 <= minimum <= angle <= maximum <= 180):
        raise ValueError(
            "Servo limits must be within [-180, 180] "
            "and contain the current angle."
        )

    print(f"\nServo {args.servo_id}: current angle {angle}")
    print(f"Adjustment limits: {minimum} to {maximum}")
    print("Click Camera window: W/S adjust, C accept, Q quit")

    
    robot.turn_servo_angle(22, -90, 500, wait=True)
    cv2.namedWindow("Camera")
    
   
    

    while True:
        frame = get_frame()

        if frame is None:
            preview = missing_camera_view()
        else:
            preview = frame.copy()
            label(preview, f"Servo {angle} deg | W/S adjust | C accept | Q quit")

        cv2.imshow("Camera", preview)
        key = cv2.waitKey(30) & 0xFF

        if key == ord("q"):
            raise KeyboardInterrupt

        if key == ord("c") and frame is not None:
            time.sleep(0.5)
            return

        if key in (ord("w"), ord("s")):
            change = 2 if key == ord("w") else -2
            target = int(np.clip(angle + change, minimum, maximum))

            if target != angle:
                robot.turn_servo_angle(
                    args.servo_id, target, 300, wait=True
                )
                angle = target
                time.sleep(0.2)


# ---------------- Floor calibration ----------------
def calibrate_floor():
    """
    Map a physical floor rectangle into a top-down image.
    The image intentionally freezes while selecting corners.
    """
    print("\nWaiting for a calibration image...")

    while True:
        frame = get_frame()
        if frame is not None:
            break

        cv2.imshow("Camera", missing_camera_view())
        if cv2.waitKey(30) & 0xFF == ord("q"):
            raise KeyboardInterrupt

    points = []

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow("Calibration")
    cv2.setMouseCallback("Calibration", on_click)

    print("Click: far-left, far-right, near-right, near-left.")
    print("C confirm | R reset | Q quit")
    print("Rectangle must be centred on and aligned with the robot.")

    while True:
        preview = frame.copy()

        for index, point in enumerate(points):
            cv2.circle(preview, point, 5, (0, 0, 255), -1)
            cv2.putText(
                preview, str(index + 1),
                (point[0] + 8, point[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2,
            )

        label(preview, "Frozen image | C confirm | R reset | Q quit")
        cv2.imshow("Calibration", preview)
        key = cv2.waitKey(20) & 0xFF

        if key == ord("q"):
            raise KeyboardInterrupt

        if key == ord("r"):
            points.clear()

        if key == ord("c") and len(points) == 4:
            source = np.float32(points)

            # Reject tiny, concave, or crossed quadrilaterals.
            if (
                abs(cv2.contourArea(source)) < 100
                or not cv2.isContourConvex(source)
            ):
                print("Invalid corners. Press R and select again.")
                continue

            destination = np.float32([
                [0, 0],
                [W - 1, 0],
                [W - 1, H - 1],
                [0, H - 1],
            ])

            transform = cv2.getPerspectiveTransform(source, destination)
            cv2.destroyWindow("Calibration")
            return transform


# ---------------- Perception: no motor commands ----------------
def detect_tape(frame, transform, threshold):
    """
    Return (error, debug_view, mask).

    error:
        Negative -> tape left.
        Positive -> tape right.
        None     -> no sufficiently large tape region detected.
    """
    view = (
        frame.copy() if transform is None
        else cv2.warpPerspective(frame, transform, (W, H))
    )

    height, width = view.shape[:2]
    reference_x = (width - 1) / 2

    gray = cv2.cvtColor(view, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # Pixels <= threshold become white; brighter pixels become black.
    _, mask = cv2.threshold(
        gray, threshold, 255, cv2.THRESH_BINARY_INV
    )

    # A horizontal look-ahead strip, below the image centre.
    y0, y1 = int(height * 0.60), int(height * 0.70)
    strip = mask[y0:y1, :]

    contours, _ = cv2.findContours(
        strip, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    error = None

    if contours:
        tape = max(contours, key=cv2.contourArea)

        if cv2.contourArea(tape) >= MIN_TAPE_AREA:
            moments = cv2.moments(tape)

            if moments["m00"] > 0:
                tape_x = moments["m10"] / moments["m00"]
                error = float((tape_x - reference_x) / reference_x)

                cv2.circle(
                    view, (int(tape_x), (y0 + y1) // 2),
                    6, (0, 0, 255), -1,
                )

    cv2.rectangle(
        view, (0, y0), (width - 1, y1), (0, 255, 0), 2
    )
    cv2.line(
        view, (int(reference_x), 0),
        (int(reference_x), height - 1), (255, 0, 0), 1,
    )

    return error, view, mask


# ---------------- Controller: no robot communication ----------------
def calculate_turn_rate(error):
    """Convert normalised tape error into signed turn rate."""
    if error is None:
        return None

    return float(np.clip(
        STEERING_GAIN * error,
        -MAX_TURN_SPEED,
        MAX_TURN_SPEED,
    ))


# ---------------- Actuation: motor commands only ----------------
LEFT_MOTORS = [11, 31]
RIGHT_MOTORS = [41, 61]
LEFT_SIGN = -1
RIGHT_SIGN = 1
# shortcut: unmeasured guess; time turn_left(got, 2) at speed 40 and set this to degrees turned / 2.
DEG_PER_SEC = 90  # at speed 40


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


def apply_motion(turn_rate, running):
    """Turn toward the tape, then move forward using timed motor commands."""
    if not args.drive:
        return
    if not running or turn_rate is None:
        stop(robot)
        return

    # Retain the existing step-duration estimate; actual distance needs calibration.
    forward_seconds = args.step_cm / FORWARD_SPEED
    turn_seconds = abs(turn_rate) * forward_seconds / DEG_PER_SEC

    try:
        # Negative tape error means left; positive tape error means right.
        if turn_rate <= -5:
            turn_left(robot, turn_seconds)
        elif turn_rate >= 5:
            turn_right(robot, turn_seconds)
        forward(robot, forward_seconds)
        
    finally:
        stop(robot)


def wait_phase(seconds):
    """Keep Q responsive during the waiting period."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        key = cv2.waitKey(20) & 0xFF
        if key == ord("q"):
            raise KeyboardInterrupt
    return True


def move_step(turn_rate):
    """Use one photo's steering for one bounded step, then always stop."""
    print(f"Step: {args.step_cm} cm | turn {turn_rate:+.1f} deg/s")
    try:
        apply_motion(turn_rate, True)
        # No camera reads while moving. Allow a small completion margin;
        # the firmware stops at mileage, and we explicitly stop afterwards.
        wait_phase(args.step_cm / FORWARD_SPEED + 0.5)
    finally:
        apply_motion(None, False)
    print("Stopped: settling before next photo.")
    return wait_phase(args.pause_seconds)


# ---------------- Main detection/control loop ----------------
def follow_tape(transform):
    """Photo -> recognise tape -> move one distance -> stop -> repeat."""
    cv2.namedWindow("Black mask")
    cv2.createTrackbar(
        "Threshold", "Black mask",
        BLACK_THRESHOLD, 255, lambda _: None,
    )

    running = args.drive
    apply_motion(None, False)

    print("Motion starts automatically after calibration when tape is detected.")
    print("Q = stop and quit")
    print(f"Photo -> move {args.step_cm} cm -> stop {args.pause_seconds:g}s -> repeat")
    if not args.drive:
        print("Preview only. Use --drive to enable movement.")

    try:
        while True:
            frame = get_frame()

            if frame is None:
                running = False
                apply_motion(None, False)

                cv2.imshow("Camera", missing_camera_view())
                if cv2.waitKey(30) & 0xFF == ord("q"):
                    break
                continue

            threshold = cv2.getTrackbarPos(
                "Threshold", "Black mask"
            )

            # Perception: locate tape and calculate lateral error.
            error, view, mask = detect_tape(
                frame, transform, threshold
            )

            # Controller: convert error into a turning command.
            turn_rate = calculate_turn_rate(error)

            running = args.drive and turn_rate is not None
            if error is None:
                apply_motion(None, False)

            if error is None:
                status = "TAPE LOST - stopped"
            else:
                mode = "STEP READY" if running else "PREVIEW"
                status = (
                    f"{mode} | error {error:+.2f} | "
                    f"turn {turn_rate:+.1f} deg/s"
                )

            preview = frame.copy()
            label(preview, status)
            label(view, "Q stop and quit")

            cv2.imshow("Camera", preview)
            cv2.imshow("Path detection", view)
            cv2.imshow("Black mask", mask)

            key = cv2.waitKey(1) & 0xFF

            if key == ord("q"):
                break

            if running:
                # The next iteration captures a fresh photo only after
                # this movement has stopped and the camera has settled.
                label(preview, f"STEP {args.step_cm} cm | Q quit")
                cv2.imshow("Camera", preview)
                running = move_step(turn_rate)

    finally:
        apply_motion(None, False)


# ---------------- Startup and cleanup ----------------
try:
    robot.initialize(args.ip)
    connected = True
    print(robot.get_peripheral_devices_list())

    apply_motion(None, False)

    robot.open_camera()
    print("Camera client ID:", robot.VISION.camera_client_id)

    adjust_camera()

    transform = (
        None if args.skip_calibration
        else calibrate_floor()
    )

    follow_tape(transform)

except KeyboardInterrupt:
    print("\nStopped.")

finally:
    try:
        if connected:
            apply_motion(None, False)
    finally:
        # Best-effort release of this program's camera session.
        try:
            if connected and robot.VISION.camera_client_id > 0:
                robot.VISION.closeCamera(robot.VISION.camera_client_id)
                robot.VISION.camera_client_id = 0
        except Exception as exc:
            print("Camera cleanup:", exc)

        cv2.destroyAllWindows()
