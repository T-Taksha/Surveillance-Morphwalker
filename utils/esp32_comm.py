"""
esp32_comm.py

ESP32 Communication Module for Raspberry Pi Robot.

This module handles communication between Raspberry Pi and Master ESP32
for wheel-to-leg transformation control.

Communication Protocol:
- Raspberry Pi → Master ESP32: JSON commands via Serial/UART
- Master ESP32 → 4 Slave ESP32s: ESP-NOW commands
- Commands: OPEN, CLOSE, STOP with speed control

Hardware Connection:
- Raspberry Pi TX (GPIO14) → ESP32 RX
- Raspberry Pi RX (GPIO15) → ESP32 TX
- GND → GND

Alternative: USB-to-Serial adapter
- Connect USB cable from Raspberry Pi to ESP32
- Use port like /dev/ttyUSB0 or /dev/ttyACM0

Author: Auto-generated for Raspberry Pi Robot Project
"""

import serial
import json
import time
import threading
from typing import Optional, Callable, Literal

# ========== CONFIGURATION ==========

# ESP32 Master Hardware Configuration
# Master ESP32 MAC Address: 40:22:d8:eb:1f:88
# The master ESP32 receives commands from Raspberry Pi and forwards them
# via ESP-NOW to 4 slave ESP32 units controlling wheel transformation servos.
MASTER_ESP32_MAC = '40:22:d8:eb:1f:88'

# Serial port settings
DEFAULT_PORT = '/dev/serial0'  # Raspberry Pi GPIO UART
DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT = 1.0

# Command definitions (matching ESP32 master code)
# Raspberry Pi sends these on/off commands for wheel-to-leg conversion:
#   - OPEN (1): Transform wheels to legs ("on" conversion)
#   - CLOSE (2): Transform legs back to wheels ("off" conversion)
#   - STOP (0): Halt any ongoing transformation
CMD_STOP = 0
CMD_OPEN = 1
CMD_CLOSE = 2

# Default speeds
DEFAULT_SPEED = 100

# ===================================


class ESP32Controller:
    """
    Controller for communicating with ESP32 Master for wheel transformation.
    
    Features:
    - Serial/UART communication
    - JSON command protocol
    - Status monitoring
    - Async command sending
    - Connection management
    
    Usage:
        esp32 = ESP32Controller(port='/dev/serial0', baudrate=115200)
        esp32.connect()
        esp32.open_wheels(speed=100)
        time.sleep(3)
        esp32.close_wheels(speed=100)
        esp32.disconnect()
    """
    
    def __init__(self, 
                 port: str = DEFAULT_PORT,
                 baudrate: int = DEFAULT_BAUDRATE,
                 timeout: float = DEFAULT_TIMEOUT,
                 auto_connect: bool = True):
        """
        Initialize ESP32 controller.
        
        Args:
            port: Serial port (e.g., '/dev/serial0', '/dev/ttyUSB0', 'COM3')
            baudrate: Baud rate (must match ESP32 Serial.begin())
            timeout: Serial read timeout in seconds
            auto_connect: Automatically connect on initialization
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        
        self._serial: Optional[serial.Serial] = None
        self._connected = False
        self._last_command = None
        self._last_command_time = 0
        
        # Callbacks
        self.on_response: Optional[Callable[[dict], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
        # Background reading thread
        self._read_thread: Optional[threading.Thread] = None
        self._running = False
        
        print(f"[ESP32Controller] Initialized (port={port}, baud={baudrate})")
        
        if auto_connect:
            self.connect()
    
    def connect(self) -> bool:
        """
        Connect to ESP32 via serial port.
        
        Returns:
            True if connection successful, False otherwise
        """
        if self._connected:
            print("[ESP32Controller] Already connected")
            return True
        
        try:
            self._serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                write_timeout=self.timeout
            )
            
            # Wait for ESP32 to reset after serial connection
            time.sleep(2)
            
            # Flush any startup messages
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
            
            self._connected = True
            print(f"[ESP32Controller] Connected to {self.port}")
            
            # Start reading thread
            self._start_read_thread()
            
            return True
            
        except serial.SerialException as e:
            print(f"[ESP32Controller] Connection failed: {e}")
            if self.on_error:
                self.on_error(f"Connection failed: {e}")
            self._connected = False
            return False
    
    def disconnect(self):
        """Disconnect from ESP32."""
        if not self._connected:
            return
        
        print("[ESP32Controller] Disconnecting...")
        
        # Stop read thread
        self._running = False
        if self._read_thread:
            self._read_thread.join(timeout=2.0)
        
        # Close serial connection
        if self._serial:
            try:
                self._serial.close()
            except Exception as e:
                print(f"[ESP32Controller] Error closing serial: {e}")
        
        self._connected = False
        print("[ESP32Controller] Disconnected")
    
    def _start_read_thread(self):
        """Start background thread to read ESP32 responses."""
        if self._read_thread and self._read_thread.is_alive():
            return
        
        self._running = True
        self._read_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._read_thread.start()
    
    def _read_loop(self):
        """Background loop to read ESP32 responses."""
        while self._running and self._connected:
            try:
                if self._serial and self._serial.in_waiting > 0:
                    line = self._serial.readline().decode('utf-8').strip()
                    if line:
                        self._process_response(line)
                time.sleep(0.1)
            except Exception as e:
                if self._running:  # Only log if not shutting down
                    print(f"[ESP32Controller] Read error: {e}")
    
    def _process_response(self, line: str):
        """
        Process response from ESP32.
        
        Args:
            line: Response line from ESP32
        """
        try:
            # Try to parse as JSON
            data = json.loads(line)
            print(f"[ESP32Controller] Response: {data}")
            
            if self.on_response:
                self.on_response(data)
                
        except json.JSONDecodeError:
            # Not JSON, just a text message
            print(f"[ESP32Controller] ESP32: {line}")
    
    def _send_command(self, command_id: int, speed: int = DEFAULT_SPEED) -> bool:
        """
        Send command to ESP32.
        
        Args:
            command_id: Command ID (CMD_STOP, CMD_OPEN, CMD_CLOSE)
            speed: Speed value (0-100)
        
        Returns:
            True if sent successfully, False otherwise
        """
        if not self._connected or not self._serial:
            print("[ESP32Controller] Not connected")
            if self.on_error:
                self.on_error("Not connected to ESP32")
            return False
        
        # Clamp speed to valid range
        speed = max(0, min(100, speed))
        
        # Create command JSON
        command = {
            "cmd": command_id,
            "speed": speed
        }
        
        try:
            # Send as JSON line
            command_str = json.dumps(command) + '\n'
            self._serial.write(command_str.encode('utf-8'))
            self._serial.flush()
            
            # Update state
            self._last_command = command_id
            self._last_command_time = time.time()
            
            cmd_name = {CMD_STOP: "STOP", CMD_OPEN: "OPEN", CMD_CLOSE: "CLOSE"}.get(command_id, "UNKNOWN")
            print(f"[ESP32Controller] Sent: {cmd_name} (speed={speed})")
            
            return True
            
        except serial.SerialException as e:
            print(f"[ESP32Controller] Send error: {e}")
            if self.on_error:
                self.on_error(f"Send error: {e}")
            return False
    
    def open_wheels(self, speed: int = DEFAULT_SPEED) -> bool:
        """
        Send OPEN command to transform wheels to legs.
        
        Args:
            speed: Transformation speed (0-100)
        
        Returns:
            True if command sent successfully
        """
        print(f"[ESP32Controller] Opening wheels (speed={speed})")
        return self._send_command(CMD_OPEN, speed)
    
    def close_wheels(self, speed: int = DEFAULT_SPEED) -> bool:
        """
        Send CLOSE command to transform legs back to wheels.
        
        Args:
            speed: Transformation speed (0-100)
        
        Returns:
            True if command sent successfully
        """
        print(f"[ESP32Controller] Closing wheels (speed={speed})")
        return self._send_command(CMD_CLOSE, speed)
    
    def stop(self) -> bool:
        """
        Send STOP command to halt all transformations.
        
        Returns:
            True if command sent successfully
        """
        print("[ESP32Controller] Stopping transformation")
        return self._send_command(CMD_STOP, 0)
    
    def get_status(self) -> dict:
        """
        Get current controller status.
        
        Returns:
            Dictionary with status information
        """
        return {
            'connected': self._connected,
            'port': self.port,
            'last_command': self._last_command,
            'last_command_time': self._last_command_time,
            'time_since_last_command': time.time() - self._last_command_time if self._last_command_time > 0 else None
        }
    
    def is_connected(self) -> bool:
        """Check if connected to ESP32."""
        return self._connected
    
    def cleanup(self):
        """Clean up resources."""
        print("[ESP32Controller] Cleaning up...")
        self.disconnect()
        print("[ESP32Controller] Cleanup complete")


# ========== DEMO / TESTING ==========
if __name__ == '__main__':
    """
    Demo usage of ESP32 controller.
    Run this script to test communication with ESP32.
    """
    import sys
    import signal
    
    print("=" * 60)
    print("ESP32 CONTROLLER TEST")
    print("=" * 60)
    print(f"Port: {DEFAULT_PORT}")
    print(f"Baud Rate: {DEFAULT_BAUDRATE}")
    print("=" * 60)
    print("\nMake sure ESP32 Master is connected and powered on!\n")
    
    # Create controller
    esp32 = ESP32Controller(port=DEFAULT_PORT, baudrate=DEFAULT_BAUDRATE)
    
    # Handle Ctrl+C
    def signal_handler(sig, frame):
        print("\n[Main] Interrupt received, shutting down...")
        esp32.cleanup()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        if not esp32.is_connected():
            print("✗ Failed to connect to ESP32")
            print(f"\nTroubleshooting:")
            print(f"1. Check ESP32 is powered on")
            print(f"2. Verify serial connection (TX→RX, RX→TX, GND→GND)")
            print(f"3. Try different port: /dev/ttyUSB0, /dev/ttyACM0, COM3, etc.")
            print(f"4. Check baud rate matches ESP32 code (115200)")
            sys.exit(1)
        
        print("✓ Connected to ESP32\n")
        
        # Test sequence
        print("Test 1: Opening wheels...")
        esp32.open_wheels(speed=100)
        time.sleep(5)
        
        print("\nTest 2: Closing wheels...")
        esp32.close_wheels(speed=100)
        time.sleep(5)
        
        print("\nTest 3: Opening at 50% speed...")
        esp32.open_wheels(speed=50)
        time.sleep(3)
        
        print("\nTest 4: Stopping...")
        esp32.stop()
        time.sleep(1)
        
        print("\nTest 5: Closing wheels...")
        esp32.close_wheels(speed=100)
        time.sleep(5)
        
        print("\n✓ All tests completed!")
        print(f"\nStatus: {esp32.get_status()}")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        esp32.cleanup()
        print("\n[Main] Goodbye!")
