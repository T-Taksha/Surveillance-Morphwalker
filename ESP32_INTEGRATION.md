# ESP32 Wheel-to-Leg Transformation Integration

## Overview

Your Raspberry Pi robot now supports ESP32-based wheel-to-leg transformation! The system communicates with your Master ESP32 via Serial/UART, which then controls 4 slave ESP32s using ESP-NOW.

## Hardware Setup

### Wiring Connection

Connect Raspberry Pi to ESP32 Master:

**Option 1: GPIO UART (Recommended)**
```
Raspberry Pi GPIO Pin 14 (TX)  →  ESP32 RX (GPIO 16 or RXD0)
Raspberry Pi GPIO Pin 15 (RX)  →  ESP32 TX (GPIO 17 or TXD0)
Raspberry Pi GND              →  ESP32 GND
```

**Option 2: USB-to-Serial**
- Connect USB cable from Raspberry Pi to ESP32
- Port will be `/dev/ttyUSB0` or `/dev/ttyACM0`

### ESP32 Configuration

Your existing ESP32 master code needs to be modified to receive commands from Raspberry Pi. Add this to your ESP32 master setup:

```cpp
// In setup()
Serial.begin(115200);  // Must match Raspberry Pi baud rate
```

Add command parsing to your ESP32 master loop:

```cpp
// In loop()
if (Serial.available() > 0) {
  String jsonString = Serial.readStringUntil('\n');
  
  // Parse JSON: {"cmd": 1, "speed": 100}
  // Extract cmd and speed, then broadcast to slaves
  // cmd: 0=STOP, 1=OPEN, 2=CLOSE
}
```

## Usage

### 1. Testing ESP32 Communication

Test the ESP32 connection:
```bash
cd "/c/VS Code/Mini Project - anti"
python utils/esp32_comm.py
```

This will:
- Connect to ESP32 on `/dev/serial0`
- Send OPEN command (speed 100)
- Wait 5 seconds
- Send CLOSE command (speed 100)

**Troubleshooting:**
- If connection fails, try different ports: `/dev/ttyUSB0`, `/dev/ttyACM0`, `COM3` (Windows)
- Check ESP32 is powered on and Serial baud rate matches (115200)
- Verify wiring connections

### 2. Using in Object Detection Mode

The transformation automatically triggers when objects are detected close to the robot:

```bash
python main.py --mode autonomous --detection --enable-esp32
```

Features:
- Automatically opens wheels→legs when object detected within 30cm
- Closes legs→wheels after 3 seconds
- Customizable trigger distance in `object_action_handler.py`

### 3. Manual Control via Web Interface

Start the robot with ESP32 enabled:
```bash
python main.py --mode stream --enable-esp32
```

Then:
1. Open browser: `http://<raspberry-pi-ip>:5000`
2. Use the "🔧 Wheels→Legs" button to open
3. Use the "🔧 Legs→Wheels" button to close

### 4. Custom Port Configuration

If using USB-to-Serial adapter:
```bash
python main.py --enable-esp32 --esp32-port /dev/ttyUSB0
```

## Python API Usage

### Direct Control

```python
from utils.esp32_comm import ESP32Controller

# Create controller
esp32 = ESP32Controller(port='/dev/serial0', baudrate=115200)

# Open wheels (transform to legs)
esp32.open_wheels(speed=100)
time.sleep(3)

# Close wheels (transform back)
esp32.close_wheels(speed=100)

# Stop transformation
esp32.stop()

# Check status
status = esp32.get_status()
print(f"Connected: {status['connected']}")

# Cleanup
esp32.cleanup()
```

### Integration in Your Code

```python
from object_action_handler import ObjectActionHandler
from motor_control import MotorController

# Initialize with ESP32
motor = MotorController()
handler = ObjectActionHandler(
    motor_controller=motor,
    enable_esp32=True,
    esp32_port='/dev/serial0'
)

# Transformation will automatically trigger on object detection
# Or manually trigger:
handler.esp32.open_wheels(speed=100)
```

## Configuration

### Speed Control
Adjust transformation speed (0-100):
```python
esp32.open_wheels(speed=50)   # Slower transformation
esp32.close_wheels(speed=100) # Faster transformation
```

### Trigger Distance
Edit `object_action_handler.py`:
```python
TRANSFORMATION_TRIGGER_DISTANCE = 30  # cm - change this value
```

### Transformation Duration
Edit `object_action_handler.py`:
```python
TRANSFORMATION_DURATION = 3.0  # seconds - auto-close timer
```

## Command Protocol

Raspberry Pi sends JSON commands via Serial:

**OPEN Command:**
```json
{"cmd": 1, "speed": 100}
```

**CLOSE Command:**
```json
{"cmd": 2, "speed": 100}
```

**STOP Command:**
```json
{"cmd": 0, "speed": 0}
```

ESP32 Master should:
1. Parse JSON from Serial
2. Extract `cmd` and `speed`
3. Broadcast to 4 slaves via ESP-NOW
4. (Optional) Send acknowledgment back to Raspberry Pi

## Files Modified

| File | Changes |
|------|---------|
| `utils/esp32_comm.py` | **NEW** - ESP32 Serial communication module |
| `object_action_handler.py` | Replaced GPIO servo control with ESP32 commands |
| `main.py` | Added ESP32 web controls and initialization |
| `controller.py` | No changes needed (future enhancement for terrain-based transformation) |

## Next Steps

1. **Modify ESP32 Master Code**: Add JSON parsing to receive commands from Raspberry Pi
2. **Test Communication**: Run `python utils/esp32_comm.py` to verify
3. **Full System Test**: Run with `--enable-esp32` flag
4. **Adjust Parameters**: Tune speed, trigger distance, and duration

## Support

If you encounter issues:
- Check Serial port permissions: `sudo usermod -a -G dialout $USER`
- Verify ESP32 baud rate matches (115200)
- Monitor ESP32 Serial output in Arduino IDE
- Check physical wiring connections
