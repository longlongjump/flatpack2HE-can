# Flatpack2 HE CAN Controller

Python controller for Eltek Flatpack2 HE 2000W power supplies via CAN bus using SLCAN adapters (macOS compatible).

## Features

- Set live output voltage (43.5V - 57.4V) and current (0 - 41.7A)
- Store default voltage for power-on state
- Real-time monitoring of voltage, current, and temperature
- Support for multiple units via unit ID addressing (1-63)
- Automatic login and keep-alive

## Requirements

```bash
pip install python-can
```

Hardware: SLCAN-compatible CAN adapter (USB-to-CAN)

## Quick Start

```bash
# Monitor status
uv run main.py --monitor

# Set live voltage and current
uv run main.py --voltage 52.0 --current 30.0

# Store default voltage (applied after power cycle)
uv run main.py --default-voltage 48.0

# Specify custom serial number
uv run main.py --serial 134372105069 --voltage 50.0
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--channel` | SLCAN device path | `/dev/tty.usbserial-A10KHTR4` |
| `--unit-id` | Unit address (1-63) | `1` |
| `--serial` | Flatpack serial number (12 digits) | `134372105069` |
| `--voltage` | Set live output voltage (V) | - |
| `--current` | Set current limit (A) | - |
| `--ovp` | Over-voltage protection (V) | - |
| `--default-voltage` | Store default voltage | - |
| `--monitor` | Continuous monitoring mode | - |

## Usage Examples

```bash
# Multi-unit setup - control unit 2
python main.py --unit-id 2 --voltage 54.0

# Set voltage with over-voltage protection
python main.py --voltage 52.0 --current 35.0 --ovp 59.5

# Monitor with custom device
python main.py --channel /dev/tty.usbserial-XXXX --monitor
```

## Technical Details

- **CAN Bus Rate**: 125 kbps
- **Protocol**: Eltek Flatpack2 extended CAN ID
- **Login Interval**: Every 10 seconds (automatic)
- **Voltage Resolution**: 0.01V
- **Current Resolution**: 0.1A

## Notes

- Default voltage changes only take effect after the Flatpack logs out or power-cycles
- The script sends periodic login messages to maintain connection
- Press `Ctrl+C` to stop monitoring mode

## License

Open source - use freely
