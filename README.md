# ugbots

UGOT robot code using the Python SDK (`ugot` on PyPI).

## Setup
```bash
uv venv .venv && uv pip install --python .venv -r requirements.txt
# or: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt  (needs python3-venv)
source .venv/bin/activate
python main.py            # scans LAN for the robot
python main.py 192.168.x.x  # or connect by IP (shown in the robot's settings)
```
Your laptop must be on the same Wi-Fi as the robot.

## Workflow
- `main` stays runnable on the robot. Branch per feature: `git switch -c feat/line-follow`.
- Open a PR, a teammate tests it on the robot, then merge.
- Add new deps with a pinned version in `requirements.txt`.
