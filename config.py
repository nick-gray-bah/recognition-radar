import os
from dotenv import load_dotenv

load_dotenv()


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
    RECOGNITION_MODEL_NAME = "VGG-Face"
    RECOGNITION_DISTANCE_METRIC = "cosine"
    RECOGNITION_DETECTOR_BACKEND = "opencv"
    RECOGNITION_MIN_CONFIDENCE = 0.5
    RECOGNITION_THRESHOLD = 0.35
    RECOGNITION_FRAME_RATE = 30

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


config_dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}
