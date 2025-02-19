from flask import Blueprint, request, jsonify
from app import db
from app.models import Contact
from .utils import validate_input
import re

contacts_bp = Blueprint('contacts', __name__)


def is_valid_email(email):
    """
    Validate email format using regular expression (simple version).
    """
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(email_regex, email) is not None


@contacts_bp.route('/add_contact', methods=['POST'])
def add_contact():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['contact_name', 'contact_email']
        is_valid, error_message = validate_input(data, required_fields)
        if not is_valid:
            return jsonify({'error': error_message}), 400

        # Validate contact_name (ensure it's not empty)
        if not data['contact_name'].strip():
            return jsonify({'error': 'Contact name cannot be empty'}), 400

        # Validate email format
        if not is_valid_email(data['contact_email']):
            return jsonify({'error': 'Invalid email format'}), 400

        # Check for existing contact (avoid duplicate emails)
        existing_contact = Contact.query.filter_by(
            contact_email=data['contact_email']).first()
        if existing_contact:
            return jsonify({'error': 'Contact with this email already exists'}), 400

        new_contact = Contact(
            contact_name=data['contact_name'], contact_email=data['contact_email'], active=True)
        db.session.add(new_contact)
        db.session.commit()

        return jsonify({'message': 'Contact added!', 'contact': f'{new_contact.to_dict()}'}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@contacts_bp.route('/contacts', methods=['GET'])
def get_contacts():
    try:
        contacts = Contact.query.all()
        return jsonify([c.to_dict() for c in contacts])

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@contacts_bp.route('/contacts/<int:id>', methods=['GET'])
def get_contact_by_id(id):
    try:
        contact = Contact.query.get(id)
        if not contact:
            return jsonify({'error': 'Contact not found'}), 404
        return jsonify(contact.to_dict())

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@contacts_bp.route('/contacts/<int:id>', methods=['DELETE'])
def delete_contact(id):
    try:
        contact = Contact.query.get(id)
        if not contact:
            return jsonify({'error': 'Contact not found'}), 404
        db.session.delete(contact)
        db.session.commit()
        return jsonify({'message': 'Contact deleted'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
