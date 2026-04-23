"""
Auth Routes
===========
Signup, login, logout, and current-user endpoints.
"""

from datetime import datetime, timezone

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
)

from ..extensions import db, blocklist
from ..models.user import User
from ..models.activity import Activity

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/signup", methods=["POST"])
def signup():
    """Register a new user."""
    data = request.get_json()

    # Validate input
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not name or not email or not password:
        return jsonify({"error": "Name, email, and password are required."}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409

    # Create user
    user = User(name=name, email=email, role="user")
    user.set_password(password)

    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Account created successfully.",
        "user": user.to_dict(),
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    """Authenticate and return a JWT token."""
    data = request.get_json()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = User.query.filter_by(email=email).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Invalid email or password."}), 401

    if not user.is_active:
        return jsonify({"error": "Your account has been disabled. Contact admin."}), 403

    # Update login count
    user.login_count = (user.login_count or 0) + 1

    # Create/update activity record
    activity = Activity(user_id=user.id)
    db.session.add(activity)
    db.session.commit()

    # Generate JWT token with user identity
    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={"role": user.role, "email": user.email},
    )

    return jsonify({
        "message": "Login successful.",
        "access_token": access_token,
        "user": user.to_dict(),
    }), 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    """Invalidate the current JWT token."""
    jti = get_jwt()["jti"]
    blocklist.add(jti)
    return jsonify({"message": "Logged out successfully."}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    """Return current user info (for frontend role check)."""
    user_id = get_jwt_identity()
    user = User.query.get(int(user_id))

    if not user:
        return jsonify({"error": "User not found."}), 404

    # Get latest activity
    latest_activity = (
        Activity.query.filter_by(user_id=user.id)
        .order_by(Activity.login_time.desc())
        .first()
    )

    user_data = user.to_dict()
    if latest_activity:
        user_data["total_usage"] = latest_activity.usage_count
        user_data["last_used"] = (
            latest_activity.last_used.isoformat() if latest_activity.last_used else None
        )

    return jsonify({"user": user_data}), 200
