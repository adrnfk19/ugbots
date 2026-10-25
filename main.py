import argparse
from ugot import ugot
from tasks import sound_turn


def hello(got, args):
    got.play_audio_tts("Team Jellyfish", 0, True)


# Add new tasks here: name -> function(got, args)
TASKS = {
    "hello": hello,
    "sound-turn": lambda got, a: sound_turn.run(got, a.speed),
}

p = argparse.ArgumentParser(description="Run a UGOT task")
p.add_argument("task", choices=TASKS)
p.add_argument("--ip", required=True, help="robot IP, from its controller: Settings -> About")
p.add_argument("--speed", type=int, default=40, help="motor speed while turning, 1-140")
args = p.parse_args()

got = ugot.UGOT()
got.initialize(args.ip)
TASKS[args.task](got, args)
