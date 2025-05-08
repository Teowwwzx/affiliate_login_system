from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# The seeding logic is handled by the 'init-db' command in app/__init__.py


__all__ = ['db']