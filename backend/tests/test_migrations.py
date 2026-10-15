"""The Alembic migrations must build exactly the schema the ORM models describe."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect

from app.db import Base, make_engine
from app.migrate import alembic_config


def _migrated_engine(tmp_path, revision="head"):
    url = f"sqlite:///{(tmp_path / 'migrations.db').as_posix()}"
    config = alembic_config()
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, revision)
    return config, make_engine(url)


def test_migrations_match_models(tmp_path):
    _, engine = _migrated_engine(tmp_path)
    with engine.connect() as connection:
        diff = compare_metadata(MigrationContext.configure(connection), Base.metadata)
    engine.dispose()
    assert diff == [], f"models and migrations differ: {diff}"


def test_migrations_downgrade_and_upgrade_again(tmp_path):
    config, engine = _migrated_engine(tmp_path)
    command.downgrade(config, "base")
    assert set(inspect(engine).get_table_names()) == {"alembic_version"}
    command.upgrade(config, "head")
    assert {"doctors", "patients", "appointments"} <= set(inspect(engine).get_table_names())
    engine.dispose()
