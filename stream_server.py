"""
stream_server.py

Flask-based MJPEG server for live video streaming from Raspberry Pi camera.

This module provides a web interface to view the robot's camera feed in real-time
from any device on the same network. It integrates with the camera_stream module
and optionally overlays detection results from the detector module.

Features:
- Live MJPEG video stream viewable in any browser
- Snapshot endpoint for capturing single frames
- Optional object detection overlay
- Configurable resolution and quality
- Network accessible from any device
- Clean web interface with embedded video player

Endpoints:
- /              : Home page with links and embedded video
- /video         : MJPEG stream endpoint
- /snapshot      : Single JPEG snapshot
- /status        : Server and camera status (JSON)

Usage:
    python stream_server.py
    
    Then open in browser:
        http://<raspberry-pi-ip>:5000/
    
    With custom settings:
        python stream_server.py --port 8080 --width 1280 --height 720

Requirements:
    - Flask
    - OpenCV (cv2)
    - camera_stream module

Author: Auto-generated for Raspberry Pi Robot Project
"""

import cv2
import time
import argparse
from flask import Flask, Response, render_template_string, jsonify, abort
from camera_stream import CameraStream
from typing import Optional

# ========== CONFIGURATION ==========
DEFAULT_PORT = 5000
DEFAULT_HOST = '0.0.0.0'  # Listen on all network interfaces
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 480
DEFAULT_FPS = 20
JPEG_QUALITY = 80

# Enable detection overlay (requires detector module)
ENABLE_DETECTION = False
# ===================================


# Flask app
app = Flask(__name__)
camera: Optional[CameraStream] = None


# HTML template for the home page
HOME_PAGE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Robot Camera Stream</title>
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
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 20px;
            color: #fff;
        }
        
        .container {
            max-width: 1200px;
            width: 100%;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            padding: 30px;
            box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        
        h1 {
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }
        
        .subtitle {
            text-align: center;
            margin-bottom: 30px;
            opacity: 0.9;
            font-size: 1.1em;
        }
        
        .video-container {
            position: relative;
            width: 100%;
            background: #000;
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            margin-bottom: 30px;
        }
        
        .video-container img {
            width: 100%;
            height: auto;
            display: block;
        }
        
        .status-badge {
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
        
        .status-badge::before {
            content: '';
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
        
        .controls {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        
        .btn {
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid rgba(255, 255, 255, 0.3);
            color: #fff;
            padding: 15px 25px;
            border-radius: 10px;
            text-decoration: none;
            text-align: center;
            font-size: 1em;
            font-weight: bold;
            transition: all 0.3s ease;
            cursor: pointer;
            display: inline-block;
        }
        
        .btn:hover {
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }
        
        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .info-card {
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            border: 1px solid rgba(255, 255, 255, 0.2);
        }
        
        .info-card h3 {
            margin-bottom: 10px;
            font-size: 1.2em;
            color: #fff;
        }
        
        .info-card p {
            opacity: 0.9;
            line-height: 1.6;
        }
        
        .footer {
            text-align: center;
            margin-top: 30px;
            opacity: 0.8;
            font-size: 0.9em;
        }
        
        @media (max-width: 768px) {
            h1 { font-size: 2em; }
            .container { padding: 20px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 Robot Camera Stream</h1>
        <p class="subtitle">Live video feed from Raspberry Pi</p>
        
        <div class="video-container">
            <div class="status-badge">LIVE</div>
            <img src="/video" alt="Live Camera Feed">
        </div>
        
        <div class="controls">
            <a href="/video" target="_blank" class="btn">📹 Open Stream</a>
            <a href="/snapshot" target="_blank" class="btn">📸 Take Snapshot</a>
            <a href="/status" target="_blank" class="btn">📊 View Status</a>
        </div>
        
        <div class="info-grid">
            <div class="info-card">
                <h3>📡 Stream Info</h3>
                <p>
                    <strong>Resolution:</strong> {{ width }}x{{ height }}<br>
                    <strong>Format:</strong> MJPEG<br>
                    <strong>Target FPS:</strong> {{ fps }}
                </p>
            </div>
            
            <div class="info-card">
                <h3>🔗 Endpoints</h3>
                <p>
                    <strong>/video</strong> - MJPEG stream<br>
                    <strong>/snapshot</strong> - Single frame<br>
                    <strong>/status</strong> - JSON status
                </p>
            </div>
            
            <div class="info-card">
                <h3>ℹ️ About</h3>
                <p>
                    This is a Flask-based streaming server for the autonomous robot project.
                    Access from any device on the network.
                </p>
            </div>
        </div>
        
        <div class="footer">
            <p>Raspberry Pi Robot Project | Stream Server v1.0</p>
        </div>
    </div>
</body>
</html>
"""


def generate_frames():
    """
    Generator function to yield MJPEG frames.
    
    Yields:
        Multipart JPEG frames for streaming
    """
    global camera
    
    if camera is None:
        return
    
    while True:
        # Get frame from camera
        frame_bytes = camera.get_frame_jpeg()
        
        if frame_bytes is None:
            # No frame available yet, wait a bit
            time.sleep(0.01)
            continue
        
        # Optional: Add detection overlay here if ENABLE_DETECTION is True
        if ENABLE_DETECTION:
            try:
                # Get raw frame for processing
                frame_bgr = camera.get_frame_bgr()
                if frame_bgr is not None:
                    # TODO: Add detection overlay
                    # from detector import detect_objects
                    # frame_bgr = detect_objects(frame_bgr)
                    
                    # Re-encode to JPEG
                    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
                    ret, jpeg = cv2.imencode('.jpg', frame_bgr, encode_param)
                    if ret:
                        frame_bytes = jpeg.tobytes()
            except Exception as e:
                print(f"[StreamServer] Detection error: {e}")
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n'
               b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
               b'\r\n' + frame_bytes + b'\r\n')


@app.route('/')
def index():
    """Home page with embedded video player."""
    if camera is None:
        return "Camera not initialized", 503
    
    return render_template_string(
        HOME_PAGE_TEMPLATE,
        width=camera.width,
        height=camera.height,
        fps=camera.fps
    )


@app.route('/video')
def video_feed():
    """
    MJPEG video stream endpoint.
    
    Returns:
        Response with multipart MJPEG stream
    """
    if camera is None:
        abort(503, "Camera not initialized")
    
    return Response(
        generate_frames(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/snapshot')
def snapshot():
    """
    Single JPEG snapshot endpoint.
    
    Returns:
        Response with single JPEG image
    """
    if camera is None:
        abort(503, "Camera not initialized")
    
    frame_bytes = camera.get_frame_jpeg()
    
    if frame_bytes is None:
        abort(503, "No frame available")
    
    return Response(frame_bytes, mimetype='image/jpeg')


@app.route('/status')
def status():
    """
    Server status endpoint (JSON).
    
    Returns:
        JSON with server and camera status
    """
    if camera is None:
        return jsonify({
            'status': 'error',
            'message': 'Camera not initialized'
        }), 503
    
    return jsonify({
        'status': 'online',
        'camera': {
            'device_index': camera.device_index,
            'width': camera.width,
            'height': camera.height,
            'fps': camera.fps,
            'running': camera._running
        },
        'server': {
            'detection_enabled': ENABLE_DETECTION,
            'jpeg_quality': JPEG_QUALITY
        },
        'timestamp': time.time()
    })


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Flask-based MJPEG streaming server for Raspberry Pi robot'
    )
    parser.add_argument('--device', type=int, default=0,
                       help='Camera device index (default: 0)')
    parser.add_argument('--width', type=int, default=DEFAULT_WIDTH,
                       help=f'Frame width (default: {DEFAULT_WIDTH})')
    parser.add_argument('--height', type=int, default=DEFAULT_HEIGHT,
                       help=f'Frame height (default: {DEFAULT_HEIGHT})')
    parser.add_argument('--fps', type=int, default=DEFAULT_FPS,
                       help=f'Target FPS (default: {DEFAULT_FPS})')
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                       help=f'Server host (default: {DEFAULT_HOST})')
    parser.add_argument('--port', type=int, default=DEFAULT_PORT,
                       help=f'Server port (default: {DEFAULT_PORT})')
    parser.add_argument('--detection', action='store_true',
                       help='Enable object detection overlay')
    
    return parser.parse_args()


def main():
    """Main entry point for the stream server."""
    global camera, ENABLE_DETECTION
    
    args = parse_args()
    ENABLE_DETECTION = args.detection
    
    print("=" * 60)
    print("ROBOT CAMERA STREAM SERVER")
    print("=" * 60)
    print(f"Camera Device: {args.device}")
    print(f"Resolution: {args.width}x{args.height}")
    print(f"Target FPS: {args.fps}")
    print(f"Detection Overlay: {'Enabled' if ENABLE_DETECTION else 'Disabled'}")
    print("=" * 60)
    
    # Initialize camera
    try:
        camera = CameraStream(
            device_index=args.device,
            width=args.width,
            height=args.height,
            fps=args.fps
        )
        camera.start()
        print(f"✓ Camera initialized successfully")
    except Exception as e:
        print(f"✗ Error initializing camera: {e}")
        print("\nTroubleshooting:")
        print("  - Check if camera is connected")
        print("  - Try different device index (--device 0, 1, 2, ...)")
        print("  - Check camera permissions")
        return 1
    
    # Start Flask server
    try:
        print(f"\n🚀 Starting server on http://{args.host}:{args.port}/")
        print(f"📹 Stream URL: http://{args.host}:{args.port}/video")
        print(f"📸 Snapshot URL: http://{args.host}:{args.port}/snapshot")
        print("\nPress Ctrl+C to stop\n")
        
        app.run(
            host=args.host,
            port=args.port,
            threaded=True,
            debug=False
        )
    except KeyboardInterrupt:
        print("\n\n[StreamServer] Keyboard interrupt received")
    except Exception as e:
        print(f"\n[StreamServer] Error: {e}")
    finally:
        print("[StreamServer] Shutting down camera...")
        if camera:
            camera.stop()
        print("[StreamServer] Goodbye!")
    
    return 0


if __name__ == '__main__':
    exit(main())
