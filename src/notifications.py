import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from twilio.rest import Client

# Setup logging
logger = logging.getLogger(__name__)

def load_notification_contacts(notification_contacts, config):
    """Load notification contacts from the configuration."""
    if 'CONTACTS' in config:
        for key, value in config['CONTACTS'].items():
            if key.startswith('email'):
                notification_contacts.append({'email': value})
            elif key.startswith('phone'):
                notification_contacts.append({'phone': value})
    
    logger.info(f"Loaded {len(notification_contacts)} notification contacts")

def get_twilio_client(config):
    """Get a configured Twilio client."""
    return Client(
        config['TWILIO']['ACCOUNT_SID'],
        config['TWILIO']['AUTH_TOKEN']
    )

def send_email_alert(target_id, timestamp, video_url, notification_contacts, config):
    """Send email alert when a target is identified."""
    EMAIL_SENDER = config['EMAIL']['SENDER']
    EMAIL_PASSWORD = config['EMAIL']['PASSWORD']
    EMAIL_SMTP = config['EMAIL']['SMTP_SERVER']
    EMAIL_PORT = int(config['EMAIL']['SMTP_PORT'])
    
    for contact in notification_contacts:
        if 'email' not in contact:
            continue
        
        try:
            msg = MIMEMultipart()
            msg['From'] = EMAIL_SENDER
            msg['To'] = contact['email']
            msg['Subject'] = f"ALERT: Target {target_id} Identified"
            
            body = f"""
            Target individual {target_id} has been identified.
            Timestamp: {timestamp}
            Video: {video_url}
            """
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(EMAIL_SMTP, EMAIL_PORT) as server:
                server.starttls()
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
                
            logger.info(f"Email alert sent to {contact['email']}")
        except Exception as e:
            logger.error(f"Failed to send email to {contact['email']}: {str(e)}")

def send_sms_alert(target_id, timestamp, video_url, notification_contacts, config):
    """Send SMS alert when a target is identified."""
    TWILIO_PHONE = config['TWILIO']['PHONE_NUMBER']
    twilio_client = get_twilio_client(config)
    
    for contact in notification_contacts:
        if 'phone' not in contact:
            continue
        
        try:
            message = twilio_client.messages.create(
                body=f"ALERT: Target {target_id} identified at {timestamp}. Video: {video_url}",
                from_=TWILIO_PHONE,
                to=contact['phone']
            )
            logger.info(f"SMS alert sent to {contact['phone']}: {message.sid}")
        except Exception as e:
            logger.error(f"Failed to send SMS to {contact['phone']}: {str(e)}")

def send_webhook_alert(target_id, timestamp, video_url, config):
    """Send webhook alert when a target is identified (if configured)."""
    if 'WEBHOOK' in config and 'URL' in config['WEBHOOK']:
        import requests
        
        webhook_url = config['WEBHOOK']['URL']
        
        try:
            payload = {
                'target_id': target_id,
                'timestamp': timestamp,
                'video_url': video_url,
                'alert_type': 'face_recognition'
            }
            
            response = requests.post(webhook_url, json=payload)
            
            if response.status_code < 300:
                logger.info(f"Webhook alert sent to {webhook_url}")
            else:
                logger.warning(f"Webhook alert failed with status {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send webhook alert: {str(e)}")