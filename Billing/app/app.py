from flask import Flask, jsonify


def create_app() -> Flask:
    """Factory that builds and returns a Flask application."""
    app = Flask(__name__)

    @app.route("/", methods=["GET"])
    def index():
        """Simple JSON response for sanity?check / health?check."""
        return jsonify({"message": "Hello, Billing"})

    @app.route("/health", methods=["GET"])
    def health():
        """Health check endpoint."""
        return jsonify({"status": "healthy", "service": "billing"})

    return app


# When running via `flask run`, the global variable `app` must exist.
app = create_app()
