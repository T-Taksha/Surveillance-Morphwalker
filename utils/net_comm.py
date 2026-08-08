"""
Simple networking helpers:
- HTTP POST helper (requests)
- Optional MQTT client wrapper using paho-mqtt

This module is lightweight: it provides simple functions you can call from controller.py
to notify a PC / cloud server about events (e.g., object detected) or to publish via MQTT.

NOTE:
- Install dependencies if you use features:
    pip install requests
    pip install paho-mqtt
"""

import json
import threading
from typing import Callable, Optional

# HTTP helper uses requests (install if needed)
try:
    import requests
    _REQUESTS_AVAILABLE = True
except Exception:
    _REQUESTS_AVAILABLE = False

# MQTT helper uses paho.mqtt.client
try:
    import paho.mqtt.client as mqtt  # type: ignore
    _MQTT_AVAILABLE = True
except Exception:
    _MQTT_AVAILABLE = False


def send_http_post(url: str, payload: dict, timeout: float = 3.0) -> Optional[dict]:
    """
    Send a JSON HTTP POST. Returns parsed JSON response if available.
    Non-blocking option: caller can wrap this call in a Thread if desired.

    Example:
        send_http_post("http://192.168.1.10:5001/event", {"event": "detected", "label":"bottle"})
    """
    if not _REQUESTS_AVAILABLE:
        raise RuntimeError("requests library not installed. Run: pip install requests")

    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            return {"status_code": resp.status_code, "text": resp.text}
    except Exception as e:
        # In production, replace prints with proper logging
        print(f"[net_comm] HTTP POST failed: {e}")
        return None


# ========== MQTT Wrapper ==========
class SimpleMQTTClient:
    """
    Tiny MQTT client to publish messages and optionally subscribe.
    Example:
        client = SimpleMQTTClient(broker="192.168.1.100", port=1883, client_id="robot01")
        client.connect()
        client.publish("robot/events", {"event":"detected","label":"bottle"})
        client.disconnect()
    """
    def __init__(self, broker: str = "localhost", port: int = 1883, client_id: str = None, keepalive: int = 60):
        if not _MQTT_AVAILABLE:
            raise RuntimeError("paho-mqtt not installed. Run: pip install paho-mqtt")

        self.broker = broker
        self.port = port
        self.client_id = client_id
        self.keepalive = keepalive
        self._client = mqtt.Client(client_id) if client_id else mqtt.Client()
        self._is_connected = False
        # user callbacks
        self.on_message_callback: Optional[Callable[[str, bytes], None]] = None

        # internal bindings
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.on_disconnect = self._on_disconnect

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._is_connected = True
            print(f"[net_comm][MQTT] Connected to {self.broker}:{self.port}")
        else:
            print(f"[net_comm][MQTT] Bad connection, rc={rc}")

    def _on_disconnect(self, client, userdata, rc):
        self._is_connected = False
        print("[net_comm][MQTT] Disconnected")

    def _on_message(self, client, userdata, msg):
        if self.on_message_callback:
            try:
                self.on_message_callback(msg.topic, msg.payload)
            except Exception as e:
                print(f"[net_comm][MQTT] on_message_callback error: {e}")

    def connect(self, keepalive: Optional[int] = None, blocking: bool = True):
        """Connect to broker. If blocking=False, connection runs in background thread."""
        if keepalive is None:
            keepalive = self.keepalive

        def _run():
            try:
                self._client.connect(self.broker, self.port, keepalive)
                self._client.loop_forever()
            except Exception as e:
                print(f"[net_comm][MQTT] Connection error: {e}")

        if blocking:
            _run()
        else:
            t = threading.Thread(target=_run, daemon=True)
            t.start()

    def publish(self, topic: str, payload: dict, qos: int = 0, retain: bool = False):
        """Publish JSON-serializable payload."""
        if not self._is_connected:
            # try a single attempt to connect (blocking connect)
            try:
                self._client.connect(self.broker, self.port, self.keepalive)
                self._client.loop_start()
                self._is_connected = True
            except Exception as e:
                print(f"[net_comm][MQTT] Could not connect to publish: {e}")
                return False

        try:
            body = json.dumps(payload)
            self._client.publish(topic, body, qos=qos, retain=retain)
            return True
        except Exception as e:
            print(f"[net_comm][MQTT] Publish failed: {e}")
            return False

    def subscribe(self, topic: str, qos: int = 0):
        try:
            self._client.subscribe(topic, qos=qos)
            return True
        except Exception as e:
            print(f"[net_comm][MQTT] Subscribe failed: {e}")
            return False

    def disconnect(self):
        try:
            self._client.disconnect()
            self._client.loop_stop()
        except Exception:
            pass


# Demo usage if run directly
if __name__ == "__main__":
    print("net_comm demo. Requests installed:", _REQUESTS_AVAILABLE, "MQTT available:", _MQTT_AVAILABLE)

    # HTTP demo (only if requests installed)
    if _REQUESTS_AVAILABLE:
        print("HTTP demo skipped (not calling external endpoints).")

    # MQTT demo (only if paho-mqtt installed)
    if _MQTT_AVAILABLE:
        client = SimpleMQTTClient(broker="test.mosquitto.org", client_id="demo_robot_01")
        # Non-blocking connect -> background loop
        client.connect(blocking=False)
        import time
        time.sleep(1)
        client.publish("mini_project/test", {"msg": "hello from robot"})
        time.sleep(1)
        client.disconnect()
    else:
        print("MQTT not available: install paho-mqtt to enable MQTT features.")
