#!/usr/bin/env python
"""Copy the old JSON store into a migrated, empty SQLite database.

This is a one-time tool for moving off `helios.data`. Rows are inserted with
raw SQL so that each record keeps its original `id` and `created_at`.
"""

from datetime import datetime
import json
from pathlib import Path
import sqlite3
import sys
from typing import Any, NoReturn

from helios.config import ConfigError
from helios.database import DatabaseError, Model, ModelError, types
from helios.database.sqlite import Connection, connect, quote_identifier
from luna.cli import Argument, Option, Program

from app.config import Config, ENV_FILE
from app.data import models
from lib.migrate import MigrationError, read_version


class StoreImportError(RuntimeError):
	pass


def main(path: str, dry: bool):
	"""Import a JSON store file into the configured database."""

	try:
		config = Config.load(env_file=ENV_FILE)
	except ConfigError as error:
		fail(error)

	database_file = config.database.database_file
	if not database_file.is_file():
		fail(f"database {database_file} does not exist; run bin/migrate.py apply")

	try:
		records = read_records(Path(path))
		with connect(config.database) as connection:
			counts = import_records(connection, records, dry)
	except (StoreImportError, MigrationError, DatabaseError) as error:
		fail(error)

	for model_type in models:
		print(f"{model_type.table:<12} {counts[model_type]}")
	if dry:
		print("dry run: nothing imported")
	else:
		print(f"imported {sum(counts.values())} records into {database_file}")


def read_records(path: Path) -> list[dict[str, Any]]:
	try:
		records = json.loads(path.read_text())
	except (OSError, ValueError) as error:
		raise StoreImportError(f"could not read {path}: {error}") from error
	if not isinstance(records, list) or not all(
		isinstance(record, dict) for record in records
	):
		raise StoreImportError(f"{path} is not a list of records")
	return records


def import_records(
	connection: Connection,
	records: list[dict[str, Any]],
	dry: bool,
) -> dict[type[Model], int]:
	"""Insert every record in one transaction, committing unless dry."""

	connection.begin()
	if read_version(connection) < 1:
		raise StoreImportError(
			"database has not been migrated; run bin/migrate.py apply"
		)
	for model_type in models:
		if count_rows(connection, model_type) > 0:
			raise StoreImportError(f"table {model_type.table} is not empty")

	# Parents and children may appear in any order in the JSON, so foreign keys
	# are checked once, before committing.
	connection.control("PRAGMA defer_foreign_keys = ON", "configuration")

	models_by_name = {model_type.__name__: model_type for model_type in models}
	for record in records:
		model_type = models_by_name.get(record.get("_type"))
		if model_type is None:
			raise StoreImportError(f"record has an unknown _type: {describe(record)}")
		insert(connection, model_type, record)

	check_foreign_keys(connection)
	counts = {model_type: count_rows(connection, model_type) for model_type in models}

	if dry:
		connection.rollback()
	else:
		connection.commit()
	return counts


def insert(connection: Connection, model_type: type[Model], record: dict[str, Any]):
	extra = set(record) - set(model_type.attrs) - {"_type"}
	if extra:
		raise StoreImportError(
			f"record has unknown attributes {sorted(extra)}: {describe(record)}"
		)

	names = tuple(model_type.attrs)
	try:
		parameters = [encode(model_type, name, record) for name in names]
	except (TypeError, ValueError, ModelError) as error:
		raise StoreImportError(f"{error}: {describe(record)}") from error

	columns = ", ".join(quote_identifier(name) for name in names)
	placeholders = ", ".join("?" for _ in names)
	sql = (
		f"INSERT INTO {quote_identifier(model_type.table)} ({columns}) "
		f"VALUES ({placeholders})"
	)
	try:
		connection.execute(sql, parameters).close()
	except DatabaseError as error:
		raise StoreImportError(
			f"{sqlite_message(error)}: {describe(record)}"
		) from error


def encode(model_type: type[Model], name: str, record: dict[str, Any]):
	"""Decode a value the way the JSON store did, then encode it for SQLite.

	Missing values are filled as the JSON store filled them: the default when
	there is one, otherwise null when the attribute allows it.
	"""

	attribute = model_type.attrs[name]
	if name in record:
		value = decode(attribute.type, record[name])
	elif not attribute.required:
		value = attribute.default
	elif attribute.nullable:
		value = None
	else:
		raise ModelError(f"{model_type.__name__}.{name}: missing")

	attribute.check(value, model_type)
	if value is None:
		return None
	return types.encode(attribute.type, value)


def decode(codec: types.Type[Any], value: object) -> object:
	if value is None:
		return None
	if isinstance(codec, types.Date):
		if not isinstance(value, str):
			raise TypeError(f"expected a datetime string, got {type(value).__name__}")
		decoded = datetime.fromisoformat(value)
		if decoded.tzinfo is None or decoded.utcoffset() is None:
			raise ValueError(f"expected an aware datetime, got {value!r}")
		return decoded
	if isinstance(codec, types.Bool):
		if not isinstance(value, bool):
			raise TypeError(f"expected a boolean, got {type(value).__name__}")
		return value
	if not isinstance(value, int | float | str | bytes):
		raise TypeError(f"expected a scalar, got {type(value).__name__}")
	return codec.decode(value)


def check_foreign_keys(connection: Connection):
	cursor = connection.execute("PRAGMA foreign_key_check")
	try:
		violations = cursor.fetch_all()
	finally:
		cursor.close()
	if not violations:
		return

	for table, rowid, parent, index in violations:
		cursor = connection.execute(
			f"SELECT id FROM {quote_identifier(str(table))} WHERE rowid = ?",
			(rowid,),
		)
		try:
			row = cursor.fetch_one()
		finally:
			cursor.close()
		identifier = row[0] if row is not None else f"rowid {rowid}"
		print(
			f"{table} {identifier} references a missing {parent} row (foreign key {index})",
			file=sys.stderr,
		)
	raise StoreImportError(f"{len(violations)} foreign key violation(s)")


def count_rows(connection: Connection, model_type: type[Model]) -> int:
	cursor = connection.execute(
		f"SELECT COUNT(*) FROM {quote_identifier(model_type.table)}"
	)
	try:
		row = cursor.fetch_one()
	finally:
		cursor.close()
	if row is None or not isinstance(row[0], int):
		raise StoreImportError(f"could not count rows in {model_type.table}")
	return row[0]


def describe(record: dict[str, Any]) -> str:
	return f"{record.get("_type", "?")} {record.get("id", "?")}"


def sqlite_message(error: BaseException) -> str:
	"""Name the SQLite error behind a Helios DatabaseError, when there is one."""

	cause = error.__cause__
	while cause is not None:
		if isinstance(cause, sqlite3.Error):
			return str(cause)
		cause = cause.__cause__
	return str(error)


def fail(error: object) -> NoReturn:
	message = f"import_store: error: {error}"
	if isinstance(error, BaseException) and sqlite_message(error) not in str(error):
		message += f"\nimport_store: sqlite: {sqlite_message(error)}"
	raise SystemExit(message) from None


program = Program(
	"import_store",
	main,
	description=main.__doc__,
	arguments=[Argument("path", help="the JSON store file to import")],
	options=[
		Option(
			"dry",
			short="d",
			type=bool,
			help="import inside a transaction, report counts, and roll back",
		),
	],
)


if __name__ == "__main__":
	program.run(sys.argv)
