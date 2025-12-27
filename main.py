#!/usr/bin/env python3
"""
Eltek Flatpack2 HE 2000 CAN Bus Controller for macOS (SLCAN only)
Supports setting live voltage/current and storing default voltage properly.
"""

import can
import time
import argparse
import sys

class EltekFlatpack:
    MIN_VOLTAGE = 43.5
    MAX_VOLTAGE = 57.4
    MAX_CURRENT = 41.7

    LOGIN_ID_BASE = 0x05004800
    CONTROL_ID_BASE = 0x05FF4000
    STATUS_ID_BASE = 0x05014000

    def __init__(self, channel='/dev/tty.usbserial-A10KHTR4', unit_id=1, serial_number=None):
        if unit_id < 1 or unit_id > 63:
            raise ValueError("Unit ID must be 1-63")
        self.unit_id = unit_id
        self.target_voltage = 48.0
        self.target_current = 40.0
        self.ovp_voltage = 59.5

        # Serial number for login
        if serial_number:
            self.set_serial_number(serial_number)
        else:
            print("Using default serial number 134372105069")
            self.login = bytes([0x13,0x43,0x72,0x10,0x50,0x69,0x00,0x00])

        # CAN IDs
        self.login_id = self.LOGIN_ID_BASE + (self.unit_id*4)
        self.control_id = self.CONTROL_ID_BASE + (self.unit_id*4)
        self.status_id1 = self.STATUS_ID_BASE + (self.unit_id*4)
        self.status_id2 = self.STATUS_ID_BASE + (self.unit_id*4)+4

        # Initialize SLCAN bus
        try:
            self.bus = can.interface.Bus(channel=channel, bustype='slcan', bitrate=125000)
            print(f"✓ SLCAN bus initialized on {channel}")
        except Exception as e:
            print(f"✗ CAN bus init failed: {e}")
            sys.exit(1)

        # Initial login
        self.send_login()
        time.sleep(0.2)

    def set_serial_number(self, serial):
        serial_str = str(serial).zfill(12)
        if len(serial_str) != 12:
            raise ValueError("Serial must be 12 digits")
        serial_bytes = [int(serial_str[i:i+2]) for i in range(0,12,2)]
        serial_bytes.extend([0x00,0x00])
        self.login = bytes(serial_bytes)
        print(f"Serial set: {serial_str}, bytes: {' '.join(f'0x{b:02X}' for b in self.login)}")

    def send_login(self):
        msg = can.Message(arbitration_id=self.login_id, data=self.login, is_extended_id=True)
        self.bus.send(msg)

    def set_voltage_and_current(self, volts=None, amps=None, ovp=None):
        if volts is not None:
            volts = max(self.MIN_VOLTAGE, min(volts, self.MAX_VOLTAGE))
            self.target_voltage = volts
        if amps is not None:
            amps = max(0, min(amps, self.MAX_CURRENT))
            self.target_current = amps
        if ovp is not None:
            self.ovp_voltage = ovp

        scaled_current = int(self.target_current * 10)  # 0.1A units
        scaled_voltage = int(self.target_voltage * 100)  # 0.01V units
        scaled_ovp = int(self.ovp_voltage * 100)

        data = bytearray([
            scaled_current & 0xFF, (scaled_current >> 8) & 0xFF,
            scaled_voltage & 0xFF, (scaled_voltage >> 8) & 0xFF,
            scaled_voltage & 0xFF, (scaled_voltage >> 8) & 0xFF,
            scaled_ovp & 0xFF, (scaled_ovp >> 8) & 0xFF
        ])

        msg = can.Message(arbitration_id=self.control_id, data=data, is_extended_id=True)
        self.bus.send(msg)
        print(f"→ Live set: {self.target_voltage:.2f}V, {self.target_current:.1f}A (OVP: {self.ovp_voltage:.1f}V)")

    def set_default_voltage(self, volts):
        """Send default voltage command (applied after logout/power cycle)"""
        volts = max(self.MIN_VOLTAGE, min(volts, self.MAX_VOLTAGE))
        centivolts = int(volts * 100)
        data = bytearray([0x29, 0x15, 0x00]) + centivolts.to_bytes(2, 'little')
        default_id = 0x05000000 | (self.unit_id << 16) | 0x9C00
        msg = can.Message(arbitration_id=default_id, data=data, is_extended_id=True)
        self.bus.send(msg)
        print(f"→ Default voltage command sent: {volts:.2f}V")
        print("⚠️  Note: This will take effect only after the Flatpack logs out or power-cycles.")

    def read_status(self, timeout=1.0):
        end = time.time() + timeout
        while time.time() < end:
            msg = self.bus.recv(timeout=0.1)
            if msg and msg.arbitration_id in [self.status_id1, self.status_id2]:
                print(msg.arbitration_id)
                d = msg.data
                temp = d[0]
                current = (d[2]*256 + d[1]) * 0.1
                voltage = (d[4]*256 + d[3]) * 0.01
                power = voltage * current
                input_v = d[5]
                flags = d[6] | (d[7]<<8)
                return {'temperature': temp, 'current': current, 'voltage': voltage,
                        'power': power, 'input_voltage': input_v,
                        'walk_in': bool(flags&0x01),
                        'float': bool(flags&0x02),
                        'error': bool(flags&0x04)}
        return None

    def monitor(self, duration=None):
        print("\nMonitoring Flatpack... Ctrl+C to stop")
        start=time.time()
        last_login=time.time()
        try:
            while True:
                if time.time()-last_login > 10:
                    self.send_login()
                    last_login=time.time()
                status=self.read_status(timeout=0.5)
                if status:
                    print(f"\r{status['voltage']:.2f}V {status['current']:.1f}A {status['temperature']}°C", end='')
                time.sleep(0.2)
                if duration and time.time()-start>duration: break
        except KeyboardInterrupt:
            print("\nStopped monitoring.")

    def close(self):
        self.bus.shutdown()
        print("CAN bus closed")


def main():
    parser = argparse.ArgumentParser(description="Eltek Flatpack2 SLCAN controller")
    parser.add_argument('--channel', default='/dev/tty.usbserial-A10KHTR4', help='SLCAN device')
    parser.add_argument('--serial', type=str, help='Flatpack serial number')
    parser.add_argument('--unit-id', type=int, default=1, help='Unit ID 1-63')
    parser.add_argument('--voltage', type=float, help='Set live voltage')
    parser.add_argument('--current', type=float, help='Set current limit')
    parser.add_argument('--ovp', type=float, help='Over-voltage protection')
    parser.add_argument('--default-voltage', type=float, help='Store default voltage (applied after logout/power-cycle)')
    parser.add_argument('--monitor', action='store_true', help='Monitor continuously')

    args = parser.parse_args()

    fp = EltekFlatpack(channel=args.channel, unit_id=args.unit_id, serial_number=args.serial)

    try:
        if args.voltage or args.current or args.ovp:
            fp.set_voltage_and_current(args.voltage, args.current, args.ovp)
            time.sleep(0.2)
        if args.default_voltage:
            fp.set_default_voltage(args.default_voltage)
        if args.monitor:
            fp.monitor()
        else:
            status = fp.read_status()
            if status:
                print(f"Voltage: {status['voltage']:.2f} V, Current: {status['current']:.2f} A, Temp: {status['temperature']}°C")
            else:
                print("⚠️ No response from Flatpack")
    finally:
        fp.close()


if __name__=='__main__':
    main()