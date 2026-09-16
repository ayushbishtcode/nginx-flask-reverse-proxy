from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def home():
    return "Flask application is running\n"


@app.route("/users")
def users():
    return jsonify({
        "users": [
            {"id": 1, "name": "Ayush"},
            {"id": 2, "name": "DevOps"},
            {"id": 3, "name": "Engineer"}
        ]
    })


@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5007
    )