import os
import logging
import cv2
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify, render_template
import tensorflow as tf
from waitress import serve

app = Flask(__name__, static_folder='static')

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

# Configure the app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max upload size

# Sign language classes
SIGN_CLASSES = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'space', 'delete', 'nothing'
]

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
interpreter.allocate_tensors()
input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    img = cv2.resize(image, (IMG_WIDTH, IMG_HEIGHT))
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    img = img.astype(np.float32) / 255.0
    img = np.expand_dims(img, axis=0)
    return img

def predict(image):
    processed_image = preprocess_image(image)
    interpreter.set_tensor(input_details[0]['index'], processed_image)
    interpreter.invoke()
    output_data = interpreter.get_tensor(output_details[0]['index'])
    predicted_class_index = np.argmax(output_data[0])
    confidence = float(output_data[0][predicted_class_index])
    predicted_class = SIGN_CLASSES[predicted_class_index] if predicted_class_index < len(SIGN_CLASSES) else f"Unknown ({predicted_class_index})"
    return {"class": predicted_class, "confidence": confidence}

def process_video(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return {"error": "Failed to open video file"}
    
    predictions = []
    frame_count = 0
    interval = 5  # Process every 5th frame
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % interval == 0:
            result = predict(frame)
            predictions.append(result['class'])
        
        frame_count += 1
    
    cap.release()
    
    if predictions:
        final_prediction = max(set(predictions), key=predictions.count)
        return {"class": final_prediction, "predictions": predictions}
    else:
        return {"error": "No valid frames processed"}

@app.route('/predict-video', methods=['POST'])
def predict_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        result = process_video(file_path)
        os.remove(file_path)
        
        return jsonify(result)
    else:
        return jsonify({"error": "Invalid file type"}), 400

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
