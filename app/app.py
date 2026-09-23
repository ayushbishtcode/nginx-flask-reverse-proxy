import time
from flask import Flask, jsonify, session
from flask_session import Session
import os
import redis

app = Flask(__name__)

app.config["SECRET_KEY"] = "devops-lab-secret-change-me"

app.config["SESSION_TYPE"] = "redis"
app.config["SESSION_REDIS"] = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=False
)
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 24 * 30
Session(app)

redis_client = redis.Redis(
    host="127.0.0.1",
    port=6379,
    decode_responses=True
)

@app.route("/")
def home():
    return "Flask application is running\n"

@app.route("/users")
def users():

    cached_users = redis_client.get("users")

    if cached_users:
        return cached_users, 200, {
            "Content-Type": "application/json",
            "X-Cache": "HIT"
        }

    users_data = {
        "users": [
            {"id": 1, "name": "Ayush"},
            {"id": 2, "name": "DevOps"},
            {"id": 3, "name": "Engineer"}
        ]
    }

    import json

    response = json.dumps(users_data)

    redis_client.setex(
        "users",
        60,
        response
    )

    return response, 200, {
        "Content-Type": "application/json",
        "X-Cache": "MISS"
    }

@app.route("/health")
def health():
    return jsonify({
        "status": "healthy"
    })


@app.route("/whoami")
def whoami():
    return jsonify({
        "server": os.environ.get("SERVER_ID", "unknown"),
        "port": int(os.environ.get("PORT", 5007))
    })

@app.route("/slow")
def slow():
    time.sleep(10)

    return jsonify({
        "server": os.environ.get("SERVER_ID", "unknown"),
        "port": int(os.environ.get("PORT", 5007))
    })

@app.route("/redis-test")
def redis_test():

    redis_client.set("devops_test", "Redis is working")

    value = redis_client.get("devops_test")

    return jsonify({
        "redis": value
    })

@app.route("/session-test")
def session_test():
    session["user"] = "Ayush"

    return jsonify({
        "session_user": session.get("user"),
        "server": os.environ.get("SERVER_ID", "unknown"),
        "port": int(os.environ.get("PORT", 5007))
    })

@app.route("/session-get")
def session_get():
    return jsonify({
        "session_user": session.get("user"),
        "server": os.environ.get("SERVER_ID", "unknown"),
        "port": int(os.environ.get("PORT", 5007))
    })
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5007))

    app.run(
        host="127.0.0.1",
        port=port
    )
