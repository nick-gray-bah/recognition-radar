import os
import sys
import cv2
import numpy as np
import threading
import queue
from deepface import DeepFace

# Queue to store frames
frame_queue = queue.Queue(maxsize=60)
output_queue = queue.Queue(maxsize=60)

# Initialize webcam
cap = cv2.VideoCapture(0)

# Dictionary to store reference face embeddings and their corresponding names
reference_faces = {}

def upload_reference_images():
    """Loads multiple reference images and generates embeddings."""
    reference_images = {
        "nick": "img/nick.jpg",
        "thomas": "img/thomas.jpg",
    }

    for name, image_path in reference_images.items():
        if not os.path.exists(image_path):
            print(f"Error: The file '{image_path}' does not exist.")
            sys.exit(1)

        try:
            result = DeepFace.represent(image_path, model_name="Facenet", enforce_detection=True)[0]
            reference_faces[name] = result['embedding']
            print(f"Reference embedding for {name} generated successfully with confidence: {result['face_confidence']}.")
        except Exception as e:
            print(f"Error processing reference image {name}: {e}")
            sys.exit(1)

def video_capture():
    """Captures frames from webcam and sends them to the queue."""
    if not cap.isOpened():
        print("Error: Could not open webcam.")
        sys.exit(1)

    while True:
        ret, frame = cap.read()
        if not ret or frame is None:
            print("Failed to capture a valid frame. Retrying...")
            continue

        if frame_queue.full():
            frame_queue.get()
        frame_queue.put(frame)

def face_recognition():
    """Processes frames, detects faces, and identifies them."""
    while True:
        if not frame_queue.empty():
            frame = frame_queue.get()

            try:
                detected_faces = DeepFace.extract_faces(frame, detector_backend="opencv")

                if detected_faces:
                    for face_info in detected_faces:
                        face_img = face_info["face"]
                        facial_area = face_info["facial_area"]
                        x, y, w, h = (facial_area[key] for key in ("x", "y", "w", "h"))

                        try:
                            result = DeepFace.represent(face_img, model_name="Facenet", enforce_detection=False)[0]

                            min_distance = float('inf')
                            label = "Unknown"
                            
                            for name, reference_embedding in reference_faces.items():
                                distance = np.linalg.norm(np.array(reference_embedding) - np.array(result['embedding']))
                                if distance < min_distance:
                                    min_distance = distance
                                    label = f'name: {name} confidence: {result['face_confidence']}'

                            color = (0, 255, 0) if label != "Unknown" else (0, 0, 255)

                        except Exception as e:
                            print("Face embedding error:", e)
                            label = "Unknown"
                            color = (0, 0, 255)

                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)

            except Exception as e:
                print("Face recognition error:", e)

            # Always send frame to output_queue, even if no face was detected
            if output_queue.full():
                output_queue.get()
            output_queue.put(frame)

def main():
    """Main function to start facial recognition."""
    print("Starting facial recognition app...")

    # Upload reference images and generate embeddings
    upload_reference_images()

    # Start background threads
    capture_thread = threading.Thread(target=video_capture, daemon=True)
    recognition_thread = threading.Thread(target=face_recognition, daemon=True)

    capture_thread.start()
    recognition_thread.start()

    # Run display in the main thread
    while True:
        if not output_queue.empty():
            frame = output_queue.get()

            if frame is None or frame.size == 0:
                print("Warning: Empty frame received. Skipping...")
                continue

            cv2.imshow("Webcam Stream", frame)

        # Break on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Exiting...")
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    sys.exit(0)

if __name__ == "__main__":
    main()
