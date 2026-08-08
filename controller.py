"""
controller.py

Autonomous robot controller using 3 ultrasonic sensors for obstacle avoidance.

Sensor Configuration:
- Front sensor: Detects obstacles ahead
- Left sensor: Detects obstacles on the left side
- Right sensor: Detects obstacles on the right side

Movement Logic:
- If all paths are clear → Move forward
- If obstacle ahead but sides clear → Turn towards clearer side
- If obstacle on one side → Turn away from obstacle
- If obstacles on all sides → Reverse and turn

Hardware:
- 3x HC-SR04 Ultrasonic Sensors
- Motor driver (L298N or BTS IBT_2)
- Raspberry Pi 4

Author: Auto-generated
"""

import time
import threading
from typing import Optional, Callable
from utils.gpio_helper import MotorDriver, UltrasonicSensor, GPIOHelper

# ========== CONFIGURATION ==========
# Distance thresholds (in centimeters)
SAFE_DISTANCE = 30          # Minimum safe distance from obstacles
CRITICAL_DISTANCE = 15      # Critical distance requiring immediate action
TURN_DISTANCE = 40          # Distance to start turning

# Movement speeds (0-100)
NORMAL_SPEED = 40           # Normal forward speed
TURN_SPEED = 35             # Speed while turning
REVERSE_SPEED = 55          # Speed while reversing

# Timing (in seconds)
SENSOR_READ_INTERVAL = 0.1  # How often to read sensors
TURN_DURATION = 0.5         # Duration of turn maneuvers
REVERSE_DURATION = 0.8      # Duration of reverse maneuvers

# Motor pins (adjust based on your wiring)
MOTOR_IN1 = 17
MOTOR_IN2 = 27
MOTOR_ENA = 18
MOTOR_IN3 = 22
MOTOR_IN4 = 23
MOTOR_ENB = 24

# Ultrasonic sensor pins (from CSV configuration)
FRONT_TRIGGER_1 = 20
FRONT_ECHO_1 = 21
FRONT_TRIGGER_2 = 7
FRONT_ECHO_2 = 8
LEFT_TRIGGER = 1
LEFT_ECHO = 4
RIGHT_TRIGGER = 23
RIGHT_ECHO = 9

# ===================================


class RobotController:
    """
    Main controller for autonomous robot navigation using ultrasonic sensors.
    
    Features:
    - Continuous sensor monitoring
    - Intelligent obstacle avoidance
    - Configurable movement behaviors
    - Safe shutdown handling
    """
    
    def __init__(self,
                 motor_pins: dict = None,
                 sensor_pins: dict = None,
                 safe_distance: float = SAFE_DISTANCE,
                 critical_distance: float = CRITICAL_DISTANCE,
                 normal_speed: int = NORMAL_SPEED):
        """
        Initialize the robot controller.
        
        Args:
            motor_pins: Dict with keys 'in1', 'in2', 'ena', 'in3', 'in4', 'enb'
            sensor_pins: Dict with keys 'front', 'left', 'right' (each containing 'trigger', 'echo')
            safe_distance: Minimum safe distance from obstacles (cm)
            critical_distance: Critical distance requiring immediate action (cm)
            normal_speed: Default forward speed (0-100)
        """
        # Setup GPIO
        GPIOHelper.set_mode()
        
        # Initialize motor driver
        if motor_pins is None:
            motor_pins = {
                'in1': MOTOR_IN1, 'in2': MOTOR_IN2, 'ena': MOTOR_ENA,
                'in3': MOTOR_IN3, 'in4': MOTOR_IN4, 'enb': MOTOR_ENB
            }
        
        self.motor = MotorDriver(**motor_pins)
        
        # Initialize ultrasonic sensors
        if sensor_pins is None:
            sensor_pins = {
                'front1': {'trigger': FRONT_TRIGGER_1, 'echo': FRONT_ECHO_1},
                'front2': {'trigger': FRONT_TRIGGER_2, 'echo': FRONT_ECHO_2},
                'left': {'trigger': LEFT_TRIGGER, 'echo': LEFT_ECHO},
                'right': {'trigger': RIGHT_TRIGGER, 'echo': RIGHT_ECHO}
            }
        
        self.sensor_front1 = UltrasonicSensor(
            trigger_pin=sensor_pins['front1']['trigger'],
            echo_pin=sensor_pins['front1']['echo']
        )
        self.sensor_front2 = UltrasonicSensor(
            trigger_pin=sensor_pins['front2']['trigger'],
            echo_pin=sensor_pins['front2']['echo']
        )
        self.sensor_left = UltrasonicSensor(
            trigger_pin=sensor_pins['left']['trigger'],
            echo_pin=sensor_pins['left']['echo']
        )
        self.sensor_right = UltrasonicSensor(
            trigger_pin=sensor_pins['right']['trigger'],
            echo_pin=sensor_pins['right']['echo']
        )
        
        # Configuration
        self.safe_distance = safe_distance
        self.critical_distance = critical_distance
        self.normal_speed = normal_speed
        
        # State
        self._running = False
        self._control_thread: Optional[threading.Thread] = None
        self._last_distances = {'front': 999, 'left': 999, 'right': 999}
        
        # Callbacks
        self.on_obstacle_detected: Optional[Callable[[str, float], None]] = None
        self.on_state_change: Optional[Callable[[str], None]] = None
        
        print("[Controller] Initialized with 3 ultrasonic sensors")
        print(f"[Controller] Safe distance: {safe_distance}cm, Critical: {critical_distance}cm")
    
    def read_sensors(self) -> dict:
        """
        Read all ultrasonic sensors and return distances.
        
        Returns:
            Dict with keys 'front1', 'front2', 'left', 'right' containing distances in cm
        """
        distances = {
            'front1': self.sensor_front1.get_distance_cm(),
            'front2': self.sensor_front2.get_distance_cm(),
            'left': self.sensor_left.get_distance_cm(),
            'right': self.sensor_right.get_distance_cm()
        }
        
        # Store for reference
        self._last_distances = distances
        
        return distances
    
    def decide_action(self, distances: dict) -> str:
        """
        Decide what action to take based on sensor readings.
        
        Args:
            distances: Dict with 'front1', 'front2', 'left', 'right' distances
        
        Returns:
            Action string: 'forward', 'turn_left', 'turn_right', 'reverse', 'stop'
        """
        # Use the minimum of the two front sensors as the effective front distance
        front = min(distances['front1'], distances['front2'])
        left = distances['left']
        right = distances['right']
        
        # Critical obstacle ahead - immediate action required
        if front < self.critical_distance:
            if left > right:
                return 'turn_left'
            else:
                return 'turn_right'
        
        # Obstacle ahead but not critical
        if front < self.safe_distance:
            # Check which side has more space
            if left > self.safe_distance and right > self.safe_distance:
                # Both sides clear, turn towards the side with more space
                return 'turn_left' if left > right else 'turn_right'
            elif left > self.safe_distance:
                return 'turn_left'
            elif right > self.safe_distance:
                return 'turn_right'
            else:
                # Both sides blocked, reverse
                return 'reverse'
        
        # Obstacle on left side
        if left < self.safe_distance and front > self.safe_distance:
            return 'turn_right'
        
        # Obstacle on right side
        if right < self.safe_distance and front > self.safe_distance:
            return 'turn_left'
        
        # All clear - move forward
        if front > self.safe_distance:
            return 'forward'
        
        # Default: stop
        return 'stop'
    
    def execute_action(self, action: str):
        """
        Execute the decided action.
        
        Args:
            action: Action string from decide_action()
        """
        if action == 'forward':
            self.motor.forward(speed=self.normal_speed)
            if self.on_state_change:
                self.on_state_change('forward')
        
        elif action == 'turn_left':
            self.motor.left(speed=TURN_SPEED)
            if self.on_state_change:
                self.on_state_change('turn_left')
            time.sleep(TURN_DURATION)
        
        elif action == 'turn_right':
            self.motor.right(speed=TURN_SPEED)
            if self.on_state_change:
                self.on_state_change('turn_right')
            time.sleep(TURN_DURATION)
        
        elif action == 'reverse':
            self.motor.backward(speed=REVERSE_SPEED)
            if self.on_state_change:
                self.on_state_change('reverse')
            time.sleep(REVERSE_DURATION)
            # After reversing, turn to find clear path
            if self._last_distances['left'] > self._last_distances['right']:
                self.motor.left(speed=TURN_SPEED)
                time.sleep(TURN_DURATION)
            else:
                self.motor.right(speed=TURN_SPEED)
                time.sleep(TURN_DURATION)
        
        elif action == 'stop':
            self.motor.stop()
            if self.on_state_change:
                self.on_state_change('stop')
    
    def _control_loop(self):
        """
        Main control loop running in background thread.
        Continuously reads sensors and executes appropriate actions.
        """
        print("[Controller] Control loop started")
        
        while self._running:
            try:
                # Read all sensors
                distances = self.read_sensors()
                
                # Log sensor readings (optional, comment out for less verbosity)
                # print(f"[Sensors] Front: {distances['front']:.1f}cm, "
                #       f"Left: {distances['left']:.1f}cm, "
                #       f"Right: {distances['right']:.1f}cm")
                
                # Trigger obstacle detection callbacks
                if self.on_obstacle_detected:
                    for direction, distance in distances.items():
                        if distance < self.safe_distance:
                            self.on_obstacle_detected(direction, distance)
                
                # Decide action based on sensor data
                action = self.decide_action(distances)
                
                # Execute the action
                self.execute_action(action)
                
                # Small delay before next iteration
                time.sleep(SENSOR_READ_INTERVAL)
                
            except Exception as e:
                print(f"[Controller] Error in control loop: {e}")
                self.motor.stop()
                time.sleep(0.5)
        
        # Stop motors when loop exits
        self.motor.stop()
        print("[Controller] Control loop stopped")
    
    def start(self):
        """Start autonomous navigation."""
        if self._running:
            print("[Controller] Already running")
            return
        
        self._running = True
        self._control_thread = threading.Thread(target=self._control_loop, daemon=True)
        self._control_thread.start()
        print("[Controller] Autonomous navigation started")
    
    def stop(self):
        """Stop autonomous navigation."""
        if not self._running:
            return
        
        print("[Controller] Stopping autonomous navigation...")
        self._running = False
        
        if self._control_thread:
            self._control_thread.join(timeout=2.0)
        
        self.motor.stop()
        print("[Controller] Stopped")
    
    def get_status(self) -> dict:
        """
        Get current robot status.
        
        Returns:
            Dict with current distances and running state
        """
        return {
            'running': self._running,
            'distances': self._last_distances.copy(),
            'safe_distance': self.safe_distance,
            'critical_distance': self.critical_distance
        }
    
    def cleanup(self):
        """Clean up resources and stop all operations."""
        print("[Controller] Cleaning up...")
        self.stop()
        self.motor.cleanup()
        GPIOHelper.cleanup()
        print("[Controller] Cleanup complete")


# ========== DEMO / TESTING ==========
if __name__ == '__main__':
    """
    Demo usage of the robot controller.
    Run this script directly to test autonomous navigation.
    """
    import signal
    import sys
    
    # Create controller instance
    controller = RobotController()
    
    # Optional: Add callbacks for monitoring
    def on_obstacle(direction: str, distance: float):
        print(f"[!] Obstacle detected: {direction} at {distance:.1f}cm")
    
    def on_state(state: str):
        print(f"[Robot] State: {state}")
    
    controller.on_obstacle_detected = on_obstacle
    controller.on_state_change = on_state
    
    # Handle Ctrl+C for graceful shutdown
    def signal_handler(sig, frame):
        print("\n[Main] Interrupt received, shutting down...")
        controller.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("=" * 50)
        print("AUTONOMOUS ROBOT CONTROLLER")
        print("=" * 50)
        print(f"Safe Distance: {SAFE_DISTANCE}cm")
        print(f"Critical Distance: {CRITICAL_DISTANCE}cm")
        print(f"Normal Speed: {NORMAL_SPEED}%")
        print("=" * 50)
        print("\nStarting autonomous navigation...")
        print("Press Ctrl+C to stop\n")
        
        # Start autonomous navigation
        controller.start()
        
        # Keep main thread alive and print status periodically
        while True:
            time.sleep(5)
            status = controller.get_status()
            d = status['distances']
            print(f"\n[Status] Front1={d['front1']:.1f}cm, Front2={d['front2']:.1f}cm, "
                  f"Left={d['left']:.1f}cm, Right={d['right']:.1f}cm")
    
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt")
    
    finally:
        controller.cleanup()
        print("[Main] Goodbye!")
