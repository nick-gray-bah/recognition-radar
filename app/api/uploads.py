import os
import logging
import cv2
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from deepface import DeepFace

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)

# This doesn't make sense to me not sure what this one is for
# Doesn't store anything just extracts and returns length?
# is this supposed to be the example of the video stream?


@upload_bp.route('/upload_video', methods=['POST'])
def upload_video():
    """Process a video file to extract target faces."""
    if 'video' not in request.files or 'target_id' not in request.form:
        return jsonify({'error': 'Missing video file or target ID'}), 400

    file = request.files['video']
    target_id = request.form['target_id']
    video_path = os.path.join(current_app.config['TEMP_VIDEO_DIR'], secure_filename(file.filename))
    file.save(video_path)

    try:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return jsonify({'error': 'Could not open video file'}), 400

        frame_count = 0
        extracted_faces = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            if frame_count % 30 == 0:
                faces = DeepFace.extract_faces(frame, enforce_detection=False)
                extracted_faces.extend(
                    [face['face'] for face in faces if face['confidence'] >= 0.5])

        cap.release()

        if not extracted_faces:
            return jsonify({'error': 'No faces detected in the video'}), 400

        return jsonify({'success': True, 'target_id': target_id, 'faces_extracted': len(extracted_faces)})
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        return jsonify({'error': str(e)}), 500
