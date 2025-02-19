from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import config_dict

db = SQLAlchemy()

from app.api import register_blueprints

def create_app(config_name="development"):
    app = Flask(__name__)

    # Load config
    app.config.from_object(config_dict.get(config_name, "development"))

    db.init_app(app)

    register_blueprints(app)

    # Initialize the database (create tables)
    with app.app_context():
        db.create_all()

    return app
