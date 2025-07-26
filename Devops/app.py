from flask import Flask

app = Flask(__name__)


@app.route('/health')
def health_check():
    return 'OK', 200




@app.route('/push-main', methods=['POST'])
def push_main(secret=None):
    print("Push to main branch triggered")
    return 'Push to main triggered', 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)