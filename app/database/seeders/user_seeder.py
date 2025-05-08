# app/database/seeders/user_seeder.py
import os
import click
from .. import db
from ..models.user import User

def seed_user():
    """Seed initial users, including admin from env vars and other test users."""
    click.echo("Seeding users...")

    # --- Create Admin User from Environment Variables ---
    admin_username = os.environ.get("ADMIN_DEFAULT_USERNAME", "admin")
    admin_email = os.environ.get("ADMIN_DEFAULT_EMAIL", "admin@gmail.com")
    admin_password = os.environ.get("ADMIN_DEFAULT_PASSWORD", "123")

    if not User.query.filter_by(username=admin_username).first():
        admin = User(
            username=admin_username,
            email=admin_email,
            role='admin',
            status=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        click.echo(f"Admin user '{admin_username}' created.")
    else:
        click.echo(f"Admin user '{admin_username}' already exists. Skipping.")

    # # --- Create a Test Team Leader ---
    # leader_username = 'leader1'
    # if not User.query.filter_by(username=leader_username).first():
    #     leader = User(
    #         username=leader_username,
    #         email='leader1@gmail.com',
    #         role='leader',
    #         status=True
    #     )
    #     leader.set_password('123')
    #     db.session.add(leader)
    #     # Must flush to get leader.id if other users depend on it before commit
    #     db.session.flush() 
    #     click.echo(f"User '{leader_username}' created.")
    #     leader_id_for_members = leader.id
    # else:
    #     existing_leader = User.query.filter_by(username=leader_username).first()
    #     leader_id_for_members = existing_leader.id # Use existing leader's ID
    #     click.echo(f"User '{leader_username}' already exists. Skipping creation, using existing for member assignment.")

    # # --- Create Test Team Members ---
    # members_data = [
    #     {'username': 'test1', 'email': 'test1@gmail.com'},
    #     {'username': 'test2', 'email': 'test2@gmail.com'},
    #     {'username': 'test3', 'email': 'test3@gmail.com'}
    # ]

    # for member_info in members_data:
    #     if not User.query.filter_by(username=member_info['username']).first():
    #         member = User(
    #             username=member_info['username'],
    #             email=member_info['email'],
    #             role='member',
    #             leader_id=leader_id_for_members, # Assign leader
    #             status=True
    #         )
    #         member.set_password('123')
    #         db.session.add(member)
    #         click.echo(f"User '{member_info['username']}' created.")
    #     else:
    #         click.echo(f"User '{member_info['username']}' already exists. Skipping.")
    # # Removed db.session.commit() - will be handled by seed_all()
    # click.echo("User seeding attempts complete.")