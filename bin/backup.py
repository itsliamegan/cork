#!/usr/bin/env python

from compression import zstd
from datetime import UTC, date, datetime, timedelta
import hashlib
from pathlib import Path
import re
import sqlite3
import sys
from tempfile import TemporaryDirectory

from boto3 import client
from helios.config import ConfigError
from luna.cli import Option, Program

import app.config

ZSTD_LEVEL = 10
KEEP_DAYS = 30


class Config(app.config.Config):
	def __init__(self, values: dict[str, str]):
		super().__init__(values)

		self.endpoint = self.require("APP_BACKUP_ENDPOINT")
		self.access_key_id = self.require("APP_BACKUP_ACCESS_KEY_ID")
		self.secret_access_key = self.require("APP_BACKUP_SECRET_ACCESS_KEY")
		self.bucket = self.require("APP_BACKUP_BUCKET")
		self.prefix = self.text("APP_BACKUP_PREFIX", "backups").strip("/")


def main(dry: bool, keep: int):
	"""Back up the database to Cloudflare R2."""

	try:
		config = Config.load(env_file=app.config.ENV_FILE)
	except ConfigError as error:
		raise SystemExit(f"backup: error: {error}") from None

	s3 = client(
		"s3",
		endpoint_url=config.endpoint,
		aws_access_key_id=config.access_key_id,
		aws_secret_access_key=config.secret_access_key,
		region_name="auto",
	)
	archive = Archive(config)

	backup(s3, archive, config, dry)
	prune(s3, archive, keep, dry)


def backup(s3, archive: Archive, config: Config, dry: bool):
	"""Upload a compressed snapshot of the database."""

	raw = snapshot(config)
	body = zstd.compress(raw, level=ZSTD_LEVEL)
	key = archive.key(datetime.now(UTC).date())

	print(f"store  {len(raw)} bytes sha256:{hashlib.sha256(raw).hexdigest()}")
	print(f"object {key} {len(body)} bytes")

	if dry:
		print("dry run: nothing uploaded")
		return

	s3.put_object(Bucket=archive.bucket, Key=key, Body=body)
	print(f"uploaded to {archive.bucket}/{key}")


def prune(s3, archive: Archive, keep: int, dry: bool):
	"""Delete backup objects older than the retention window."""

	cutoff = datetime.now(UTC).date() - timedelta(days=keep)
	keys = expired(s3, archive, cutoff)

	if not keys:
		print(f"keep   nothing taken before {cutoff.isoformat()}")
		return

	for key in keys:
		print(f"prune  {key}")

	if dry:
		print(f"dry run: nothing deleted ({len(keys)} would be)")
		return

	result = s3.delete_objects(
		Bucket=archive.bucket,
		Delete={"Objects": [{"Key": key} for key in keys]},
	)

	failures = 0
	for error in result.get("Errors", []):
		failures += 1
		print(f"backup: error: {error["Key"]}: {error["Message"]}", file=sys.stderr)

	print(f"deleted {len(keys) - failures} object(s) taken before {cutoff.isoformat()}")

	if failures:
		raise SystemExit(1)


def snapshot(config: Config) -> bytes:
	"""Copy the live database with VACUUM INTO, and read the copy.

	VACUUM INTO produces a consistent snapshot while Cork keeps running, and
	rebuilds it compactly, leaving out the free pages a direct page copy
	would carry over from deletes and updates.
	"""

	source_uri = f"{config.database.database_file.resolve().as_uri()}?mode=ro"
	with TemporaryDirectory() as directory:
		destination_file = Path(directory, "snapshot.sqlite")
		source = sqlite3.connect(source_uri, uri=True)
		try:
			source.execute("VACUUM INTO ?", (str(destination_file),))
		finally:
			source.close()

		destination = sqlite3.connect(destination_file)
		try:
			(result,) = destination.execute("PRAGMA quick_check").fetchone()
		finally:
			destination.close()

		if result != "ok":
			raise SystemExit(f"backup: error: snapshot failed quick_check: {result}")
		return destination_file.read_bytes()


def expired(s3, archive: Archive, cutoff: date) -> list[str]:
	"""List the keys of backup objects taken before the cutoff date."""

	pages = s3.get_paginator("list_objects_v2").paginate(
		Bucket=archive.bucket,
		Prefix=f"{archive.prefix}/",
	)

	keys = []
	for page in pages:
		for item in page.get("Contents", []):
			taken = archive.taken(item["Key"])
			if taken is not None and taken < cutoff:
				keys.append(item["Key"])
	return keys


class Archive:
	"""The dated backup objects held under a prefix in the bucket."""

	# The name is written in one place and read back with a pattern derived
	# from it, so the two directions cannot drift apart. Only names matching
	# it exactly are ever eligible for deletion. Backups taken before the move
	# to SQLite used the JSON name; recognising it lets them age out.
	NAME = "store-{date}.sqlite.zst"
	NAMES = (NAME, "store-{date}.json.zst")
	PATTERNS = tuple(
		re.compile(re.escape(name).replace(r"\{date\}", r"(\d{4}-\d{2}-\d{2})"))
		for name in NAMES
	)

	def __init__(self, config: Config):
		self.bucket = config.bucket
		self.prefix = config.prefix

	def key(self, taken: date) -> str:
		"""Build the key of the backup object taken on a given date."""

		return f"{self.prefix}/{self.NAME.format(date=taken.isoformat())}"

	def taken(self, key: str) -> date | None:
		"""Read the date out of an object key, or None if it isn't one of ours."""

		name = key.removeprefix(f"{self.prefix}/")
		for pattern in self.PATTERNS:
			match = pattern.fullmatch(name)
			if match is not None:
				break
		else:
			return None

		try:
			return date.fromisoformat(match.group(1))
		except ValueError:
			return None


program = Program(
	"backup",
	main,
	description=main.__doc__,
	options=[
		Option(
			"dry",
			short="d",
			type=bool,
			help="report what would be uploaded and deleted, without doing either",
		),
		Option(
			"keep",
			short="k",
			type=int,
			default=KEEP_DAYS,
			help=f"days of backups to retain (default: {KEEP_DAYS})",
		),
	],
)


if __name__ == "__main__":
	program.run(sys.argv)
