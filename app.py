from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np
from waitress import serve  # Import Waitress

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

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        data = request.get_json(force=True)
        input_data = data['input']
        predictions = predict(input_data)
        return jsonify({"predictions": predictions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    # Use Waitress to serve the app in production
    serve(app, host='0.0.0.0', port=5001)
