from app import create_app
from app.models import db, User, CompanySetting
from werkzeug.security import generate_password_hash
import click

app = create_app()

@app.cli.command('reset-db')
@click.option('--seed/--no-seed', default=True, help='Seed the database with initial data.')
def reset_db_command(seed):
    """Drops database tables, recreates them, and optionally seeds initial data."""
    try:
        click.echo('Dropping database tables...')
        db.drop_all()
        click.echo('Creating database tables...')
        db.create_all()
        click.echo('Database reset successfully.')

        if seed:
            click.echo('Seeding initial data...')
            # Seed Admin User
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('password'), # CHANGE THIS IN PRODUCTION!
                role='admin'
            )
            db.session.add(admin_user)

            # Seed initial funds setting
            initial_funds = CompanySetting(
                key='total_funds',
                value='1000.00' # Default initial value
            )
            db.session.add(initial_funds)

            db.session.commit()
            click.echo('Default admin user (admin/password) and initial funds created.')
        else:
             click.echo('Skipping data seeding.')

    except Exception as e:
        click.echo(f'Error resetting database: {e}', err=True)
        db.session.rollback()

if __name__ == '__main__':
    # Note: For Render deployment, Gunicorn will be used instead of this dev server.
    # Debug mode should be False in production.
    app.run(debug=True, host='0.0.0.0', port=5000) # Use 0.0.0.0 to be accessible on network
