"""
object_action_handler.py

Object Detection Action Handler for Raspberry Pi Robot.

This module handles object-based decision making and actions:
- Detects specific objects (colored cubes, markers, etc.)
- Performs automatic actions (stop, turn, count)
- Triggers servo transformation based on detection
- Manages object counting and tracking

Integrates with:
- camera_stream.py: Gets video frames
- motor_control.py: Controls robot movement
- utils/gpio_helper.py: Controls servo actuator
- YOLO detection: Identifies objects

Author: Auto-generated for Raspberry Pi Robot Project
"""

import time
import cv2
import numpy as np
from typing import List, Dict, Optional, Callable, Tuple
from collections import defaultdict
from utils.gpio_helper import GPIOHelper
from utils.esp32_comm import ESP32Controller

# ========== CONFIGURATION ==========

# ESP32 settings for wheel transformation
ESP32_PORT = '/dev/serial0'  # Default Raspberry Pi UART (can be /dev/ttyUSB0, /dev/ttyACM0, etc.)
ESP32_BAUDRATE = 115200
ESP32_SPEED = 100  # Default transformation speed (0-100)
TRANSFORMATION_TRIGGER_DISTANCE = 30  # cm - distance to trigger transformation

# Detection settings
TARGET_OBJECTS = {
    'person': {'action': 'stop', 'priority': 1},
    'bottle': {'action': 'count', 'priority': 2},
    'cup': {'action': 'count', 'priority': 2},
    'cell phone': {'action': 'turn_left', 'priority': 3},
    'book': {'action': 'turn_right', 'priority': 3}
}

# Color detection for cubes/markers (HSV ranges)
COLOR_RANGES = {
    'red': {
        'lower1': np.array([0, 100, 100]),
        'upper1': np.array([10, 255, 255]),
        'lower2': np.array([160, 100, 100]),
        'upper2': np.array([180, 255, 255])
    },
    'blue': {
        'lower': np.array([100, 100, 100]),
        'upper': np.array([130, 255, 255])
    },
    'green': {
        'lower': np.array([40, 100, 100]),
        'upper': np.array([80, 255, 255])
    },
    'yellow': {
        'lower': np.array([20, 100, 100]),
        'upper': np.array([40, 255, 255])
    }
}

# Action settings
MIN_OBJECT_AREA = 1000  # Minimum contour area to consider
TRANSFORMATION_DURATION = 3.0  # seconds to keep wheels in leg mode
COUNTING_COOLDOWN = 2.0  # seconds between counting same object
WHEEL_ROTATION_SPEED = 20  # Motor speed after transformation

# ===================================


class ObjectActionHandler:
    """
    Handles object detection and corresponding robot actions.
    
    Features:
    - YOLO-based object detection
    - Color-based cube/marker detection
    - Automatic action execution
    - Servo transformation trigger
    - Object counting
    - Distance-based decisions
    """
    
    def __init__(self, 
                 motor_controller=None,
                 detection_model=None,
                 enable_esp32=True,
                 esp32_port=ESP32_PORT,
                 enable_color_detection=True):
        """
        Initialize the object action handler.
        
        Args:
            motor_controller: MotorController instance
            detection_model: YOLO model instance
            enable_esp32: Enable ESP32 wheel transformation control
            esp32_port: Serial port for ESP32 communication
            enable_color_detection: Enable color-based detection
        """
        self.motor_controller = motor_controller
        self.detection_model = detection_model
        self.enable_color_detection = enable_color_detection
        
        # Initialize ESP32 controller if enabled
        self.esp32 = None
        if enable_esp32:
            try:
                self.esp32 = ESP32Controller(
                    port=esp32_port,
                    baudrate=ESP32_BAUDRATE,
                    auto_connect=True
                )
                if self.esp32.is_connected():
                    print(f"[ObjectActionHandler] ESP32 controller initialized on {esp32_port}")
                else:
                    print(f"[ObjectActionHandler] ESP32 connection failed")
                    self.esp32 = None
            except Exception as e:
                print(f"[ObjectActionHandler] ESP32 initialization failed: {e}")
                self.esp32 = None
        
        # State tracking
        self.object_counts = defaultdict(int)
        self.last_action = 'idle'
        self.last_detection_time = defaultdict(float)
        self.transformation_start_time = None
        self.detected_objects_history = []
        
        # Callbacks
        self.on_object_detected: Optional[Callable] = None
        self.on_action_executed: Optional[Callable] = None
        
        print("[ObjectActionHandler] Initialized")
    
    def detect_yolo_objects(self, frame, confidence=0.5) -> List[Dict]:
        """
        Detect objects using YOLO model.
        
        Args:
            frame: Input image frame
            confidence: Minimum confidence threshold
        
        Returns:
            List of detected objects with metadata
        """
        if self.detection_model is None:
            return []
        
        try:
            results = self.detection_model(frame, conf=confidence, verbose=False)
            
            detected = []
            for result in results[0].boxes.data:
                x1, y1, x2, y2, conf, class_id = result
                class_name = self.detection_model.names[int(class_id)]
                
                detected.append({
                    'name': class_name,
                    'confidence': float(conf),
                    'bbox': (int(x1), int(y1), int(x2), int(y2)),
                    'center': (int((x1 + x2) / 2), int((y1 + y2) / 2)),
                    'area': (int(x2) - int(x1)) * (int(y2) - int(y1))
                })
            
            return detected
        
        except Exception as e:
            print(f"[ObjectActionHandler] YOLO detection error: {e}")
            return []
    
    def detect_colored_objects(self, frame) -> List[Dict]:
        """
        Detect colored cubes/markers using color segmentation.
        
        Args:
            frame: Input BGR image frame
        
        Returns:
            List of detected colored objects
        """
        if not self.enable_color_detection:
            return []
        
        try:
            # Convert to HSV
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            
            detected = []
            
            for color_name, ranges in COLOR_RANGES.items():
                # Create mask
                if 'lower1' in ranges:  # Red has two ranges
                    mask1 = cv2.inRange(hsv, ranges['lower1'], ranges['upper1'])
                    mask2 = cv2.inRange(hsv, ranges['lower2'], ranges['upper2'])
                    mask = cv2.bitwise_or(mask1, mask2)
                else:
                    mask = cv2.inRange(hsv, ranges['lower'], ranges['upper'])
                
                # Find contours
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                
                for contour in contours:
                    area = cv2.contourArea(contour)
                    if area > MIN_OBJECT_AREA:
                        # Get bounding box
                        x, y, w, h = cv2.boundingRect(contour)
                        
                        detected.append({
                            'name': f'{color_name}_cube',
                            'confidence': 1.0,
                            'bbox': (x, y, x + w, y + h),
                            'center': (x + w // 2, y + h // 2),
                            'area': area,
                            'color': color_name
                        })
            
            return detected
        
        except Exception as e:
            print(f"[ObjectActionHandler] Color detection error: {e}")
            return []
    
    def process_frame(self, frame, distance_front=None) -> Tuple[np.ndarray, List[Dict]]:
        """
        Process frame for object detection and actions.
        
        Args:
            frame: Input BGR image frame
            distance_front: Front sensor distance (cm)
        
        Returns:
            Tuple of (annotated_frame, detected_objects)
        """
        # Detect objects
        yolo_objects = self.detect_yolo_objects(frame)
        color_objects = self.detect_colored_objects(frame)
        all_objects = yolo_objects + color_objects
        
        # Draw detections on frame
        annotated_frame = frame.copy()
        
        for obj in all_objects:
            x1, y1, x2, y2 = obj['bbox']
            name = obj['name']
            conf = obj['confidence']
            
            # Choose color based on object type
            if 'cube' in name:
                color = self._get_color_bgr(obj.get('color', 'white'))
            else:
                color = (0, 255, 0)  # Green for YOLO objects
            
            # Draw bounding box
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
            
            # Draw label
            label = f"{name} {conf:.2f}"
            cv2.putText(annotated_frame, label, (x1, y1 - 10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
        
        # Execute actions based on detections
        if all_objects:
            self._execute_actions(all_objects, distance_front)
        
        # Manage transformation state
        self._manage_transformation()
        
        return annotated_frame, all_objects
    
    def _execute_actions(self, objects: List[Dict], distance_front: Optional[float]):
        """
        Execute actions based on detected objects.
        
        Args:
            objects: List of detected objects
            distance_front: Front sensor distance
        """
        # Sort by priority
        priority_objects = []
        for obj in objects:
            name = obj['name']
            if name in TARGET_OBJECTS:
                priority = TARGET_OBJECTS[name]['priority']
                priority_objects.append((priority, obj))
        
        if not priority_objects:
            return
        
        # Execute highest priority action
        priority_objects.sort(key=lambda x: x[0])
        _, obj = priority_objects[0]
        
        name = obj['name']
        action = TARGET_OBJECTS[name]['action']
        
        # Check cooldown
        current_time = time.time()
        if current_time - self.last_detection_time[name] < COUNTING_COOLDOWN:
            return
        
        self.last_detection_time[name] = current_time
        
        # Execute action
        if action == 'stop':
            self._action_stop(obj)
        elif action == 'turn_left':
            self._action_turn_left(obj)
        elif action == 'turn_right':
            self._action_turn_right(obj)
        elif action == 'count':
            self._action_count(obj)
        
        # Trigger transformation if object is close
        if distance_front and distance_front < TRANSFORMATION_TRIGGER_DISTANCE:
            self._trigger_transformation(obj, distance_front)
        
        # Callback
        if self.on_action_executed:
            self.on_action_executed(action, obj)
    
    def _action_stop(self, obj):
        """Stop the robot."""
        if self.motor_controller:
            self.motor_controller.stop()
            self.last_action = f"stopped (detected {obj['name']})"
            print(f"[Action] Stopped - {obj['name']} detected")
    
    def _action_turn_left(self, obj):
        """Turn left."""
        if self.motor_controller:
            self.motor_controller.left(duration=0.5)
            self.last_action = f"turned left (detected {obj['name']})"
            print(f"[Action] Turned left - {obj['name']} detected")
    
    def _action_turn_right(self, obj):
        """Turn right."""
        if self.motor_controller:
            self.motor_controller.right(duration=0.5)
            self.last_action = f"turned right (detected {obj['name']})"
            print(f"[Action] Turned right - {obj['name']} detected")
    
    def _action_count(self, obj):
        """Count the object."""
        name = obj['name']
        self.object_counts[name] += 1
        self.last_action = f"counted {name} (total: {self.object_counts[name]})"
        print(f"[Action] Counted {name} - Total: {self.object_counts[name]}")
    
    def _trigger_transformation(self, obj, distance):
        """
        Trigger wheel-to-leg transformation via ESP32.
        
        Args:
            obj: Detected object
            distance: Distance to object
        """
        if self.esp32 and self.transformation_start_time is None:
            # Send OPEN command to ESP32
            success = self.esp32.open_wheels(speed=ESP32_SPEED)
            
            if success:
                self.transformation_start_time = time.time()
                self.last_action = f"wheels opened (object at {distance:.1f}cm)"
                print(f"[Transformation] Wheels→Legs transformation triggered - {obj['name']} at {distance:.1f}cm")
                
                # Rotate wheels at specified speed after transformation
                if self.motor_controller:
                    self.motor_controller.forward(speed=WHEEL_ROTATION_SPEED)
                    print(f"[Transformation] Wheels rotating at {WHEEL_ROTATION_SPEED}% speed")
            else:
                print(f"[Transformation] Failed to send OPEN command to ESP32")
    
    def _manage_transformation(self):
        """Manage transformation state (auto-close after duration)."""
        if self.transformation_start_time is not None:
            if time.time() - self.transformation_start_time > TRANSFORMATION_DURATION:
                # Send CLOSE command to ESP32
                if self.esp32:
                    success = self.esp32.close_wheels(speed=ESP32_SPEED)
                    if success:
                        self.transformation_start_time = None
                        self.last_action = "wheels closed"
                        print("[Transformation] Legs→Wheels transformation - timeout")
                    else:
                        print("[Transformation] Failed to send CLOSE command to ESP32")
    
    def _get_color_bgr(self, color_name: str) -> Tuple[int, int, int]:
        """Get BGR color tuple for visualization."""
        colors = {
            'red': (0, 0, 255),
            'blue': (255, 0, 0),
            'green': (0, 255, 0),
            'yellow': (0, 255, 255),
            'white': (255, 255, 255)
        }
        return colors.get(color_name, (255, 255, 255))
    
    def get_status(self) -> Dict:
        """
        Get current status.
        
        Returns:
            Dictionary with status information
        """
        status = {
            'last_action': self.last_action,
            'object_counts': dict(self.object_counts),
            'transformation_active': self.transformation_start_time is not None,
            'total_objects_counted': sum(self.object_counts.values())
        }
        
        # Add ESP32 status if available
        if self.esp32:
            status['esp32'] = self.esp32.get_status()
        
        return status
    
    def reset_counts(self):
        """Reset object counters."""
        self.object_counts.clear()
        print("[ObjectActionHandler] Counts reset")
    
    def cleanup(self):
        """Clean up resources."""
        if self.esp32:
            try:
                self.esp32.close_wheels()  # Close wheels before disconnecting
                time.sleep(1)
                self.esp32.cleanup()
            except Exception as e:
                print(f"[ObjectActionHandler] ESP32 cleanup error: {e}")
        print("[ObjectActionHandler] Cleanup complete")


# ========== DEMO / TESTING ==========
if __name__ == '__main__':
    """
    Demo usage of the object action handler.
    """
    import sys
    
    print("=" * 60)
    print("OBJECT ACTION HANDLER TEST")
    print("=" * 60)
    
    try:
        # Initialize (without actual hardware for testing)
        handler = ObjectActionHandler(
            motor_controller=None,
            detection_model=None,
            enable_esp32=False,  # Set to True to test ESP32 communication
            enable_color_detection=True
        )
        
        print("\n✓ Handler initialized")
        print(f"Target objects: {list(TARGET_OBJECTS.keys())}")
        print(f"Color detection: {list(COLOR_RANGES.keys())}")
        print(f"Transformation trigger distance: {TRANSFORMATION_TRIGGER_DISTANCE}cm")
        
        # Test with dummy frame
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        annotated, objects = handler.process_frame(dummy_frame, distance_front=50)
        
        print(f"\n✓ Frame processing works")
        print(f"Status: {handler.get_status()}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
    
    finally:
        handler.cleanup()
        print("\nGoodbye!")
