import os
import logging
from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from waitress import serve

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Verify the model file exists
model_path = "sign_language_model.tflite"
if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found at: {model_path}")

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path=model_path)
interpreter.allocate_tensors()

def predict(input_data):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    input_data = np.array(input_data, dtype=np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_details[0]['index'])
    return output_data.tolist()

@app.route('/')
def home():
    return """
    <h1>Sign Language Model API</h1>
    <p>Welcome to the Sign Language Model API!</p>
    <p>Use the <code>/predict</code> endpoint to make predictions.</p>
    """

@app.route('/script-health-check', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy"}), 200

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        data = request.get_json(force=True)
        input_data = data['input']
        predictions = predict(input_data)
        return jsonify({"predictions": predictions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.before_request
def log_request_info():
    app.logger.info(f"Incoming request: {request.method} {request.path}")

@app.after_request
def log_response_info(response):
    app.logger.info(f"Outgoing response: {response.status}")
    return response

if __name__ == '__main__':
    serve(app, host='0.0.0.0', port=5000, threads=4, connection_limit=1000)
