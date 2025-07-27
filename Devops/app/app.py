from flask import Flask, request, jsonify
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.ci_manager import run_ci_pipeline
import os

app = Flask(__name__)

@app.route('/trigger', methods=['POST'])
def trigger_ci():
    data = request.get_json()
    print (f"Received payload: {data}")
    # save json to file for debugging
    with open('/app/ci_payload.json', 'w') as f:
        f.write(str(data))
    if not data:
        return jsonify({'error': 'Missing payload'}), 400
    event_type = request.headers.get('X-GitHub-Event', '')
    print(f"Received event: {event_type}")
    if not data:
        return jsonify({'error': 'Missing payload'}), 400

    if event_type != 'push':
        return jsonify({'status': 'Ignored ? not a push event'}), 200

    # Parse branch from payload
    ref = data.get('ref', '')  # e.g. "refs/heads/main"
    print(f"Branch ref: {ref}")
    branch = ref.split('/')[-1] if ref else None
    print(f"Branch name: {branch}")
    repo = data.get('repository', {}).get('name')
    print(f"Repository name: {repo}")
    pusher_name= data.get('pusher', {}).get('name', 'unknown')
    print(f"Pusher name: {pusher_name}")
    commit_message = data.get('head_commit', {}).get('message', 'unknown')
    print(f"Commit message: {commit_message}")

    if not branch or not repo:
        return jsonify({'error': 'Missing branch or repository info'}), 400

    result = run_ci_pipeline(branch, pusher_name, commit_message)
    return jsonify({'status': result}), 200

@app.route('/health', methods=['GET'])
def health():
    return "OK", 200

if __name__ == '__main__':
    import ssl
    import os
    
    # Check if SSL certificates exist
    cert_file = '/app/cert.pem'
    key_file = '/app/key.pem'
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        # Run with HTTPS on port 8080
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(cert_file, key_file)
        print("Starting HTTPS server on port 8080...")
        app.run(host='0.0.0.0', port=8080, ssl_context=context, debug=False)
    else:
        # Run with HTTP
        print("Starting HTTP server on port 8080...")
        app.run(host='0.0.0.0', port=8080)
