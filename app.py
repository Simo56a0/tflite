import os
import logging
import cv2
import base64
import numpy as np
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import tensorflow as tf
from waitress import serve

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for frontend requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
MODEL_PATH = "sign_language_model.tflite"
IMG_HEIGHT = 224
IMG_WIDTH = 224
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'avi', 'mov'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Sign language classes
SIGN_CLASSES = ['hello', 'thank you', 'yes', 'no', 'I love you']  # Modify with actual word classes

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def preprocess_image(image):
    """Preprocess the image for model inference."""
    try:
        img = cv2.resize(image, (IMG_WIDTH, IMG_HEIGHT))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.expand_dims(img, axis=0)
        return img
    except Exception as e:
        logger.error(f"Error preprocessing image: {str(e)}")
        return None

def predict(image):
    """Make a prediction using the TFLite model."""
    processed_image = preprocess_image(image)
    if processed_image is None:
        return {"error": "Invalid image"}
    
    interpreter.set_tensor(input_details[0]['index'], processed_image)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    predicted_class_index = np.argmax(output_data[0])
    confidence = float(output_data[0][predicted_class_index])
    
    predicted_class = SIGN_CLASSES[predicted_class_index] if predicted_class_index < len(SIGN_CLASSES) else "Unknown"
    return {"class": predicted_class, "confidence": confidence}

@app.route('/translate', methods=['POST'])
def translate_frames():
    """Receive and process frames from the frontend."""
    data = request.json
    if not data or 'frames' not in data:
        return jsonify({"error": "No frames data"}), 400

    try:
        frames = data['frames']
        predictions = []

        for frame_base64 in frames:
            frame_data = frame_base64.split(',')[1] if ',' in frame_base64 else frame_base64
            img_bytes = base64.b64decode(frame_data)
            img_array = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

            if frame is not None:
                result = predict(frame)
                if "error" not in result:
                    predictions.append(result['class'])

        if predictions:
            final_prediction = max(set(predictions), key=predictions.count)
            confidence = predictions.count(final_prediction) / len(predictions)
            return jsonify({"translation": final_prediction, "confidence": confidence, "predictions": predictions})
        else:
            return jsonify({"error": "No valid frames processed"})

    except Exception as e:
        logger.error(f"Error processing frames: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/webcam-predict', methods=['POST'])
def webcam_predict():
    """Handle frame-by-frame predictions from the webcam."""
    try:
        frame_data = request.json.get("frame")
        if not frame_data:
            return jsonify({"error": "No frame data received"}), 400

        img_bytes = base64.b64decode(frame_data.split(',')[1])
        img_array = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        if frame is not None:
            result = predict(frame)
            return jsonify(result)
        else:
            return jsonify({"error": "Failed to process image"}), 400

    except Exception as e:
        logger.error(f"Webcam processing error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
