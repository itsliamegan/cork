from collections.abc import Iterable

class Header:
	def __init__(self, name: str, val: str | list[str]):
		self.name = name
		self.val = val if isinstance(val, list) else [val]

	def set(self, val: str | list[str]):
		if isinstance(val, list):
			self.val = val
		else:
			self.val = [val]

	def __add__(self, other: str) -> list[str]:
		return self.val + [other]

	def __iter__(self) -> Iterable[str]:
		return iter(self.val)

	def __str__(self) -> str:
		return ", ".join(self.val)

	def __repr__(self) -> str:
		return f"Header({repr(self.name)}, {repr(self.val)})"

class Headers:
	def __init__(self, pairs: dict[str, str | list[str]] | None = None):
		if pairs is None:
			pairs = {}
		headers = {}
		for raw_name in pairs:
			name = normalize(raw_name)
			headers[name] = Header(name, pairs[raw_name])
		self.headers = headers

	def __getitem__(self, name: str) -> Header:
		return self.headers[normalize(name)]

	def __setitem__(self, raw_name: str, val: str | list[str]):
		name = normalize(raw_name)
		if name in self.headers:
			self.headers[name].set(val)
		else:
			self.headers[name] = Header(name, val)

	def __contains__(self, name: str) -> bool:
		return normalize(name) in self.headers

	def __iter__(self) -> Iterable[tuple[str, str]]:
		for name in self.headers:
			yield name, str(self.headers[name])

	def __repr__(self) -> str:
		return f"Headers({repr(self.headers)})"

def normalize(raw_name: str) -> str:
	parts = raw_name.split("-")
	name = "-".join(part.lower().capitalize() for part in parts)
	return name
