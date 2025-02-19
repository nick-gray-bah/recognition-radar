import logging
import os
import uuid
from flask import Blueprint, current_app as app, jsonify, request
from werkzeug.utils import secure_filename
from deepface import DeepFace

from app import db
from app.models import Target

logger = logging.getLogger(__name__)
targets_bp = Blueprint('targets', __name__)


@targets_bp.route('/api/targets', methods=['GET'])
def get_targets():
    """Get the list of target individuals."""
    try:
        targets = Target.query.all()
        return jsonify([target.to_dict() for target in targets])
    except Exception as e:
        logger.error(f"Error fetching targets: {str(e)}")
        return jsonify({'error': str(e)}), 500


@targets_bp.route('/api/targets', methods=['POST'])
def add_target():
    """Add a new target individual."""
    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400

    file = request.files['image']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if 'target_name' not in request.form:
        return jsonify({'error': 'No target name provided'}), 400

    target_name = request.form['target_name']
    target_id = str(uuid.uuid4())

    TARGET_DIR = app.config['TARGET_DIR']
    RECOGNITION_MODEL = app.config['RECOGNITION_MODEL']

    try:
        filename = secure_filename(
            f"{target_name}{os.path.splitext(file.filename)[1]}")
        target_path = os.mkdir(target_name)
        filepath = os.path.join(TARGET_DIR, target_path, filename)
        file.save(filepath)

        embedding = DeepFace.represent(filepath, model_name=RECOGNITION_MODEL)[
            0]['embedding']

        new_target = Target(target_id=target_id, target_name=target_name,
                            embedding=embedding, target_path=target_path)
        db.session.add(new_target)
        db.session.commit()

        logger.info(f"Added new target: {target_id}")
        return jsonify({'success': True, 'target_id': target_id})

    except Exception as e:
        logger.error(f"Error adding target {target_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


@targets_bp.route('/api/targets/<target_id>', methods=['DELETE'])
def remove_target(target_id):
    """Remove a target individual."""
    try:
        target = Target.query.filter_by(target_id=target_id).first()
        if not target:
            return jsonify({'error': 'Target not found'}), 404

        db.session.delete(target)
        db.session.commit()

        if os.path.exists(target.image_path):
            os.remove(target.image_path)

        logger.info(f"Removed target: {target_id}")
        return jsonify({'success': True})

    except Exception as e:
        logger.error(f"Error removing target {target_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500
