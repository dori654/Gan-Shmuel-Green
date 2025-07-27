# Weight/app/app.py
from flask import Flask, jsonify


def create_app() -> Flask:
    """Factory that builds and returns a Flask application."""
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        """Simple JSON response for sanity?check / health?check."""
        return jsonify({"message": "Hello, Weight!"})

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "service": "weight"})

    return app


# create the global app object once
app = create_app()

if __name__ == "__main__":
    # run on port 5005 as requested
    app.run(host="0.0.0.0", port=5005)
