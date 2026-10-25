"""Exercise motion decisions without importing the script's robot startup."""
import ast
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class StepMotionTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path(__file__).with_name("follow_tape.py").read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"apply_motion", "move_step", "wait_phase"}]
        self.robot = Mock()
        self.robot.MODEL.mecanum_move_control.return_value.code = 0
        self.args = SimpleNamespace(drive=True, step_cm=5, pause_seconds=0.5)
        self.env = dict(robot=self.robot, args=self.args, FORWARD_SPEED=8,
                        time=Mock(), cv2=Mock())
        exec(compile(ast.Module(body=functions, type_ignores=[]), "motion", "exec"), self.env)

    def test_distance_and_steering_then_stop_before_settling(self):
        def wait(seconds):
            if seconds == self.args.pause_seconds:
                self.robot.mecanum_stop.assert_called_once()
            return True
        self.env["wait_phase"] = Mock(side_effect=wait)
        self.assertTrue(self.env["move_step"](12.0))
        self.robot.MODEL.mecanum_move_control.assert_called_once_with(
            linear_speed=8, direction=0, rotate_speed=-12, mileage=5)

    def test_preview_never_sends_motor_commands(self):
        self.args.drive = False
        self.env["apply_motion"](0, True)
        self.env["apply_motion"](None, False)
        self.assertEqual(self.robot.mock_calls, [])

    def test_paused_or_missing_detection_stops(self):
        self.env["apply_motion"](None, True)
        self.env["apply_motion"](10, False)
        self.assertEqual(self.robot.mecanum_stop.call_count, 2)
        self.robot.MODEL.mecanum_move_control.assert_not_called()

    def test_space_interrupts_step_and_stops(self):
        self.env["wait_phase"] = Mock(return_value=False)
        self.assertFalse(self.env["move_step"](0))
        self.robot.mecanum_stop.assert_called_once()
        self.env["wait_phase"].assert_called_once()

    def test_quit_stops_even_during_motion(self):
        self.env["wait_phase"] = Mock(side_effect=KeyboardInterrupt)
        with self.assertRaises(KeyboardInterrupt):
            self.env["move_step"](-10)
        self.robot.mecanum_stop.assert_called_once()

    def test_rejected_motion_stops_and_reports_failure(self):
        self.robot.MODEL.mecanum_move_control.return_value.code = -1
        with self.assertRaisesRegex(RuntimeError, "Movement rejected"):
            self.env["move_step"](0)
        self.robot.mecanum_stop.assert_called_once()

    def test_wait_checks_space_and_quit(self):
        for key in (ord(" "), ord("q")):
            self.env["time"].monotonic.side_effect = [0, 0]
            self.env["cv2"].waitKey.return_value = key
            if key == ord("q"):
                with self.assertRaises(KeyboardInterrupt):
                    self.env["wait_phase"](1)
            else:
                self.assertFalse(self.env["wait_phase"](1))


if __name__ == "__main__":
    unittest.main()
