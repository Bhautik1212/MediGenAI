"""MediGen AI - Flask application entry point.

Run (from the backend folder):   python app.py
"""
from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from config import Config
from database.db import init_db
from routes.api import api
from services.generator import provider_info


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    init_db(app)
    app.register_blueprint(api)

    @app.get("/")
    def index():
        return jsonify({
            "service": "MediGen AI backend",
            "message": "Open the frontend at http://localhost:5173.",
            "health": "/api/health",
            "api": "/api",
        })

    @app.errorhandler(HTTPException)
    def http_error(e):
        return jsonify({"error": {"message": e.description, "code": e.name.lower().replace(" ", "_")}}), e.code

    @app.errorhandler(Exception)
    def unexpected(e):
        app.logger.exception("Unhandled error")
        return jsonify({"error": {"message": "Something went wrong on the server.", "code": "server_error"}}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    info = provider_info(app.config)
    print("=" * 60)
    print(f" MediGen AI backend | provider: {info['provider']} | model: {info['model']}")
    if info["is_demo"]:
        print(" WARNING: DEMO MODE - images are placeholders, NOT AI-generated.")
        print("          Set HF_API_TOKEN in backend/.env for real generation.")
    for p in info["problems"]:
        print(f" PROBLEM: {p}")
    print("=" * 60)
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
