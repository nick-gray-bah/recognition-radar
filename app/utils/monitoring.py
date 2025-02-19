import os
import cv2
import logging
import datetime
from flask import current_app as app
from deepface import DeepFace
from app.models import Contact, Stream
from app.utils.storage import upload_to_s3
from app.utils.notifications import send_email_alert, send_sms_alert
from app import db

logger = logging.getLogger(__name__)


def monitor_stream(stream_id, stream_url):
    """Monitor a video stream, extract frames, and use DeepFace's find() to detect known individuals."""
    logger.info(f"Starting monitoring for stream {stream_id}: {stream_url}")

    TEMP_VIDEO_DIR = "temp_videos"
    os.makedirs(TEMP_VIDEO_DIR, exist_ok=True)

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        logger.error(f"Failed to open stream: {stream_url}")
        return

    frame_count = 0
    detected_targets = set()
    alert_sent = False

    # Define video recording settings
    fourcc = cv2.VideoWriter.fourcc(*"XVID")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(TEMP_VIDEO_DIR, f"{stream_id}_{timestamp}.avi")
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(out_path, fourcc, 20.0, (frame_width, frame_height))

    try:
        stream = Stream.query.filter_by(
            stream_id=stream_id, active=True).first()
        if not stream:
            logger.error(
                f"Stream {stream_id} is no longer active or doesn't exist in the database.")
            return

        while stream.active:
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from stream {stream_id}")
                break

            frame_count += 1

            # Process every 15 frames to reduce computational load
            if frame_count % 15 == 0:
                try:
                    results = DeepFace.find(
                        img_path=frame,
                        db_path=app.config["TARGET_DIR"],
                        model_name=app.config["RECOGNITION"]["MODEL_NAME"],
                        distance_metric=app.config["RECOGNITION"]["DISTANCE_METRIC"],
                        detector_backend=app.config["RECOGNITION"]["DETECTOR_BACKEND"],
                        enforce_detection=False,
                        silent=True,
                    )

                    if results and not results[0].empty:
                        matched_targets = set(results[0]["identity"].tolist())

                        if matched_targets:
                            detected_targets.update(matched_targets)
                            logger.info(
                                f"Detected individuals: {matched_targets} in stream {stream_id}")

                            # Start recording if not already
                            # if not alert_sent:
                            #     alert_sent = True

                            #     # Save video recording
                            #     out.release()
                            #     s3_object_name = f"alerts/{stream_id}/{timestamp}.avi"
                            #     video_url = upload_to_s3(
                            #         out_path, s3_object_name, app.config)

                            #     # Get notification contacts
                            #     notification_contacts = [
                            #         contact for contact in Contact.query.all()]

                            #     # Send alerts
                            #     if video_url:
                            #         send_email_alert(
                            #             detected_targets, timestamp, video_url, notification_contacts, app.config)
                            #         send_sms_alert(
                            #             detected_targets, timestamp, video_url, notification_contacts, app.config)

                            #     # Start new video segment
                            #     out = cv2.VideoWriter(
                            #         out_path, fourcc, 20.0, (frame_width, frame_height))

                except Exception as e:
                    logger.error(f"Error processing frame: {str(e)}")

            # Save frames if alert has been triggered
            if alert_sent:
                out.write(frame)

        # Mark stream as inactive in the database
        stream.active = False
        db.session.commit()
        logger.info(f"Stopped monitoring stream {stream_id}")

    except Exception as e:
        logger.error(f"Error monitoring stream {stream_id}: {str(e)}")
    finally:
        cap.release()
        out.release()

        if stream:
            stream.active = False
            db.session.commit()
