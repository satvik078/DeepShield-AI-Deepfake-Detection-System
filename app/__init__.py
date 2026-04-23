"""
Flask Application Factory
==========================
Creates and configures the Flask application.
"""

import os

from flask import Flask, send_from_directory

from config import get_config
from .extensions import db, jwt, cors, blocklist


def create_app():
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend"),
        static_url_path="",
    )

    # Load config
    config_class = get_config()
    app.config.from_object(config_class)

    # Ensure upload directory exists
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ── Initialize extensions ───────────────────────────────
    db.init_app(app)
    jwt.init_app(app)
    cors.init_app(app)

    # ── JWT blocklist check ─────────────────────────────────
    @jwt.token_in_blocklist_loader
    def check_token_blocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        return jti in blocklist

    # ── Register Blueprints ─────────────────────────────────
    from .auth.routes import auth_bp
    from .prediction.routes import prediction_bp
    from .admin.routes import admin_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(prediction_bp, url_prefix="/api/predict")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")

    # ── Frontend routes ─────────────────────────────────────
    @app.route("/")
    def serve_index():
        return send_from_directory(app.static_folder, "index.html")

    @app.route("/<path:filename>")
    def serve_static(filename):
        return send_from_directory(app.static_folder, filename)

    # ── Create DB tables & default admin ────────────────────
    with app.app_context():
        from .models.user import User
        from .models.activity import Activity

        db.create_all()
        _create_default_admin(app)

    # ── Load ML model ───────────────────────────────────────
    _load_ml_model(app)

    return app


def _create_default_admin(app):
    """Create default admin user if none exists."""
    from .models.user import User

    admin = User.query.filter_by(role="admin").first()
    if admin is None:
        admin = User(
            name=app.config["ADMIN_NAME"],
            email=app.config["ADMIN_EMAIL"],
            role="admin",
        )
        admin.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(admin)
        db.session.commit()
        print(f"👤 Default admin created: {app.config['ADMIN_EMAIL']}")


def _load_ml_model(app):
    """Load the deepfake detection ViT model at startup."""
    from .utils.inference import load_model

    model_path = app.config["MODEL_PATH"]

    # Check that model directory exists and contains config.json
    config_file = os.path.join(model_path, "config.json")
    if os.path.isdir(model_path) and os.path.exists(config_file):
        try:
            model = load_model(model_path)
            app.config["MODEL"] = model
            print(f"🤖 ViT model loaded from {model_path}")
        except Exception as e:
            print(f"⚠️  Failed to load model: {e}")
            import traceback
            traceback.print_exc()
            app.config["MODEL"] = None
    else:
        print(f"⚠️  Model directory not found at {model_path} (expected a directory with config.json + model.safetensors)")
        print(f"    Prediction endpoints will return errors until a valid model is provided.")
        app.config["MODEL"] = None
