import logging
from logging.config import fileConfig

from flask import current_app

from alembic import context
import sqlalchemy

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger('alembic.env')

# Define a naming convention for constraints
# This helps especially with SQLite in batch mode
NAMING_CONVENTION = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

def get_engine():
    try:
        # this works with Flask-SQLAlchemy<3 and Alchemical
        return current_app.extensions['migrate'].db.get_engine()
    except (TypeError, AttributeError):
        # this works with Flask-SQLAlchemy>=3
        return current_app.extensions['migrate'].db.engine


def get_engine_url():
    try:
        return get_engine().url.render_as_string(hide_password=False).replace(
            '%', '%%')
    except AttributeError:
        return str(get_engine().url).replace('%', '%%')


# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
config.set_main_option('sqlalchemy.url', get_engine_url())
target_db = current_app.extensions['migrate'].db

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_metadata():
    # Create MetaData with naming convention
    metadata = sqlalchemy.MetaData(naming_convention=NAMING_CONVENTION)
    # Reflect existing tables into this MetaData object
    # This ensures that autogenerate compares against a DB state that understands these names
    # Only needed if you had pre-existing tables NOT created by Alembic using this convention
    # with get_engine().connect() as conn:
    #     metadata.reflect(bind=conn)

    # Then merge with the target_db metadata from your Flask app models
    # This is a simplified approach; for complex scenarios, more detailed merging might be needed.
    # The primary goal here is to ensure the MetaData used by Alembic has the naming convention.
    for table in target_db.metadata.tables.values():
        table.to_metadata(metadata)
    return metadata


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, 
        target_metadata=get_metadata(), 
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True, # ADDED for SQLite offline support
        naming_convention=NAMING_CONVENTION # ADDED
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    conf_args = current_app.extensions['migrate'].configure_args
    if conf_args.get("process_revision_directives") is None:
        conf_args["process_revision_directives"] = process_revision_directives

    connectable = get_engine()

    with connectable.connect() as connection:
        # Pass naming_convention to context.configure
        context_opts = {
            'connection': connection,
            'target_metadata': get_metadata(), # This should now return metadata with naming convention
            'process_revision_directives': process_revision_directives,
            **conf_args
        }
        # Enable batch mode for SQLite
        if connection.engine.name == 'sqlite':
            context_opts['render_as_batch'] = True
            # Naming convention is now part of get_metadata()
            # context_opts['naming_convention'] = NAMING_CONVENTION

        context.configure(**context_opts)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
