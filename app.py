import os
import socket
from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from waitress import serve

app = Flask(__name__)

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path="sign_language_model.tflite")
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

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        data = request.get_json(force=True)
        input_data = data['input']
        predictions = predict(input_data)
        return jsonify({"predictions": predictions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

def find_available_port(start_port=5000):
    port = start_port
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('0.0.0.0', port))
                return port
        except OSError:
            port += 1

if __name__ == '__main__':
    port = find_available_port()
    print(f"Running on port {port}")
    serve(app, host='0.0.0.0', port=port)
