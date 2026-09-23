#!/usr/bin/env python

from pathlib import Path
import sqlite3
import sys
from typing import NoReturn

from helios.config import ConfigError
from luna.cli import Command, Option, Program

import app.config
import lib.migrate
from lib.migrate import MigrationError

MIGRATIONS_DIR = Path(app.config.ROOT_DIR, "database", "migrations")


def apply(dry: bool):
	"""Apply pending migrations to the database."""

	config = load_config()
	try:
		migrations = lib.migrate.apply(config.database, MIGRATIONS_DIR, dry)
	except MigrationError as error:
		fail(error)

	for migration in migrations:
		print(f"apply  {migration.name}")

	if dry:
		print("dry run: nothing applied")
	else:
		status = lib.migrate.status(config.database, MIGRATIONS_DIR)
		print(f"database at version {status.current}")


def status():
	"""Report the database version and pending migrations."""

	config = load_config()
	try:
		status = lib.migrate.status(config.database, MIGRATIONS_DIR)
	except MigrationError as error:
		fail(error)

	print(f"current  {status.current}")
	print(f"latest   {status.latest}")
	if status.current > status.latest:
		print("database is newer than the latest migration")
	for migration in status.pending:
		print(f"pending  {migration.name}")


def load_config() -> app.config.Config:
	try:
		return app.config.Config.load(env_file=app.config.ENV_FILE)
	except ConfigError as error:
		raise SystemExit(f"migrate: error: {error}") from None


def fail(error: MigrationError) -> NoReturn:
	"""Exit with the error, followed by the SQLite error that caused it."""

	message = f"migrate: error: {error}"
	cause = error.__cause__
	while cause is not None:
		if isinstance(cause, sqlite3.Error):
			message += f"\nmigrate: sqlite: {cause}"
			break
		cause = cause.__cause__
	raise SystemExit(message) from None


program = Program(
	"migrate",
	commands=[
		Command(
			"apply",
			apply,
			description=apply.__doc__,
			options=[
				Option(
					"dry",
					short="d",
					type=bool,
					help="report the migrations that would be applied, without applying them",
				),
			],
		),
		Command("status", status, description=status.__doc__),
	],
)


if __name__ == "__main__":
	program.run(sys.argv)
