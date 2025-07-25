from flask import Flask
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