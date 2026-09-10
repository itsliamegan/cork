#!/usr/bin/env python

from compression import zstd
from datetime import UTC, datetime
import hashlib
import sys

from boto3 import client
from helios.config import ConfigError
from helios.persist.files import Files
from luna.cli import Option, Program

import app.config

ZSTD_LEVEL = 10


class Config(app.config.Config):
	def __init__(self, values: dict[str, str]):
		super().__init__(values)

		self.endpoint = self.require("APP_BACKUP_ENDPOINT")
		self.access_key_id = self.require("APP_BACKUP_ACCESS_KEY_ID")
		self.secret_access_key = self.require("APP_BACKUP_SECRET_ACCESS_KEY")
		self.bucket = self.require("APP_BACKUP_BUCKET")
		self.prefix = self.text("APP_BACKUP_PREFIX", "backups").strip("/")


def snapshot(config: Config) -> bytes:
	"""Read the contents of the store file while holding the persistence lock."""

	with Files(config.persist).lock():
		return config.data.store_file.read_bytes()


def backup(dry: bool):
	"""Back up the data store to Cloudflare R2."""

	try:
		config = Config.load(env_file=app.config.ENV_FILE)
	except ConfigError as error:
		raise SystemExit(f"backup: error: {error}") from None

	raw = snapshot(config)
	body = zstd.compress(raw, level=ZSTD_LEVEL)
	key = f"{config.prefix}/store-{datetime.now(UTC).date().isoformat()}.json.zst"

	print(f"store  {len(raw)} bytes sha256:{hashlib.sha256(raw).hexdigest()}")
	print(f"object {key} {len(body)} bytes")

	if dry:
		print("dry run: nothing uploaded")
		return

	client(
		"s3",
		endpoint_url=config.endpoint,
		aws_access_key_id=config.access_key_id,
		aws_secret_access_key=config.secret_access_key,
		region_name="auto",
	).put_object(Bucket=config.bucket, Key=key, Body=body)
	print(f"uploaded to {config.bucket}/{key}")


program = Program(
	"backup",
	backup,
	description=backup.__doc__,
	options=[
		Option(
			"dry",
			short="d",
			type=bool,
			help="snapshot and compress without uploading",
		)
	],
)


if __name__ == "__main__":
	program.run(sys.argv)
