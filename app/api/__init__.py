from flask import Flask
from .index import index_bp
from .contacts import contacts_bp
from .streams import streams_bp
from .targets import targets_bp
from .uploads import upload_bp

def register_blueprints(app: Flask):
    app.register_blueprint(index_bp)
    app.register_blueprint(contacts_bp, url_prefix='/api')
    app.register_blueprint(streams_bp, url_prefix='/api')
    app.register_blueprint(upload_bp, url_prefix='/api')
    app.register_blueprint(targets_bp, url_prefix='/api')