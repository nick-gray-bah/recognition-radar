import os
import logging
import boto3
from botocore.exceptions import ClientError
from flask import current_app as app

logger = logging.getLogger(__name__)

S3_BUCKET = app.config['AWS_BUCKET_NAME']

s3_client = boto3.client(
    's3',
    aws_access_key_id=app.config['AWS_ACCESS_KEY'],
    aws_secret_access_key=app.config['AWS_SECRET_KEY'],
    region_name=app.config['AWS_REGION']
)


def ensure_directories():
    """Create necessary directories if they don't exist."""
    os.makedirs('targets', exist_ok=True)
    os.makedirs('temp_videos', exist_ok=True)


def upload_to_s3(file_path, object_name=None, config=None):
    """Upload a file to an S3 bucket."""
    if object_name is None:
        object_name = os.path.basename(file_path)

    try:
        s3_client.upload_file(file_path, S3_BUCKET, object_name)
        s3_url = f"https://{S3_BUCKET}.s3.amazonaws.com/{object_name}"
        logger.info(f"File uploaded to S3: {s3_url}")
        return s3_url
    except ClientError as e:
        logger.error(f"Error uploading to S3: {str(e)}")
        return None


def download_from_s3(object_name, file_path, config=None):
    """Download a file from an S3 bucket."""

    try:
        s3_client.download_file(S3_BUCKET, object_name, file_path)
        logger.info(f"File downloaded from S3: {object_name}")
        return True
    except ClientError as e:
        logger.error(f"Error downloading from S3: {str(e)}")
        return False


def list_s3_objects(prefix, config=None):
    """List objects in an S3 bucket with the given prefix."""

    try:
        response = s3_client.list_objects_v2(Bucket=S3_BUCKET, Prefix=prefix)

        if 'Contents' in response:
            return [item['Key'] for item in response['Contents']]
        else:
            return []
    except ClientError as e:
        logger.error(f"Error listing S3 objects: {str(e)}")
        return []


def delete_from_s3(object_name, config=None):
    """Delete an object from an S3 bucket."""

    try:
        s3_client.delete_object(Bucket=S3_BUCKET, Key=object_name)
        logger.info(f"Deleted object from S3: {object_name}")
        return True
    except ClientError as e:
        logger.error(f"Error deleting from S3: {str(e)}")
        return False
