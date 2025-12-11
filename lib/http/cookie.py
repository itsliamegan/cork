from collections.abc import Iterable

from .headers import Headers

class Cookie:
	def __init__(self, name: str, val: str):
		self.name = name
		self.val = val

	def __str__(self) -> str:
		return f"{self.name}={self.val}"

	def __repr__(self) -> str:
		return f"Cookie(name={self.name}, val={self.val})"

class Cookies:
	def __init__(self, pairs: dict[str, str] | None = None):
		if pairs is None:
			pairs = {}
		cookies = {}
		for name in pairs:
			cookies[name] = Cookie(name, pairs[name])
		self.cookies = cookies

	@classmethod
	def from_headers(cls, headers: Headers) -> "Cookies":
		cookies = cls()
		if "Cookie" not in headers:
			return cookies
		cookie_pairs = str(headers["Cookie"]).split(";")
		for cookie_pair in cookie_pairs:
			name, val = cookie_pair.split("=")
			cookies[name] = val
		return cookies

	def to_headers(self) -> Headers:
		headers = Headers()
		if len(self.cookies) > 0:
			headers["Set-Cookie"] = []
			for name in self.cookies:
				headers["Set-Cookie"] += str(self.cookies[name])
		return headers

	def __getitem__(self, name: str) -> Cookie:
		return self.cookies[name]

	def __setitem__(self, name: str, val: str):
		if name in self.cookies:
			self.cookies[name].val = val
		else:
			self.cookies[name] = Cookie(name, val)
