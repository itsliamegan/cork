#!/usr/bin/env python

from pathlib import Path
import sqlite3
import sys
from typing import NoReturn

from helios.config import ConfigError
from luna.cli import Command, Program, option

from app.config import Config, ENV_FILE, ROOT_DIR
from lib.migrate import MigrationError, Migrations, Migrator

MIGRATIONS_DIR = Path(ROOT_DIR, "database", "migrations")


class Apply(Command):
	"""Apply pending migrations to the database."""

	name = "apply"
	dry: bool = option(
		default=False,
		short="d",
		help="report the migrations that would be applied without applying them",
	)

	def run(self):
		migrator = load_migrator()
		try:
			if self.dry:
				migrations = migrator.pending()
			else:
				migrations = migrator.apply()
		except MigrationError as error:
			if not self.dry:
				report_version(migrator)
			fail(error)

		for migration in migrations:
			print(f"apply  {migration.name}")

		if self.dry:
			print("dry run: nothing applied")
		else:
			report_version(migrator)


class Status(Command):
	"""Report the database version and pending migrations."""

	name = "status"

	def run(self):
		migrator = load_migrator()
		try:
			status = migrator.status()
		except MigrationError as error:
			fail(error)

		print(f"current  {status.current}")
		print(f"latest   {status.latest}")
		if status.current > status.latest:
			print("database is newer than the latest migration")
		for migration in status.pending:
			print(f"pending  {migration.name}")


def load_migrator() -> Migrator:
	try:
		config = Config.load(env_file=ENV_FILE)
	except ConfigError as error:
		raise SystemExit(f"migrate: error: {error}") from None

	try:
		migrations = Migrations.load(MIGRATIONS_DIR)
	except MigrationError as error:
		fail(error)

	return Migrator(config.database, migrations)


def report_version(migrator: Migrator):
	"""Print the database version, if the database can be read."""

	try:
		version = migrator.version()
	except MigrationError:
		return
	print(f"database at version {version}", flush=True)


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


class Migrate(Program):
	name = "migrate"
	commands = (Apply, Status)


if __name__ == "__main__":
	Migrate.main(sys.argv)
