"""
main.py

Main entry point for the Raspberry Pi 4B Autonomous Robot System.

This script integrates all modules to provide a complete autonomous robot system with:
- Autonomous navigation using ultrasonic sensors
- Live camera streaming via web interface
- Object detection (optional)
- Motor control
- Multiple operation modes

Modules Integrated:
- motor_control.py: Motor control interface
- controller.py: Autonomous navigation with ultrasonic sensors
- camera_stream.py: Camera capture and frame provider
- stream_server.py: Flask web server for video streaming
- detector.py: Object detection (optional)
- utils/gpio_helper.py: GPIO utilities

Operation Modes:
1. AUTONOMOUS: Full autonomous navigation with obstacle avoidance
2. STREAM_ONLY: Camera streaming without movement
3. DETECTION: Object detection with camera feed
4. MANUAL: Manual control via web interface (future enhancement)

Usage:
    # Full autonomous mode with streaming
    python main.py --mode autonomous
    
    # Stream only (no movement)
    python main.py --mode stream
    
    # With object detection
    python main.py --mode autonomous --detection
    
    # Custom settings
    python main.py --mode autonomous --port 8080 --speed 70

Hardware Requirements:
- Raspberry Pi 4 Model B
- Motor driver (L298N or BTS IBT_2)
- 3x HC-SR04 Ultrasonic Sensors
- Pi Camera or USB Webcam
- DC Motors

Author: Auto-generated for Raspberry Pi Robot Project
"""

import sys
import time
import signal
import argparse
import threading
from typing import Optional, Literal
from flask import Flask, Response, render_template_string, jsonify, request

# Import project modules
try:
    from controller import RobotController
    from camera_stream import CameraStream
    from motor_control import MotorController
    from utils.gpio_helper import GPIOHelper
    from utils.esp32_comm import ESP32Controller
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all required modules are in the same directory.")
    sys.exit(1)

# Optional imports
YOLO_AVAILABLE = False
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    print("[Warning] YOLO not available. Detection mode will be disabled.")

# ========== CONFIGURATION ==========
DEFAULT_MODE = 'autonomous'
DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'
DEFAULT_CAMERA_WIDTH = 640
DEFAULT_CAMERA_HEIGHT = 480
DEFAULT_CAMERA_FPS = 20
DEFAULT_MOTOR_SPEED = 60
DEFAULT_DRIVER_TYPE = 'L298N'  # or 'IBT'

# Detection settings
DETECTION_MODEL = 'yolov8n.pt'
DETECTION_CONFIDENCE = 0.5
TARGET_OBJECTS = ['person', 'bottle', 'cup']  # Objects to detect and react to

# ===================================

# Global instances
robot_controller: Optional[RobotController] = None
motor_controller: Optional[MotorController] = None
camera: Optional[CameraStream] = None
detection_model: Optional[any] = None
esp32_controller: Optional[ESP32Controller] = None
app = Flask(__name__)

# System state
system_state = {
    'mode': DEFAULT_MODE,
    'running': False,
    'detection_enabled': False,
    'detected_objects': [],
    'last_action': 'idle',
    'uptime_start': time.time()
}


# ========== WEB INTERFACE ==========

MAIN_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Autonomous Robot Control</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 3em;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
            margin-bottom: 10px;
        }
        
        .header .mode-badge {
            display: inline-block;
            background: rgba(76, 175, 80, 0.9);
            padding: 10px 20px;
            border-radius: 25px;
            font-weight: bold;
            font-size: 1.1em;
        }
        
        .grid {
            display: grid;
            grid-template-columns: 2fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        .card h2 {
            margin-bottom: 20px;
            font-size: 1.8em;
            border-bottom: 2px solid rgba(255, 255, 255, 0.3);
            padding-bottom: 10px;
        }
        
        .video-container {
            position: relative;
            background: #000;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 15px;
        }
        
        .video-container img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .status-indicator {
            position: absolute;
            top: 15px;
            right: 15px;
            background: rgba(76, 175, 80, 0.9);
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.9em;
            font-weight: bold;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .status-indicator.offline {
            background: rgba(244, 67, 54, 0.9);
        }
        
        .pulse {
            width: 10px;
            height: 10px;
            background: #fff;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .stat-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 15px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .stat-item h3 {
            font-size: 0.9em;
            opacity: 0.8;
            margin-bottom: 5px;
        }
        
        .stat-item .value {
            font-size: 1.8em;
            font-weight: bold;
        }
        
        .controls {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
        }
        
        .btn {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: #fff;
            padding: 15px;
            border-radius: 10px;
            font-size: 1em;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }
        
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        
        .btn.danger {
            background: rgba(244, 67, 54, 0.3);
            border-color: rgba(244, 67, 54, 0.5);
        }
        
        .btn.success {
            background: rgba(76, 175, 80, 0.3);
            border-color: rgba(76, 175, 80, 0.5);
        }
        
        .log-container {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
            max-height: 200px;
            overflow-y: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .log-entry {
            margin-bottom: 5px;
            opacity: 0.9;
        }
        
        .detection-list {
            list-style: none;
        }
        
        .detection-item {
            background: rgba(255, 255, 255, 0.1);
            padding: 10px;
            margin-bottom: 8px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
        }
        
        @media (max-width: 1024px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
    <script>
        function updateStatus() {
            fetch('/api/status')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('mode').textContent = data.mode.toUpperCase();
                    document.getElementById('uptime').textContent = data.uptime;
                    document.getElementById('action').textContent = data.last_action;
                    
                    // Update sensor distances if available
                    if (data.distances) {
                        document.getElementById('front-dist').textContent = data.distances.front + ' cm';
                        document.getElementById('left-dist').textContent = data.distances.left + ' cm';
                        document.getElementById('right-dist').textContent = data.distances.right + ' cm';
                    }
                    
                    // Update detection list
                    if (data.detected_objects && data.detected_objects.length > 0) {
                        const list = document.getElementById('detection-list');
                        list.innerHTML = '';
                        data.detected_objects.forEach(obj => {
                            const li = document.createElement('li');
                            li.className = 'detection-item';
                            li.textContent = `${obj.name} (${(obj.confidence * 100).toFixed(1)}%)`;
                            list.appendChild(li);
                        });
                    }
                });
        }
        
        function controlRobot(action) {
            fetch('/api/control', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({action: action})
            })
            .then(response => response.json())
            .then(data => {
                console.log('Control response:', data);
            });
        }
        
        // Update status every 1 second
        setInterval(updateStatus, 1000);
        updateStatus();
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Autonomous Robot System</h1>
            <div class="mode-badge">MODE: <span id="mode">{{ mode }}</span></div>
        </div>
        
        <div class="grid">
            <div>
                <div class="card">
                    <h2>📹 Live Camera Feed</h2>
                    <div class="video-container">
                        <div class="status-indicator">
                            <div class="pulse"></div>
                            LIVE
                        </div>
                        <img src="/video" alt="Live Camera Feed">
                    </div>
                </div>
                
                <div class="card">
                    <h2>📊 Sensor Data</h2>
                    <div class="stats-grid">
                        <div class="stat-item">
                            <h3>Front Distance</h3>
                            <div class="value" id="front-dist">-- cm</div>
                        </div>
                        <div class="stat-item">
                            <h3>Left Distance</h3>
                            <div class="value" id="left-dist">-- cm</div>
                        </div>
                        <div class="stat-item">
                            <h3>Right Distance</h3>
                            <div class="value" id="right-dist">-- cm</div>
                        </div>
                        <div class="stat-item">
                            <h3>Last Action</h3>
                            <div class="value" id="action">idle</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div>
                <div class="card">
                    <h2>🎮 Controls</h2>
                    <div class="controls">
                        <button class="btn success" onclick="controlRobot('start')">▶️ Start</button>
                        <button class="btn danger" onclick="controlRobot('stop')">⏹️ Stop</button>
                        <button class="btn" onclick="controlRobot('forward')">⬆️ Forward</button>
                        <button class="btn" onclick="controlRobot('backward')">⬇️ Backward</button>
                        <button class="btn" onclick="controlRobot('left')">⬅️ Left</button>
                        <button class="btn" onclick="controlRobot('right')">➡️ Right</button>
                        <button class="btn success" onclick="controlRobot('esp32_open')">🔧 Wheels→Legs</button>
                        <button class="btn success" onclick="controlRobot('esp32_close')">🔧 Legs→Wheels</button>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🔍 Detected Objects</h2>
                    <ul class="detection-list" id="detection-list">
                        <li style="opacity: 0.6; text-align: center;">No objects detected</li>
                    </ul>
                </div>
                
                <div class="card">
                    <h2>ℹ️ System Info</h2>
                    <div class="stat-item">
                        <h3>Uptime</h3>
                        <div class="value" id="uptime" style="font-size: 1.2em;">0s</div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""


def generate_frames():
    """Generate video frames with optional detection overlay."""
    global camera, detection_model, system_state
    
    while True:
        if camera is None:
            time.sleep(0.1)
            continue
        
        frame = camera.get_frame_bgr()
        if frame is None:
            time.sleep(0.01)
            continue
        
        # Apply detection if enabled
        if system_state['detection_enabled'] and detection_model is not None:
            try:
                results = detection_model(frame, conf=DETECTION_CONFIDENCE, verbose=False)
                frame = results[0].plot()
                
                # Extract detected objects
                detected = []
                for result in results[0].boxes.data:
                    class_id = int(result[5])
                    confidence = float(result[4])
                    class_name = detection_model.names[class_id]
                    detected.append({
                        'name': class_name,
                        'confidence': confidence
                    })
                
                system_state['detected_objects'] = detected
                
            except Exception as e:
                print(f"[Detection] Error: {e}")
        
        # Encode frame to JPEG
        import cv2
        ret, jpeg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            continue
        
        frame_bytes = jpeg.tobytes()
        
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
               b'\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    """Main web interface."""
    return render_template_string(MAIN_PAGE_TEMPLATE, mode=system_state['mode'])


@app.route('/video')
def video_feed():
    """Video streaming endpoint."""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/status')
def api_status():
    """API endpoint for system status."""
    global robot_controller, system_state
    
    status = {
        'mode': system_state['mode'],
        'running': system_state['running'],
        'detection_enabled': system_state['detection_enabled'],
        'last_action': system_state['last_action'],
        'uptime': f"{int(time.time() - system_state['uptime_start'])}s",
        'detected_objects': system_state['detected_objects'],
        'distances': {'front': 0, 'left': 0, 'right': 0}
    }
    
    if robot_controller:
        robot_status = robot_controller.get_status()
        status['distances'] = robot_status.get('distances', status['distances'])
        status['running'] = robot_status.get('running', False)
    
    # Add ESP32 status if available
    if esp32_controller:
        status['esp32_connected'] = esp32_controller.is_connected()
        status['esp32_status'] = esp32_controller.get_status()
    else:
        status['esp32_connected'] = False
    
    return jsonify(status)


@app.route('/api/control', methods=['POST'])
def api_control():
    """API endpoint for robot control."""
    global robot_controller, motor_controller, system_state
    
    data = request.get_json()
    action = data.get('action', '')
    
    try:
        if action == 'start':
            if robot_controller and system_state['mode'] == 'autonomous':
                robot_controller.start()
                system_state['running'] = True
                system_state['last_action'] = 'started'
        
        elif action == 'stop':
            if robot_controller:
                robot_controller.stop()
            if motor_controller:
                motor_controller.stop()
            system_state['running'] = False
            system_state['last_action'] = 'stopped'
        
        elif action in ['forward', 'backward', 'left', 'right']:
            if motor_controller and system_state['mode'] != 'autonomous':
                getattr(motor_controller, action)(duration=0.5)
                system_state['last_action'] = action
        
        elif action == 'esp32_open':
            global esp32_controller
            if esp32_controller and esp32_controller.is_connected():
                esp32_controller.open_wheels(speed=100)
                system_state['last_action'] = 'ESP32: wheels→legs'
        
        elif action == 'esp32_close':
            if esp32_controller and esp32_controller.is_connected():
                esp32_controller.close_wheels(speed=100)
                system_state['last_action'] = 'ESP32: legs→wheels'
        
        return jsonify({'status': 'success', 'action': action})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


# ========== MAIN SYSTEM ==========

def initialize_camera(args):
    """Initialize camera system."""
    global camera
    
    print("[Main] Initializing camera...")
    try:
        camera = CameraStream(
            device_index=args.camera_device,
            width=args.camera_width,
            height=args.camera_height,
            fps=args.camera_fps
        )
        camera.start()
        print("[Main] ✓ Camera initialized")
        return True
    except Exception as e:
        print(f"[Main] ✗ Camera initialization failed: {e}")
        return False


def initialize_detection(args):
    """Initialize object detection."""
    global detection_model, system_state
    
    if not args.detection or not YOLO_AVAILABLE:
        return True
    
    print("[Main] Initializing object detection...")
    try:
        detection_model = YOLO(DETECTION_MODEL)
        system_state['detection_enabled'] = True
        print(f"[Main] ✓ Detection initialized with {DETECTION_MODEL}")
        return True
    except Exception as e:
        print(f"[Main] ✗ Detection initialization failed: {e}")
        return False


def initialize_motors(args):
    """Initialize motor control."""
    global motor_controller
    
    print("[Main] Initializing motor control...")
    try:
        motor_controller = MotorController(driver_type=args.driver_type)
        print(f"[Main] ✓ Motor controller initialized ({args.driver_type})")
        return True
    except Exception as e:
        print(f"[Main] ✗ Motor initialization failed: {e}")
        return False


def initialize_autonomous(args):
    """Initialize autonomous navigation."""
    global robot_controller
    
    if args.mode != 'autonomous':
        return True
    
    print("[Main] Initializing autonomous navigation...")
    try:
        robot_controller = RobotController(
            normal_speed=args.speed
        )
        print("[Main] ✓ Autonomous controller initialized")
        return True
    except Exception as e:
        print(f"[Main] ✗ Autonomous initialization failed: {e}")
        return False


def cleanup_all():
    """Clean up all resources."""
    global robot_controller, motor_controller, camera
    
    print("\n[Main] Cleaning up resources...")
    
    if robot_controller:
        try:
            robot_controller.cleanup()
        except:
            pass
    
    if motor_controller:
        try:
            motor_controller.cleanup()
        except:
            pass
    
    if camera:
        try:
            camera.stop()
        except:
            pass
    
    try:
        GPIOHelper.cleanup()
    except:
        pass
    
    # ESP32 cleanup
    global esp32_controller
    if esp32_controller:
        try:
            esp32_controller.cleanup()
        except:
            pass
    
    print("[Main] ✓ Cleanup complete")


def signal_handler(sig, frame):
    """Handle Ctrl+C gracefully."""
    print("\n[Main] Interrupt received, shutting down...")
    cleanup_all()
    sys.exit(0)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Raspberry Pi Autonomous Robot System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --mode autonomous
  python main.py --mode stream --port 8080
  python main.py --mode autonomous --detection --speed 70
        """
    )
    
    parser.add_argument('--mode', type=str, default=DEFAULT_MODE,
                       choices=['autonomous', 'stream', 'detection', 'manual'],
                       help='Operation mode (default: autonomous)')
    
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                       help=f'Web server port (default: {DEFAULT_PORT})')
    
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                       help=f'Web server host (default: {DEFAULT_HOST})')
    
    parser.add_argument('--camera-device', type=int, default=0,
                       help='Camera device index (default: 0)')
    
    parser.add_argument('--camera-width', type=int, default=DEFAULT_CAMERA_WIDTH,
                       help=f'Camera width (default: {DEFAULT_CAMERA_WIDTH})')
    
    parser.add_argument('--camera-height', type=int, default=DEFAULT_CAMERA_HEIGHT,
                       help=f'Camera height (default: {DEFAULT_CAMERA_HEIGHT})')
    
    parser.add_argument('--camera-fps', type=int, default=DEFAULT_CAMERA_FPS,
                       help=f'Camera FPS (default: {DEFAULT_CAMERA_FPS})')
    
    parser.add_argument('--detection', action='store_true',
                       help='Enable object detection')
    
    parser.add_argument('--speed', type=int, default=DEFAULT_MOTOR_SPEED,
                       help=f'Motor speed 0-100 (default: {DEFAULT_MOTOR_SPEED})')
    
    parser.add_argument('--driver-type', type=str, default=DEFAULT_DRIVER_TYPE,
                       choices=['L298N', 'IBT'],
                       help=f'Motor driver type (default: {DEFAULT_DRIVER_TYPE})')
    
    parser.add_argument('--no-web', action='store_true',
                       help='Disable web interface (autonomous only)')
    
    parser.add_argument('--esp32-port', type=str, default='/dev/serial0',
                       help='ESP32 serial port (default: /dev/serial0)')
    
    parser.add_argument('--enable-esp32', action='store_true',
                       help='Enable ESP32 wheel transformation control')
    
    return parser.parse_args()


def main():
    """Main entry point."""
    global system_state
    
    # Parse arguments
    args = parse_arguments()
    system_state['mode'] = args.mode
    
    # Setup signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    # Print banner
    print("=" * 70)
    print("🤖 RASPBERRY PI AUTONOMOUS ROBOT SYSTEM")
    print("=" * 70)
    print(f"Mode: {args.mode.upper()}")
    print(f"Motor Driver: {args.driver_type}")
    print(f"Camera: {args.camera_width}x{args.camera_height} @ {args.camera_fps}fps")
    print(f"Detection: {'Enabled' if args.detection else 'Disabled'}")
    print(f"Web Interface: http://{args.host}:{args.port}/")
    print("=" * 70)
    print()
    
    # Initialize components based on mode
    success = True
    
    # Camera (all modes)
    success = success and initialize_camera(args)
    
    # Detection (if enabled)
    if args.detection:
        success = success and initialize_detection(args)
    
    # Motors (autonomous and manual modes)
    if args.mode in ['autonomous', 'manual']:
        success = success and initialize_motors(args)
    
    # Autonomous controller (autonomous mode only)
    if args.mode == 'autonomous':
        success = success and initialize_autonomous(args)
    
    if not success:
        print("\n[Main] ✗ Initialization failed. Exiting...")
        cleanup_all()
        return 1
    
    print("\n[Main] ✓ All systems initialized successfully!\n")
    
    # Initialize ESP32 controller if enabled
    if args.enable_esp32:
        print("[Main] Initializing ESP32 controller...")
        try:
            esp32_controller = ESP32Controller(port=args.esp32_port, baudrate=115200, auto_connect=True)
            if esp32_controller.is_connected():
                print(f"[Main] ✓ ESP32 controller connected on {args.esp32_port}")
            else:
                print(f"[Main] ! ESP32 connection failed (will retry on demand)")
        except Exception as e:
            print(f"[Main] ! ESP32 initialization failed: {e}")
            esp32_controller = None
    
    # Start autonomous navigation if in autonomous mode
    if args.mode == 'autonomous' and robot_controller:
        print("[Main] Starting autonomous navigation...")
        robot_controller.start()
        system_state['running'] = True
    
    # Start web server (unless disabled)
    if not args.no_web:
        try:
            print(f"[Main] Starting web server on http://{args.host}:{args.port}/")
            print("[Main] Press Ctrl+C to stop\n")
            app.run(host=args.host, port=args.port, threaded=True, debug=False)
        except Exception as e:
            print(f"[Main] Web server error: {e}")
    else:
        # Keep running without web interface
        print("[Main] Running in headless mode. Press Ctrl+C to stop\n")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    
    # Cleanup
    cleanup_all()
    print("[Main] Goodbye! 👋")
    return 0


if __name__ == '__main__':
    sys.exit(main())
