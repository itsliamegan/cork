"""A forward-only SQL migration runner for SQLite databases.

Migrations are `NNNN_description.sql` files numbered from 0001 without gaps.
`PRAGMA user_version` records the number of the last applied migration, and
each migration commits together with its version bump.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3

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


@dataclass
class Status:
	current: int
	latest: int
	pending: list[Migration]


def apply(config: Config, directory: Path, dry: bool = False) -> list[Migration]:
	"""Apply every pending migration, or list them without applying when dry."""

	if dry:
		require_database(config)
	elif not config.database_file.parent.is_dir():
		raise MigrationError(
			f"database directory {config.database_file.parent} does not exist"
		)

	migrations = load(directory)

	if dry:
		with open_database(config) as connection:
			current = read_version(connection)
		return pending(migrations, current)

	applied = []
	with open_database(config) as connection:
		disable_foreign_keys(connection)
		while migration := next_migration(connection, migrations):
			run(connection, migration)
			applied.append(migration)
	return applied


def status(config: Config, directory: Path) -> Status:
	"""Report the database's version and the migrations it has not applied."""

	require_database(config)
	migrations = load(directory)

	with open_database(config) as connection:
		current = read_version(connection)

	return Status(
		current=current,
		latest=len(migrations),
		pending=migrations[current:],
	)


def load(directory: Path) -> list[Migration]:
	"""Read and validate every migration in the directory, ordered by number."""

	if not directory.is_dir():
		raise MigrationError(f"migrations directory {directory} does not exist")

	migrations = []
	malformed = []
	for path in sorted(directory.iterdir(), key=lambda path: path.name):
		if path.name.startswith("."):
			continue
		match = FILENAME.match(path.name)
		if match is None or not path.is_file():
			malformed.append(path.name)
			continue
		migrations.append(
			Migration(
				number=int(match.group(1)),
				name=path.stem,
				path=path,
				statements=[],
			)
		)

	if malformed:
		raise MigrationError(
			"migration files must be named NNNN_description.sql: "
			+ ", ".join(malformed)
		)

	check_numbering(migrations)

	for migration in migrations:
		migration.statements = split(migration)

	return migrations


def check_numbering(migrations: list[Migration]):
	"""Refuse duplicate numbers and numbering that does not run from 1 to N."""

	by_number: dict[int, list[Migration]] = {}
	for migration in migrations:
		by_number.setdefault(migration.number, []).append(migration)

	duplicates = [
		migration.path.name
		for group in by_number.values()
		if len(group) > 1
		for migration in group
	]
	if duplicates:
		raise MigrationError("duplicate migration numbers: " + ", ".join(duplicates))

	out_of_sequence = [
		migration.path.name
		for position, migration in enumerate(migrations, start=1)
		if migration.number != position
	]
	if out_of_sequence:
		raise MigrationError(
			"migration numbers must run from 0001 without gaps: "
			+ ", ".join(out_of_sequence)
		)


def split(migration: Migration) -> list[str]:
	"""Split a migration file into its complete SQL statements."""

	text = migration.path.read_text()
	statements = []
	statement = ""
	for line in text.splitlines(keepends=True):
		statement += line
		if sqlite3.complete_statement(statement):
			if strip_leading_comments(statement).strip(" \t\r\n;"):
				statements.append(statement)
			statement = ""

	if strip_leading_comments(statement):
		raise MigrationError(f"{migration.path.name}: incomplete final statement")

	for statement in statements:
		keyword = first_keyword(statement)
		if keyword in TRANSACTION_KEYWORDS:
			raise MigrationError(
				f"{migration.path.name}: {keyword} is not allowed, "
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


def require_database(config: Config):
	"""Refuse to continue when the database file does not exist.

	Connecting would otherwise create an empty file, leaving a stray database
	behind when the path is mistyped.
	"""

	if not config.database_file.is_file():
		raise MigrationError(f"database {config.database_file} does not exist")


def open_database(config: Config) -> Connection:
	try:
		return connect(config)
	except DatabaseError as error:
		raise MigrationError(
			f"could not open database {config.database_file}"
		) from error


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


def pending(migrations: list[Migration], current: int) -> list[Migration]:
	"""Select the migrations after the current version.

	A version beyond the latest migration means the database was migrated by
	newer code, which this code cannot safely run against.
	"""

	if current > len(migrations):
		raise MigrationError(
			f"database is at version {current}, "
			f"newer than the latest migration {len(migrations):04d}"
		)
	return migrations[current:]


def next_migration(
	connection: Connection,
	migrations: list[Migration],
) -> Migration | None:
	"""Begin a transaction for the next pending migration, if there is one.

	The version is read inside the write transaction, so a concurrent runner
	cannot apply the same migration twice.
	"""

	try:
		connection.begin()
	except DatabaseError as error:
		raise MigrationError("could not begin a transaction") from error

	try:
		remaining = pending(migrations, read_version(connection))
	except BaseException:
		rollback(connection)
		raise

	if not remaining:
		rollback(connection)
		return None
	return remaining[0]


def run(connection: Connection, migration: Migration):
	"""Run one migration in the open transaction and commit it with its version."""

	try:
		for statement in migration.statements:
			execute(connection, migration, statement)
		check_foreign_keys(connection, migration)
		try:
			connection.control(
				f"PRAGMA user_version = {migration.number}",
				"version update",
			)
			connection.commit()
		except DatabaseError as error:
			raise MigrationError(
				f"{migration.path.name}: could not record version {migration.number}"
			) from error
	except BaseException:
		rollback(connection)
		raise


def execute(connection: Connection, migration: Migration, statement: str):
	try:
		connection.execute(statement).close()
	except DatabaseError as error:
		raise MigrationError(
			f"{migration.path.name}: statement failed: {summarize(statement)}"
		) from error

	if not connection.in_transaction:
		raise MigrationError(
			f"{migration.path.name}: statement ended the transaction early: "
			f"{summarize(statement)}"
		)


def check_foreign_keys(connection: Connection, migration: Migration):
	try:
		cursor = connection.execute("PRAGMA foreign_key_check")
		try:
			violations = cursor.fetch_all()
		finally:
			cursor.close()
	except DatabaseError as error:
		raise MigrationError(
			f"{migration.path.name}: could not check foreign keys"
		) from error

	if violations:
		details = "; ".join(
			f"{table} row {rowid} references missing {parent} (foreign key {index})"
			for table, rowid, parent, index in violations
		)
		raise MigrationError(
			f"{migration.path.name}: foreign key violations: {details}"
		)


def rollback(connection: Connection):
	"""Roll back the open transaction, keeping the original error if it fails."""

	try:
		connection.rollback()
	except DatabaseError:
		pass
