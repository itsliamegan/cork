import uuid
from datetime import datetime
from typing import Any

class Type:
	pass

class Str(Type):
	def encode(self, val: str) -> Any:
		return val

	def decode(self, val: Any) -> str:
		if isinstance(val, str):
			return val
		else:
			return str(val)

class Bool(Type):
	def encode(self, val: bool) -> Any:
		return val

	def decode(self, val: Any) -> bool:
		if isinstance(val, bool):
			return val
		else:
			return bool(val)

class UUID(Type):
	def encode(self, val: uuid.UUID) -> Any:
		return str(val)

	def decode(self, val: Any) -> uuid.UUID:
		if isinstance(val, uuid.UUID):
			return val
		else:
			return uuid.UUID(val)

class Date(Type):
	def encode(self, val: datetime) -> Any:
		return val.isoformat()

	def decode(self, val: Any) -> datetime:
		if isinstance(val, datetime):
			return val
		else:
			return datetime.fromisoformat(val)
