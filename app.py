from flask import Flask, request, jsonify
import tensorflow as tf
import numpy as np

app = Flask(__name__)

# Load the TFLite model
interpreter = tf.lite.Interpreter(model_path="model.tflite")
interpreter.allocate_tensors()

# Function to make predictions
def predict(input_data):
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()

    # Preprocess input data
    input_data = np.array(input_data, dtype=np.float32)
    interpreter.set_tensor(input_details[0]['index'], input_data)
    interpreter.invoke()

    # Get the output
    output_data = interpreter.get_tensor(output_details[0]['index'])
    return output_data.tolist()

@app.route('/predict', methods=['POST'])
def predict_route():
    try:
        # Get input data from request
        data = request.get_json(force=True)
        input_data = data['input']  # The input should be passed as a list or array
        predictions = predict(input_data)

        return jsonify({"predictions": predictions})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
