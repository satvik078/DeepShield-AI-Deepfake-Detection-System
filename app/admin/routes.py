"""
Admin Routes
============
User management and dashboard statistics (admin-only).
"""

from functools import wraps

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from sqlalchemy import func

from ..extensions import db
from ..models.user import User
from ..models.activity import Activity

admin_bp = Blueprint("admin", __name__)


def admin_required(fn):
    """Decorator: ensure the current user has 'admin' role."""
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        claims = get_jwt()
        if claims.get("role") != "admin":
            return jsonify({"error": "Admin access required."}), 403
        return fn(*args, **kwargs)
    return wrapper


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    """List all users with their activity stats."""
    users = User.query.order_by(User.created_at.desc()).all()

    user_list = []
    for user in users:
        user_data = user.to_dict()

        # Get total usage across all sessions
        total_usage = (
            db.session.query(func.sum(Activity.usage_count))
            .filter(Activity.user_id == user.id)
            .scalar()
        ) or 0

        # Get last activity
        last_activity = (
            Activity.query.filter_by(user_id=user.id)
            .order_by(Activity.login_time.desc())
            .first()
        )

        user_data["total_usage"] = total_usage
        user_data["last_login"] = (
            last_activity.login_time.isoformat() if last_activity else None
        )
        user_list.append(user_data)

    return jsonify({"users": user_list, "total": len(user_list)}), 200


@admin_bp.route("/disable_user", methods=["POST"])
@admin_required
def toggle_user_status():
    """Enable or disable a user account."""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required."}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.role == "admin":
        return jsonify({"error": "Cannot disable admin accounts."}), 403

    # Toggle status
    user.is_active = not user.is_active
    db.session.commit()

    status = "enabled" if user.is_active else "disabled"
    return jsonify({
        "message": f"User {user.email} has been {status}.",
        "user": user.to_dict(),
    }), 200


@admin_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    """Dashboard statistics for admin."""
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_count = User.query.filter_by(role="admin").count()

    total_predictions = (
        db.session.query(func.sum(Activity.usage_count)).scalar()
    ) or 0

    # Recent signups (last 7 days)
    from datetime import datetime, timedelta, timezone
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    recent_signups = User.query.filter(User.created_at >= week_ago).count()

    # Most active users
    top_users = (
        db.session.query(
            User.name,
            User.email,
            func.sum(Activity.usage_count).label("total_usage"),
        )
        .join(Activity)
        .group_by(User.id)
        .order_by(func.sum(Activity.usage_count).desc())
        .limit(5)
        .all()
    )

    return jsonify({
        "total_users": total_users,
        "active_users": active_users,
        "admin_count": admin_count,
        "total_predictions": int(total_predictions),
        "recent_signups": recent_signups,
        "top_users": [
            {"name": u.name, "email": u.email, "total_usage": int(u.total_usage)}
            for u in top_users
        ],
    }), 200
