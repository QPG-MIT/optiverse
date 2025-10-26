#!/usr/bin/env python3
import os
import subprocess
import sys


def main() -> int:
    root = os.path.dirname(os.path.dirname(__file__))
    res_src = os.path.join(root, "src", "optical_drawing", "ui", "resources")
    gen_out = os.path.join(res_src, "gen")
    os.makedirs(gen_out, exist_ok=True)

    rc = 0
    for dirpath, _dirnames, filenames in os.walk(res_src):
        for fn in filenames:
            if not fn.endswith(".qrc"):
                continue
            src = os.path.join(dirpath, fn)
            base = os.path.splitext(fn)[0]
            dst = os.path.join(gen_out, f"rc_{base}.py")
            cmd = ["pyrcc6", src, "-o", dst]
            print(" ".join(cmd))
            try:
                subprocess.check_call(cmd)
            except subprocess.CalledProcessError as e:
                print(f"pyrcc6 failed for {src}: {e}")
                rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())


