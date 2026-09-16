#!/usr/bin/env python3
"""
Lê a saída serial do ESP32 por N segundos e imprime tudo que receber.
Útil para validar a telemetria de circuitos sem precisar de terminal interativo.
"""
import serial
import sys
import time
import argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', default='/dev/ttyUSB0')
    ap.add_argument('--baud', type=int, default=115200)
    ap.add_argument('--seconds', type=int, default=8)
    args = ap.parse_args()

    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except serial.SerialException as e:
        print(f"[ERR] {e}", file=sys.stderr)
        sys.exit(1)

    # Reset do ESP32 via DTR toggle (o chip usa auto-reset)
    ser.dtr = False
    time.sleep(0.1)
    ser.dtr = True
    time.sleep(0.1)
    ser.reset_input_buffer()

    print(f"[INFO] Lendo {args.port} por {args.seconds}s a {args.baud} baud...")
    start = time.time()
    try:
        while time.time() - start < args.seconds:
            data = ser.read(256)
            if data:
                sys.stdout.write(data.decode('utf-8', errors='replace'))
                sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        ser.close()
    print("\n[INFO] Fim da leitura.")

if __name__ == '__main__':
    main()
