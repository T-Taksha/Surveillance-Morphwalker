# 🤖 Raspberry Pi Autonomous Robot System

## Project Overview

This is a **complete autonomous robot system** built using Raspberry Pi 4B that demonstrates computer vision, autonomous navigation, object-based decision making, and servo-driven transformation mechanisms - all implemented in Python without ROS.

### 🌟 Key Features

- **🚗 Autonomous Navigation**: Obstacle avoidance using 3 ultrasonic sensors
- **📹 Live Camera Streaming**: Real-time video feed from Logitech C270 HD webcam
- **🔍 Dual Object Detection**: YOLO-based + color-based cube/marker detection
- **🎯 Object-Based Actions**: Automatic stop, turn, and count based on detected objects
- **🦾 Servo Transformation**: Mechanical leg-to-wheel transformation triggered by detection
- **🌐 Web Interface**: Beautiful dashboard for monitoring and control
- **🎮 Multiple Modes**: Autonomous, Stream, Detection, Manual control

---

## 📦 Project Structure

```
MiniProject/
├── main.py                      # Main integration hub
├── motor_control.py             # Motor control (IBT_02 + L298N)
├── camera_stream.py             # Camera capture
├── detector.py                  # YOLO detection
├── controller.py                # Autonomous navigation
├── stream_server.py             # Flask web server
├── object_action_handler.py     # Object actions & servo ⭐ NEW
│
├── requirements.txt
├── README.md
│
├── utils/
│   ├── gpio_helper.py          # GPIO, motors, servo
│   └── net_comm.py
│
└── models/
    └── yolov8n.pt              # Auto-downloaded
```

---

## 🚀 Quick Start

### 1. Installation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
pip install -r requirements.txt

# Test individual modules
python motor_control.py      # Test motors
python camera_stream.py      # Test camera
python controller.py         # Test sensors
```

### 2. Run the Robot

```bash
# Basic autonomous mode
python main.py

# With object detection
python main.py --detection

# Custom configuration
python main.py --mode autonomous --speed 70 --port 8080
```

### 3. Access Web Interface

```
Open browser: http://<raspberry-pi-ip>:5000/
```

---

## 🔧 Hardware Setup

### Required Components

1. **Raspberry Pi 4 Model B** (4GB+ RAM)
2. **Motor Driver**: BTS IBT_02 H-Bridge
3. **Motors**: 2x DC Motors
4. **Camera**: Logitech C270 HD Webcam
5. **Sensors**: 3x HC-SR04 Ultrasonic
6. **Servo**: Standard hobby servo
7. **Power**: 7.4V-12V battery + 5V 3A for Pi

### Pin Connections

**IBT_02 Motor Driver:**
```
M1_RPWM → GPIO 12    M2_RPWM → GPIO 18
M1_LPWM → GPIO 13    M2_LPWM → GPIO 19
```

**Ultrasonic Sensors:**
```
Front: TRIG=5,  ECHO=6
Left:  TRIG=13, ECHO=19
Right: TRIG=16, ECHO=20
```

**Servo Motor:**
```
Signal → GPIO 25
```

---

## 🎮 Operation Modes

### 1. Autonomous Mode
```bash
python main.py --mode autonomous
```
Full navigation with obstacle avoidance

### 2. Stream Mode
```bash
python main.py --mode stream
```
Camera streaming only (no movement)

### 3. Detection Mode
```bash
python main.py --mode detection --detection
```
Object detection with visual overlay

### 4. Manual Mode
```bash
python main.py --mode manual
```
Web-based manual control

---

## 🎯 Object-Based Actions

The robot can detect objects and perform automatic actions:

### YOLO Object Detection
- **Person** → Stop robot
- **Bottle/Cup** → Count objects
- **Cell Phone** → Turn left
- **Book** → Turn right

### Color-Based Detection
Detects colored cubes/markers:
- Red, Blue, Green, Yellow

### Servo Transformation
- Triggers when object detected within 30cm
- Opens mechanical transformation
- Auto-closes after 3 seconds

### Object Counting
Tracks and counts detected objects in real-time

---

## 📚 Module Documentation

### main.py
Central integration hub with 4 operation modes, web interface, and REST API.

### motor_control.py
Motor control supporting IBT_02 and L298N drivers with PWM speed control.

### camera_stream.py
Background camera capture with Logitech C270 support.

### controller.py
Autonomous navigation using 3 ultrasonic sensors.

### stream_server.py
Flask MJPEG streaming server with beautiful web UI.

### object_action_handler.py ⭐ NEW
- YOLO + color-based detection
- Automatic actions (stop/turn/count)
- Servo transformation trigger
- Object counting

### utils/gpio_helper.py
- `MotorDriver`: L298N control
- `IBTMotorDriver`: IBT_02 control
- `UltrasonicSensor`: HC-SR04 interface
- `WheelActuator`: Servo control

---

## 🌐 Web Interface

Access at `http://<pi-ip>:5000/`

**Features:**
- Live camera feed
- Real-time sensor data
- Control buttons
- Detected objects list
- System status
- Object counts

**API Endpoints:**
- `GET /` - Dashboard
- `GET /video` - MJPEG stream
- `GET /api/status` - JSON status
- `POST /api/control` - Robot control

---

## ⚙️ Configuration

### Command-Line Options

```bash
python main.py [OPTIONS]

--mode {autonomous,stream,detection,manual}
--port PORT              (default: 5000)
--speed SPEED            (default: 60)
--driver-type {L298N,IBT}
--detection              (enable detection)
--camera-width WIDTH
--camera-height HEIGHT
--camera-fps FPS
```

### Examples

```bash
# High-speed autonomous
python main.py --speed 80

# HD streaming
python main.py --mode stream --camera-width 1280 --camera-height 720

# IBT driver with detection
python main.py --driver-type IBT --detection
```

---

## 🔍 Troubleshooting

### Camera Not Working
```bash
ls /dev/video*
python main.py --camera-device 1
```

### Motors Not Responding
```bash
python motor_control.py
sudo usermod -a -G gpio $USER
```

### Low FPS
```bash
python main.py --camera-width 320 --camera-height 240
```

---

## 📝 Notes

- Reduce camera resolution if FPS is low
- Ensure Raspberry Pi has enough RAM for YOLO
- Use 5V 3A power supply for Pi
- Common ground for all components
- Always call cleanup() to avoid GPIO locks

---

## 🎓 Project Highlights

**Total Code:** 2,000+ lines of Python
**Modules:** 8 main modules
**Features:** 20+ features
**Documentation:** Comprehensive guides

**Technologies:**
- Computer Vision (OpenCV, YOLO)
- Web Development (Flask, JavaScript)
- Robotics (GPIO, PWM, Sensors)
- Threading & Concurrency

---

## 📞 Support

Check documentation in artifacts directory:
- `system_guide.md` - Complete guide
- `quick_reference.md` - Quick commands
- `architecture.md` - System design
- `walkthrough.md` - Project overview

---

## 🎉 Ready to Run!

```bash
python main.py --mode autonomous --detection
```

**Open:** `http://<raspberry-pi-ip>:5000/`

**Happy Robotics! 🤖✨**