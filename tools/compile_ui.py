#!/usr/bin/env python3
import os
import subprocess
import sys


def main() -> int:
    root = os.path.dirname(os.path.dirname(__file__))
    ui_src = os.path.join(root, "src", "optical_drawing", "ui", "resources", "ui")
    ui_out = os.path.join(root, "src", "optical_drawing", "ui", "resources", "gen")
    os.makedirs(ui_out, exist_ok=True)

    if not os.path.isdir(ui_src):
        print(f"No ui dir: {ui_src}")
        return 0

    rc = 0
    for dirpath, _dirnames, filenames in os.walk(ui_src):
        for fn in filenames:
            if not fn.endswith(".ui"):
                continue
            src = os.path.join(dirpath, fn)
            base = os.path.splitext(fn)[0]
            dst = os.path.join(ui_out, f"ui_{base}.py")
            cmd = [sys.executable, "-m", "PyQt6.uic.pyuic", src, "-o", dst]
            print(" ".join(cmd))
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                print(f"pyuic6 failed for {src}: {e}")
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
