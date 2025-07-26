from flask import Flask, request, jsonify   
from db import db

app = Flask(__name__)
db.init_app(app)

@app.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute("SELECT 1")
        return "OK", 200
    except:
        return "Failure", 500

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

