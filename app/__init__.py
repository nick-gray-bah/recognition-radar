from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config_dict
from app.api import register_blueprints

db = SQLAlchemy()

def create_app(config_name="development"):
    print('Initializing Flask app...')
    app = Flask(__name__)

    # Load configuration from config.py
    app.config.from_object(config_dict.get(config_name, "development"))

    # Initialize the database
    db.init_app(app)

    # Register routes
    register_blueprints(app)

    # Initialize the database (create tables)
    with app.app_context():
        db.create_all()

    return app
