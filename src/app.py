import logging
import configparser
import traceback
from flask import Flask

from api import setup_routes
from monitoring import load_target_embeddings
from storage import ensure_directories
from notifications import load_notification_contacts

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load config
config = configparser.ConfigParser()
config.read('config.ini')

# Initialize global variables
target_embeddings = {}
notification_contacts = []
active_streams = {}

def init_app():
    """Initialize the application."""
    # Create necessary directories
    ensure_directories()
    
    # Load target embeddings
    load_target_embeddings(target_embeddings, config)
    
    # Load notification contacts from config if available
    load_notification_contacts(notification_contacts, config)
    
    logger.info("Application initialized successfully")

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    setup_routes(app, target_embeddings, active_streams, notification_contacts, config)
    
    return app

if __name__ == "__main__":    
    try: 
      init_app()
      app = create_app()
      app.run(host='127.0.0.1', port=int(config['APP']['PORT']), threaded=True)
      
    except Exception as e:
      print(e)
      traceback.print_exc()
    