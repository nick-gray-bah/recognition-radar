import os
import datetime
import threading
import logging
from flask import request, jsonify, render_template
from werkzeug.utils import secure_filename
import cv2
from deepface import DeepFace

from monitoring import monitor_stream

logger = logging.getLogger(__name__)

def setup_routes(app, target_embeddings, active_streams, notification_contacts, config):
    """Configure all the routes for the Flask application."""
    
    TARGET_DIR = 'targets'
    TEMP_VIDEO_DIR = 'temp_videos'
    RECOGNITION_MODEL = config['RECOGNITION']['MODEL_NAME']
    
    @app.route('/')
    def index():
        """Render the main dashboard page."""
        return jsonify({
          'message': 'Healthy'
        }), 200
        # return render_template('index.html', 
        #                       targets=list(target_embeddings.keys()),
        #                       streams=active_streams)
        

    @app.route('/api/targets', methods=['GET'])
    def get_targets():
        """Get the list of target individuals."""
        return jsonify(list(target_embeddings.keys()))

    @app.route('/api/targets', methods=['POST'])
    def add_target():
        """Add a new target individual."""
        if 'image' not in request.files:
            return jsonify({'error': 'No image provided'}), 400
        
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if 'target_id' not in request.form:
            return jsonify({'error': 'No target ID provided'}), 400
        
        target_id = request.form['target_id']
        
        try:
            # Save the target image
            filename = secure_filename(f"{target_id}{os.path.splitext(file.filename)[1]}")
            filepath = os.path.join(TARGET_DIR, filename)
            file.save(filepath)
            
            # Generate embedding
            embedding = DeepFace.represent(filepath, model_name=RECOGNITION_MODEL)[0]['embedding']
            target_embeddings[target_id] = embedding
            
            logger.info(f"Added new target: {target_id}")
            return jsonify({'success': True, 'target_id': target_id})
        
        except Exception as e:
            logger.error(f"Error adding target {target_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/targets/<target_id>', methods=['DELETE'])
    def remove_target(target_id):
        """Remove a target individual."""
        if target_id not in target_embeddings:
            return jsonify({'error': 'Target not found'}), 404
        
        try:
            del target_embeddings[target_id]
            
            # Remove image files
            for filename in os.listdir(TARGET_DIR):
                if filename.startswith(f"{target_id}.") or filename == f"{target_id}":
                    os.remove(os.path.join(TARGET_DIR, filename))
            
            logger.info(f"Removed target: {target_id}")
            return jsonify({'success': True})
        
        except Exception as e:
            logger.error(f"Error removing target {target_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/contacts', methods=['GET'])
    def get_contacts():
        """Get the list of notification contacts."""
        return jsonify(notification_contacts)

    @app.route('/api/contacts', methods=['POST'])
    def add_contact():
        """Add a new notification contact."""
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = []
        if 'email' not in data and 'phone' not in data:
            required_fields.append('email or phone')
        
        if required_fields:
            return jsonify({'error': f"Missing required fields: {', '.join(required_fields)}"}), 400
        
        try:
            notification_contacts.append(data)
            logger.info(f"Added new contact: {data}")
            return jsonify({'success': True, 'contact': data})
        
        except Exception as e:
            logger.error(f"Error adding contact: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/contacts/<int:contact_index>', methods=['DELETE'])
    def remove_contact(contact_index):
        """Remove a notification contact."""
        if contact_index < 0 or contact_index >= len(notification_contacts):
            return jsonify({'error': 'Contact not found'}), 404
        
        try:
            removed_contact = notification_contacts.pop(contact_index)
            logger.info(f"Removed contact: {removed_contact}")
            return jsonify({'success': True})
        
        except Exception as e:
            logger.error(f"Error removing contact: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/streams', methods=['GET'])
    def get_streams():
        """Get the list of active video streams."""
        return jsonify(active_streams)

    @app.route('/api/streams', methods=['POST'])
    def add_stream():
        """Add a new video stream to monitor."""
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = []
        if 'stream_id' not in data:
            required_fields.append('stream_id')
        if 'stream_url' not in data:
            required_fields.append('stream_url')
        
        if required_fields:
            return jsonify({'error': f"Missing required fields: {', '.join(required_fields)}"}), 400
        
        stream_id = data['stream_id']
        stream_url = data['stream_url']
        
        if stream_id in active_streams:
            return jsonify({'error': f"Stream {stream_id} already exists"}), 400
        
        try:
            # Test if we can open the stream
            cap = cv2.VideoCapture(stream_url)
            if not cap.isOpened():
                return jsonify({'error': f"Could not open stream: {stream_url}"}), 400
            cap.release()
            
            # Add to active streams
            active_streams[stream_id] = {
                'stream_url': stream_url,
                'active': True,
                'started_at': datetime.datetime.now().isoformat()
            }
            
            # Start monitoring in a separate thread
            thread = threading.Thread(
                target=monitor_stream, 
                args=(stream_id, stream_url, active_streams, target_embeddings, config, notification_contacts)
            )
            thread.daemon = True
            thread.start()
            
            logger.info(f"Started monitoring stream: {stream_id} ({stream_url})")
            return jsonify({'success': True, 'stream_id': stream_id})
        
        except Exception as e:
            logger.error(f"Error adding stream {stream_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/api/streams/<stream_id>', methods=['DELETE'])
    def remove_stream(stream_id):
        """Stop monitoring a video stream."""
        if stream_id not in active_streams:
            return jsonify({'error': 'Stream not found'}), 404
        
        try:
            active_streams[stream_id]['active'] = False
            
            # Give it some time to stop
            # TODO: why? Do we need to also clean up the thread?
            threading.Timer(2.0, lambda: active_streams.pop(stream_id, None)).start()
            
            logger.info(f"Stopped monitoring stream: {stream_id}")
            return jsonify({'success': True, 'stream_id': stream_id})
        
        except Exception as e:
            logger.error(f"Error removing stream {stream_id}: {str(e)}")
            return jsonify({'error': str(e), 'stream_id': {stream_id}}), 500

    @app.route('/api/upload_video', methods=['POST'])
    def upload_video():
        """Process a video file to extract target faces."""
        if 'video' not in request.files:
            return jsonify({'error': 'No video provided'}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if 'target_id' not in request.form:
            return jsonify({'error': 'No target ID provided'}), 400
        
        target_id = request.form['target_id']
        
        try:
            # Save the uploaded video temporarily
            # TODO: Delete the video after processing
            video_path = os.path.join(TEMP_VIDEO_DIR, secure_filename(file.filename))
            file.save(video_path)
            
            # Extract frames from the video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return jsonify({'error': 'Could not open video file'}), 400
            
            frame_count = 0
            extracted_faces = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                frame_count += 1
                # only extract every 30 frames for performance
                if frame_count % 30 == 0:
                    try:
                        faces = DeepFace.extract_faces(frame, enforce_detection=False)
                        for face in faces:
                            if face['confidence'] >= 0.5:
                                extracted_faces.append(face['face'])
                    except Exception as e:
                        logger.warning(f"Could not extract face from frame {frame_count}: {str(e)}")
            
            cap.release()
            
            # If no faces found
            if not extracted_faces:
                return jsonify({'error': 'No faces detected in the video'}), 400
            
            # Save extracted faces and generate embeddings
            for i, face in enumerate(extracted_faces):
                face_path = os.path.join(TARGET_DIR, f"{target_id}_video_{i}.jpg")
                cv2.imwrite(face_path, face)
                
                embedding = DeepFace.represent(face, model_name=RECOGNITION_MODEL)[0]['embedding']
                
                # If this is the first face, use it as the primary embedding
                # TODO: this may not work becuase it may just capture the first face everytime
                if i == 0:
                    target_embeddings[target_id] = embedding
            
            logger.info(f"Processed video for target {target_id}, extracted {len(extracted_faces)} faces")
            return jsonify({
                'success': True,
                'target_id': target_id,
                'faces_extracted': len(extracted_faces)
            })
        
        except Exception as e:
            logger.error(f"Error processing video for target {target_id}: {str(e)}")
            return jsonify({'error': str(e)}), 500