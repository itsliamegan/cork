from uuid import UUID

from helios.database import Model, attr
from helios.http import URL


class Pin(Model):
	table = "pins"

	url = attr(str)
	title = attr(str)
	note = attr(str, default="")
	creator_id = attr(UUID)

	def display_url(self) -> str:
		try:
			host = URL(self.url).host
		except ValueError:
			return self.url
		return host.removeprefix("www.") if host else self.url
