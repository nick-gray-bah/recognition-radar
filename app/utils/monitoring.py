import os
import cv2
from deepface import DeepFace
import datetime
import logging
from app.models import Stream, Target, Contact
from app.utils.monitoring import process_frame, upload_to_s3, send_email_alert, send_sms_alert
from app import db
from flask import current_app as app

from app.utils.storage import upload_to_s3
from app.utils.notifications import send_email_alert, send_sms_alert

logger = logging.getLogger(__name__)


def get_target_embeddings():
    """Retrieve all target embeddings from the database."""
    target_embeddings = {}
    try:
        # Fetch all targets from the database
        targets = Target.query.all()

        # Map target_id to embedding for each target
        for target in targets:
            if target.embedding:
                target_embeddings[target.target_id] = target.embedding

        logger.info(
            f"Loaded {len(target_embeddings)} target embeddings from the database.")
    except Exception as e:
        logger.error(f"Error retrieving target embeddings: {str(e)}")

    return target_embeddings


def get_notification_contacts():
    """Retrieve all notification contacts from the database."""
    contacts = []
    try:
        # Fetch all contacts from the database
        # Assuming only active contacts should be notified
        contacts_data = Contact.query.filter_by(active=True).all()

        # Collect contact emails and phone numbers
        for contact in contacts_data:
            if contact.contact_email:
                contacts.append({'email': contact.contact_email})
            if contact.contact_phone:
                contacts.append({'phone': contact.contact_phone})

        logger.info(
            f"Loaded {len(contacts)} notification contacts from the database.")
    except Exception as e:
        logger.error(f"Error retrieving notification contacts: {str(e)}")

    return contacts


def process_frame(frame, stream_id, target_embeddings):
    """Process a video frame to detect and recognize faces."""
    # Retrieve recognition configuration from Flask app config
    RECOGNITION_MODEL = app.config['MODEL_NAME']
    DISTANCE_METRIC = app.config['DISTANCE_METRIC']
    THRESHOLD = float(app.config['THRESHOLD'])

    try:
        # Detect faces
        faces = DeepFace.extract_faces(frame, enforce_detection=False)

        matched_targets = []

        for face in faces:
            if face['confidence'] < 0.5:  # Skip low confidence detections
                continue

            face_img = face['face']
            embedding = DeepFace.represent(face_img, model_name=RECOGNITION_MODEL)[0]['embedding']

            # Compare with all target embeddings
            for target_id, target_embedding in target_embeddings.items():
                distance = 0
                if DISTANCE_METRIC == 'cosine':
                    distance = DeepFace.dst.findCosineDistance(
                        embedding, target_embedding)
                elif DISTANCE_METRIC == 'euclidean':
                    distance = DeepFace.dst.findEuclideanDistance(
                        embedding, target_embedding)
                elif DISTANCE_METRIC == 'euclidean_l2':
                    distance = DeepFace.dst.findEuclideanDistance(
                        DeepFace.dst.l2_normalize(embedding),
                        DeepFace.dst.l2_normalize(target_embedding)
                    )

                if distance <= THRESHOLD:
                    matched_targets.append(target_id)
                    logger.info(
                        f"Target {target_id} identified in stream {stream_id} (distance: {distance:.4f})")

        return matched_targets
    except Exception as e:
        logger.error(f"Error processing frame: {str(e)}")
        return []


logger = logging.getLogger(__name__)


def monitor_stream(stream_id, stream_url):
    """Monitor a video stream for target faces."""
    logger.info(f"Starting monitoring for stream {stream_id}: {stream_url}")

    TEMP_VIDEO_DIR = 'temp_videos'
    S3_BUCKET = app.config['AWS']['BUCKET_NAME']

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        logger.error(f"Failed to open stream: {stream_url}")
        return

    # Define output video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(TEMP_VIDEO_DIR, f"{stream_id}_{timestamp}.avi")
    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    out = cv2.VideoWriter(out_path, fourcc, 20.0, (frame_width, frame_height))

    recording = False
    detected_targets = set()
    frame_count = 0
    alert_sent = False

    try:
        # Query the stream from the database
        stream = Stream.query.filter_by(
            stream_id=stream_id, active=True).first()
        if not stream:
            logger.error(
                f"Stream {stream_id} is no longer active or doesn't exist in the database.")
            return

        # Get all target embeddings from the database
        target_embeddings = get_target_embeddings()

        # Get all notification contacts from the database
        notification_contacts = get_notification_contacts()

        while stream.active:
            ret, frame = cap.read()
            if not ret:
                logger.warning(f"Failed to read frame from stream {stream_id}")
                break

            frame_count += 1

            # Process only every 15 frames to reduce CPU usage
            if frame_count % 15 == 0:
                matched_targets = process_frame(
                    frame, stream_id, target_embeddings)

                if matched_targets and not recording:
                    recording = True
                    detected_targets = set(matched_targets)
                    logger.info(
                        f"Started recording for targets: {detected_targets}")

                elif matched_targets and recording:
                    detected_targets.update(matched_targets)

            # If recording, save frame to video
            if recording:
                # Draw boxes around faces
                try:
                    faces = DeepFace.extract_faces(
                        frame, enforce_detection=False)
                    for face in faces:
                        if face['confidence'] < 0.5:
                            continue
                        facial_area = face['facial_area']
                        x, y, w, h = facial_area['x'], facial_area['y'], facial_area['w'], facial_area['h']
                        cv2.rectangle(frame, (x, y), (x+w, y+h),
                                      (0, 255, 0), 2)
                except Exception as e:
                    logger.error(f"Error drawing face boxes: {str(e)}")

                out.write(frame)

            # Send alert if we've been recording for 5+ seconds and haven't sent an alert yet
            if recording and not alert_sent and frame_count > 150:  # 5 seconds at 30fps
                targets_str = ', '.join(detected_targets)
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Finish and save the current video segment
                out.release()

                # Upload video to S3
                s3_object_name = f"alerts/{stream_id}/{targets_str}_{timestamp}.avi"
                video_url = upload_to_s3(out_path, s3_object_name, app.config)

                if video_url:
                    # Send alerts
                    send_email_alert(targets_str, current_time,
                                     video_url, notification_contacts, app.config)
                    send_sms_alert(targets_str, current_time,
                                   video_url, notification_contacts, app.config)
                    alert_sent = True

                    # Start a new video segment
                    out = cv2.VideoWriter(
                        out_path, fourcc, 20.0, (frame_width, frame_height))

        # After monitoring stops, update the database to mark the stream as inactive
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
