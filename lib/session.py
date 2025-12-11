import json
from pathlib import Path
from typing import Any
from uuid import UUID

from lib.app import Component, Context

class Component(Component):
	def __init__(self, file: Path):
		self.file = file
		self.sessions = None

	def before(self, ctx: Context):
		self.sessions = load(self.file)
		ctx.session = None

	def after(self, ctx: Context):
		save(self.file, self.sessions)

class Session:
	def __init__(self, id: UUID, items: dict[str, Any] | None = None):
		if items is None:
			items = {}
		self.id = id
		self.items = items

	def __getitem__(self, key: str) -> Any:
		return self.items[key]

	def __setitem__(self, key: str, val: Any):
		self.items[key] = val

class Sessions:
	def __init__(self, sessions: dict[UUID, Session] | None = None):
		if sessions is None:
			sessions = {}
		self.sessions = sessions

	def get(self, id: UUID) -> Session:
		return self.sessions[id]

	def put(self, session: Session):
		self.sessions[session.id] = session

def save(path: Path, sessions: Sessions):
	with open(path, "w") as file:
		data = encode(sessions)
		json.dump(data, file)

def load(path: Path) -> Sessions:
	with open(path, "r") as file:
		data = json.load(file)
		sessions = decode(data)
		return sessions

def encode(sessions: Sessions) -> dict[str, Any]:
	data = {}
	for id in sessions.sessions:
		data[str(id)] = sessions.sessions[id].items
	return data

def decode(data: dict[str, Any]) -> Sessions:
	sessions = {}
	for raw_id in data:
		id = UUID(raw_id)
		sessions[id] = Session(id, data[raw_id])
	return Sessions(sessions)
