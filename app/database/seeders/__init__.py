# app/database/seeders/__init__.py
import click # For feedback
from .. import db # To manage the session commit
from .user_seeder import seed_user
from .fund_seeder import seed_fund
from .sale_seeder import seed_sale

__all__ = ['seed_user', 'seed_fund', 'seed_sale', 'seed_all'] # Add seed_all to __all__

def seed_all():
    """Seed all initial data by calling individual seeder functions."""
    click.echo("Starting database seeding...")
    
    # Call individual seeders
    seed_user()  # Handles admin and other users
    seed_fund()  # Handles initial funds
    # seed_sale() # Uncomment if/when you want to seed sales data
    
    try:
        db.session.commit()
        click.echo("All data committed successfully.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"Error during seeding commit: {e}", err=True)

    click.echo("Database seeding process completed.")