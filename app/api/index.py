from flask import Blueprint, jsonify

index_bp = Blueprint('index', __name__)


@index_bp.route('/')
def index():
    """healthcheck endpoint"""
    return jsonify({'message': 'Healthy'}), 200
