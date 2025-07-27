from flask import Flask, request, jsonify
from scripts.ci_manager import run_ci_pipeline
import os

app = Flask(__name__)

@app.route('/trigger', methods=['POST'])
def trigger_ci():
    data = request.get_json()
    event_type = request.headers.get('X-GitHub-Event', '')
    print(f"Received event: {event_type}")
    return jsonify({'status': 'Ignored'}), 200  # Default response
    if not data:
        return jsonify({'error': 'Missing payload'}), 400

    if event_type != 'push':
        return jsonify({'status': 'Ignored ? not a push event'}), 200

    # Parse branch from payload
    ref = data.get('ref', '')  # e.g. "refs/heads/main"
    branch = ref.split('/')[-1] if ref else None
    repo = data.get('repository', {}).get('name')

    if not branch or not repo:
        return jsonify({'error': 'Missing branch or repository info'}), 400

    result = run_ci_pipeline(branch)
    return jsonify({'status': result}), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
