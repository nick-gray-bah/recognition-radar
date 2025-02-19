from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config_dict

db = SQLAlchemy()

# Function to create the Flask app
def create_app(config_name="development"):
    print('Initializing Flask app...')
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object(config_dict.get(config_name, "development"))

    # Initialize the database with the app
    db.init_app(app)

    # Register Blueprints for routing
    from app.api import register_blueprints
    register_blueprints(app)

    # Initialize the database (create tables)
    with app.app_context():
        db.create_all()

    return app
