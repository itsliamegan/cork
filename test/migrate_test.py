import os
from pathlib import Path
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory

from helios.database import Config
from luna.test.assertion import (
	assert_eq,
	assert_not,
	assert_not_eq,
	assert_raises,
	assert_that,
)

from app.config import ROOT_DIR
from lib.migrate import MigrationError, apply, status


class Scratch:
	"""A temporary migrations directory and database file."""

	def __init__(self):
		self.temp_dir = TemporaryDirectory()
		self.dir = Path(self.temp_dir.name)
		self.migrations = self.dir.joinpath("migrations")
		self.migrations.mkdir()
		self.config = Config(self.dir.joinpath("store.sqlite"))

	def __enter__(self):
		return self

	def __exit__(self, exception_type, exception, traceback):
		self.temp_dir.cleanup()

	def write(self, name: str, sql: str):
		self.migrations.joinpath(name).write_text(sql)

	def query(self, sql: str) -> list[tuple]:
		connection = sqlite3.connect(self.config.database_file)
		try:
			return connection.execute(sql).fetchall()
		finally:
			connection.close()

	def version(self) -> int:
		return self.query("PRAGMA user_version")[0][0]

	def tables(self) -> list[str]:
		return [
			name
			for (name,) in self.query(
				"SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
			)
		]


def names(migrations) -> list[str]:
	return [migration.name for migration in migrations]


def test_applies_every_migration_to_a_fresh_database():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER PRIMARY KEY);\n",
		)
		scratch.write(
			"0002_boards.sql",
			"CREATE TABLE boards (id INTEGER PRIMARY KEY);\n",
		)

		applied = apply(scratch.config, scratch.migrations)

		assert_eq(names(applied), ["0001_users", "0002_boards"])
		assert_eq(scratch.version(), 2)
		assert_eq(scratch.tables(), ["boards", "users"])


def test_second_apply_does_nothing():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER PRIMARY KEY);\n",
		)
		apply(scratch.config, scratch.migrations)

		applied = apply(scratch.config, scratch.migrations)

		assert_eq(applied, [])
		assert_eq(scratch.version(), 1)


def test_applies_only_migrations_after_the_current_version():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER PRIMARY KEY);\n",
		)
		apply(scratch.config, scratch.migrations)
		scratch.write(
			"0002_boards.sql",
			"CREATE TABLE boards (id INTEGER PRIMARY KEY);\n",
		)

		applied = apply(scratch.config, scratch.migrations)

		assert_eq(names(applied), ["0002_boards"])
		assert_eq(scratch.version(), 2)
		assert_eq(scratch.tables(), ["boards", "users"])


def test_failing_statement_rolls_back_its_whole_migration():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER PRIMARY KEY);\n",
		)
		scratch.write(
			"0002_broken.sql",
			"CREATE TABLE boards (id INTEGER PRIMARY KEY);\n"
			"INSERT INTO missing VALUES (1);\n",
		)

		with assert_raises(MigrationError) as raised:
			apply(scratch.config, scratch.migrations)

		message = str(raised.exception)
		assert_that("0002_broken.sql" in message, message)
		assert_that("INSERT INTO missing" in message, message)
		assert_that(isinstance(raised.exception.__cause__.__cause__, sqlite3.Error))
		assert_eq(scratch.version(), 1)
		assert_eq(scratch.tables(), ["users"])


def test_foreign_key_violation_rolls_back_the_migration():
	with Scratch() as scratch:
		scratch.write(
			"0001_tables.sql",
			"CREATE TABLE boards (id INTEGER PRIMARY KEY);\n"
			"CREATE TABLE pins (\n"
			"\tid INTEGER PRIMARY KEY,\n"
			"\tboard_id INTEGER REFERENCES boards (id)\n"
			");\n",
		)
		scratch.write("0002_orphan.sql", "INSERT INTO pins VALUES (1, 99);\n")

		with assert_raises(MigrationError) as raised:
			apply(scratch.config, scratch.migrations)

		message = str(raised.exception)
		assert_that("0002_orphan.sql" in message, message)
		assert_that("pins row 1 references missing boards" in message, message)
		assert_eq(scratch.version(), 1)
		assert_eq(scratch.query("SELECT * FROM pins"), [])


def test_rebuilds_a_table_that_other_tables_reference():
	with Scratch() as scratch:
		scratch.write(
			"0001_tables.sql",
			"CREATE TABLE boards (id INTEGER PRIMARY KEY, title TEXT);\n"
			"CREATE TABLE pins (\n"
			"\tid INTEGER PRIMARY KEY,\n"
			"\tboard_id INTEGER REFERENCES boards (id) ON DELETE CASCADE\n"
			");\n"
			"INSERT INTO boards VALUES (1, 'Kitchen');\n"
			"INSERT INTO pins VALUES (1, 1);\n",
		)
		scratch.write(
			"0002_rebuild_boards.sql",
			"CREATE TABLE new_boards (id INTEGER PRIMARY KEY, title TEXT NOT NULL);\n"
			"INSERT INTO new_boards SELECT id, title FROM boards;\n"
			"DROP TABLE boards;\n"
			"ALTER TABLE new_boards RENAME TO boards;\n",
		)

		apply(scratch.config, scratch.migrations)

		assert_eq(scratch.version(), 2)
		assert_eq(scratch.query("SELECT * FROM boards"), [(1, "Kitchen")])
		assert_eq(scratch.query("SELECT * FROM pins"), [(1, 1)])


def test_runs_semicolons_inside_triggers_and_strings():
	with Scratch() as scratch:
		scratch.write(
			"0001_audit.sql",
			"-- Record every new board.\n"
			"CREATE TABLE boards (id INTEGER PRIMARY KEY, title TEXT);\n"
			"CREATE TABLE audit (message TEXT);\n"
			"CREATE TRIGGER boards_audit AFTER INSERT ON boards\n"
			"BEGIN\n"
			"\tINSERT INTO audit VALUES ('created; ' || NEW.title);\n"
			"\tINSERT INTO audit VALUES ('done;');\n"
			"END;\n"
			"INSERT INTO boards VALUES (1, 'a;\n"
			"b');\n"
			"/* trailing comment */\n",
		)

		apply(scratch.config, scratch.migrations)

		assert_eq(scratch.query("SELECT title FROM boards"), [("a;\nb",)])
		assert_eq(
			scratch.query("SELECT message FROM audit"),
			[("created; a;\nb",), ("done;",)],
		)


def assert_refused(scratch: Scratch, expected: str):
	with assert_raises(MigrationError) as raised:
		apply(scratch.config, scratch.migrations)

	message = str(raised.exception)
	assert_that(expected in message, message)
	assert_not(scratch.config.database_file.exists())


def test_refuses_a_gap_in_numbering():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		scratch.write("0003_boards.sql", "CREATE TABLE boards (id INTEGER);\n")

		assert_refused(scratch, "0003_boards.sql")


def test_refuses_a_duplicate_number():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		scratch.write("0001_boards.sql", "CREATE TABLE boards (id INTEGER);\n")

		assert_refused(scratch, "0001_boards.sql, 0001_users.sql")


def test_refuses_a_malformed_filename():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		scratch.write("2_Boards.sql", "CREATE TABLE boards (id INTEGER);\n")

		assert_refused(scratch, "2_Boards.sql")


def test_refuses_an_incomplete_final_statement():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER);\nCREATE TABLE boards (id INTEGER)\n",
		)

		assert_refused(scratch, "0001_users.sql: incomplete final statement")


def test_refuses_transaction_control_statements():
	with Scratch() as scratch:
		scratch.write(
			"0001_users.sql",
			"CREATE TABLE users (id INTEGER);\n/* sneaky */ COMMIT;\n",
		)

		assert_refused(scratch, "0001_users.sql: COMMIT is not allowed")


def test_refuses_a_database_newer_than_the_latest_migration():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		connection = sqlite3.connect(scratch.config.database_file)
		connection.execute("PRAGMA user_version = 5")
		connection.close()

		with assert_raises(MigrationError) as raised:
			apply(scratch.config, scratch.migrations)

		message = str(raised.exception)
		assert_that("version 5" in message, message)
		assert_eq(scratch.version(), 5)
		assert_eq(scratch.tables(), [])


def test_dry_apply_reports_pending_migrations_without_applying_them():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		apply(scratch.config, scratch.migrations)
		scratch.write("0002_boards.sql", "CREATE TABLE boards (id INTEGER);\n")

		pending = apply(scratch.config, scratch.migrations, dry=True)

		assert_eq(names(pending), ["0002_boards"])
		assert_eq(scratch.version(), 1)
		assert_eq(scratch.tables(), ["users"])


def test_status_reports_current_latest_and_pending():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		apply(scratch.config, scratch.migrations)
		scratch.write("0002_boards.sql", "CREATE TABLE boards (id INTEGER);\n")

		result = status(scratch.config, scratch.migrations)

		assert_eq(result.current, 1)
		assert_eq(result.latest, 2)
		assert_eq(names(result.pending), ["0002_boards"])


def test_status_and_dry_apply_refuse_a_missing_database():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")

		with assert_raises(MigrationError):
			status(scratch.config, scratch.migrations)
		with assert_raises(MigrationError):
			apply(scratch.config, scratch.migrations, dry=True)

		assert_not(scratch.config.database_file.exists())


def test_apply_refuses_a_missing_database_directory():
	with Scratch() as scratch:
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")
		config = Config(scratch.dir.joinpath("missing", "store.sqlite"))

		with assert_raises(MigrationError) as raised:
			apply(config, scratch.migrations)

		message = str(raised.exception)
		assert_that("missing" in message, message)
		assert_not(config.database_file.parent.exists())


def test_ignores_hidden_files():
	with Scratch() as scratch:
		scratch.write(".gitkeep", "")
		scratch.write(".0002_draft.sql.swp", "not sql")
		scratch.write("0001_users.sql", "CREATE TABLE users (id INTEGER);\n")

		applied = apply(scratch.config, scratch.migrations)

		assert_eq(names(applied), ["0001_users"])
		assert_eq(scratch.version(), 1)


def test_cli_status_refuses_a_missing_database():
	with TemporaryDirectory() as dir:
		database_file = Path(dir, "store.sqlite")

		result = subprocess.run(
			[sys.executable, str(ROOT_DIR.joinpath("bin", "migrate.py")), "status"],
			env={**os.environ, "APP_DATABASE_FILE": str(database_file)},
			capture_output=True,
			text=True,
			check=False,
		)

		assert_not_eq(result.returncode, 0)
		assert_that(
			f"database {database_file} does not exist" in result.stderr,
			result.stderr,
		)
		assert_not(database_file.exists())
