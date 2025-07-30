import logging
import os
from flask import Flask
from routes import routes

app = Flask(__name__)
app.register_blueprint(routes)

# --- Logging Configuration ---
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)

log_file_path = os.path.join(LOG_DIR, 'app.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler()  # for console output
    ]
)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
