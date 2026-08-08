import cv2
import threading
import time
from flask import Flask, Response, abort

# ===== FORCE LAPTOP WEBCAM =====
WIDTH = 640
HEIGHT = 480
FPS = 30
JPEG_QUALITY = 80
# =============================


class CameraStream:
    # ✅ main.py passes these — we accept them but force webcam anyway
    def __init__(self, device_index=0, width=WIDTH, height=HEIGHT, fps=FPS):
        print("Opening LAPTOP webcam...")

        self.cap = cv2.VideoCapture(1, cv2.CAP_DSHOW)

        if not self.cap.isOpened():
            raise RuntimeError("Laptop webcam not detected")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self.cap.set(cv2.CAP_PROP_FPS, fps)

        self.frame = None
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        self.running = True
        threading.Thread(target=self.update, daemon=True).start()

    def update(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame
            time.sleep(1 / FPS)

    def get_frame_jpeg(self):
        with self.lock:
            if self.frame is None:
                return None

            ret, jpeg = cv2.imencode(
                ".jpg",
                self.frame,
                [int(cv2.IMWRITE_JPEG_QUALITY), JPEG_QUALITY]
            )
            if not ret:
                return None
            return jpeg.tobytes()

    def get_frame_bgr(self):
        with self.lock:
            if self.frame is None:
                return None
            return self.frame.copy()

    def stop(self):
        self.running = False
        self.cap.release()


# ===== WEBSITE STREAM SERVER (used by main.py) =====
app = Flask(__name__)
camera = None


def stream_generator():
    while True:
        frame = camera.get_frame_jpeg()
        if frame is None:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route("/video")
def video():
    if camera is None:
        abort(503)
    return Response(stream_generator(),
                    mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/")
def home():
    return """
    <html>
    <body>
        <h2>Laptop Webcam Stream</h2>
        <img src="/video" width="720">
    </body>
    </html>
    """


if __name__ == "__main__":
    camera = CameraStream()
    camera.start()

    print("Webcam streaming at http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, threaded=True)
