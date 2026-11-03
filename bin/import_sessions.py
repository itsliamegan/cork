#!/usr/bin/env python

from datetime import datetime
import json
from pathlib import Path
import sys

from helios.config import Environment
from helios.database import Database
from helios.session import Session, Token
from helios.session.driver import database
from luna.cli import Program

import app.config
from app.wsgi import Application


class Import(Program):
	"""Import the sessions in the session file into the database.

	A session already in the database or expired is skipped, so the import can
	run again. Every session is imported in one transaction.
	"""

	name = "import_sessions"

	def run(self):
		environment = Environment.load(env_file=app.config.ENV_FILE)
		path = environment.path(
			"APP_SESSION_STORE_FILE",
			Path(app.config.DATA_DIR, "sessions.json"),
		)
		maximum_age = app.config.session(environment).maximum_age
		entries = json.loads(path.read_text())

		imported = 0
		existing = 0
		expired = 0
		with Application(environment) as application:
			application.boot()
			with application.container.get(Database).store() as store:
				driver = database.Driver(store)
				for plaintext, entry in entries.items():
					# The cookie holds the old session ID, which becomes the token.
					token = Token.from_plaintext(plaintext)
					if driver.read(token) is not None:
						existing += 1
						continue

					raw_last_active_at = entry["last_active_at"]
					if raw_last_active_at is None:
						# A session with no activity time starts active now.
						last_active_at = None
					else:
						last_active_at = datetime.fromisoformat(raw_last_active_at)
					session = Session(token, entry["items"], last_active_at)
					if session.is_expired(maximum_age):
						expired += 1
					else:
						driver.write(session)
						imported += 1

		print(f"import {imported} session(s) from {path}")
		print(f"skip   {existing} already imported")
		print(f"skip   {expired} expired")


if __name__ == "__main__":
	Import.main(sys.argv)
