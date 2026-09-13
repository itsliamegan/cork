#!/usr/bin/env python

from argparse import ArgumentParser
from datetime import datetime
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
from typing import Any
from uuid import UUID, uuid4


class MigrationError(Exception):
	pass


BASE_FIELDS = {"_type", "id", "created_at"}
MODEL_FIELDS = {
	"User": ({"name"}, {"open_in_new_tab"}),
	"Recovery": ({"user_id", "code"}, set()),
	"Invite": ({"token", "creator_id", "target_id", "expires_at"}, set()),
	"Share": ({"board_id", "user_id"}, set()),
	"Ordering": ({"user_id", "board_id", "position"}, set()),
}
UUID_FIELDS = {
	"id",
	"user_id",
	"creator_id",
	"target_id",
	"pin_id",
	"board_id",
	"adder_id",
}
DATETIME_FIELDS = {"created_at", "expires_at"}
STRING_FIELDS = {"name", "code", "token", "title", "url", "note"}


def parse_uuid(value: Any, description: str) -> UUID:
	if not isinstance(value, str):
		raise MigrationError(f"{description} must be a UUID string")
	try:
		return UUID(value)
	except ValueError:
		raise MigrationError(f"{description} is not a valid UUID: {value!r}") from None


def parse_datetime(value: Any, description: str) -> datetime:
	if not isinstance(value, str):
		raise MigrationError(f"{description} must be an aware datetime string")
	try:
		parsed = datetime.fromisoformat(value)
	except ValueError:
		raise MigrationError(
			f"{description} is not a valid datetime: {value!r}"
		) from None
	if parsed.tzinfo is None or parsed.utcoffset() is None:
		raise MigrationError(f"{description} must be timezone-aware")
	return parsed


def reject_duplicate_fields(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
	result = {}
	for name, value in pairs:
		if name in result:
			raise MigrationError(f"duplicate JSON field {name!r}")
		result[name] = value
	return result


def load_records(raw: bytes) -> list[dict[str, Any]]:
	try:
		data = json.loads(raw, object_pairs_hook=reject_duplicate_fields)
	except UnicodeDecodeError as error:
		raise MigrationError(f"store is not UTF-8: {error}") from None
	except json.JSONDecodeError as error:
		raise MigrationError(f"store is not valid JSON: {error}") from None
	if not isinstance(data, list):
		raise MigrationError("top-level JSON value must be an array")
	for index, record in enumerate(data):
		if not isinstance(record, dict):
			raise MigrationError(f"record {index} must be an object")
	return data


def validate_fields(
	record: dict[str, Any],
	required: set[str],
	optional: set[str] | None = None,
):
	optional = optional or set()
	model_type = record["_type"]
	record_id = record["id"]
	missing = required - record.keys()
	if missing:
		raise MigrationError(
			f"{model_type} {record_id} is missing {", ".join(sorted(missing))}"
		)
	unexpected = record.keys() - BASE_FIELDS - required - optional
	if unexpected:
		raise MigrationError(
			f"{model_type} {record_id} has unexpected fields: "
			f"{", ".join(sorted(unexpected))}"
		)

	for name, value in record.items():
		description = f"{model_type} {record_id} field {name}"
		if name in UUID_FIELDS:
			if name == "target_id" and value is None:
				continue
			parse_uuid(value, description)
		elif name in DATETIME_FIELDS:
			parse_datetime(value, description)
		elif name in STRING_FIELDS and not isinstance(value, str):
			raise MigrationError(f"{description} must be a string")
		elif name == "open_in_new_tab" and not isinstance(value, bool):
			raise MigrationError(f"{description} must be a boolean")
		elif name == "position" and (
			not isinstance(value, int) or isinstance(value, bool)
		):
			raise MigrationError(f"{description} must be an integer")


def classify_record(record: dict[str, Any]) -> str | None:
	model_type = record["_type"]
	if model_type not in {"Board", "Pin"}:
		return None

	has_old_creator = "user_id" in record
	has_new_creator = "creator_id" in record
	if has_old_creator and has_new_creator:
		raise MigrationError(
			f"{model_type} {record["id"]} has both user_id and creator_id"
		)
	if not has_old_creator and not has_new_creator:
		raise MigrationError(
			f"{model_type} {record["id"]} is missing its creator field"
		)

	if model_type == "Board":
		creator_field = "user_id" if has_old_creator else "creator_id"
		validate_fields(record, {"title", creator_field})
	else:
		creator_field = "user_id" if has_old_creator else "creator_id"
		if has_old_creator:
			if "board_id" not in record or record["board_id"] is None:
				raise MigrationError(
					f"Pin {record["id"]} has a null or missing board_id"
				)
			validate_fields(
				record, {"url", "title", creator_field, "board_id"}, {"note"}
			)
		else:
			if "board_id" in record:
				raise MigrationError(
					f"Pin {record["id"]} mixes creator_id with legacy board_id"
				)
			validate_fields(record, {"url", "title", creator_field}, {"note"})
	return "source" if has_old_creator else "destination"


def validate_records(records: list[dict[str, Any]]) -> tuple[str, dict[str, int]]:
	ids: dict[UUID, dict[str, Any]] = {}
	by_type: dict[str, list[dict[str, Any]]] = {}
	formats = set()

	for index, record in enumerate(records):
		model_type = record.get("_type")
		if not isinstance(model_type, str) or not model_type:
			raise MigrationError(
				f"record {index} is missing a valid _type discriminator"
			)
		if "id" not in record:
			raise MigrationError(f"{model_type} record {index} is missing id")
		if "created_at" not in record:
			raise MigrationError(f"{model_type} {record["id"]} is missing created_at")

		record_id = parse_uuid(record["id"], f"{model_type} record ID")
		if record_id in ids:
			raise MigrationError(f"duplicate model ID: {record["id"]}")
		ids[record_id] = record
		by_type.setdefault(model_type, []).append(record)

		if model_type in MODEL_FIELDS:
			required, optional = MODEL_FIELDS[model_type]
			validate_fields(record, required, optional)
		elif model_type == "Placement":
			validate_fields(record, {"pin_id", "board_id", "adder_id"})
		elif model_type not in {"Board", "Pin"}:
			raise MigrationError(f"unsupported model discriminator {model_type!r}")

		record_format = classify_record(record)
		if record_format is not None:
			formats.add(record_format)

	if len(formats) > 1:
		raise MigrationError("store mixes source and destination Board or Pin formats")

	placements = by_type.get("Placement", [])
	store_format = next(iter(formats), "destination")
	if store_format == "source" and placements:
		raise MigrationError(
			"Placement records are present alongside legacy Board or Pin records"
		)

	users = {parse_uuid(row["id"], "User ID") for row in by_type.get("User", [])}
	boards = {
		parse_uuid(row["id"], "Board ID"): row for row in by_type.get("Board", [])
	}
	pins = {parse_uuid(row["id"], "Pin ID"): row for row in by_type.get("Pin", [])}
	creator_field = "user_id" if store_format == "source" else "creator_id"
	for model_type in ("Board", "Pin"):
		for record in by_type.get(model_type, []):
			creator_id = parse_uuid(
				record[creator_field], f"{model_type} {record["id"]} creator"
			)
			if creator_id not in users:
				raise MigrationError(
					f"{model_type} {record["id"]} refers to missing creator "
					f"{record[creator_field]}"
				)

	if store_format == "source":
		for pin in pins.values():
			board_id = parse_uuid(pin["board_id"], f"Pin {pin["id"]} board_id")
			if board_id not in boards:
				raise MigrationError(
					f"Pin {pin["id"]} refers to missing board {pin["board_id"]}"
				)
	else:
		placement_counts = {pin_id: 0 for pin_id in pins}
		for placement in placements:
			pin_id = parse_uuid(
				placement["pin_id"], f"Placement {placement["id"]} pin_id"
			)
			board_id = parse_uuid(
				placement["board_id"], f"Placement {placement["id"]} board_id"
			)
			adder_id = parse_uuid(
				placement["adder_id"], f"Placement {placement["id"]} adder_id"
			)
			if pin_id not in pins:
				raise MigrationError(
					f"Placement {placement["id"]} refers to missing pin "
					f"{placement["pin_id"]}"
				)
			if board_id not in boards:
				raise MigrationError(
					f"Placement {placement["id"]} refers to missing board "
					f"{placement["board_id"]}"
				)
			if adder_id not in users:
				raise MigrationError(
					f"Placement {placement["id"]} refers to missing adder "
					f"{placement["adder_id"]}"
				)
			placement_counts[pin_id] += 1
		for pin_id, count in placement_counts.items():
			if count != 1:
				raise MigrationError(
					f"destination Pin {pins[pin_id]["id"]} has {count} Placements; "
					"expected exactly one"
				)

	return store_format, {
		"boards": len(boards),
		"pins": len(pins),
		"placements": len(placements),
	}


def transform(
	records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
	store_format, counts = validate_records(records)
	if store_format == "destination":
		return records, counts

	used_ids = {parse_uuid(record["id"], "model ID") for record in records}
	migrated = []
	placements = []
	for record in records:
		model_type = record["_type"]
		updated = dict(record)
		if model_type in {"Board", "Pin"}:
			updated["creator_id"] = updated.pop("user_id")
		if model_type == "Pin":
			board_id = updated.pop("board_id")
			placement_id = uuid4()
			while placement_id in used_ids:
				placement_id = uuid4()
			used_ids.add(placement_id)
			placements.append(
				{
					"_type": "Placement",
					"id": str(placement_id),
					"created_at": updated["created_at"],
					"pin_id": updated["id"],
					"board_id": board_id,
					"adder_id": updated["creator_id"],
				}
			)
		migrated.append(updated)

	counts["placements"] = len(placements)
	return [*migrated, *placements], counts


def migrate(path: Path) -> bool:
	try:
		raw = path.read_bytes()
	except OSError as error:
		raise MigrationError(f"could not read {path}: {error}") from None

	records = load_records(raw)
	migrated, counts = transform(records)
	if migrated is records:
		print(
			f"No migration necessary for {path}: "
			f"{counts["boards"]} Boards, {counts["pins"]} Pins, "
			f"{counts["placements"]} Placements"
		)
		return False

	try:
		serialized = (json.dumps(migrated, indent="\t") + "\n").encode()
	except (TypeError, ValueError) as error:
		raise MigrationError(f"could not serialize migrated store: {error}") from None

	temporary_path = None
	try:
		mode = stat.S_IMODE(path.stat().st_mode)
		with tempfile.NamedTemporaryFile(
			mode="wb", prefix=f".{path.name}.", dir=path.parent, delete=False
		) as temporary:
			temporary_path = Path(temporary.name)
			os.chmod(temporary.fileno(), mode)
			temporary.write(serialized)
			temporary.flush()
			os.fsync(temporary.fileno())
		os.replace(temporary_path, path)
	except OSError as error:
		if temporary_path is not None:
			try:
				temporary_path.unlink(missing_ok=True)
			except OSError:
				pass
		raise MigrationError(f"could not replace {path}: {error}") from None

	print(
		f"Migrated {path}: {counts["boards"]} Boards, {counts["pins"]} Pins, "
		f"created {counts["placements"]} Placements"
	)
	return True


def main() -> int:
	parser = ArgumentParser(
		description="Migrate Cork's store to placement-backed pins. Run with Cork stopped."
	)
	parser.add_argument("path", nargs="?", type=Path, default=Path("data/store.json"))
	args = parser.parse_args()
	try:
		migrate(args.path)
	except MigrationError as error:
		print(f"migration: error: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
