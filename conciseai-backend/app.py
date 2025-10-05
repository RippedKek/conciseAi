from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/')
def home():
    return jsonify({"message": "ConciseAI Backend is Running 🚀"})

@app.route('/upload', methods=['POST'])
def upload_video():
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file provided"}), 400

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(file_path)

    return jsonify({"message": "File uploaded successfully", "path": file_path})

@app.route('/summarize', methods=['POST'])
def summarize():
    data = request.get_json()
    transcript = data.get("transcript", "No transcript provided.")
    
    # Mock summary — replace with actual AI model later
    summary = "This is a short summary of the uploaded lecture."
    
    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
