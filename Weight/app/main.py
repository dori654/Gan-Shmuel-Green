from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from .routes import api    # Your Blueprint with /weight endpoint
from app.db import get_db_connection # Your DB connection and init_app()


def create_app():
    load_dotenv()
    app = Flask(__name__)
    
    # Enable CORS for all routes and origins (for Docker networking)
    CORS(app, origins=['*'], methods=['GET', 'POST', 'OPTIONS'], allow_headers=['Content-Type'])
    
    app.register_blueprint(api)
    
    @app.route("/health", methods=["GET"])
    def health():
        try:
            conn = get_db_connection()
            if conn:
                conn.close()
                return "OK", 200
            return "Failure", 500
        except:
            return "Failure", 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000)


