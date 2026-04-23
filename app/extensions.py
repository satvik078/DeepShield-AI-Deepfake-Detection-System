"""
Flask Extensions
================
Instantiate extensions here so they can be imported anywhere
without circular import issues.
"""

from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS

db = SQLAlchemy()
jwt = JWTManager()
cors = CORS()

# In-memory JWT blocklist (for logout).
# For production, use Redis or a DB table.
blocklist: set = set()
