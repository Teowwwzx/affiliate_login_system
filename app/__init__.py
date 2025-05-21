import os
from flask import Flask
from .database import db
from dotenv import load_dotenv
from flask_migrate import Migrate
from flask_login import LoginManager, current_user
import logging  # For better debugging
from datetime import datetime # Make sure datetime is imported from datetime module
from .routes.general_routes import general_bp
from .routes.auth_routes import auth_bp
from .routes.admin_routes import admin_bp
from .routes.leader_routes import leader_bp
from .routes.member_routes import member_bp
import click    
from .database.models import User 
from .utils import register_filters

load_dotenv()  # Ensure this is called to load .env variables

migrate = Migrate()
login_manager = LoginManager()

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)

    # --- App configurations ---
    # Choose the database URL based on FLASK_ENV
    if os.environ.get("FLASK_ENV") == "production":
        db_uri = os.environ.get("DATABASE_URL_PROD")
        if not db_uri:
            app.logger.error("DATABASE_URL_PROD is not set for production environment!")
            # Potentially raise an error or use a fallback if critical
    else: # Default to development
        db_uri = os.environ.get("DATABASE_URL_DEV")
        if not db_uri:
            app.logger.error("DATABASE_URL_DEV is not set for development environment!")

    app.config.from_mapping(
        SECRET_KEY=os.environ.get(
            "SECRET_KEY", "a_default_fallback_secret_key_if_not_in_env"
        ),
        SQLALCHEMY_DATABASE_URI=db_uri, # Use the selected URI
        SQLALCHEMY_TRACK_MODIFICATIONS=False,  # Recommended to set to False
    )

    if test_config:
        app.config.from_mapping(test_config)

    # --- Initialize extensions ---
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Set PRAGMA busy_timeout for SQLite to help with 'database is locked' errors
    if app.config.get('SQLALCHEMY_DATABASE_URI', '').startswith('sqlite'):
        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        @event.listens_for(Engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            # app is in scope here from create_app
            cursor = dbapi_connection.cursor()
            try:
                app.logger.info("Attempting to set SQLite PRAGMAs...")
                # Set busy_timeout first
                cursor.execute("PRAGMA busy_timeout = 5000;")
                app.logger.info("PRAGMA busy_timeout set to 5000.")

                # Check current journal mode
                current_journal_mode_row = cursor.execute("PRAGMA journal_mode;").fetchone()
                current_mode = current_journal_mode_row[0].lower() if current_journal_mode_row else "unknown"
                app.logger.info(f"Current journal_mode: {current_mode}")

                if current_mode != 'wal':
                    app.logger.info("Attempting to set journal_mode to WAL...")
                    cursor.execute("PRAGMA journal_mode=WAL;")
                    # Verify it changed
                    new_journal_mode_row = cursor.execute("PRAGMA journal_mode;").fetchone()
                    if new_journal_mode_row and new_journal_mode_row[0].lower() == 'wal':
                        app.logger.info("Successfully set journal_mode to WAL.")
                    else:
                        app.logger.warning(f"Failed to set journal_mode to WAL. Mode is still: {new_journal_mode_row[0].lower() if new_journal_mode_row else 'unknown'}")
                else:
                    app.logger.info("journal_mode is already WAL.")

            except Exception as e:
                # Log the full traceback for the error during PRAGMA setting
                app.logger.error(f"Error setting SQLite PRAGMAs: {e}", exc_info=True)
            finally:
                cursor.close()

    # Context processors
    @app.context_processor
    def inject_current_year():
        return {'current_year': datetime.utcnow().year}

    @app.context_processor
    def inject_current_user():
        return dict(current_user=current_user)

    # --- Custom Jinja Filters ---
    def format_datetime_custom(value, format_str='%b %d, %Y %I:%M %p'):
        """Formats a datetime object to a custom string format. Default: Month Day, Year HH:MM AM/PM."""
        if value is None:
            return ""
        if isinstance(value, str):
            # Try to parse if it's a string, assuming ISO format for robustness if needed
            try:
                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
            except ValueError:
                # Fallback or re-raise, depending on how strict you want to be
                try:
                    value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f') # Example common format
                except ValueError:
                    return value # Return original string if parsing fails
        
        # Ensure it's a datetime object before formatting
        if not isinstance(value, datetime):
            return value # Or handle error appropriately
        
        return value.strftime(format_str)

    app.jinja_env.filters['datetime_custom'] = format_datetime_custom

    # --- Register blueprints ---
    app.register_blueprint(general_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(leader_bp, url_prefix='/leader')
    app.register_blueprint(member_bp, url_prefix='/member')

    # --- Register filters ---
    register_filters(app)

    # --- Setup Logging ---
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.INFO)

    # Ensure the session is removed after each request
    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db.session.remove()

    # --- CLI commands ---
    @app.cli.command("init-db")
    @click.option(
        "--seed/--no-seed", default=False, help="Seed the database with initial data."
    )
    def init_db_command(seed):
        """Clear existing data and create new tables. Optionally seed data."""
        with app.app_context():
            db.drop_all()
            db.create_all()
            click.echo("Initialized the database.")
            if seed:
                from .database.seeders import seed_all
                seed_all()
                click.echo("Database seeded.")

    return app
