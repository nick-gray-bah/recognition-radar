import uuid
import datetime
import threading
import logging
import cv2
from flask import Blueprint, request, jsonify
from app import db
from app.models import Stream
from app.utils.monitoring import monitor_stream

logger = logging.getLogger(__name__)
streams_bp = Blueprint('streams', __name__)


@streams_bp.route('/streams', methods=['POST'])
def add_stream():
    """Add a new video stream to monitor or reactivate an existing one."""

    data = request.json
    if not data or 'stream_url' not in data:
        return jsonify({'error': 'Missing stream_url'}), 400

    stream_url = data['stream_url']

    # Check if the stream URL already exists
    existing_stream = Stream.query.filter_by(stream_url=stream_url).first()

    # Case 1: Stream already exists and is active
    if existing_stream and existing_stream.active:
        return jsonify({
            'message': f"Stream with URL {stream_url} is already being monitored",
            'stream_id': existing_stream.stream_id,
            'status': 'active'
        }), 200

    # Case 2: Stream exists but is inactive, reactivate it
    if existing_stream and not existing_stream.active:
        existing_stream.active = True
        existing_stream.started_at = datetime.datetime.utcnow()
        db.session.commit()

        # Restart the monitoring thread
        thread = threading.Thread(target=monitor_stream, args=(
            existing_stream.stream_id, stream_url))
        thread.daemon = True
        thread.start()

        logger.info(
            f"Reactivated monitoring for stream: {existing_stream.stream_id} ({stream_url})")
        return jsonify({
            'message': f"Stream with URL {stream_url} has been reactivated",
            'stream_id': existing_stream.stream_id,
            'status': 'active'
        }), 200

    # Case 3: Stream doesn't exist, create a new one
    try:
        cap = cv2.VideoCapture(stream_url)
        if not cap.isOpened():
            return jsonify({'error': f"Could not open stream: {stream_url}"}), 400
        cap.release()

        stream_id = str(uuid.uuid4())
        new_stream = Stream(
            stream_id=stream_id,
            stream_url=stream_url,
            active=True,
            started_at=datetime.datetime.utcnow()
        )
        db.session.add(new_stream)
        db.session.commit()

        # Start stream monitoring in a separate thread
        thread = threading.Thread(
            target=monitor_stream, args=(stream_id, stream_url))
        thread.daemon = True
        thread.start()

        logger.info(f"Started monitoring stream: {stream_id} ({stream_url})")
        return jsonify({
            'message': f"Started monitoring stream with URL {stream_url}",
            'stream_id': stream_id,
            'status': 'active'
        }), 201

    except Exception as e:
        logger.error(f"Error adding stream with URL {stream_url}: {str(e)}")
        return jsonify({'error': str(e)}), 500
