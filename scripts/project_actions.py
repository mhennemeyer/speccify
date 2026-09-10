"""Small, explicit local actions for demonstrating this repository in Speccify."""

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def chart_demo():
    print("SHA-256 im RAM: 6 echte Messungen; Einheit MiB/s, kein App-Profiling.", flush=True)
    payload = b"s" * (1024 * 1024)
    points = []
    for sample in range(1, 7):
        started = time.perf_counter()
        for _ in range(128):
            hashlib.sha256(payload).digest()
        elapsed = time.perf_counter() - started
        rate = round(128 / elapsed, 1)
        points.append([sample, rate])
        print(f"[{sample}/6] SHA-256: {rate} MiB/s", flush=True)
        print(
            json.dumps(
                {
                    "kind": "chart",
                    "mark": "line",
                    "height": 160,
                    "series": [{"name": "SHA-256 (MiB/s)", "points": points}],
                }
            ),
            flush=True,
        )
        time.sleep(0.3)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "quick-tests",
            "desktop-tests",
            "typecheck",
            "git-status",
            "chart-demo",
        ],
    )
    args = parser.parse_args()
    os.chdir(ROOT)
    if args.action == "chart-demo":
        return chart_demo()

    # Native app launches need not inherit an interactive shell's toolchain PATH.
    extra_paths = [
        "/opt/homebrew/opt/rustup/bin",
        str(Path.home() / ".cargo/bin"),
        "/opt/homebrew/bin",
        "/usr/local/bin",
    ]
    os.environ["PATH"] = os.pathsep.join(extra_paths + [os.environ.get("PATH", "")])
    commands = {
        "quick-tests": [sys.executable, "-u", "scripts/test_dev_runtime.py", "-v"],
        "desktop-tests": ["cargo", "test", "-p", "speccify-desktop"],
        "typecheck": ["pnpm", "--filter", "speccify-desktop", "typecheck"],
        "git-status": ["git", "--no-pager", "status", "--short", "--branch"],
    }
    command = commands[args.action]
    program = shutil.which(command[0])
    if not program:
        print(f"Fehlt: {command[0]}. Bitte die Projektumgebung einrichten.", file=sys.stderr)
        return 1
    print(f"Projekt: {ROOT}\nStart: {' '.join(command)}", flush=True)
    # Replace the launcher so the app's Stop button controls the actual command.
    os.execv(program, command)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
