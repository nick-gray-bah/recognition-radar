import os
import queue
import threading
import cv2
import logging
import datetime
from deepface import DeepFace
from app.utils.storage import upload_to_s3
from app.utils.notifications import send_email_alert, send_sms_alert
from app import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class StreamMonitor(threading.Thread):
    def __init__(self, app, stream_id, stream_url=0, max_queue=60, daemon=True):
        super().__init__(daemon=daemon)
        self.app = app
        self.stream_id = stream_id
        self.stream_url = stream_url
        self.active = False
        self.recording = False
        self.empty_frames = 0

        # OpenCV Video Capture
        self.cap = cv2.VideoCapture(int(stream_url))
        if not self.cap.isOpened():
            logger.error(f"Failed to open stream: {stream_url}")
            self.active = False
            return

        # frame queue
        self.queue = queue.Queue(maxsize=max_queue)

        # capture and processing threads
        self.capture_thread = threading.Thread(
            target=self._capture_frames, daemon=True)

        self.process_thread = threading.Thread(
            target=self._process_frames, daemon=True)

        # recordings
        self.video_writer = None
        self.out_path = None

    def _start_recording(self):
        """Start a new recording session."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        save_dir = os.path.join("recordings", str(self.stream_id))
        os.makedirs(save_dir, exist_ok=True)

        self.out_path = os.path.join(save_dir, f"{timestamp}.mp4")
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        self.video_writer = cv2.VideoWriter(
            self.out_path, fourcc, 20.0, (frame_width, frame_height))

        self.recording = True

        logger.info(f"🎥 Started recording: {self.out_path}")

    def _stop_recording(self):
        """Stop the current recording session."""
        if self.video_writer:
            self.video_writer.release()
            logger.info(f"✅ Saved recording: {self.out_path}")
            self.video_writer = None
            self.out_path = None
            # add logic to save the recording to S3 and delete local file

        self.recording = False

    def _capture_frames(self):
        """Continuously capture frames and store them in a queue."""
        while self.active:
            ret, frame = self.cap.read()
            if not ret:
                logger.warning(
                    f"Failed to read frame from stream {self.stream_id}")
                break

            if self.queue.full():
                self.queue.get()
            self.queue.put(frame)

    def _process_frames(self):
      while self.active:
          try:
              frame = self.queue.get(timeout=1)
          except queue.Empty:
              continue

          try:
              results = DeepFace.find(
                  img_path=frame,
                  db_path=self.app.config["TARGET_DIR"],
                  model_name=self.app.config["RECOGNITION_MODEL_NAME"],
                  distance_metric=self.app.config["RECOGNITION_DISTANCE_METRIC"],
                  detector_backend=self.app.config["RECOGNITION_DETECTOR_BACKEND"],
                  enforce_detection=True,  # Force detection
                  silent=True,
              )

              if not results or results[0].empty:
                  raise ValueError("No faces detected in frame")

              for result in results[0].to_dict('records'):
                  x, y, w, h = result['source_x'], result['source_y'], result['source_w'], result['source_h']
                  identity = result.get('identity', 'Unknown').split('/')[1]
                  
                  if identity!= 'Unknown':
                    logger.info(f'hi {identity}')
                  
                  cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                  cv2.putText(frame, identity, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2)

              if not self.recording:
                  self._start_recording()
                  
              self.video_writer.write(frame)
              self.empty_frames = 0

          except Exception as e:
              self.empty_frames += 1
              if self.empty_frames >= 15 and self.recording:
                  self._stop_recording()


    def run(self):
        """Start processing"""
        self.active = True
        self.capture_thread.start()
        self.process_thread.start()

    def stop(self):
        """stop monitoring"""
        self.active = False
        self.capture_thread.join()
        self.process_thread.join()
        self.cap.release()
        if self.recording:
            self._stop_recording()
