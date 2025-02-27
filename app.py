import os
import logging
import cv2
import base64
import numpy as np
from PIL import Image
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_from_directory
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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Create upload folder if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Configure the app
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Sign language classes
SIGN_CLASSES = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 
    'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
    'space', 'delete', 'nothing'
]

# Verify the model file exists
if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")

# Load the TFLite model
try:
    interpreter = tf.lite.Interpreter(model_path=MODEL_PATH)
    interpreter.allocate_tensors()
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    logger.info(f"Model loaded successfully. Input shape: {input_details[0]['shape']}")
except Exception as e:
    logger.error(f"Failed to load model: {str(e)}")
    raise

def allowed_file(filename):
    """Check if the file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def preprocess_image(image):
    """Preprocess the image for model input"""
    # Resize image to expected dimensions
    img = cv2.resize(image, (IMG_WIDTH, IMG_HEIGHT))
    
    # Convert to RGB if it's BGR (OpenCV default)
    if len(img.shape) == 3 and img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Normalize pixel values to [0, 1]
    img = img.astype(np.float32) / 255.0
    
    # Add batch dimension
    img = np.expand_dims(img, axis=0)
    
    return img

def predict(image):
    """Make prediction using the TFLite model"""
    # Preprocess the image
    processed_image = preprocess_image(image)
    
    # Set the tensor
    interpreter.set_tensor(input_details[0]['index'], processed_image)
    
    # Run inference
    interpreter.invoke()
    
    # Get prediction results
    output_data = interpreter.get_tensor(output_details[0]['index'])
    
    # Get the top prediction
    predicted_class_index = np.argmax(output_data[0])
    confidence = float(output_data[0][predicted_class_index])
    
    # Map to class name if available
    if predicted_class_index < len(SIGN_CLASSES):
        predicted_class = SIGN_CLASSES[predicted_class_index]
    else:
        predicted_class = f"Unknown ({predicted_class_index})"
    
    return {
        "class": predicted_class,
        "confidence": confidence,
        "class_index": int(predicted_class_index),
        "probabilities": output_data[0].tolist()
    }

@app.route('/')
def home():
    """Render the main application page"""
    return render_template('index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    """Serve static files"""
    return send_from_directory('static', path)

@app.route('/script-health-check', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

@app.route('/predict', methods=['POST'])
def predict_route():
    """Process uploaded image and return prediction"""
    try:
        # Check if the post request has the file part
        if 'file' not in request.files:
            # Try to get base64 image from JSON
            if request.is_json:
                data = request.get_json()
                if 'image' in data:
                    # Process base64 image
                    img_data = data['image']
                    # Remove data URL prefix if present
                    if ',' in img_data:
                        img_data = img_data.split(',')[1]
                    
                    # Decode base64 image
                    img_bytes = base64.b64decode(img_data)
                    img = Image.open(BytesIO(img_bytes))
                    img = np.array(img)
                    
                    # Make prediction
                    result = predict(img)
                    return jsonify(result)
                else:
                    return jsonify({"error": "No image data provided"}), 400
            else:
                return jsonify({"error": "No file part or JSON data"}), 400
        
        # Process file upload
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({"error": "No selected file"}), 400
        
        if file and allowed_file(file.filename):
            # Save the file temporarily
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            
            # Read and process the image
            img = cv2.imread(file_path)
            if img is None:
                return jsonify({"error": "Could not read image file"}), 400
            
            # Make prediction
            result = predict(img)
            
            # Return the result
            return jsonify(result)
        else:
            return jsonify({"error": "File type not allowed"}), 400
            
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/predict-from-camera', methods=['POST'])
def predict_from_camera():
    """Process base64 image from camera and return prediction"""
    try:
        data = request.get_json(force=True)
        if 'image' not in data:
            return jsonify({"error": "No image data provided"}), 400
        
        # Get the base64 string and remove the data URL prefix if present
        img_data = data['image']
        if ',' in img_data:
            img_data = img_data.split(',')[1]
        
        # Decode base64 image
        img_bytes = base64.b64decode(img_data)
        img = Image.open(BytesIO(img_bytes))
        img = np.array(img)
        
        # Make prediction
        result = predict(img)
        
        return jsonify(result)
    
    except Exception as e:
        logger.error(f"Camera prediction error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/translations', methods=['GET'])
def get_translations():
    """Get recent translations (placeholder - would need a database in production)"""
    # In a real application, you would fetch this from a database
    sample_translations = [
        {"id": 1, "text": "Hello", "timestamp": "2025-02-27T14:30:00", "thumbnail": "/static/thumbnails/sample1.jpg"},
        {"id": 2, "text": "Thank you", "timestamp": "2025-02-27T14:15:00", "thumbnail": "/static/thumbnails/sample2.jpg"}
    ]
    return jsonify({"translations": sample_translations})

@app.before_request
def log_request_info():
    """Log information about incoming requests"""
    app.logger.info(f"Incoming request: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    """Log information about outgoing responses"""
    app.logger.info(f"Outgoing response: {response.status}")
    return response

@app.route('/templates/<path:path>')
def serve_template(path):
    """Serve template files"""
    return send_from_directory('templates', path)

def create_template_file():
    """Create index.html template file from the HTML UI"""
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    os.makedirs(template_dir, exist_ok=True)
    
    # The HTML content from your previous UI design would go here
    # For this example, I'm using a placeholder that loads from a file if it exists
    template_path = os.path.join(template_dir, 'index.html')
    
    # Only create if it doesn't exist
    if not os.path.exists(template_path):
        with open(template_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sign Language Translator</title>
    <!-- CSS would go here, or be linked as a static file -->
</head>
<body>
    <!-- Content from your UI HTML would go here -->
    <h1>Sign Language Translator</h1>
    <p>Please ensure the template file is properly set up with your UI design.</p>
</body>
</html>
            """)

if __name__ == '__main__':
    # Create template file if needed
    create_template_file()
    
    # Use the PORT environment variable provided by Render
    port = int(os.environ.get('PORT', 10000))
    
    # Start the server
    logger.info(f"Starting server on port {port}")
    try:
        serve(app, host='0.0.0.0', port=port, threads=4, connection_limit=1000)
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
