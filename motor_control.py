"""
motor_control.py

Controls robot movement using L298N or BTS IBT_2 motor driver and Raspberry Pi GPIO pins.

This module provides a high-level interface for controlling a differential drive robot.
It supports both L298N and BTS IBT_2 motor drivers with configurable pins and speeds.

Features:
- Forward, backward, left, right, and stop movements
- Speed control using PWM (0-100%)
- Configurable motor driver type (L298N or IBT)
- Safe cleanup and GPIO management
- Smooth acceleration/deceleration (optional)

Hardware Compatibility:
- L298N Motor Driver: Uses IN1, IN2, ENA, IN3, IN4, ENB pins
- BTS IBT_2 Motor Driver: Uses RPWM and LPWM pins for each motor

Usage:
    from motor_control import MotorController
    
    # Using L298N driver
    motor = MotorController(driver_type='L298N')
    motor.forward(speed=70)
    motor.left(speed=50)
    motor.stop()
    motor.cleanup()
    
    # Using IBT driver
    motor = MotorController(driver_type='IBT', 
                           m1_rpwm=12, m1_lpwm=13, 
                           m2_rpwm=18, m2_lpwm=19)
    motor.forward(speed=60)
    motor.cleanup()

Author: Auto-generated for Raspberry Pi Robot Project
"""

import time
from typing import Optional, Literal
from utils.gpio_helper import MotorDriver, IBTMotorDriver, GPIOHelper

# ========== CONFIGURATION ==========
# Default L298N pins (adjust based on your wiring)
DEFAULT_L298N_PINS = {
    'in1': 17,
    'in2': 27,
    'ena': 18,
    'in3': 22,
    'in4': 23,
    'enb': 24
}

# Default IBT pins (from CSV configuration)
DEFAULT_IBT_PINS = {
    'm1_rpwm_pin': 17,  # Driver 1 Motor A RPWM
    'm1_lpwm_pin': 27,  # Driver 1 Motor A LPWM
    'm2_rpwm_pin': 6,   # Driver 2 Motor A RPWM
    'm2_lpwm_pin': 13,  # Driver 2 Motor A LPWM
    'm1_r_en_pin': 22,  # Driver 1 R_EN
    'm1_l_en_pin': 5,   # Driver 1 L_EN
    'm2_r_en_pin': 19,  # Driver 2 R_EN
    'm2_l_en_pin': 26   # Driver 2 L_EN
}

# Default speeds (0-100)
DEFAULT_FORWARD_SPEED = 40
DEFAULT_TURN_SPEED = 35
DEFAULT_REVERSE_SPEED = 55

# PWM frequency (Hz)
DEFAULT_PWM_FREQ = 1000

# Acceleration settings
ENABLE_SMOOTH_ACCELERATION = False
ACCELERATION_STEP = 5  # Speed increment per step
ACCELERATION_DELAY = 0.05  # Delay between steps (seconds)

# ===================================


class MotorController:
    """
    High-level motor controller for differential drive robots.
    
    Supports both L298N and BTS IBT_2 motor drivers with a unified interface.
    Provides movement functions: forward, backward, left, right, stop.
    
    IBT-2 Hardware Configuration (from hardware table):
    Driver 1 (Left Side): RPWM=GPIO17, LPWM=GPIO27, R_EN=GPIO22, L_EN=GPIO5
    Driver 2 (Right Side): RPWM=GPIO6, LPWM=GPIO13, R_EN=GPIO19, L_EN=GPIO26
    
    Motor Movement Logic (for IBT-2 differential drive):
    Forward: M1(+), M2(+) - Both sides move forward
    Backward: M1(-), M2(-) - Both sides move backward
    Left: M1(-), M2(+) - Left reverses, right forward (pivot left)
    Right: M1(+), M2(-) - Left forward, right reverses (pivot right)
    
    Attributes:
        driver_type: Type of motor driver ('L298N' or 'IBT')
        current_speed: Current speed setting (0-100)
        is_moving: Whether the robot is currently moving
    """
    
    def __init__(self, 
                 driver_type: Literal['L298N', 'IBT'] = 'L298N',
                 **kwargs):
        """
        Initialize the motor controller.
        
        Args:
            driver_type: Type of motor driver ('L298N' or 'IBT')
            **kwargs: Pin configuration for the selected driver
                     For L298N: in1, in2, ena, in3, in4, enb
                     For IBT: m1_rpwm_pin, m1_lpwm_pin, m2_rpwm_pin, m2_lpwm_pin
        """
        self.driver_type = driver_type
        self.current_speed = 0
        self.is_moving = False
        self._target_speed = 0
        
        # Setup GPIO mode
        GPIOHelper.set_mode()
        
        # Initialize the appropriate motor driver
        if driver_type == 'L298N':
            # Use provided pins or defaults
            pins = DEFAULT_L298N_PINS.copy()
            pins.update(kwargs)
            
            self.driver = MotorDriver(
                in1=pins['in1'],
                in2=pins['in2'],
                ena=pins['ena'],
                in3=pins['in3'],
                in4=pins['in4'],
                enb=pins['enb'],
                pwm_freq=kwargs.get('pwm_freq', DEFAULT_PWM_FREQ)
            )
            print(f"[MotorController] Initialized with L298N driver")
            print(f"[MotorController] Pins: IN1={pins['in1']}, IN2={pins['in2']}, ENA={pins['ena']}, "
                  f"IN3={pins['in3']}, IN4={pins['in4']}, ENB={pins['enb']}")
            
        elif driver_type == 'IBT':
            # Use provided pins or defaults
            pins = DEFAULT_IBT_PINS.copy()
            pins.update(kwargs)
            
            self.driver = IBTMotorDriver(
                m1_rpwm_pin=pins['m1_rpwm_pin'],
                m1_lpwm_pin=pins['m1_lpwm_pin'],
                m2_rpwm_pin=pins['m2_rpwm_pin'],
                m2_lpwm_pin=pins['m2_lpwm_pin'],
                m1_r_en_pin=pins.get('m1_r_en_pin'),
                m1_l_en_pin=pins.get('m1_l_en_pin'),
                m2_r_en_pin=pins.get('m2_r_en_pin'),
                m2_l_en_pin=pins.get('m2_l_en_pin'),
                pwm_freq=kwargs.get('pwm_freq', DEFAULT_PWM_FREQ)
            )
            print(f"[MotorController] Initialized with BTS IBT_2 driver")
            print(f"[MotorController] Pins: M1_RPWM={pins['m1_rpwm_pin']}, M1_LPWM={pins['m1_lpwm_pin']}, "
                  f"M2_RPWM={pins['m2_rpwm_pin']}, M2_LPWM={pins['m2_lpwm_pin']}")
        else:
            raise ValueError(f"Unknown driver type: {driver_type}. Use 'L298N' or 'IBT'")
    
    def _smooth_speed_change(self, target_speed: int):
        """
        Gradually change speed to target (if smooth acceleration is enabled).
        
        Args:
            target_speed: Target speed (0-100)
        """
        if not ENABLE_SMOOTH_ACCELERATION:
            self.current_speed = target_speed
            return
        
        # Gradually increase or decrease speed
        while self.current_speed != target_speed:
            if self.current_speed < target_speed:
                self.current_speed = min(self.current_speed + ACCELERATION_STEP, target_speed)
            else:
                self.current_speed = max(self.current_speed - ACCELERATION_STEP, target_speed)
            
            time.sleep(ACCELERATION_DELAY)
    
    def forward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Move forward at specified speed.
        
        Args:
            speed: Speed (0-100), defaults to DEFAULT_FORWARD_SPEED
            duration: Optional duration in seconds (blocks until complete)
        """
        if speed is None:
            speed = DEFAULT_FORWARD_SPEED
        
        speed = max(0, min(100, speed))  # Clamp to 0-100
        
        self._smooth_speed_change(speed)
        self.driver.forward(speed=speed)
        self.is_moving = True
        
        print(f"[MotorController] Moving forward at {speed}% speed")
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def backward(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Move backward at specified speed.
        
        Args:
            speed: Speed (0-100), defaults to DEFAULT_REVERSE_SPEED
            duration: Optional duration in seconds (blocks until complete)
        """
        if speed is None:
            speed = DEFAULT_REVERSE_SPEED
        
        speed = max(0, min(100, speed))  # Clamp to 0-100
        
        self._smooth_speed_change(speed)
        self.driver.backward(speed=speed)
        self.is_moving = True
        
        print(f"[MotorController] Moving backward at {speed}% speed")
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def left(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Turn left (spin in place).
        
        Args:
            speed: Speed (0-100), defaults to DEFAULT_TURN_SPEED
            duration: Optional duration in seconds (blocks until complete)
        """
        if speed is None:
            speed = DEFAULT_TURN_SPEED
        
        speed = max(0, min(100, speed))  # Clamp to 0-100
        
        self.driver.left(speed=speed)
        self.is_moving = True
        
        print(f"[MotorController] Turning left at {speed}% speed")
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def right(self, speed: Optional[int] = None, duration: Optional[float] = None):
        """
        Turn right (spin in place).
        
        Args:
            speed: Speed (0-100), defaults to DEFAULT_TURN_SPEED
            duration: Optional duration in seconds (blocks until complete)
        """
        if speed is None:
            speed = DEFAULT_TURN_SPEED
        
        speed = max(0, min(100, speed))  # Clamp to 0-100
        
        self.driver.right(speed=speed)
        self.is_moving = True
        
        print(f"[MotorController] Turning right at {speed}% speed")
        
        if duration:
            time.sleep(duration)
            self.stop()
    
    def stop(self):
        """Stop all motor movement."""
        self.driver.stop()
        self.current_speed = 0
        self.is_moving = False
        print("[MotorController] Stopped")
    
    def set_custom_speed(self, left_speed: int, right_speed: int):
        """
        Set custom speeds for left and right motors independently.
        
        Args:
            left_speed: Speed for left motor (-100 to 100, negative = reverse)
            right_speed: Speed for right motor (-100 to 100, negative = reverse)
        
        Note: This is a low-level function. Use with caution.
        """
        if self.driver_type == 'L298N':
            # For L298N, we need to handle direction separately
            # This is a simplified implementation
            if left_speed >= 0 and right_speed >= 0:
                self.driver.forward(speed=max(left_speed, right_speed))
            elif left_speed < 0 and right_speed < 0:
                self.driver.backward(speed=max(abs(left_speed), abs(right_speed)))
            else:
                # Mixed directions - use turn functions
                if left_speed < 0:
                    self.driver.left(speed=max(abs(left_speed), abs(right_speed)))
                else:
                    self.driver.right(speed=max(abs(left_speed), abs(right_speed)))
        
        elif self.driver_type == 'IBT':
            # IBT driver supports direct speed control per motor
            self.driver.set_speed_m1(left_speed)
            self.driver.set_speed_m2(right_speed)
        
        self.is_moving = (left_speed != 0 or right_speed != 0)
        print(f"[MotorController] Custom speeds: Left={left_speed}%, Right={right_speed}%")
    
    def get_status(self) -> dict:
        """
        Get current motor status.
        
        Returns:
            Dict with current speed and movement state
        """
        return {
            'driver_type': self.driver_type,
            'current_speed': self.current_speed,
            'is_moving': self.is_moving
        }
    
    def cleanup(self):
        """Clean up GPIO resources and stop motors."""
        print("[MotorController] Cleaning up...")
        self.stop()
        self.driver.cleanup()
        GPIOHelper.cleanup()
        print("[MotorController] Cleanup complete")


# ========== DEMO / TESTING ==========
if __name__ == '__main__':
    """
    Demo usage of the motor controller.
    Run this script directly to test motor movements.
    """
    import signal
    import sys
    
    # Choose driver type (change to 'IBT' if using BTS IBT_2)
    DRIVER_TYPE = 'L298N'
    
    # Create motor controller
    if DRIVER_TYPE == 'L298N':
        motor = MotorController(driver_type='L298N')
    else:
        motor = MotorController(driver_type='IBT')
    
    # Handle Ctrl+C for graceful shutdown
    def signal_handler(sig, frame):
        print("\n[Main] Interrupt received, shutting down...")
        motor.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        print("=" * 50)
        print("MOTOR CONTROLLER TEST")
        print("=" * 50)
        print(f"Driver Type: {DRIVER_TYPE}")
        print("=" * 50)
        print("\nTesting motor movements...")
        print("Press Ctrl+C to stop\n")
        
        # Test sequence
        print("\n1. Moving forward for 2 seconds...")
        motor.forward(speed=60, duration=2)
        time.sleep(1)
        
        print("\n2. Moving backward for 2 seconds...")
        motor.backward(speed=60, duration=2)
        time.sleep(1)
        
        print("\n3. Turning left for 1 second...")
        motor.left(speed=50, duration=1)
        time.sleep(1)
        
        print("\n4. Turning right for 1 second...")
        motor.right(speed=50, duration=1)
        time.sleep(1)
        
        print("\n5. Testing speed variations...")
        for speed in [30, 50, 70, 90]:
            print(f"   Forward at {speed}% for 1 second...")
            motor.forward(speed=speed, duration=1)
            time.sleep(0.5)
        
        print("\n✓ All tests completed successfully!")
        print("\nStatus:", motor.get_status())
        
    except KeyboardInterrupt:
        print("\n[Main] Keyboard interrupt")
    
    except Exception as e:
        print(f"\n[Main] Error: {e}")
    
    finally:
        motor.cleanup()
        print("[Main] Goodbye!")
