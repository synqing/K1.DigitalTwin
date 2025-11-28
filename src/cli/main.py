import argparse
import time
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sim.core import TwinEngine


def cmd_state(engine: TwinEngine):
    engine.load_assets()
    s = engine.state()
    print("status: ok")
    print(f"assets: {s['assets']}")
    print(f"tick: {s['tick']}")


def cmd_run(engine: TwinEngine, ticks: int, interval: float):
    engine.load_assets()
    for _ in range(ticks):
        engine.tick()
        time.sleep(interval)
    s = engine.state()
    print(f"done ticks: {ticks}")
    print(f"assets: {s['assets']}")
    print(f"tick: {s['tick']}")


def main():
    parser = argparse.ArgumentParser(prog="k1-dt", description="K1 Digital Twin CLI")
    sub = parser.add_subparsers(dest="cmd")

    st = sub.add_parser("state", help="Show current twin state")

    rn = sub.add_parser("run", help="Advance simulation ticks")
    rn.add_argument("ticks", type=int, nargs="?", default=10)
    rn.add_argument("--interval", type=float, default=0.2)

    args = parser.parse_args()
    engine = TwinEngine()

    if args.cmd == "run":
        cmd_run(engine, args.ticks, args.interval)
    else:
        cmd_state(engine)


if __name__ == "__main__":
    main()
