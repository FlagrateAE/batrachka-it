import asyncio
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"

SCHEMA_OBJECTS = text(
    """
    SELECT conname AS name FROM pg_constraint
    JOIN pg_namespace ON pg_namespace.oid = pg_constraint.connamespace
    WHERE nspname = 'public'
    UNION
    SELECT indexname FROM pg_indexes WHERE schemaname = 'public'
    UNION
    SELECT typname FROM pg_type
    JOIN pg_namespace ON pg_namespace.oid = pg_type.typnamespace
    WHERE nspname = 'public' AND typtype = 'e'
    """
)


async def schema_objects(connection: AsyncConnection) -> set[str]:
    names = (await connection.scalars(SCHEMA_OBJECTS)).all()
    return {name for name in names if not name.startswith("alembic_version")}


async def test_migrations_match_models_and_downgrade_cleanly(app: FastAPI) -> None:
    base_url = app.state.engine.url
    database = f"{base_url.database}_migrations"
    admin = create_async_engine(base_url, isolation_level="AUTOCOMMIT")
    async with admin.connect() as connection:
        await connection.execute(text(f'DROP DATABASE IF EXISTS "{database}"'))
        await connection.execute(text(f'CREATE DATABASE "{database}"'))

    migrated_url = make_url(base_url).set(database=database)
    config = Config(str(ALEMBIC_INI))
    config.set_main_option(
        "sqlalchemy.url", migrated_url.render_as_string(hide_password=False).replace("%", "%%")
    )
    migrated = create_async_engine(migrated_url)
    try:
        await asyncio.to_thread(command.upgrade, config, "head")
        async with migrated.connect() as connection:
            from_migrations = await schema_objects(connection)
        async with app.state.engine.connect() as connection:
            from_models = await schema_objects(connection)

        await asyncio.to_thread(command.downgrade, config, "base")
        async with migrated.connect() as connection:
            leftovers = await schema_objects(connection)
    finally:
        await migrated.dispose()
        async with admin.connect() as connection:
            await connection.execute(text(f'DROP DATABASE IF EXISTS "{database}" WITH (FORCE)'))
        await admin.dispose()

    assert from_migrations == from_models
    assert leftovers == set()