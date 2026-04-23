"""
Activity Model
==============
Tracks user activity (logins, prediction usage).
"""

from datetime import datetime, timezone

from ..extensions import db


class Activity(db.Model):
    """User activity tracking model."""

    __tablename__ = "activities"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    login_time = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime, nullable=True)

    def increment_usage(self):
        """Increment the usage counter and update last_used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    def __repr__(self):
        return f"<Activity user_id={self.user_id} usage={self.usage_count}>"
