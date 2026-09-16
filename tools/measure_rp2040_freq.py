#!/usr/bin/env python3

import re
import sys
import time

try:
    import serial
except ImportError:
    print("pyserial is required", file=sys.stderr)
    sys.exit(1)


LINE_RE = re.compile(r"FREQ=(\d+)Hz")


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} /dev/ttyACM0", file=sys.stderr)
        return 2

    port = sys.argv[1]
    ser = serial.Serial(port, 115200, timeout=2)
    time.sleep(2)
    ser.reset_input_buffer()

    samples = []
    deadline = time.time() + 8.0
    while time.time() < deadline and len(samples) < 8:
        line = ser.readline().decode("utf-8", errors="replace").strip()
        if not line:
            continue
        m = LINE_RE.search(line)
        if m:
            samples.append(int(m.group(1)))
            print(line)

    ser.close()

    if samples:
        avg = sum(samples) / len(samples)
        print(f"AVG={avg:.1f}Hz N={len(samples)}")
        return 0

    print("no FREQ samples captured", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
