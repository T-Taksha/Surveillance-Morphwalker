"""
GPIO helper utilities for Raspberry Pi.

Features:
- Safe import of RPi.GPIO with a mock fallback (so code can run on your PC for testing).
- GPIOHelper class for generic setup/cleanup.
- PWMChannel wrapper for PWM handling.
- MotorDriver class for a simple L298N-driven 2-motor differential drive.
- IBTMotorDriver class for BTS IBT_02 (BTS7960) modules.
- WheelActuator class for a simple servo-based mechanism (e.g., wheel opening).

Usage examples:
    from utils.gpio_helper import IBTMotorDriver, MotorDriver, GPIOHelper, WheelActuator

    GPIOHelper.set_mode()  # default BCM
    motor = IBTMotorDriver(m1_rpwm_pin=17, m1_lpwm_pin=27, m2_rpwm_pin=6, m2_lpwm_pin=13)
    motor.forward(70)
    motor.stop()
    WheelActuator(servo_pin=18).set_angle(90)
    GPIOHelper.cleanup()

"""

from time import sleep

# Try to import RPi.GPIO; if not available, provide a lightweight mock for dev on PC.
try:
    import RPi.GPIO as GPIO  # type: ignore
    _RPi_AVAILABLE = True
except Exception:
    _RPi_AVAILABLE = False

    class _MockGPIO:
        BCM = "BCM"
        BOARD = "BOARD"
        OUT = "OUT"
        IN = "IN"
        HIGH = 1
        LOW = 0

        def __init__(self):
            self._pins = {}

        def setwarnings(self, flag): pass
        def setmode(self, mode): pass
        def setup(self, pin, mode): self._pins[pin] = {"mode": mode, "state": None}
        def output(self, pin, state): self._pins[pin]["state"] = state
        def PWM(self, pin, freq):
            # Simple PWM mock that provides start/ChangeDutyCycle/stop
            class _PWM:
                def __init__(self):
                    self.pin = pin
                    self.freq = freq
                    self.dc = 0
                def start(self, dc): self.dc = dc
                def ChangeDutyCycle(self, dc): self.dc = dc
                def stop(self): pass
            return _PWM()
        def input(self, pin): return 0
        def cleanup(self): self._pins = {}

    GPIO = _MockGPIO()  # type: ignore

# Constants for convenience
DEFAULT_PWM_FREQ = 1000  # Hz for motor PWM (adjust if needed)
DEFAULT_SERVO_FREQ = 50  # Hz for typical hobby servos (20ms period)


class GPIOHelper:
    """Utilities for global GPIO behavior."""
    @staticmethod
    def set_mode(mode=GPIO.BCM, warnings=False):
        """Set GPIO mode (BCM or BOARD) and warnings flag."""
        GPIO.setwarnings(warnings)
        GPIO.setmode(mode)

    @staticmethod
    def setup_pin(pin, direction=GPIO.OUT, initial=GPIO.LOW):
        """Setup a single pin safely."""
        GPIO.setup(pin, direction)
        if direction == GPIO.OUT:
            GPIO.output(pin, initial)

    @staticmethod
    def cleanup():
        """Cleanup physical GPIO pins."""
        try:
            GPIO.cleanup()
        except Exception:
            # In case mock doesn't implement cleanup
            pass


class PWMChannel:
    """Wrapper around GPIO.PWM to make starting/stopping simpler."""
    def __init__(self, pin, freq=DEFAULT_PWM_FREQ, start_duty=0):
        GPIO.setup(pin, GPIO.OUT)
        self.pin = pin
        self.freq = freq
        self._pwm = GPIO.PWM(pin, freq)
        self._pwm.start(start_duty)
        self._duty = start_duty

    def set_duty(self, duty):
        """Set duty cycle (0-100)."""
        if duty < 0: duty = 0
        if duty > 100: duty = 100
        self._duty = duty
        self._pwm.ChangeDutyCycle(duty)

    def stop(self):
        """Stop PWM on this channel."""
        try:
            self._pwm.stop()
        except Exception:
            pass


class MotorDriver:
    """
    Simple L298N dual-motor driver wrapper.
    Controls two motors: motor A (in1, in2, ena) and motor B (in3, in4, enb).

    Example:
        motor = MotorDriver(in1=17, in2=27, ena=18, in3=22, in4=23, enb=24)
        motor.forward(70)
        motor.left(50)
        motor.stop()
        GPIOHelper.cleanup()
    """
    def __init__(self, in1, in2, ena, in3, in4, enb, pwm_freq=DEFAULT_PWM_FREQ, use_pwm=True):
        # pins
        self.in1 = in1
        self.in2 = in2
        self.ena = ena
        self.in3 = in3
        self.in4 = in4
        self.enb = enb
        self.use_pwm = use_pwm

        # setup pins
        for pin in (in1, in2, in3, in4):
            GPIOHelper.setup_pin(pin, GPIO.OUT, GPIO.LOW)

        if use_pwm:
            self.pwm_a = PWMChannel(ena, freq=pwm_freq, start_duty=0)
            self.pwm_b = PWMChannel(enb, freq=pwm_freq, start_duty=0)
        else:
            GPIOHelper.setup_pin(ena, GPIO.OUT, GPIO.LOW)
            GPIOHelper.setup_pin(enb, GPIO.OUT, GPIO.LOW)
            self.pwm_a = None
            self.pwm_b = None

    # Low level helpers
    def _set_motor_a(self, forward=True):
        GPIO.output(self.in1, GPIO.HIGH if forward else GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW if forward else GPIO.HIGH)

    def _set_motor_b(self, forward=True):
        GPIO.output(self.in3, GPIO.HIGH if forward else GPIO.LOW)
        GPIO.output(self.in4, GPIO.LOW if forward else GPIO.HIGH)

    def set_speed(self, speed_a: float, speed_b: float):
        """Set speed for motor A and motor B (0-100)."""
        if self.use_pwm:
            self.pwm_a.set_duty(speed_a)
            self.pwm_b.set_duty(speed_b)
        else:
            GPIO.output(self.ena, GPIO.HIGH if speed_a > 0 else GPIO.LOW)
            GPIO.output(self.enb, GPIO.HIGH if speed_b > 0 else GPIO.LOW)

    # High level movements
    def forward(self, speed=60):
        self._set_motor_a(forward=True)
        self._set_motor_b(forward=True)
        self.set_speed(speed, speed)

    def backward(self, speed=60):
        self._set_motor_a(forward=False)
        self._set_motor_b(forward=False)
        self.set_speed(speed, speed)

    def left(self, speed=50):
        # Spin by reversing one motor
        self._set_motor_a(forward=False)
        self._set_motor_b(forward=True)
        self.set_speed(speed, speed)

    def right(self, speed=50):
        self._set_motor_a(forward=True)
        self._set_motor_b(forward=False)
        self.set_speed(speed, speed)

    def stop(self):
        self.set_speed(0, 0)
        # also set inputs low
        GPIO.output(self.in1, GPIO.LOW)
        GPIO.output(self.in2, GPIO.LOW)
        GPIO.output(self.in3, GPIO.LOW)
        GPIO.output(self.in4, GPIO.LOW)

    def cleanup(self):
        """Stop PWMs and cleanup pins."""
        if self.use_pwm:
            try:
                self.pwm_a.stop()
                self.pwm_b.stop()
            except Exception:
                pass


class IBTMotorDriver:
    """
    Motor driver wrapper for BTS IBT_02 (BTS7960-style) modules.

    Each motor uses two PWM inputs: RPWM and LPWM.
    To drive forward:  RPWM = speed, LPWM = 0
    To drive reverse:  RPWM = 0,     LPWM = speed

    speed range: -100 .. 0 .. +100 (negative -> reverse)
    """

    def __init__(self,
                 m1_rpwm_pin, m1_lpwm_pin,
                 m2_rpwm_pin, m2_lpwm_pin,
                 m1_r_en_pin=None, m1_l_en_pin=None,
                 m2_r_en_pin=None, m2_l_en_pin=None,
                 pwm_freq=DEFAULT_PWM_FREQ):
        # store pins
        self.m1_rpwm_pin = m1_rpwm_pin
        self.m1_lpwm_pin = m1_lpwm_pin
        self.m2_rpwm_pin = m2_rpwm_pin
        self.m2_lpwm_pin = m2_lpwm_pin
        
        # Enable pins (optional, but recommended for IBT-2)
        self.enable_pins = [p for p in [m1_r_en_pin, m1_l_en_pin, m2_r_en_pin, m2_l_en_pin] if p is not None]

        # Setup pins as outputs and PWM channels
        GPIOHelper.setup_pin(m1_rpwm_pin, GPIO.OUT, GPIO.LOW)
        GPIOHelper.setup_pin(m1_lpwm_pin, GPIO.OUT, GPIO.LOW)
        GPIOHelper.setup_pin(m2_rpwm_pin, GPIO.OUT, GPIO.LOW)
        GPIOHelper.setup_pin(m2_lpwm_pin, GPIO.OUT, GPIO.LOW)
        
        # Setup enable pins and set them HIGH
        for pin in self.enable_pins:
            GPIOHelper.setup_pin(pin, GPIO.OUT, GPIO.HIGH)

        # Create PWM channels
        self.m1_r = PWMChannel(m1_rpwm_pin, freq=pwm_freq, start_duty=0)
        self.m1_l = PWMChannel(m1_lpwm_pin, freq=pwm_freq, start_duty=0)
        self.m2_r = PWMChannel(m2_rpwm_pin, freq=pwm_freq, start_duty=0)
        self.m2_l = PWMChannel(m2_lpwm_pin, freq=pwm_freq, start_duty=0)

    def _apply_pwm_pair(self, pwm_pos: PWMChannel, pwm_neg: PWMChannel, speed: float):
        """Set pair so that one channel is duty and the other is zero."""
        # clamp and convert to 0..100
        if speed is None:
            speed = 0
        if speed > 100: speed = 100
        if speed < -100: speed = -100

        if speed >= 0:
            pwm_neg.set_duty(0)
            pwm_pos.set_duty(abs(speed))
        else:
            pwm_pos.set_duty(0)
            pwm_neg.set_duty(abs(speed))

    def set_speed_m1(self, speed: float):
        """Set motor1 speed (-100..100)."""
        self._apply_pwm_pair(self.m1_r, self.m1_l, speed)

    def set_speed_m2(self, speed: float):
        """Set motor2 speed (-100..100)."""
        self._apply_pwm_pair(self.m2_r, self.m2_l, speed)

    def forward(self, speed=60):
        """Both motors forward at given speed."""
        self.set_speed_m1(abs(speed))
        self.set_speed_m2(abs(speed))

    def backward(self, speed=60):
        self.set_speed_m1(-abs(speed))
        self.set_speed_m2(-abs(speed))

    def left(self, speed=50):
        # Pivot left: left motor reverse, right motor forward (or slow one side)
        self.set_speed_m1(-abs(speed))
        self.set_speed_m2(abs(speed))

    def right(self, speed=50):
        self.set_speed_m1(abs(speed))
        self.set_speed_m2(-abs(speed))

    def stop(self):
        self.m1_r.set_duty(0)
        self.m1_l.set_duty(0)
        self.m2_r.set_duty(0)
        self.m2_l.set_duty(0)
        # Note: We keep enable pins HIGH to allow braking if supported, 
        # or you could set them LOW to coast. For now, we just stop PWM.

    def cleanup(self):
        try:
            self.m1_r.stop(); self.m1_l.stop()
            self.m2_r.stop(); self.m2_l.stop()
        except Exception:
            pass


class UltrasonicSensor:
    """
    HC-SR04 Ultrasonic Distance Sensor wrapper.
    
    Measures distance by sending ultrasonic pulses and timing the echo.
    
    Usage:
        sensor = UltrasonicSensor(trigger_pin=5, echo_pin=6)
        distance = sensor.get_distance_cm()
        print(f"Distance: {distance}cm")
    
    Note: Returns 999 if measurement fails or times out.
    """
    def __init__(self, trigger_pin, echo_pin, timeout=0.1):
        """
        Initialize ultrasonic sensor.
        
        Args:
            trigger_pin: GPIO pin for trigger signal
            echo_pin: GPIO pin for echo signal
            timeout: Maximum time to wait for echo (seconds)
        """
        self.trigger_pin = trigger_pin
        self.echo_pin = echo_pin
        self.timeout = timeout
        
        # Setup pins
        GPIOHelper.setup_pin(trigger_pin, GPIO.OUT, GPIO.LOW)
        GPIOHelper.setup_pin(echo_pin, GPIO.IN)
        
        # Allow sensor to settle
        sleep(0.1)
    
    def get_distance_cm(self):
        """
        Measure distance in centimeters.
        
        Returns:
            Distance in cm, or 999 if measurement fails
        """
        # If running on mock GPIO, return a random-ish value for testing
        if not _RPi_AVAILABLE:
            import random
            return random.uniform(20, 100)
        
        try:
            # Send 10us pulse to trigger
            GPIO.output(self.trigger_pin, GPIO.HIGH)
            sleep(0.00001)  # 10 microseconds
            GPIO.output(self.trigger_pin, GPIO.LOW)
            
            # Wait for echo to start
            pulse_start = None
            pulse_end = None
            timeout_start = sleep(0)  # Get current time
            
            import time
            timeout_start = time.time()
            
            # Wait for echo pin to go HIGH
            while GPIO.input(self.echo_pin) == GPIO.LOW:
                pulse_start = time.time()
                if pulse_start - timeout_start > self.timeout:
                    return 999  # Timeout
            
            # Wait for echo pin to go LOW
            while GPIO.input(self.echo_pin) == GPIO.HIGH:
                pulse_end = time.time()
                if pulse_end - timeout_start > self.timeout:
                    return 999  # Timeout
            
            if pulse_start is None or pulse_end is None:
                return 999
            
            # Calculate distance
            pulse_duration = pulse_end - pulse_start
            # Speed of sound: 34300 cm/s
            # Distance = (Time × Speed) / 2 (divide by 2 for round trip)
            distance = (pulse_duration * 34300) / 2
            
            # Clamp to reasonable range (2cm to 400cm for HC-SR04)
            if distance < 2 or distance > 400:
                return 999
            
            return round(distance, 1)
            
        except Exception as e:
            print(f"[UltrasonicSensor] Error reading sensor: {e}")
            return 999


class WheelActuator:
    """
    Simple servo wrapper for wheel-opening mechanism.
    - servo_pin: GPIO pin connected to servo signal.
    - min_angle, max_angle: expected angles (0-180).
    - pulse widths assumed standard 0.5ms-2.5ms at 50Hz; tune if needed.

    Usage:
        servo = WheelActuator(servo_pin=25)
        servo.set_angle(90)   # middle
        servo.open()          # configured open angle
        servo.close()
    """
    def __init__(self, servo_pin, freq=DEFAULT_SERVO_FREQ, open_angle=90, closed_angle=0):
        self.servo_pin = servo_pin
        self.freq = freq
        self.open_angle = open_angle
        self.closed_angle = closed_angle

        GPIOHelper.setup_pin(servo_pin, GPIO.OUT, GPIO.LOW)
        self._pwm = GPIO.PWM(servo_pin, freq)
        self._pwm.start(0)
        sleep(0.1)

    @staticmethod
    def _angle_to_duty(angle):
        # Convert 0-180 angle to duty cycle appropriate for standard servos.
        # This formula maps 0->2.5 and 180->12.5 roughly (tweak if needed).
        return 2.5 + (angle / 180.0) * 10.0

    def set_angle(self, angle):
        duty = self._angle_to_duty(angle)
        self._pwm.ChangeDutyCycle(duty)
        sleep(0.4)  # allow servo to move
        self._pwm.ChangeDutyCycle(0)  # stop sending to avoid jitter

    def open(self):
        self.set_angle(self.open_angle)

    def close(self):
        self.set_angle(self.closed_angle)

    def stop(self):
        try:
            self._pwm.stop()
        except Exception:
            pass


# Demonstration block (won't run effectfully on non-hardware systems)
if __name__ == "__main__":
    print("GPIO helper demo (no hardware actions if RPi not available). RPi present:", _RPi_AVAILABLE)
    GPIOHelper.set_mode()
    try:
        print("Testing L298N MotorDriver (mock-safe) ...")
        motor = MotorDriver(in1=17, in2=27, ena=18, in3=22, in4=23, enb=24)
        motor.forward(50)
        sleep(1)
        motor.stop()

        print("Testing IBT Motor Driver (mock-safe) ...")
        ibt = IBTMotorDriver(m1_rpwm_pin=17, m1_lpwm_pin=27, m2_rpwm_pin=6, m2_lpwm_pin=13)
        ibt.forward(50)
        sleep(1)
        ibt.left(40)
        sleep(0.6)
        ibt.stop()

        servo = WheelActuator(servo_pin=18, open_angle=100, closed_angle=10)
        servo.open()
        sleep(0.6)
        servo.close()
        servo.stop()
    finally:
        try:
            motor.cleanup()
        except Exception:
            pass
        try:
            ibt.cleanup()
        except Exception:
            pass
        GPIOHelper.cleanup()
        print("Cleaned up GPIO")
