import argparse
import time

import cv2
import numpy as np
import base64

_last_camera_request = 0.0
from ugot import ugot


# ---------- Settings ----------
BLACK_THRESHOLD = 60       # Adjust using the debug window slider.
FORWARD_SPEED = 8         # cm/s; mecanum configuration only.
STEERING_GAIN = 40        # degrees/s per unit of normalised error.
MAX_TURN_SPEED = 30       # degrees/s.
MIN_TAPE_AREA = 30        # Reject small specks in the detection strip.

# Top-down output: matches a 40 cm wide × 60 cm long floor rectangle.
# Change the ratio if your physical rectangle has different proportions.
W, H = 400, 600

parser = argparse.ArgumentParser()
parser.add_argument("ip", help="Robot IP address")
parser.add_argument("--servo-id", type=int, required=True,
                    help="Camera tilt servo ID")
parser.add_argument("--drive", action="store_true",
                    help="Enable mecanum motion; otherwise debug only")
args = parser.parse_args()

robot = ugot.UGOT()


# def get_frame():
#     """UGOT returns encoded image bytes; decode them into an OpenCV image."""
#     data = robot.read_camera_data()
#     if not data:
#         return None
#     return cv2.imdecode(
#         np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR
#     )

def get_frame():
    global _last_camera_request

    # Limit requests to approximately 10 FPS.
    delay = 0.1 - (time.monotonic() - _last_camera_request)
    if delay > 0:
        time.sleep(delay)

    _last_camera_request = time.monotonic()

    # Internal SDK interface: used here to inspect the response.
    response = robot.VISION.readCameraData()

    if response.code != 0 or response.nDataLen <= 0:
        print(
            f"Camera: code={response.code}, "
            f"data_length={response.nDataLen}",
            flush=True,
        )
        return None

    image_bytes = base64.b64decode(response.pdata)
    return cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    
def stop():
    """Only send chassis commands when motion was enabled."""
    if args.drive:
        robot.mecanum_stop()


def label(image, text):
    cv2.putText(
        image, text, (10, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2
    )


def adjust_camera():
    """Preview the camera and adjust the tilt before floor calibration."""
    angles = robot.read_servo_angle(args.servo_id)
    current = angles.get(str(args.servo_id))
    if current is None:
        raise RuntimeError("Cannot read servo angle. Check --servo-id.")

    angle = int(round(current))

    # Initial adjustment range around the current position.
    # Check that this range is mechanically clear on your assembled arm.
    minimum = max(-180, angle - 180)
    maximum = min(180, angle + 180)

    print("\nCAMERA: W/S = adjust 5 degrees, C = accept, Q = quit")
    print(f"Adjustment range: {minimum} to {maximum} degrees")
    cv2.namedWindow("Camera")

    while True:
        frame = get_frame()
        if frame is not None:
            preview = frame.copy()
            label(preview, f"Angle {angle} | W/S adjust | C accept | Q quit")
            cv2.imshow("Camera", preview)

        key = cv2.waitKey(30) & 0xFF
        
        # frame = get_frame()

        # if frame is not None:
        #  cv2.imshow("Camera", frame)

        # key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            raise KeyboardInterrupt

        if key == ord("c") and frame is not None:
            print(f"Selected servo angle: {angle}")
            time.sleep(0.5)
            return

        if key in (ord("w"), ord("s")):
            change = 5 if key == ord("w") else -5
            angle = int(np.clip(angle + change, minimum, maximum))
            robot.turn_servo_angle(
                args.servo_id, angle, 300, wait=True
            )
            time.sleep(0.2)



def calibrate_floor():
    """Map four corners of a floor rectangle into a top-down view."""
    frame = get_frame()
    if frame is None:
        raise RuntimeError("No camera frame available for calibration.")

    points = []

    def on_click(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            points.append((x, y))

    cv2.namedWindow("Calibration")
    cv2.setMouseCallback("Calibration", on_click)

    print("\nCALIBRATION: click the floor rectangle corners in this order:")
    print("1 far-left, 2 far-right, 3 near-right, 4 near-left")
    print("R = reset clicks, C = confirm four points, Q = quit")

    while True:
        preview = frame.copy()
        for i, point in enumerate(points):
            cv2.circle(preview, point, 5, (0, 0, 255), -1)
            cv2.putText(
                preview, str(i + 1), (point[0] + 8, point[1]),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2
            )

        label(preview, "Click corners | R reset | C confirm | Q quit")
        cv2.imshow("Calibration", preview)

        key = cv2.waitKey(20) & 0xFF
        if key == ord("q"):
            raise KeyboardInterrupt
        if key == ord("r"):
            points.clear()
        if key == ord("c") and len(points) == 4:
            break

    source = np.float32(points)
    destination = np.float32([
        [0, 0], [W - 1, 0], [W - 1, H - 1], [0, H - 1]
    ])

    if abs(cv2.contourArea(source)) < 100:
        raise RuntimeError("Invalid calibration: corners are too close.")

    cv2.destroyWindow("Calibration")
    return cv2.getPerspectiveTransform(source, destination)


def follow_tape(transform):
    """Display detection and optionally follow the tape."""
    cv2.namedWindow("Black mask")
    cv2.createTrackbar(
        "Threshold", "Black mask", BLACK_THRESHOLD, 255, lambda _: None
    )

    # Space toggles movement. Start paused even with --drive.
    running = False
    y0, y1 = int(H * 0.60), int(H * 0.70)

    print("\nRUN: Space = start/pause, Q = quit")
    print("Tune Threshold until only the tape appears white.")
    print("Motion enabled:", args.drive)

    while True:
        frame = get_frame()

        if frame is None:
            stop()
            running = False
            print("Camera frame missing: paused.")
            key = cv2.waitKey(30) & 0xFF
            if key == ord("q"):
                break
            continue

        # Convert the floor view into a top-down image.
        top = cv2.warpPerspective(frame, transform, (W, H))
        gray = cv2.cvtColor(top, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)

        threshold = cv2.getTrackbarPos("Threshold", "Black mask")
        _, mask = cv2.threshold(
            gray, threshold, 255, cv2.THRESH_BINARY_INV
        )

        # Detect tape only in a narrow look-ahead strip.
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
                    cx = moments["m10"] / moments["m00"]

                    # Negative = tape left; positive = tape right.
                    error = (cx - (W - 1) / 2) / ((W - 1) / 2)
                    cv2.circle(
                        top, (int(cx), (y0 + y1) // 2),
                        6, (0, 0, 255), -1
                    )

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        if key == ord(" "):
            running = not running

        # Stop and require another Space press if the tape disappears.
        if error is None:
            stop()
            running = False
            status = "TAPE LOST - paused"
        else:
            status = f"Error {error:+.2f} | {'RUN' if running else 'PAUSED'}"

            if args.drive and running:
                turn_rate = float(np.clip(
                    STEERING_GAIN * error,
                    -MAX_TURN_SPEED, MAX_TURN_SPEED
                ))

                if abs(turn_rate) < 5:
                    robot.mecanum_move_speed(0, FORWARD_SPEED)
                else:
                    # 2 = left, 3 = right; translation angle 0 = forward.
                    robot.mecanum_move_turn(
                        0, FORWARD_SPEED,
                        3 if turn_rate > 0 else 2,
                        int(round(abs(turn_rate)))
                    )
            else:
                stop()

        # Debug overlays are drawn after image processing.
        cv2.rectangle(top, (0, y0), (W - 1, y1), (0, 255, 0), 2)
        cv2.line(top, (W // 2, 0), (W // 2, H - 1), (255, 0, 0), 1)

        preview = frame.copy()
        label(preview, status + " | Space start/pause | Q quit")
        cv2.imshow("Camera", preview)
        cv2.imshow("Top-down path", top)
        cv2.imshow("Black mask", mask)


try:
    robot.initialize(args.ip)
    print(robot.get_peripheral_devices_list())
    stop()
    robot.open_camera()

    adjust_camera()
    floor_transform = calibrate_floor()
    follow_tape(floor_transform)

except KeyboardInterrupt:
    print("\nStopped.")
finally:
    try:
        stop()
    finally:
        cv2.destroyAllWindows()
