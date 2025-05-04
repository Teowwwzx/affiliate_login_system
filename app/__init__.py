import os
from flask import Flask
from .models import db
from .routes import general_bp, admin_bp, leader_bp, offline_bp
from .auth import auth_bp
from dotenv import load_dotenv
from flask_migrate import Migrate # Import Migrate
from flask_wtf.csrf import CSRFProtect
from datetime import datetime # Import datetime

load_dotenv() # Load environment variables from .env file

# Initialize Migrate outside create_app
migrate = Migrate()

def create_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True) # instance_relative_config=True allows loading config from instance/ folder

    # --- Configuration ---
    # Default configuration
    app.config.from_mapping(
        SECRET_KEY=os.environ.get('SECRET_KEY', 'dev'), # Default 'dev' key for development, MUST be overridden in production
        # Use DATABASE_URL from environment if available, otherwise use SQLite default
        SQLALCHEMY_DATABASE_URI=os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(app.instance_path, 'app.db')}"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is None:
        # Load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True) # e.g., instance/config.py
    else:
        # Load the test config if passed in
        app.config.update(test_config)

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Already exists

    # --- Initialize Extensions ---
    db.init_app(app)
    migrate.init_app(app, db) # Initialize Migrate with app and db

    # --- Register Blueprints ---
    app.register_blueprint(general_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp)
    app.register_blueprint(leader_bp)
    app.register_blueprint(offline_bp) # Add /auth prefix to auth routes

    # --- Database Initialization Command (Optional but helpful) ---
    @app.cli.command('init-db')
    def init_db_command():
        """Clear existing data and create new tables."""
        with app.app_context():
            db.drop_all() # Use with caution!
            db.create_all()
        print('Initialized the database.')

    # --- User Creation Command ---
    import click
    from werkzeug.security import generate_password_hash
    from .models import User # Import User model

    @app.cli.command('create-user')
    @click.argument('username')
    @click.argument('password')
    @click.option('--role', default='offline', help='User role (admin, leader, offline)')
    @click.option('--leader', default=None, help='Username of the leader (required for offline role)')
    @click.option('--can-view-funds', is_flag=True, help='Set if leader can view funds (only for leader role)')
    def create_user_command(username, password, role, leader, can_view_funds):
        """Creates a new user."""
        if User.query.filter_by(username=username).first():
            print(f"Error: Username '{username}' already exists.")
            return

        leader_user = None
        if role == 'offline':
            if not leader:
                print("Error: --leader is required for role 'offline'.")
                return
            leader_user = User.query.filter_by(username=leader, role='leader').first()
            if not leader_user:
                print(f"Error: Leader with username '{leader}' not found or is not a leader.")
                return
        elif leader:
             print("Warning: --leader option is ignored for roles other than 'offline'.")

        if role != 'leader' and can_view_funds:
            print("Warning: --can-view-funds flag is ignored for roles other than 'leader'.")
            can_view_funds = False # Ensure it's false if not a leader

        hashed_password = generate_password_hash(password)
        new_user = User(
            username=username,
            password_hash=hashed_password,
            role=role,
            leader_id=leader_user.id if leader_user else None,
            can_view_funds=can_view_funds if role == 'leader' else False
        )
        db.session.add(new_user)
        db.session.commit()
        print(f"User '{username}' ({role}) created successfully.")


    # --- Simple route for testing ---
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    # --- Add Context Processor ---
    @app.context_processor
    def inject_current_year():
        return dict(current_year=datetime.utcnow().year)

    return app
