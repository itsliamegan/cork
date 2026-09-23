"""A forward-only SQL migration runner for SQLite databases.

Migrations are `NNNN_description.sql` files numbered from 0001 without gaps.
`PRAGMA user_version` records the number of the last applied migration, and
each migration commits together with its version bump.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Self

from helios.database import Config, DatabaseError
from helios.database.sqlite import Connection, connect

FILENAME = re.compile(r"^(\d{4})_([a-z0-9_]+)\.sql$")
TRANSACTION_KEYWORDS = {"BEGIN", "COMMIT", "END", "ROLLBACK", "SAVEPOINT", "RELEASE"}


class MigrationError(RuntimeError):
	pass


@dataclass
class Migration:
	number: int
	name: str
	path: Path
	statements: list[str]

	@classmethod
	def read(cls, path: Path) -> Self:
		"""Read a migration file and split it into its SQL statements."""

		match = FILENAME.match(path.name)
		if match is None:
			raise MigrationError(
				f"migration files must be named NNNN_description.sql: {path.name}"
			)

		return cls(
			number=int(match.group(1)),
			name=path.stem,
			path=path,
			statements=split(path),
		)

	def run(self, connection: Connection):
		"""Run the statements and record the version in the open transaction.

		The caller owns the transaction and commits it afterwards.
		"""

		for statement in self.statements:
			self.execute(connection, statement)

		self.check_foreign_keys(connection)

		try:
			connection.control(
				f"PRAGMA user_version = {self.number}",
				"version update",
			)
		except DatabaseError as error:
			raise MigrationError(
				f"{self.path.name}: could not record version {self.number}"
			) from error

	def execute(self, connection: Connection, statement: str):
		try:
			connection.execute(statement).close()
		except DatabaseError as error:
			raise MigrationError(
				f"{self.path.name}: statement failed: {summarize(statement)}"
			) from error

		if not connection.in_transaction:
			raise MigrationError(
				f"{self.path.name}: statement ended the transaction early: "
				f"{summarize(statement)}"
			)

	def check_foreign_keys(self, connection: Connection):
		try:
			cursor = connection.execute("PRAGMA foreign_key_check")
			try:
				violations = cursor.fetch_all()
			finally:
				cursor.close()
		except DatabaseError as error:
			raise MigrationError(
				f"{self.path.name}: could not check foreign keys"
			) from error

		if violations:
			details = "; ".join(
				f"{table} row {rowid} references missing {parent} (foreign key {index})"
				for table, rowid, parent, index in violations
			)
			raise MigrationError(f"{self.path.name}: foreign key violations: {details}")


class Migrations:
	"""A complete sequence of migrations, numbered from 1 without gaps."""

	def __init__(self, migrations: list[Migration]):
		self.migrations = sorted(
			migrations,
			key=lambda migration: (migration.number, migration.path.name),
		)
		self.check_numbering()

	@classmethod
	def load(cls, directory: Path) -> Self:
		"""Read and validate every migration in a directory, ignoring hidden files."""

		if not directory.is_dir():
			raise MigrationError(f"migrations directory {directory} does not exist")

		paths = [
			path
			for path in sorted(directory.iterdir(), key=lambda path: path.name)
			if not path.name.startswith(".")
		]

		malformed = [
			path.name
			for path in paths
			if FILENAME.match(path.name) is None or not path.is_file()
		]
		if malformed:
			raise MigrationError(
				"migration files must be named NNNN_description.sql: "
				+ ", ".join(malformed)
			)

		return cls([Migration.read(path) for path in paths])

	def __iter__(self) -> Iterator[Migration]:
		return iter(self.migrations)

	def __len__(self) -> int:
		return len(self.migrations)

	@property
	def latest(self) -> int:
		return len(self.migrations)

	def after(self, version: int) -> list[Migration]:
		"""Select the migrations after a version.

		A version beyond the latest migration means the database was migrated by
		newer code, which this code cannot safely run against.
		"""

		if version > self.latest:
			raise MigrationError(
				f"database is at version {version}, "
				f"newer than the latest migration {self.latest:04d}"
			)
		return self.migrations[version:]

	def check_numbering(self):
		"""Refuse duplicate numbers and numbering that does not run from 1 to N."""

		by_number: dict[int, list[Migration]] = {}
		for migration in self.migrations:
			by_number.setdefault(migration.number, []).append(migration)

		duplicates = [
			migration.path.name
			for group in by_number.values()
			if len(group) > 1
			for migration in group
		]
		if duplicates:
			raise MigrationError(
				"duplicate migration numbers: " + ", ".join(duplicates)
			)

		out_of_sequence = [
			migration.path.name
			for position, migration in enumerate(self.migrations, start=1)
			if migration.number != position
		]
		if out_of_sequence:
			raise MigrationError(
				"migration numbers must run from 0001 without gaps: "
				+ ", ".join(out_of_sequence)
			)


@dataclass
class Status:
	current: int
	latest: int
	pending: list[Migration]


class Migrator:
	"""Brings one database up to date with a sequence of migrations."""

	def __init__(self, config: Config, migrations: Migrations):
		self.config = config
		self.migrations = migrations

	def version(self) -> int:
		"""Read the database's version without opening a transaction."""

		self.require_database()
		with self.connect() as connection:
			return read_version(connection)

	def status(self) -> Status:
		"""Report the database's version and the migrations it has not applied."""

		current = self.version()
		latest = self.migrations.latest
		return Status(
			current=current,
			latest=latest,
			pending=[] if current > latest else self.migrations.after(current),
		)

	def pending(self) -> list[Migration]:
		"""List the migrations apply would run, without changing the database."""

		return self.migrations.after(self.version())

	def apply(self) -> list[Migration]:
		"""Apply every pending migration, each in its own transaction.

		When a migration fails, it is rolled back and the ones before it stay
		committed, leaving the database at the last fully applied version.
		"""

		if not self.config.database_file.parent.is_dir():
			raise MigrationError(
				f"database directory {self.config.database_file.parent} does not exist"
			)

		applied = []
		with self.connect() as connection:
			disable_foreign_keys(connection)
			while migration := self.begin_next(connection):
				try:
					migration.run(connection)
					commit(connection, migration)
				except BaseException:
					rollback(connection)
					raise
				applied.append(migration)
		return applied

	def begin_next(self, connection: Connection) -> Migration | None:
		"""Begin a transaction for the next pending migration, if there is one.

		The version is read inside the write transaction, so a concurrent runner
		cannot apply the same migration twice.
		"""

		try:
			connection.begin()
		except DatabaseError as error:
			raise MigrationError("could not begin a transaction") from error

		try:
			remaining = self.migrations.after(read_version(connection))
		except BaseException:
			rollback(connection)
			raise

		if not remaining:
			rollback(connection)
			return None
		return remaining[0]

	def require_database(self):
		"""Refuse to continue when the database file does not exist.

		Connecting would otherwise create an empty file, leaving a stray database
		behind when the path is mistyped.
		"""

		if not self.config.database_file.is_file():
			raise MigrationError(f"database {self.config.database_file} does not exist")

	def connect(self) -> Connection:
		try:
			return connect(self.config)
		except DatabaseError as error:
			raise MigrationError(
				f"could not open database {self.config.database_file}"
			) from error


def split(path: Path) -> list[str]:
	"""Split a migration file into its complete SQL statements."""

	statements = []
	statement = ""
	for line in path.read_text().splitlines(keepends=True):
		statement += line
		if sqlite3.complete_statement(statement):
			if strip_leading_comments(statement).strip(" \t\r\n;"):
				statements.append(statement)
			statement = ""

	if strip_leading_comments(statement):
		raise MigrationError(f"{path.name}: incomplete final statement")

	for statement in statements:
		keyword = first_keyword(statement)
		if keyword in TRANSACTION_KEYWORDS:
			raise MigrationError(
				f"{path.name}: {keyword} is not allowed, "
				f"the runner owns the transaction: {summarize(statement)}"
			)

	return statements


def strip_leading_comments(statement: str) -> str:
	"""Remove whitespace and comments from the start of a statement."""

	remainder = statement.lstrip()
	while True:
		if remainder.startswith("--"):
			end = remainder.find("\n")
			remainder = "" if end == -1 else remainder[end + 1 :]
		elif remainder.startswith("/*"):
			end = remainder.find("*/")
			remainder = "" if end == -1 else remainder[end + 2 :]
		else:
			return remainder
		remainder = remainder.lstrip()


def first_keyword(statement: str) -> str:
	match = re.match(r"[A-Za-z]+", strip_leading_comments(statement))
	return "" if match is None else match.group(0).upper()


def summarize(statement: str) -> str:
	"""Collapse a statement onto one line, shortened for error messages."""

	text = " ".join(strip_leading_comments(statement).split())
	return text if len(text) <= 80 else text[:77] + "..."


def disable_foreign_keys(connection: Connection):
	"""Turn foreign keys off so migrations can rebuild referenced tables.

	SQLite ignores this pragma inside a transaction, so it must run before the
	first one begins. Each migration checks foreign keys before committing.
	"""

	try:
		connection.control("PRAGMA foreign_keys = OFF", "configuration")
	except DatabaseError as error:
		raise MigrationError("could not disable foreign keys") from error


def read_version(connection: Connection) -> int:
	try:
		cursor = connection.execute("PRAGMA user_version")
		try:
			row = cursor.fetch_one()
		finally:
			cursor.close()
	except DatabaseError as error:
		raise MigrationError("could not read the database version") from error
	if row is None or not isinstance(row[0], int):
		raise MigrationError("could not read the database version")
	return row[0]


def commit(connection: Connection, migration: Migration):
	try:
		connection.commit()
	except DatabaseError as error:
		raise MigrationError(f"{migration.path.name}: could not commit") from error


def rollback(connection: Connection):
	"""Roll back the open transaction, keeping the original error if it fails."""

	try:
		connection.rollback()
	except DatabaseError:
		pass
