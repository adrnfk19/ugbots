# ugbots

UGOT robot code using the Python SDK (`ugot` on PyPI).

## Setup
Your laptop must be on the same Wi-Fi as the robot. Find the robot's IP on its controller under Settings → About.

### macOS / Linux / WSL
```bash
python3 -m venv .venv          # Ubuntu/WSL may need: sudo apt install python3-venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py sound-turn --ip 10.10.53.123   # --ip is required; see --help for tasks
```

### Windows (PowerShell)
Install Python 3.12 from python.org (tick "Add python.exe to PATH"), then:
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py sound-turn --ip 10.10.53.123   # --ip is required; see --help for tasks
```
If activation is blocked, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
In cmd.exe use `.venv\Scripts\activate.bat` instead.

Tip: with [uv](https://docs.astral.sh/uv/) installed, `uv venv` + `uv pip install -r requirements.txt` works on every OS.

## Workflow
- `main` stays runnable on the robot. Branch per feature: `git switch -c feat/line-follow`.
- Open a PR, a teammate tests it on the robot, then merge.
- Add new deps with a pinned version in `requirements.txt`.
