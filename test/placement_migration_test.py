import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from uuid import UUID

from helios.data.store import Format
from luna.test.assertion import assert_eq, assert_that

from app.data import Board, Ordering, Pin, Placement, Share, schema

SCRIPT = Path(__file__).parents[1] / "bin" / "migrate_placement_backed_pins.py"
ALICE_ID = "10000000-0000-0000-0000-000000000001"
BOB_ID = "10000000-0000-0000-0000-000000000002"
BOARD_ID = "20000000-0000-0000-0000-000000000001"
PIN_ID = "30000000-0000-0000-0000-000000000001"
SHARE_ID = "40000000-0000-0000-0000-000000000001"
ORDERING_ID = "50000000-0000-0000-0000-000000000001"
CREATED_AT = "2025-01-02T03:04:05+00:00"


def source_records():
	return [
		{
			"_type": "User",
			"id": ALICE_ID,
			"created_at": CREATED_AT,
			"name": "Alice",
			"open_in_new_tab": False,
		},
		{
			"_type": "User",
			"id": BOB_ID,
			"created_at": CREATED_AT,
			"name": "Bob",
			"open_in_new_tab": True,
		},
		{
			"_type": "Board",
			"id": BOARD_ID,
			"created_at": CREATED_AT,
			"title": "Reading",
			"user_id": ALICE_ID,
		},
		{
			"_type": "Pin",
			"id": PIN_ID,
			"created_at": CREATED_AT,
			"url": "https://example.com/essay",
			"title": "An essay",
			"note": "Read this later",
			"board_id": BOARD_ID,
			"user_id": ALICE_ID,
		},
		{
			"_type": "Share",
			"id": SHARE_ID,
			"created_at": CREATED_AT,
			"board_id": BOARD_ID,
			"user_id": BOB_ID,
		},
		{
			"_type": "Ordering",
			"id": ORDERING_ID,
			"created_at": CREATED_AT,
			"user_id": BOB_ID,
			"board_id": BOARD_ID,
			"position": 2,
		},
	]


def run_migration(path: Path):
	return subprocess.run(
		[sys.executable, str(SCRIPT), str(path)],
		text=True,
		capture_output=True,
		check=False,
	)


def write_records(path: Path, records):
	path.write_text(json.dumps(records))


def test_migrates_store_to_new_schema():
	with TemporaryDirectory() as directory:
		path = Path(directory) / "store.json"
		records = source_records()
		share = records[4].copy()
		ordering = records[5].copy()
		write_records(path, records)
		os.chmod(path, 0o640)

		result = run_migration(path)
		migrated = json.loads(path.read_text())
		store = Format(schema).decode(migrated)
		board = store.find_one(Board, UUID(BOARD_ID))
		pin = store.find_one(Pin, UUID(PIN_ID))
		placement = store.find_all(Placement)[0]

		assert_eq(result.returncode, 0)
		assert_that(str(path) in result.stdout)
		assert_that("1 Boards, 1 Pins, created 1 Placements" in result.stdout)
		assert_eq(stat.S_IMODE(path.stat().st_mode), 0o640)
		assert_eq(board.title, "Reading")
		assert_eq(board.creator_id, UUID(ALICE_ID))
		assert_eq(pin.url, "https://example.com/essay")
		assert_eq(pin.title, "An essay")
		assert_eq(pin.note, "Read this later")
		assert_eq(pin.creator_id, UUID(ALICE_ID))
		assert_eq(str(placement.pin_id), PIN_ID)
		assert_eq(str(placement.board_id), BOARD_ID)
		assert_eq(str(placement.adder_id), ALICE_ID)
		assert_eq(placement.created_at.isoformat(), CREATED_AT)
		assert_eq(next(row for row in migrated if row["_type"] == "Share"), share)
		assert_eq(next(row for row in migrated if row["_type"] == "Ordering"), ordering)
		assert_eq(len(store.find_all(Share)), 1)
		assert_eq(len(store.find_all(Ordering)), 1)
		original_ids = {row["id"] for row in records}
		migrated_original_ids = {
			row["id"] for row in migrated if row["_type"] != "Placement"
		}
		assert_eq(migrated_original_ids, original_ids)


def test_rejects_invalid_stores_without_changing_file():
	invalid_stores = []

	null_board = source_records()
	null_board[3]["board_id"] = None
	invalid_stores.append((null_board, PIN_ID))

	mixed = source_records()
	mixed[3]["creator_id"] = mixed[3].pop("user_id")
	del mixed[3]["board_id"]
	invalid_stores.append((mixed, "mixes source and destination"))

	duplicate = source_records()
	duplicate.append(duplicate[2].copy())
	invalid_stores.append((duplicate, "duplicate model ID"))

	missing_creator = source_records()
	del missing_creator[2]["user_id"]
	invalid_stores.append((missing_creator, "missing its creator"))

	invalid_stores.append(({"not": "an array"}, "top-level JSON value"))

	with TemporaryDirectory() as directory:
		for index, (records, expected_error) in enumerate(invalid_stores):
			path = Path(directory) / f"invalid-{index}.json"
			write_records(path, records)
			before = path.read_bytes()

			result = run_migration(path)

			assert_eq(result.returncode, 1)
			assert_that(expected_error in result.stderr)
			assert_eq(path.read_bytes(), before)


def test_rejects_placement_mixed_with_legacy_pin():
	with TemporaryDirectory() as directory:
		path = Path(directory) / "store.json"
		records = source_records()
		records.append(
			{
				"_type": "Placement",
				"id": "60000000-0000-0000-0000-000000000001",
				"created_at": CREATED_AT,
				"pin_id": PIN_ID,
				"board_id": BOARD_ID,
				"adder_id": ALICE_ID,
			}
		)
		write_records(path, records)
		before = path.read_bytes()

		result = run_migration(path)

		assert_eq(result.returncode, 1)
		assert_that("Placement records are present" in result.stderr)
		assert_eq(path.read_bytes(), before)


def test_already_migrated_store_is_unchanged():
	with TemporaryDirectory() as directory:
		path = Path(directory) / "store.json"
		write_records(path, source_records())
		first = run_migration(path)
		before = path.read_bytes()

		second = run_migration(path)

		assert_eq(first.returncode, 0)
		assert_eq(second.returncode, 0)
		assert_that("No migration necessary" in second.stdout)
		assert_eq(path.read_bytes(), before)
