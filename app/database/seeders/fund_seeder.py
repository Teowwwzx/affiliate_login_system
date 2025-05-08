# app/database/seeders/fund_seeder.py
import os
import click
from datetime import datetime # Keep for created_at if model doesn't auto-set
from .. import db
from ..models.fund import Fund
from ..models.user import User # To fetch the admin user

def seed_fund():
    """Seed initial fund data based on environment variables."""
    click.echo("Seeding funds...")

    # Check if funds already exist (simple check, can be made more specific)
    # For example, check for a fund with remarks='Initial company funds'
    if Fund.query.filter_by(remarks="Initial company funds").first() is not None:
        click.echo("Initial company funds already seem to exist. Skipping.")
        return

    admin_username = os.environ.get("ADMIN_DEFAULT_USERNAME", "admin")
    admin_user = User.query.filter_by(username=admin_username).first()

    if not admin_user:
        click.echo(f"Admin user '{admin_username}' not found. Cannot seed initial funds.", err=True)
        return

    initial_funds_str = os.environ.get("INITIAL_TOTAL_FUNDS", "1000.00")
    try:
        initial_funds = float(initial_funds_str)
    except ValueError:
        click.echo(f'Error: INITIAL_TOTAL_FUNDS "{initial_funds_str}" is not a valid number. Skipping fund seeding.', err=True)
        return

    fund_entry = Fund(
        amount=initial_funds,
        remarks="Initial company funds", # Specific remark for idempotency
        created_by=admin_user.id,
        # created_at=datetime.utcnow() # Add if your model doesn't set default
    )
    db.session.add(fund_entry)
    click.echo(f"Initial funds ({initial_funds:.2f}) seeded for admin '{admin_username}'.")
    # Removed db.session.commit() - will be handled by seed_all()
    click.echo("Fund seeding attempt complete.")