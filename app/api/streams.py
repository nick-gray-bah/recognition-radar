import uuid
import datetime
import threading
import logging
import cv2
from flask import Blueprint, request, jsonify, current_app as app
from app import db
from app.models import Stream

from app.api.utils import validate_active_field
from app.stream_monitor import StreamMonitor

logger = logging.getLogger(__name__)
streams_bp = Blueprint('streams', __name__)

# tracks all active StreamMonitor instances
active_streams = {}

@streams_bp.route('/streams/activate', methods=['PUT'])
def activate_stream():
    """activate or deactivate existing stream"""
    data = request.json
    if not data or 'stream_url' not in data:
        return jsonify({'error': 'Missing required field: stream_url'}), 400

    active = validate_active_field(data['active'])

    if active is None:
        return jsonify({'error': "invalid value for 'active', must be boolean"}), 400

    stream_url = data['stream_url']

    try:
        existing_stream = Stream.query.filter_by(stream_url=stream_url).first()

        if not existing_stream:
            return jsonify({
                'message': f"Stream with URL {stream_url} does not exist",
            }), 404

        if active == True:
            # update Stream in db to active
            existing_stream.active = True
            existing_stream.started_at = datetime.datetime.utcnow()
            db.session.commit()

            # create new StreamMonitor
            active_app = app._get_current_object()
            new_stream = StreamMonitor(
                active_app, existing_stream.stream_id, existing_stream.stream_url)
            new_stream.run()
            active_streams[new_stream.stream_id] = new_stream
            print(active_streams)

            return jsonify({'message': f"Stream with URL {stream_url} activated", }), 200

        if active == False:
            # update Stream in db to inactive
            existing_stream.active = False
            db.session.commit()

            # delete associated StreamMonitor
            stream = active_streams.pop(
                existing_stream.stream_id, None)
            if stream:
                stream.stop()
            print(active_streams)

            return jsonify({'message': f"Stream with URL {stream_url} deactivated", }), 200

    except Exception as e:
        logger.warning(e)
        return jsonify('internal server error'), 500


@streams_bp.route('/streams', methods=['POST'])
def add_stream():
    """Add a new video stream to monitor or reactivate an existing one."""

    data = request.json
    if not data or 'stream_url' not in data:
        return jsonify({'error': 'Missing stream_url'}), 400

    stream_url = data['stream_url']

    try:
        existing_stream = Stream.query.filter_by(stream_url=stream_url).first()

        if existing_stream:
            return jsonify({
                'message': f"Stream with URL {stream_url} already exists",
                'stream_id': existing_stream.stream_id,
                'active': existing_stream.active
            }), 200

        # create new Stream in db
        stream_id = str(uuid.uuid4())
        new_stream = Stream(
            stream_id=stream_id,
            stream_url=stream_url,
            active=True,
            started_at=datetime.datetime.utcnow()
        )
        db.session.add(new_stream)
        db.session.commit()

        # create new StreamMonitor
        active_app = app._get_current_object()
        new_stream = StreamMonitor(
            active_app, stream_id, stream_url)
        new_stream.run()
        active_streams[stream_id] = new_stream
        logger.info(active_streams)

        logger.info(f"Started monitoring stream: {stream_id} ({stream_url})")
        return jsonify({
            'message': f"Started monitoring stream with URL {stream_url}",
            'stream_id': stream_id,
            'status': 'active'
        }), 201

    except Exception as e:
        logger.error(f"Error adding stream with URL {stream_url}: {str(e)}")
        return jsonify({'error': 'failed to add new stream'}), 500
