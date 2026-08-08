from ultralytics import YOLO
import cv2

# Load YOLOv8 model
model = YOLO("yolov8n.pt")

# Open webcam
cap = cv2.VideoCapture(1)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    annotated_frame = results[0].plot()

    # Print detections
    # for box in results[0].boxes:
    #     try:
    #         class_id = int(box.cls)
    #         conf = float(box.conf)
    #         name = model.names[class_id]
    #         print(f"Detected: {name} ({conf:.2f})")
    #     except:
    #         pass

    # Save the latest frame (headless mode)
    # cv2.imwrite("last_detection.jpg", annotated_frame)
    
    # Display the resulting frame
    cv2.imshow('Detector Feed', annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
    
cap.release()
cv2.destroyAllWindows()