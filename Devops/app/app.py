from flask import Flask, request, jsonify
from scripts.ci_manager import run_ci_pipeline
app = Flask(__name__)
import threading


@app.route('/trigger', methods=['POST'])
def trigger_ci():
    data = request.get_json()
    print(f"Received payload: {data}")
    
    if not data:
        return jsonify({'error': 'Missing payload'}), 400

    event_type = request.headers.get('X-GitHub-Event', '')
    print(f"Received event: {event_type}")

    if event_type != 'push':
        return jsonify({'status': 'Ignored – not a push event'}), 200

    # Run CI pipeline in a separate thread and send the full payload
    threading.Thread(target=run_ci_pipeline, args=(data,)).start()
    
    return jsonify({'status': 'CI started with full payload'}), 202


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'OK'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)