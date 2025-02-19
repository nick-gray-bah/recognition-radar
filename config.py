import os

class Config:
    """Base configuration (shared across environments)"""
    PORT = 5000
    TARGET_DIR = "targets"
    TEMP_VIDEO_DIR = "temp_videos"
    RECOGNITION_MODEL = "Facenet"

    # AWS Configuration
    AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
    AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
    AWS_REGION = "us-east-1"
    AWS_BUCKET_NAME = "face-recognition-alerts"

    # Twilio Configuration
    TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
    TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
    TWILIO_PHONE_NUMBER = "+15551234567"

    # Email Configuration
    EMAIL_SENDER = "alerts@yourcompany.com"
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587

    # Recognition Settings
    MODEL_NAME = "VGG-Face"
    DISTANCE_METRIC = "cosine"
    THRESHOLD = 0.35

    # Contacts
    CONTACTS = {
        "emails": ["security@yourcompany.com", "admin@yourcompany.com"],
        "phones": ["+15551234567", "+15557654321"],
    }

class DevelopmentConfig(Config):
    """Development-specific configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///localdb.sqlite' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    """Production-specific configuration"""
    DEBUG = False


# Configuration dictionary for selecting the environment
config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
